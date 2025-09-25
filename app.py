import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import threading

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="📈 Virtual Stock Market", layout="wide")

# ---------- BACKEND ----------
BACKEND = "https://virtual-stock-market-7mxp.onrender.com"  # update to your backend

# ---------- DARK THEME ----------
st.markdown("""
<style>
body { background-color: #0D1117; color: #E6EDF3; }
.stApp { background-color: #0D1117; }
.block-container { max-width: 1400px; }
.card {
    background-color: #161B22;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 15px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.6);
}
.stDataFrame { background-color: #161B22 !important; color: #E6EDF3; }
.metric-label, .metric-value { color: #E6EDF3 !important; }
a { text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# ---------- SESSION STATE ----------
if "team" not in st.session_state:
    st.session_state.team = None
if "round_start" not in st.session_state:
    st.session_state.round_start = None
if "paused" not in st.session_state:
    st.session_state.paused = False
if "timer_thread_started" not in st.session_state:
    st.session_state.timer_thread_started = False
if "chart_thread_started" not in st.session_state:
    st.session_state.chart_thread_started = False

ROUND_DURATION = 15 * 60  # 15 min

# ---------- FETCH FUNCTIONS ----------
@st.cache_data(ttl=5)
def fetch_stocks():
    try:
        r = requests.get(f"{BACKEND}/stocks", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        return []
    return []

@st.cache_data(ttl=5)
def fetch_leaderboard():
    try:
        r = requests.get(f"{BACKEND}/leaderboard", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        return []
    return []

@st.cache_data(ttl=60)
def fetch_news():
    try:
        r = requests.get(f"{BACKEND}/news", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        return {"articles": []}
    return {"articles": []}

def fetch_portfolio(team):
    try:
        r = requests.get(f"{BACKEND}/portfolio/{team}", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        return None
    return None

def trade(team, symbol, qty):
    try:
        r = requests.post(f"{BACKEND}/trade", json={"team": team, "symbol": symbol, "qty": qty}, timeout=6)
        return r.json(), r.status_code
    except:
        return {"detail": "Server error"}, 500

# ---------- TEAM LOGIN ----------
if st.session_state.team is None:
    st.title("👥 Team Login")
    team_name = st.text_input("Enter Team Name")
    if st.button("Join / Register"):
        if team_name.strip():
            res = requests.post(f"{BACKEND}/init_team", json={"team": team_name.strip()})
            if res.status_code in [200, 400]:
                st.session_state.team = team_name.strip()
                st.experimental_rerun()
            else:
                st.error("Could not register/login team.")
    st.stop()

st.markdown(f"<h3 style='color:#58A6FF;'>✅ Logged in as {st.session_state.team}</h3>", unsafe_allow_html=True)

# ---------- LIVE TIMER ----------
timer_placeholder = st.empty()

def run_timer():
    while st.session_state.round_start:
        if st.session_state.paused:
            elapsed = st.session_state.pause_time - st.session_state.round_start
        else:
            elapsed = time.time() - st.session_state.round_start
        remaining = max(0, ROUND_DURATION - elapsed)
        mins, secs = divmod(int(remaining), 60)
        color = "#16A34A" if remaining > 60 else ("#FACC15" if remaining > 10 else "#F87171")
        timer_placeholder.markdown(
            f"<h2 style='text-align:center;color:{color};'>⏱️ {mins:02d}:{secs:02d}</h2>",
            unsafe_allow_html=True
        )
        if remaining <= 0:
            break
        time.sleep(1)

if st.session_state.round_start and not st.session_state.timer_thread_started:
    threading.Thread(target=run_timer, daemon=True).start()
    st.session_state.timer_thread_started = True

# ---------- PLACEHOLDERS ----------
chart_placeholder = st.empty()

def update_3d_chart():
    while True:
        stocks = fetch_stocks()
        if stocks:
            df = pd.DataFrame(stocks)
            df['Trend'] = df['pct_change'].apply(lambda x: "🟢" if x >= 0 else "🔴")
            df['volume'] = [i*1000 for i in range(1,len(df)+1)]
            fig3d = px.scatter_3d(
                df, x='price', y='pct_change', z='volume',
                color='Trend', hover_name='name', size='price', size_max=16,
                opacity=0.8, title="Live Stock Market"
            )
            fig3d.update_layout(
                scene=dict(xaxis_title="Price", yaxis_title="% Change", zaxis_title="Volume"),
                template="plotly_dark",
                margin=dict(l=0,r=0,b=0,t=30)
            )
            chart_placeholder.plotly_chart(fig3d, use_container_width=True)
        time.sleep(3)

if not st.session_state.chart_thread_started:
    threading.Thread(target=update_3d_chart, daemon=True).start()
    st.session_state.chart_thread_started = True

# ---------- FETCH DATA ----------
stocks = fetch_stocks()
portfolio = fetch_portfolio(st.session_state.team)
leaderboard = fetch_leaderboard()
news = fetch_news()

# ---------- UI ----------
col1, col2 = st.columns([2,1])

with col1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💼 Portfolio")
    if portfolio:
        st.metric("Available Cash", f"₹{portfolio['cash']:.2f}")
        if portfolio["holdings"]:
            holdings_df = pd.DataFrame.from_dict(portfolio["holdings"], orient="index")
            st.dataframe(holdings_df, use_container_width=True)
        else:
            st.info("No holdings yet.")
    else:
        st.error("Portfolio not loaded.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💸 Place Trade")
    if stocks:
        symbol = st.selectbox("Select Stock", [s["symbol"] for s in stocks])
        qty = st.number_input("Quantity", min_value=1, step=1, value=1)
        colb, cols = st.columns(2)
        with colb:
            if st.button("Buy", key="buy"):
                resp, code = trade(st.session_state.team, symbol, qty)
                if code == 200:
                    st.success(f"✅ Bought {qty} of {symbol}")
                    st.cache_data.clear()
                else:
                    st.error(resp.get("detail","Failed to buy"))
        with cols:
            if st.button("Sell", key="sell"):
                resp, code = trade(st.session_state.team, symbol, -qty)
                if code == 200:
                    st.success(f"✅ Sold {qty} of {symbol}")
                    st.cache_data.clear()
                else:
                    st.error(resp.get("detail","Failed to sell"))
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🏆 Leaderboard")
    if leaderboard:
        ldf = pd.DataFrame(leaderboard)
        if "portfolio_value" in ldf.columns and "value" not in ldf.columns:
            ldf["value"] = ldf["portfolio_value"]
        st.dataframe(ldf.rename(columns={"team":"Team","value":"Value"}), use_container_width=True)
    else:
        st.info("No teams yet.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📰 Market News")
    if news and "articles" in news and news["articles"]:
        for article in news["articles"][:6]:
            st.markdown(
                f"<p><a href='{article['url']}' target='_blank' style='color:#58A6FF;'>{article['title']}</a></p>",
                unsafe_allow_html=True
            )
    else:
        st.info("No news available.")
    st.markdown("</div>", unsafe_allow_html=True)
