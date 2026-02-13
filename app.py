import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 허브 (Gemini 연결)")

# 1분마다 자동 새로고침 (RSS 업데이트 확인용)
st_autorefresh(interval=60000, key="news_refresh")

# 2. 뉴스 카테고리 설정
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
        for entry in feed.entries[:10]: # API를 안 쓰므로 넉넉하게 10개씩 수집
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

# 4. 메인 실행
all_news = []
for cat_name, query in CATEGORIES.items():
    all_news.extend(get_news_feed(cat_name, query))

if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    
    st.subheader(f"📍 업데이트: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')} (KST)")
    st.info("💡 'AI 번역/요약' 버튼을 누르면 Gemini로 연결됩니다. 원문 링크가 자동 포함됩니다.")
    st.divider()

    for i, row in df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([4, 1, 1.5])
            
            with col1:
                st.markdown(f"**<{row['category']}> {row['title']}**")
                st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
            
            with col2:
                st.link_button("원본 기사 ↗️", row['link'])
            
            with col3:
                # [핵심] Gemini 연결 링크 생성
                # 기사 링크와 함께 번역/요약 요청 메시지를 URL 인코딩하여 전달
                prompt = f"이 기사 링크 읽고 한국어로 전문 번역하고 3줄 요약해줘: {row['link']}"
                encoded_prompt = urllib.parse.quote(prompt)
                gemini_url = f"https://gemini.google.com/app?prompt={encoded_prompt}"
                
                st.link_button("🤖 Gemini 번역/요약", gemini_url, type="primary")
            
            st.divider()
else:
    st.info("현재 새로운 뉴스가 없습니다.")
