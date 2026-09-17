"""이미지 프록시.

제주 GIS 로드뷰 이미지는 인증서 체인 문제로 브라우저가 직접 로드하지 못할 수 있어
백엔드가 대신 받아(verify=False) 전달한다. SSRF 방지를 위해 허용 호스트를 제한한다.
"""
import io
from urllib.parse import urlparse

import requests
import urllib3
from fastapi import APIRouter, HTTPException, Query, Response
from PIL import Image

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

router = APIRouter(prefix="/api", tags=["media"])

ALLOWED_HOSTS = {"gis.jeju.go.kr"}


@router.get("/image")
def proxy_image(
    url: str = Query(..., description="원본 이미지 URL"),
    w: int = Query(640, ge=64, le=1600, description="리사이즈 최대 너비(px)"),
) -> Response:
    """제주 GIS 로드뷰 이미지를 받아 리사이즈해 전달한다(원본 6720px → 대역폭 절감)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
        raise HTTPException(status_code=400, detail="허용되지 않은 이미지 주소입니다.")
    try:
        r = requests.get(url, timeout=15, verify=False)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        if img.width > w:
            img = img.resize((w, round(img.height * w / img.width)))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="이미지를 불러오지 못했습니다.")
    return Response(
        content=buf.getvalue(),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
