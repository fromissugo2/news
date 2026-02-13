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
st.title("📡 실시간 외신 테크 뉴스 & AI 전문 분석")

st_autorefresh(interval=60000, key="news_refresh")

# 2. Gemini 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    st.warning("⚠️ Secrets에 API 키를 등록해주세요.")

# 3. 본문 추출 및 번역 함수
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
                f"기사 본문 크롤링이 차단되었습니다. 제공된 요약 정보를 바탕으로 내용을 추론하여 설명해주세요.\n\n"
                f"요약 정보:\n{fallback_summary}"
            )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 분석 중 오류 발생: {str(e)}"

# 4. 뉴스 수집 로직
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
                    "summary": entry.summary,
                    "source": entry.source.title if hasattr(entry, 'source') else "News",
                    "dt": dt_utc
                })
            except: continue
    return news_list

# 5. 메인 출력 화면
all_news = []
for cat_name, query in CATEGORIES.items():
    all_news.extend(get_news_feed(cat_name, query))

if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    
    # 세션 상태 초기화 (번역 결과를 저장하기 위함)
    if 'translations' not in st.session_state:
        st.session_state.translations = {}

    for i, row in df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([4, 0.8, 1])
            with col1:
                st.markdown(f"**<{row['category']}>** \n[{row['source']}] {row['title']}")
                st.caption(f"🕒 {row['time']}")
            with col2:
                st.link_button("원본 보기", row['link'])
            with col3:
                # 버튼을 누르면 해당 인덱스의 번역 요청 상태를 True로 변경
                if st.button("AI 분석 실행", key=f"btn_{i}"):
                    st.session_state.translations[i] = True
            
            # 번역 버튼이 눌렸을 때만 표시되는 영역 (expander 대신 컨테이너 활용)
            if st.session_state.translations.get(i):
                with st.expander("📄 AI 분석 리포트 (클릭하여 열기/닫기)", expanded=True):
                    with st.spinner('기사 내용을 심층 분석 중입니다...'):
                        # 중복 요청 방지를 위해 결과 저장
                        res_key = f"res_{i}"
                        if res_key not in st.session_state:
                            st.session_state[res_key] = get_full_article_translation(row['link'], f"제목: {row['title']}\n요약: {row['summary']}")
                        st.markdown(st.session_state[res_key])
            st.divider()
else:
    st.info("현재 새로운 뉴스가 없습니다.")
