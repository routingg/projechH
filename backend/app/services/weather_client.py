"""기상청 단기예보 + 기상특보 조회 (data.go.kr 1360000).

- 단기예보(getVilageFcst): 강수확률(POP)·풍속(WSD)·기온(TMP)·습도(REH)·강수량(PCP)
- 기상특보(getWthrWrnList): 제주 지역 현행 특보 문구

키(kma_api_key)가 없거나 미승인(403)·오류 시 mock_weather.json 으로 fallback.
"""
import logging
import time
from datetime import datetime, timedelta

import requests

from app.config import get_settings
from app.services import data_loader

logger = logging.getLogger(__name__)

# 간단한 TTL 캐시 (10분) — 요청마다 외부 호출하지 않도록
_CACHE: dict[str, object] = {"data": None, "ts": 0.0}
_CACHE_TTL = 600.0

# 단기예보 발표시각 (매일 02,05,08,11,14,17,20,23시, 약 10분 뒤 제공)
_BASE_TIMES = ["2300", "2000", "1700", "1400", "1100", "0800", "0500", "0200"]


def _latest_base(now: datetime) -> tuple[str, str]:
    """현재 시각 기준 가장 최근의 (base_date, base_time)."""
    for _ in range(9):  # 최대 하루 전까지 되짚기
        hhmm = now.strftime("%H%M")
        for bt in _BASE_TIMES:
            # 발표 후 15분 여유
            if hhmm >= f"{int(bt)//100:02d}{int(bt)%100+15:02d}":
                return now.strftime("%Y%m%d"), bt
        now -= timedelta(days=1)
        now = now.replace(hour=23, minute=59)
    return now.strftime("%Y%m%d"), "0200"


def _heat_risk(temp: float | None) -> str:
    if temp is None:
        return "normal"
    if temp >= 35:
        return "danger"
    if temp >= 33:
        return "warning"
    return "normal"


def fetch_forecast() -> dict:
    """단기예보를 조회해 그 날의 대표 위험 지표로 요약한다. 실패 시 예외."""
    s = get_settings()
    base_date, base_time = _latest_base(datetime.now())
    r = requests.get(
        s.kma_forecast_url,
        params={
            "serviceKey": s.kma_api_key,
            "pageNo": 1,
            "numOfRows": 800,
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": s.kma_grid_nx,
            "ny": s.kma_grid_ny,
        },
        timeout=s.public_api_timeout_seconds,
    )
    r.raise_for_status()
    items = r.json()["response"]["body"]["items"]["item"]

    # 가장 이른 예보일자의 값만 집계 (당일/익일 기준)
    target = min(i["fcstDate"] for i in items)
    day = [i for i in items if i["fcstDate"] == target]

    def vals(cat: str) -> list[float]:
        out = []
        for i in day:
            if i["category"] == cat:
                try:
                    out.append(float(i["fcstValue"]))
                except ValueError:
                    pass
        return out

    pop = vals("POP")
    wsd = vals("WSD")
    tmp = vals("TMP")
    reh = vals("REH")
    pcp = [v for v in vals("PCP") if v]  # 강수없음은 문자열이라 제외됨

    temp = round(sum(tmp) / len(tmp), 1) if tmp else None
    return {
        "area": "제주시",
        "date": f"{target[:4]}-{target[4:6]}-{target[6:]}",
        "rain_probability": int(max(pop)) if pop else 0,
        "rain_amount": round(max(pcp), 1) if pcp else 0,
        "wind_speed": round(max(wsd), 1) if wsd else 0,
        "temperature": temp,
        "humidity": int(max(reh)) if reh else None,
        "weather_alert": None,  # 특보는 별도 조회로 채운다
        "heat_risk": _heat_risk(temp),
    }


def _clean_alert(title: str) -> str | None:
    """"[특보] 제07-23호 : 2026.07.08.10:00 / 폭염주의보 발표 (*)" → "폭염주의보".
    해제된 특보면 None."""
    part = title.split("/")[-1].strip()  # "폭염주의보 발표 (*)"
    if "해제" in part:
        return None
    return part.replace("발표", "").replace("(*)", "").strip() or None


def fetch_alert() -> str | None:
    """제주 지역 현행 기상특보(발표 중) 문구. 없거나 실패면 None."""
    s = get_settings()
    today = datetime.now().strftime("%Y%m%d")
    frm = (datetime.now() - timedelta(days=2)).strftime("%Y%m%d")
    r = requests.get(
        s.kma_alert_url,
        params={
            "serviceKey": s.kma_api_key,
            "pageNo": 1,
            "numOfRows": 20,
            "dataType": "JSON",
            "stnId": s.kma_stn_id,
            "fromTmFc": frm,
            "toTmFc": today,
        },
        timeout=s.public_api_timeout_seconds,
    )
    r.raise_for_status()
    items = r.json()["response"]["body"]["items"]["item"]
    items = items if isinstance(items, list) else [items]
    # 최신순(tmFc 내림차순)으로 첫 '발표' 특보를 채택
    for it in sorted(items, key=lambda x: x.get("tmFc", 0), reverse=True):
        alert = _clean_alert(it.get("title", ""))
        if alert:
            return alert
    return None


def get_weather() -> dict:
    """실 기상 데이터. 키 없거나 실패 시 mock_weather.json 으로 fallback. 10분 캐시."""
    s = get_settings()
    if not s.kma_api_key.strip():
        return data_loader.load_weather()

    if _CACHE["data"] is not None and time.time() - float(_CACHE["ts"]) < _CACHE_TTL:
        return _CACHE["data"]  # type: ignore[return-value]

    try:
        weather = fetch_forecast()
        try:
            alert = fetch_alert()
            weather["weather_alert"] = alert
            # 폭염특보가 있으면 heat_risk 상향 (기온 집계만으로는 놓칠 수 있음)
            if alert and "폭염" in alert:
                weather["heat_risk"] = "danger" if "경보" in alert else "warning"
        except Exception as exc:  # noqa: BLE001 - 특보 실패는 예보만으로 진행
            logger.warning("기상특보 조회 실패: %s", exc)
        _CACHE.update(data=weather, ts=time.time())
        return weather
    except Exception as exc:  # noqa: BLE001
        logger.warning("기상청 API 실패, mock 으로 fallback: %s", exc)
        return data_loader.load_weather()
