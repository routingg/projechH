"""제주 저상버스 데이터 정규화.

raw/transport 의 두 CSV 를 요약해 processed/low_floor_buses.json 으로 저장한다.

주의: 이 데이터에는 '정류소 위치(좌표)'가 없어 관광지별 근접도를 계산할 수 없다.
      따라서 관광지 점수에 직접 반영하지 않고, 서비스 전역의 저상버스 운행 현황(참고 정보)으로만 사용한다.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
RAW = BACKEND / "data" / "raw" / "transport"
PROCESSED = BACKEND / "data" / "processed"

STATUS_CSV = RAW / "제주특별자치도_저상버스현황_20230612.csv"
ROUTE_CSV = RAW / "제주특별자치도_저상버스운행노선현황_20241231.csv"
SOURCE = "제주특별자치도 저상버스현황 / 저상버스운행노선현황"


def _rows(path: Path) -> list[dict]:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            with path.open(encoding=enc) as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"인코딩 판별 실패: {path}")


def main() -> int:
    status = _rows(STATUS_CSV)
    routes = _rows(ROUTE_CSV)

    low_floor_routes = sorted({r["노선"].strip() for r in status if r.get("노선")})
    operators = dict(Counter(r["버스회사"].strip() for r in status if r.get("버스회사")))
    total_low_floor = sum(
        int(r["저상버스대수"]) for r in routes if r.get("저상버스대수", "").isdigit()
    )

    summary = {
        "vehicle_count": len(status),          # 저상버스 차량 수
        "route_count": len(low_floor_routes),  # 저상버스 운행 노선 수(고유)
        "total_low_floor_buses": total_low_floor,
        "operators": operators,                # 운수업체별 대수
        "routes": low_floor_routes,            # 저상버스 노선 번호 목록
        "source": SOURCE,
        "note": "정류소 좌표가 없어 관광지별 근접도는 산정하지 않으며, 서비스 전역 참고 정보로만 사용합니다.",
    }

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "low_floor_buses.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[성공] 저상버스 요약 저장 → {out.relative_to(BACKEND)}")
    print(f"  노선 {summary['route_count']}개 · 차량 {summary['vehicle_count']}대 · "
          f"업체 {len(operators)}곳")
    return 0


if __name__ == "__main__":
    sys.exit(main())
