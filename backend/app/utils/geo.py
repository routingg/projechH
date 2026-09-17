"""좌표 유틸리티."""
from math import asin, cos, radians, sin, sqrt

# 제주국제공항 좌표
JEJU_AIRPORT_LAT = 33.5113
JEJU_AIRPORT_LON = 126.4929


def dms_to_decimal(dms: str) -> float | None:
    """"126; 37; 9.0300" (도;분;초) 형식을 십진 도(decimal degree)로 변환."""
    try:
        d, m, s = (float(x.strip()) for x in dms.split(";"))
    except (ValueError, AttributeError):
        return None
    return round(d + m / 60 + s / 3600, 6)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 사이 거리(km)."""
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return round(2 * r * asin(sqrt(a)), 2)


def distance_to_airport_km(lat: float, lon: float) -> float:
    return haversine_km(lat, lon, JEJU_AIRPORT_LAT, JEJU_AIRPORT_LON)
