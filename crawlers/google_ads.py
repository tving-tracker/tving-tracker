"""Google Ads Transparency crawler — 유튜브 집행 기간 수집"""
import time
import logging
import calendar
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://adstransparency.google.com/",
    "x-goog-authuser": "0",
}

# Unofficial API used by the Ads Transparency web app
SEARCH_URL = "https://adstransparency.google.com/anji/_/rpc/AdsTransparencyService/SearchAds"
ADVERTISER_URL = "https://adstransparency.google.com/anji/_/rpc/AdsTransparencyService/SearchAdvertisers"


class GoogleAdsCrawler:
    def __init__(self, delay: float = 2.0):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay

    def crawl(self, advertisers: list[str], year: int, month: int) -> dict:
        """
        Returns: { advertiser: [{"s": int, "e": int}, ...] }
        """
        results = {}
        for adv in advertisers:
            try:
                periods = self._crawl_advertiser(adv, year, month)
                if periods:
                    results[adv] = periods
                    logger.info(f"Google {adv}: {len(periods)} 기간")
                time.sleep(self.delay)
            except Exception as e:
                logger.warning(f"Google {adv} 실패: {e}")
        return results

    def _crawl_advertiser(self, advertiser: str, year: int, month: int) -> list[dict]:
        # Step 1: Find advertiser ID
        adv_id = self._find_advertiser_id(advertiser)
        if not adv_id:
            return []

        # Step 2: Get ads for target month
        return self._get_ads_for_month(adv_id, year, month)

    def _find_advertiser_id(self, name: str) -> str | None:
        """Search for advertiser and return their ID."""
        try:
            payload = {
                "1": name,       # search query
                "2": "KR",       # country
                "3": 1,          # page token
            }
            resp = self.session.post(
                ADVERTISER_URL,
                json=payload,
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            # Response structure varies; try common paths
            advertisers = (
                data.get("1", {}).get("1", []) or
                data.get("advertisers", []) or
                []
            )
            for a in advertisers[:5]:
                adv_name = a.get("2", "") or a.get("name", "")
                if name[:4] in adv_name:
                    return str(a.get("1", "") or a.get("id", ""))
        except Exception as e:
            logger.debug(f"Google find_advertiser {name}: {e}")
        return None

    def _get_ads_for_month(self, adv_id: str, year: int, month: int) -> list[dict]:
        """Get active ad periods for advertiser in given month (0-indexed)."""
        target_month = month + 1  # convert to 1-indexed
        days_in_month = calendar.monthrange(year, target_month)[1]

        start_date = f"{year}-{target_month:02d}-01"
        end_date = f"{year}-{target_month:02d}-{days_in_month:02d}"

        try:
            payload = {
                "1": adv_id,
                "2": "KR",
                "3": {"1": start_date, "2": end_date},
                "4": "YOUTUBE",  # platform filter
            }
            resp = self.session.post(SEARCH_URL, json=payload, timeout=15)
            if resp.status_code != 200:
                return []

            data = resp.json()
            ads = data.get("1", []) or data.get("ads", [])
            return _parse_ad_periods(ads, year, target_month, days_in_month)
        except Exception as e:
            logger.debug(f"Google get_ads {adv_id}: {e}")
            return []


def _parse_ad_periods(ads: list, year: int, month: int, days_in_month: int) -> list[dict]:
    """Extract and merge run periods from ad objects."""
    days_active = set()

    for ad in ads:
        # Try various date field paths from the unofficial API
        start_str = (
            ad.get("start_date") or
            ad.get("3", {}).get("1") or
            ""
        )
        end_str = (
            ad.get("end_date") or
            ad.get("3", {}).get("2") or
            ""
        )

        try:
            s = datetime.strptime(start_str, "%Y-%m-%d") if start_str else None
            e = datetime.strptime(end_str, "%Y-%m-%d") if end_str else None
        except ValueError:
            continue

        if s and e:
            cur = s
            while cur <= e:
                if cur.year == year and cur.month == month:
                    days_active.add(cur.day)
                cur = cur.replace(day=cur.day + 1) if cur.day < days_in_month else \
                    cur.replace(month=cur.month + 1, day=1) if cur.month < 12 else \
                    cur.replace(year=cur.year + 1, month=1, day=1)

    if not days_active:
        return []

    return _days_to_periods(sorted(days_active))


def _days_to_periods(days: list[int]) -> list[dict]:
    if not days:
        return []
    periods = []
    start = days[0]
    prev = days[0]
    for d in days[1:]:
        if d <= prev + 2:
            prev = d
        else:
            periods.append({"s": start, "e": prev})
            start = d
            prev = d
    periods.append({"s": start, "e": prev})
    return periods
