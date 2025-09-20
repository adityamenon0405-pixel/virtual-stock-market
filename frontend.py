import streamlit as st
import requests
import pandas as pd
import time

# -------------------------------
# CONFIG
# -------------------------------
API_URL = "https://your-backend-url.onrender.com"  # Change this to your backend URL

st.set_page_config(page_title="Game of Trades", page_icon="📈", layout="wide")

# -------------------------------
# SESSION STATE
# -------------------------------
if "username" not in st.session_state:
    st.session_state.username = None

# -------------------------------
# FUNCTIONS
# -------------------------------
def get_status():
    try:
        res = requests.get(f"{API_URL}/status")
        return res.json()
    except:
        return {"active": False, "remaining_seconds": 0, "frozen": True}

def register_user(username):
    res = requests.post(f"{API_URL}/register", json={"username": username})
    return res

def get_prices():
    return requests.get(f"{API_URL}/prices").json()

def get_portfolio(username):
    return requests.get(f"{API_URL}/portfolio/{username}").json()

def buy_stock(username, stock, qty):
    return requests.post(f"{API_URL}/buy", json={"username": username, "stock": stock, "qty": qty}).json()

def sell_stock(username, stock, qty):
    return requests.post(f"{API_URL}/sell", json={"username": username, "stock": stock, "qty": qty}).json()

def get_leaderboard():
    return requests.get(f"{API_URL}/leaderboard").json()

# -------------------------------
# HEADER
# -------------------------------
st.title("📈 Game of Trades")
st.caption("Welcome to the virtual stock market event! Trade smart, grow your portfolio, and top the leaderboard.")

# -------------------------------
# EVENT STATUS CHECK
# -------------------------------
status = get_status()
if not status["active"]:
    st.error("⏳ Event Over! Final Results:")
    leaderboard = get_leaderboard()
    if leaderboard:
        winner = leaderboard[0]
        st.success(f"🏆 **Winner:** {winner['username']} with Net Worth ₹{winner['net_worth']}")
        st.subheader("🏁 Final Leaderboard")
        st.table(pd.DataFrame(leaderboard))
    st.stop()

# -------------------------------
# USER REGISTRATION
# -------------------------------
if not st.session_state.username:
    st.subheader("📝 Register to Play")
    username = st.text_input("Enter your username")
    if st.button("Register"):
        if username.strip():
            res = register_user(username)
            if res.status_code in [200, 400]:  # Registered or already exists
                st.session_state.username = username
                st.rerun()
            else:
                st.error(res.json().get("message", "Could not register"))
    st.stop()

# -------------------------------
# MAIN TRADING DASHBOARD
# -------------------------------
st.sidebar.header(f"👋 Hello, {st.session_state.username}")
st.sidebar.info(f"⏳ Time Left: **{status['remaining_seconds']//60} min {status['remaining_seconds']%60} sec**")
st.sidebar.button("🔄 Refresh", on_click=st.rerun)

# --- Prices ---
st.subheader("📊 Live Stock Prices")
prices = get_prices()
df_prices = pd.DataFrame(list(prices.items()), columns=["Stock", "Price"])
st.dataframe(df_prices, use_container_width=True)

# --- Trading ---
st.subheader("💰 Trade Stocks")
col1, col2 = st.columns(2)

with col1:
    selected_stock = st.selectbox("Choose Stock to Buy/Sell", df_prices["Stock"])
    qty = st.number_input("Quantity", min_value=1, step=1)
    if st.button("Buy"):
        res = buy_stock(st.session_state.username, selected_stock, qty)
        st.success(res.get("message", "Trade executed"))
        st.rerun()

with col2:
    if st.button("Sell"):
        res = sell_stock(st.session_state.username, selected_stock, qty)
        if "message" in res:
            st.success(res["message"])
        else:
            st.error("Unable to sell. Check your holdings.")
        st.rerun()

# --- Portfolio ---
st.subheader("📦 Your Portfolio")
portfolio = get_portfolio(st.session_state.username)
st.metric("Available Cash", f"₹{portfolio['cash']}")
st.metric("Net Worth", f"₹{portfolio['net_worth']}")
if portfolio["portfolio"]:
    df_portfolio = pd.DataFrame(portfolio["portfolio"])
    st.table(df_portfolio)
else:
    st.info("You have no holdings yet.")

# --- Leaderboard ---
st.subheader("🏆 Leaderboard")
leaderboard = get_leaderboard()
df_leaderboard = pd.DataFrame(leaderboard)
st.table(df_leaderboard)

# Auto-refresh every 15 seconds
time.sleep(15)
st.rerun()
