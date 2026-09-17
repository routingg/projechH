"""날씨 기반 일정 재구성 서비스.

- 이동가능성 상위 장소로 오전/오후 일정을 구성한다.
- 기상 위험이 높으면 실외 장소를 실내 장소로 대체한다.
- 출도 시간과 기상 상황을 고려해 공항 조기 이동을 권장한다.
"""
from app.schemas.itinerary import (
    EarlyDeparture,
    ItineraryResponse,
    ItinerarySlot,
    WeatherSummary,
)
from app.schemas.user import UserProfile
from app.services import recommendation_service, weather_client
from app.utils import constants as C


def shift_time(hhmm: str, minus_minutes: int) -> str | None:
    """"HH:MM" 에서 분을 빼서 "HH:MM" 으로 반환."""
    try:
        h, m = (int(x) for x in hhmm.split(":"))
    except (ValueError, AttributeError):
        return None
    total = h * 60 + m - minus_minutes
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def is_weather_risky(weather: dict) -> bool:
    rain = weather.get("rain_probability") or 0
    wind = weather.get("wind_speed") or 0
    alert = weather.get("weather_alert")
    return bool(alert) or rain >= C.RAIN_HIGH or wind >= C.WIND_HIGH


# 방문 슬롯 시간 힌트: 오전 최대 2곳, 이후는 전부 오후 배치
MORNING_HINTS = ["09:30", "11:00"]
AFTERNOON_HINTS = ["14:00", "16:00", "17:00", "18:00"]


def _pick_visits(
    recs: list, risky: bool, selected_place_ids: list[str] | None
) -> tuple[list[tuple], list[str]]:
    """방문 리스트를 만든다: (rec, is_user_selected) 목록 + 주의사항.

    사용자가 담은 장소는 등급과 무관하게 순서 그대로 반드시 포함하고,
    부족분(최소 2곳)은 기존 자동 선택 로직(날씨·지역 다양성)으로 채운다.
    """
    cautions: list[str] = []
    rec_by_id = {r.place_id: r for r in recs}

    selected: list = []
    missing: list[str] = []
    for pid in dict.fromkeys(selected_place_ids or []):  # 중복 제거, 순서 유지
        rec = rec_by_id.get(pid)
        if rec is not None:
            selected.append(rec)
        else:
            missing.append(pid)
    if missing:
        cautions.append(f"찾을 수 없어 제외한 선택 장소: {', '.join(missing)}")
    if len(selected) > 4:
        cautions.append("선택한 장소가 많아 하루 일정으로는 이동 부담이 클 수 있습니다.")

    selected_ids = {r.place_id for r in selected}
    visitable = [
        r for r in recs
        if r.recommendation_level != "not_recommended" and r.place_id not in selected_ids
    ]
    indoor = [r for r in visitable if r.category == "indoor"]

    # 날씨가 나쁘면 실내 우선, 아니면 이동가능성 상위 순
    ordered = (indoor + [r for r in visitable if r not in indoor]) if risky else visitable

    # 다양성: 서로 다른 지역에서 뽑는다 (같은 박물관 군집 방지)
    def _region(rec) -> str | None:
        a = rec.address or ""
        return "서귀포시" if "서귀포" in a else "제주시" if "제주시" in a else None

    autos: list = []
    need = max(0, 2 - len(selected))
    for _ in range(need):
        base = (selected + autos)[-1] if (selected or autos) else None
        pick = None
        if base is not None:
            pick = next((r for r in ordered if _region(r) != _region(base)), None)
        if pick is None and ordered:
            pick = ordered[0]
        if pick is None:
            break
        autos.append(pick)
        ordered = [r for r in ordered if r.place_id != pick.place_id]

    visits = [(r, True) for r in selected] + [(r, False) for r in autos]
    return visits, cautions


def build_itinerary(
    user_profile: UserProfile,
    travel_date: str | None = None,
    selected_place_ids: list[str] | None = None,
) -> ItineraryResponse:
    weather = weather_client.get_weather()
    risky = is_weather_risky(weather)

    recs = recommendation_service.build_recommendations(user_profile, travel_date)
    visits, extra_cautions = _pick_visits(recs, risky, selected_place_ids)

    slots: list[ItinerarySlot] = []

    def make_slot(period: str, time_hint: str, title: str, rec, user_selected: bool) -> None:
        if rec is None:
            slots.append(
                ItinerarySlot(
                    period=period,
                    time_hint=time_hint,
                    title=title,
                    reason="오늘 조건에 맞는 추천 장소가 부족합니다. 실내 휴식을 권장합니다.",
                )
            )
            return
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
        slots.append(
            ItinerarySlot(
                period=period,
                time_hint=time_hint,
                title=title,
                place_id=rec.place_id,
                place_name=rec.name,
                category=rec.category,
                lat=rec.lat,
                lon=rec.lon,
                reason=reason,
                is_alternative=is_alt,
                is_user_selected=user_selected,
            )
        )

    # 오전 최대 2곳 → 점심 → 나머지는 오후
    n = len(visits)
    morning_count = min(len(MORNING_HINTS), (n + 1) // 2) if n else 1
    morning = visits[:morning_count] or [(None, False)]
    afternoon = visits[morning_count:] or [(None, False)]

    for i, (rec, sel) in enumerate(morning):
        title = "오전 관광" if len(morning) == 1 else f"오전 관광 {i + 1}"
        make_slot("morning", MORNING_HINTS[min(i, len(MORNING_HINTS) - 1)], title, rec, sel)
    slots.append(
        ItinerarySlot(
            period="lunch",
            time_hint="12:30",
            title="점심 식사",
            reason="접근 가능한 식당에서 충분히 휴식한 뒤 오후 일정을 시작하세요.",
        )
    )
    for i, (rec, sel) in enumerate(afternoon):
        title = "오후 관광" if len(afternoon) == 1 else f"오후 관광 {i + 1}"
        make_slot("afternoon", AFTERNOON_HINTS[min(i, len(AFTERNOON_HINTS) - 1)], title, rec, sel)

    # 공항 조기 이동 권장
    departure = user_profile.departure_time
    buffer_min = 150 if risky else 120  # 기상 악화 시 30분 추가 버퍼
    arrival = shift_time(departure, buffer_min) if departure else None
    early_reason = (
        "기상 악화로 이동 지연 가능성이 있어 평소보다 일찍 공항 도착을 권장합니다."
        if risky
        else "여유 있는 출도를 위해 출발 2시간 전 공항 도착을 권장합니다."
    )
    slots.append(
        ItinerarySlot(
            period="pre_departure",
            time_hint=arrival or "-",
            title="공항 이동 및 출도 준비",
            reason=early_reason,
        )
    )

    cautions = extra_cautions + [
        "일정은 참고용이며 현장 상황과 최신 기상정보를 확인하세요.",
        "확인되지 않은 편의시설은 방문 전 개별 확인이 필요합니다.",
    ]

    return ItineraryResponse(
        travel_date=travel_date,
        weather_summary=WeatherSummary(
            rain_probability=weather.get("rain_probability"),
            wind_speed=weather.get("wind_speed"),
            weather_alert=weather.get("weather_alert"),
        ),
        slots=slots,
        early_departure=EarlyDeparture(
            recommended=risky,
            recommended_airport_arrival_time=arrival,
            reason=early_reason,
        ),
        cautions=cautions,
    )
