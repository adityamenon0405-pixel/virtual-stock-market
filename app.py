import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
import time
from datetime import datetime
import plotly.express as px

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="📈 Virtual Stock Market - Round 2", layout="wide")

# ---------------- GLOBAL SETTINGS ----------------
BACKEND = "http://127.0.0.1:8000"  # Replace with your backend if available
ROUND_DURATION = 15 * 60           # 15 minutes per round
REFRESH_INTERVAL_MS = 1000         # 1 second refresh

# ---------------- AUTO REFRESH ----------------
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="refresh")

# ---------------- SESSION STATE (timer) ----------------
if "round_start" not in st.session_state:
    st.session_state.round_start = time.time()

# ---------------- TEAM LOGIN ----------------
if "team" not in st.session_state:
    st.title("🏁 Virtual Stock Market - Team Login")
    with st.form("login_form"):
        team_name = st.text_input("Enter your Team Name")
        password = st.text_input("Password / PIN (optional)", type="password")
        submitted = st.form_submit_button("Login ✅")

    if submitted and team_name.strip() != "":
        st.session_state["team"] = team_name.strip()
        st.experimental_rerun()
    else:
        st.stop()
else:
    st.sidebar.success(f"👥 Logged in as: {st.session_state['team']}")
    if st.sidebar.button("🚪 Logout"):
        del st.session_state["team"]
        st.experimental_rerun()

team = st.session_state["team"]

# ---------------- SAFE API CALL ----------------
def fetch_api(endpoint):
    try:
        url = f"{BACKEND}{endpoint}"
        r = requests.get(url, timeout=4)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"⚠️ API {endpoint} failed: {e}")
        return []

# ---------------- TIMER ----------------
elapsed = time.time() - st.session_state.round_start
remaining = max(0, ROUND_DURATION - elapsed)
st.markdown("## ⏳ Event Timer")
if remaining > 0:
    mins, secs = divmod(int(remaining), 60)
    st.success(f"Time Left: {mins:02}:{secs:02}")
else:
    st.error("⏹️ Round Over! Trading is closed.")
    st.stop()

st.divider()

# ---------------- INITIAL STOCK LIST ----------------
INITIAL_STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "price": 172.5, "pct_change": 0.0, "volume": 5000},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "price": 135.3, "pct_change": 0.0, "volume": 4000},
    {"symbol": "AMZN", "name": "Amazon.com, Inc.", "price": 3302.1, "pct_change": 0.0, "volume": 3500},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "price": 298.2, "pct_change": 0.0, "volume": 4500},
    {"symbol": "TSLA", "name": "Tesla, Inc.", "price": 880.0, "pct_change": 0.0, "volume": 4200},
    {"symbol": "META", "name": "Meta Platforms, Inc.", "price": 345.0, "pct_change": 0.0, "volume": 3800},
]

# ---------------- FETCH LIVE DATA ----------------
stocks = fetch_api("/stocks")
if not stocks:
    st.warning("⚠️ Using predefined stock list for this round.")
    stocks = INITIAL_STOCKS

portfolio = fetch_api(f"/portfolio/{team}")
leaderboard = fetch_api("/leaderboard")
news = fetch_api("/news")

# ---------------- STOCKS TABLE ----------------
st.markdown("## 💹 Stocks Market")
if stocks:
    df_stocks = pd.DataFrame(stocks)
    st.dataframe(df_stocks, use_container_width=True)
else:
    st.warning("⚠️ No stocks available yet.")

st.divider()

# ---------------- TRADE PANEL ----------------
st.markdown("## 🛒 Trade Stocks")
if remaining > 0 and stocks:
    stock_options = [s['symbol'] for s in stocks]
    with st.form("trade_form"):
        selected_stock = st.selectbox("Select Stock", stock_options)
        trade_qty = st.number_input("Quantity", min_value=1, value=1)
        action = st.radio("Action", ["Buy", "Sell"])
        submitted = st.form_submit_button("Execute Trade")

    if submitted:
        try:
            response = requests.post(
                f"{BACKEND}/trade",
                json={
                    "team": team,
                    "symbol": selected_stock,
                    "qty": trade_qty,
                    "action": action.lower()
                },
                timeout=4
            )
            response.raise_for_status()
            st.success(f"✅ {action} {trade_qty} shares of {selected_stock}")
        except Exception as e:
            st.error(f"⚠️ Trade failed: {e}")
elif remaining <= 0:
    st.info("⏹️ Trading disabled. Round is over.")

st.divider()

# ---------------- 3D STOCK CHART ----------------
st.markdown("## 📊 Live 3D Stock Market View")
if stocks:
    if "volume" not in df_stocks.columns:
        df_stocks["volume"] = [(i+1)*1000 for i in range(len(df_stocks))]
    df_stocks["label"] = df_stocks.apply(
        lambda r: f"{r.get('symbol','')}: {r.get('name','')}\nPrice: ₹{r['price']}\nChange: {r['pct_change']}%", axis=1)

    fig3d = px.scatter_3d(
        df_stocks,
        x="price",
        y="pct_change",
        z="volume",
        color="pct_change",
        color_continuous_scale=px.colors.diverging.RdYlGn,
        hover_name="symbol",
        hover_data={"name": True, "price": True, "pct_change": True, "volume": True},
        size="price",
        size_max=30,
        title="💎 Price vs % Change vs Volume (3D)",
    )
    fig3d.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey'), opacity=0.85))
    fig3d.update_layout(
        scene=dict(xaxis_title='Price (₹)', yaxis_title='% Change', zaxis_title='Volume'),
        margin=dict(l=0, r=0, t=40, b=0),
        coloraxis_colorbar=dict(title="% Change"),
        template="plotly_white",
    )
    st.plotly_chart(fig3d, use_container_width=True)

st.divider()

# ---------------- TEAM PORTFOLIO ----------------
st.markdown("## 💼 Your Portfolio")
if portfolio:
    df_portfolio = pd.DataFrame(portfolio)
    if "Value" not in df_portfolio.columns and "Qty" in df_portfolio.columns and "Price" in df_portfolio.columns:
        df_portfolio["Value"] = df_portfolio["Qty"] * df_portfolio["Price"]
    st.dataframe(df_portfolio, use_container_width=True)
    total_value = df_portfolio['Value'].sum()
    st.info(f"💰 Total Portfolio Value: ₹{total_value}")

st.divider()

# ---------------- LEADERBOARD ----------------
st.markdown("## 🏆 Leaderboard")
if leaderboard:
    df_lb = pd.DataFrame(leaderboard)
    df_lb = df_lb.sort_values(by=df_lb.columns[-1], ascending=False).reset_index(drop=True)
    df_lb.index += 1

    def highlight_top3(row):
        if row.name == 0: return ['background-color: gold']*len(row)
        if row.name == 1: return ['background-color: silver']*len(row)
        if row.name == 2: return ['background-color: #cd7f32']*len(row)
        return ['']*len(row)

    st.dataframe(df_lb.style.apply(highlight_top3, axis=1), use_container_width=True)

st.divider()

# ---------------- NEWS ----------------
st.markdown("## 📰 Market News")
if news:
    for item in news[:5]:
        title = item.get("title") or item.get("headline") or "(no title)"
        url = item.get("url")
        timestamp = item.get("publishedAt") or datetime.now().strftime("%H:%M:%S")
        if url:
            st.markdown(f"- 🔗 [{title}]({url})  <span style='color:gray;font-size:12px'>{timestamp}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"- 📝 {title}  <span style='color:gray;font-size:12px'>{timestamp}</span>", unsafe_allow_html=True)

st.divider()
st.caption(f"Backend: {BACKEND} • Last refresh: {datetime.now().strftime('%H:%M:%S')}")
