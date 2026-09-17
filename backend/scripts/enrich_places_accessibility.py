"""제주데이터허브 무장애여행정보 기반 관광지 접근성 보강.

vector_store/metadata.jsonl(RAG 벡터DB 메타데이터)을 장소 단위로 집계해
  1) 기존 jeju_places 와 매칭되는 장소 → 비어 있는 접근성 필드 채움(enrich)
  2) 매칭되지 않는 장소 → 신규 장소로 추가(new_places, id="bf_<rag_place_id>")
를 data/processed/place_accessibility.json 오버레이로 저장한다.
data_loader.load_places() 가 이 오버레이를 병합하며, 파일이 없으면 기존 107곳으로 동작한다.
(jeju_places.json 을 직접 수정하지 않으므로 fetch_jeju_places.py 재실행과 무관하게 유지된다.)

원칙 — 데이터에 명시된 사실만 기록:
 - has_ramp: "휠체어 이용 용이/가능" 류 명시적 긍정 문구만 True.
   ⚠ 이 데이터의 "경사로"는 램프가 아니라 경사 구간(예: "오르막 경사로 42m/9˚")을
   뜻하므로 has_ramp 근거로 쓰지 않는다. False 는 부여하지 않는다.
 - surface_condition: "길 상태 안 좋음" → "poor" 만 기록 (원본에 "좋음" 기록 없음).
 - 매칭이 애매하면 기존 장소에 붙이지 않고 신규 장소로 둔다 (오매칭 = 거짓 정보).

사용법:
    conda activate projecth
    cd backend
    python scripts/enrich_places_accessibility.py
"""
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.utils.geo import distance_to_airport_km, haversine_km  # noqa: E402
from fetch_jeju_places import INDOOR_KEYWORDS  # noqa: E402

METADATA = BACKEND.parent / "vector_store" / "metadata.jsonl"
PLACES = BACKEND / "data" / "processed" / "jeju_places.json"
OUT = BACKEND / "data" / "processed" / "place_accessibility.json"
SOURCE = "제주데이터허브 무장애여행정보"

# 매칭 표 검토 후 수동 확정이 필요한 쌍: rag place_id → jeju id ("new" 면 강제 신규)
MANUAL_OVERRIDES: dict[str, str] = {}

MAX_SNIPPETS = 5
SNIPPET_LEN = 160
DEGREE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[˚°도]")
POOR_SURFACE_RE = re.compile(r"길\s*상태\s*안\s*좋")
NEGATIVE_HINTS = ("불가", "어려", "곤란", "힘들")


def _norm_name(name: str) -> str:
    name = unicodedata.normalize("NFC", name or "")
    return re.sub(r"[\s_\-·]", "", name).lower()


def _name_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm_name(a), _norm_name(b)).ratio()


def _load_rag_places() -> dict[str, dict]:
    """metadata.jsonl 을 place_id 단위로 집계한다."""
    groups: dict[str, dict] = {}
    with METADATA.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            doc = json.loads(line)
            pid = str(doc.get("place_id") or "")
            if not pid:
                continue
            g = groups.setdefault(pid, {"place_id": pid, "name": None, "docs": [], "coords": []})
            g["docs"].append(doc)
            if doc.get("place_name") and not g["name"]:
                g["name"] = doc["place_name"]
            if doc.get("lat") is not None and doc.get("lng") is not None:
                g["coords"].append((float(doc["lat"]), float(doc["lng"])))
    for g in groups.values():
        if g["coords"]:
            g["lat"] = sum(c[0] for c in g["coords"]) / len(g["coords"])
            g["lon"] = sum(c[1] for c in g["coords"]) / len(g["coords"])
        else:
            g["lat"] = g["lon"] = None
    return groups


def _match(rag: dict, places: list[dict]) -> tuple[dict | None, str]:
    """매칭 규칙: ①정규화 이름 완전일치·≤2km ②≤200m·(포함관계 or ratio≥0.5) ③≤500m·ratio≥0.6"""
    if rag["place_id"] in MANUAL_OVERRIDES:
        target = MANUAL_OVERRIDES[rag["place_id"]]
        if target == "new":
            return None, "수동(신규)"
        hit = next((p for p in places if p["id"] == target), None)
        return hit, "수동"

    rag_norm = _norm_name(rag["name"] or "")
    best: tuple[dict | None, str] = (None, "")
    for p in places:
        p_norm = _norm_name(p["name"])
        dist = None
        if rag["lat"] is not None and p.get("lat") is not None and p.get("lon") is not None:
            dist = haversine_km(rag["lat"], rag["lon"], p["lat"], p["lon"])
        if rag_norm and rag_norm == p_norm and (dist is None or dist <= 2.0):
            return p, f"이름일치({dist}km)"
        if dist is None:
            continue
        ratio = _name_ratio(rag["name"] or "", p["name"])
        contains = rag_norm and (rag_norm in p_norm or p_norm in rag_norm)
        if dist <= 0.2 and (contains or ratio >= 0.5):
            best = (p, f"근접+유사({dist}km, r={ratio:.2f})")
        elif dist <= 0.5 and ratio >= 0.6 and not best[0]:
            best = (p, f"인접+고유사({dist}km, r={ratio:.2f})")
    return best


def _has_positive_wheelchair(texts: list[str]) -> tuple[bool, str | None]:
    """"휠체어 … 용이/가능" 명시 긍정 문구 탐지 (부정 표현 동반 시 제외)."""
    for text in texts:
        for m in re.finditer("휠체어", text):
            window = text[m.start(): m.start() + 30]
            if ("용이" in window or "가능" in window) and not any(
                neg in window for neg in NEGATIVE_HINTS
            ):
                return True, window.strip()
    return False, None


def _derive(rag: dict) -> dict:
    """장소 문서들에서 접근성 사실을 보수적으로 파생한다."""
    docs = rag["docs"]
    texts = [d.get("text") or "" for d in docs]
    joined = "\n".join(texts)

    has_toilet = True if "장애인화장실" in joined else None
    has_ramp, ramp_evidence = _has_positive_wheelchair(texts)

    slope_docs = [d for d in docs if d.get("category") == "slope"]
    degrees = [float(v) for v in DEGREE_RE.findall(joined) if float(v) <= 45]
    has_stairs = "계단" in joined
    slope_level = None
    if slope_docs:
        risk_high = any(d.get("risk_level") == "high" for d in slope_docs)
        if (degrees and max(degrees) >= 5) or has_stairs or risk_high:
            slope_level = "high"
        elif degrees and max(degrees) < 5 and not has_stairs:
            slope_level = "low"

    surface = "poor" if POOR_SURFACE_RE.search(joined) else None

    # 대표 스니펫: 화장실·휠체어 언급 → 경사/위험 → 일반 순
    def _prio(d: dict) -> int:
        t = d.get("text") or ""
        if "장애인화장실" in t or "휠체어" in t:
            return 0
        if d.get("category") in ("slope", "risk") or d.get("risk_level") == "high":
            return 1
        return 2

    snippets: list[str] = []
    for d in sorted(docs, key=_prio):
        t = (d.get("text") or "").strip()
        if not t:
            continue
        s = t[:SNIPPET_LEN] + ("…" if len(t) > SNIPPET_LEN else "")
        if s not in snippets:
            snippets.append(s)
        if len(snippets) >= MAX_SNIPPETS:
            break

    return {
        "has_accessible_toilet": has_toilet,
        "has_ramp": True if has_ramp else None,
        "_ramp_evidence": ramp_evidence,
        "slope_level": slope_level,
        "surface_condition": surface,
        "barrier_free_info": snippets,
    }


def _is_indoor(name: str) -> bool | None:
    return True if any(k in name for k in INDOOR_KEYWORDS) else None


def _new_place(rag: dict, derived: dict) -> dict:
    name = rag["name"] or f"무장애 여행지 {rag['place_id']}"
    indoor = _is_indoor(name)
    return {
        "id": f"bf_{rag['place_id']}",
        "name": name,
        "name_en": None,
        "address": None,
        "phone": None,
        "lat": round(rag["lat"], 6) if rag["lat"] is not None else None,
        "lon": round(rag["lon"], 6) if rag["lon"] is not None else None,
        "category": "indoor" if indoor else "outdoor",
        "is_indoor": indoor,
        "has_accessible_toilet": derived["has_accessible_toilet"],
        "has_accessible_parking": None,
        "has_wheelchair_rental": None,
        "has_nursing_room": None,
        "has_accessible_rest": None,
        "toilet_count": None,
        "parking_count": None,
        "region": None,
        "has_ramp": derived["has_ramp"],
        "surface_condition": derived["surface_condition"],
        "slope_level": derived["slope_level"],
        "near_low_floor_bus": None,
        "distance_to_airport_km": (
            distance_to_airport_km(rag["lat"], rag["lon"])
            if rag["lat"] is not None else None
        ),
        "image_urls": [],
        "barrier_free_info": derived["barrier_free_info"],
        "source": SOURCE,
    }


def main() -> int:
    if not METADATA.exists():
        print(f"metadata.jsonl 없음: {METADATA} — 먼저 벡터DB를 빌드하세요.")
        return 1
    with PLACES.open(encoding="utf-8") as f:
        places = json.load(f)

    rag_places = _load_rag_places()
    enrich: dict[str, dict] = {}
    new_places: list[dict] = []
    rag_place_map: dict[str, str] = {}
    ramp_grants: list[tuple[str, str]] = []

    print(f"RAG 장소 {len(rag_places)}곳 ↔ 기존 장소 {len(places)}곳 매칭")
    print("-" * 78)
    for pid in sorted(rag_places, key=lambda x: int(x) if x.isdigit() else 0):
        rag = rag_places[pid]
        derived = _derive(rag)
        evidence = derived.pop("_ramp_evidence")
        if derived["has_ramp"]:
            ramp_grants.append((rag["name"] or pid, evidence or ""))

        hit, how = _match(rag, places)
        if hit:
            rag_place_map[pid] = hit["id"]
            fills = {
                k: v for k, v in derived.items()
                if k != "barrier_free_info" and v is not None and hit.get(k) is None
            }
            fills["barrier_free_info"] = derived["barrier_free_info"]
            enrich[hit["id"]] = fills
            filled = [k for k in fills if k != "barrier_free_info"]
            print(f"[매칭] {rag['name']:<20} → {hit['name']:<20} {how} 채움={filled}")
        else:
            place = _new_place(rag, derived)
            new_places.append(place)
            rag_place_map[pid] = place["id"]
            print(f"[신규] {rag['name']:<20} → {place['id']} "
                  f"(화장실={place['has_accessible_toilet']}, 경사={place['slope_level']})")

    print("-" * 78)
    print(f"매칭 {len(enrich)}곳 · 신규 {len(new_places)}곳 → 총 {len(places) + len(new_places)}곳")
    if ramp_grants:
        print("\nhas_ramp=True 부여 근거 (육안 검토 필수):")
        for name, ev in ramp_grants:
            print(f"  - {name}: …{ev}…")
    else:
        print("\nhas_ramp=True 부여: 없음")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE,
        "rag_place_map": rag_place_map,
        "enrich": enrich,
        "new_places": new_places,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[성공] 오버레이 저장 → {OUT.relative_to(BACKEND)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
