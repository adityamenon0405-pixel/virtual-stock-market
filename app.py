import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import os
import pandas as pd
import plotly.express as px
import time

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="📈 Virtual Stock Market", layout="wide")

# ---------- AUTO REFRESH ----------
st_autorefresh(interval=1000, key="auto_refresh")

# ---------- BACKEND URL ----------
BACKEND = os.environ.get("BACKEND", "https://virtual-stock-market-7mxp.onrender.com")

# ---------- SESSION STATE ----------
if "team" not in st.session_state:
    st.session_state.team = None
if "round_start" not in st.session_state:
    st.session_state.round_start = None  # set when organizer starts
if "paused" not in st.session_state:
    st.session_state.paused = False
if "pause_time" not in st.session_state:
    st.session_state.pause_time = 0

ROUND_DURATION = 15 * 60  # 15 minutes

# ---------- UTILITY FUNCTIONS ----------
def safe_get(url, timeout=5):
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def fetch_stocks():
    return safe_get(f"{BACKEND}/stocks")

def fetch_leaderboard():
    return safe_get(f"{BACKEND}/leaderboard")

def fetch_news():
    return safe_get(f"{BACKEND}/news")

def fetch_portfolio(team):
    return safe_get(f"{BACKEND}/portfolio/{team}")

def init_team(team):
    try:
        r = requests.post(f"{BACKEND}/init_team", json={"team": team})
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

def trade(team, symbol, qty):
    try:
        r = requests.post(f"{BACKEND}/trade", json={"team": team, "symbol": symbol, "qty": qty})
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

# ---------- TEAM REGISTRATION (FIRST PAGE) ----------
if st.session_state.team is None:
    st.title("👥 Register or Login Your Team")
    team_name_input = st.text_input("Enter Team Name")
    if st.button("Continue", type="primary"):
        if team_name_input.strip() == "":
            st.warning("⚠️ Please enter a valid team name.")
        else:
            res = init_team(team_name_input)
            if res:
                st.success(f"✅ Team **{team_name_input}** created with ₹{res['cash']:.2f}")
                st.session_state.team = team_name_input
            else:
                port = fetch_portfolio(team_name_input)
                if port:
                    st.info(f"ℹ️ Team **{team_name_input}** logged in successfully.")
                    st.session_state.team = team_name_input
                else:
                    st.error("❌ Error occurred. Try another team name.")

    st.stop()  # 🚨 STOP execution until a team is registered/logged in

team_name = st.session_state.team
st.success(f"👋 Welcome, **{team_name}**! Let's trade 🚀")
st.divider()

# ---------- ADMIN LOGIN ----------
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

with st.sidebar:
    st.markdown("### 🔑 Organizer Login")
    admin_password_input = st.text_input("Enter Admin Password", type="password")
    if st.button("Login as Admin"):
        if admin_password_input == "your_secure_password":  # CHANGE THIS PASSWORD
            st.session_state.admin_logged_in = True
            st.success("✅ Logged in as Admin")
        else:
            st.error("❌ Incorrect password.")

    if st.session_state.admin_logged_in:
        st.info("🛠 Organizer Mode Active")
        if st.button("Logout"):
            st.session_state.admin_logged_in = False

# ---------- ORGANIZER PANEL ----------
if st.session_state.admin_logged_in:
    st.subheader("🛠 Organizer Panel")
    # Put your start/stop round, reset teams, etc. buttons here
else:
    st.caption("🔒 Organizer panel is locked. Login as admin to access controls.")


# ---------- TIMER ----------
if st.session_state.round_start:
    if st.session_state.paused:
        elapsed = st.session_state.pause_time - st.session_state.round_start
    else:
        elapsed = time.time() - st.session_state.round_start

    remaining = max(0, ROUND_DURATION - elapsed)
    mins, secs = divmod(int(remaining), 60)

    if remaining <= 10:
        color = "red"
        blink = True
    elif remaining <= 60:
        color = "orange"
        blink = False
    else:
        color = "green"
        blink = False

    if remaining <= 0:
        trading_allowed = False
        st.markdown("<h2 style='text-align:center; color:red;'>⏹️ Trading round has ended!</h2>", unsafe_allow_html=True)
    else:
        trading_allowed = True
        if blink:
            st.markdown(f"""
                <h1 style='text-align:center; color:{color};
                animation: blinker 1s linear infinite;'>
                ⏱️ {mins:02d}:{secs:02d}</h1>
                <style>@keyframes blinker {{ 50% {{ opacity: 0; }} }}</style>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"<h1 style='text-align:center; color:{color};'>⏱️ {mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
else:
    trading_allowed = False
    st.markdown("<h3 style='text-align:center; color:orange;'>⌛ Waiting for round to start...</h3>", unsafe_allow_html=True)
    
# ---------- FETCH DATA ----------
stocks = fetch_stocks()
leaderboard = fetch_leaderboard()
news = fetch_news()

# ---------- PORTFOLIO ----------
portfolio = fetch_portfolio(team_name)
if portfolio:
    st.subheader("💼 Portfolio")
    st.metric("Available Cash", f"₹{portfolio['cash']:.2f}")

    if portfolio["holdings"]:
        holdings_df = pd.DataFrame.from_dict(portfolio["holdings"], orient="index")
        st.dataframe(holdings_df, use_container_width=True)
    else:
        st.info("No holdings yet. Buy some stocks!")

    # ---------- TRADE ----------
    st.subheader("💸 Place Trade")
    if stocks:
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        with col1:
            selected_stock = st.selectbox("Select Stock", [s["symbol"] for s in stocks])
        with col2:
            qty = st.number_input("Quantity", min_value=1, step=1, value=1)

        if "buy_clicked" not in st.session_state:
            st.session_state.buy_clicked = False
        if "sell_clicked" not in st.session_state:
            st.session_state.sell_clicked = False

        with col3:
            if st.button("Buy"):
                st.session_state.buy_clicked = True
        with col4:
            if st.button("Sell"):
                st.session_state.sell_clicked = True

        if st.session_state.buy_clicked:
            if trading_allowed:
                res = trade(team_name, selected_stock, int(qty))
                if res:
                    st.success(f"✅ Bought {qty} of {selected_stock}")
                else:
                    st.error("Failed to buy. Check cash balance.")
            else:
                st.warning("Trading round has ended!")
            st.session_state.buy_clicked = False

        if st.session_state.sell_clicked:
            if trading_allowed:
                res = trade(team_name, selected_stock, -int(qty))
                if res:
                    st.success(f"✅ Sold {qty} of {selected_stock}")
                else:
                    st.error("Failed to sell. Check holdings.")
            else:
                st.warning("Trading round has ended!")
            st.session_state.sell_clicked = False

else:
    st.warning("Portfolio not found. Try creating a new team.")

# ---------- STOCKS ----------
if stocks:
    st.subheader("📊 Live Stock Prices")
    df = pd.DataFrame(stocks)
    df["Trend"] = df["pct_change"].apply(lambda x: "🟢" if x >= 0 else "🔴")
    st.dataframe(df[["symbol", "name", "price", "pct_change", "Trend"]]
                 .rename(columns={"symbol": "Symbol", "name": "Company", "price": "Price", "pct_change": "% Change"}),
                 use_container_width=True)

    # 3D Chart
    df['volume'] = [i * 1000 for i in range(1, len(df) + 1)]
    fig3d = px.scatter_3d(df, x='price', y='pct_change', z='volume', color='Trend',
                          hover_name='name', size='price', size_max=20,
                          title='Stock Price vs % Change vs Volume')
    st.plotly_chart(fig3d, use_container_width=True)
else:
    st.warning("No stock data available right now.")

# ---------- LEADERBOARD ----------
st.subheader("🏆 Live Leaderboard")
if leaderboard:
    ldf = pd.DataFrame(leaderboard).sort_values("value", ascending=False).reset_index(drop=True)
    ldf.index += 1

    def highlight_top3(row):
        if row.name == 1:
            return ['background-color: gold; font-weight: bold'] * len(row)
        elif row.name == 2:
            return ['background-color: silver; font-weight: bold'] * len(row)
        elif row.name == 3:
            return ['background-color: #cd7f32; font-weight: bold'] * len(row)
        else:
            return [''] * len(row)

    styled_df = ldf.style.apply(highlight_top3, axis=1)

    st.markdown("""
        <style>
        .scroll-table { max-height: 300px; overflow-y: auto; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="scroll-table">', unsafe_allow_html=True)
    st.dataframe(styled_df, use_container_width=True, hide_index=False)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("No teams yet. Waiting for participants to trade...")

# ---------- NEWS ----------
if news and "articles" in news and news["articles"]:
    st.subheader("📰 Market News")
    for article in news["articles"]:
        st.markdown(f"🔗 [{article['title']}]({article['url']})")
else:
    st.info("No news available right now.") 


