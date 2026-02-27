import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz
import hashlib

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
    """비밀번호가 맞으면 True, 아니면 False를 반환합니다."""
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

# 2. 카테고리 정의
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

    # 🔥 새로 추가된 금리 전용 카테고리
    "📈 CNBC 금리": "site:cnbc.com (Federal Reserve OR Fed OR FOMC OR 'interest rate' OR 'rate cut' OR 'rate hike' OR inflation OR CPI OR PCE OR 'Treasury yield' OR 'bond yield' OR Powell)",

    "AI/NVIDIA": "NVIDIA OR NVDA OR 'Artificial Intelligence' OR Blackwell",
    "반도체": "Semiconductor OR Chips OR TSMC OR ASML OR AVGO OR AMD OR SAMSUNG OR SK HYNIX",
    "테슬라/머스크": "Tesla OR TSLA OR 'Elon Musk' OR Optimus",
    "빅테크": "Apple OR Microsoft OR Google OR Meta",
    "전력 인프라": "Data Center Energy OR Vertiv OR VRT OR NextEra",
    "로보틱스": "Robot OR Robotics OR Humanoid OR 'AI Robot' OR Automation OR Boston Dynamics OR Figure AI OR Optimus"
}

@st.cache_data(ttl=60)
def get_news_feed(category_name, source):
    news_list = []
    kst = pytz.timezone('Asia/Seoul')
    now_utc = datetime.now(pytz.utc)

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

    elif source == "CNBC_TECH_FILTER":
        cnbc_tech_url = "https://www.cnbc.com/id/19854910/device/rss/rss.html"
        feed = feedparser.parse(cnbc_tech_url)

        for entry in feed.entries[:40]:
            try:
                title = entry.title
                dt_utc = pd.to_datetime(entry.published, utc=True)

                if (now_utc - dt_utc).total_seconds() > 172800:
                    continue

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

st.info("💡 **이용 가이드**: '초속보'와 'CNBC' 탭은 RSS를 직접 수신하며, 나머지는 Google 검색 1시간 이내 기사입니다.")

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
                            f"2. **국외(글로벌) 주식 시장 연관성**\n"
                            f"3. **국내 주식 시장 연관성**\n"
                            f"4. **투자자 관점의 최종 결론**"
                        )

                        st.text_area("명령어 복사 (Ctrl+C)", value=prompt_text, height=150, key=widget_key)

                        st.link_button("🤖 Gemini 열기", "https://gemini.google.com/app", type="primary", use_container_width=True)
                        st.link_button("🤖 ChatGPT 열기", "https://chat.openai.com/", use_container_width=True)

                    st.divider()
        else:
            st.warning(f"현재 '{cat_name}' 카테고리에 최신 뉴스가 없습니다.")
