import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz
import hashlib

# 1. 페이지 설정
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
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
        for entry in feed.entries[:8]:
            try:
                dt_utc = pd.to_datetime(entry.published, utc=True)
                full_title = entry.title
                title_part = full_title.rsplit(' - ', 1)[0] if ' - ' in full_title else full_title
                source_part = entry.source.title if hasattr(entry, 'source') else "News Source"
                
                # 고유 키 생성을 위한 해시값 (제목 기반)
                # 이 값이 변해야 오른쪽 텍스트 영역이 갱신됩니다.
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

# 4. 뉴스 데이터 통합
all_news = []
for cat_name, query in CATEGORIES.items():
    all_news.extend(get_news_feed(cat_name, query))

# 5. 뉴스 출력부
if all_news:
    # 중복 제거 및 시간순 정렬
    df = pd.DataFrame(all_news).drop_duplicates(subset=['title']).sort_values(by="dt", ascending=False)
    
    st.info("✅ 뉴스는 1분마다 자동 갱신됩니다. 기사가 바뀌면 복사할 명령어도 자동으로 업데이트됩니다.")

    for i, row in df.iterrows():
        # 고유 식별자 생성 (데이터와 위젯을 동기화하는 핵심)
        widget_key = f"area_{row['id']}"
        
        with st.container():
            col1, col2 = st.columns([3, 1.2])
            
            with col1:
                st.markdown(f"### <{row['category']}> {row['title']}")
                st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
                st.link_button("📄 원문 기사 직접 보기", row['google_link'])
            
            with col2:
                # 명령어 구성
                prompt_text = (
                    f"출처가 '{row['source']}'인 '{row['title']}' 기사를 찾아서 다음 순서로 답해줘:\n\n"
                    f"1. **기사 전문 번역 및 상세 요약**\n"
                    f"   - 기사 전체 내용을 한국어로 정확하게 번역\n"
                    f"   - 핵심 내용을 놓침 없이 자세하게 요약\n\n"
                    f"2. **국외(글로벌) 주식 시장 연관성**\n"
                    f"   - 해당 소식으로 영향을 받는 미국 등 해외 주요 종목과 섹터 분석\n\n"
                    f"3. **국내 주식 시장 연관성**\n"
                    f"   - 국내 시장에서도 영향이 있을지 여부와 구체적인 이유\n"
                    f"   - 연관된 국내 주식 종목(수혜주/피해주)과 관련 테마\n\n"
                    f"4. **투자자 관점의 최종 결론**\n"
                    f"   - 이 기사가 시장에 주는 시그널 요약 및 투자 매력도 분석"
                )
                
                # 수정 포인트: key에 데이터 고유 ID인 widget_key를 사용함
                st.text_area(
                    "명령어 복사 (Ctrl+C)", 
                    value=prompt_text, 
                    height=120, 
                    key=widget_key
                )
                st.link_button("🤖 Gemini 열기", "https://gemini.google.com/app", type="primary", use_container_width=True)
            
            st.divider()
else:
    st.warning("가져올 뉴스가 없습니다. 잠시 후 다시 시도해주세요.")
