"""JDC 제주국제공항 면세점 매장정보 조회.

원칙: JDC 데이터는 면세점 매장정보 안내에만 사용한다.
공항 편의시설 위치·이용 가능 여부(휠체어 대여, 수유실, 물품보관함 등)는 제공하지 않는다.

data.go.kr B551391 실시간 API(`/jdcdutyfreeshop/brands`)를 호출하고,
키 미설정·미전파·제공기관 오류 등 실패 시 mock 데이터로 fallback 한다.
"""
import logging
import xml.etree.ElementTree as ET

import requests

from app.config import get_settings
from app.schemas.airport import JdcStore
from app.services import data_loader

logger = logging.getLogger(__name__)

DATA_LIMITATIONS = [
    "JDC 데이터는 면세점 매장정보만 제공합니다.",
    "JDC 데이터로 편의시설 위치나 이용 가능 여부를 판단하지 않습니다.",
    "공항 시설 안내는 한국공항공사 층별 입점업체 현황을 사용합니다.",
]

API_SOURCE = "JDC 제주국제공항 면세점 매장정보 API"
STORE_DATA_LIMIT = (
    "이 데이터는 JDC 면세점 매장정보 안내용입니다. "
    "휠체어 대여, 수유실, 물품보관함 위치는 제공하지 않습니다."
)


def _find_store_rows(payload) -> list[dict]:
    """응답 JSON에서 매장 레코드(POS_NM 등을 가진 dict) 리스트를 재귀 탐색한다.

    data.go.kr 실시간 API의 래핑 구조(response/body/items 등)가 서비스마다 달라
    구조에 의존하지 않고 매장 필드를 가진 dict 를 찾아낸다.
    """
    found: list[dict] = []

    def walk(node):
        if isinstance(node, dict):
            if "POS_NM" in node or "POS_NO" in node or "STOR_CD" in node:
                found.append(node)
            else:
                for v in node.values():
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload)
    return found


def _fmt_time(v) -> str | None:
    """"0600" → "06:00", "2120" → "21:20". 파싱 불가/빈값이면 None."""
    s = str(v).strip()
    if len(s) == 4 and s.isdigit():
        return f"{s[:2]}:{s[2:]}"
    return None


def _map_row(row: dict) -> JdcStore:
    loc = " ".join(
        str(row[k]).strip()
        for k in ("POS_LOC_CD", "POS_SUB_LOC_CD")
        if row.get(k)
    ).strip()
    return JdcStore(
        store_name=row.get("POS_NM") or row.get("STOR_CD") or "JDC 면세점 매장",
        location=loc or "제주국제공항 JDC면세점 구역",
        category=row.get("POS_BRAN_NM"),  # 판매품목
        # 변경 후 API 에 추가된 매장시작/종료시간(HHMM). 없으면 정보 없음 유지.
        open_time=_fmt_time(row.get("POS_START_TIME")),
        close_time=_fmt_time(row.get("POS_END_TIME")),
        phone=row.get("TEL_NO"),
        source=API_SOURCE,
        data_limit=STORE_DATA_LIMIT,
    )


STORE_FIELDS = (
    "STOR_CD", "POS_NO", "POS_NM", "POS_BRAN_NM",
    "TEL_NO", "POS_LOC_CD", "POS_SUB_LOC_CD", "POS_RMK",
    "POS_START_TIME", "POS_END_TIME",
)


def _parse_xml_rows(text: str) -> list[dict]:
    """응답이 XML일 때 매장 필드를 가진 노드를 추출한다."""
    root = ET.fromstring(text)
    rows: list[dict] = []
    for item in root.iter():
        children = {c.tag: (c.text or "").strip() for c in item}
        if any(f in children for f in STORE_FIELDS):
            rows.append(children)
    return rows


def fetch_live_stores() -> list[JdcStore]:
    """JDC 실시간 API 호출. 실패 시 예외를 던진다.

    문서상 필수 파라미터는 serviceKey 하나뿐이므로 그대로 호출하고,
    응답이 JSON/XML 어느 쪽이든 매장 레코드를 추출한다.
    """
    settings = get_settings()
    resp = requests.get(
        settings.jdc_api_url,
        params={"serviceKey": settings.jdc_api_key},
        timeout=settings.public_api_timeout_seconds,
    )
    resp.raise_for_status()

    try:
        rows = _find_store_rows(resp.json())
    except ValueError:  # JSON 아님 → XML 시도
        rows = _parse_xml_rows(resp.text)

    if not rows:
        raise ValueError("JDC 응답에서 매장 레코드를 찾지 못했습니다.")
    return [_map_row(r) for r in rows]


def _mock_stores() -> list[JdcStore]:
    return [
        JdcStore(
            store_name=s["store_name"],
            location=s["location"],
            category=s.get("category"),
            open_time=s.get("open_time"),
            close_time=s.get("close_time"),
            phone=s.get("phone"),
            source=s["source"],
            data_limit=s.get("data_limit"),
        )
        for s in data_loader.load_jdc_stores()
    ]


def get_stores() -> list[JdcStore]:
    """JDC 매장정보. 키가 있으면 실 API 호출, 실패하면 mock 으로 fallback."""
    settings = get_settings()
    if not settings.jdc_api_key.strip():
        return _mock_stores()
    try:
        return fetch_live_stores()
    except Exception as exc:  # noqa: BLE001 - 어떤 실패든 mock 으로 폴백
        logger.warning("JDC API 호출 실패, mock 으로 fallback: %s", exc)
        return _mock_stores()
