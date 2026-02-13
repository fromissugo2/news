import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz
import google.generativeai as genai

# 1. Gemini 설정 (Secrets에서 키 가져오기)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash') # 속도가 빠른 flash 모델 추천
except:
    st.error("Gemini API 키 설정이 필요합니다.")

# 페이지 설정
st.set_page_config(page_title="Stock News Hub", layout="wide")
st.title("🚀 AI 기반 외신 실시간 허브")

st_autorefresh(interval=60000, key="newscheck")

# 카테고리 설정
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}

# 번역 함수 정의
def translate_with_gemini(text):
    prompt = f"당신은 전문 경제 번역가입니다. 다음 영문 뉴스 제목과 요약을 한국어로 매끄럽게 번역해주세요. 전문 용어는 문맥에 맞게 번역하세요: \n\n{text}"
    response = model.generate_content(prompt)
    return response.text

def get_category_news(category_name, query):
    encoded_query = urllib.parse.quote(f"{query} when:1h")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    news_data = []
    kst = pytz.timezone('Asia/Seoul')
    
    if hasattr(feed, 'entries'):
        for entry in feed.entries[:8]:
            dt_utc = pd.to_datetime(entry.published)
            dt_kst = dt_utc.astimezone(kst)
            news_data.append({
                "카테고리": category_name,
                "한국시간": dt_kst.strftime('%m/%d %H:%M'),
                "제목": entry.title,
                "링크": entry.link,
                "출처": entry.source.title if hasattr(entry, 'source') else "Google News",
                "요약": entry.summary, # 번역용 요약 데이터
                "dt": dt_kst
            })
    return news_data

# 뉴스 수집 및 출력
all_news = []
for cat_name, query in CATEGORIES.items():
    try:
        all_news.extend(get_category_news(cat_name, query))
    except Exception as e:
        st.error(f"{cat_name} 수집 오류")

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
                st.link_button("기사 열기", row['リンク'])
            with col3:
                # 고유 키를 위해 인덱스(i) 사용
                if st.button("Gemini 번역", key=f"btn_{i}"):
                    with st.spinner('Gemini가 번역 중...'):
                        translated_text = translate_with_gemini(f"제목: {row['제목']}\n요약: {row['요약']}")
                        st.info(f"**🤖 Gemini 번역 결과:**\n\n{translated_text}")
            st.divider()
