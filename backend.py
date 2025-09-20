# backend.py
from flask import Flask, request, jsonify
from random import randint

app = Flask(__name__)

# -----------------------------
# In-memory storage
# -----------------------------
users = {}  # {"username": {"cash": 100000, "portfolio": {"TATA": 10}}}

# Initial stock prices
stocks = {
    "TATA": 1000,
    "RELIANCE": 2400,
    "INFY": 1500,
    "ADANI": 1100,
    "HDFC": 1200
}

# -----------------------------
# Helper to update stock prices randomly
# -----------------------------
def update_stock_prices():
    for stock in stocks:
        # Randomly change price by -2% to +2%
        change_pct = randint(-20, 20) / 1000  # -2% to +2%
        stocks[stock] = max(1, round(stocks[stock] * (1 + change_pct), 2))

# -----------------------------
# Routes
# -----------------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"message": "Username required"}), 400

    if username not in users:
        users[username] = {"cash": 100000, "portfolio": {}}

    return jsonify({"message": f"User {username} registered"}), 200

@app.route("/prices", methods=["GET"])
def get_prices():
    update_stock_prices()
    return jsonify(stocks)

@app.route("/buy", methods=["POST"])
def buy_stock():
    data = request.get_json()
    username = data.get("username")
    stock = data.get("stock")
    qty = int(data.get("qty", 1))

    if username not in users:
        return jsonify({"message": "User not found"}), 400
    if stock not in stocks:
        return jsonify({"message": "Invalid stock"}), 400

    total_price = stocks[stock] * qty
    if users[username]["cash"] < total_price:
        return jsonify({"message": "Not enough cash"}), 400

    users[username]["cash"] -= total_price
    users[username]["portfolio"][stock] = users[username]["portfolio"].get(stock, 0) + qty
    return jsonify({"message": f"Bought {qty} {stock} shares"}), 200

@app.route("/sell", methods=["POST"])
def sell_stock():
    data = request.get_json()
    username = data.get("username")
    stock = data.get("stock")
    qty = int(data.get("qty", 1))

    if username not in users:
        return jsonify({"message": "User not found"}), 400
    if stock not in stocks:
        return jsonify({"message": "Invalid stock"}), 400
    if users[username]["portfolio"].get(stock, 0) < qty:
        return jsonify({"message": "Not enough shares"}), 400

    total_price = stocks[stock] * qty
    users[username]["cash"] += total_price
    users[username]["portfolio"][stock] -= qty
    if users[username]["portfolio"][stock] == 0:
        del users[username]["portfolio"][stock]
    return jsonify({"message": f"Sold {qty} {stock} shares"}), 200

@app.route("/portfolio/<username>", methods=["GET"])
def get_portfolio(username):
    if username not in users:
        return jsonify({"message": "User not found"}), 400

    portfolio = []
    net_worth = users[username]["cash"]
    for stock, qty in users[username]["portfolio"].items():
        price = stocks[stock]
        total_value = price * qty
        net_worth += total_value
        portfolio.append({"Stock": stock, "Qty": qty, "Price": price, "Total": total_value})

    return jsonify({
        "cash": users[username]["cash"],
        "net_worth": net_worth,
        "portfolio": portfolio
    })

@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    lb = []
    for username, data in users.items():
        net_worth = data["cash"]
        for stock, qty in data["portfolio"].items():
            net_worth += stocks[stock] * qty
        lb.append({"username": username, "net_worth": net_worth})

    lb = sorted(lb, key=lambda x: x["net_worth"], reverse=True)
    return jsonify(lb)

# -----------------------------
# Run server
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
