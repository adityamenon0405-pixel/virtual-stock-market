# app.py (Streamlit Frontend with Charts + News)
import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import plotly.express as px

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="📈 Virtual Stock Market", layout="wide")

# ---------- BACKEND ----------
BACKEND = "https://virtual-stock-market-7mxp.onrender.com"  # <-- change to your backend

# ---------- STYLING ----------
st.markdown("""
    <style>
    body { background-color: #F9FAFB; }
    .stApp { background-color: #F9FAFB; }
    .css-1d391kg, .css-18e3th9 {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    }
    .stock-card {
        background-color: white;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    a { text-decoration: none; color: inherit; }
    </style>
""", unsafe_allow_html=True)

# ---------- SESSION STATE ----------
if "team" not in st.session_state:
    st.session_state.team = None
if "price_history" not in st.session_state:
    st.session_state.price_history = {}

# ---------- DATA FETCHERS (cached where appropriate) ----------
@st.cache_data(ttl=5)
def fetch_stocks():
    try:
        r = requests.get(f"{BACKEND}/stocks", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

@st.cache_data(ttl=5)
def fetch_leaderboard():
    try:
        r = requests.get(f"{BACKEND}/leaderboard", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

@st.cache_data(ttl=60)
def fetch_news(q: str = "stock market"):
    try:
        r = requests.get(f"{BACKEND}/news", params={"q": q}, timeout=6)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    # return empty shape consistent with backend
    return {"source": "none", "articles": []}

def fetch_portfolio(team):
    try:
        r = requests.get(f"{BACKEND}/portfolio/{team}", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def trade(team, symbol, qty):
    try:
        r = requests.post(f"{BACKEND}/trade", json={"team": team, "symbol": symbol, "qty": qty}, timeout=6)
        return r.json(), r.status_code
    except:
        return {"detail": "Server error"}, 500

# ---------- UI ----------
st.title("📊 Virtual Stock Market")
st.caption("Realistic trading dashboard — prices, charts, trades, leaderboard & news.")

# ---- Team Login / Setup ----
if st.session_state.team is None:
    st.subheader("👥 Join the Market")
    team_name = st.text_input("Enter Team Name:")
    if st.button("Register / Join"):
        if team_name.strip():
            r = requests.post(f"{BACKEND}/init_team", json={"team": team_name.strip()})
            if r.status_code in [200, 400]:  # 400 = already exists
                st.session_state.team = team_name.strip()
                st.experimental_rerun()
            else:
                st.error("Server error, try again.")
    st.stop()

st.success(f"✅ Logged in as **{st.session_state.team}**")

# ---------- Fetch data ----------
stocks = fetch_stocks()
leaderboard = fetch_leaderboard()
news_payload = fetch_news()  # cached 60s
portfolio = fetch_portfolio(st.session_state.team)

# ---------- Update price history for charts ----------
if stocks:
    for s in stocks:
        sym = s["symbol"]
        price = s["price"]
        hist = st.session_state.price_history.get(sym, [])
        hist.append({"time": time.time(), "price": price})
        st.session_state.price_history[sym] = hist[-30:]  # keep last 30 points

# ---------- Layout: Main columns ----------
left_col, right_col = st.columns([2, 1])

with left_col:
    # Live Prices table
    st.subheader("📈 Live Prices")
    if not stocks:
        st.error("Could not load stocks.")
    else:
        df = pd.DataFrame(stocks)
        df["Price"] = df["price"].round(2)
        df["Change %"] = df["pct_change"].map(lambda x: f"{x:+.2f}%")
        df = df[["symbol", "name", "Price", "Change %"]].rename(
            columns={"symbol": "Symbol", "name": "Name"})
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Portfolio
    st.subheader("💼 Portfolio")
    if portfolio:
        st.metric("Cash Balance", f"₹{portfolio['cash']:,}")
        if portfolio["holdings"]:
            port_df = pd.DataFrame([
                {"Symbol": k, "Qty": v["qty"], "Price": v["price"], "Value": v["value"]}
                for k, v in portfolio["holdings"].items()
            ])
            st.dataframe(port_df, use_container_width=True, hide_index=True)
        else:
            st.info("No holdings yet. Buy some stocks to get started!")
    else:
        st.info("Portfolio not loaded. (Server may be slow)")

    # Trade + Chart area
    st.subheader("🛒 Trade & Chart")
    chart_col, trade_col = st.columns([2, 1])

    with trade_col:
        if stocks:
            symbol = st.selectbox("Select Stock", [s["symbol"] for s in stocks])
        else:
            symbol = ""
        qty = st.number_input("Quantity", min_value=1, step=1, value=1)
        action = st.selectbox("Action", ["BUY", "SELL"])
        if st.button("Submit Trade"):
            if symbol:
                order_qty = qty if action == "BUY" else -qty
                resp, code = trade(st.session_state.team, symbol, order_qty)
                if code == 200:
                    st.success("✅ Trade Executed!")
                    st.cache_data.clear()  # refresh cached endpoints (stocks/leaderboard/news)
                else:
                    # Show backend error message if available
                    detail = resp.get("detail") if isinstance(resp, dict) else None
                    st.error(detail or "Trade failed")

    with chart_col:
        if symbol and symbol in st.session_state.price_history and len(st.session_state.price_history[symbol]) > 1:
            hist = pd.DataFrame(st.session_state.price_history[symbol])
            hist["time"] = pd.to_datetime(hist["time"], unit="s")
            fig = px.line(hist, x="time", y="price", title=f"{symbol} Price Trend", markers=True)
            fig.update_layout(xaxis_title="Time", yaxis_title="Price", template="plotly_white", height=320,
                              margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select a stock to view its mini-chart (updates automatically).")

    # Leaderboard
    st.subheader("🏆 Leaderboard")
    if leaderboard and isinstance(leaderboard, list):
        lb_df = pd.DataFrame(leaderboard)
        # if backend returns 'value' or 'portfolio_value', normalize to 'value' for display
        if "portfolio_value" in lb_df.columns and "value" not in lb_df.columns:
            lb_df["value"] = lb_df["portfolio_value"]
        # show basic columns
        display_cols = [c for c in ["team", "value"] if c in lb_df.columns]
        if display_cols:
            st.dataframe(lb_df[display_cols].rename(columns={"team": "Team", "value": "Value"}), use_container_width=True,
                         hide_index=True)
        else:
            st.json(leaderboard)
    else:
        st.info("Leaderboard empty or not available.")

with right_col:
    # NEWS
    st.subheader("📰 Market News")
    articles = news_payload.get("articles", []) if isinstance(news_payload, dict) else []
    if articles:
        # optional filter/search box
        q = st.text_input("Search news (optional)", value="")
        if st.button("Refresh News"):
            st.cache_data.clear()  # clears cached news too
            st.experimental_rerun()
        # show articles (apply search filter if provided)
        count = 0
        for a in articles:
            title = a.get("title", "No Title")
            url = a.get("url", "#")
            source = a.get("source", "")
            if q and q.lower() not in title.lower():
                continue
            count += 1
            st.markdown(
                f"""
                <div style='background-color:#ffffff;padding:10px;margin-bottom:10px;border-radius:8px;
                    box-shadow:0 1px 6px rgba(0,0,0,0.04)'>
                    <b><a href="{url}" target="_blank">{title}</a></b><br>
                    <span style="color:gray;font-size:12px;">{source} • {datetime.now().strftime('%H:%M:%S')}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            if count >= 8:
                break
        if count == 0:
            st.info("No matching articles found.")
    else:
        st.info("No news available right now. (Check NEWS_API_KEY or backend)")

    # small footer / quick controls
    st.markdown("---")
    st.caption("Tip: use the 'Refresh News' button to fetch latest headlines immediately.")

