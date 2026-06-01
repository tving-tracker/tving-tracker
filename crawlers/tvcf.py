"""TVCF (tvcf.co.kr) crawler — TV/케이블 집행 기간 수집"""
import re
import time
import logging
from datetime import datetime, date
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://tvcf.co.kr/",
}
BASE = "https://tvcf.co.kr"
SEARCH_URL = BASE + "/s/?q={query}&type=3"  # type=3: 광고주 검색


class TvcfCrawler:
    def __init__(self, delay: float = 1.5):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay

    def crawl(self, advertisers: list[str], year: int, month: int) -> dict:
        """
        Returns: { advertiser: [{"s": int, "e": int}, ...] }
        month is 0-indexed (JS style)
        """
        results = {}
        target_month = month + 1  # 1-indexed for comparison

        for adv in advertisers:
            try:
                periods = self._crawl_advertiser(adv, year, target_month)
                if periods:
                    results[adv] = periods
                    logger.info(f"TVCF {adv}: {len(periods)} 기간")
                time.sleep(self.delay)
            except Exception as e:
                logger.warning(f"TVCF {adv} 실패: {e}")

        return results

    def _crawl_advertiser(self, advertiser: str, year: int, month: int) -> list[dict]:
        """Search TVCF for advertiser and extract TV air periods."""
        url = SEARCH_URL.format(query=quote(advertiser))
        resp = self.session.get(url, timeout=10)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Find advertiser links in search results
        adv_links = []
        for a in soup.select("a[href*='/b/']"):
            if advertiser[:3] in (a.get_text() or ""):
                adv_links.append(BASE + a["href"])

        if not adv_links:
            # Try direct brand page
            adv_links = [BASE + f"/b/{quote(advertiser)}/"]

        periods = []
        seen = set()

        for link in adv_links[:3]:  # Check top 3 matches
            try:
                p = self._extract_periods_from_page(link, year, month)
                for period in p:
                    key = (period["s"], period["e"])
                    if key not in seen:
                        seen.add(key)
                        periods.append(period)
            except Exception as e:
                logger.debug(f"TVCF page error {link}: {e}")

        return periods

    def _extract_periods_from_page(self, url: str, year: int, month: int) -> list[dict]:
        """Extract air date periods from a TVCF brand page."""
        resp = self.session.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        periods = []
        date_pattern = re.compile(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})")

        # TVCF shows dates in various formats; collect all date mentions
        date_texts = []
        for elem in soup.select(".adlist-info, .ad-date, .date, time, [class*='date']"):
            date_texts.append(elem.get_text())

        # Also scan full page text for date patterns in target month
        full_text = soup.get_text()
        for m in date_pattern.finditer(full_text):
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if y == year and mo == month:
                date_texts.append(f"{y}.{mo}.{d}")

        # Build periods from found dates
        days_found = set()
        for text in date_texts:
            for m in date_pattern.finditer(text):
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if y == year and mo == month and 1 <= d <= 31:
                    days_found.add(d)

        if days_found:
            periods = _days_to_periods(sorted(days_found))

        return periods


def _days_to_periods(days: list[int]) -> list[dict]:
    """Convert a list of days to contiguous periods [{s, e}, ...]"""
    if not days:
        return []
    periods = []
    start = days[0]
    prev = days[0]
    for d in days[1:]:
        if d <= prev + 2:  # allow 1-day gaps
            prev = d
        else:
            periods.append({"s": start, "e": prev})
            start = d
            prev = d
    periods.append({"s": start, "e": prev})
    return periods
