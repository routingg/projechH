from pydantic import BaseModel, Field

from app.schemas.place import Recommendation
from app.schemas.user import UserProfile


class RecommendationRequest(BaseModel):
    user_profile: UserProfile
    travel_date: str | None = Field(default=None, examples=["2026-07-10"])
    # 자연어 질의 (예: "전동휠체어인데 바다 보이는 산책로"). 없으면 기존 랭킹 그대로.
    query: str | None = Field(default=None, examples=["휠체어로 갈만한 해안 산책로"])


class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]
    # 질의가 실제 랭킹에 반영됐는지 (벡터DB 미준비·매칭 0건이면 False)
    query_applied: bool = False
