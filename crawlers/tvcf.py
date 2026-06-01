"""TVCF (tvcf.co.kr) Playwright 크롤러 - TV/케이블 집행 기간"""
import re
import time
import logging
import calendar
from datetime import date
from urllib.parse import quote

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

SEARCH_URL = (
    "https://tvcf.co.kr/worked/video"
    "?search_term={query}&mediaType_value=1"
    "&page={page}&rows=50&sort_by=registrated_date"
    "&country_code_value=410&lang=ko"
)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class TvcfCrawler:
    def __init__(self, delay: float = 1.0, headless: bool = True):
        self.delay = delay
        self.headless = headless

    def crawl(self, advertisers: list[str], year: int, month: int) -> dict:
        """month: 0-indexed (JS style). Returns {advertiser: [{s,e}, ...]}"""
        target_month = month + 1  # 1-indexed
        results = {}

        with sync_playwright() as p:
            br = p.chromium.launch(headless=self.headless)
            ctx = br.new_context(locale="ko-KR", user_agent=UA)

            for adv in advertisers:
                try:
                    periods = self._crawl_one(ctx, adv, year, target_month)
                    if periods:
                        results[adv] = periods
                        logger.info(f"TVCF {adv}: {periods}")
                    time.sleep(self.delay)
                except Exception as e:
                    logger.warning(f"TVCF {adv}: {e}")

            br.close()

        return results

    def _crawl_one(self, ctx, advertiser: str, year: int, month: int) -> list[dict]:
        page = ctx.new_page()
        all_periods: list[dict] = []

        try:
            for pg_num in [1, 2]:  # 최대 2페이지 (100개)
                url = SEARCH_URL.format(query=quote(advertiser), page=pg_num)
                page.goto(url, wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(2000)

                # /play/ 링크 텍스트에서 날짜 추출
                cards = page.eval_on_selector_all(
                    "a[href*='/play/']",
                    "els => els.map(e=>e.innerText.trim())"
                )

                found = False
                for text in cards:
                    periods = _parse_card_dates(text, year, month)
                    all_periods.extend(periods)
                    if periods:
                        found = True

                if not found and pg_num == 1:
                    break  # 1페이지에 해당 월 결과 없으면 종료
        finally:
            page.close()

        return _merge_periods(all_periods)


# ── 날짜 파싱 헬퍼 ────────────────────────────────────────────────────────────

def _parse_card_dates(card_text: str, year: int, target_month: int) -> list[dict]:
    """
    카드 텍스트에서 날짜 추출.
    형식: "MM.DD\n(MM.DD)" 또는 "YYYY.MM.DD"
    첫 번째 날짜 = 방영 시작, 두 번째 날짜 = 방영 종료(또는 마지막 확인일)
    """
    days_in_month = calendar.monthrange(year, target_month)[1]
    month_start = date(year, target_month, 1)
    month_end   = date(year, target_month, days_in_month)

    # YYYY.MM.DD 형식 먼저 시도 (과거 CF)
    full = re.findall(r'(\d{4})\.(\d{2})\.(\d{2})', card_text)
    if full:
        try:
            s = date(int(full[0][0]), int(full[0][1]), int(full[0][2]))
            e = date(int(full[-1][0]), int(full[-1][1]), int(full[-1][2])) if len(full) > 1 else s
            return _clip(s, e, month_start, month_end)
        except ValueError:
            pass

    # MM.DD 형식
    short = re.findall(r'(\d{2})\.(\d{2})', card_text)
    if not short:
        return []

    try:
        sm, sd = int(short[0][0]), int(short[0][1])
        em, ed = int(short[-1][0]), int(short[-1][1])

        # 연도 추론: month가 1이고 날짜가 12월이면 전년도 가능
        s_year = year if sm <= 12 else year - 1
        e_year = year if em <= 12 else year - 1

        # 시작이 종료보다 늦으면 (연말→연초 크로스)
        if sm > em and abs(sm - em) > 6:
            e_year = year + 1

        s = date(s_year, sm, sd)
        e = date(e_year, em, ed)
        if s > e:
            e = s

        return _clip(s, e, month_start, month_end)
    except (ValueError, OverflowError):
        return []


def _clip(s: date, e: date, month_start: date, month_end: date) -> list[dict]:
    actual_s = max(s, month_start)
    actual_e = min(e, month_end)
    if actual_s <= actual_e:
        return [{"s": actual_s.day, "e": actual_e.day}]
    return []


def _merge_periods(periods: list[dict]) -> list[dict]:
    """겹치는/인접한 기간 병합"""
    if not periods:
        return []
    sorted_p = sorted(periods, key=lambda x: x["s"])
    merged = [sorted_p[0].copy()]
    for p in sorted_p[1:]:
        if p["s"] <= merged[-1]["e"] + 1:
            merged[-1]["e"] = max(merged[-1]["e"], p["e"])
        else:
            merged.append(p.copy())
    return merged
