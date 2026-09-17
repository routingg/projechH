from fastapi import APIRouter

from app.schemas.itinerary import ItineraryRequest, ItineraryResponse
from app.services import itinerary_service

router = APIRouter(prefix="/api", tags=["itinerary"])


@router.post("/itinerary", response_model=ItineraryResponse)
def build(payload: ItineraryRequest) -> ItineraryResponse:
    return itinerary_service.build_itinerary(
        payload.user_profile, payload.travel_date, payload.selected_place_ids
    )
