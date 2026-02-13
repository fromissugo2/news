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

st_autorefresh(interval=60000, key="news_refresh")

# 2. 뉴스 수집 함수
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

# 3. 메인 실행
all_news = []
for cat_name, query in CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}.items():
    all_news.extend(get_news_feed(cat_name, query))

if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    
    st.subheader(f"📍 업데이트: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')} (KST)")
    st.info("💡 아래 '명령어 복사'를 누른 후 'Gemini 열기' 버튼을 눌러 붙여넣으세요.")
    st.divider()

    for i, row in df.iterrows():
        with st.container():
            col1, col2 = st.columns([4, 2])
            
            with col1:
                st.markdown(f"**<{row['category']}> {row['title']}**")
                st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
            
            with col2:
                # 1. 사용자가 복사하기 편하게 텍스트 박스 제공
                copy_text = f"이 기사 번역하고 3줄 요약해줘: {row['link']}"
                st.text_input("명령어 복사 (Ctrl+C)", value=copy_text, key=f"copy_{i}", label_visibility="collapsed")
                
                # 2. Gemini 이동 버튼
                st.link_button("🤖 Gemini 열기", "https://gemini.google.com/app", type="primary", use_container_width=True)
                
                # 3. 원문 직접 보기
                st.link_button("🔗 원문 기사 링크", row['link'], use_container_width=True)
            
            st.divider()
