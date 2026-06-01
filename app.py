import json
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

import db

st.set_page_config(
    page_title="TVING · 광고주 매체 집행 트래커",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit chrome so the HTML fills the frame cleanly
st.markdown("""
<style>
#MainMenu, header, footer { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] > div { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar: crawl status + manual refresh ───────────────────────────────────
with st.sidebar:
    st.markdown("## 📺 TVING 트래커")
    st.divider()

    last = db.get_last_crawl()
    if last:
        st.success(f"마지막 업데이트\n**{last}**")
    else:
        st.warning("크롤 데이터 없음\n샘플 데이터로 표시 중")

    if st.button("🔄 지금 크롤링", use_container_width=True):
        with st.spinner("크롤링 중... (1~3분 소요)"):
            try:
                from crawl import run_all
                count = run_all()
                st.success(f"완료: {count}건 저장")
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    st.divider()
    st.caption("크롤링 소스")
    st.markdown("""
- 📺 **TVCF** — TV/케이블
- 🎥 **Google Ads Transparency** — 유튜브
- 📘 **Meta Ad Library** — FB/IG

Meta 크롤링은 `META_ACCESS_TOKEN`
환경변수 설정 필요.
""")
    st.caption("매일 01:00 KST 자동 실행 (GitHub Actions)")


# ── Load data from DB and inject into HTML template ──────────────────────────
periods = db.get_periods()
last_crawled = db.get_last_crawl()

template_path = Path(__file__).parent / "template.html"
html = template_path.read_text(encoding="utf-8")

# Inject real data into the two placeholders
periods_json = json.dumps(periods, ensure_ascii=False)
html = html.replace(
    'const REAL_PERIODS = {}; // __TVING_PERIODS_PLACEHOLDER__',
    f'const REAL_PERIODS = {periods_json};'
)
html = html.replace(
    'const LAST_CRAWLED = ""; // __TVING_LAST_CRAWLED__',
    f'const LAST_CRAWLED = "{last_crawled}";'
)

# Render the full HTML app inside Streamlit
components.html(html, height=920, scrolling=True)
