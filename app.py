import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz
import google.generativeai as genai
import re
from newspaper import Article  # 본문 추출용 라이브러리

# 1. 페이지 설정
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 & AI 전체 번역")

st_autorefresh(interval=60000, key="news_refresh")

# 2. Gemini 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    st.warning("⚠️ Secrets에 API 키를 등록해주세요.")

# 3. 본문 추출 및 번역 함수
def get_full_article_translation(url):
    try:
        # 1단계: 기사 본문 크롤링
        article = Article(url)
        article.download()
        article.parse()
        full_text = article.text
        
        if not full_text:
            return "⚠️ 기사 본문을 가져올 수 없습니다. 원문 링크를 확인해주세요."

        # 2단계: Gemini에게 전체 번역 및 요약 요청
        prompt = (
            f"당신은 전문 경제 번역가입니다. 아래 기사 전문을 한국어로 번역하고 마지막에 3줄 요약을 덧붙여주세요.\n\n"
            f"기사 본문:\n{full_text[:3000]}" # 토큰 절약을 위해 앞부분 3000자 제한
        )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 오류 발생: {str(e)}"

# 4. 새 창(Dialog) 정의
@st.dialog("AI 전체 기사 번역", width="large")
def show_full_translation(title, url):
    st.write(f"### {title}")
    st.caption(f"원문 링크: {url}")
    st.divider()
    
    with st.spinner('기사 본문을 읽고 번역 중입니다...'):
        result = get_full_article_translation(url)
        st.markdown(result)

# 5. 뉴스 수집 로직 (기존과 동일)
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}

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
                    "link": entry.link,
                    "source": entry.source.title if hasattr(entry, 'source') else "News",
                    "dt": dt_utc
                })
            except: continue
    return news_list

# 6. 메인 출력부
all_news = []
for cat_name, query in CATEGORIES.items():
    all_news.extend(get_news_feed(cat_name, query))

if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    for i, row in df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([4, 0.8, 1])
            with col1:
                st.markdown(f"**<{row['category']}>** \n[{row['source']}] {row['title']}")
                st.caption(f"🕒 {row['time']}")
            with col2:
                st.link_button("원본 보기", row['link'])
            with col3:
                # 버튼을 누르면 위에서 정의한 st.dialog 실행 (새 창 효과)
                if st.button("AI 전체 번역", key=f"btn_{i}"):
                    show_full_translation(row['title'], row['link'])
            st.divider()
