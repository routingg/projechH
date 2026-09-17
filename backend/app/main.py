"""WheelTrip Jeju (ProjectH) FastAPI 진입점."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    airport,
    itinerary,
    jdc,
    media,
    rag_gateway,
    recommendations,
    route,
)

settings = get_settings()

app = FastAPI(
    title="WheelTrip Jeju API",
    description="휠체어 이용자의 당일 이동가능성 예측 및 공항 출도 동선 안내 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
def root():
    return {"service": "WheelTrip Jeju API", "version": app.version, "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "env": settings.app_env}


app.include_router(recommendations.router)
app.include_router(itinerary.router)
app.include_router(airport.router)
app.include_router(jdc.router)
app.include_router(rag_gateway.router)
app.include_router(media.router)
app.include_router(route.router)
