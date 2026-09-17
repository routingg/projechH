# 항공편 기반 다일정(몇박 며칠) 추천 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 도착·출발 항공편(편명 조회)을 입력받아 N박 M일을 계산하고, 권역 클러스터링된 일자별 일정을 추천한다.

**Architecture:** 신규 `flight_client`(B551178 조회)와 `multi_itinerary_service`(오케스트레이터)가 기존 하루 일정 엔진(`itinerary_service._pick_visits`)을 하루 단위 부품으로 재사용한다. 기존 `/api/itinerary`는 무변경 유지, `/api/itinerary/multi`·`/api/flights` 신설. 프론트는 PlannerConditionBar 의 날짜·출도시간을 항공편 2줄 입력으로 교체하고 일정 스텝을 일자별 아코디언으로 확장한다.

**Tech Stack:** FastAPI + pydantic, pytest(신규 설치), React+TS+Tailwind v4. 상세 스펙: `docs/superpowers/specs/2026-07-14-multi-day-itinerary-design.md`

## Global Constraints

- 모든 명령은 `source ~/miniconda3/etc/profile.d/conda.sh && conda activate projecth` 후 실행 (시스템 node/python 구버전)
- 기존 스키마·엔드포인트 필드 제거 금지 (팀원 RAG 계약) — 추가만 허용
- 데이터에 없는 사실 표시 금지: 예보 범위 밖 날짜는 `forecast_available=false` 로 정직 표기
- API 키는 .env 만, 커밋 금지. 항공 API 키는 `data_go_kr_api_key or kma_api_key` 폴백
- 커밋 메시지는 한국어 conventional commit + `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- B551178 실측 사실: 오퍼레이션 `arrival`/`depart`(단수), 파라미터 `searchday=YYYYMMDD, airport_code=CJU, flight_id(정확일치), type=json`, 시각 필드 `scheduledatetime/estimateddatetime`(YYYYMMDDHHMM), 상태 `rmkKor`, 조회 범위 오늘~약+3일

---

### Task 1: flight_client 서비스 (TDD)

**Files:**
- Create: `backend/app/services/flight_client.py`
- Create: `backend/tests/__init__.py` (빈 파일), `backend/tests/test_flight_client.py`
- Modify: `backend/app/config.py` (kac_flight_url 추가)

**Interfaces:**
- Produces: `search_flights(direction: str, date: str, flight_id: str | None = None) -> list[dict]`
  — direction ∈ {"arrival","departure"}, date="YYYY-MM-DD". 반환 dict 키:
  `flight_id, airline, counterpart_airport, scheduled_time("HH:MM"|None), estimated_time, status, is_cancelled(bool), date("YYYY-MM-DD")`. 실패·0건 → `[]`.

- [ ] **Step 1: pytest 설치** — `pip install pytest` (projecth), `mkdir -p backend/tests && touch backend/tests/__init__.py`
- [ ] **Step 2: 실패 테스트 작성** `backend/tests/test_flight_client.py`:

```python
"""flight_client 단위 테스트 — 외부 호출은 monkeypatch 로 대체."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import flight_client


SAMPLE = {"response": {"header": {"resultCode": "00"}, "body": {"totalCount": 2, "items": {"item": [
    {"flightid": "RS901", "airline": "에어서울", "depAirport": "서울/김포", "arrAirport": "제주",
     "scheduledatetime": "202607140715", "estimateddatetime": "202607140707",
     "rmkKor": "도착", "searchday": "20260714", "line": "국내"},
    {"flightid": "TW701", "airline": "티웨이항공", "depAirport": "서울/김포", "arrAirport": "제주",
     "scheduledatetime": "202607140650", "estimateddatetime": "202607140650",
     "rmkKor": "사전결항", "searchday": "20260714", "line": "국내"},
]}}}}


class _Resp:
    def raise_for_status(self):
        pass

    def json(self):
        return SAMPLE


def test_search_flights_maps_fields(monkeypatch):
    flight_client._CACHE.clear()
    monkeypatch.setattr(flight_client.requests, "get", lambda *a, **k: _Resp())
    flights = flight_client.search_flights("arrival", "2026-07-14")
    assert len(flights) == 2
    first = flights[0]  # 시간순 정렬 → 06:50 결항편이 먼저
    assert first["flight_id"] == "TW701"
    assert first["is_cancelled"] is True
    second = flights[1]
    assert second == {
        "flight_id": "RS901", "airline": "에어서울", "counterpart_airport": "서울/김포",
        "scheduled_time": "07:15", "estimated_time": "07:07", "status": "도착",
        "is_cancelled": False, "date": "2026-07-14",
    }


def test_search_flights_failure_returns_empty(monkeypatch):
    flight_client._CACHE.clear()

    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(flight_client.requests, "get", boom)
    assert flight_client.search_flights("departure", "2026-07-14") == []
```

- [ ] **Step 3: 실패 확인** — `cd backend && python -m pytest tests/test_flight_client.py -q` → `ModuleNotFoundError: app.services.flight_client` 계열 실패
- [ ] **Step 4: config.py 에 추가** (kakao_rest_key 블록 위):

```python
    # 한국공항공사 실시간 항공운항 현황 (제주 도착·출발 편명 조회)
    kac_flight_url: str = "https://apis.data.go.kr/B551178/flight-status"
```

- [ ] **Step 5: 구현** `backend/app/services/flight_client.py`:

```python
"""한국공항공사 실시간 항공운항 현황 (B551178/flight-status).

제주(CJU) 기준 도착/출발 항공편을 조회한다. 조회 범위는 대략 오늘~+3일이며,
범위 밖 날짜·호출 실패 시 빈 목록을 반환한다 (프론트가 시간 직접 입력으로 폴백).
"""
import logging
import time

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)

JEJU_AIRPORT_CODE = "CJU"
_CACHE: dict[tuple, tuple[float, list[dict]]] = {}
_CACHE_TTL = 600.0


def _fmt_time(value: str | None) -> str | None:
    """"202607140715" → "07:15"."""
    if not value or len(value) < 12:
        return None
    return f"{value[8:10]}:{value[10:12]}"


def _fmt_date(value: str | None) -> str | None:
    if not value or len(value) < 8:
        return None
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def _map_item(item: dict, direction: str) -> dict:
    counterpart = item.get("depAirport") if direction == "arrival" else item.get("arrAirport")
    status = (item.get("rmkKor") or "").strip() or None
    return {
        "flight_id": item.get("flightid"),
        "airline": item.get("airline"),
        "counterpart_airport": counterpart,
        "scheduled_time": _fmt_time(item.get("scheduledatetime")),
        "estimated_time": _fmt_time(item.get("estimateddatetime")),
        "status": status,
        "is_cancelled": bool(status and "결항" in status),
        "date": _fmt_date(item.get("searchday")),
    }


def search_flights(direction: str, date: str, flight_id: str | None = None) -> list[dict]:
    """제주 기준 항공편 조회. direction: arrival(제주 도착) | departure(제주 출발)."""
    s = get_settings()
    key = (s.data_go_kr_api_key or s.kma_api_key).strip()
    if not key:
        return []
    op = "arrival" if direction == "arrival" else "depart"
    searchday = date.replace("-", "")
    cache_key = (op, searchday, (flight_id or "").strip().upper())
    hit = _CACHE.get(cache_key)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        return hit[1]

    params: dict = {
        "serviceKey": key, "type": "json", "numOfRows": 500, "pageNo": 1,
        "searchday": searchday, "airport_code": JEJU_AIRPORT_CODE,
    }
    if flight_id:
        params["flight_id"] = flight_id.strip().upper()
    try:
        r = requests.get(f"{s.kac_flight_url}/{op}", params=params,
                         timeout=s.public_api_timeout_seconds)
        r.raise_for_status()
        body = r.json()["response"]["body"]
        raw = (body.get("items") or {}).get("item") or []
        raw = raw if isinstance(raw, list) else [raw]
        flights = sorted((_map_item(i, direction) for i in raw),
                         key=lambda f: f["scheduled_time"] or "99:99")
        _CACHE[cache_key] = (time.time(), flights)
        return flights
    except Exception as exc:  # noqa: BLE001 - 조회 실패는 빈 목록 (수동 입력 폴백)
        logger.warning("항공편 조회 실패(%s %s): %s", op, searchday, exc)
        return []
```

- [ ] **Step 6: 통과 확인** — `python -m pytest tests/test_flight_client.py -q` → 2 passed
- [ ] **Step 7: 커밋** — `feat: 항공편 조회 클라이언트 (KAC flight-status)`

### Task 2: GET /api/flights 라우터

**Files:**
- Create: `backend/app/schemas/flight.py`, `backend/app/routers/flights.py`
- Modify: `backend/app/main.py` (라우터 등록 — 기존 include_router 나열부에 1줄)

**Interfaces:**
- Consumes: `flight_client.search_flights`
- Produces: `GET /api/flights?direction=arrival|departure&date=YYYY-MM-DD&flight_id=` → `{"flights": FlightInfo[], "searchable": bool}` (searchable=false ⇒ 그 날짜 데이터 자체가 없음)

- [ ] **Step 1: 스키마** `backend/app/schemas/flight.py`:

```python
from pydantic import BaseModel


class FlightInfo(BaseModel):
    flight_id: str | None = None
    airline: str | None = None
    counterpart_airport: str | None = None
    scheduled_time: str | None = None
    estimated_time: str | None = None
    status: str | None = None
    is_cancelled: bool = False
    date: str | None = None


class FlightSearchResponse(BaseModel):
    flights: list[FlightInfo]
    # 그 날짜에 조회 가능한 운항 데이터가 있는지 (없으면 프론트가 시간 직접 입력 안내)
    searchable: bool
```

- [ ] **Step 2: 라우터** `backend/app/routers/flights.py`:

```python
from fastapi import APIRouter, Query

from app.schemas.flight import FlightSearchResponse
from app.services import flight_client

router = APIRouter(prefix="/api", tags=["flights"])


@router.get("/flights", response_model=FlightSearchResponse)
def search(
    direction: str = Query(..., pattern="^(arrival|departure)$"),
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    flight_id: str | None = Query(default=None),
) -> FlightSearchResponse:
    flights = flight_client.search_flights(direction, date, flight_id)
    if flights:
        return FlightSearchResponse(flights=flights, searchable=True)
    # 편명 미일치와 '날짜 범위 밖'을 구분 — 전체 목록 존재 여부로 판단 (캐시됨)
    any_flights = flight_client.search_flights(direction, date) if flight_id else []
    return FlightSearchResponse(flights=[], searchable=bool(any_flights))
```

- [ ] **Step 3: main.py 등록** — 기존 라우터 나열에 `from app.routers import flights` 및 `app.include_router(flights.router)` 추가 (기존 스타일 그대로)
- [ ] **Step 4: curl 검증** (uvicorn --reload 상태):

```bash
curl -s "localhost:8000/api/flights?direction=arrival&date=$(date +%F)" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['searchable'], len(d['flights']))"
# 기대: True 200+
curl -s "localhost:8000/api/flights?direction=departure&date=$(date -d '+10 days' +%F)&flight_id=KE1234" | python3 -m json.tool
# 기대: {"flights": [], "searchable": false}
```

- [ ] **Step 5: 커밋** — `feat: 항공편 조회 API (/api/flights)`

### Task 3: 일자별 예보 (weather_client 확장, TDD)

**Files:**
- Modify: `backend/app/services/weather_client.py`
- Create: `backend/tests/test_weather_daily.py`

**Interfaces:**
- Produces: `get_weather_daily() -> dict[str, dict]` — `{"2026-07-14": {rain_probability, wind_speed, temperature, weather_alert, ...}}`. 키 없음·실패 → `{}`. 특보는 가장 이른 날짜(오늘)에만 부여.
- 기존 `fetch_forecast()`/`get_weather()` 동작 불변 (회귀 0)

- [ ] **Step 1: 실패 테스트** `backend/tests/test_weather_daily.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import weather_client


ITEMS = [
    {"fcstDate": "20260714", "category": "POP", "fcstValue": "30"},
    {"fcstDate": "20260714", "category": "WSD", "fcstValue": "5.0"},
    {"fcstDate": "20260714", "category": "TMP", "fcstValue": "30"},
    {"fcstDate": "20260715", "category": "POP", "fcstValue": "80"},
    {"fcstDate": "20260715", "category": "WSD", "fcstValue": "12.5"},
    {"fcstDate": "20260715", "category": "TMP", "fcstValue": "27"},
]


def test_fetch_forecast_daily_groups_by_date(monkeypatch):
    monkeypatch.setattr(weather_client, "_fetch_items", lambda: ITEMS)
    daily = weather_client.fetch_forecast_daily()
    assert set(daily) == {"2026-07-14", "2026-07-15"}
    assert daily["2026-07-14"]["rain_probability"] == 30
    assert daily["2026-07-15"]["wind_speed"] == 12.5


def test_fetch_forecast_uses_earliest_date(monkeypatch):
    monkeypatch.setattr(weather_client, "_fetch_items", lambda: ITEMS)
    assert weather_client.fetch_forecast()["date"] == "2026-07-14"
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/test_weather_daily.py -q` → `_fetch_items 없음` 실패
- [ ] **Step 3: 리팩토링 구현** — `fetch_forecast()` 의 HTTP 부분을 `_fetch_items() -> list[dict]` 로, 집계 부분을 `_summarize(day_items: list[dict]) -> dict` 로 추출 (본문 로직 그대로 이동). 그리고:

```python
def fetch_forecast() -> dict:
    """단기예보를 조회해 가장 이른 날의 대표 위험 지표로 요약한다. 실패 시 예외."""
    items = _fetch_items()
    target = min(i["fcstDate"] for i in items)
    return _summarize([i for i in items if i["fcstDate"] == target])


def fetch_forecast_daily() -> dict[str, dict]:
    """예보를 일자별로 요약: {"YYYY-MM-DD": summary}. 단기예보 특성상 +2~3일 범위."""
    items = _fetch_items()
    out: dict[str, dict] = {}
    for target in sorted({i["fcstDate"] for i in items}):
        summary = _summarize([i for i in items if i["fcstDate"] == target])
        out[summary["date"]] = summary
    return out


_DAILY_CACHE: dict[str, object] = {"data": None, "ts": 0.0}


def get_weather_daily() -> dict[str, dict]:
    """일자별 실황(+특보는 오늘자에만). 키 없음·실패 → {} (호출부가 정직 표기)."""
    s = get_settings()
    if not s.kma_api_key.strip():
        return {}
    if _DAILY_CACHE["data"] is not None and time.time() - float(_DAILY_CACHE["ts"]) < _CACHE_TTL:
        return _DAILY_CACHE["data"]  # type: ignore[return-value]
    try:
        daily = fetch_forecast_daily()
        try:
            alert = fetch_alert()
            if alert and daily:
                first = min(daily)
                daily[first]["weather_alert"] = alert
                if "폭염" in alert:
                    daily[first]["heat_risk"] = "danger" if "경보" in alert else "warning"
        except Exception as exc:  # noqa: BLE001
            logger.warning("기상특보 조회 실패: %s", exc)
        _DAILY_CACHE.update(data=daily, ts=time.time())
        return daily
    except Exception as exc:  # noqa: BLE001
        logger.warning("일자별 예보 실패: %s", exc)
        return {}
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests -q` → 전체 passed. 회귀: `curl -s localhost:8000/api/itinerary -d '{"user_profile":{"wheelchair_type":"manual"}}' -H 'Content-Type: application/json'` 정상 응답
- [ ] **Step 5: 커밋** — `feat: 일자별 예보 집계 (get_weather_daily)`

### Task 4: 다일정 스키마 + itinerary_service 부품화

**Files:**
- Create: `backend/app/schemas/multi_itinerary.py`
- Modify: `backend/app/services/itinerary_service.py`

**Interfaces:**
- Produces (스키마): `MultiItineraryRequest{user_profile, arrival_date, arrival_time, departure_date, departure_time, selected_place_ids=[]}`, `ItineraryDay{date, day_label, region_label, forecast_available, weather_summary|None, slots}`, `MultiItineraryResponse{nights, days_count, trip_label, days, early_departure, cautions}`
- Produces (서비스): `_pick_visits(recs, risky, selected_place_ids, target_count=2)` (기본값으로 기존 동작 유지), 모듈 함수 `make_visit_slot(period, time_hint, title, rec, user_selected, risky) -> ItinerarySlot`, `make_lunch_slot() -> ItinerarySlot`

- [ ] **Step 1: 스키마** `backend/app/schemas/multi_itinerary.py`:

```python
from pydantic import BaseModel, Field

from app.schemas.itinerary import EarlyDeparture, ItinerarySlot, WeatherSummary
from app.schemas.user import UserProfile


class MultiItineraryRequest(BaseModel):
    user_profile: UserProfile
    arrival_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    arrival_time: str = Field(..., examples=["10:30"])
    departure_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    departure_time: str = Field(..., examples=["18:30"])
    selected_place_ids: list[str] = []


class ItineraryDay(BaseModel):
    date: str
    day_label: str        # "1일차"
    region_label: str     # "제주시권" | "동부" | "남부" | "서부" | "전체"
    forecast_available: bool = False
    weather_summary: WeatherSummary | None = None
    slots: list[ItinerarySlot]


class MultiItineraryResponse(BaseModel):
    nights: int
    days_count: int
    trip_label: str       # "당일 여행" | "2박 3일"
    days: list[ItineraryDay]
    early_departure: EarlyDeparture
    cautions: list[str]
```

- [ ] **Step 2: itinerary_service 부품화** — (a) `_pick_visits(..., target_count: int = 2)` 파라미터 추가, 내부 `need = max(0, 2 - len(selected))` → `need = max(0, target_count - len(selected))`. (b) `build_itinerary` 안의 중첩 `make_slot` 을 모듈 함수로 추출:

```python
def make_visit_slot(period: str, time_hint: str, title: str, rec,
                    user_selected: bool, risky: bool) -> ItinerarySlot:
    """방문 슬롯 1개를 만든다 (rec=None 이면 안내 슬롯)."""
    if rec is None:
        return ItinerarySlot(period=period, time_hint=time_hint, title=title,
                             reason="오늘 조건에 맞는 추천 장소가 부족합니다. 실내 휴식을 권장합니다.")
    is_alt = (not user_selected) and risky and rec.category == "indoor"
    if user_selected:
        reason = "직접 선택하신 장소입니다."
        if risky and rec.category == "outdoor":
            reason += " 기상 위험이 있는 실외 장소이니 현장 확인을 권장합니다."
        if rec.recommendation_level == "not_recommended":
            reason += " 오늘 조건에서는 이동 부담이 커 비추천 등급이니 무리하지 마세요."
    elif is_alt:
        reason = "기상 위험이 있어 실내 관광지로 배치했습니다."
    else:
        reason = f"이동가능성 {rec.mobility_feasibility_score}점으로 오늘 조건에 적합합니다."
    return ItinerarySlot(period=period, time_hint=time_hint, title=title,
                         place_id=rec.place_id, place_name=rec.name, category=rec.category,
                         lat=rec.lat, lon=rec.lon, reason=reason,
                         is_alternative=is_alt, is_user_selected=user_selected)


def make_lunch_slot() -> ItinerarySlot:
    return ItinerarySlot(period="lunch", time_hint="12:30", title="점심 식사",
                         reason="접근 가능한 식당에서 충분히 휴식한 뒤 오후 일정을 시작하세요.")
```

`build_itinerary` 내부의 `make_slot(...)` 호출부는 `slots.append(make_visit_slot(period, time_hint, title, rec, sel, risky))` 로, 점심 슬롯은 `slots.append(make_lunch_slot())` 로 대체 (출력 불변).
- [ ] **Step 3: 회귀 확인** — `python -m pytest tests -q` + Task 3 Step 4 의 /api/itinerary curl 재실행: 슬롯 구조가 이전과 동일
- [ ] **Step 4: 커밋** — `refactor: 일정 슬롯 생성 부품화 및 다일정 스키마`

### Task 5: multi_itinerary_service (TDD 핵심)

**Files:**
- Create: `backend/app/services/multi_itinerary_service.py`
- Create: `backend/tests/test_multi_itinerary.py`

**Interfaces:**
- Consumes: `itinerary_service._pick_visits/make_visit_slot/make_lunch_slot/shift_time/is_weather_risky/build_itinerary`, `weather_client.get_weather_daily`, `recommendation_service.build_recommendations`
- Produces: `region_of(lat, lon) -> str`, `build_multi_itinerary(user_profile, arrival_date, arrival_time, departure_date, departure_time, selected_place_ids=None) -> MultiItineraryResponse` (날짜 역전 시 `ValueError`)

- [ ] **Step 1: 실패 테스트** `backend/tests/test_multi_itinerary.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas.place import PlaceFacts, Recommendation
from app.schemas.user import UserProfile
from app.services import itinerary_service, multi_itinerary_service, recommendation_service, weather_client


def _rec(pid, name, lat, lon, level="conditional"):
    return Recommendation(
        place_id=pid, name=name, category="outdoor", lat=lat, lon=lon,
        accessibility_score=50, weather_risk_score=0, transport_score=50,
        airport_burden_score=0, mobility_feasibility_score=50,
        recommendation_level=level, warnings=[], facts=PlaceFacts(),
    )


FAKE_RECS = [
    _rec("p_jeju1", "제주시A", 33.50, 126.52), _rec("p_jeju2", "제주시B", 33.51, 126.49),
    _rec("p_south1", "서귀포A", 33.25, 126.56), _rec("p_south2", "서귀포B", 33.24, 126.40),
    _rec("p_east1", "동부A", 33.45, 126.91), _rec("p_west1", "서부A", 33.39, 126.24),
]
WEATHER = {"rain_probability": 10, "wind_speed": 3.0, "weather_alert": None}


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    monkeypatch.setattr(recommendation_service, "build_recommendations",
                        lambda *a, **k: list(FAKE_RECS))
    monkeypatch.setattr(weather_client, "get_weather_daily",
                        lambda: {"2026-07-20": dict(WEATHER), "2026-07-21": dict(WEATHER)})
    monkeypatch.setattr(weather_client, "get_weather", lambda: dict(WEATHER))


PROFILE = UserProfile(wheelchair_type="manual")


def test_region_of_rules():
    assert multi_itinerary_service.region_of(33.39, 126.24) == "서부"
    assert multi_itinerary_service.region_of(33.45, 126.91) == "동부"
    assert multi_itinerary_service.region_of(33.25, 126.56) == "남부"
    assert multi_itinerary_service.region_of(33.50, 126.52) == "제주시권"
    assert multi_itinerary_service.region_of(None, None) == "제주시권"


def test_same_day_is_single_trip():
    res = multi_itinerary_service.build_multi_itinerary(
        PROFILE, "2026-07-20", "10:30", "2026-07-20", "18:30")
    assert (res.nights, res.days_count, res.trip_label) == (0, 1, "당일 여행")
    assert len(res.days) == 1


def test_two_nights_three_days_regions_and_no_repeat():
    res = multi_itinerary_service.build_multi_itinerary(
        PROFILE, "2026-07-20", "10:30", "2026-07-22", "18:30")
    assert res.trip_label == "2박 3일"
    assert [d.region_label for d in res.days] == ["제주시권", "남부", "제주시권"]
    ids = [s.place_id for d in res.days for s in d.slots if s.place_id]
    assert len(ids) == len(set(ids))  # 날짜 간 장소 중복 없음
    assert res.days[-1].slots[-1].period == "pre_departure"
    assert res.days[2].forecast_available is False  # 07-22 는 예보 밖
    assert any("예보 범위" in c for c in res.cautions)


def test_selected_place_goes_to_matching_region_day():
    res = multi_itinerary_service.build_multi_itinerary(
        PROFILE, "2026-07-20", "10:30", "2026-07-22", "18:30",
        selected_place_ids=["p_south1"])
    south_day = res.days[1]
    slot = next(s for s in south_day.slots if s.place_id == "p_south1")
    assert slot.is_user_selected is True


def test_reversed_dates_raise():
    with pytest.raises(ValueError):
        multi_itinerary_service.build_multi_itinerary(
            PROFILE, "2026-07-22", "10:30", "2026-07-20", "18:30")
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/test_multi_itinerary.py -q` → import 실패
- [ ] **Step 3: 구현** `backend/app/services/multi_itinerary_service.py`:

```python
"""항공편 기반 다일정(몇박 며칠) 오케스트레이터.

기존 하루 일정 엔진(itinerary_service)을 하루 단위 부품으로 재사용해
도착~출발 사이의 일자별 일정을 만든다. 하루에 한 권역(제주시권/동부/남부/서부)을
배정해 휠체어 장거리 이동 부담을 줄이고, 날짜 간 장소를 중복시키지 않는다.
"""
from datetime import datetime, timedelta

from app.schemas.itinerary import EarlyDeparture, ItinerarySlot, WeatherSummary
from app.schemas.multi_itinerary import ItineraryDay, MultiItineraryResponse
from app.schemas.user import UserProfile
from app.services import itinerary_service, recommendation_service, weather_client

MIDDLE_REGIONS = ["남부", "동부", "서부"]  # 중간일 권역 순회 순서
ARRIVAL_BUFFER_MIN = 60                    # 도착 후 수속·이동 시간
AFTERNOON_ONLY_FROM = "12:00"              # 이후 시작이면 오전 슬롯 생략
SINGLE_VISIT_FROM = "14:00"                # 이후 시작이면 도착일 1곳만


def region_of(lat: float | None, lon: float | None) -> str:
    """좌표 → 권역. 좌표 없으면 제주시권(공항 인근) 취급."""
    if lat is None or lon is None:
        return "제주시권"
    if lon < 126.35:
        return "서부"
    if lon > 126.75:
        return "동부"
    if lat < 33.35:
        return "남부"
    return "제주시권"


def _add_minutes(hhmm: str, minutes: int) -> str:
    h, m = (int(x) for x in hhmm.split(":"))
    total = (h * 60 + m + minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def _day_slots(visits, risky, *, is_first, is_last, day_start, departure_time):
    """하루치 슬롯 구성 (도착일은 도착시간 이후, 출발일은 공항 이동으로 마감)."""
    slots: list[ItinerarySlot] = []
    afternoon_only = is_first and day_start >= AFTERNOON_ONLY_FROM

    if is_last:
        morning, afternoon = visits[:1], []
    elif afternoon_only:
        morning, afternoon = [], visits
    else:
        n = len(visits)
        mc = min(2, (n + 1) // 2) if n else 1
        morning, afternoon = visits[:mc], visits[mc:]

    first_morning = max(day_start, "09:30") if is_first else "09:30"
    m_hints = [first_morning, "11:00"]
    a_hints = ([max(day_start, "14:00"), "16:00", "17:00", "18:00"]
               if afternoon_only else ["14:00", "16:00", "17:00", "18:00"])

    airport_arrival = None
    if is_last:
        airport_arrival = itinerary_service.shift_time(
            departure_time, 150 if risky else 120)

    if not visits:
        period = "afternoon" if afternoon_only else "morning"
        hint = a_hints[0] if afternoon_only else m_hints[0]
        slots.append(itinerary_service.make_visit_slot(period, hint, "관광", None, False, risky))

    for j, (rec, sel) in enumerate(morning):
        title = "오전 관광" if len(morning) == 1 else f"오전 관광 {j + 1}"
        slots.append(itinerary_service.make_visit_slot(
            "morning", m_hints[min(j, 1)], title, rec, sel, risky))

    include_lunch = bool(visits) and not afternoon_only and (
        (airport_arrival or "23:59") > "13:30" if is_last else True)
    if include_lunch:
        slots.append(itinerary_service.make_lunch_slot())

    for j, (rec, sel) in enumerate(afternoon):
        title = "오후 관광" if len(afternoon) == 1 else f"오후 관광 {j + 1}"
        slots.append(itinerary_service.make_visit_slot(
            "afternoon", a_hints[min(j, 3)], title, rec, sel, risky))

    if is_last:
        slots.append(ItinerarySlot(
            period="pre_departure", time_hint=airport_arrival or "-",
            title="공항 이동 및 출도 준비",
            reason="출발 항공편에 맞춰 여유 있게 공항으로 이동하세요.",
        ))
    return slots


def build_multi_itinerary(
    user_profile: UserProfile,
    arrival_date: str, arrival_time: str,
    departure_date: str, departure_time: str,
    selected_place_ids: list[str] | None = None,
) -> MultiItineraryResponse:
    arr = datetime.strptime(arrival_date, "%Y-%m-%d").date()
    dep = datetime.strptime(departure_date, "%Y-%m-%d").date()
    if dep < arr:
        raise ValueError("출발일이 도착일보다 빠릅니다.")
    nights = (dep - arr).days
    profile = user_profile.model_copy(update={"departure_time": departure_time})

    if nights == 0:
        single = itinerary_service.build_itinerary(profile, arrival_date, selected_place_ids)
        day = ItineraryDay(date=arrival_date, day_label="1일차", region_label="전체",
                           forecast_available=True, weather_summary=single.weather_summary,
                           slots=single.slots)
        return MultiItineraryResponse(nights=0, days_count=1, trip_label="당일 여행",
                                      days=[day], early_departure=single.early_departure,
                                      cautions=single.cautions)

    dates = [(arr + timedelta(days=i)).isoformat() for i in range(nights + 1)]
    regions = (["제주시권"]
               + [MIDDLE_REGIONS[i % len(MIDDLE_REGIONS)] for i in range(nights - 1)]
               + ["제주시권"])

    daily_weather = weather_client.get_weather_daily()
    recs = recommendation_service.build_recommendations(profile, arrival_date)
    rec_by_id = {r.place_id: r for r in recs}

    # 담은 장소를 권역이 맞는 날에 배정 (맞는 날 없으면 중간일 순서대로)
    selected_by_day: list[list[str]] = [[] for _ in dates]
    missing: list[str] = []
    fallback_days = list(range(1, len(dates) - 1)) or [0]
    fb = 0
    for pid in dict.fromkeys(selected_place_ids or []):
        rec = rec_by_id.get(pid)
        if rec is None:
            missing.append(pid)
            continue
        want = region_of(rec.lat, rec.lon)
        idx = next((i for i, rg in enumerate(regions) if rg == want), None)
        if idx is None:
            idx = fallback_days[fb % len(fallback_days)]
            fb += 1
        selected_by_day[idx].append(pid)

    used: set[str] = set()
    days: list[ItineraryDay] = []
    cautions: list[str] = []
    out_of_forecast = False
    if missing:
        cautions.append(f"찾을 수 없어 제외한 선택 장소: {', '.join(missing)}")

    day_start = _add_minutes(arrival_time, ARRIVAL_BUFFER_MIN)

    for i, (d, rg) in enumerate(zip(dates, regions)):
        weather = daily_weather.get(d)
        available = weather is not None
        out_of_forecast = out_of_forecast or not available
        risky = itinerary_service.is_weather_risky(weather) if available else False

        is_first, is_last = i == 0, i == len(dates) - 1
        if is_last:
            target = 1
        elif is_first:
            target = 1 if day_start >= SINGLE_VISIT_FROM else 2
        else:
            target = 2

        pool = [r for r in recs if r.place_id not in used]
        primary = [r for r in pool if region_of(r.lat, r.lon) == rg]
        candidates = primary + [r for r in pool if r not in primary]  # 부족 시 타 권역 보충

        visits, day_cautions = itinerary_service._pick_visits(
            candidates, risky, selected_by_day[i], target_count=target)
        cautions.extend(c for c in day_cautions if c not in cautions)
        for rec, _sel in visits:
            used.add(rec.place_id)

        days.append(ItineraryDay(
            date=d, day_label=f"{i + 1}일차", region_label=rg,
            forecast_available=available,
            weather_summary=WeatherSummary(
                rain_probability=weather.get("rain_probability"),
                wind_speed=weather.get("wind_speed"),
                weather_alert=weather.get("weather_alert"),
            ) if available else None,
            slots=_day_slots(visits, risky, is_first=is_first, is_last=is_last,
                             day_start=day_start, departure_time=departure_time),
        ))

    last_weather = daily_weather.get(dates[-1])
    last_risky = itinerary_service.is_weather_risky(last_weather) if last_weather else False
    early = EarlyDeparture(
        recommended=last_risky,
        recommended_airport_arrival_time=itinerary_service.shift_time(
            departure_time, 150 if last_risky else 120),
        reason=("기상 악화로 이동 지연 가능성이 있어 평소보다 일찍 공항 도착을 권장합니다."
                if last_risky else "여유 있는 출도를 위해 출발 2시간 전 공항 도착을 권장합니다."),
    )

    if out_of_forecast:
        cautions.append("기상 예보 범위(약 3일) 밖 날짜는 날씨를 반영하지 못했습니다. "
                        "여행이 가까워지면 다시 확인하세요.")
    cautions += ["일정은 참고용이며 현장 상황과 최신 기상정보를 확인하세요.",
                 "확인되지 않은 편의시설은 방문 전 개별 확인이 필요합니다."]

    return MultiItineraryResponse(
        nights=nights, days_count=nights + 1, trip_label=f"{nights}박 {nights + 1}일",
        days=days, early_departure=early, cautions=cautions,
    )
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests -q` → 전체 passed
- [ ] **Step 5: 커밋** — `feat: 다일정 오케스트레이터 (권역 클러스터링·일자별 날씨)`

### Task 6: POST /api/itinerary/multi 라우터

**Files:**
- Modify: `backend/app/routers/itinerary.py`

**Interfaces:**
- Produces: `POST /api/itinerary/multi` (MultiItineraryRequest → MultiItineraryResponse, 날짜 역전 422)

- [ ] **Step 1: 라우터 추가** (`itinerary.py` 에 append):

```python
from fastapi import HTTPException

from app.schemas.multi_itinerary import MultiItineraryRequest, MultiItineraryResponse
from app.services import multi_itinerary_service


@router.post("/itinerary/multi", response_model=MultiItineraryResponse)
def build_multi(payload: MultiItineraryRequest) -> MultiItineraryResponse:
    try:
        return multi_itinerary_service.build_multi_itinerary(
            payload.user_profile,
            payload.arrival_date, payload.arrival_time,
            payload.departure_date, payload.departure_time,
            payload.selected_place_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
```

- [ ] **Step 2: curl 검증**:

```bash
curl -s localhost:8000/api/itinerary/multi -H 'Content-Type: application/json' -d '{
  "user_profile": {"wheelchair_type": "manual"},
  "arrival_date": "'$(date +%F)'", "arrival_time": "10:30",
  "departure_date": "'$(date -d "+2 days" +%F)'", "departure_time": "18:30"}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['trip_label']); [print(x['day_label'], x['region_label'], x['forecast_available'], len(x['slots'])) for x in d['days']]"
# 기대: 2박 3일 / 1일차 제주시권 True 4 / 2일차 남부 True 4 / 3일차 제주시권 ? 3
# 날짜 역전 → HTTP 422 확인, 같은 날 → "당일 여행" days 1개 확인
```

- [ ] **Step 3: 커밋** — `feat: 다일정 생성 API (/api/itinerary/multi)`

### Task 7: 프론트 API·타입

**Files:**
- Create: `frontend/src/api/flights.ts`
- Modify: `frontend/src/api/itinerary.ts`, `frontend/src/types/itinerary.ts`

**Interfaces:**
- Produces: `getFlights(direction, date, flightId?)`, `postItineraryMulti(profile, trip, selectedIds?)`, 타입 `FlightInfo/FlightSearchResponse/ItineraryDay/MultiItinerary/TripWindow`

- [ ] **Step 1:** `frontend/src/api/flights.ts`:

```ts
import { client } from "./client";

export interface FlightInfo {
  flight_id: string | null;
  airline: string | null;
  counterpart_airport: string | null;
  scheduled_time: string | null;
  estimated_time: string | null;
  status: string | null;
  is_cancelled: boolean;
  date: string | null;
}

export interface FlightSearchResponse {
  flights: FlightInfo[];
  searchable: boolean;
}

export async function getFlights(
  direction: "arrival" | "departure",
  date: string,
  flightId?: string
): Promise<FlightSearchResponse> {
  const { data } = await client.get<FlightSearchResponse>("/api/flights", {
    params: { direction, date, flight_id: flightId || undefined },
  });
  return data;
}
```

- [ ] **Step 2:** `types/itinerary.ts` 에 추가 (기존 타입 유지):

```ts
export interface ItineraryDay {
  date: string;
  day_label: string;
  region_label: string;
  forecast_available: boolean;
  weather_summary: WeatherSummary | null;
  slots: ItinerarySlot[];
}

export interface MultiItinerary {
  nights: number;
  days_count: number;
  trip_label: string;
  days: ItineraryDay[];
  early_departure: EarlyDeparture;
  cautions: string[];
}
```

- [ ] **Step 3:** `api/itinerary.ts` 에 추가:

```ts
import type { MultiItinerary } from "../types/itinerary";

export interface TripWindow {
  arrival_date: string;
  arrival_time: string;
  departure_date: string;
  departure_time: string;
}

export async function postItineraryMulti(
  user_profile: UserProfile,
  trip: TripWindow,
  selected_place_ids?: string[]
): Promise<MultiItinerary> {
  const { data } = await client.post<MultiItinerary>("/api/itinerary/multi", {
    user_profile,
    ...trip,
    selected_place_ids: selected_place_ids ?? [],
  });
  return data;
}
```

- [ ] **Step 4:** `npm run build` 통과 → 커밋 `feat: 항공편·다일정 프론트 API 클라이언트`

### Task 8: FlightField + PlannerConditionBar 항공편 입력

**Files:**
- Create: `frontend/src/components/FlightField.tsx`
- Modify: `frontend/src/components/PlannerConditionBar.tsx`

**Interfaces:**
- Produces: `FlightField` props `{label, direction, value: FlightValue, onChange(v: FlightValue)}`, `FlightValue = {date: string; time: string; flightId: string; resolved: FlightInfo | null; manual: boolean}`
- `PlannerValue` 확장: `{profile, query, arrival: FlightValue, departure: FlightValue}` — `profile.departure_time = departure.time`, 추천 travel_date 는 `arrival.date`

- [ ] **Step 1:** `frontend/src/components/FlightField.tsx`:

```tsx
import { useState } from "react";
import { getFlights, type FlightInfo } from "../api/flights";

export interface FlightValue {
  date: string;
  time: string;          // 확정된 시각 (조회 결과 또는 직접 입력)
  flightId: string;
  resolved: FlightInfo | null;
  manual: boolean;       // 시간 직접 입력 모드
}

const inputCls =
  "px-3 py-2 rounded-xl border border-brand-100 bg-white text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-brand-300";

export default function FlightField({
  label,
  direction,
  value,
  onChange,
}: {
  label: string; // "제주 도착" | "제주 출발"
  direction: "arrival" | "departure";
  value: FlightValue;
  onChange: (v: FlightValue) => void;
}) {
  const [searching, setSearching] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function search() {
    const flightId = value.flightId.trim();
    if (!flightId) {
      setNotice("편명을 입력해 주세요 (예: RS901)");
      return;
    }
    setSearching(true);
    setNotice(null);
    try {
      const res = await getFlights(direction, value.date, flightId);
      const found = res.flights[0];
      if (found) {
        const time = found.estimated_time ?? found.scheduled_time ?? value.time;
        onChange({ ...value, time, resolved: found, manual: false });
        if (found.is_cancelled) setNotice("cancelled");
      } else if (res.searchable) {
        onChange({ ...value, resolved: null, manual: true });
        setNotice(`${value.date} 에서 '${flightId}' 편을 찾지 못했어요. 시간을 직접 입력해 주세요.`);
      } else {
        onChange({ ...value, resolved: null, manual: true });
        setNotice("이 날짜는 아직 운항 정보가 없어요(오늘~약 3일 뒤까지 조회 가능). 시간을 직접 입력해 주세요.");
      }
    } catch {
      onChange({ ...value, resolved: null, manual: true });
      setNotice("항공편 조회에 실패했어요. 시간을 직접 입력해 주세요.");
    } finally {
      setSearching(false);
    }
  }

  const r = value.resolved;
  return (
    <div>
      <span className="text-xs font-semibold text-stone-500">{label}</span>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        <input
          type="date"
          className={inputCls}
          value={value.date}
          onChange={(e) => onChange({ ...value, date: e.target.value, resolved: null })}
          aria-label={`${label} 날짜`}
        />
        <input
          className={`${inputCls} w-28`}
          placeholder="편명 RS901"
          value={value.flightId}
          onChange={(e) => onChange({ ...value, flightId: e.target.value, resolved: null })}
          aria-label={`${label} 편명`}
        />
        <button
          type="button"
          onClick={search}
          disabled={searching}
          className="px-4 py-2 rounded-xl border border-brand-300 text-brand-700 bg-white hover:bg-brand-50 disabled:opacity-60 text-sm font-bold cursor-pointer"
        >
          {searching ? "조회 중…" : "🔍 편명 조회"}
        </button>
        {(value.manual || !r) && (
          <label className="flex items-center gap-1.5 text-xs font-semibold text-stone-500">
            시간 직접 입력
            <input
              type="time"
              className={inputCls}
              value={value.time}
              onChange={(e) => onChange({ ...value, time: e.target.value, manual: true })}
              aria-label={`${label} 시간`}
            />
          </label>
        )}
      </div>
      {r && (
        <p
          className={`m-0 mt-1.5 text-sm font-semibold ${
            r.is_cancelled ? "text-red-600" : "text-sea-700"
          }`}
        >
          {r.is_cancelled ? "⚠️ " : "✓ "}
          {r.airline} {r.flight_id} · {direction === "arrival"
            ? `${r.counterpart_airport} → 제주`
            : `제주 → ${r.counterpart_airport}`} · {r.estimated_time ?? r.scheduled_time}
          {r.is_cancelled && " — 결항으로 안내된 편입니다. 항공사에서 확인해 주세요."}
        </p>
      )}
      {notice && notice !== "cancelled" && (
        <p className="m-0 mt-1.5 text-sm text-stone-500">{notice}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: PlannerConditionBar 개편** — 상태 `travelDate/departureTime` 제거, 다음으로 대체:

```tsx
const [arrival, setArrival] = useState<FlightValue>({
  date: today(), time: "10:00", flightId: "", resolved: null, manual: false,
});
const [departure, setDeparture] = useState<FlightValue>({
  date: today(), time: "18:30", flightId: "", resolved: null, manual: false,
});
```

`PlannerValue` 를 `{ profile: UserProfile; query: string; arrival: FlightValue; departure: FlightValue }` 로 변경. `submit()` 의 profile 은 `departure_time: departure.time` 사용. 필수 조건 그리드(여행 날짜·출도 시간 자리)에 `<FlightField label="제주 도착" direction="arrival" value={arrival} onChange={setArrival} />` 와 `<FlightField label="제주 출발" direction="departure" ... />` 2줄 배치, 그 아래 여행 기간 배지:

```tsx
const nights = Math.round(
  (new Date(departure.date).getTime() - new Date(arrival.date).getTime()) / 86400000
);
// 렌더: nights < 0 → "출발일이 도착일보다 빠릅니다" (빨강, submit 버튼 disabled)
//        nights === 0 → "당일 여행" / nights > 0 → `${nights}박 ${nights + 1}일`
```

- [ ] **Step 3:** `npm run build` 통과 (PlannerPage 는 다음 태스크에서 맞춤 — 빌드 오류 나면 PlannerPage 의 `value.travelDate` 참조를 임시로 `value.arrival.date` 로 고쳐 통과시킴)
- [ ] **Step 4: 커밋** — `feat: 항공편 편명 조회 입력 (도착·출발, 수동 폴백)`

### Task 9: PlannerPage 다일정 렌더 + ItineraryTimeline 확장

**Files:**
- Modify: `frontend/src/pages/PlannerPage.tsx`, `frontend/src/components/ItineraryTimeline.tsx`

**Interfaces:**
- Consumes: `postItineraryMulti`, `MultiItinerary`, `PlannerValue{arrival, departure}`
- ItineraryTimeline 신규 optional props: `weatherLabel?: string`(기본 "오늘의 기상"), `hideWeather?: boolean`(기본 false)

- [ ] **Step 1: ItineraryTimeline** — props 확장 + 기상 배너에 적용(`hideWeather` 면 배너 생략, 라벨 치환), cautions 빈 배열이면 details 미렌더:

```tsx
export default function ItineraryTimeline({
  itinerary, weatherLabel = "오늘의 기상", hideWeather = false,
}: { itinerary: Itinerary; weatherLabel?: string; hideWeather?: boolean }) {
```

- [ ] **Step 2: PlannerPage** — `itinerary: Itinerary|null` → `multi: MultiItinerary|null`. `makeItinerary()`:

```tsx
const result = await postItineraryMulti(
  conditions.profile,
  {
    arrival_date: conditions.arrival.date,
    arrival_time: conditions.arrival.time,
    departure_date: conditions.departure.date,
    departure_time: conditions.departure.time,
  },
  cart.map((c) => c.place_id)
);
setMulti(result);
```

④ 섹션 렌더 — day → 기존 Itinerary 로 매핑해 재사용:

```tsx
{multi && (
  <section id="step-itinerary" className="scroll-mt-28 mt-8">
    <h2 className="text-lg font-extrabold text-stone-800 mb-2">
      ④ {multi.trip_label} 일정
    </h2>
    {multi.days.map((day, i) => (
      <details key={day.date} open={i === 0} className="group mb-3 bg-white/60 rounded-2xl border border-brand-100 p-4">
        <summary className="cursor-pointer list-none flex items-center gap-2 flex-wrap">
          <strong className="text-stone-800">{day.day_label}</strong>
          <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-brand-50 text-brand-700">{day.region_label}</span>
          <span className="text-xs text-stone-500">{day.date}</span>
          {!day.forecast_available && (
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-stone-100 text-stone-500">예보 범위 밖 — 날씨 미반영</span>
          )}
          <span className="ml-auto inline-block transition-transform group-open:rotate-180 text-stone-400">▾</span>
        </summary>
        <div className="mt-3">
          <ItineraryTimeline
            itinerary={{
              travel_date: day.date,
              weather_summary: day.weather_summary ?? { rain_probability: null, wind_speed: null, weather_alert: null },
              slots: day.slots,
              early_departure: i === multi.days.length - 1 ? multi.early_departure : { recommended: false, recommended_airport_arrival_time: null, reason: "" },
              cautions: [],
            }}
            weatherLabel={`${day.day_label} 기상`}
            hideWeather={!day.forecast_available}
          />
        </div>
      </details>
    ))}
    {multi.cautions.length > 0 && (
      <details className="group mt-1">
        <summary className="cursor-pointer list-none text-xs font-semibold text-stone-400 hover:text-stone-500 select-none">
          이용 시 주의사항 <span className="inline-block transition-transform group-open:rotate-180">▾</span>
        </summary>
        <ul className="mt-2 mb-0 pl-4 space-y-0.5 text-xs text-stone-400">
          {multi.cautions.map((c, i) => (<li key={i}>{c}</li>))}
        </ul>
      </details>
    )}
  </section>
)}
```

⑤ 공항: `postAirportPlan({ departure_time: conditions.departure.time })`. 스텝 인디케이터 ④ 라벨을 `④ ${multi?.trip_label ?? "일정"}` 으로. handleSubmit 의 추천 요청 `travel_date: value.arrival.date`.
- [ ] **Step 3:** `npm run build && npx oxlint` 통과
- [ ] **Step 4: 커밋** — `feat: 플래너 다일정 렌더 (일자별 아코디언·공항 연동)`

### Task 10: 통합 검증

- [ ] 백엔드: `python -m pytest tests -q` 전체 통과 + 기존 `/api/itinerary` (빈 selected) 응답이 변경 전과 동일한지 diff
- [ ] curl 시나리오: 당일 / 오늘+2일(2박3일, 권역·중복·예보) / +7일 출발(예보 밖 caution) / 날짜 역전 422
- [ ] 프론트 육안(5173): 편명 조회 성공(오늘 실편명, 예: RS901)·미래날짜 폴백·결항 경고 3상태, N박 배지, 일자별 아코디언, 마지막 날 pre_departure, 공항 스텝 시각 연동
- [ ] `npm run build` + `npx oxlint` 최종 통과
