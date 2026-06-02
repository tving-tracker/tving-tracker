"""2026년 1~6월 전체 재크롤 스크립트."""
import sys
import logging
from crawl import run_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

months = [(2026, m) for m in range(1, 7)]  # 1월~6월

total_all = 0
for year, month in months:
    print(f"\n{'='*50}", flush=True)
    print(f"  2026년 {month}월 크롤링 시작", flush=True)
    print(f"{'='*50}", flush=True)
    try:
        count = run_all(year=year, month=month, platforms=["tv", "yt"])
        total_all += count
        print(f"  완료: 2026년 {month}월 {count}건", flush=True)
    except Exception as e:
        print(f"  오류: 2026년 {month}월 - {e}", flush=True)

print(f"\n{'='*50}", flush=True)
print(f"  전체 완료: {total_all}건 저장", flush=True)
print(f"{'='*50}", flush=True)
