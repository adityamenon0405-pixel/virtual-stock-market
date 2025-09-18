import streamlit as st
import requests
import pandas as pd
import time
import plotly.express as px

# -----------------------------
# CONFIGURE YOUR BACKEND URL
# -----------------------------
API_URL = "https://virtual-stock-backend.onrender.com"  # Replace with your deployed backend URL

st.set_page_config(page_title="Virtual Stock Market", layout="wide")

# -----------------------------
# SESSION STATE SETUP
# -----------------------------
if "username" not in st.session_state:
    st.session_state.username = ""
if "rerun_flag" not in st.session_state:
    st.session_state.rerun_flag = False

stocks_list = ["TATA", "RELIANCE", "INFY", "ADANI", "HDFC"]

if "price_history" not in st.session_state:
    st.session_state.price_history = {stock: [] for stock in stocks_list}
if "time_points" not in st.session_state:
    st.session_state.time_points = []

# -----------------------------
# LOGIN / REGISTER
# -----------------------------
if st.session_state.username == "":
    username = st.text_input("Enter your username:")
    if st.button("Register/Login"):
        res = requests.post(f"{API_URL}/register", json={"username": username})
        if res.status_code in [200, 400]:
            st.session_state.username = username
            # Force Streamlit rerun
            st.session_state.rerun_flag = not st.session_state.rerun_flag
        else:
            st.error("Could not register")
else:
    st.title("📈 Virtual Stock Market")

    # -----------------------------
    # FETCH CURRENT PRICES
    # -----------------------------
    try:
        prices = requests.get(f"{API_URL}/prices").json()
    except:
        st.error("Could not connect to backend. Check your backend URL and server.")
        st.stop()

    # Update session state for charts
    current_time = pd.Timestamp.now().strftime("%H:%M:%S")
    st.session_state.time_points.append(current_time)
    for stock in stocks_list:
        st.session_state.price_history[stock].append(prices[stock])

    # -----------------------------
    # LAYOUT
    # -----------------------------
    col1, col2 = st.columns([2, 1])

    # -----------------------------
    # LEFT COLUMN: STOCKS + CHARTS
    # -----------------------------
    with col1:
        # ----- Stock Prices Table with % Change -----
        st.subheader("💹 Live Stock Prices")
        data = []
        for stock in stocks_list:
            current_price = prices[stock]
            prev_price = st.session_state.price_history[stock][-2] if len(st.session_state.price_history[stock]) > 1 else current_price
            change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price != 0 else 0
            arrow = "▲" if change_pct > 0 else ("▼" if change_pct < 0 else "-")
            data.append({
                "Stock": stock,
                "Price": current_price,
                "Change (%)": f"{arrow} {round(change_pct,2)}%"
            })

        df_prices = pd.DataFrame(data)

        def color_change(val):
            if "▲" in val:
                color = 'green'
            elif "▼" in val:
                color = 'red'
            else:
                color = 'black'
            return f'color: {color}'

        st.dataframe(df_prices.style.applymap(color_change, subset=["Change (%)"]))

        # ----- Buy/Sell Controls -----
        stock_choice = st.selectbox("Select Stock", stocks_list)
        qty = st.number_input("Quantity", min_value=1, value=1)
        buy_col, sell_col = st.columns(2)
        with buy_col:
            if st.button("Buy"):
                res = requests.post(f"{API_URL}/buy", json={
                    "username": st.session_state.username,
                    "stock": stock_choice,
                    "qty": qty
                })
                st.success(res.json()["message"])
        with sell_col:
            if st.button("Sell"):
                res = requests.post(f"{API_URL}/sell", json={
                    "username": st.session_state.username,
                    "stock": stock_choice,
                    "qty": qty
                })
                st.success(res.json()["message"])

        # ----- Live Price Charts -----
        st.subheader("📊 Stock Price Trends (Live)")
        for stock in stocks_list:
            df_chart = pd.DataFrame({
                "Time": st.session_state.time_points,
                "Price": st.session_state.price_history[stock]
            })
            fig = px.line(df_chart, x="Time", y="Price",
                          title=f"{stock} Price Trend",
                          markers=True)
            st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # RIGHT COLUMN: PORTFOLIO + LEADERBOARD
    # -----------------------------
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

    # -----------------------------
    # REFRESH EVERY 10 SECONDS
    # -----------------------------
    time.sleep(10)
    st.session_state.rerun_flag = not st.session_state.rerun_flag
