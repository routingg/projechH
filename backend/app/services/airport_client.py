"""한국공항공사 공항 데이터 조회.

- 제주국제공항 도면 이미지 정보 (SVG/PNG)
- 제주공항 층별 입점업체 현황 (CSV)

data/processed 에 정규화된 실데이터(build_airport_data.py 산출물)가 있으면 우선 사용하고,
없으면 data/mock 으로 fallback 한다.
"""
import json

from app.config import BASE_DIR
from app.schemas.airport import AirportFacility, FloorMap
from app.services import data_loader

PROCESSED_DIR = BASE_DIR / "data" / "processed"


def _load_processed(name: str) -> list[dict] | None:
    path = PROCESSED_DIR / name
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data:
            return data
    return None


def get_floor_maps() -> list[FloorMap]:
    data = _load_processed("airport_floor_maps.json") or data_loader.load_airport_floor_maps()
    return [FloorMap(**m) for m in data]


def get_facilities() -> list[AirportFacility]:
    data = _load_processed("airport_facilities.json") or data_loader.load_airport_facilities()
    return [
        AirportFacility(
            facility_name=f["facility_name"],
            terminal=f["terminal"],
            floor=f["floor"],
            category=f["category"],
            location_hint=f.get("location_hint"),
            source=f["source"],
        )
        for f in data
    ]
