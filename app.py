import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="AI & Tech News Hub", layout="wide")
st.title("🚀 실시간 AI/반도체/테슬라 뉴스 허브")

# 2. 60초마다 자동 새로고침 설정 (1분 = 60000ms)
count = st_autorefresh(interval=60000, key="newscheck")

# 3. RSS 주소 설정 (이전 대화에서 만든 쿼리)
RSS_URL = 'https://news.google.com/rss/search?q=AI+OR+Semiconductor+OR+NVIDIA+OR+Tesla+OR+Robot+OR+"Elon+Musk"+when:1h&hl=en-US&gl=US&ceid=US:en'

def get_news():
    feed = feedparser.parse(RSS_URL)
    news_list = []
    for entry in feed.entries:
        news_list.append({
            "시간": entry.published,
            "제목": entry.title,
            "링크": entry.link,
            "출처": entry.source.title if hasattr(entry, 'source') else "Google News"
        })
    return pd.DataFrame(news_list)

# 4. 데이터 로드 및 출력
st.subheader(f"마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}")

df = get_news()

if not df.empty:
    for index, row in df.iterrows():
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"#### [{row['출처']}] {row['제목']}")
                st.caption(f"발행시간: {row['시간']}")
            with col2:
                st.link_button("기사 원문보기", row['링크'])
            st.divider()
else:
    st.info("현재 조건에 맞는 새로운 뉴스가 없습니다.")
