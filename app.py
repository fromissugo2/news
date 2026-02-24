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

# ==============================
# 📊 실시간 증시 모니터링 (완전 안정 버전)
# ==============================

st.subheader("📊 실시간 증시 모니터링")

market_col1, market_col2 = st.columns(2)

with market_col1:
    st.markdown("### 🇺🇸 NASDAQ Composite (5분봉)")
    st.components.v1.html("""
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container">
      <div id="tradingview_nasdaq"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
      {
        "autosize": true,
        "symbol": "NASDAQ:IXIC",
        "interval": "5",
        "timezone": "America/New_York",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "hide_top_toolbar": false,
        "withdateranges": true,
        "allow_symbol_change": false
      }
      </script>
    </div>
    <!-- TradingView Widget END -->
    """, height=420)

with market_col2:
    st.markdown("### 🇰🇷 KOSDAQ (5분봉)")
    st.components.v1.html("""
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container">
      <div id="tradingview_kosdaq"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
      {
        "autosize": true,
        "symbol": "KRX:KOSDAQ",
        "interval": "5",
        "timezone": "Asia/Seoul",
        "theme": "dark",
        "style": "1",
        "locale": "kr",
        "hide_top_toolbar": false,
        "withdateranges": true,
        "allow_symbol_change": false
      }
      </script>
    </div>
    <!-- TradingView Widget END -->
    """, height=420)

st.divider()

# 60초마다 화면 자동 갱신
st_autorefresh(interval=60000, key="news_refresh")

# 🔥 중복 방지용 전역 저장소
if "seen_ids" not in st.session_state:
    st.session_state.seen_ids = set()

# --- 비밀번호 설정부 ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔑 접근 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔑 접근 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        st.error("❌ 비밀번호가 틀렸습니다.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ==============================
# 이하 뉴스 로직 전부 그대로
# ==============================

CATEGORIES = {
    "⭐ 초속보 (Direct)": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=2000&keywords=technology",
        "https://9to5mac.com/feed/",
        "https://www.reutersagency.com/feed/?best-topics=technology&post_type=best",
        "https://www.zdnet.com/news/rss.xml"
    ],
    "📺 CNBC (Tech/Stock)": "CNBC_TECH_FILTER",
    "AI/NVIDIA": "NVIDIA OR NVDA OR 'Artificial Intelligence' OR Blackwell",
    "반도체": "Semiconductor OR Chips OR TSMC OR ASML OR AVGO",
    "테슬라/머스크": "Tesla OR TSLA OR 'Elon Musk' OR Optimus",
    "빅테크": "Apple OR Microsoft OR Google OR Meta",
    "전력 인프라": "Data Center Energy OR Vertiv OR VRT OR NextEra",
    "로보틱스": "Robot OR Robotics OR Humanoid OR 'AI Robot' OR Automation OR Boston Dynamics OR Figure AI OR Optimus"
}

# 이하 뉴스 함수와 루프는 네 코드 그대로 유지
