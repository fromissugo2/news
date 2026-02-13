import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz
import google.generativeai as genai

# 페이지 설정
st.set_page_config(page_title="Stock News Hub", layout="wide")
st.title("🚀 AI 기반 외신 실시간 허브")

# 1분마다 자동 새로고침
st_autorefresh(interval=60000, key="newscheck")

# 1. Gemini 설정 (Secrets 확인)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Gemini 연결 실패: {e}")
else:
    st.warning("⚠️ Streamlit Secrets에 GEMINI_API_KEY를 등록해주세요. (번역 기능 비활성화)")

# 카테고리 설정
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}

def get_category_news(category_name, query):
    encoded_query = urllib.parse.quote(f"{query} when:1h")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    news_data = []
    kst = pytz.timezone('Asia/Seoul')
    
    if hasattr(feed, 'entries'):
        for entry in feed.entries[:8]:
            try:
                # 시간 파싱 에러 방지용
                dt_utc = pd.to_datetime(entry.published, utc=True)
                dt_kst = dt_utc.astimezone(kst)
                
                news_data.append({
                    "카테고리": category_name,
                    "한국시간": dt_kst.strftime('%m/%d %H:%M'),
                    "제목": entry.title,
                    "링크": entry.link,
                    "출처": entry.source.title if hasattr(entry, 'source') else "Google News",
                    "요약": entry.summary if hasattr(entry, 'summary') else "",
                    "dt": dt_kst
                })
            except:
                continue # 시간 파싱 실패한 기사는 건너뜀
    return news_data

# 뉴스 수집부
all_news = []
for cat_name, query in CATEGORIES.items():
    res = get_category_news(cat_name, query)
    if res:
        all_news.extend(res)

# 출력부
if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['제목']).sort_values(by="dt", ascending=False)
    st.subheader(f"📍 마지막 업데이트: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')} (KST)")

    for i, row in df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"**<{row['카테고리']}>** \n[{row['출처']}] {row['제목']}")
                st.caption(f"🕒 {row['한국시간']}")
            with col2:
                st.link_button("기사 열기", row['링크'])
            with col3:
                if "GEMINI_API_KEY" in st.secrets:
                    if st.button("Gemini 번역", key=f"btn_{i}"):
                        with st.spinner('번역 중...'):
                            prompt = f"번역해줘: {row['제목']}"
                            response = model.generate_content(prompt)
                            st.info(f"🤖 **번역:** {response.text}")
            st.divider()
else:
    st.info("현재 수집된 뉴스가 없습니다. 1분만 기다려보세요.")
