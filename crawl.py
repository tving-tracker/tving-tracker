"""Daily crawl runner.
Usage:
    py crawl.py                  # crawl current month
    py crawl.py --year 2025 --month 6   # crawl specific month (1-indexed)
    py crawl.py --platforms tv,yt       # specific platforms only
"""
import argparse
import logging
import os
from datetime import datetime

import db
from crawlers import TvcfCrawler, GoogleAdsCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("crawl")

# ── Alias 매핑 ────────────────────────────────────────────────────────────────
# TVCF에서 광고주명이 아닌 브랜드/자회사명으로 등록된 경우 추가
# key: ADVERTISERS의 광고주명, value: TVCF에서 검색할 추가 검색어 목록
# 수동으로 확인하면서 계속 추가 필요
ADVERTISER_ALIASES: dict[str, list[str]] = {
    # 그룹/지주 → 브랜드
    '한라그룹':             ['에피트'],
    '세방그룹':             ['세방전지'],
    'LX홀딩스':             ['LX하우시스', 'LX인터내셔널'],
    '지에스건설':           ['자이'],
    '포스코':               ['포스코퓨처엠', 'POSCO'],

    # 통신
    '에스케이텔레콤':       ['SK텔레콤', 'SKT'],
    '케이티':               ['KT'],
    '엘지유플러스':         ['LG유플러스'],

    # 전자/가전
    '삼성전자_한국총괄':    ['삼성전자', '갤럭시'],
    '엘지전자':             ['LG전자'],

    # 자동차
    '현대자동차':           ['현대차', '제네시스'],
    '기아':                 ['기아자동차'],
    'BMW코리아':            ['BMW', 'MINI'],
    '폭스바겐그룹코리아':   ['폭스바겐', '아우디', 'Audi'],
    '스텔란티스코리아':     ['지프', 'Jeep', '푸조', 'Peugeot'],
    '볼보코리아':           ['Volvo', '볼보'],
    '르노코리아':           ['르노'],

    # 유통/커머스
    '롯데쇼핑':             ['롯데마트', '롯데백화점', '롯데온'],
    '신세계':               ['신세계백화점', 'SSG'],

    # 금융
    '신한금융지주':         ['신한'],
    '우리금융지주':         ['우리은행', '우리'],
    'MG새마을금고':         ['새마을금고'],

    # 주류
    '오비맥주':             ['카스', '한맥'],
    'OB맥주':               ['카스', 'OB'],
    '하이트진로음료':       ['하이트', '진로', '테라', '참이슬'],
    '디아지오코리아':       ['조니워커'],
    '빔산토리코리아':       ['짐빔'],

    # 음식료
    '한국코카콜라':         ['코카콜라', '환타'],
    '롯데칠성음료':         ['칠성사이다', '펩시'],
    '동아오츠카':           ['포카리스웨트'],
    '동서식품':             ['맥심', '카누'],
    '씨제이제일제당':       ['CJ제일제당', '비비고', '햇반'],
    '대상홀딩스':           ['청정원', '종가'],
    '롯데웰푸드':           ['빼빼로', '가나초콜릿'],
    '한국마즈':             ['스니커즈', 'm&m'],

    # 프랜차이즈
    '비케이알':             ['버거킹'],
    '롯데지알에스':         ['롯데리아'],
    '아이더스에프앤비':     ['맘스터치'],
    '다이닝브랜즈그룹':     ['TGIF', '아웃백'],

    # 뷰티/생활
    '아모레퍼시픽':         ['설화수', '라네즈', '헤라', '이니스프리'],
    '에이피알':             ['메디큐브', '에이프릴스킨'],
    '클리오':               ['구달', '페리페라'],
    '엘브이엠에치코스메틱스': ['디올뷰티', '겔랑', 'Givenchy'],
    '한국피앤지':           ['페브리즈', '질레트'],
    '유한킴벌리':           ['하기스', '크리넥스'],
    '유니레버코리아':       ['도브'],

    # 제약/건강
    '한국인삼공사':         ['정관장', 'KGC'],
    '대상웰라이프':         ['대상웰라이프', '뉴케어'],

    # 여행
    '익스피디아그룹':       ['익스피디아', 'Expedia', '호텔스닷컴'],
}

# All advertisers tracked
ADVERTISERS = [
    '삼성전자_한국총괄','한국존슨앤드존슨','삼성생명보험','애플','엘지유플러스','디비손해보험',
    '쓰리에이치','브리타코리아','엘지전자','필립스코리아','케이비손해보험','유한킴벌리','다이슨',
    '현대해상','케이티','악사손해보험','한화생명보험','도루코','라이나생명','삼성화재','신한라이프',
    '애경산업','에스케이텔레콤','에이비엘생명보험','유니레버코리아','코스모앤컴퍼니','팅크웨어모바일',
    '한국프리드라이프','한국피앤지','켄뷰코리아',
    '올리브영','신세계','지마켓','네이버','롯데쇼핑','아정네트웍스','우아한형제들','이마트','잡코리아','쿠팡',
    '세방그룹','지에스건설','포스코','한라그룹','현대엘리베이터',
    '파마리서치','한국오츠카제약','대상웰라이프','유한양행','동화약품','바이엘코리아','광동제약',
    '한국MSD','한국인삼공사','쎌바이오텍','바임글로벌','동국제약','동아제약','멀츠아시아퍼시픽',
    '삼양사','삼진제약','에이스바이옴','GNM라이프','한국알콘','헤일리온코리아',
    '한샘','일룸','경동나비엔','코웨이','귀뚜라미보일러','세라젬','세스코','에이스침대',
    'LX홀딩스','자코모','청호나이스','퍼시스',
    '컴투스','OB맥주','바이트댄스','오비맥주','하이트진로음료','익스피디아그룹','넷마블',
    '에어비앤비코리아','구글코리아','한국닌텐도','디아지오코리아','넥슨코리아','빔산토리코리아',
    '스마일게이트','스포티파이코리아','엔씨소프트','여기어때','웹젠','위메이드','켄바',
    '트립닷컴','하나투어','해긴','호텔스컴바인',
    '롯데칠성음료','다이닝브랜즈그룹','한국맥도날드','파파존스','티젠','빙그레','한국코카콜라',
    '제스프리인터내셔날코리아','HK이노엔','지앤푸드','써브웨이','동서식품','동아오츠카',
    '아이더스에프앤비','비케이알','아모레퍼시픽','롯데지알에스','웅진식품','롯데아사히주류',
    '대상홀딩스','롯데웰푸드','멕시카나','삼양식품','씨제이제일제당','에스씨케이컴퍼니',
    '에이피알','엘브이엠에치코스메틱스','엘카코리아','청오디피케이','클리오','풀무원','퓨젠바이오','한국마즈',
    'MG새마을금고','자비스앤빌런즈','브이아이피자산운용','한국타이어','르노코리아','NH투자증권',
    '한국토요타자동차','언더아머코리아','볼보코리아','아이더','금호타이어','미래에셋증권',
    '해빗팩토리','엔에이치아문디자산운용','블랙야크','아디다스코리아','신한금융지주','스텔란티스코리아',
    '현대자동차','기아','BYD코리아','신한카드','나이키코리아','롯데카드','BMW코리아','삼성카드',
    '신한은행','NH농협은행','엔카닷컴','우리금융지주','재규어랜드로버','KB캐피탈','코오롱스포츠',
    '키움증권','토스','폭스바겐그룹코리아','폴스타','현대카드','KB증권',
]


def run_all(year: int = None, month: int = None, platforms: list[str] = None) -> int:
    """Run all crawlers and store results. Returns total period count inserted."""
    now = datetime.now()
    year = year or now.year
    month_1indexed = month or now.month
    month_0indexed = month_1indexed - 1  # JS-style

    platforms = platforms or ["tv", "yt", "meta"]
    db.init_db()

    total = 0
    crawled_at = now.isoformat()

    # ── TV/케이블: TVCF ────────────────────────────────────────────────────────
    if "tv" in platforms:
        logger.info(f"TVCF 크롤링 시작: {year}년 {month_1indexed}월")
        try:
            crawler = TvcfCrawler()
            results = crawler.crawl(ADVERTISERS, year, month_0indexed, aliases=ADVERTISER_ALIASES)
            count = 0
            for adv in ADVERTISERS:
                db.mark_crawled(adv, "tv", year, month_0indexed, crawled_at)
            for adv, periods in results.items():
                db.upsert_periods(adv, "tv", year, month_0indexed, periods, crawled_at)
                count += len(periods)
            db.log_crawl("tv", "ok", count)
            total += count
            logger.info(f"TVCF 완료: {count}건")
        except Exception as e:
            db.log_crawl("tv", "error", message=str(e))
            logger.error(f"TVCF 오류: {e}")

    # ── 유튜브: Google Ads Transparency ───────────────────────────────────────
    if "yt" in platforms:
        logger.info(f"Google Ads 크롤링 시작: {year}년 {month_1indexed}월")
        try:
            crawler = GoogleAdsCrawler()
            results = crawler.crawl(ADVERTISERS, year, month_0indexed)
            count = 0
            for adv in ADVERTISERS:
                db.mark_crawled(adv, "youtube", year, month_0indexed, crawled_at)
            for adv, periods in results.items():
                db.upsert_periods(adv, "youtube", year, month_0indexed, periods, crawled_at)
                count += len(periods)
            db.log_crawl("youtube", "ok", count)
            total += count
            logger.info(f"Google Ads 완료: {count}건")
        except Exception as e:
            db.log_crawl("youtube", "error", message=str(e))
            logger.error(f"Google Ads 오류: {e}")

    logger.info(f"전체 크롤링 완료: {total}건 저장")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TVING 광고 크롤러")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--month", type=int, default=None, help="1-12")
    parser.add_argument("--platforms", type=str, default="tv,yt",
                        help="tv,yt (쉼표 구분)")
    args = parser.parse_args()

    platforms = [p.strip() for p in args.platforms.split(",")]
    run_all(year=args.year, month=args.month, platforms=platforms)
