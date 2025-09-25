import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import os
import pandas as pd
import plotly.express as px
import time
from datetime import datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="📈 Virtual Stock Market", layout="wide")

# ---------- AUTO REFRESH ----------
st_autorefresh(interval=1000, key="auto_refresh")  # refresh every 1 sec

# ---------- BACKEND URL ----------
BACKEND = os.environ.get("BACKEND", "https://virtual-stock-market-7mxp.onrender.com")

# ---------- SESSION STATE ----------
for key in ["team", "round_start", "paused", "pause_time", "buy_clicked", "sell_clicked"]:
    if key not in st.session_state:
        if key in ["buy_clicked", "sell_clicked", "paused"]:
            st.session_state[key] = False
        else:
            st.session_state[key] = None if key in ["team", "round_start"] else 0

ROUND_DURATION = 15 * 60  # 15 minutes

# ---------- UTILITY FUNCTIONS ----------
def safe_get(url, timeout=5):
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except:
        return None

def fetch_stocks():
    return safe_get(f"{BACKEND}/stocks") or []

def fetch_leaderboard():
    return safe_get(f"{BACKEND}/leaderboard") or []

def fetch_news():
    return safe_get(f"{BACKEND}/news") or {"articles": []}

def fetch_portfolio(team):
    return safe_get(f"{BACKEND}/portfolio/{team}") or {"cash": 0, "holdings": {}}

def init_team(team):
    try:
        r = requests.post(f"{BACKEND}/init_team", json={"team": team})
        if r.status_code == 200:
            return r.json()
    except:
        return None
    return None

def trade(team, symbol, qty):
    try:
        r = requests.post(f"{BACKEND}/trade", json={"team": team, "symbol": symbol, "qty": qty})
        if r.status_code == 200:
            return r.json()
    except:
        return None
    return None

# ---------- TEAM REGISTRATION ----------
if st.session_state.team is None:
    st.title("👥 Register or Login Your Team")
    team_name_input = st.text_input("Enter Team Name")
    if st.button("Continue"):
        if team_name_input.strip():
            res = init_team(team_name_input)
            if res:
                st.success(f"Team '{team_name_input}' created with ₹{res['cash']:.2f}")
                st.session_state.team = team_name_input
            else:
                port = fetch_portfolio(team_name_input)
                if port:
                    st.info(f"Team '{team_name_input}' logged in successfully.")
                    st.session_state.team = team_name_input
                else:
                    st.error("Error occurred. Try another team name.")
    st.stop()  # stop here until team is set

team_name = st.session_state.team

# ---------- ORGANIZER CONTROLS ----------
with st.expander("⚙️ Organizer Controls"):
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

# ---------- TIMER WITH PROGRESS BAR ----------
if st.session_state.round_start:
    if st.session_state.paused:
        elapsed = st.session_state.pause_time - st.session_state.round_start
    else:
        elapsed = time.time() - st.session_state.round_start

    remaining = max(0, ROUND_DURATION - elapsed)
    mins, secs = divmod(int(remaining), 60)
    progress = remaining / ROUND_DURATION

    if remaining <= 0:
        trading_allowed = False
        st.markdown("<h2 style='text-align:center; color:red;'>⏹️ Trading round has ended!</h2>", unsafe_allow_html=True)
        st.progress(0)
    else:
        trading_allowed = True
        # Color logic
        if remaining <= 10:
            color = "red"
            blink = True
        elif remaining <= 60:
            color = "orange"
            blink = False
        else:
            color = "green"
            blink = False

        # Blinking effect in last 10 seconds
        if blink:
            st.markdown(f"""
                <h1 style='text-align:center; color:{color};
                animation: blinker 1s linear infinite;'>{mins:02d}:{secs:02d}</h1>
                <style>@keyframes blinker {{ 50% {{ opacity: 0; }} }}</style>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"<h1 style='text-align:center; color:{color};'>⏱️ {mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
        
        # Progress bar
        st.progress(progress)
else:
    trading_allowed = False
    st.markdown("<h3 style='text-align:center; color:orange;'>⌛ Waiting for round to start...</h3>", unsafe_allow_html=True)
    st.progress(0)

# ---------- FETCH DATA ----------
stocks = fetch_stocks()
leaderboard = fetch_leaderboard()
news = fetch_news()
portfolio = fetch_portfolio(team_name)

# ---------- PORTFOLIO ----------
st.subheader("💼 Portfolio")
cash = portfolio.get("cash", 0)
holdings = portfolio.get("holdings", {})
st.metric("Available Cash", f"₹{cash:.2f}")

if holdings:
    holdings_df = pd.DataFrame.from_dict(holdings, orient="index")
    st.dataframe(holdings_df, use_container_width=True)
else:
    st.info("No holdings yet. Buy some stocks!")

# ---------- TRADE ----------
st.subheader("💸 Place Trade")
if stocks:
    col1, col2, col3, col4 = st.columns([2,2,1,1])
    with col1:
        selected_stock = st.selectbox("Select Stock", [s.get("symbol","") for s in stocks])
    with col2:
        qty = st.number_input("Quantity", min_value=1, step=1, value=1)
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

# ---------- STOCKS ----------
st.subheader("📊 Live Stock Prices")
if stocks:
    df = pd.DataFrame(stocks)
    if not df.empty:
        df["Trend"] = df.get("pct_change", pd.Series([0]*len(df))).apply(lambda x: "🟢" if x >=0 else "🔴")
        st.dataframe(df[["symbol","name","price","pct_change","Trend"]]
                     .rename(columns={"symbol":"Symbol","name":"Company","price":"Price","pct_change":"% Change"}), use_container_width=True)

        # 3D Chart
        df['volume'] = [i*1000 for i in range(1,len(df)+1)]
        fig3d = px.scatter_3d(df, x='price', y='pct_change', z='volume', color='Trend',
                              hover_name='name', size='price', size_max=18, opacity=0.8)
        fig3d.update_traces(marker=dict(line=dict(width=1,color='DarkSlateGrey')))
        fig3d.update_layout(scene=dict(xaxis_title="Price", yaxis_title="% Change", zaxis_title="Volume"), margin=dict(l=0,r=0,b=0,t=30))
        st.plotly_chart(fig3d, use_container_width=True)
else:
    st.warning("No stock data available right now.")

# ---------- LEADERBOARD ----------
st.subheader("🏆 Live Leaderboard")
if leaderboard:
    if isinstance(leaderboard, list) and len(leaderboard) > 0:
        ldf = pd.DataFrame(leaderboard)
        if "value" in ldf.columns:
            ldf = ldf.sort_values("value",ascending=False).reset_index(drop=True)
            ldf.index += 1
            def highlight_top3(row):
                if row.name==1: return ['background-color: gold; font-weight:bold']*len(row)
                elif row.name==2: return ['background-color: silver; font-weight:bold']*len(row)
                elif row.name==3: return ['background-color: #cd7f32; font-weight:bold']*len(row)
                else: return ['']*len(row)
            st.dataframe(ldf.style.apply(highlight_top3, axis=1), use_container_width=True, hide_index=False)
        else:
            st.warning("Leaderboard data missing 'value'. Check backend API.")
    else:
        st.info("Leaderboard is empty.")
else:
    st.info("No teams yet. Waiting for participants to trade...")

# ---------- NEWS ----------
st.subheader("📰 Market News")
articles = news.get("articles", [])
if articles:
    for article in articles:
        st.markdown(f"""
        <div style='background-color:white;padding:10px;margin-bottom:8px;border-radius:8px;
        box-shadow:0 2px 6px rgba(0,0,0,0.1)'>
            <b><a href="{article.get('url','#')}" target="_blank">{article.get('title','No Title')}</a></b><br>
            <span style="color:gray;font-size:12px;">{datetime.now().strftime('%H:%M:%S')}</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No news available right now.")

