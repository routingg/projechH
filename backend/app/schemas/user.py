from typing import Literal

from pydantic import BaseModel, Field

WheelchairType = Literal["manual", "electric", "unknown"]
WeatherSensitivity = Literal["low", "normal", "high"]


class UserProfile(BaseModel):
    start_location: str | None = Field(default=None, examples=["제주시 연동"])
    wheelchair_type: WheelchairType = "manual"
    has_companion: bool = False
    preferred_type: list[str] = Field(default_factory=list, examples=[["indoor", "nature"]])
    departure_time: str | None = Field(default=None, examples=["18:30"])
    weather_sensitivity: WeatherSensitivity = "normal"
    # 사용자 현재 위치(GPS). 있으면 교통 근접도를 이 위치 기준으로 계산.
    user_lat: float | None = None
    user_lon: float | None = None
