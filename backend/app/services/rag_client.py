"""RAG 연동 클라이언트.

RAG(LLM 추천 설명)는 별도 팀원이 담당한다. 이 모듈은 gateway 역할만 한다.
- Step 11: 항상 mock 설명을 반환한다.
- Step 12: RAG_SERVER_URL 이 설정되어 있으면 외부 서버로 proxy 하고,
  실패 시 mock 으로 fallback 한다.
"""
import logging

import requests

from app.config import get_settings
from app.schemas.rag import RagRequest, RagResponse

logger = logging.getLogger(__name__)

# RAG 서버 미연결 시 반환하는 기본 mock (가이드 §8.2)
FALLBACK_RESPONSE = RagResponse(
    summary="현재는 RAG 서버가 연결되지 않아 기본 템플릿 설명을 제공합니다.",
    recommended_itinerary_reason="접근성 점수와 날씨 위험도를 기준으로 추천 결과를 생성했습니다.",
    risk_explanation="기상 위험도가 높은 실외 장소는 조건부 추천 또는 비추천으로 분류됩니다.",
    airport_guidance=(
        "출도 시간이 가까운 경우 공항 조기 이동과 공항공사 도면·층별 입점업체 정보, "
        "JDC 면세점 매장정보 확인을 권장합니다."
    ),
    cautions=["RAG 기반 상세 설명은 추후 연결 예정입니다."],
    source="mock",
)


def build_mock_response(payload: RagRequest) -> RagResponse:
    """근거 데이터를 반영한 데이터 인지형(mock) 설명을 생성한다."""
    places = sorted(
        payload.candidate_places,
        key=lambda p: p.mobility_feasibility_score or 0,
        reverse=True,
    )
    if not places:
        return FALLBACK_RESPONSE

    top = places[0]
    risky = [
        p
        for p in places
        if (p.weather_risk_score or 0) >= 40 or p.category == "outdoor"
    ]
    alert = (payload.weather_summary or {}).get("weather_alert")

    if risky:
        summary = (
            f"오늘은 {alert or '기상 악화'} 영향으로 실외보다 실내 관광지를 우선 추천합니다."
        )
        risk_target = risky[-1]
        risk_explanation = (
            f"{risk_target.name}은(는) 기본 접근성이 있더라도 오늘 기상 상황에서는 "
            "휠체어 이동 피로도가 높아질 수 있습니다."
        )
    else:
        summary = "오늘은 기상 위험이 낮아 계획한 일정대로 이동 가능성이 높습니다."
        risk_explanation = "현재 조건에서는 특별히 위험도가 높은 장소가 확인되지 않았습니다."

    recommended_itinerary_reason = (
        f"{top.name}은(는) 이동가능성 {top.mobility_feasibility_score}점으로 오늘 조건에서 "
        f"이동 부담이 가장 낮습니다."
    )

    ctx = payload.airport_context or {}
    arrival = ctx.get("recommended_airport_arrival_time")
    departure = ctx.get("departure_time")
    airport_guidance = (
        (f"출도 시간이 {departure}이므로 " if departure else "")
        + (f"{arrival} 전후 공항 도착을 권장합니다. " if arrival else "")
        + "공항 동선은 한국공항공사 도면·층별 입점업체 현황을 참고하고, "
        "JDC 데이터는 면세점 매장정보 확인에만 사용합니다."
    )

    return RagResponse(
        summary=summary,
        recommended_itinerary_reason=recommended_itinerary_reason,
        risk_explanation=risk_explanation,
        airport_guidance=airport_guidance,
        cautions=[
            "데이터에서 확인되지 않은 편의시설은 현장 확인이 필요합니다.",
            "본 추천은 안전을 보장하지 않으며 이동 전 최신 기상정보를 확인해야 합니다.",
        ],
        source="mock",
    )


def _call_external(
    url: str,
    payload: RagRequest,
    timeout: float,
    model_name: str,
) -> RagResponse:
    """RAG 팀원 서버로 proxy 요청을 보낸다."""
    request_body = payload.model_dump()
    request_body["model_name"] = payload.model_name or model_name
    resp = requests.post(url, json=request_body, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    data.setdefault("source", "rag-server")
    # 서버가 일부 필드를 빠뜨려도 mock 값으로 보완
    base = build_mock_response(payload).model_dump()
    base.update({k: v for k, v in data.items() if v is not None})
    base["source"] = data.get("source", "rag-server")
    return RagResponse(**base)


def get_recommendation(payload: RagRequest) -> RagResponse:
    """RAG_SERVER_URL 이 설정되어 있으면 외부 서버로 proxy 하고,
    실패(미설정·타임아웃·오류)하면 mock 설명으로 fallback 한다.
    """
    settings = get_settings()
    url = settings.rag_server_url.strip()
    if not url:
        return build_mock_response(payload)

    try:
        return _call_external(
            url,
            payload,
            settings.rag_timeout_seconds,
            settings.rag_model_name,
        )
    except Exception as exc:  # noqa: BLE001 - 어떤 실패든 mock 으로 폴백
        logger.warning("RAG 서버 호출 실패, mock 으로 fallback: %s", exc)
        return build_mock_response(payload)
