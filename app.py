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
        model = genai.GenerativeModel('gemini-2.0-flash')
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

# 번역 함수 보완
def translate_with_gemini(text):
    try:
        current_model = genai.GenerativeModel('gemini-2.0-flash') 
        prompt = f"전문 경제 번역가로서 다음 뉴스를 한국어로 번역해줘:\n\n{text}"
        response = current_model.generate_content(prompt)
        return response.text
    except Exception as e:
        # 한도 초과(ResourceExhausted) 에러 처리
        if "429" in str(e) or "ResourceExhausted" in str(e):
            return "⚠️ 현재 Gemini 무료 사용량이 일시적으로 소진되었습니다. 1~2분 후 다시 시도해주세요."
        return f"⚠️ 번역 중 오류 발생: {str(e)}"

# 버튼 클릭 부분 (출력부)
if st.button("Gemini 번역", key=f"btn_{i}"):
    with st.spinner('번역 중...'):
        result = translate_with_gemini(f"제목: {row['제목']}\n요약: {row['요약']}")
        if "⚠️" in result:
            st.warning(result) # 경고 메시지로 표시
        else:
            st.info(f"🤖 **Gemini 번역:**\n\n{result}")
            st.divider()
else:
    st.info("현재 수집된 뉴스가 없습니다. 1분만 기다려보세요.")
