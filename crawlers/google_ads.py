"""Google Ads Transparency Playwright 크롤러 - 유튜브 집행 기간"""
import re
import time
import logging
import calendar
from datetime import date

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

TRANSPARENCY_URL = "https://adstransparency.google.com/?region=KR"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class GoogleAdsCrawler:
    def __init__(self, delay: float = 2.0, headless: bool = True):
        self.delay = delay
        self.headless = headless

    def crawl(self, advertisers: list[str], year: int, month: int) -> dict:
        """month: 0-indexed. Returns {advertiser: [{s,e}, ...]}"""
        target_month = month + 1
        days_in_month = calendar.monthrange(year, target_month)[1]
        date_from = f"{year}-{target_month:02d}-01"
        date_to   = f"{year}-{target_month:02d}-{days_in_month:02d}"

        results = {}

        with sync_playwright() as p:
            br = p.chromium.launch(headless=self.headless)
            ctx = br.new_context(locale="ko-KR", user_agent=UA)

            for adv in advertisers:
                try:
                    periods = self._crawl_one(ctx, adv, year, target_month,
                                              days_in_month, date_from, date_to)
                    if periods:
                        results[adv] = periods
                        logger.info(f"Google Ads {adv}: {periods}")
                    time.sleep(self.delay)
                except Exception as e:
                    logger.warning(f"Google Ads {adv}: {e}")

            br.close()

        return results

    def _crawl_one(self, ctx, advertiser: str, year: int, month: int,
                   days_in_month: int, date_from: str, date_to: str) -> list[dict]:
        page = ctx.new_page()
        try:
            page.goto(TRANSPARENCY_URL, wait_until="networkidle", timeout=20000)

            # 검색
            search = page.locator("input").first
            search.fill(advertiser)
            page.wait_for_timeout(1500)

            # 첫 번째 광고주 클릭 (exact match 우선, 없으면 첫 번째)
            clicked = False
            try:
                # 광고주 이름이 텍스트로 들어있는 MATERIAL-SELECT-ITEM 클릭
                items = page.locator("material-select-item").all()
                if items:
                    # 가장 비슷한 이름 찾기
                    best = items[0]
                    for item in items[:5]:
                        txt = item.inner_text()
                        # 공백/특수문자 제거 후 비교
                        clean_adv = re.sub(r'[\s\(\)\.,]', '', advertiser)
                        clean_txt = re.sub(r'[\s\(\)\.,]', '', txt)
                        if clean_adv in clean_txt or clean_txt.startswith(clean_adv[:4]):
                            best = item
                            break
                    best.click()
                    clicked = True
            except Exception:
                pass

            if not clicked:
                # fallback: text 클릭
                try:
                    page.click(f"text={advertiser[:5]}", timeout=3000)
                    clicked = True
                except Exception:
                    pass

            if not clicked:
                page.close()
                return []

            page.wait_for_timeout(2000)

            # 날짜 필터 설정
            self._set_date_filter(page, date_from, date_to)
            page.wait_for_timeout(2000)

            # 광고 수 확인
            body_text = page.inner_text("body")
            ad_count = _extract_ad_count(body_text)

            if ad_count == 0:
                page.close()
                return []

            # 광고가 있으면 날짜 기간 추출 시도
            periods = _extract_periods_from_page(page, year, month, days_in_month)
            if not periods:
                # 날짜 추출 실패해도 활성으로 간주 (전체 월로 기록)
                periods = [{"s": 1, "e": days_in_month}]

            page.close()
            return periods

        except Exception as e:
            logger.debug(f"Google _crawl_one {advertiser}: {e}")
            page.close()
            return []

    def _set_date_filter(self, page, date_from: str, date_to: str):
        """날짜 필터를 특정 월로 설정"""
        try:
            # "전체 기간" 버튼 클릭
            page.click("text=전체 기간", timeout=5000)
            page.wait_for_timeout(1000)

            # URL 파라미터 방식 시도
            cur_url = page.url
            if "?" in cur_url:
                new_url = cur_url + f"&start_date={date_from}&end_date={date_to}"
            else:
                new_url = cur_url + f"?start_date={date_from}&end_date={date_to}"
            page.goto(new_url, wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(1500)

        except Exception as e:
            logger.debug(f"날짜 필터 설정 실패: {e}")


def _extract_ad_count(text: str) -> int:
    """페이지 텍스트에서 광고 개수 추출"""
    # "광고 약 X만개" or "광고 X개"
    m = re.search(r'광고\s*(?:약\s*)?([\d.]+)(만)?개', text)
    if m:
        n = float(m.group(1))
        if m.group(2) == '만':
            n *= 10000
        return int(n)
    # 광고 카드 수 - 최소한 텍스트가 있으면 활성
    if '인증' in text or 'videocam' in text:
        return 1
    return 0


def _extract_periods_from_page(page, year: int, month: int,
                                days_in_month: int) -> list[dict]:
    """광고 페이지에서 날짜 패턴 추출"""
    text = page.inner_text("body")
    month_start = date(year, month, 1)
    month_end   = date(year, month, days_in_month)

    days_active = set()

    # 날짜 패턴 탐색 (YYYY년 MM월 DD일 형식 등)
    patterns = [
        r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
        r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            try:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if y == year and mo == month and 1 <= d <= days_in_month:
                    days_active.add(d)
            except (ValueError, IndexError):
                pass

    if not days_active:
        return []

    return _days_to_periods(sorted(days_active))


def _days_to_periods(days: list[int]) -> list[dict]:
    if not days:
        return []
    periods, start, prev = [], days[0], days[0]
    for d in days[1:]:
        if d <= prev + 2:
            prev = d
        else:
            periods.append({"s": start, "e": prev})
            start = prev = d
    periods.append({"s": start, "e": prev})
    return periods
