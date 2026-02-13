import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="Stock News Hub", layout="wide")
st.title("🚀 카테고리별 외신 실시간 허브")

# 1분마다 자동 새로고침
st_autorefresh(interval=60000, key="newscheck")

# 카테고리 정의 (키워드: RSS 쿼리)
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}

def get_category_news(category_name, query):
    # 각 카테고리별 RSS 주소 생성 (최근 1시간 기사)
    url = f"https://news.google.com/rss/search?q={query}+when:1h&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    news_data = []
    
    for entry in feed.entries[:10]: # 카테고리당 최신 10개
        news_data.append({
            "카테고리": category_name,
            "시간": entry.published,
            "제목": entry.title,
            "링크": entry.link,
            "출처": entry.source.title if hasattr(entry, 'source') else "Google News",
            "dt": pd.to_datetime(entry.published) # 정렬용 데이트타임
        })
    return news_data

# 모든 카테고리 뉴스 수집
all_news = []
for cat_name, query in CATEGORIES.items():
    all_news.extend(get_category_news(cat_name, query))

# 데이터프레임 변환 및 시간순 정렬
if all_news:
    df = pd.DataFrame(all_news)
    df = df.sort_values(by="dt", ascending=False) # 최신순 정렬

    st.subheader(f"📍 마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}")
    st.divider()

    for _, row in df.iterrows():
        # 요청하신 형식: <카테고리> [출처] 제목
        display_text = f"<{row['카테고리']}>\n[{row['출처']}] {row['제목']}"
        
        with st.container():
            col1, col2 = st.columns([5, 1])
            with col1:
                # 카테고리별로 색상 강조 (Optional)
                st.info(display_text) if row['카테고리'] == "AI" else st.write(display_text)
                st.caption(f"🕒 {row['시간']}")
            with col2:
                st.link_button("기사 읽기", row['링크'])
            st.write("") # 간격 조절
else:
    st.warning("현재 새로 올라온 뉴스가 없습니다.")
