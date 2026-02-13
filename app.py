import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import urllib.parse
import pytz

# ==============================
# 1. 페이지 설정
# ==============================
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 허브")

st_autorefresh(interval=60000, key="news_refresh")

# ==============================
# 2. 카테고리 정의
# ==============================
CATEGORIES = {
    "AI/NVIDIA": "NVIDIA OR NVDA OR 'Artificial Intelligence' OR Blackwell",
    "반도체": "Semiconductor OR Chips OR TSMC OR ASML OR AVGO",
    "테슬라/머스크": "Tesla OR TSLA OR 'Elon Musk' OR Optimus",
    "빅테크": "Apple OR Microsoft OR Google OR Meta",
    "전력 인프라": "Data Center Energy OR Vertiv OR VRT OR NextEra",
    "로보틱스": "Humanoid Robot OR Figure AI OR Boston Dynamics"
}

# ==============================
# 3. 실제 원문 링크 추출 함수
# ==============================
def extract_real_link(entry):
    try:
        # 기본 링크
        link = entry.link

        # Google News 리다이렉트일 경우 실제 링크 추출 시도
        if "news.google.com" in link:
            for l in entry.links:
                if l.get("type") == "text/html":
                    return l.get("href")

        return link
    except:
        return entry.link


# ==============================
# 4. 뉴스 수집 함수
# ==============================
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

                real_link = extract_real_link(entry)

                news_list.append({
                    "category": category_name,
                    "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": title_part,
                    "real_link": real_link,
                    "source": source_part,
                    "dt": dt_utc
                })
            except:
                continue

    return news_list


# ==============================
# 5. 뉴스 실행 및 출력
# ==============================
all_news = []

for cat_name, query in CATEGORIES.items():
    all_news.extend(get_news_feed(cat_name, query))

if all_news:
    df = (
        pd.DataFrame(all_news)
        .drop_duplicates(subset=['title'])
        .sort_values(by="dt", ascending=False)
    )

    st.info("✅ Gemini는 반드시 해당 기사 링크만 기반으로 분석하도록 구성되어 있습니다.")

    for i, row in df.iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1.3])

            with col1:
                st.markdown(f"### <{row['category']}> {row['title']}")
                st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
                st.link_button("📄 원문 기사 직접 보기", row['real_link'])

            with col2:

                prompt_text = (
                    f"다음 기사 링크의 내용을 직접 확인하고 분석해줘:\n\n"
                    f"{row['real_link']}\n\n"
                    f"⚠ 반드시 위 링크 기사 내용만 기반으로 답변해.\n"
                    f"다른 기사 검색이나 유사 기사 추측은 절대 하지 마.\n\n"
                    f"다음 순서로 답해줘:\n\n"
                    f"1. **기사 전문 번역 및 상세 요약**\n"
                    f"   - 기사 전체 내용을 한국어로 정확하게 번역\n"
                    f"   - 핵심 내용을 놓침 없이 자세하게 요약\n\n"
                    f"2. **국외(글로벌) 주식 시장 연관성**\n"
                    f"   - 영향을 받는 해외 주요 종목 및 섹터 분석\n\n"
                    f"3. **국내 주식 시장 연관성**\n"
                    f"   - 국내 시장 영향 여부 및 관련 종목/테마 분석\n\n"
                    f"4. **투자자 관점 최종 결론**\n"
                    f"   - 시장 시그널 및 투자 매력도 평가"
                )

                st.text_area(
                    "명령어 복사 (Ctrl+C)",
                    value=prompt_text,
                    height=180,
                    key=f"copy_{i}"
                )

                st.link_button(
                    "🤖 Gemini 열기",
                    "https://gemini.google.com/app",
                    type="primary",
                    use_container_width=True
                )

            st.divider()

else:
    st.warning("현재 수집된 뉴스가 없습니다.")
