"""Google Ads Transparency — 배치 병렬 크롤러
배치당 브라우저 1개 + 페이지 1개 재사용 (goto 최소화)
domcontentloaded 사용으로 networkidle 타임아웃 제거
"""
import re
import logging
import calendar
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

TRANSPARENCY_URL = "https://adstransparency.google.com/?region=KR"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
N_THREADS = 8


class GoogleAdsCrawler:
    def __init__(self, threads: int = N_THREADS, headless: bool = True):
        self.threads = threads
        self.headless = headless

    def crawl(self, advertisers: list[str], year: int, month: int) -> dict:
        """month: 0-indexed. Returns {advertiser: [{s,e}, ...]}"""
        target_month = month + 1
        days_in_month = calendar.monthrange(year, target_month)[1]

        batches = _split(advertisers, self.threads)
        all_results = {}

        with ThreadPoolExecutor(max_workers=self.threads) as ex:
            futures = [
                ex.submit(_process_batch, b, year, target_month, days_in_month, self.headless)
                for b in batches if b
            ]
            for fut in as_completed(futures):
                try:
                    all_results.update(fut.result())
                except Exception as e:
                    logger.warning(f"배치 실패: {e}")

        return all_results


def _split(lst: list, n: int) -> list[list]:
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]


def _process_batch(advertisers: list[str], year: int, month: int,
                   days_in_month: int, headless: bool) -> dict:
    """브라우저 1개 + 페이지 1개를 배치 전체에서 재사용 (goto는 최초 1회만)."""
    results = {}
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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(locale="ko-KR", user_agent=UA)
        page = ctx.new_page()
        page.on("response", on_response)

        # 페이지 최초 1회 로드 (domcontentloaded — networkidle 타임아웃 없음)
        try:
            page.goto(TRANSPARENCY_URL, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_selector("input", timeout=10000)
        except Exception as e:
            logger.warning(f"배치 초기 로드 실패: {e}")
            browser.close()
            return results

        for adv in advertisers:
            try:
                api_data.clear()
                periods = _search_one(page, api_data, adv, year, month, days_in_month)
                if periods:
                    results[adv] = periods
                    logger.info(f"Google {adv}: {periods}")
            except Exception as e:
                logger.debug(f"Google {adv}: {e}")

        browser.close()
    return results


def _search_one(page, api_data: list[bytes], advertiser: str,
                year: int, month: int, days_in_month: int) -> list[dict]:
    """페이지 재사용: 검색창 갱신만으로 다음 광고주 검색."""
    # 검색창 초기화 후 입력 (fill은 기존 텍스트 자동 클리어)
    inp = page.locator("input").first
    inp.fill(advertiser)
    page.wait_for_timeout(900)

    # 드롭다운 항목 클릭
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
        return []

    page.wait_for_timeout(1200)

    body_text = page.inner_text("body")
    if _ad_count(body_text) == 0:
        return []

    periods = _parse_api_responses(api_data, year, month, days_in_month)
    if not periods:
        # 날짜 데이터 없이 광고주만 확인된 경우 → 1일(라이브 확인)만 표시
        periods = [{"s": 1, "e": 1}]

    # 다음 광고주를 위해 검색 홈으로 복귀 (domcontentloaded → 빠름)
    try:
        page.goto(TRANSPARENCY_URL, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_selector("input", timeout=8000)
    except Exception:
        pass

    return periods


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
    # 개별 날짜를 각각 단일 포인트로 반환 (범위 미사용)
    return [{"s": d, "e": d} for d in days]
