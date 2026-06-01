"""Meta Ad Library crawler — Facebook/Instagram 집행 기간 수집
Meta Graph API 사용: https://developers.facebook.com/docs/graph-api/reference/ads_archive/
환경변수 META_ACCESS_TOKEN 필요.
"""
import os
import time
import logging
import calendar
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://graph.facebook.com/v19.0/ads_archive"
DEFAULT_FIELDS = "id,ad_creation_time,ad_delivery_start_time,ad_delivery_stop_time,page_name"


class MetaAdsCrawler:
    def __init__(self, access_token: str = None, delay: float = 1.0):
        self.token = access_token or os.getenv("META_ACCESS_TOKEN", "")
        self.delay = delay

    @property
    def available(self) -> bool:
        return bool(self.token)

    def crawl(self, advertisers: list[str], year: int, month: int) -> dict:
        """
        Returns: { advertiser: [{"s": int, "e": int}, ...] }
        """
        if not self.available:
            logger.warning("META_ACCESS_TOKEN 미설정 — Meta 크롤링 건너뜀")
            return {}

        results = {}
        target_month = month + 1
        days_in_month = calendar.monthrange(year, target_month)[1]

        for adv in advertisers:
            try:
                periods = self._crawl_advertiser(adv, year, target_month, days_in_month)
                if periods:
                    results[adv] = periods
                    logger.info(f"Meta {adv}: {len(periods)} 기간")
                time.sleep(self.delay)
            except Exception as e:
                logger.warning(f"Meta {adv} 실패: {e}")

        return results

    def _crawl_advertiser(self, advertiser: str, year: int, month: int,
                          days_in_month: int) -> list[dict]:
        params = {
            "search_terms": advertiser,
            "ad_reached_countries": "KR",
            "ad_type": "ALL",
            "ad_delivery_date_min": f"{year}-{month:02d}-01",
            "ad_delivery_date_max": f"{year}-{month:02d}-{days_in_month:02d}",
            "fields": DEFAULT_FIELDS,
            "limit": 100,
            "access_token": self.token,
        }

        ads = []
        url = API_BASE

        while url:
            resp = requests.get(url, params=params if url == API_BASE else {}, timeout=15)
            if resp.status_code == 400:
                logger.debug(f"Meta API 400: {resp.text[:200]}")
                break
            resp.raise_for_status()
            data = resp.json()
            ads.extend(data.get("data", []))

            # Pagination
            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}  # next URL already has params embedded

            if len(ads) >= 200:  # cap per advertiser
                break

        return _parse_periods(ads, year, month, days_in_month)


def _parse_periods(ads: list, year: int, month: int, days_in_month: int) -> list[dict]:
    days_active = set()

    for ad in ads:
        start_str = ad.get("ad_delivery_start_time", "")
        stop_str = ad.get("ad_delivery_stop_time", "")

        try:
            s = datetime.fromisoformat(start_str[:10]) if start_str else None
            e = datetime.fromisoformat(stop_str[:10]) if stop_str else datetime(year, month, days_in_month)
        except ValueError:
            continue

        if not s:
            continue

        # Clamp to target month
        month_start = datetime(year, month, 1)
        month_end = datetime(year, month, days_in_month)
        actual_start = max(s, month_start)
        actual_end = min(e, month_end)

        if actual_start <= actual_end:
            d = actual_start.day
            while d <= actual_end.day:
                days_active.add(d)
                d += 1

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
