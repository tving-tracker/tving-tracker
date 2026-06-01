import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="TVING 광고주 매체 집행 트래커",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 상수 ──────────────────────────────────────────────────────────────────────

POD_COLORS = {
    "Pod 1": "#E5072A",
    "Pod 2": "#00A8CC",
    "Pod 3": "#FF8C00",
    "Pod 4": "#28A745",
    "Pod 5": "#9B59B6",
}

POD_DESC = {
    "Pod 1": "가전·소비재·보험·통신",
    "Pod 2": "커머스·헬스케어·홈리빙",
    "Pod 3": "게임·주류·미디어·여행",
    "Pod 4": "식음료·푸드·뷰티",
    "Pod 5": "금융·자동차·패션",
}

VERT_KO = {
    "Consumer Electronics": "가전제품",
    "Consumer Goods": "소비재",
    "Finance_Insurance": "보험",
    "Telecom": "통신",
    "Commerce/Platform": "커머스/플랫폼",
    "Corporate": "기업광고",
    "Health/Medical": "헬스케어",
    "Home/Living": "홈리빙",
    "Game": "게임",
    "Alcohol": "주류",
    "Media/Entertainment": "미디어/엔터",
    "Travel": "여행",
    "Beverage": "음료",
    "Food Franchise": "외식프랜차이즈",
    "Food": "식품",
    "Beauty": "뷰티",
    "Finance_Bank/Card": "은행/카드",
    "Fintech/Investment": "핀테크/투자",
    "Auto": "자동차",
    "Fashion": "패션/스포츠",
}

# ── 데이터 ────────────────────────────────────────────────────────────────────

_RAW = [
    # Pod 1 — 가전·소비재·보험·통신
    ("삼성전자_한국총괄",        960058824, "Pod 1", "Consumer Electronics"),
    ("한국존슨앤드존슨",         335294118, "Pod 1", "Consumer Goods"),
    ("삼성생명보험",             300000000, "Pod 1", "Finance_Insurance"),
    ("애플",                    287205882, "Pod 1", "Consumer Electronics"),
    ("엘지유플러스(LG유플러스)", 230000000, "Pod 1", "Telecom"),
    ("디비손해보험(DB손해보험)", 191764706, "Pod 1", "Finance_Insurance"),
    ("쓰리에이치(3H)",          142264706, "Pod 1", "Consumer Electronics"),
    ("브리타코리아",             125620000, "Pod 1", "Consumer Goods"),
    ("엘지전자(LG전자)",        105882353, "Pod 1", "Consumer Electronics"),
    ("필립스코리아",              67873302, "Pod 1", "Consumer Goods"),
    ("케이비손해보험(KB손해보험)", 61764706, "Pod 1", "Finance_Insurance"),
    ("유한킴벌리",               60000000, "Pod 1", "Consumer Goods"),
    ("다이슨",                   30000000, "Pod 1", "Consumer Electronics"),
    ("현대해상",                 20000000, "Pod 1", "Finance_Insurance"),
    ("케이티(KT)",               16666667, "Pod 1", "Telecom"),
    ("악사손해보험(AXA손해보험)", 10000000, "Pod 1", "Finance_Insurance"),
    ("한화생명보험",             10000000, "Pod 1", "Finance_Insurance"),
    ("LG전자",                         0, "Pod 1", "Consumer Electronics"),
    ("도루코",                         0, "Pod 1", "Consumer Goods"),
    ("라이나생명",                     0, "Pod 1", "Finance_Insurance"),
    ("삼성전자",                       0, "Pod 1", "Consumer Electronics"),
    ("삼성화재",                       0, "Pod 1", "Finance_Insurance"),
    ("신한라이프",                     0, "Pod 1", "Finance_Insurance"),
    ("애경산업",                       0, "Pod 1", "Consumer Goods"),
    ("에스케이텔레콤(SK텔레콤)",       0, "Pod 1", "Telecom"),
    ("에이비엘생명보험",               0, "Pod 1", "Finance_Insurance"),
    ("유니레버코리아",                 0, "Pod 1", "Consumer Goods"),
    ("케이비손해보험(kb손해보험)",      0, "Pod 1", "Finance_Insurance"),
    ("코스모앤컴퍼니",                 0, "Pod 1", "Consumer Electronics"),
    ("팅크웨어모바일",                 0, "Pod 1", "Consumer Electronics"),
    ("한국프리드라이프",               0, "Pod 1", "Finance_Insurance"),
    ("한국피앤지",                     0, "Pod 1", "Consumer Goods"),
    ("켄뷰코리아(Kenvue Korea)",       0, "Pod 1", "Consumer Goods"),
    # Pod 2 — 커머스·헬스케어·홈리빙
    ("올리브영",                510000000, "Pod 2", "Commerce/Platform"),
    ("신세계",                  391929825, "Pod 2", "Commerce/Platform"),
    ("지마켓",                  105000000, "Pod 2", "Commerce/Platform"),
    ("네이버",                          0, "Pod 2", "Commerce/Platform"),
    ("롯데쇼핑",                        0, "Pod 2", "Commerce/Platform"),
    ("아정네트웍스",                    0, "Pod 2", "Commerce/Platform"),
    ("우아한형제들",                    0, "Pod 2", "Commerce/Platform"),
    ("이마트",                          0, "Pod 2", "Commerce/Platform"),
    ("잡코리아",                        0, "Pod 2", "Commerce/Platform"),
    ("쿠팡",                            0, "Pod 2", "Commerce/Platform"),
    ("세방그룹",                        0, "Pod 2", "Corporate"),
    ("지에스건설(GS건설)",              0, "Pod 2", "Corporate"),
    ("포스코",                          0, "Pod 2", "Corporate"),
    ("한라그룹(HL그룹)",               0, "Pod 2", "Corporate"),
    ("현대엘리베이터",                  0, "Pod 2", "Corporate"),
    ("파마리서치",              331764706, "Pod 2", "Health/Medical"),
    ("한국오츠카제약",          131764706, "Pod 2", "Health/Medical"),
    ("대상웰라이프",             70000000, "Pod 2", "Health/Medical"),
    ("유한양행",                 70000000, "Pod 2", "Health/Medical"),
    ("동화약품",                 61764706, "Pod 2", "Health/Medical"),
    ("바이엘코리아",             60000000, "Pod 2", "Health/Medical"),
    ("광동제약",                 50000000, "Pod 2", "Health/Medical"),
    ("한국엠에스디(한국MSD)",    50000000, "Pod 2", "Health/Medical"),
    ("한국인삼공사",             50000000, "Pod 2", "Health/Medical"),
    ("쎌바이오텍",               33152174, "Pod 2", "Health/Medical"),
    ("바임글로벌",               30000000, "Pod 2", "Health/Medical"),
    ("동국제약",                        0, "Pod 2", "Health/Medical"),
    ("동아제약",                        0, "Pod 2", "Health/Medical"),
    ("멀츠아시아퍼시픽피티이엘티디",    0, "Pod 2", "Health/Medical"),
    ("삼양사",                          0, "Pod 2", "Health/Medical"),
    ("삼진제약",                        0, "Pod 2", "Health/Medical"),
    ("에이스바이옴",                    0, "Pod 2", "Health/Medical"),
    ("지엔엠라이프(GNM라이프)",         0, "Pod 2", "Health/Medical"),
    ("한국알콘",                        0, "Pod 2", "Health/Medical"),
    ("헤일리온코리아",                  0, "Pod 2", "Health/Medical"),
    ("한샘",                   200000000, "Pod 2", "Home/Living"),
    ("일룸",                   120000000, "Pod 2", "Home/Living"),
    ("경동나비엔",               95000000, "Pod 2", "Home/Living"),
    ("코웨이",                   50000000, "Pod 2", "Home/Living"),
    ("귀뚜라미보일러",                  0, "Pod 2", "Home/Living"),
    ("세라젬",                          0, "Pod 2", "Home/Living"),
    ("세스코",                          0, "Pod 2", "Home/Living"),
    ("에이스침대",                      0, "Pod 2", "Home/Living"),
    ("엘엑스홀딩스(LX홀딩스)",         0, "Pod 2", "Home/Living"),
    ("자코모",                          0, "Pod 2", "Home/Living"),
    ("청호나이스",                      0, "Pod 2", "Home/Living"),
    ("퍼시스",                          0, "Pod 2", "Home/Living"),
    # Pod 3 — 게임·주류·미디어·여행
    ("컴투스",                 520588235, "Pod 3", "Game"),
    ("OB맥주",                 500000000, "Pod 3", "Alcohol"),
    ("바이트댄스",             460000000, "Pod 3", "Media/Entertainment"),
    ("오비맥주(OB맥주)",       352941176, "Pod 3", "Alcohol"),
    ("하이트진로음료",         326823529, "Pod 3", "Alcohol"),
    ("익스피디아그룹",         181764706, "Pod 3", "Travel"),
    ("넷마블",                 141764706, "Pod 3", "Game"),
    ("에어비앤비코리아",       117647059, "Pod 3", "Travel"),
    ("구글코리아",              61764706, "Pod 3", "Media/Entertainment"),
    ("한국닌텐도",              40000000, "Pod 3", "Game"),
    ("디아지오코리아",          30000000, "Pod 3", "Alcohol"),
    ("구글",                           0, "Pod 3", "Media/Entertainment"),
    ("넥슨코리아",                     0, "Pod 3", "Game"),
    ("놀(NOL)",                        0, "Pod 3", "Travel"),
    ("빔산토리코리아",                 0, "Pod 3", "Alcohol"),
    ("스마일게이트",                   0, "Pod 3", "Game"),
    ("스포티파이코리아",               0, "Pod 3", "Media/Entertainment"),
    ("엔씨소프트(Ncsoft)",             0, "Pod 3", "Game"),
    ("여기어때",                       0, "Pod 3", "Travel"),
    ("웹젠",                           0, "Pod 3", "Game"),
    ("위메이드",                       0, "Pod 3", "Game"),
    ("켄바",                           0, "Pod 3", "Media/Entertainment"),
    ("트립닷컴",                       0, "Pod 3", "Travel"),
    ("하나투어",                       0, "Pod 3", "Travel"),
    ("해긴",                           0, "Pod 3", "Game"),
    ("호텔스컴바인",                   0, "Pod 3", "Travel"),
    # Pod 4 — 식음료·푸드·뷰티
    ("롯데칠성음료",           460000000, "Pod 4", "Beverage"),
    ("다이닝브랜즈그룹",       290000000, "Pod 4", "Food Franchise"),
    ("한국맥도날드",           180217723, "Pod 4", "Food Franchise"),
    ("파파존스",               142264706, "Pod 4", "Food Franchise"),
    ("티젠",                   141764706, "Pod 4", "Beverage"),
    ("빙그레",                 131764706, "Pod 4", "Beverage"),
    ("한국코카콜라",           124705882, "Pod 4", "Beverage"),
    ("제스프리인터내셔날코리아", 117647058, "Pod 4", "Food"),
    ("에이치케이이노엔(HK이노엔)", 100000000, "Pod 4", "Beauty"),
    ("지앤푸드",               100000000, "Pod 4", "Food Franchise"),
    ("써브웨이",                73928571, "Pod 4", "Food Franchise"),
    ("동서식품",                70000000, "Pod 4", "Beverage"),
    ("동서음료",                70000000, "Pod 4", "Beverage"),
    ("동아오츠카",              70000000, "Pod 4", "Beverage"),
    ("아이더스에프앤비",        70000000, "Pod 4", "Food Franchise"),
    ("비케이알(BKR)",           61764706, "Pod 4", "Food Franchise"),
    ("아모레퍼시픽",            32571429, "Pod 4", "Beauty"),
    ("롯데지알에스",            30000000, "Pod 4", "Food Franchise"),
    ("웅진식품",                30000000, "Pod 4", "Beverage"),
    ("롯데아사히주류",          15000000, "Pod 4", "Beverage"),
    ("노모어에프앤비",                 0, "Pod 4", "Food Franchise"),
    ("대상홀딩스",                     0, "Pod 4", "Food"),
    ("동원산업",                       0, "Pod 4", "Food"),
    ("롯데웰푸드",                     0, "Pod 4", "Food"),
    ("롯데지알에스(롯데GRS)",          0, "Pod 4", "Food Franchise"),
    ("멕시카나",                       0, "Pod 4", "Food Franchise"),
    ("바비톡",                         0, "Pod 4", "Beauty"),
    ("삼양그룹",                       0, "Pod 4", "Food"),
    ("삼양식품",                       0, "Pod 4", "Food"),
    ("샤넬코리아",                     0, "Pod 4", "Beauty"),
    ("씨제이제일제당(CJ제일제당)",     0, "Pod 4", "Food"),
    ("아워홈",                         0, "Pod 4", "Food"),
    ("에스씨케이컴퍼니",               0, "Pod 4", "Food Franchise"),
    ("에이피알",                       0, "Pod 4", "Beauty"),
    ("에치와이(HY)",                   0, "Pod 4", "Beverage"),
    ("엘브이엠에치코스메틱스",         0, "Pod 4", "Beauty"),
    ("엘카코리아(ELCA)",               0, "Pod 4", "Beauty"),
    ("올데이프레쉬",                   0, "Pod 4", "Food Franchise"),
    ("청오디피케이",                   0, "Pod 4", "Food Franchise"),
    ("클리오",                         0, "Pod 4", "Beauty"),
    ("팔도",                           0, "Pod 4", "Food"),
    ("풀무원",                         0, "Pod 4", "Food"),
    ("퓨젠바이오",                     0, "Pod 4", "Beauty"),
    ("한국마즈",                       0, "Pod 4", "Food"),
    ("한국청정음료",                   0, "Pod 4", "Beverage"),
    ("한국하겐다즈",                   0, "Pod 4", "Food"),
    # Pod 5 — 금융·자동차·패션
    ("엠지새마을금고(MG새마을금고)", 472320261, "Pod 5", "Finance_Bank/Card"),
    ("자비스앤빌런즈",          410000000, "Pod 5", "Fintech/Investment"),
    ("브이아이피자산운용",      246764706, "Pod 5", "Fintech/Investment"),
    ("한국타이어",              170000000, "Pod 5", "Auto"),
    ("르노코리아",              151764706, "Pod 5", "Auto"),
    ("엔에이치투자증권(NH투자증권)", 151764706, "Pod 5", "Fintech/Investment"),
    ("한국토요타자동차",        142264706, "Pod 5", "Auto"),
    ("언더아머코리아",          131764706, "Pod 5", "Fashion"),
    ("볼보코리아",              130000000, "Pod 5", "Auto"),
    ("아이더",                  100000000, "Pod 5", "Fashion"),
    ("금호타이어",               91764706, "Pod 5", "Auto"),
    ("미래에셋증권",             90000000, "Pod 5", "Fintech/Investment"),
    ("해빗팩토리",               80000000, "Pod 5", "Fintech/Investment"),
    ("엔에이치아문디자산운용",   70000000, "Pod 5", "Finance_Bank/Card"),
    ("비와이엔블랙야크",         61764706, "Pod 5", "Fashion"),
    ("아디다스코리아",           58823530, "Pod 5", "Fashion"),
    ("신한금융지주",             53333333, "Pod 5", "Fintech/Investment"),
    ("스텔란티스코리아",         30000000, "Pod 5", "Auto"),
    ("현대자동차",               30000000, "Pod 5", "Auto"),
    ("기아",                     17307692, "Pod 5", "Auto"),
    ("비와이디코리아(BYD)",      10000000, "Pod 5", "Auto"),
    ("신한카드",                 10000000, "Pod 5", "Finance_Bank/Card"),
    ("나이키코리아",                    0, "Pod 5", "Fashion"),
    ("더케이커넥트",                    0, "Pod 5", "Fashion"),
    ("롯데카드",                        0, "Pod 5", "Finance_Bank/Card"),
    ("비엠더블유코리아(BMW)",           0, "Pod 5", "Auto"),
    ("비자코리아",                      0, "Pod 5", "Finance_Bank/Card"),
    ("삼성카드",                        0, "Pod 5", "Finance_Bank/Card"),
    ("신용협동조합",                    0, "Pod 5", "Finance_Bank/Card"),
    ("신한은행",                        0, "Pod 5", "Finance_Bank/Card"),
    ("아이엠뱅크",                      0, "Pod 5", "Finance_Bank/Card"),
    ("에스비아이저축은행(SBI저축은행)", 0, "Pod 5", "Finance_Bank/Card"),
    ("엔에이치농협은행(NH농협은행)",    0, "Pod 5", "Finance_Bank/Card"),
    ("엔카닷컴",                        0, "Pod 5", "Auto"),
    ("오케이저축은행",                  0, "Pod 5", "Finance_Bank/Card"),
    ("우리금융지주",                    0, "Pod 5", "Finance_Bank/Card"),
    ("재규어랜드로버",                  0, "Pod 5", "Auto"),
    ("케이비캐피탈(KB캐피탈)",         0, "Pod 5", "Fintech/Investment"),
    ("코오롱스포츠",                    0, "Pod 5", "Fashion"),
    ("키움증권",                        0, "Pod 5", "Fintech/Investment"),
    ("토스",                            0, "Pod 5", "Fintech/Investment"),
    ("티머니",                          0, "Pod 5", "Fintech/Investment"),
    ("폭스바겐그룹코리아",              0, "Pod 5", "Auto"),
    ("폴스타",                          0, "Pod 5", "Auto"),
    ("피알앤디컴퍼니",                  0, "Pod 5", "Auto"),
    ("현대카드",                        0, "Pod 5", "Finance_Bank/Card"),
    ("케이비증권(KB증권)",              0, "Pod 5", "Finance_Bank/Card"),
]


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

@st.cache_data
def load_df():
    df = pd.DataFrame(_RAW, columns=["광고주", "예산", "Pod", "vertical"])
    df["버티컬"] = df["vertical"].map(VERT_KO).fillna(df["vertical"])
    df["상태"] = df["예산"].apply(lambda x: "집행확정" if x > 0 else "미집행")
    df["예산_억"] = df["예산"] / 1e8
    return df


def fmt(n: int) -> str:
    if n >= 1e8:
        return f"₩{n/1e8:.1f}억"
    if n >= 1e4:
        return f"₩{int(n/1e4):,}만"
    if n > 0:
        return f"₩{n:,}"
    return "—"


def badge(pod: str) -> str:
    c = POD_COLORS.get(pod, "#888")
    return f"<span style='background:{c};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700'>{pod}</span>"


# ── 앱 시작 ───────────────────────────────────────────────────────────────────

df = load_df()

# ── 사이드바 ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📺 TVING")
    st.markdown("### 광고주 매체 집행 트래커")
    st.divider()

    sel_pods = st.multiselect(
        "Pod 선택",
        options=["Pod 1", "Pod 2", "Pod 3", "Pod 4", "Pod 5"],
        default=["Pod 1", "Pod 2", "Pod 3", "Pod 4", "Pod 5"],
    )

    all_verts = sorted(df["버티컬"].unique().tolist())
    sel_verts = st.multiselect("버티컬 선택", options=all_verts, default=all_verts)

    sel_status = st.radio("집행 상태", ["전체", "집행확정", "미집행"], horizontal=True)
    search = st.text_input("🔍 광고주 검색", placeholder="이름 입력...")

    st.divider()
    st.caption("Pod 구성")
    for pod, desc in POD_DESC.items():
        c = POD_COLORS[pod]
        st.markdown(
            f"<span style='color:{c};font-size:18px'>●</span> **{pod}** — {desc}",
            unsafe_allow_html=True,
        )

# ── 필터 ───────────────────────────────────────────────────────────────────────
fdf = df.copy()
if sel_pods:
    fdf = fdf[fdf["Pod"].isin(sel_pods)]
if sel_verts:
    fdf = fdf[fdf["버티컬"].isin(sel_verts)]
if sel_status != "전체":
    fdf = fdf[fdf["상태"] == sel_status]
if search:
    fdf = fdf[fdf["광고주"].str.contains(search, case=False, na=False)]

# ── KPI ────────────────────────────────────────────────────────────────────────
total_budget = fdf["예산"].sum()
active_cnt = int((fdf["예산"] > 0).sum())
total_cnt = len(fdf)
exec_rate = active_cnt / total_cnt * 100 if total_cnt > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("총 집행예산", fmt(total_budget))
c2.metric("집행확정 광고주", f"{active_cnt}개사")
c3.metric("전체 광고주", f"{total_cnt}개사")
c4.metric("집행률", f"{exec_rate:.0f}%")

st.divider()

# ── 탭 ─────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 전체 현황", "📦 Pod별 현황", "📋 광고주 목록", "🔍 버티컬 분석"]
)

# ── Tab 1: 전체 현황 ───────────────────────────────────────────────────────────
with tab1:
    if fdf.empty:
        st.info("조건에 맞는 데이터가 없습니다.")
    else:
        col_l, col_r = st.columns(2)

        with col_l:
            pod_sum = (
                fdf.groupby("Pod")["예산_억"]
                .sum()
                .reindex(["Pod 1", "Pod 2", "Pod 3", "Pod 4", "Pod 5"])
                .dropna()
                .reset_index()
            )
            pod_sum.columns = ["Pod", "예산_억"]
            pod_sum["label"] = pod_sum["예산_억"].apply(lambda x: f"₩{x:.1f}억")

            fig = px.bar(
                pod_sum,
                x="예산_억",
                y="Pod",
                orientation="h",
                color="Pod",
                color_discrete_map=POD_COLORS,
                text="label",
                title="Pod별 집행 예산 합계",
                labels={"예산_억": "예산 (억원)", "Pod": ""},
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#FAFAFA",
                showlegend=False,
                height=320,
                margin=dict(l=0, r=60, t=40, b=0),
                title_font_size=14,
            )
            fig.update_traces(textposition="outside", marker_line_width=0)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            vert_sum = (
                fdf[fdf["예산"] > 0]
                .groupby("버티컬")["예산_억"]
                .sum()
                .reset_index()
                .sort_values("예산_억", ascending=False)
            )
            fig2 = px.treemap(
                vert_sum,
                path=["버티컬"],
                values="예산_억",
                title="버티컬별 예산 비중",
                color="예산_억",
                color_continuous_scale=["#1A1A2E", "#E5072A"],
                hover_data={"예산_억": ":.1f"},
            )
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#FAFAFA",
                height=320,
                margin=dict(l=0, r=0, t=40, b=0),
                title_font_size=14,
                coloraxis_showscale=False,
            )
            fig2.update_traces(
                texttemplate="<b>%{label}</b><br>₩%{value:.1f}억",
                hovertemplate="%{label}<br>₩%{value:.1f}억<extra></extra>",
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### Pod별 요약")
        cols = st.columns(5)
        for i, pod in enumerate(["Pod 1", "Pod 2", "Pod 3", "Pod 4", "Pod 5"]):
            if pod not in sel_pods:
                continue
            sub = fdf[fdf["Pod"] == pod]
            total = sub["예산"].sum()
            ac = int((sub["예산"] > 0).sum())
            tc = len(sub)
            color = POD_COLORS[pod]
            with cols[i]:
                st.markdown(
                    f"""
                    <div style="border-left:4px solid {color};padding:10px 14px;
                    background:#1A1A1A;border-radius:4px;margin-bottom:8px">
                    <div style="font-size:13px;color:{color};font-weight:700">{pod}</div>
                    <div style="font-size:11px;color:#aaa">{POD_DESC[pod]}</div>
                    <div style="font-size:20px;font-weight:700;margin-top:6px">{fmt(total)}</div>
                    <div style="font-size:12px;color:#ccc">{ac}/{tc}개사 집행</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ── Tab 2: Pod별 현황 ──────────────────────────────────────────────────────────
with tab2:
    for pod in ["Pod 1", "Pod 2", "Pod 3", "Pod 4", "Pod 5"]:
        if pod not in sel_pods:
            continue
        sub = fdf[fdf["Pod"] == pod]
        pod_total = sub["예산"].sum()
        pod_active = int((sub["예산"] > 0).sum())
        pod_total_cnt = len(sub)
        color = POD_COLORS[pod]

        header = (
            f"**{pod}** &nbsp;—&nbsp; {POD_DESC[pod]} &nbsp;|&nbsp; "
            f"집행확정 **{pod_active}개사** &nbsp;|&nbsp; 합계 **{fmt(pod_total)}**"
        )
        with st.expander(header, expanded=True):
            ca, cb = st.columns([3, 2])

            with ca:
                top = (
                    sub[sub["예산"] > 0]
                    .sort_values("예산", ascending=True)
                    .tail(12)
                )
                if not top.empty:
                    top["label"] = top["예산"].apply(fmt)
                    fig = px.bar(
                        top,
                        x="예산_억",
                        y="광고주",
                        orientation="h",
                        color="버티컬",
                        text="label",
                        labels={"예산_억": "억원", "광고주": ""},
                        title=f"{pod} 집행확정 광고주",
                    )
                    fig.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#FAFAFA",
                        height=max(300, len(top) * 32),
                        showlegend=True,
                        legend=dict(orientation="h", y=-0.15, font_size=11),
                        margin=dict(l=0, r=60, t=40, b=40),
                        title_font_size=13,
                    )
                    fig.update_traces(textposition="outside", marker_line_width=0)
                    fig.update_xaxes(showgrid=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("집행확정 광고주가 없습니다.")

            with cb:
                vert_tbl = (
                    sub.groupby("버티컬")
                    .agg(예산합계=("예산", "sum"), 전체=("광고주", "count"),
                         집행확정=("상태", lambda x: (x == "집행확정").sum()))
                    .reset_index()
                    .sort_values("예산합계", ascending=False)
                )
                vert_tbl["예산합계"] = vert_tbl["예산합계"].apply(fmt)
                vert_tbl["집행률"] = (
                    vert_tbl["집행확정"] / vert_tbl["전체"] * 100
                ).round(0).astype(int).astype(str) + "%"
                st.caption("버티컬별 현황")
                st.dataframe(vert_tbl, hide_index=True, use_container_width=True)


# ── Tab 3: 광고주 목록 ─────────────────────────────────────────────────────────
with tab3:
    disp = fdf[["광고주", "Pod", "버티컬", "예산", "상태"]].copy()
    disp = disp.sort_values(["Pod", "예산"], ascending=[True, False])
    disp["집행예산"] = disp["예산"].apply(fmt)
    disp = disp.drop(columns=["예산"]).rename(columns={"집행예산": "집행예산"})

    st.dataframe(
        disp,
        hide_index=True,
        use_container_width=True,
        height=580,
        column_config={
            "Pod": st.column_config.TextColumn("Pod", width="small"),
            "상태": st.column_config.TextColumn("상태", width="small"),
            "집행예산": st.column_config.TextColumn("집행예산", width="medium"),
        },
    )

    csv_bytes = (
        disp.to_csv(index=False, encoding="utf-8-sig")
        .encode("utf-8-sig")
    )
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv_bytes,
        file_name="tving_advertiser_tracker.csv",
        mime="text/csv",
    )


# ── Tab 4: 버티컬 분석 ─────────────────────────────────────────────────────────
with tab4:
    if fdf.empty:
        st.info("조건에 맞는 데이터가 없습니다.")
    else:
        vert_agg = (
            fdf.groupby("버티컬")
            .agg(
                예산합계=("예산", "sum"),
                전체=("광고주", "count"),
                집행확정=("상태", lambda x: (x == "집행확정").sum()),
            )
            .reset_index()
            .sort_values("예산합계", ascending=False)
        )
        vert_agg["예산_억"] = vert_agg["예산합계"] / 1e8
        vert_agg["집행률"] = (vert_agg["집행확정"] / vert_agg["전체"] * 100).round(1)

        col_l, col_r = st.columns([3, 2])

        with col_l:
            fig = px.bar(
                vert_agg,
                x="버티컬",
                y="예산_억",
                color="예산_억",
                color_continuous_scale=["#1a1a2e", "#E5072A"],
                text=vert_agg["예산_억"].apply(lambda x: f"₩{x:.1f}억" if x > 0 else ""),
                title="버티컬별 집행 예산",
                labels={"예산_억": "예산 (억원)", "버티컬": ""},
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#FAFAFA",
                xaxis_tickangle=45,
                height=450,
                showlegend=False,
                coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=40, b=120),
                title_font_size=14,
            )
            fig.update_traces(textposition="outside", marker_line_width=0)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(showgrid=True, gridcolor="#2a2a2a")
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            tbl = vert_agg[["버티컬", "예산_억", "전체", "집행확정", "집행률"]].copy()
            tbl["예산_억"] = tbl["예산_억"].round(1)
            tbl.columns = ["버티컬", "예산(억)", "전체", "집행확정", "집행률(%)"]
            st.caption("버티컬 집계표")
            st.dataframe(
                tbl,
                hide_index=True,
                use_container_width=True,
                height=450,
            )

        st.divider()
        st.markdown("#### 버티컬 × Pod 크로스 분석")
        pivot = (
            fdf.pivot_table(
                values="예산_억",
                index="버티컬",
                columns="Pod",
                aggfunc="sum",
                fill_value=0,
            )
            .round(1)
        )
        pivot.columns.name = None
        st.dataframe(pivot, use_container_width=True)
