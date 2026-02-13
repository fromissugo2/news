import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz
from googlenewsdecoder import decoderv2 # 구글 뉴스 전용 디코더 추가

# 1. 페이지 설정
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 허브")

st_autorefresh(interval=60000, key="news_refresh")

# 2. [완벽 해결] 구글 암호화 링크를 진짜 주소로 디코딩
@st.cache_data(ttl=3600)
def get_real_url(google_url):
    try:
        # 암호화된 구글 RSS 링크를 실제 기사 주소로 복호화합니다.
        decoded = decoderv2(google_url)
        return decoded['decoded_url']
    except Exception as e:
        # 실패 시 차선책으로 원래 링크라도 반환
        return google_url

# 3. 뉴스 카테고리 정의
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}

# 4. 뉴스 수집 함수
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

# 5. 뉴스 수집 및 출력
all_news = []
for cat_name, query in CATEGORIES.items():
    all_news.extend(get_news_feed(cat_name, query))

if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    
    st.subheader(f"📍 마지막 업데이트: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')} (KST)")
    st.success("✅ 이제 '원문 보기'와 'AI 번역' 링크가 100% 일치합니다.")
    st.divider()

    for i, row in df.iterrows():
        # 디코딩 실행 (진짜 URL 추출)
        real_url = get_real_url(row['google_link'])
        
        with st.container():
            col1, col2 = st.columns([3, 1.2])
            
            with col1:
                st.markdown(f"### <{row['category']}> {row['title']}")
                st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
                # 원문 기사 보기 버튼에 진짜 주소 연결
                st.link_button("📄 원문 기사 직접 보기", real_url)
            
            with col2:
                # Gemini 명령어에 진짜 주소 포함
                prompt_text = f"이 뉴스 기사 한국어로 번역하고 자세히 요약해줘: {real_url}"
                st.text_area("명령어 복사 (Ctrl+C)", value=prompt_text, height=90, key=f"copy_{i}")
                
                st.link_button("🤖 Gemini 열기", "https://gemini.google.com/app", type="primary", use_container_width=True)
            
            st.divider()
else:
    st.info("현재 수집된 뉴스가 없습니다.")
