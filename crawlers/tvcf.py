"""TVCF (tvcf.co.kr) — requests 기반 고속 크롤러 (SSR 확인)
ThreadPoolExecutor로 동시 처리. Playwright 불필요.
"""
import re
import logging
import calendar
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEARCH_URL = (
    "https://tvcf.co.kr/worked/video"
    "?search_term={query}&mediaType_value=1"
    "&page={page}&rows=50&sort_by=registrated_date"
    "&country_code_value=410&lang=ko"
)
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://tvcf.co.kr/",
}
MAX_WORKERS = 10
MAX_PAGES = 2   # 페이지당 50개 → 최대 100개 CF 확인


class TvcfCrawler:
    def __init__(self, workers: int = MAX_WORKERS):
        self.workers = workers
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def crawl(self, advertisers: list[str], year: int, month: int,
              aliases: dict[str, list[str]] | None = None) -> dict:
        """month: 0-indexed (JS). aliases: {advertiser: [extra_search_terms]}
        Returns {advertiser: [{s,e}, ...]}"""
        target_month = month + 1
        aliases = aliases or {}
        results = {}

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futures = {
                ex.submit(
                    self._crawl_adv, adv, year, target_month, aliases.get(adv, [])
                ): adv
                for adv in advertisers
            }
            for fut in as_completed(futures):
                adv = futures[fut]
                try:
                    periods = fut.result()
                    if periods:
                        results[adv] = periods
                        logger.info(f"TVCF {adv}: {periods}")
                except Exception as e:
                    logger.warning(f"TVCF {adv}: {e}")

        return results

    def _crawl_adv(self, advertiser: str, year: int, month: int,
                   extra_terms: list[str]) -> list[dict]:
        """광고주명 + alias 모두 검색 후 결과 병합."""
        all_periods: list[dict] = []
        for term in [advertiser] + extra_terms:
            all_periods.extend(self._crawl_one(term, year, month))
        return _merge_periods(all_periods)

    def _crawl_one(self, advertiser: str, year: int, month: int) -> list[dict]:
        all_periods: list[dict] = []

        for pg in range(1, MAX_PAGES + 1):
            url = SEARCH_URL.format(query=quote(advertiser), page=pg)
            try:
                resp = self.session.get(url, timeout=12)
                resp.raise_for_status()
            except Exception as e:
                logger.debug(f"TVCF GET {advertiser} p{pg}: {e}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("a[href*='/play/']")

            found_this_page = False
            for card in cards:
                text = card.get_text(" ", strip=True)
                periods = _parse_card_dates(text, year, month)
                if periods:
                    all_periods.extend(periods)
                    found_this_page = True

            # 1페이지에 해당 월 결과 없으면 중단
            if not found_this_page and pg == 1:
                break

        return _merge_periods(all_periods)


# ── 날짜 파싱 ─────────────────────────────────────────────────────────────────

DATE_PAT = re.compile(r'(\d{2})\.(\d{2})')
FULL_DATE_PAT = re.compile(r'(\d{4})\.(\d{2})\.(\d{2})')


def _parse_card_dates(text: str, year: int, target_month: int) -> list[dict]:
    """
    카드 텍스트 예시:
      "삼성 갤럭시 S26 서클 투 서치 하객룩 05.28 (05.28)"
    첫 번째 MM.DD = 온에어 시작일, 마지막 MM.DD = 종료일(마지막 확인)
    """
    days_in = calendar.monthrange(year, target_month)[1]
    m_start = date(year, target_month, 1)
    m_end   = date(year, target_month, days_in)

    # 연도가 명시된 경우 (2025.10.03 형식)
    full = FULL_DATE_PAT.findall(text)
    if full:
        try:
            sy, sm, sd = int(full[0][0]), int(full[0][1]), int(full[0][2])
            ey, em, ed = int(full[-1][0]), int(full[-1][1]), int(full[-1][2])
            return _clip(date(sy, sm, sd), date(ey, em, ed), m_start, m_end)
        except ValueError:
            pass

    # MM.DD 형식 (올해 기준)
    shorts = DATE_PAT.findall(text)
    # CSS 값 필터링: month 01-12, day 01-31 범위만
    valid = [(int(m), int(d)) for m, d in shorts
             if 1 <= int(m) <= 12 and 1 <= int(d) <= 31]
    if not valid:
        return []

    try:
        sm, sd = valid[0]
        em, ed = valid[-1]

        # 연도 추론: 12월 → 1월 크로스
        sy = ey = year
        if sm > em and sm - em > 6:
            ey = year + 1

        s = date(sy, sm, sd)
        e = date(ey, em, ed)
        if s > e:
            e = s

        return _clip(s, e, m_start, m_end)
    except (ValueError, OverflowError):
        return []


def _clip(s: date, e: date, m_start: date, m_end: date) -> list[dict]:
    today = date.today()
    actual_s = max(s, m_start)
    # 현재 월이면 오늘 이후 미래 날짜 제거
    actual_e = min(e, m_end, today if m_end >= today else m_end)
    if actual_s <= actual_e:
        return [{"s": actual_s.day, "e": actual_e.day}]
    return []


def _merge_periods(periods: list[dict]) -> list[dict]:
    if not periods:
        return []
    uniq = {(p["s"], p["e"]) for p in periods}
    sorted_p = sorted(uniq, key=lambda x: x[0])
    merged = [{"s": sorted_p[0][0], "e": sorted_p[0][1]}]
    for s, e in sorted_p[1:]:
        if s <= merged[-1]["e"] + 1:
            merged[-1]["e"] = max(merged[-1]["e"], e)
        else:
            merged.append({"s": s, "e": e})
    return merged
