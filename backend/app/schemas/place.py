from typing import Literal

from pydantic import BaseModel

RecommendationLevel = Literal["recommended", "conditional", "not_recommended"]


class PlaceFacts(BaseModel):
    """데이터에서 확인된 사실. 확인되지 않은 값은 None(정보 없음)으로 유지한다."""

    has_accessible_parking: bool | None = None
    has_accessible_toilet: bool | None = None
    has_wheelchair_rental: bool | None = None
    is_indoor: bool | None = None


class Recommendation(BaseModel):
    place_id: str
    name: str
    category: str
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    image_urls: list[str] = []
    accessibility_score: int
    weather_risk_score: int
    transport_score: int
    airport_burden_score: int
    mobility_feasibility_score: int
    recommendation_level: RecommendationLevel
    warnings: list[str] = []
    facts: PlaceFacts
    # 자연어 질의 관련도(0~100, 질의 없거나 미매칭이면 None)와 근거 문서 스니펫
    relevance_score: int | None = None
    match_reason: list[str] = []
    # 제주데이터허브 무장애여행정보 원문 스니펫 (없는 장소는 빈 목록)
    barrier_free_info: list[str] = []
