"""애플리케이션 설정. .env 에서 환경변수를 읽는다."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
MOCK_DIR = BASE_DIR / "data" / "mock"


class Settings(BaseSettings):
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"

    # RAG 연동 (별도 팀원 서버). 비어 있으면 mock fallback.
    rag_server_url: str = ""
    rag_timeout_seconds: float = 5.0
    rag_model_name: str = "kakaocorp/kanana-1.5-8b-instruct-2505"
    rag_embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    rag_vector_store_dir: str = "../vector_store"

    # 공공데이터 API 키 (Step 14 실연동)
    kma_api_key: str = ""
    jdc_api_key: str = ""
    data_go_kr_api_key: str = ""

    # JDC 면세점 매장정보 API (data.go.kr B551391). serviceKey 는 Decoding 키.
    # 변경 후 URL(복수형 base) + /brand 오퍼레이션. 129개 매장, 운영시간 포함.
    jdc_api_url: str = "https://apis.data.go.kr/B551391/jdcdutyfreeshops/brand"
    public_api_timeout_seconds: float = 10.0

    # 기상청(1360000) — 단기예보 + 기상특보. serviceKey 는 위 인증키 공용.
    kma_forecast_url: str = (
        "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    )
    kma_alert_url: str = (
        "https://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrWrnList"
    )
    kma_grid_nx: int = 52   # 제주시 격자 X
    kma_grid_ny: int = 38   # 제주시 격자 Y
    kma_stn_id: int = 184   # 제주 특보 지점코드

    # 카카오 모빌리티 길찾기 (REST 키). 없으면 프론트가 직선 동선으로 표시.
    kakao_rest_key: str = ""
    kakao_directions_url: str = (
        "https://apis-navi.kakaomobility.com/v1/waypoints/directions"
    )

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
