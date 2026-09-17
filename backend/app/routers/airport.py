from fastapi import APIRouter

from app.schemas.airport import AirportPlanRequest, AirportPlanResponse
from app.services import airport_client, itinerary_service, jdc_client, weather_client

router = APIRouter(prefix="/api/airport", tags=["airport"])

BASE_CAUTIONS = [
    "공항공사 도면 이미지는 동선 참고용입니다.",
    "JDC 데이터는 면세점 매장정보 안내에만 사용됩니다.",
    "JDC 데이터로 휠체어 대여, 수유실, 물품보관함 위치를 판단하지 않습니다.",
]


@router.post("/departure-plan", response_model=AirportPlanResponse)
def departure_plan(payload: AirportPlanRequest) -> AirportPlanResponse:
    weather = (
        payload.weather_summary.model_dump()
        if payload.weather_summary
        else weather_client.get_weather()
    )
    risky = itinerary_service.is_weather_risky(weather)

    buffer_min = 150 if risky else 120
    arrival = itinerary_service.shift_time(payload.departure_time, buffer_min)

    if risky:
        reason = (
            f"출도 시간이 {payload.departure_time}이고 기상 위험(예: {weather.get('weather_alert') or '악천후'})이 "
            "있어 이동 지연 가능성을 고려해 평소보다 이른 도착을 권장합니다."
        )
    else:
        reason = f"출도 시간이 {payload.departure_time}이므로 출발 2시간 전 공항 도착을 권장합니다."

    return AirportPlanResponse(
        recommended_airport_arrival_time=arrival,
        reason=reason,
        airport_floor_maps=airport_client.get_floor_maps(),
        airport_facilities=airport_client.get_facilities(),
        jdc_stores=jdc_client.get_stores(),  # 면세점 매장정보 안내용 (편의시설 아님)
        cautions=BASE_CAUTIONS,
    )
