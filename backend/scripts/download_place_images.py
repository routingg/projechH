"""관광지 로드뷰 사진을 로컬(frontend/public)에 미리 받아둔다.

Render 무료 플랜의 hibernate/cold-start 특성 때문에 /api/image 프록시가
간헐적으로 502/503을 내는 문제를 피하기 위해, 매 요청마다 gis.jeju.go.kr에서
실시간으로 가져오는 대신 정적 파일로 미리 저장해 프론트에서 직접 서빙한다.

각 관광지의 image_urls[0](카드에 실제로 쓰이는 첫 번째 사진)만 내려받고,
원본 URL의 도메인 이후 경로를 그대로 frontend/public 아래에 저장한다.
예: https://gis.jeju.go.kr/images/roadview/DUMOAK/DUMOAK-2-011.jpg
    -> frontend/public/images/roadview/DUMOAK/DUMOAK-2-011.jpg
    -> 프론트에서 /images/roadview/DUMOAK/DUMOAK-2-011.jpg 로 접근

실행: backend/.venv/Scripts/python.exe scripts/download_place_images.py
"""
import io
import json
from pathlib import Path
from urllib.parse import urlparse

import requests
import urllib3
from PIL import Image

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
PLACES_JSON = BASE_DIR / "data" / "processed" / "jeju_places.json"
FRONTEND_PUBLIC = BASE_DIR.parent / "frontend" / "public"
MAX_WIDTH = 640
JPEG_QUALITY = 80


def download_and_resize(url: str, dest: Path) -> bool:
    if dest.exists():
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(url, timeout=15, verify=False)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        if img.width > MAX_WIDTH:
            img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)))
        img.save(dest, format="JPEG", quality=JPEG_QUALITY)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL {url}: {exc}")
        return False


def main() -> None:
    places = json.loads(PLACES_JSON.read_text(encoding="utf-8"))
    ok, fail = 0, 0
    for p in places:
        urls = p.get("image_urls") or []
        if not urls:
            continue
        url = urls[0]
        path = urlparse(url).path  # /images/roadview/DUMOAK/DUMOAK-2-011.jpg
        dest = FRONTEND_PUBLIC / path.lstrip("/")
        # 확장자를 JPEG로 통일 (원본이 png 등이어도 변환 저장)
        dest = dest.with_suffix(".jpg")
        if download_and_resize(url, dest):
            ok += 1
        else:
            fail += 1
    print(f"완료: {ok}개 저장, {fail}개 실패 (총 {ok + fail}곳)")


if __name__ == "__main__":
    main()
