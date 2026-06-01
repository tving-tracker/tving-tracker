"""4차 진단 - 클릭 선택자 정밀화"""
import re
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

def dump_tvcf_links():
    print("\n== TVCF 검색결과 모든 링크 ==")
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        pg = br.new_context(locale="ko-KR", user_agent=UA).new_page()
        url = "https://tvcf.co.kr/worked/video?search_term=%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90&mediaType_value=1&page=1&rows=50&sort_by=registrated_date&country_code_value=410&lang=ko"
        pg.goto(url, wait_until="networkidle", timeout=20000)
        pg.wait_for_timeout(3000)
        pg.screenshot(path="debug_tvcf_search2.png")

        all_hrefs = pg.eval_on_selector_all(
            "a[href]",
            "els => els.map(e=>({href:e.href,text:e.innerText.trim().slice(0,60)}))"
        )
        print(f"전체 링크 {len(all_hrefs)}개:")
        for l in all_hrefs:
            if l['href'] and 'tvcf' in l['href']:
                print(f"  {l['href']!s:80s} | {l['text']}")

        # 날짜 패턴 탐색
        text = pg.inner_text("body")
        dates = re.findall(r"\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}", text)
        print(f"\n날짜: {dates[:20]}")
        print(f"\n텍스트 앞 2000자:\n{text[:2000]}")
        br.close()


def dump_google_click():
    print("\n== Google Ads: 드롭다운 클릭 선택자 탐색 ==")
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        pg = br.new_context(locale="ko-KR", user_agent=UA).new_page()
        pg.goto("https://adstransparency.google.com/?region=KR",
                wait_until="networkidle", timeout=20000)
        pg.locator("input").first.fill("삼성전자")
        pg.wait_for_timeout(2000)

        # 드롭다운 요소 탐색
        dropdown_items = pg.eval_on_selector_all(
            "[role='option'], [role='listitem'], li, .autocomplete-item, [class*='option'], [class*='result'], [class*='suggestion']",
            "els => els.slice(0,15).map(e=>({tag:e.tagName,role:e.getAttribute('role'),cls:e.className.slice(0,60),text:e.innerText.trim().slice(0,80)}))"
        )
        print("드롭다운 후보 요소:")
        for item in dropdown_items:
            if item['text']:
                print(f"  {item['tag']} role={item['role']} cls={item['cls']}")
                print(f"    text: {item['text']}")

        # 텍스트로 직접 클릭
        try:
            pg.click("text=삼성전자(주)", timeout=3000)
            pg.wait_for_timeout(4000)
            print("\n'text=삼성전자(주)' 클릭 성공!")
            print("URL:", pg.url)
            pg.screenshot(path="debug_google_clicked.png")
            text = pg.inner_text("body")
            dates = re.findall(r"\d{4}[.\-/년]\s*\d{1,2}[.\-/월]?\s*\d{0,2}일?", text)
            print(f"날짜: {dates[:30]}")
            print(f"\n텍스트:\n{text[:2000]}")
        except Exception as e:
            print(f"text 클릭 실패: {e}")
            # nth(0) 시도
            try:
                items = pg.locator("li, [role='option']").all()
                print(f"li/option 요소 수: {len(items)}")
                if items:
                    items[0].click()
                    pg.wait_for_timeout(4000)
                    print("URL:", pg.url)
                    pg.screenshot(path="debug_google_clicked2.png")
            except Exception as e2:
                print(f"li 클릭도 실패: {e2}")

        br.close()


if __name__ == "__main__":
    dump_tvcf_links()
    dump_google_click()
