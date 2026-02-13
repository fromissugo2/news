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

# 60초마다 화면 자동 갱신
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
        for entry in feed.entries[:30]:
            try:
                dt_utc = pd.to_datetime(entry.published, utc=True)
                full_title = entry.title
                title_part = full_title.rsplit(' - ', 1)[0] if ' - ' in full_title else full_title
                source_part = entry.source.title if hasattr(entry, 'source') else "News Source"
                
                item_id = hashlib.md5(title_part.encode()).hexdigest()[:12]
                
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

# 4. 상단 공통 안내 (st.info)
st.info("💡 **이용 가이드**: 아래 탭을 클릭하여 카테고리별 뉴스를 확인하세요. 기사 우측의 명령어를 복사해 Gemini에 붙여넣으면 즉시 심층 분석이 시작됩니다.")

# 5. 상단 탭 구성
tabs = st.tabs(list(CATEGORIES.keys()))

# 6. 각 탭별 뉴스 출력 루프
for tab, (cat_name, query) in zip(tabs, CATEGORIES.items()):
    with tab:
        news_data = get_news_feed(cat_name, query)
        
        # 현재 시간 (갱신 확인용)
        now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')
        
        if news_data:
            df = pd.DataFrame(news_data).sort_values(by="dt", ascending=False)
            
            # 뉴스 개수와 갱신 상태 안내 (st.caption 활용)
            st.caption(f"🔥 현재 **{len(df)}개**의 최신 뉴스가 수집되었습니다. (마지막 갱신: {now_kst} | 60초 후 자동 업데이트)")
            
            for _, row in df.iterrows():
                widget_key = f"copy_{row['id']}_{cat_name}"
                
                with st.container():
                    col1, col2 = st.columns([3, 1.2])
                    
                    with col1:
                        st.markdown(f"### {row['title']}")
                        st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
                        st.link_button(f"📄 {row['source']} 원문 기사 보기", row['google_link'])
                    
                    with col2:
                        # 분석 프롬프트
                        prompt_text = (
                            f"출처가 '{row['source']}'인 '{row['title']}' 기사를 찾아서 다음 순서로 답해줘:\n\n"
                            f"1. **기사 전문 번역 및 상세 요약**\n"
                            f"   - 기사 전체 내용을 한국어로 정확하게 번역\n"
                            f"   - 핵심 내용을 놓침 없이 자세하게 요약\n\n"
                            f"2. **국외(글로벌) 주식 시장 연관성**\n"
                            f"   - 해당 소식으로 영향을 받는 미국 등 해외 주요 종목과 섹터 분석\n\n"
                            f"3. **국내 주식 시장 연관성**\n"
                            f"   - 국내 시장에서도 영향이 있을지 여부와 구체적인 이유\n"
                            f"   - 연관된 국내 주식 종목(수혜주/피해주)과 관련 테마(예: HBM, 자율주행 등)\n\n"
                            f"4. **투자자 관점의 최종 결론**\n"
                            f"   - 이 기사가 시장에 주는 시그널 요약 및 투자 매력도 분석"
                        )
                        
                        st.text_area("명령어 복사 (Ctrl+C)", value=prompt_text, height=150, key=widget_key)
                        st.link_button("🤖 Gemini 열기", "https://gemini.google.com/app", type="primary", use_container_width=True)
                    
                    st.divider()
        else:
            st.warning(f"현재 '{cat_name}' 카테고리에 1시간 이내 등록된 최신 뉴스가 없습니다.")
