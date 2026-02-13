import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz
import google.generativeai as genai
import re
from newspaper import Article

# 1. 페이지 설정
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 & AI 제목 번역")

st_autorefresh(interval=60000, key="news_refresh")

# 2. Gemini 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    st.warning("⚠️ Secrets에 API 키를 등록해주세요.")

# 3. 제목 번역 전용 함수 (캐시 적용하여 속도 향상)
@st.cache_data(ttl=3600)
def translate_title(title_text):
    try:
        prompt = f"다음 뉴스 제목을 한국어로 자연스럽게 번역해줘. 결과만 딱 한 줄로 말해줘: {title_text}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return title_text

# 4. 본문 추출 및 분석 함수
@st.cache_data(ttl=3600)
def get_full_article_translation(url, fallback_summary):
    try:
        article = Article(url, language='en')
        article.download()
        article.parse()
        full_text = article.text
        
        if full_text and len(full_text) > 200:
            prompt = (
                f"당신은 테크/경제 전문 번역가입니다. 아래 기사 전문을 한국어로 읽기 쉽게 번역해주세요.\n"
                f"마지막에는 반드시 '### 💡 3줄 핵심 요약' 섹션을 만들어주세요.\n\n"
                f"기사 본문:\n{full_text[:4000]}"
            )
        else:
            prompt = (
                f"본문 크롤링이 제한되어 요약본을 분석합니다. 내용을 한국어로 상세히 풀어서 설명해 주세요.\n\n요약 정보:\n{fallback_summary}"
            )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 분석 중 오류 발생: {str(e)}"

# 5. 새 창(Dialog) 정의
@st.dialog("📋 AI 상세 분석 리포트", width="large")
def show_full_translation(translated_title, original_title, url, summary):
    st.markdown(f"### {translated_title}")
    st.caption(f"Original: {original_title}")
    st.caption(f"🔗 원문: {url}")
    st.divider()
    
    with st.container(height=600): 
        with st.spinner('AI가 기사 내용을 심층 분석 중입니다...'):
            result = get_full_article_translation(url, f"제목: {original_title}\n요약: {summary}")
            st.markdown(result)
    
    if st.button("닫기"):
        st.rerun()

# 6. 뉴스 수집 로직
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
        for entry in feed.entries[:6]: # 속도를 위해 카테고리당 6개로 조정
            try:
                dt_utc = pd.to_datetime(entry.published, utc=True)
                news_list.append({
                    "category": category_name,
                    "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.summary,
                    "source": entry.source.title if hasattr(entry, 'source') else "News",
                    "dt": dt_utc
                })
            except: continue
    return news_list

# 7. 메인 출력 화면
all_news = []
for cat_name, query in CATEGORIES.items():
    all_news.extend(get_news_feed(cat_name, query))

if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    
    st.subheader(f"📍 업데이트: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')} (KST)")
    st.divider()

    for i, row in df.iterrows():
        # 메인 화면 제목 번역
        with st.spinner('제목 번역 중...'):
            korean_title = translate_title(row['title'])
            
        with st.container():
            col1, col2, col3 = st.columns([4, 0.8, 1])
            with col1:
                # 번역된 제목을 크게, 원문 제목을 작게 표시
                st.markdown(f"**<{row['category']}> {korean_title}**")
                st.caption(f"[{row['source']}] {row['title']}")
                st.caption(f"🕒 {row['time']}")
            with col2:
                st.link_button("원본", row['link'])
            with col3:
                if st.button("AI 분석", key=f"btn_{i}"):
                    show_full_translation(korean_title, row['title'], row['link'], row['summary'])
            st.divider()
else:
    st.info("현재 새로운 뉴스가 없습니다.")
