import base64
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import db

# Playwright 브라우저 자동 설치 (Streamlit Cloud 초기 실행 시)
@st.cache_resource(show_spinner=False)
def _install_playwright():
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
        capture_output=True,
    )

_install_playwright()

st.set_page_config(
    page_title="TVING · 광고주 매체 집행 트래커",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
#MainMenu, header, footer { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] > div { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)


def _commit_db_to_github() -> bool:
    """DB를 GitHub API로 커밋. GITHUB_TOKEN 시크릿이 없으면 False 반환."""
    try:
        import requests
        token = st.secrets.get("GITHUB_TOKEN", "")
        if not token:
            return False
        owner = st.secrets.get("GITHUB_OWNER", "tving-tracker")
        repo  = st.secrets.get("GITHUB_REPO",  "tving-tracker")
        url   = f"https://api.github.com/repos/{owner}/{repo}/contents/data/tracker.db"
        hdrs  = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

        with open(db.DB_PATH, "rb") as f:
            content = base64.b64encode(f.read()).decode()

        sha = requests.get(url, headers=hdrs, timeout=10).json().get("sha", "")
        requests.put(url, headers=hdrs, timeout=30, json={
            "message": f"chore: sync crawl {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "content": content,
            "sha": sha,
            "committer": {"name": "TVING Tracker", "email": "tving-tracker@noreply.github.com"},
        })
        return True
    except Exception:
        return False


# ── Sync trigger (query param ?sync=1) ────────────────────────────────────────
if st.query_params.get("sync") == "1":
    st.query_params.clear()
    from crawl import run_all
    with st.status("크롤링 중...", expanded=True) as status:
        try:
            st.write("📺 TVCF (TV/케이블) 크롤링 중...")
            tv_count = run_all(platforms=["tv"])
            st.write(f"TV 완료: {tv_count}건")

            st.write("🎥 Google Ads (유튜브) 크롤링 중... (약 2~3분)")
            yt_count = run_all(platforms=["yt"])
            st.write(f"유튜브 완료: {yt_count}건")

            committed = _commit_db_to_github()
            label = f"완료: {tv_count + yt_count}건 저장" + (" · GitHub 반영됨" if committed else "")
            status.update(label=label, state="complete")
            st.session_state["_sync_msg"] = ("ok", label)
        except Exception as e:
            status.update(label=f"오류: {e}", state="error")
            st.session_state["_sync_msg"] = ("err", f"오류: {e}")
    st.rerun()

sync_message = ""
if "_sync_msg" in st.session_state:
    kind, sync_message = st.session_state.pop("_sync_msg")


# ── Sidebar (정보 표시용) ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📺 TVING 트래커")
    st.divider()
    last = db.get_last_crawl()
    if last:
        st.success(f"마지막 업데이트\n**{last}**")
    else:
        st.warning("크롤 데이터 없음")
    st.divider()
    st.caption("크롤링 소스")
    st.markdown("""
- 📺 **TVCF** — TV/케이블
- 🎥 **Google Ads** — 유튜브
""")
    st.caption("우측 상단 Sync 버튼으로 수동 크롤링")


# ── Load data & render HTML ───────────────────────────────────────────────────
periods      = db.get_periods()
coverage     = db.get_coverage()
last_crawled = db.get_last_crawl()

template_path = Path(__file__).parent / "template.html"
html = template_path.read_text(encoding="utf-8")

html = html.replace(
    'const REAL_PERIODS = {}; // __TVING_PERIODS_PLACEHOLDER__',
    f'const REAL_PERIODS = {json.dumps(periods, ensure_ascii=False)};'
)
html = html.replace(
    'const LAST_CRAWLED = ""; // __TVING_LAST_CRAWLED__',
    f'const LAST_CRAWLED = "{last_crawled}";'
)
html = html.replace(
    'const CRAWL_COVERAGE = {}; // __TVING_COVERAGE_PLACEHOLDER__',
    f'const CRAWL_COVERAGE = {json.dumps(coverage, ensure_ascii=False)};'
)
html = html.replace(
    'const SYNC_MESSAGE = ""; // __TVING_SYNC_MESSAGE__',
    f'const SYNC_MESSAGE = {json.dumps(sync_message)};'
)

components.html(html, height=920, scrolling=True)
