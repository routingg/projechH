"""제주 GIS 무장애 관광지 실데이터 수집·병합.

제주도 GIS 서버(키 불필요)의 3개 endpoint 를 병합한다.
  1) getJejuTouristList : 관광지 목록 + 접근성(장애인화장실/주차 개수, 휠체어대여/수유실/휴게실)
  2) getJejuTouristMeta : 이미지별 좌표(DMS) → 관광지 대표 좌표
  3) getJejuTouristIMG  : 로드뷰 이미지 URL

병합 결과를 우리 place 스키마로 정규화하여 data/processed/jeju_places.json 에 저장한다.

사용법:
    conda activate projecth
    cd backend
    python scripts/fetch_jeju_places.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import requests  # noqa: E402

from app.utils.geo import distance_to_airport_km, dms_to_decimal  # noqa: E402

BASE = "https://gis.jeju.go.kr/rest/JejuRoadViewTourList"
RAW_DIR = BACKEND / "data" / "raw"
PROCESSED_DIR = BACKEND / "data" / "processed"
MAX_IMAGES = 5  # 관광지당 페이지에 노출할 이미지 수

# 이름으로 실내 여부를 가볍게 추정 (없는 값은 넣지 않고 None 유지가 원칙이나,
# 실내/실외는 날씨 점수에 중요하여 명확한 실내 유형만 True 로 표시)
INDOOR_KEYWORDS = ("박물관", "미술관", "전시", "기념관", "과학관", "아쿠아", "수족관",
                   "도서관", "갤러리", "천문", "아트")


def _get(op: str) -> list[dict]:
    """GIS endpoint 호출. 서버 인증서 검증 이슈로 verify=False (공개 데이터)."""
    last = None
    for _ in range(5):
        try:
            r = requests.get(f"{BASE}/{op}", timeout=60, verify=False)
            r.raise_for_status()
            return r.json().get("resultSummary", [])
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError(f"{op} 호출 실패: {last}")


def _is_indoor(name: str) -> bool | None:
    return True if any(k in name for k in INDOOR_KEYWORDS) else None


def _coords_by_place(meta: list[dict]) -> dict[str, tuple[float, float]]:
    """관광지(touristEn)별 이미지 좌표 평균."""
    acc: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for m in meta:
        lat = dms_to_decimal(m.get("lat", "")) if m.get("lat") else None
        lon = dms_to_decimal(m.get("lon", "")) if m.get("lon") else None
        if lat is not None and lon is not None:
            acc[m["touristEn"]].append((lat, lon))
    return {
        en: (round(sum(a for a, _ in pts) / len(pts), 6),
             round(sum(o for _, o in pts) / len(pts), 6))
        for en, pts in acc.items()
    }


def _images_by_place(img: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for i in img:
        p = i.get("touristImgPath")
        if p and len(out[i["touristEn"]]) < MAX_IMAGES:
            out[i["touristEn"]].append(p)
    return out


def _to_bool(v) -> bool | None:
    if v is None:
        return None
    s = str(v).strip().upper()
    if s in ("Y", "YES", "T", "TRUE"):
        return True
    if s in ("N", "NO", "F", "FALSE"):
        return False
    return None


def _count_positive(v) -> bool | None:
    """장애인 화장실/주차 '개수' → 1개 이상이면 True, 0이면 False, 파싱 불가면 None."""
    try:
        return int(v) > 0
    except (TypeError, ValueError):
        return None


def _as_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _region(addr: str | None) -> str | None:
    if not addr:
        return None
    if "서귀포" in addr:
        return "서귀포시"
    if "제주시" in addr:
        return "제주시"
    return None


def build_places() -> list[dict]:
    lst = _get("getJejuTouristList")
    meta = _get("getJejuTouristMeta")
    img = _get("getJejuTouristIMG")

    gis_dir = RAW_DIR / "jeju_gis_api"
    gis_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (("list", lst), ("meta", meta), ("img", img)):
        (gis_dir / f"jeju_tour_{name}_raw.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

    coords = _coords_by_place(meta)
    images = _images_by_place(img)

    places: list[dict] = []
    for r in lst:
        en = r["touristEn"]
        latlon = coords.get(en)
        lat, lon = (latlon if latlon else (None, None))
        tel = r.get("touristTel")
        places.append({
            "id": f"jeju_{r['seq']}",
            "name": r["touristNm"],
            "name_en": en,
            "address": r.get("touristAddr"),
            "phone": tel if tel and tel != "-" else None,
            "lat": lat,
            "lon": lon,
            "category": "indoor" if _is_indoor(r["touristNm"]) else "outdoor",
            "is_indoor": _is_indoor(r["touristNm"]),
            "has_accessible_toilet": _count_positive(r.get("toristDtoil")),
            "has_accessible_parking": _count_positive(r.get("toruistDpar")),
            "has_wheelchair_rental": _to_bool(r.get("touristLent")),
            "has_nursing_room": _to_bool(r.get("touristNursing")),
            "has_accessible_rest": _to_bool(r.get("touristRest")),
            # 점수 세분화를 위한 원시 개수 + 지역
            "toilet_count": _as_int(r.get("toristDtoil")),
            "parking_count": _as_int(r.get("toruistDpar")),
            "region": _region(r.get("touristAddr")),
            # GIS 데이터에 없는 항목은 정보 없음(None) 유지
            "has_ramp": None,
            "surface_condition": None,
            "slope_level": None,
            "near_low_floor_bus": None,
            "distance_to_airport_km": (
                distance_to_airport_km(lat, lon) if lat is not None else None
            ),
            "image_urls": images.get(en, []),
            "source": "제주특별자치도 사회적약자 시설데이터 로드뷰 (제주 GIS)",
        })
    return places


def main() -> int:
    # verify=False 경고 억제
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print("제주 GIS 관광지 3종 endpoint 수집 중…")
    places = build_places()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "jeju_places.json"
    out.write_text(json.dumps(places, ensure_ascii=False, indent=2), encoding="utf-8")

    with_coords = sum(1 for p in places if p["lat"] is not None)
    with_img = sum(1 for p in places if p["image_urls"])
    print(f"[성공] 관광지 {len(places)}곳 저장 → {out.relative_to(BACKEND)}")
    print(f"  좌표 보유 {with_coords}곳 · 이미지 보유 {with_img}곳")
    for p in places[:3]:
        print(f"  - {p['name']} | 화장실={p['has_accessible_toilet']} 주차={p['has_accessible_parking']} "
              f"대여={p['has_wheelchair_rental']} 이미지={len(p['image_urls'])}장")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
