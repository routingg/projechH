from pydantic import BaseModel
from fastapi import APIRouter

from app.schemas.airport import JdcStore
from app.services import jdc_client

router = APIRouter(prefix="/api/jdc", tags=["jdc"])


class JdcStoreResponse(BaseModel):
    stores: list[JdcStore]
    data_limitations: list[str]


@router.get("/stores", response_model=JdcStoreResponse)
def stores() -> JdcStoreResponse:
    return JdcStoreResponse(
        stores=jdc_client.get_stores(),
        data_limitations=jdc_client.DATA_LIMITATIONS,
    )
