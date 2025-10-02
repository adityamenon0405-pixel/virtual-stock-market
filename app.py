import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import os
import pandas as pd
import plotly.express as px
import time

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="📈 Virtual Stock Market", layout="wide")

# ---------- CUSTOM STYLES ----------
st.markdown("""
    <style>
    body {
        background-color: #f8f9f9;
    }
    .timer-box {
        background: #ffffff;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
        margin: 15px 0;
        text-align: center;
    }
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
""", unsafe_allow_html=True)

# ---------- AUTO REFRESH ----------
st_autorefresh(interval=1000, key="auto_refresh")

# ---------- BACKEND URL ----------
BACKEND = os.environ.get("BACKEND", "https://virtual-stock-market-7mxp.onrender.com")

# ---------- SESSION STATE ----------
if "team" not in st.session_state:
    st.session_state.team = None
if "round_start" not in st.session_state:
    st.session_state.round_start = None
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

def fetch_data(endpoint):
    return safe_get(f"{BACKEND}/{endpoint}")

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

# ---------- ORGANIZER CONTROLS (Password Protected) ----------
st.sidebar.subheader("🔒 Organizer Access")
admin_pass = st.sidebar.text_input("Enter Organizer Password", type="password")

if admin_pass == "secret123":  # change this to your own password
    with st.sidebar.expander("⚙️ Organizer Controls", expanded=True):
        st.write("Control the round timer here.")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("▶️ Start Round"):
                st.session_state.round_start = time.time()
                st.session_state.paused = False
                st.success("✅ Round started.")
        with col2:
            if st.button("⏸ Pause Round"):
                if st.session_state.round_start and not st.session_state.paused:
                    st.session_state.paused = True
                    st.session_state.pause_time = time.time()
                    st.info("⏸ Round paused.")
        with col3:
            if st.button("🔄 Resume Round"):
                if st.session_state.paused:
                    paused_duration = time.time() - st.session_state.pause_time
                    st.session_state.round_start += paused_duration
                    st.session_state.paused = False
                    st.success("▶️ Round resumed.")
        if st.button("♻️ Reset Round"):
            st.session_state.round_start = None
            st.session_state.paused = False
            st.session_state.pause_time = 0
            st.warning("Round reset. You must start again.")
else:
    st.sidebar.info("Organizer controls hidden. Enter password to unlock.")

# ---------- REGISTRATION FIRST ----------
if st.session_state.team is None:
    st.title("👥 Register or Login Your Team")
    team_name_input = st.text_input("Enter Team Name")
    if st.button("Continue"):
        if team_name_input.strip() == "":
            st.warning("Please enter a valid team name.")
        else:
            res = init_team(team_name_input)
            if res:
                st.success(f"✅ Team '{team_name_input}' created with ₹{res['cash']:.2f}")
                st.session_state.team = team_name_input
            else:
                port = fetch_data(f"portfolio/{team_name_input}")
                if port:
                    st.info(f"Team '{team_name_input}' logged in successfully.")
                    st.session_state.team = team_name_input
                else:
                    st.error("⚠️ Error occurred. Try another team name.")
    st.stop()

team_name = st.session_state.team

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
        st.markdown("<div class='timer-box'><h2 style='color:red;'>⏹️ Trading round has ended!</h2></div>", unsafe_allow_html=True)
    else:
        trading_allowed = True
        if blink:
            st.markdown(f"""
                <div class='timer-box'>
                <h1 style='color:{color}; animation: blinker 1s linear infinite;'>
                ⏱️ {mins:02d}:{secs:02d}</h1>
                <style>@keyframes blinker {{ 50% {{ opacity: 0; }} }}</style>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='timer-box'><h1 style='color:{color};'>⏱️ {mins:02d}:{secs:02d}</h1></div>", unsafe_allow_html=True)
else:
    trading_allowed = False
    st.markdown("<div class='timer-box'><h3 style='color:orange;'>⌛ Waiting for round to start...</h3></div>", unsafe_allow_html=True)

# ---------- FETCH DATA ----------
stocks = fetch_data("stocks")
leaderboard = fetch_data("leaderboard")
news = fetch_data("news")
portfolio = fetch_data(f"portfolio/{team_name}")

# ---------- PORTFOLIO ----------
st.header("💼 Your Portfolio")
if portfolio:
    st.markdown(f"""
        <div class="timer-box" style="background:#eaf2f8;">
            <h3>Available Cash: 💵 ₹{portfolio['cash']:.2f}</h3>
        </div>
    """, unsafe_allow_html=True)

    if portfolio["holdings"]:
        holdings_df = pd.DataFrame.from_dict(portfolio["holdings"], orient="index")
        st.dataframe(
            holdings_df.style.background_gradient(cmap="Blues"),
            use_container_width=True
        )
    else:
        st.info("📌 No holdings yet. Buy some stocks!")
else:
    st.warning("⚠️ Portfolio not found.")

# ---------- TRADE ----------
if stocks:
    st.subheader("💸 Place Trade")
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        selected_stock = st.selectbox("Select Stock", [s["symbol"] for s in stocks])
    with col2:
        qty = st.number_input("Quantity", min_value=1, step=1, value=1)
    with col3:
        if st.button("Buy"):
            if trading_allowed:
                res = trade(team_name, selected_stock, int(qty))
                if res:
                    st.success(f"✅ Bought {qty} of {selected_stock}")
                else:
                    st.error("❌ Failed to buy. Check balance.")
            else:
                st.warning("Trading round has ended!")
    with col4:
        if st.button("Sell"):
            if trading_allowed:
                res = trade(team_name, selected_stock, -int(qty))
                if res:
                    st.success(f"✅ Sold {qty} of {selected_stock}")
                else:
                    st.error("❌ Failed to sell. Check holdings.")
            else:
                st.warning("Trading round has ended!")

# ---------- STOCKS ----------
st.header("📊 Live Stock Prices")
if stocks:
    df = pd.DataFrame(stocks)
    df["Trend"] = df["pct_change"].apply(lambda x: "🟢" if x >= 0 else "🔴")
    st.dataframe(
        df[["symbol", "name", "price", "pct_change", "Trend"]]
        .rename(columns={"symbol": "Symbol", "name": "Company", "price": "Price", "pct_change": "% Change"}),
        use_container_width=True
    )

    # 3D Chart (Attractive)
    df['volume'] = [i * 1000 for i in range(1, len(df) + 1)]
    fig3d = px.scatter_3d(
        df, x='price', y='pct_change', z='volume', color='Trend',
        hover_name='name', size='price', size_max=20,
        title='💹 Stock Price vs % Change vs Volume'
    )
    fig3d.update_layout(scene=dict(
        xaxis_title='Price',
        yaxis_title='% Change',
        zaxis_title='Volume',
        bgcolor="rgba(240,248,255,0.8)"
    ))
    st.plotly_chart(fig3d, use_container_width=True)
else:
    st.warning("⚠️ No stock data available.")

# ---------- LEADERBOARD ----------
st.header("🏆 Live Leaderboard")
if leaderboard:
    ldf = pd.DataFrame(leaderboard).sort_values("value", ascending=False).reset_index(drop=True)
    ldf.index += 1

    def highlight_top(row):
        if row.name == 1:
            return ['background-color: gold; font-weight: bold;'] * len(row)
        elif row.name == 2:
            return ['background-color: silver; font-weight: bold;'] * len(row)
        elif row.name == 3:
            return ['background-color: #cd7f32; font-weight: bold;'] * len(row)
        return [''] * len(row)

    styled_ldf = ldf.style.apply(highlight_top, axis=1).background_gradient(cmap="Greens")

    st.markdown("""
        <div class="timer-box" style="background:#fef9e7;">
            <h3>📊 Current Rankings</h3>
        </div>
    """, unsafe_allow_html=True)

    st.dataframe(styled_ldf, use_container_width=True, hide_index=False)
else:
    st.info("⚠️ No leaderboard data yet.")

# ---------- NEWS ----------
st.header("📰 Market News")
if news and "articles" in news and news["articles"]:
    for article in news["articles"]:
        st.markdown(f"🔗 [{article['title']}]({article['url']})")
else:
    st.info("⚠️ No news available right now.")
