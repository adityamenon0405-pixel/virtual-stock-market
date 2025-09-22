import streamlit as st
import requests
import json
import os
import pandas as pd

st.set_page_config(page_title="📈 Virtual Stock Market", layout="wide")

# ✅ Backend URL from secret or fallback to Render URL
BACKEND = os.environ.get("BACKEND", "https://virtual-stock-market-7mxp.onrender.com")

# ✅ Use st.query_params (no deprecation warning)
params = st.query_params

# ---- Utility Functions ----
def fetch_stocks():
    return requests.get(f"{BACKEND}/stocks", timeout=6).json()

def fetch_leaderboard():
    return requests.get(f"{BACKEND}/leaderboard", timeout=6).json()

def fetch_news():
    return requests.get(f"{BACKEND}/news", timeout=6).json()

def fetch_portfolio(team):
    r = requests.get(f"{BACKEND}/portfolio/{team}", timeout=6)
    if r.status_code == 200:
        return r.json()
    return None

def init_team(team):
    r = requests.post(f"{BACKEND}/init_team", json={"team": team})
    return r.json() if r.status_code == 200 else None

def trade(team, symbol, qty):
    r = requests.post(f"{BACKEND}/trade", json={"team": team, "symbol": symbol, "qty": qty})
    return r.json() if r.status_code == 200 else None

# ---- Sidebar: Team Selection ----
st.sidebar.title("👥 Team Setup")
team_name = st.sidebar.text_input("Enter Team Name", value=params.get("team", [""])[0])

if team_name:
    st.query_params["team"] = team_name  # Persist in URL
    if st.sidebar.button("Create Team / Reset"):
        res = init_team(team_name)
        if res:
            st.sidebar.success(f"Team '{team_name}' initialized with ₹{res['cash']:.2f}")
        else:
            st.sidebar.warning("Team already exists or error occurred.")
else:
    st.sidebar.warning("Enter a team name to start.")

# ---- Fetch Data ----
try:
    stocks = fetch_stocks()
    leaderboard = fetch_leaderboard()
    news = fetch_news()
except requests.exceptions.RequestException as e:
    st.error(f"❌ Could not connect to backend. Check BACKEND URL. Error: {e}")
    st.stop()

# ---- Portfolio Section ----
if team_name:
    portfolio = fetch_portfolio(team_name)
    if portfolio:
        st.subheader(f"📊 Portfolio for {team_name}")
        st.metric("Total Portfolio Value", f"₹{portfolio['portfolio_value']:.2f}")
        st.write(f"💵 **Cash:** ₹{portfolio['cash']:.2f}")

        if portfolio["holdings"]:
            holdings_df = pd.DataFrame.from_dict(portfolio["holdings"], orient="index")
            st.dataframe(holdings_df, use_container_width=True)
        else:
            st.info("No holdings yet. Buy some stocks!")

        # ---- Buy/Sell Form ----
        st.subheader("💸 Place Trade")
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        with col1:
            selected_stock = st.selectbox("Select Stock", [s["symbol"] for s in stocks])
        with col2:
            qty = st.number_input("Quantity", min_value=1, step=1, value=1)
        with col3:
            if st.button("Buy"):
                res = trade(team_name, selected_stock, int(qty))
                if res:
                    st.success(f"✅ Bought {qty} of {selected_stock}")
                    st.experimental_rerun()
                else:
                    st.error("Failed to buy. Check cash balance.")
        with col4:
            if st.button("Sell"):
                res = trade(team_name, selected_stock, -int(qty))
                if res:
                    st.success(f"✅ Sold {qty} of {selected_stock}")
                    st.experimental_rerun()
                else:
                    st.error("Failed to sell. Check holdings.")
    else:
        st.warning("Team not found. Click 'Create Team' in sidebar.")
else:
    st.info("👈 Enter a team name in the sidebar to view portfolio & trade.")

# ---- Stocks Section ----
st.subheader("💹 Live Stock Prices")
df = pd.DataFrame(stocks)
if not df.empty:
    df["Trend"] = df["pct_change"].apply(lambda x: "🟢" if x >= 0 else "🔴")
    st.dataframe(df[["symbol", "name", "price", "pct_change", "Trend"]].rename(columns={
        "symbol": "Symbol",
        "name": "Company",
        "price": "Price",
        "pct_change": "% Change"
    }), use_container_width=True)
else:
    st.warning("No stock data available.")

# ---- Leaderboard ----
st.subheader("🏆 Leaderboard")
if leaderboard:
    ldf = pd.DataFrame(leaderboard)
    st.dataframe(ldf, use_container_width=True)
else:
    st.info("No teams yet.")

# ---- News ----
st.subheader("📰 Market News")
if news.get("articles"):
    for article in news["articles"]:
        st.markdown(f"🔗 [{article['title']}]({article['url']})")
else:
    st.info("No news available right now.")

