import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz
import google.generativeai as genai
import re  # HTML 태그 제거를 위한 정규표현식 라이브러리

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 & AI 번역")

# 1분마다 페이지 자동 새로고침
st_autorefresh(interval=60000, key="news_refresh")

# 2. Gemini API 설정
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 가장 안정적인 최신 별칭(Alias) 사용
        model = genai.GenerativeModel('gemini-flash-latest')
    except Exception as e:
        st.error(f"Gemini 초기화 실패: {e}")
else:
    st.warning("⚠️ Streamlit Secrets에 GEMINI_API_KEY를 등록해주세요.")

# 3. 뉴스 카테고리 설정
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}

# 4. 핵심 기능: Gemini 번역 (HTML 제거 및 한도 핸들링)
def translate_with_gemini(title, summary):
    try:
        # 요약 데이터에서 <...>, &nbsp; 등 HTML 태그 및 특수문자 제거
        clean_summary = re.sub('<[^<]+?>', '', summary)
        clean_summary = clean_summary.replace('&nbsp;', ' ').strip()
        
        prompt = (
            f"당신은 전문 경제/테크 번역가입니다. 아래 뉴스 제목과 요약을 "
            f"매끄러운 한국어로 번역하고, 주요 맥락(Context)을 한 줄 덧붙여주세요.\n\n"
            f"제목: {title}\n요약: {clean_summary}"
        )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "ResourceExhausted" in error_msg:
            return "⚠️ [한도 초과] 현재 요청이 많습니다. 1분 뒤 다시 시도해주세요."
        return f"⚠️ [번역 오류] {error_msg}"

# 5. 핵심 기능: RSS 뉴스 수집
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
                dt_kst = dt_utc.astimezone(kst)
                
                news_list.append({
                    "category": category_name,
                    "time": dt_kst.strftime('%m/%d %H:%M'),
                    "title": entry.title,
                    "link": entry.link,
                    "source": entry.source.title if hasattr(entry, 'source') else "News",
                    "summary": entry.summary if hasattr(entry, 'summary') else "",
                    "dt": dt_kst
                })
            except:
                continue
    return news_list

# 6. 메인 출력부
all_news = []
for cat_name, query in CATEGORIES.items():
    cat_news = get_news_feed(cat_name, query)
    if cat_news:
        all_news.extend(cat_news)

if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    
    st.subheader(f"📍 업데이트: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')} (KST)")
    st.divider()

    for i, row in df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([4, 0.8, 1])
            with col1:
                st.markdown(f"**<{row['category']}>** \n[{row['source']}] {row['title']}")
                st.caption(f"🕒 {row['time']}")
            with col2:
                st.link_button("원본 기사", row['link'])
            with col3:
                if st.button("AI 번역 & 요약", key=f"btn_{i}"):
                    with st.spinner('Gemini 분석 중...'):
                        result = translate_with_gemini(row['title'], row['summary'])
                        if "⚠️" in result:
                            st.warning(result)
                        else:
                            st.info(f"🤖 **AI 번역 결과:**\n\n{result}")
            st.write("") 
else:
    st.info("현재 새로운 뉴스가 없습니다. 1분 뒤 자동 갱신됩니다.")
