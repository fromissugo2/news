import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse  # URL 인코딩을 위한 라이브러리 추가

# 페이지 설정
st.set_page_config(page_title="Stock News Hub", layout="wide")
st.title("🚀 카테고리별 외신 실시간 허브")

# 1분마다 자동 새로고침
st_autorefresh(interval=60000, key="newscheck")

# 카테고리 정의
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}

def get_category_news(category_name, query):
    # 중요: 쿼리 내용을 URL 형식에 맞게 인코딩 (공백 -> %20 등)
    encoded_query = urllib.parse.quote(f"{query} when:1h")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    feed = feedparser.parse(url)
    news_data = []
    
    if hasattr(feed, 'entries'):
        for entry in feed.entries[:10]:
            news_data.append({
                "카테고리": category_name,
                "시간": entry.published,
                "제목": entry.title,
                "링크": entry.link,
                "출처": entry.source.title if hasattr(entry, 'source') else "Google News",
                "dt": pd.to_datetime(entry.published)
            })
    return news_data

# 모든 카테고리 뉴스 수집
all_news = []
for cat_name, query in CATEGORIES.items():
    try:
        all_news.extend(get_category_news(cat_name, query))
    except Exception as e:
        st.error(f"{cat_name} 수집 중 오류 발생: {e}")

# 데이터 출력 로직
if all_news:
    df = pd.DataFrame(all_news)
    # 중복 기사 제거 (제목 기준)
    df = df.drop_duplicates(subset=['제목'])
    # 최신순 정렬
    df = df.sort_values(by="dt", ascending=False)

    st.subheader(f"📍 마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}")
    st.divider()

    for _, row in df.iterrows():
        display_text = f"<{row['카테고리']}>\n[{row['출처']}] {row['제목']}"
        
        with st.container():
            col1, col2 = st.columns([5, 1])
            with col1:
                # 카테고리 강조 디자인
                if row['카테고리'] in ["엔비디아", "테슬라"]:
                    st.success(display_text)
                elif row['카테고리'] == "AI":
                    st.info(display_text)
                else:
                    st.write(display_text)
                st.caption(f"🕒 {row['시간']}")
            with col2:
                st.link_button("기사 읽기", row['링크'])
            st.write("") 
else:
    st.warning("현재 새로 올라온 뉴스가 없습니다. 키워드를 확인하거나 잠시만 기다려주세요.")
