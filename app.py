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

st_autorefresh(interval=60000, key="news_refresh")

# 2. 카테고리 정의
CATEGORIES = {
    "AI": "AI OR Artificial Intelligence",
    "반도체": "Semiconductor OR Chips",
    "엔비디아": "NVIDIA OR NVDA",
    "테슬라": "Tesla OR TSLA",
    "일론 머스크": '"Elon Musk"'
    "AI/NVIDIA": "NVIDIA OR NVDA OR Blackwell",
    "빅테크": "Tesla OR Apple OR Microsoft OR Google",
    "전력 인프라": "Data Center Energy OR Vertiv OR VRT",
    "반도체": "Broadcom OR AVGO OR TSMC",
    "로보틱스": "Humanoid Robot OR Tesla Optimus OR Figure AI"
}

# 3. 뉴스 수집 함수 (가장 기본적이고 빠른 RSS 수집)
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
                # 제목에서 출처( - Source) 부분 분리
                full_title = entry.title
                title_part = full_title.rsplit(' - ', 1)[0] if ' - ' in full_title else full_title
                source_part = entry.source.title if hasattr(entry, 'source') else "News Source"
                
                news_list.append({
                    "category": category_name,
                    "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": title_part,
                    "google_link": entry.link,
                    "source": source_part,
                    "dt": dt_utc
                })
            except: continue
    return news_list

# 4. 뉴스 실행 및 출력
all_news = []
for cat_name, query in CATEGORIES.items():
    all_news.extend(get_news_feed(cat_name, query))

if all_news:
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    
    st.info("✅ 'Gemini 열기' 클릭 시, 해당 기사를 Gemini가 직접 찾아 번역하도록 명령어가 자동 구성됩니다.")

    for i, row in df.iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1.2])
            
            with col1:
                st.markdown(f"### <{row['category']}> {row['title']}")
                st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
                # 원문 보기는 구글 링크를 그대로 쓰되, 새 탭에서 열리도록 함
                st.link_button("📄 원문 기사 직접 보기", row['google_link'])
            
            with col2:
                # [해결책] 링크 대신 '제목'과 '출처'를 조합해 Gemini에게 던집니다.
                # 이렇게 하면 Gemini가 자신의 검색 능력을 사용해 정확한 기사를 찾아내어 번역합니다.
                prompt_text = f"출처가 '{row['source']}'인 '{row['title']}' 기사를 찾아서 한국어로 전문 번역하고 자세히 요약해줘."
                
                st.text_area("명령어 복사 (Ctrl+C)", value=prompt_text, height=90, key=f"copy_{i}")
                st.link_button("🤖 Gemini 열기", "https://gemini.google.com/app", type="primary", use_container_width=True)
            
            st.divider()
