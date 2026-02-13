import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 허브")

# 1분마다 자동 새로고침
st_autorefresh(interval=60000, key="news_refresh")

# 2. 카테고리 정의
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}

# 3. 뉴스 수집 함수
def get_news_feed(category_name, query):
    encoded_query = urllib.parse.quote(f"{query} when:1h")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    news_list = []
    kst = pytz.timezone('Asia/Seoul')
    
    if hasattr(feed, 'entries'):
        for entry in feed.entries[:10]:
            try:
                dt_utc = pd.to_datetime(entry.published, utc=True)
                news_list.append({
                    "category": category_name,
                    "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": entry.title,
                    "link": entry.link,
                    "source": entry.source.title if hasattr(entry, 'source') else "News",
                    "dt": dt_utc
                })
            except: continue
    return news_list

# 4. 뉴스 수집 실행
all_news = []
for cat_name, query in CATEGORIES.items():
    all_news.extend(get_news_feed(cat_name, query))

# 5. 메인 화면 출력
if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    
    st.subheader(f"📍 마지막 업데이트: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')} (KST)")
    st.info("💡 명령어 박스 내용을 복사한 후 '🤖 Gemini 열기' 버튼을 클릭하세요.")
    st.divider()

    for i, row in df.iterrows():
        with st.container():
            # 비율 조정: 기사 내용(3), 액션 버튼(1)
            col1, col2 = st.columns([3, 1.2])
            
            with col1:
                st.markdown(f"### <{row['category']}> {row['title']}")
                st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
                # 지저분한 URL 대신 깔끔한 버튼 배치
                st.link_button("📄 원문 기사 보기", row['link'])
            
            with col2:
                # 명령어 복사창
                prompt_text = f"이 뉴스 기사 한국어로 번역하고 3줄로 핵심 요약해줘: {row['link']}"
                st.text_area("명령어 (전체 복사하세요)", value=prompt_text, height=90, key=f"copy_{i}")
                
                # Gemini 이동 버튼 (가장 강조)
                st.link_button("🤖 Gemini 열기", "https://gemini.google.com/app", type="primary", use_container_width=True)
            
            st.divider()
else:
    st.info("현재 수집된 뉴스가 없습니다.")
