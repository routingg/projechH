from pydantic import BaseModel, Field

from app.schemas.itinerary import WeatherSummary


class AirportPlanRequest(BaseModel):
    departure_time: str = Field(examples=["18:30"])
    wheelchair_type: str = "manual"
    has_companion: bool = False
    weather_summary: WeatherSummary | None = None


class FloorMap(BaseModel):
    floor: str
    image_url: str
    description: str
    source: str


class AirportFacility(BaseModel):
    facility_name: str
    terminal: str
    floor: str
    category: str
    location_hint: str | None = None
    source: str


class JdcStore(BaseModel):
    store_name: str
    location: str
    category: str | None = None
    open_time: str | None = None
    close_time: str | None = None
    phone: str | None = None
    source: str
    data_limit: str | None = None


class AirportPlanResponse(BaseModel):
    recommended_airport_arrival_time: str | None = None
    reason: str
    airport_floor_maps: list[FloorMap]
    airport_facilities: list[AirportFacility]
    jdc_stores: list[JdcStore] = []
    cautions: list[str]
