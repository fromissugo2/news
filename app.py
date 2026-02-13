import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz
import requests
from googlenewsdecoder import decoderv2

# 1. 페이지 설정
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 허브 (최종 보완)")

st_autorefresh(interval=60000, key="news_refresh")

# 2. [종합] 진짜 URL을 찾아내는 2단계 추적 함수
@st.cache_data(ttl=3600)
def get_final_real_url(google_url):
    try:
        # 1단계: 전용 디코더 시도
        decoded = decoderv2(google_url)
        real_url = decoded['decoded_url']
        
        # 2단계: 만약 디코딩된 주소가 여전히 google.com을 포함한다면 직접 헤더 추적
        if "news.google.com" in real_url:
            response = requests.head(real_url, allow_redirects=True, timeout=5)
            real_url = response.url
            
        return real_url
    except:
        try:
            # 3단계: 모든 시도 실패 시 직접 접속하여 최종 URL 확인
            response = requests.get(google_url, timeout=5)
            return response.url
        except:
            return google_url

# 3. 뉴스 카테고리 정의
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}

# 4. 뉴스 수집 및 출력 로직
def get_news_feed(category_name, query):
    encoded_query = urllib.parse.quote(f"{query} when:1h")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    news_list = []
    kst = pytz.timezone('Asia/Seoul')
    
    if hasattr(feed, 'entries'):
        for entry in feed.entries[:8]:
            try:
                dt_utc = pd.to_datetime(entry.published, utc=True)
                news_list.append({
                    "category": category_name,
                    "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": entry.title,
                    "google_link": entry.link,
                    "source": entry.source.title if hasattr(entry, 'source') else "News",
                    "dt": dt_utc
                })
            except: continue
    return news_list

# 뉴스 수집 실행
all_news = []
for cat_name, query in CATEGORIES.items():
    all_news.extend(get_news_feed(cat_name, query))

# 메인 화면 출력
if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    st.info("💡 명령어 박스의 주소와 '원문 보기' 주소가 일치하도록 정밀 추적 중입니다.")

    for i, row in df.iterrows():
        # 정밀 추적 실행
        final_url = get_final_real_url(row['google_link'])
        
        with st.container():
            col1, col2 = st.columns([3, 1.2])
            with col1:
                st.markdown(f"### <{row['category']}> {row['title']}")
                st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
                # 버튼에 최종 확인된 진짜 주소 연결
                st.link_button("📄 원문 기사 직접 보기", final_url)
            
            with col2:
                # Gemini 명령어에도 동일한 최종 주소 삽입
                prompt_text = f"이 뉴스 기사 한국어로 번역하고 자세히 요약해줘: {final_url}"
                st.text_area("명령어 복사 (Ctrl+C)", value=prompt_text, height=90, key=f"copy_{i}")
                st.link_button("🤖 Gemini 열기", "https://gemini.google.com/app", type="primary", use_container_width=True)
            st.divider()
