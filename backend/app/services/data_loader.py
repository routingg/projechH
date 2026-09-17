"""mock JSON 데이터 로더.

MVP는 DB 대신 data/mock/*.json 을 읽어 메모리에 캐시한다.
실 공공데이터 연동 단계에서는 각 *_client.py 가 이 로더를 fallback 으로 사용한다.
"""
import json
from functools import lru_cache
from typing import Any

from app.config import BASE_DIR, MOCK_DIR

PROCESSED_DIR = BASE_DIR / "data" / "processed"


def _load_json(filename: str) -> Any:
    path = MOCK_DIR / filename
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_overlay() -> dict:
    """무장애 접근성 오버레이(scripts/enrich_places_accessibility.py 산출물).
    없으면 빈 dict — 기존 장소 목록 그대로 동작한다."""
    path = PROCESSED_DIR / "place_accessibility.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _merge_accessibility(places: list[dict]) -> list[dict]:
    overlay = _load_overlay()
    if not overlay:
        return places
    enrich = overlay.get("enrich", {})
    for place in places:
        extra = enrich.get(place["id"])
        if not extra:
            continue
        for key, value in extra.items():
            # 기존 GIS 값 우선 — null 인 필드만 채운다 (barrier_free_info 는 신규 필드)
            if place.get(key) is None or key == "barrier_free_info":
                place[key] = value
    return places + overlay.get("new_places", [])


@lru_cache
def load_places() -> list[dict]:
    """관광지 목록. 실데이터(data/processed/jeju_places.json)가 있으면 우선 사용,
    없으면 mock 으로 fallback. 무장애 오버레이가 있으면 병합한다."""
    real = PROCESSED_DIR / "jeju_places.json"
    if real.exists():
        with real.open(encoding="utf-8") as f:
            data = json.load(f)
        if data:
            return _merge_accessibility(data)
    return _load_json("mock_places.json")


@lru_cache
def load_rag_place_map() -> dict[str, str]:
    """RAG 문서 place_id → 서비스 place id 매핑 (자연어 추천 관련도 결합용)."""
    return _load_overlay().get("rag_place_map", {})


@lru_cache
def load_weather() -> dict:
    return _load_json("mock_weather.json")


@lru_cache
def load_airport_floor_maps() -> list[dict]:
    return _load_json("mock_airport_floor_maps.json")


@lru_cache
def load_airport_facilities() -> list[dict]:
    return _load_json("mock_airport_facilities.json")


@lru_cache
def load_jdc_stores() -> list[dict]:
    return _load_json("mock_jdc_stores.json")


def get_place_by_id(place_id: str) -> dict | None:
    return next((p for p in load_places() if p["id"] == place_id), None)
