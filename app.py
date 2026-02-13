import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 허브")

# 1분마다 자동 새로고침
st_autorefresh(interval=60000, key="news_refresh")

# 2. 카테고리 사전 정의 (for문 밖에서 선언해야 합니다)
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
}

# 3. 뉴스 수집 함수
def get_news_feed(category_name, query):
    encoded_query = urllib.parse.quote(f"{query} when:1h")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    news_list = []
    kst = pytz.timezone('Asia/Seoul')
    
    if hasattr(feed, 'entries'):
        for entry in feed.entries[:10]:
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

# 4. 뉴스 수집 실행
all_news = []
for cat_name, query in CATEGORIES.items(): # 여기서 SyntaxError가 났던 부분을 수정했습니다.
    all_news.extend(get_news_feed(cat_name, query))

# 5. 메인 화면 출력
if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    
    st.subheader(f"📍 업데이트: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')} (KST)")
    st.info("💡 명령어 박스를 클릭(또는 더블클릭)하여 복사한 후, Gemini 버튼을 눌러 붙여넣으세요!")
    st.divider()

    for i, row in df.iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### <{row['category']}> {row['title']}")
                st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
                # 원문 링크 바로가기 (작게)
                st.caption(f"🔗 원문 주소: {row['link']}")
            
            with col2:
                # 1. 명령어 복사창 (사용자가 바로 복사할 수 있게 구성)
                prompt_text = f"이 뉴스 기사 한국어로 번역하고 자세히 요약해줘: {row['link']}"
                st.text_area("명령어 (복사하세요)", value=prompt_text, height=80, key=f"copy_{i}")
                
                # 2. Gemini 이동 버튼
                st.link_button("🤖 Gemini 열기", "https://gemini.google.com/app", type="primary", use_container_width=True)
            
            st.divider()
else:
    st.info("현재 새로운 뉴스가 없습니다. 키워드를 변경하거나 잠시 기다려주세요.")
