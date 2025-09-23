# app.py
import streamlit as st
import requests
import time
import os
import pandas as pd

try:
    from streamlit_autorefresh import st_autorefresh
    AUTORELOAD_AVAILABLE = True
except:
    AUTORELOAD_AVAILABLE = False

# ---- Page Config ----
st.set_page_config(page_title="📈 Virtual Stock Market", layout="wide")

# ---- Custom Styling ----
st.markdown("""
    <style>
    body {
        background-color: #ffffff;
        color: #000000;
        font-family: 'Segoe UI', sans-serif;
    }
    h1, h2, h3 {
        font-weight: 700;
    }
    .big-timer {
        font-size: 60px !important;
        font-weight: 800 !important;
        text-align: center;
        margin-bottom: 10px;
    }
    .stButton>button {
        background: linear-gradient(135deg, #4cafef, #1976d2);
        color: white;
        font-weight: 600;
        border-radius: 12px;
        padding: 0.6em 1.2em;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        border: none;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #64b5f6, #1565c0);
    }
    .news-item {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 8px;
        background: linear-gradient(180deg, #f8fafc, #ffffff);
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .news-title {
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .news-meta {
        font-size: 12px;
        color: #555555;
    }
    </style>
""", unsafe_allow_html=True)

# ---- Config ----
BACKEND = os.environ.get("BACKEND", "https://virtual-stock-market-7mxp.onrender.com")
ROUND_DURATION = 15 * 60
AUTO_REFRESH_MS = 5000

if AUTORELOAD_AVAILABLE:
    st_autorefresh(interval=AUTO_REFRESH_MS, key="app_refresh")

# ---- Session State ----
if "team" not in st.session_state:
    st.session_state.team = ""

# ---- Utility ----
def safe_get_json(url):
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return r.json()
    except:
        return None

def safe_post(url, payload):
    try:
        r = requests.post(url, json=payload, timeout=5)
        r.raise_for_status()
        return r.json()
    except:
        return {"error": "Backend unavailable."}

# ---- Team Login ----
st.sidebar.title("👤 Team Login")
team_name = st.sidebar.text_input("Enter Team Name", st.session_state.team)
if st.sidebar.button("Join / Init Team"):
    resp = safe_post(f"{BACKEND}/init_team", {"team": team_name})
    if resp and "error" not in resp:
        st.session_state.team = team_name
        st.sidebar.success(f"✅ Joined as {team_name}")
    else:
        st.sidebar.error("❌ Could not connect to backend.")

if not st.session_state.team:
    st.warning("Please enter your team name in the sidebar to continue.")
    st.stop()

# ---- Timer ----
start_time = float(os.environ.get("ROUND_START", time.time()))
elapsed = time.time() - start_time
remaining = max(0, ROUND_DURATION - elapsed)
mins, secs = divmod(int(remaining), 60)

timer_color = "#28a745" if remaining > 300 else "#ff9800" if remaining > 60 else "#f44336"
st.markdown(f"<h1 class='big-timer' style='color:{timer_color};'>⏱️ {mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)

if remaining <= 0:
    st.error("⏹️ Trading round has ended!")
    st.stop()

# ---- Fetch Data ----
stocks = safe_get_json(f"{BACKEND}/stocks") or []
portfolio = safe_get_json(f"{BACKEND}/portfolio/{st.session_state.team}") or {"cash": 0, "holdings": []}
leaderboard = safe_get_json(f"{BACKEND}/leaderboard") or []
news = safe_get_json(f"{BACKEND}/news")  # keep None if invalid so we can show helpful message

# ---- Portfolio ----
st.markdown("## 💼 Portfolio")
st.write(f"**Available Cash:** ₹{portfolio.get('cash', 0):,.2f}")

if portfolio.get("holdings"):
    df_holdings = pd.DataFrame(portfolio["holdings"])
    st.dataframe(df_holdings, use_container_width=True, height=300)
else:
    st.info("No holdings yet.")

# ---- Trade Section ----
st.markdown("## 💹 Trade")
if stocks:
    df_stocks = pd.DataFrame(stocks)
    st.dataframe(df_stocks, use_container_width=True, height=300)

    selected_stock = st.selectbox("Select Stock", df_stocks["symbol"])
    qty = st.number_input("Quantity", min_value=1, step=1)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🟢 Buy"):
            resp = safe_post(f"{BACKEND}/trade", {"team": st.session_state.team, "symbol": selected_stock, "qty": int(qty)})
            if resp and "error" not in resp:
                st.success(resp.get("message", f"Bought {qty} {selected_stock}"))
            else:
                st.error("❌ Trade failed. Check backend or balance.")
    with c2:
        if st.button("🔴 Sell"):
            resp = safe_post(f"{BACKEND}/trade", {"team": st.session_state.team, "symbol": selected_stock, "qty": -int(qty)})
            if resp and "error" not in resp:
                st.success(resp.get("message", f"Sold {qty} {selected_stock}"))
            else:
                st.error("❌ Trade failed. Check backend or holdings.")
else:
    st.warning("No stock data available.")

# ---- Leaderboard ----
st.markdown("## 🏆 Leaderboard")
if leaderboard:
    df = pd.DataFrame(leaderboard).sort_values(by="portfolio_value", ascending=False)
    st.dataframe(df, use_container_width=True, height=350)
else:
    st.warning("No leaderboard data available.")

# ---- News Section (new) ----
st.markdown("## 📰 Market News")
if news is None:
    st.error("News feed currently unavailable. Check backend /news endpoint.")
else:
    # Normalize different possible backend formats
    if isinstance(news, dict):
        articles = news.get("articles") or news.get("data") or []
    elif isinstance(news, list):
        articles = news
    else:
        articles = []

    if not articles:
        st.info("No news articles available right now.")
    else:
        # Show up to 6 articles
        for art in articles[:6]:
            # art may be dict with title,url,source,publishedAt,description
            title = art.get("title") if isinstance(art, dict) else str(art)
            url = art.get("url") if isinstance(art, dict) else None
            source = art.get("source", {}).get("name") if isinstance(art.get("source", {}), dict) else art.get("source") if isinstance(art, dict) else None
            desc = art.get("description") if isinstance(art, dict) else None
            pub = art.get("publishedAt") if isinstance(art, dict) else None

            st.markdown("<div class='news-item'>", unsafe_allow_html=True)
            if url:
                st.markdown(f"<div class='news-title'><a href='{url}' target='_blank'>{title}</a></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='news-title'>{title}</div>", unsafe_allow_html=True)

            meta_parts = []
            if source:
                meta_parts.append(f"{source}")
            if pub:
                meta_parts.append(f"{pub}")
            if meta_parts:
                st.markdown(f"<div class='news-meta'>{' • '.join(meta_parts)}</div>", unsafe_allow_html=True)
            if desc:
                st.markdown(f"<div style='margin-top:6px'>{desc}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ---- Footer / Status ----
st.markdown("---")
status_col1, status_col2 = st.columns([3,1])
with status_col1:
    st.write(f"Backend: `{BACKEND}` • Last fetch: {time.strftime('%H:%M:%S')}")
with status_col2:
    st.write(f"Auto-refresh: {'✅ every 5s' if AUTORELOAD_AVAILABLE else '❌ not installed'}")
