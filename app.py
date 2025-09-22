import streamlit as st
import requests
import json
import os
import pandas as pd

st.set_page_config(page_title="📈 Virtual Stock Market", layout="wide")

# Backend URL from environment variable or default
BACKEND = os.environ.get("BACKEND", "https://your-render-backend.onrender.com")

# ---- Session State ----
if "team" not in st.session_state:
    st.session_state.team = None

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
    team_name_input = st.text_input("Enter Team Name")
    if st.button("Create Team"):
        if team_name_input.strip() == "":
            st.warning("Please enter a valid team name.")
        else:
            res = init_team(team_name_input)
            if res:
                st.success(f"Team '{team_name_input}' created with ₹{res['cash']:.2f}")
                st.session_state.team = team_name_input
            else:
                st.error("Team already exists or error occurred.")
    st.stop()  # Stop execution until team is registered

# ---- Main Dashboard ----
team_name = st.session_state.team

# ---- Fetch Data ----
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
            else:
                st.error("Failed to buy. Check cash balance.")
    with col4:
        if st.button("Sell"):
            res = trade(team_name, selected_stock, -int(qty))
            if res:
                st.success(f"✅ Sold {qty} o
