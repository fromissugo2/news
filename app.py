import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz
import hashlib
import requests

# 1. 페이지 설정
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 허브")

# 60초마다 화면 자동 갱신
st_autorefresh(interval=60000, key="news_refresh")

# 🔥 중복 방지용 전역 저장소
if "seen_ids" not in st.session_state:
    st.session_state.seen_ids = set()

# --- 비밀번호 설정부 ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔑 접근 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔑 접근 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        st.error("❌ 비밀번호가 틀렸습니다.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ==============================
# 📊 빅테크 SEC 실적 모니터링 (최근 36시간)
# ==============================

BIGTECH_CIKS = {
    "Apple": "0000320193",
    "Microsoft": "0000789019",
    "Tesla": "0001318605",
    "NVIDIA": "0001045810",
    "AMD": "0000002488",
    "Meta": "0001326801",
    "Alphabet": "0001652044"
}

HEADERS = {
    "User-Agent": "GlobalTechNews your@email.com"
}

@st.cache_data(ttl=60)
def get_bigtech_earnings():
    news_list = []
    kst = pytz.timezone('Asia/Seoul')
    now_utc = datetime.now(pytz.utc)

    for company, cik in BIGTECH_CIKS.items():
        try:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = r.json()

            filings = data["filings"]["recent"]
            df = pd.DataFrame(filings)
            df = df[df["form"].isin(["8-K", "10-Q", "10-K"])]

            for _, row in df.head(5).iterrows():
                filing_date = pd.to_datetime(row["filingDate"], utc=True)

                # 최근 36시간 기준
                if (now_utc - filing_date).total_seconds() > 129600:
                    continue

                accession = row["accessionNumber"].replace("-", "")
                primary_doc = row["primaryDocument"]

                filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_doc}"
                title = f"{company} {row['form']} Filing"

                item_id = hashlib.md5((company + row["accessionNumber"]).encode()).hexdigest()[:12]

                if item_id in st.session_state.seen_ids:
                    continue
                st.session_state.seen_ids.add(item_id)

                news_list.append({
                    "id": item_id,
                    "category": "📊 빅테크 실적 (SEC)",
                    "time": filing_date.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": title,
                    "link": filing_url,
                    "source": "SEC EDGAR",
                    "dt": filing_date
                })
        except:
            continue

    return sorted(news_list, key=lambda x: x['dt'], reverse=True)

# ==============================
# 2. 카테고리 정의
# ==============================

CATEGORIES = {
    "⭐ 초속보 (Direct)": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=2000&keywords=technology",
        "https://9to5mac.com/feed/",
        "https://www.reutersagency.com/feed/?best-topics=technology&post_type=best",
        "https://www.zdnet.com/news/rss.xml"
    ],
    "📺 CNBC (Tech/Stock)": "CNBC_TECH_FILTER",
    "📈 CNBC 금리": "site:cnbc.com (Federal Reserve OR Fed OR FOMC OR 'interest rate' OR 'rate cut' OR 'rate hike' OR inflation OR CPI OR PCE OR 'Treasury yield' OR 'bond yield' OR Powell)",
    "AI/NVIDIA": "NVIDIA OR NVDA OR 'Artificial Intelligence' OR Blackwell",
    "반도체": "Semiconductor OR Chips OR TSMC OR ASML OR AVGO OR AMD OR SAMSUNG OR SK HYNIX",
    "테슬라/머스크": "Tesla OR TSLA OR 'Elon Musk' OR Optimus",
    "빅테크": "Apple OR Microsoft OR Google OR Meta",
    "전력 인프라": "Data Center Energy OR Vertiv OR VRT OR NextEra",
    "로보틱스": "Robot OR Robotics OR Humanoid OR 'AI Robot' OR Automation OR Boston Dynamics OR Figure AI OR Optimus",
    "📊 빅테크 실적 (SEC)": "SEC_EARNINGS"
}

@st.cache_data(ttl=60)
def get_news_feed(category_name, source):
    news_list = []
    kst = pytz.timezone('Asia/Seoul')
    now_utc = datetime.now(pytz.utc)

    # 🔥 SEC 실적 분기
    if source == "SEC_EARNINGS":
        return get_bigtech_earnings()

    # RSS 직접 수신
    if isinstance(source, list):
        for url in source:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                try:
                    if hasattr(entry, 'published_parsed'):
                        dt_utc = datetime(*entry.published_parsed[:6], tzinfo=pytz.utc)
                    else:
                        dt_utc = pd.to_datetime(entry.published, utc=True)

                    if (now_utc - dt_utc).total_seconds() > 21600:
                        continue

                    title = entry.title
                    item_id = hashlib.md5(title.encode()).hexdigest()[:12]

                    if item_id in st.session_state.seen_ids:
                        continue
                    st.session_state.seen_ids.add(item_id)

                    news_list.append({
                        "id": item_id,
                        "category": category_name,
                        "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                        "title": title,
                        "link": entry.link,
                        "source": urllib.parse.urlparse(url).netloc.replace('www.', ''),
                        "dt": dt_utc
                    })
                except:
                    continue

    # CNBC 전용 RSS
    elif source == "CNBC_TECH_FILTER":
        cnbc_tech_url = "https://www.cnbc.com/id/19854910/device/rss/rss.html"
        feed = feedparser.parse(cnbc_tech_url)

        for entry in feed.entries[:40]:
            try:
                dt_utc = pd.to_datetime(entry.published, utc=True)
                if (now_utc - dt_utc).total_seconds() > 172800:
                    continue

                title = entry.title
                item_id = hashlib.md5(title.encode()).hexdigest()[:12]

                if item_id in st.session_state.seen_ids:
                    continue
                st.session_state.seen_ids.add(item_id)

                news_list.append({
                    "id": item_id,
                    "category": category_name,
                    "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": title,
                    "link": entry.link,
                    "source": "CNBC (Official)",
                    "dt": dt_utc
                })
            except:
                continue

    # Google News 검색
    else:
        encoded_query = urllib.parse.quote(f"{source} when:1h")
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)

        for entry in feed.entries[:30]:
            try:
                dt_utc = pd.to_datetime(entry.published, utc=True)
                if (now_utc - dt_utc).total_seconds() > 3600:
                    continue

                full_title = entry.title
                title_part = full_title.rsplit(' - ', 1)[0] if ' - ' in full_title else full_title
                source_part = entry.source.title if hasattr(entry, 'source') else "Google News"

                item_id = hashlib.md5(title_part.encode()).hexdigest()[:12]

                if item_id in st.session_state.seen_ids:
                    continue
                st.session_state.seen_ids.add(item_id)

                news_list.append({
                    "id": item_id,
                    "category": category_name,
                    "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": title_part,
                    "link": entry.link,
                    "source": source_part,
                    "dt": dt_utc
                })
            except:
                continue

    return sorted(news_list, key=lambda x: x['dt'], reverse=True)

# ==============================
# UI 출력
# ==============================

st.info("💡 '📊 빅테크 실적' 탭은 최근 36시간 기준 SEC 공시를 1분마다 모니터링합니다.")

tabs = st.tabs(list(CATEGORIES.keys()))
st.session_state.seen_ids = set()

for tab_idx, (tab, (cat_name, source)) in enumerate(zip(tabs, CATEGORIES.items())):
    with tab:
        news_data = get_news_feed(cat_name, source)
        now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')

        if news_data:
            df = pd.DataFrame(news_data)
            st.caption(f"🔥 현재 **{len(df)}개**의 최신 뉴스가 수집되었습니다. (마지막 갱신: {now_kst})")

            for i, (_, row) in enumerate(df.iterrows()):
                widget_key = f"copy_{tab_idx}_{i}_{row['id']}"

                with st.container():
                    col1, col2 = st.columns([3, 1.2])

                    with col1:
                        st.markdown(f"### {row['title']}")
                        st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
                        st.link_button(f"📄 {row['source']} 원문 기사 보기", row['link'])

                    with col2:
                        prompt_text = (
                            f"출처가 '{row['source']}'인 '{row['title']}' 기사를 찾아서 다음 순서로 답해줘:\n\n"
                            f"1. **기사 전문 번역 및 상세 요약**\n"
                            f"   - 기사 전체 내용을 한국어로 정확하게 번역\n"
                            f"   - 핵심 내용을 놓침 없이 자세하게 요약\n\n"
                            f"2. **국외(글로벌) 주식 시장 연관성**\n"
                            f"   - 해당 소식으로 영향을 받는 미국 등 해외 주요 종목과 섹터 분석\n\n"
                            f"3. **국내 주식 시장 연관성**\n"
                            f"   - 국내 시장에서도 영향이 있을지 여부와 구체적인 이유\n"
                            f"   - 연관된 국내 주식 종목(수혜주/피해주)과 관련 테마(예: HBM, 자율주행 등)\n\n"
                            f"4. **투자자 관점의 최종 결론**\n"
                            f"   - 이 기사가 시장에 주는 시그널 요약 및 투자 매력도 분석"
                        )

                        st.text_area("명령어 복사 (Ctrl+C)", value=prompt_text, height=150, key=widget_key)

                        st.link_button("🤖 Gemini 열기", "https://gemini.google.com/app", type="primary", use_container_width=True)
                        st.link_button("🤖 ChatGPT 열기", "https://chat.openai.com/", use_container_width=True)

                    st.divider()
        else:
            st.warning(f"현재 '{cat_name}' 카테고리에 최신 뉴스가 없습니다.")
