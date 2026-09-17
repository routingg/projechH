"""관광지 추천 서비스.

관광지 + 날씨를 점수화하여 이동가능성 순으로 정렬한 추천 목록을 만든다.
자연어 질의(query)가 있으면 무장애 문서 검색 관련도를 랭킹에 결합한다.
"""
import logging

from app.schemas.place import PlaceFacts, Recommendation
from app.schemas.user import UserProfile
from app.services import data_loader, scoring_service, weather_client
from app.utils import constants as C

logger = logging.getLogger(__name__)

MATCH_REASON_LEN = 120

GENERIC_CAUTION = "본 추천은 참고 정보이며 휠체어 접근 가능성이나 안전을 보장하지 않습니다."


def _build_warnings(place: dict, level: str) -> list[str]:
    warnings = scoring_service.accessibility_unknowns(place)
    if level == "not_recommended":
        warnings.append("오늘 조건에서는 이동 부담이 커 비추천입니다.")
    elif level == "conditional":
        warnings.append("조건부 추천입니다. 동반자 동행과 현장 확인을 권장합니다.")
    warnings.append(GENERIC_CAUTION)
    return warnings


# 등급을 상대(백분위) 기준으로 부여해 다양성을 확보한다.
# 실데이터 특성상 절대 점수가 낮게 뭉쳐 절대 임계값(75/50)만으로는 대부분 비추천이 되므로,
# 이동가능성 순위 상위 REC_PCT 는 추천, 다음 COND_PCT 까지는 조건부로 분류한다.
# (실제 점수는 카드에 그대로 노출되어 정직성 유지)
REC_PCT = 0.15
COND_PCT = 0.55


def _relative_level(mobility: int, rec_cut: int, cond_cut: int) -> str:
    if mobility >= rec_cut:
        return "recommended"
    if mobility >= cond_cut:
        return "conditional"
    return "not_recommended"


def _query_relevance(query: str) -> dict[str, dict]:
    """자연어 질의 → 장소 id 별 관련도(0~100)와 근거 문서 텍스트.

    벡터DB 미준비·오버레이 부재 등 어떤 실패든 빈 dict 를 반환해
    기존 이동가능성 랭킹으로 동작한다 (질의 무시).
    """
    try:
        from app.services import retriever

        docs = retriever.retrieve_documents(query, top_k=C.QUERY_TOP_K_DOCS)
    except Exception as exc:  # noqa: BLE001 - FAISS/모델 미준비 시 질의 무시
        logger.warning("질의 검색 실패, 기본 랭킹으로 진행: %s", exc)
        return {}

    rag_map = data_loader.load_rag_place_map()
    by_place: dict[str, dict] = {}
    for doc in docs:  # retrieve_documents 는 유사도 내림차순
        our_id = rag_map.get(str(doc.get("place_id") or ""))
        if not our_id:
            continue
        entry = by_place.setdefault(our_id, {"scores": [], "texts": []})
        entry["scores"].append(doc["score"])
        text = (doc.get("text") or "").strip()
        if text:
            entry["texts"].append(text)
    if not by_place:
        return {}

    # 장소 관련도 = 최고 문서 유사도 + 문서 수 보너스(최대 +0.2) → min-max 정규화
    raw = {
        pid: max(e["scores"]) + 0.05 * min(len(e["scores"]) - 1, 4)
        for pid, e in by_place.items()
    }
    lo, hi = min(raw.values()), max(raw.values())
    for pid, entry in by_place.items():
        norm = 1.0 if hi == lo else (raw[pid] - lo) / (hi - lo)
        entry["relevance"] = round(norm * 100)
    return by_place


def build_recommendations(
    user_profile: UserProfile,
    travel_date: str | None = None,
    query: str | None = None,
) -> list[Recommendation]:
    weather = weather_client.get_weather()
    profile_dict = user_profile.model_dump()

    relevance = _query_relevance(query.strip()) if query and query.strip() else {}

    # 1) 모든 장소 점수화
    scored: list[tuple[dict, dict]] = []
    for place in data_loader.load_places():
        scores = scoring_service.calculate_mobility_feasibility_score(
            place, weather, profile_dict
        )
        scored.append((place, scores))

    # 2) 백분위 컷오프는 항상 이동가능성 기준으로 계산 (동점은 같은 등급으로 묶임)
    #    — 질의 관련도는 정렬에만 반영하고 등급(안전/이동가능성 의미)은 바꾸지 않는다.
    n = len(scored)
    mob_desc = sorted((s["mobility_feasibility_score"] for _, s in scored), reverse=True)
    rec_cut = mob_desc[min(n - 1, int(n * REC_PCT))] if n else 0
    cond_cut = mob_desc[min(n - 1, int(n * COND_PCT))] if n else 0

    # 3) 정렬: 질의가 있으면 이동가능성·관련도 결합 점수, 없으면 이동가능성 순
    if relevance:
        alpha = C.QUERY_RELEVANCE_WEIGHT
        scored.sort(
            key=lambda x: (1 - alpha) * x[1]["mobility_feasibility_score"]
            + alpha * relevance.get(x[0]["id"], {}).get("relevance", 0),
            reverse=True,
        )
    else:
        scored.sort(key=lambda x: x[1]["mobility_feasibility_score"], reverse=True)

    # 4) 상대 등급 부여 + 결과 구성
    results: list[Recommendation] = []
    for place, scores in scored:
        level = _relative_level(scores["mobility_feasibility_score"], rec_cut, cond_cut)
        scores = {**scores, "recommendation_level": level}
        rel_entry = relevance.get(place["id"])
        match_reason = []
        if rel_entry:
            match_reason = [
                t[:MATCH_REASON_LEN] + ("…" if len(t) > MATCH_REASON_LEN else "")
                for t in rel_entry["texts"][:2]
            ]
        results.append(
            Recommendation(
                place_id=place["id"],
                name=place["name"],
                category=place["category"],
                address=place.get("address"),
                lat=place.get("lat"),
                lon=place.get("lon"),
                image_urls=place.get("image_urls", []),
                warnings=_build_warnings(place, level),
                facts=PlaceFacts(
                    has_accessible_parking=place.get("has_accessible_parking"),
                    has_accessible_toilet=place.get("has_accessible_toilet"),
                    has_wheelchair_rental=place.get("has_wheelchair_rental"),
                    is_indoor=place.get("is_indoor"),
                ),
                relevance_score=rel_entry["relevance"] if rel_entry else None,
                match_reason=match_reason,
                barrier_free_info=place.get("barrier_free_info") or [],
                **scores,
            )
        )
    return results
