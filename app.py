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
st.title("📡 실시간 외신 테크 뉴스 & AI 전체 번역")

st_autorefresh(interval=60000, key="news_refresh")

# 2. Gemini 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    st.warning("⚠️ Secrets에 API 키를 등록해주세요.")

# 3. 본문 추출 및 번역 함수 (백업 로직 추가)
def get_full_article_translation(url, fallback_summary):
    try:
        article = Article(url, language='en')
        article.download()
        article.parse()
        full_text = article.text
        
        # 본문 수집 성공 시
        if full_text and len(full_text) > 200:
            prompt = (
                f"당신은 테크/경제 전문 번역가입니다. 아래 기사 전문을 한국어로 읽기 쉽게 번역해주세요.\n"
                f"번역이 끝난 뒤에는 '### 💡 3줄 핵심 요약' 섹션을 만들어 내용을 요약해 주세요.\n\n"
                f"기사 본문:\n{full_text[:4000]}"
            )
        # 본문 수집 실패 시 (RSS 요약 정보 활용)
        else:
            prompt = (
                f"기사 본문 크롤링이 차단되어 요약 정보만 제공합니다. "
                f"아래 제목과 짧은 요약을 바탕으로 어떤 내용의 기사인지 한국어로 설명해주고, "
                f"예상되는 주요 내용을 추론해서 알려주세요.\n\n"
                f"제목 및 요약:\n{fallback_summary}"
            )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 분석 중 오류 발생: {str(e)}"

# 4. 새 창(Dialog) 정의
@st.dialog("AI 기사 상세 분석", width="large")
def show_full_translation(title, url, summary):
    st.write(f"### {title}")
    st.caption(f"🔗 원문 주소: {url}")
    st.divider()
    
    with st.spinner('기사 내용을 분석하는 중입니다...'):
        # 본문 수집 실패를 대비해 RSS 요약(summary)도 함께 전달
        result = get_full_article_translation(url, f"제목: {title}\n요약: {summary}")
        st.markdown(result)

# 5. 뉴스 수집 로직
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
                    "summary": entry.summary, # 백업용 요약 데이터 유지
                    "source": entry.source.title if hasattr(entry, 'source') else "News",
                    "dt": dt_utc
                })
            except: continue
    return news_list

# 6. 메인 출력 화면
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
                # 버튼 클릭 시 제목, 링크, 요약 정보를 모두 다이얼로그로 전달
                if st.button("AI 전체 분석", key=f"btn_{i}"):
                    show_full_translation(row['title'], row['link'], row['summary'])
            st.divider()
