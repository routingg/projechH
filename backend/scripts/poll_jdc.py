"""JDC 면세점 API 가 살아날 때까지 주기적으로 재시도하는 폴러.

성공하면 데이터를 저장하고 즉시 종료한다. 실패하면 간격만큼 쉬고 다시 시도한다.

사용법:
    conda activate projecth
    cd backend

    # 포그라운드 (기본 20분 간격, 최대 24시간)
    python scripts/poll_jdc.py

    # 간격/최대시간 조절 (초 단위 간격, 시간 단위 최대)
    python scripts/poll_jdc.py --interval 600 --max-hours 12

    # 백그라운드 실행
    nohup python scripts/poll_jdc.py > jdc_poll.log 2>&1 &

옵션:
    --interval  재시도 간격(초). 기본 1200(20분).
    --max-hours 최대 폴링 시간(시간). 기본 24. 0이면 무한.
    --once      1회만 시도하고 종료.
"""
import argparse
import functools
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from scripts.fetch_jdc import fetch_and_save  # noqa: E402

# 파일로 리다이렉트해도 로그가 즉시 보이도록 flush 강제
print = functools.partial(print, flush=True)  # noqa: A001


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main() -> int:
    p = argparse.ArgumentParser(description="JDC API 폴링 재시도")
    p.add_argument("--interval", type=int, default=1200, help="재시도 간격(초), 기본 1200")
    p.add_argument("--max-hours", type=float, default=24.0, help="최대 폴링 시간(시간), 0=무한")
    p.add_argument("--once", action="store_true", help="1회만 시도")
    args = p.parse_args()

    deadline = None if args.max_hours <= 0 else time.time() + args.max_hours * 3600
    attempt = 0

    print(f"[{_ts()}] JDC 폴링 시작 (간격 {args.interval}s, 최대 {args.max_hours}h)")
    while True:
        attempt += 1
        ok, msg = fetch_and_save()
        if ok:
            print(f"[{_ts()}] ✅ 성공 (시도 {attempt}회): {msg}")
            print("이제 앱을 재시작하면 실데이터가 반영됩니다.")
            return 0

        print(f"[{_ts()}] ⏳ 시도 {attempt}회 실패: {msg}")

        if args.once:
            return 2
        if deadline is not None and time.time() + args.interval > deadline:
            print(f"[{_ts()}] ⛔ 최대 폴링 시간({args.max_hours}h) 초과, 종료.")
            return 1
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
