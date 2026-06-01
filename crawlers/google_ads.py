"""Google Ads Transparency — 배치 병렬 크롤러
각 스레드가 독립 Playwright 인스턴스 + 브라우저를 가짐 (greenlet 충돌 회피)
4개 스레드 × 40개 광고주 배치 = ~5분
"""
import re
import logging
import calendar
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

TRANSPARENCY_URL = "https://adstransparency.google.com/?region=KR"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
N_THREADS = 4   # 독립 브라우저 4개


class GoogleAdsCrawler:
    def __init__(self, threads: int = N_THREADS, headless: bool = True):
        self.threads = threads
        self.headless = headless

    def crawl(self, advertisers: list[str], year: int, month: int) -> dict:
        """month: 0-indexed. Returns {advertiser: [{s,e}, ...]}"""
        target_month = month + 1
        days_in_month = calendar.monthrange(year, target_month)[1]

        # advertisers를 threads개 배치로 분할
        batches = _split(advertisers, self.threads)
        all_results = {}

        def run_batch(batch):
            return _process_batch(batch, year, target_month, days_in_month, self.headless)

        with ThreadPoolExecutor(max_workers=self.threads) as ex:
            futures = [ex.submit(run_batch, b) for b in batches if b]
            for fut in as_completed(futures):
                try:
                    batch_result = fut.result()
                    all_results.update(batch_result)
                except Exception as e:
                    logger.warning(f"배치 실패: {e}")

        return all_results


def _split(lst: list, n: int) -> list[list]:
    """리스트를 n개 청크로 균등 분할"""
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]


def _process_batch(advertisers: list[str], year: int, month: int,
                   days_in_month: int, headless: bool) -> dict:
    """하나의 스레드: 자체 playwright + browser로 배치 처리"""
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        for adv in advertisers:
            try:
                ctx = browser.new_context(locale="ko-KR", user_agent=UA)
                periods = _crawl_one(ctx, adv, year, month, days_in_month)
                ctx.close()
                if periods:
                    results[adv] = periods
                    logger.info(f"Google {adv}: {periods}")
            except Exception as e:
                logger.debug(f"Google {adv}: {e}")
        browser.close()
    return results


def _crawl_one(ctx, advertiser: str, year: int,
               month: int, days_in_month: int) -> list[dict]:
    page = ctx.new_page()
    api_data: list[bytes] = []

    def on_response(resp):
        try:
            if ("adstransparency.google.com" in resp.url
                    and resp.status == 200 and "anji" in resp.url):
                body = resp.body()
                if body:
                    api_data.append(body)
        except Exception:
            pass

    page.on("response", on_response)

    try:
        page.goto(TRANSPARENCY_URL, wait_until="networkidle", timeout=25000)
        page.locator("input").first.fill(advertiser)
        page.wait_for_timeout(1500)

        # 광고주 드롭다운 클릭 (이름 유사도 기준)
        clicked = False
        items = page.locator("material-select-item").all()
        if items:
            clean = re.sub(r'[\s\(\)\.,\[\]]', '', advertiser)
            best = items[0]
            for item in items[:5]:
                txt = item.inner_text()
                if clean[:4] in re.sub(r'[\s\(\)\.,\[\]]', '', txt):
                    best = item
                    break
            best.click()
            clicked = True

        if not clicked:
            try:
                page.click(f"text={advertiser[:5]}", timeout=3000)
                clicked = True
            except PWTimeout:
                pass

        if not clicked:
            page.close()
            return []

        page.wait_for_timeout(2000)

        body_text = page.inner_text("body")
        if _ad_count(body_text) == 0:
            page.close()
            return []

        periods = _parse_api_responses(api_data, year, month, days_in_month)
        if not periods:
            periods = [{"s": 1, "e": days_in_month}]   # 활성 확인됨, 날짜 불명

        page.close()
        return periods

    except Exception as e:
        logger.debug(f"_crawl_one {advertiser}: {e}")
        try:
            page.close()
        except Exception:
            pass
        return []


def _ad_count(text: str) -> int:
    m = re.search(r'광고\s*(?:약\s*)?([\d.]+)(만)?개', text)
    if m:
        n = float(m.group(1))
        return int(n * 10000 if m.group(2) == '만' else n)
    return 1 if ('인증' in text or 'videocam' in text) else 0


def _parse_api_responses(responses: list[bytes], year: int,
                          month: int, days_in_month: int) -> list[dict]:
    days_active: set[int] = set()
    full_pat = re.compile(rb'(\d{4})-(\d{2})-(\d{2})')
    for body in responses:
        for m in full_pat.finditer(body):
            try:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if y == year and mo == month and 1 <= d <= days_in_month:
                    days_active.add(d)
            except ValueError:
                pass
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
