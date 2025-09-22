import streamlit as st
import requests
import json
import os
import pandas as pd

st.set_page_config(page_title="📈 Virtual Stock Market", layout="wide")

# Backend URL from environment variable or default to Render backend
BACKEND = os.environ.get("BACKEND", "https://virtual-stock-market-7mxp.onrender.com")

# Initialize session state
if "team" not in st.session_state:
    st.session_state.team = None
if "refresh" not in st.session_state:
    st.session_state.refresh = False

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

# ---- Starting Page: Team Registration ----
if st.session_state.team is None:
    st.title("👥 Register Your Team")
    team_name = st.text_input("Enter Team Name")
    if st.button("Create Team"):
        if team_name.strip() == "":
            st.warning("Please enter a valid team name.")
        else:
            res = init_team(team_name)
            if res:
                st.success(f"Team '{team_name}' created with ₹{res['cash']:.2f}")
                st.session_state.team = team_name
                st.experimental_rerun()
            else:
                st.error("Team already exists or error occurred.")
    st.stop()  # Stop execution until team is registered

# ---- Main Dashboard ----
team_name = st.session_state.team

try:
    stocks = fetch_stocks()
    leaderboard = fetch_leaderboard()
    news = fetch_news()
except requests.exceptions.RequestException as e:
    st.error(f"❌ Could not connect to backend. Check BACKEND URL. Error: {e}")
    st.stop()

# ---- Portfolio Section ----
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
                st.session_state.refresh = not st.session_state.refresh
            else:
                st.error("Failed to buy. Check cash balance.")
    with col4:
        if st.button("Sell"):
            res = trade(team_name, selected_stock, -int(qty))
            if res:
                st.success(f"✅ Sold {qty} of {selected_stock}")
                st.session_state.refresh = not st.session_state.refresh
            else:
                st.error("Failed to sell. Check holdings.")

    # Trigger rerun if refresh toggled
    if st.session_state.refresh:
        st.session_state.refresh = False
        st.experimental_rerun()
else:
    st.warning("Portfolio not found. Try creating a new team.")

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
