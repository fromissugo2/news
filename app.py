import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz
import google.generativeai as genai

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 & AI 번역")

# 1분마다 페이지 자동 새로고침 (실시간성 유지)
st_autorefresh(interval=60000, key="news_refresh")

# 2. Gemini API 설정 (Streamlit Secrets에서 호출)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 최신 모델명 사용 (gemini-1.5-flash 또는 gemini-2.0-flash)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Gemini 초기화 실패: {e}")
else:
    st.warning("⚠️ Streamlit Secrets에 GEMINI_API_KEY를 등록해주세요. 현재 번역 기능이 제한됩니다.")

# 3. 뉴스 카테고리 및 검색어 설정
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}

# 4. 핵심 기능: Gemini 번역 (한도 초과 핸들링 포함)
def translate_with_gemini(title, summary):
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ API 키가 설정되지 않았습니다."
    
    try:
        prompt = f"당신은 경제/테크 전문 번역가입니다. 아래 영어 뉴스 제목과 요약을 문맥에 맞게 한글로 번역해주세요:\n\n제목: {title}\n요약: {summary}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # 한도 초과(429) 에러 집중 핸들링
        error_msg = str(e)
        if "429" in error_msg or "ResourceExhausted" in error_msg:
            return "⚠️ [한도 초과] 현재 무료 번역 요청이 많습니다. 1분 뒤에 다시 시도해주세요."
        elif "NotFound" in error_msg:
            return "⚠️ [모델 에러] 모델 이름을 찾을 수 없습니다. 코드를 확인하세요."
        else:
            return f"⚠️ [오류] {error_msg}"

# 5. 핵심 기능: RSS 뉴스 수집 (시간대/인코딩 해결)
def get_news_feed(category_name, query):
    # 특수문자 및 공백 인코딩 해결
    encoded_query = urllib.parse.quote(f"{query} when:1h")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    feed = feedparser.parse(url)
    news_list = []
    kst = pytz.timezone('Asia/Seoul') # 한국 시간대 설정
    
    if hasattr(feed, 'entries'):
        for entry in feed.entries[:8]: # 카테고리당 최대 8개
            try:
                # 시간 변환: UTC -> KST
                dt_utc = pd.to_datetime(entry.published, utc=True)
                dt_kst = dt_utc.astimezone(kst)
                
                news_list.append({
                    "category": category_name,
                    "time": dt_kst.strftime('%m/%d %H:%M'),
                    "title": entry.title,
                    "link": entry.link,
                    "source": entry.source.title if hasattr(entry, 'source') else "News",
                    "summary": entry.summary if hasattr(entry, 'summary') else "",
                    "dt": dt_kst # 정렬용
                })
            except:
                continue
    return news_list

# 6. 메인 로직: 뉴스 수집 및 출력
all_news = []
for cat_name, query in CATEGORIES.items():
    cat_news = get_news_feed(cat_name, query)
    if cat_news:
        all_news.extend(cat_news)

if all_news:
    # 중복 제거 및 시간순 정렬
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    
    st.subheader(f"📍 마지막 업데이트: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')} (한국 시간)")
    st.divider()

    for i, row in df.iterrows():
        # 디자인: 카테고리별 강조
        cat_tag = f"**<{row['category']}>**"
        
        with st.container():
            col1, col2, col3 = st.columns([4, 0.8, 1])
            with col1:
                st.markdown(f"{cat_tag}  \n[{row['source']}] {row['title']}")
                st.caption(f"🕒 {row['time']}")
            with col2:
                st.link_button("기사 열기", row['link'])
            with col3:
                # 번역 버튼
                if st.button("AI 번역", key=f"btn_{i}"):
                    with st.spinner('Gemini 번역 중...'):
                        result = translate_with_gemini(row['title'], row['summary'])
                        if "⚠️" in result:
                            st.warning(result)
                        else:
                            st.info(f"🤖 **Gemini 번역 결과:**\n\n{result}")
            st.write("") # 간격
else:
    st.info("현재 수집된 새로운 뉴스가 없습니다. 키워드를 변경하거나 잠시 기다려주세요.")
