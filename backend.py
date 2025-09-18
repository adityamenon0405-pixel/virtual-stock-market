from flask import Flask, request, jsonify
import random

app = Flask(__name__)

# Initialize stock prices
stocks = {
    "TATA": 1000,
    "RELIANCE": 2400,
    "INFY": 1500,
    "ADANI": 1100,
    "HDFC": 1200
}

# User data
users = {}

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    if username not in users:
        users[username] = {"cash": 100000, "portfolio": {}}
    return jsonify({"message": f"User {username} registered"}), 200

@app.route("/prices", methods=["GET"])
def get_prices():
    # Simulate random stock changes
    for stock in stocks:
        change = random.randint(-10, 10)
        stocks[stock] += change
        if stocks[stock] < 1:
            stocks[stock] = 1
    return jsonify(stocks)

@app.route("/buy", methods=["POST"])
def buy_stock():
    data = request.get_json()
    user = users[data["username"]]
    stock = data["stock"]
    qty = int(data["qty"])
    price = stocks[stock] * qty
    if user["cash"] >= price:
        user["cash"] -= price
        user["portfolio"][stock] = user["portfolio"].get(stock, 0) + qty
        return jsonify({"message": f"Bought {qty} shares of {stock}"}), 200
    else:
        return jsonify({"message": "Not enough cash"}), 400

@app.route("/sell", methods=["POST"])
def sell_stock():
    data = request.get_json()
    user = users[data["username"]]
    stock = data["stock"]
    qty = int(data["qty"])
    if user["portfolio"].get(stock, 0) >= qty:
        user["portfolio"][stock] -= qty
        user["cash"] += stocks[stock] * qty
        return jsonify({"message": f"Sold {qty} shares of {stock}"}), 200
    else:
        return jsonify({"message": "Not enough stocks"}), 400

@app.route("/portfolio/<username>", methods=["GET"])
def portfolio(username):
    user = users.get(username, {"cash": 0, "portfolio": {}})
    net_worth = user["cash"]
    for stock, qty in user["portfolio"].items():
        net_worth += stocks[stock] * qty
    portfolio_list = [{"Stock": s, "Quantity": q, "Value": stocks[s]*q} for s, q in user["portfolio"].items()]
    return jsonify({"cash": user["cash"], "net_worth": net_worth, "portfolio": portfolio_list})

@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    lb = []
    for username, data in users.items():
        net_worth = data["cash"]
        for stock, qty in data["portfolio"].items():
            net_worth += stocks[stock] * qty
        lb.append({"Username": username, "Net Worth": net_worth})
    lb.sort(key=lambda x: x["Net Worth"], reverse=True)
    return jsonify(lb)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
