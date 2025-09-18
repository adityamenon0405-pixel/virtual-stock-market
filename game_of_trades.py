# game_of_trades.py
import threading
import time
import random
import requests
import pandas as pd
import streamlit as st
from flask import Flask, request, jsonify
from werkzeug.serving import make_server

# ---------------------------
# BACKEND - FLASK API
# ---------------------------
app = Flask(__name__)

stocks = {
    "TATA": 100.0,
    "RELIANCE": 200.0,
    "INFY": 150.0,
    "ADANI": 250.0,
    "HDFC": 300.0
}
users = {}  # username -> {"cash": 100000, "portfolio": {"TATA": 10}}

def update_prices():
    while True:
        time.sleep(60)
        for stock in stocks:
            change = random.uniform(-5, 5)
            stocks[stock] = max(1, round(stocks[stock] + change, 2))

@app.route("/register", methods=["POST"])
def register():
    username = request.json.get("username")
    if username in users:
        return jsonify({"message": "User already exists"}), 400
    users[username] = {"cash": 100000, "portfolio": {}}
    return jsonify({"message": "Registered successfully"}), 200

@app.route("/prices", methods=["GET"])
def get_prices():
    return jsonify(stocks)

@app.route("/buy", methods=["POST"])
def buy_stock():
    data = request.json
    username, stock, qty = data["username"], data["stock"], int(data["qty"])
    price = stocks.get(stock)
    if username not in users:
        return jsonify({"message": "User not found"}), 404
    cost = price * qty
    if users[username]["cash"] < cost:
        return jsonify({"message": "Insufficient funds"}), 400
    users[username]["cash"] -= cost
    users[username]["portfolio"][stock] = users[username]["portfolio"].get(stock, 0) + qty
    return jsonify({"message": "Bought successfully"}), 200

@app.route("/sell", methods=["POST"])
def sell_stock():
    data = request.json
    username, stock, qty = data["username"], data["stock"], int(data["qty"])
    price = stocks.get(stock)
    if username not in users or users[username]["portfolio"].get(stock, 0) < qty:
        return jsonify({"message": "Not enough shares"}), 400
    users[username]["portfolio"][stock] -= qty
    users[username]["cash"] += price * qty
    return jsonify({"message": "Sold successfully"}), 200

@app.route("/portfolio/<username>", methods=["GET"])
def get_portfolio(username):
    if username not in users:
        return jsonify({"message": "User not found"}), 404
    user = users[username]
    portfolio_details = []
    total_value = user["cash"]
    for stock, qty in user["portfolio"].items():
        stock_value = stocks[stock] * qty
        portfolio_details.append({
            "stock": stock,
            "qty": qty,
            "price": stocks[stock],
            "value": round(stock_value, 2)
        })
        total_value += stock_value
    return jsonify({
        "cash": round(user["cash"], 2),
        "portfolio": portfolio_details,
        "net_worth": round(total_value, 2)
    })

@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    leaderboard = []
    for username, data in users.items():
        total_value = data["cash"]
        for stock, qty in data["portfolio"].items():
            total_value += qty * stocks[stock]
        leaderboard.append({"username": username, "value": round(total_value, 2)})
    leaderboard.sort(key=lambda x: x["value"], reverse=True)
    return jsonify(leaderboard)

# ---- Run Flask in background thread ----
class ServerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = make_server('127.0.0.1', 5000, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()

server = ServerThread(app)
server.daemon = True
server.start()

# Start stock price updates
threading.Thread(target=update_prices, daemon=True).start()

# ---------------------------
# FRONTEND - STREAMLIT
# ---------------------------
API_URL = "http://127.0.0.1:5000"

st.set_page_config(page_title="Virtual Stock Market", layout="wide")

if "username" not in st.session_state:
    st.session_state.username = ""

if st.session_state.username == "":
    username = st.text_input("Enter your username:")
    if st.button("Register/Login"):
        res = requests.post(f"{API_URL}/register", json={"username": username})
        if res.status_code in [200, 400]:  # already exists
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
