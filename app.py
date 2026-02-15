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
            del st.session_state["password"]  # 보안을 위해 세션에서 비밀번호 삭제
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 비밀번호 입력창 표시
        st.text_input("🔑 접근 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # 비밀번호가 틀렸을 때
        st.text_input("🔑 접근 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        st.error("❌ 비밀번호가 틀렸습니다.")
        return False
    else:
        # 비밀번호가 맞았을 때
        return True

# 비밀번호 체크 실행
if not check_password():
    st.stop()  # 비밀번호가 맞기 전까지 아래 코드를 실행하지 않음

# 2. 카테고리 정의 (CNBC 전용 카테고리 추가)
CATEGORIES = {
    "⭐ 초속보 (Direct)": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=2000&keywords=technology",
        "https://9to5mac.com/feed/",
        "https://www.reutersagency.com/feed/?best-topics=technology&post_type=best",
        "https://www.zdnet.com/news/rss.xml"
    ],
    "📺 CNBC (Tech/Stock)": "CNBC_TECH_FILTER", # CNBC 전용 필터 예약어
    "AI/NVIDIA": "NVIDIA OR NVDA OR 'Artificial Intelligence' OR Blackwell",
    "반도체": "Semiconductor OR Chips OR TSMC OR ASML OR AVGO",
    "테슬라/머스크": "Tesla OR TSLA OR 'Elon Musk' OR Optimus",
    "빅테크": "Apple OR Microsoft OR Google OR Meta",
    "전력 인프라": "Data Center Energy OR Vertiv OR VRT OR NextEra",
    "로보틱스": "Robot OR Robotics OR Humanoid OR 'AI Robot' OR Automation OR Boston Dynamics OR Figure AI OR Optimus"
}

# 3. 뉴스 수집 함수
@st.cache_data(ttl=60)
def get_news_feed(category_name, source):
    news_list = []
    kst = pytz.timezone('Asia/Seoul')
    now_utc = datetime.now(pytz.utc)

    # --- Case 1: 직접 RSS 피드 (초속보 리스트) ---
    if isinstance(source, list):
        for url in source:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                try:
                    if hasattr(entry, 'published_parsed'):
                        dt_utc = datetime(*entry.published_parsed[:6], tzinfo=pytz.utc)
                    else:
                        dt_utc = pd.to_datetime(entry.published, utc=True)
                    
                    if (now_utc - dt_utc).total_seconds() > 21600: # 6시간
                        continue
                    
                    title = entry.title
                    item_id = hashlib.md5(title.encode()).hexdigest()[:12]
                    
                    if item_id in st.session_state.seen_ids: continue
                    st.session_state.seen_ids.add(item_id)

                    news_list.append({
                        "id": item_id, "category": category_name,
                        "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                        "title": title, "link": entry.link,
                        "source": urllib.parse.urlparse(url).netloc.replace('www.', ''),
                        "dt": dt_utc
                    })
                except: continue

   # --- Case 2: CNBC 전용 필터 수집 (보강 버전) ---
    elif source == "CNBC_TECH_FILTER":
        cnbc_rss_url = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=2000&keywords=technology"
        feed = feedparser.parse(cnbc_rss_url)
        
        # 필터링 키워드 대폭 확장 (더 많은 뉴스 포착)
        tech_keywords = [
            "Tesla", "Musk", "Nvidia", "AI", "Apple", "Microsoft", "Google", "Meta", "Amazon", 
            "Semiconductor", "Chip", "OpenAI", "Blackwell", "SpaceX", "EV", "Earnings", "Fed", "Rate",
            "Broadcom", "TSMC", "ASML", "Intelligence", "Computing", "Software"
        ]
        
        for entry in feed.entries[:50]: # 더 많은 기사를 훑어봅니다.
            try:
                title = entry.title
                # 대소문자 구분 없이 키워드 매칭
                if not any(kw.lower() in title.lower() for kw in tech_keywords):
                    continue
                    
                dt_utc = pd.to_datetime(entry.published, utc=True)
                # 24시간(86400초) 이내 기사까지 허용하여 공백기 방지
                if (now_utc - dt_utc).total_seconds() > 86400:
                    continue

                item_id = hashlib.md5(title.encode()).hexdigest()[:12]
                if item_id in st.session_state.seen_ids: continue
                st.session_state.seen_ids.add(item_id)

                news_list.append({
                    "id": item_id, "category": category_name,
                    "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": title, "link": entry.link,
                    "source": "CNBC", "dt": dt_utc
                })
            except: continue

    # --- Case 3: Google News 검색 ---
    else:
        encoded_query = urllib.parse.quote(f"{source} when:1h")
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)
        for entry in feed.entries[:30]:
            try:
                dt_utc = pd.to_datetime(entry.published, utc=True)
                if (now_utc - dt_utc).total_seconds() > 3600: continue

                full_title = entry.title
                title_part = full_title.rsplit(' - ', 1)[0] if ' - ' in full_title else full_title
                source_part = entry.source.title if hasattr(entry, 'source') else "Google News"
                item_id = hashlib.md5(title_part.encode()).hexdigest()[:12]

                if item_id in st.session_state.seen_ids: continue
                st.session_state.seen_ids.add(item_id)

                news_list.append({
                    "id": item_id, "category": category_name,
                    "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": title_part, "link": entry.link,
                    "source": source_part, "dt": dt_utc
                })
            except: continue

    return sorted(news_list, key=lambda x: x['dt'], reverse=True)

# 4. 상단 공통 안내
st.info("💡 **이용 가이드**: '초속보'와 'CNBC' 탭은 RSS를 직접 수신하며, 나머지는 Google 검색 1시간 이내 기사입니다.")

# 5. 상단 탭 구성
tabs = st.tabs(list(CATEGORIES.keys()))

# 🔥 새로고침 시 중복 초기화
st.session_state.seen_ids = set()

# 6. 각 탭별 뉴스 출력 루프
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
                    st.divider()
        else:
            st.warning(f"현재 '{cat_name}' 카테고리에 최신 뉴스가 없습니다.")
