"""JDC 면세점 매장정보 실 API 원본 수집.

사용법:
    conda activate projecth
    cd backend
    python scripts/fetch_jdc.py

- backend/.env 의 JDC_API_KEY / JDC_API_URL 을 사용한다.
- 원본 응답을 data/raw/ 에, 정규화 결과를 data/processed/jdc_stores.json 에 저장한다.
- 반복 재시도가 필요하면 scripts/poll_jdc.py 를 사용한다.
"""
import json
import sys
from pathlib import Path

# backend 를 import 경로에 추가
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import requests  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.services import jdc_client  # noqa: E402

RAW_DIR = BACKEND / "data" / "raw"
PROCESSED_DIR = BACKEND / "data" / "processed"


def fetch_and_save() -> tuple[bool, str]:
    """실 API 를 1회 호출해 저장한다. (성공여부, 메시지) 반환."""
    settings = get_settings()
    if not settings.jdc_api_key.strip():
        return False, "JDC_API_KEY 미설정 (backend/.env 확인)"

    try:
        resp = requests.get(
            settings.jdc_api_url,
            params={"serviceKey": settings.jdc_api_key},
            timeout=settings.public_api_timeout_seconds,
        )
        resp.raise_for_status()
        stores = jdc_client.fetch_live_stores()
    except Exception as exc:  # noqa: BLE001
        return False, f"실패: {exc}"

    jdc_raw = RAW_DIR / "jdc_dutyfree"
    jdc_raw.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    (jdc_raw / "jdc_brands_raw.txt").write_text(resp.text, encoding="utf-8")
    (PROCESSED_DIR / "jdc_stores.json").write_text(
        json.dumps([s.model_dump() for s in stores], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    preview = ", ".join(s.store_name for s in stores[:5])
    return True, f"매장 {len(stores)}건 저장 → data/processed/jdc_stores.json ({preview})"


def main() -> int:
    settings = get_settings()
    print(f"호출: {settings.jdc_api_url}")
    ok, msg = fetch_and_save()
    if ok:
        print(f"[성공] {msg}")
        return 0
    print(f"[{msg}]")
    print("키가 방금 발급되었다면 전파(활성화)까지 최대 1시간~1일 걸릴 수 있습니다. 나중에 다시 시도하세요.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
