"""한국공항공사 제주공항 데이터 정규화.

raw 의 두 데이터를 처리한다.
  1) 층별 입점업체 현황 CSV(cp949) → data/processed/airport_facilities.json
  2) 제주국제공항 도면 이미지(SVG/PNG) → frontend/public/airport/ 로 복사
     + data/processed/airport_floor_maps.json

사용법:
    conda activate projecth
    cd backend
    python scripts/build_airport_data.py
"""
import csv
import json
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
RAW = BACKEND / "data" / "raw"
PROCESSED = BACKEND / "data" / "processed"
FRONT_PUBLIC = BACKEND.parent / "frontend" / "public" / "airport"

TENANT_CSV = RAW / "airport" / "층별_입점업체_현황.csv"
MAP_DIR = RAW / "airport" / "floor_maps"

# 도면 파일 → (층, 정리된 파일명, 설명)
FLOOR_IMAGES = [
    ("제주공항 1층 정보.svg", "1F", "jeju_airport_1f.svg", "제주국제공항 1층 도면"),
    ("제주공항 2층 정보.svg", "2F", "jeju_airport_2f.svg", "제주국제공항 2층 도면"),
    ("제주공항 3층 정보.svg", "3F", "jeju_airport_3f.svg", "제주국제공항 3층 도면"),
    ("제주공항 4층 정보.svg", "4F", "jeju_airport_4f.svg", "제주국제공항 4층 도면"),
    ("제주공항 2층(면세점 안내 서비스용).png", "2F", "jeju_airport_2f_dutyfree.png",
     "제주국제공항 2층 면세점 안내"),
]
SOURCE_FACILITY = "한국공항공사_제주공항 층별 입점업체 현황"
SOURCE_MAP = "한국공항공사_제주국제공항 도면 이미지 정보"


def _open_csv(path: Path):
    """UTF-8 우선, 실패 시 cp949 로 CSV 를 연다 (인코딩 무관 견고 처리)."""
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            with path.open(encoding=enc) as f:
                f.read()
            return path.open(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.open(encoding="utf-8", errors="replace")


def build_facilities() -> int:
    rows = list(csv.DictReader(_open_csv(TENANT_CSV)))
    out = []
    for i, r in enumerate(rows, 1):
        out.append({
            "facility_id": f"airport_facility_{i:03d}",
            "facility_name": (r.get("업체명") or "").strip(),
            "terminal": (r.get("청사") or "").strip(),
            "floor": (r.get("위치") or "").strip(),
            "category": (r.get("업종") or "").strip(),
            "location_hint": f"{(r.get('청사') or '').strip()} {(r.get('위치') or '').strip()}".strip(),
            "source": SOURCE_FACILITY,
        })
    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "airport_facilities.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return len(out)


def build_floor_maps() -> int:
    FRONT_PUBLIC.mkdir(parents=True, exist_ok=True)
    maps = []
    for src_name, floor, dst_name, desc in FLOOR_IMAGES:
        src = MAP_DIR / src_name
        if not src.exists():
            print(f"  ! 없음: {src_name}")
            continue
        shutil.copyfile(src, FRONT_PUBLIC / dst_name)
        maps.append({
            "floor": floor,
            "image_url": f"/airport/{dst_name}",
            "description": desc,
            "source": SOURCE_MAP,
        })
    (PROCESSED / "airport_floor_maps.json").write_text(
        json.dumps(maps, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return len(maps)


def main() -> int:
    if not TENANT_CSV.exists():
        print(f"입점업체 CSV 없음: {TENANT_CSV}")
        return 1
    n_fac = build_facilities()
    n_map = build_floor_maps()
    print(f"[성공] 입점업체 {n_fac}개 → processed/airport_facilities.json")
    print(f"[성공] 도면 {n_map}개 → frontend/public/airport/ + processed/airport_floor_maps.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
