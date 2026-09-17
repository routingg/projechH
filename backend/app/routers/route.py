"""카카오 모빌리티 길찾기 프록시.

일정 코스(경유지 순서)의 실도로 경로 polyline 과 총 거리·시간을 반환한다.
REST 키가 없거나 실패하면 입력 지점을 그대로 이어붙인 직선 경로로 fallback 한다.
"""
import logging

import requests
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["route"])


class Point(BaseModel):
    lat: float
    lng: float


class RouteRequest(BaseModel):
    points: list[Point]  # 방문 순서대로 (마지막에 공항 포함 가능)


class RouteResponse(BaseModel):
    path: list[Point]        # 경로 polyline 좌표
    distance_m: int | None = None
    duration_s: int | None = None
    source: str              # "kakao" | "straight"


def _straight(points: list[Point]) -> RouteResponse:
    return RouteResponse(path=points, source="straight")


@router.post("/route", response_model=RouteResponse)
def route(payload: RouteRequest) -> RouteResponse:
    pts = payload.points
    if len(pts) < 2:
        return _straight(pts)

    s = get_settings()
    if not s.kakao_rest_key.strip():
        return _straight(pts)

    try:
        body = {
            "origin": {"x": pts[0].lng, "y": pts[0].lat},
            "destination": {"x": pts[-1].lng, "y": pts[-1].lat},
            "waypoints": [{"x": p.lng, "y": p.lat} for p in pts[1:-1]],
            "priority": "RECOMMEND",
        }
        r = requests.post(
            s.kakao_directions_url,
            json=body,
            headers={"Authorization": f"KakaoAK {s.kakao_rest_key}"},
            timeout=s.public_api_timeout_seconds,
        )
        r.raise_for_status()
        route0 = r.json()["routes"][0]
        if route0.get("result_code") not in (0, None):
            raise ValueError(route0.get("result_msg", "길찾기 실패"))

        path: list[Point] = []
        for sec in route0["sections"]:
            for road in sec["roads"]:
                v = road["vertexes"]
                for i in range(0, len(v), 2):
                    path.append(Point(lat=v[i + 1], lng=v[i]))
        summary = route0.get("summary", {})
        return RouteResponse(
            path=path or pts,
            distance_m=summary.get("distance"),
            duration_s=summary.get("duration"),
            source="kakao",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("카카오 길찾기 실패, 직선으로 fallback: %s", exc)
        return _straight(pts)
