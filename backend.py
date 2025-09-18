from flask import Flask, request, jsonify
from threading import Thread
import time, random

app = Flask(__name__)

# ---- DATA STORAGE ----
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

Thread(target=update_prices, daemon=True).start()

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
