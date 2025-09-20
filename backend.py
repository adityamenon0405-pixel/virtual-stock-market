from flask import Flask, request, jsonify
from random import randint
import time

app = Flask(__name__)

# -----------------------------
# Global State
# -----------------------------
users = {}
stocks = {
    "TATA": 1000,
    "RELIANCE": 2400,
    "INFY": 1500,
    "ADANI": 1100,
    "HDFC": 1200
}

# Timer config
EVENT_DURATION = 30 * 60  # 30 minutes
start_time = time.time()
event_frozen = False
final_leaderboard = []  # will store final standings

# -----------------------------
# Helpers
# -----------------------------
def update_stock_prices():
    """Randomly update prices if event still running."""
    global event_frozen
    if event_frozen:
        return
    for stock in stocks:
        change_pct = randint(-20, 20) / 1000  # -2% to +2%
        stocks[stock] = max(1, round(stocks[stock] * (1 + change_pct), 2))

def event_active():
    """Check if 30-minute window still open."""
    return (time.time() - start_time) < EVENT_DURATION

def remaining_time():
    rem = EVENT_DURATION - (time.time() - start_time)
    return max(0, int(rem))

def generate_leaderboard():
    lb = []
    for username, data in users.items():
        net_worth = data["cash"]
        for stock, qty in data["portfolio"].items():
            net_worth += stocks[stock] * qty
        lb.append({"username": username, "net_worth": round(net_worth, 2)})
    return sorted(lb, key=lambda x: x["net_worth"], reverse=True)

def freeze_event():
    """Freeze leaderboard & prices after event ends."""
    global event_frozen, final_leaderboard
    event_frozen = True
    final_leaderboard = generate_leaderboard()

# -----------------------------
# Routes
# -----------------------------
@app.route("/status", methods=["GET"])
def status():
    if not event_active() and not event_frozen:
        freeze_event()
    return jsonify({
        "active": event_active(),
        "remaining_seconds": remaining_time(),
        "frozen": event_frozen
    })

@app.route("/register", methods=["POST"])
def register():
    if not event_active():
        return jsonify({"message": "Event over! Registration closed."}), 403

    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"message": "Username required"}), 400

    if username not in users:
        users[username] = {"cash": 100000, "portfolio": {}}

    return jsonify({"message": f"User {username} registered"}), 200

@app.route("/prices", methods=["GET"])
def get_prices():
    if event_active():
        update_stock_prices()
    return jsonify(stocks)

@app.route("/buy", methods=["POST"])
def buy_stock():
    if not event_active():
        return jsonify({"message": "Trading session ended!"}), 403

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
    if not event_active():
        return jsonify({"message": "Trading session ended!"}), 403

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
        "net_worth": round(net_worth, 2),
        "portfolio": portfolio
    })

@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    if event_frozen:
        return jsonify(final_leaderboard)
    return jsonify(generate_leaderboard())

# -----------------------------
# Run server
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
