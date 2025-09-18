import streamlit as st
import requests
import pandas as pd
import time

# TODO: Replace with your deployed backend URL
API_URL = "https://your-backend-service.onrender.com"

st.set_page_config(page_title="Virtual Stock Market", layout="wide")

if "username" not in st.session_state:
    st.session_state.username = ""

if st.session_state.username == "":
    username = st.text_input("Enter your username:")
    if st.button("Register/Login"):
        res = requests.post(f"{API_URL}/register", json={"username": username})
        if res.status_code in [200, 400]:
            st.session_state.username = username
            st.experimental_rerun()
        else:
            st.error("Could not register")

else:
    st.title("📈 Virtual Stock Market")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Live Stock Prices")
        prices = requests.get(f"{API_URL}/prices").json()
        df = pd.DataFrame(list(prices.items()), columns=["Stock", "Price"])
        st.table(df)

        stock_choice = st.selectbox("Select Stock", list(prices.keys()))
        qty = st.number_input("Quantity", min_value=1, value=1)
        buy_col, sell_col = st.columns(2)
        with buy_col:
            if st.button("Buy"):
                res = requests.post(f"{API_URL}/buy", json={"username": st.session_state.username, "stock": stock_choice, "qty": qty})
                st.success(res.json()["message"])
        with sell_col:
            if st.button("Sell"):
                res = requests.post(f"{API_URL}/sell", json={"username": st.session_state.username, "stock": stock_choice, "qty": qty})
                st.success(res.json()["message"])

    with col2:
        st.subheader(f"💼 {st.session_state.username}'s Portfolio")
        portfolio_data = requests.get(f"{API_URL}/portfolio/{st.session_state.username}").json()
        st.write(f"💵 **Cash:** ₹{portfolio_data['cash']}")
        st.write(f"📊 **Net Worth:** ₹{portfolio_data['net_worth']}")
        if portfolio_data["portfolio"]:
            df_portfolio = pd.DataFrame(portfolio_data["portfolio"])
            st.table(df_portfolio)
        else:
            st.info("No holdings yet. Buy some stocks!")

        st.subheader("🏆 Leaderboard")
        leaderboard = requests.get(f"{API_URL}/leaderboard").json()
        df_lb = pd.DataFrame(leaderboard)
        st.table(df_lb)

    time.sleep(10)
    st.experimental_rerun()
