import streamlit as st
import feedparser
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import urllib.parse
import pytz
import hashlib
import requests

# 1. 페이지 설정
st.set_page_config(page_title="Global Tech News Hub", layout="wide")
st.title("📡 실시간 외신 테크 뉴스 허브")

# 60초마다 화면 자동 갱신
st_autorefresh(interval=60000, key="news_refresh")

# 2. 카테고리 정의
CATEGORIES = {
    "AI/NVIDIA": "NVIDIA NVDA Artificial Intelligence Blackwell",
    "반도체": "Semiconductor Chips TSMC ASML AVGO",
    "테슬라/머스크": "Tesla TSLA Elon Musk Optimus",
    "빅테크": "Apple Microsoft Google Meta",
    "전력 인프라": "Data Center Energy Vertiv VRT NextEra",
    "로보틱스": "Humanoid Robot Figure AI Boston Dynamics",
    "가상화폐/머스크/AI": "Bitcoin Ethereum Crypto Elon Musk AI"
}

# 3. 뉴스 수집 함수 (Finnhub + 키워드 필터링)
@st.cache_data(ttl=60)
def get_news_feed(category_name, keywords):
    news_list = []
    kst = pytz.timezone('Asia/Seoul')
    now_utc = datetime.now(pytz.utc)

    api_key = st.secrets.get("FINNHUB_API_KEY")

    if not api_key:
        st.error("⚠️ FINNHUB_API_KEY가 설정되지 않았습니다.")
        return []

    try:
        # 최근 1일 뉴스 호출 (Finnhub 무료 플랜 안정)
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        url = "https://finnhub.io/api/v1/news"
        params = {
            "category": "general",
            "from": yesterday.strftime("%Y-%m-%d"),
            "to": today.strftime("%Y-%m-%d"),
            "token": api_key
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            st.error(f"Finnhub API 오류 (코드: {response.status_code})")
            return []

        data = response.json()

        keyword_list = keywords.lower().split()

        for entry in data:
            try:
                dt_utc = datetime.fromtimestamp(entry['datetime'], pytz.utc)

                # 1시간 이내 뉴스만 허용
                if (now_utc - dt_utc).total_seconds() > 3600:
                    continue

                title = entry['headline']
                summary = entry.get('summary', '')
                combined_text = f"{title} {summary}".lower()

                # 키워드 필터링
                if not any(word.lower() in combined_text for word in keyword_list):
                    continue

                item_id = hashlib.md5(title.encode()).hexdigest()[:12]

                news_list.append({
                    "id": item_id,
                    "category": category_name,
                    "time": dt_utc.astimezone(kst).strftime('%m/%d %H:%M'),
                    "title": title,
                    "google_link": entry['url'],
                    "source": entry.get('source', 'Finnhub'),
                    "dt": dt_utc
                })

            except:
                continue

    except Exception as e:
        st.error(f"Finnhub API 에러: {e}")

    return sorted(news_list, key=lambda x: x['dt'], reverse=True)


# 4. 상단 공통 안내
st.info("💡 **이용 가이드**: 탭을 클릭해 실시간 속보를 확인하세요. 1시간 이내의 최신 기사만 표시됩니다.")

# 5. 상단 탭 구성
tabs = st.tabs(list(CATEGORIES.keys()))

# 6. 각 탭별 뉴스 출력
for tab_idx, (tab, (cat_name, keywords)) in enumerate(zip(tabs, CATEGORIES.items())):
    with tab:
        news_data = get_news_feed(cat_name, keywords)
        now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')

        if news_data:
            df = pd.DataFrame(news_data)
            st.caption(f"🔥 현재 **{len(df)}개**의 최신 뉴스가 수집되었습니다. (마지막 갱신: {now_kst})")

            for i, (_, row) in enumerate(df.iterrows()):
                widget_key = f"copy_{tab_idx}_{i}_{row['id']}"

                with st.container():
                    col1, col2 = st.columns([3, 1.2])

                    with col1:
                        st.markdown(f"### {row['title']}")
                        st.caption(f"🕒 {row['time']} | 출처: {row['source']}")
                        st.link_button(f"📄 {row['source']} 원문 기사 보기", row['google_link'])

                    with col2:
                        prompt_text = (
                            f"출처가 '{row['source']}'인 '{row['title']}' 기사를 찾아서 다음 순서로 답해줘:\n\n"
                            f"1. **기사 전문 번역 및 상세 요약**\n"
                            f"2. **국외(글로벌) 주식 시장 연관성 분석**\n"
                            f"3. **국내 주식 시장 연관성 분석**\n"
                            f"4. **투자자 관점 최종 결론**"
                        )

                        st.text_area("명령어 복사 (Ctrl+C)", value=prompt_text, height=150, key=widget_key)
                        st.link_button("🤖 Gemini 열기", "https://gemini.google.com/app", type="primary", use_container_width=True)

                    st.divider()

        else:
            st.warning(f"현재 '{cat_name}' 카테고리에 최신 뉴스가 없습니다. (자동 필터링 중)")
