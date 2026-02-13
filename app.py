import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import urllib.parse
import pytz
import hashlib

# 1. 페이지 설정
st.set_page_config(page_title="Tech News Dashboard", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 허브")

# 60초마다 자동 갱신
st_autorefresh(interval=60000, key="news_refresh")

# 2. 카테고리 정의
CATEGORIES = {
    "AI/NVIDIA": "NVIDIA OR NVDA OR 'Artificial Intelligence' OR Blackwell",
    "반도체": "Semiconductor OR Chips OR TSMC OR ASML OR AVGO",
    "테슬라/머스크": "Tesla OR TSLA OR 'Elon Musk' OR Optimus",
    "빅테크": "Apple OR Microsoft OR Google OR Meta",
    "전력 인프라": "Data Center Energy OR Vertiv OR VRT OR NextEra",
    "로보틱스": "Humanoid Robot OR Figure AI OR Boston Dynamics"
}

# 3. 뉴스 수집 함수
def get_news_feed(category_name, query):
    encoded_query = urllib.parse.quote(f"{query} when:1h")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    news_list = []
    kst = pytz.timezone('Asia/Seoul')
    
    if hasattr(feed, 'entries'):
        for entry in feed.entries[:10]: # 탭별로 보여주므로 개수를 조금 늘려도 가독성이 좋습니다.
            try:
                dt_utc = pd.to_datetime(entry.published, utc=True)
                full_title = entry.title
                title_part = full_title.rsplit(' - ', 1)[0] if ' - ' in full_title else full_title
                source_part = entry.source.title if hasattr(entry, 'source') else "News Source"
                item_id = hashlib.md5(title_part.encode()).hexdigest()[:10]
                
                news_list.append({
                    "id": item_id,
                    "category": category_name,
                    "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": title_part,
                    "google_link": entry.link,
                    "source": source_part,
                    "dt": dt_utc
                })
            except: continue
    return news_list

# 4. 탭 생성 (카테고리 이름으로 탭을 만듭니다)
tab_titles = list(CATEGORIES.keys())
tabs = st.tabs(tab_titles)

# 5. 각 탭별로 뉴스 수집 및 출력
for tab, (cat_name, query) in zip(tabs, CATEGORIES.items()):
    with tab:
        news_data = get_news_feed(cat_name, query)
        
        if news_data:
            # 시간순 정렬
            df = pd.DataFrame(news_data).sort_values(by="dt", ascending=False)
            
            st.caption(f"📍 현재 {len(df)}개의 최신 뉴스가 있습니다. (1분 간격 자동 갱신)")
            
            for _, row in df.iterrows():
                # 고유 키 생성
                widget_key = f"area_{row['id']}_{cat_name}"
                
                with st.container():
                    col1, col2 = st.columns([3, 1.2])
                    
                    with col1:
                        st.markdown(f"### {row['title']}")
                        st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
                        st.link_button(f"📄 {row['source']} 원문 보기", row['google_link'])
                    
                    with col2:
                        prompt_text = (
                            f"출처가 '{row['source']}'인 '{row['title']}' 기사를 찾아서 다음 순서로 답해줘:\n\n"
                            f"1. **기사 전문 번역 및 상세 요약**\n"
                            f"2. **국외(글로벌) 주식 시장 연관성**\n"
                            f"3. **국내 주식 시장 연관성**\n"
                            f"4. **투자자 관점의 최종 결론**"
                        )
                        
                        st.text_area("명령어 복사", value=prompt_text, height=100, key=widget_key)
                        st.link_button("🤖 Gemini 실행", "https://gemini.google.com/app", type="primary", use_container_width=True)
                    st.divider()
        else:
            st.info(f"현재 '{cat_name}' 카테고리에 새로운 뉴스가 없습니다.")
