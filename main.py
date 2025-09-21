from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
import random
import httpx
from apscheduler.schedulers.background import BackgroundScheduler

# --- FastAPI app ---
app = FastAPI(title="Simulated Stock Market API")

# --- CORS to allow frontend from anywhere ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Config ---
VIRTUAL_CASH = 100000
UPDATE_INTERVAL = 60  # seconds (1 minute)
COMPANIES = {
    "Tesla": 700,
    "Apple": 150,
    "Amazon": 3200,
    "Google": 2800,
    "Microsoft": 300,
}

users = {}  # user_id: {"cash": X, "portfolio": {"Tesla": 10,...}}
stock_changes = {company: 0 for company in COMPANIES}  # % changes

# --- Models ---
class Trade(BaseModel):
    user_id: str
    company: str
    action: str  # "buy" or "sell"
    quantity: int

# --- Stock Price Updater ---
def update_stock_prices():
    global COMPANIES, stock_changes
    for company in COMPANIES:
        change = random.uniform(-3, 3)  # random ±3% change
        stock_changes[company] = round(change, 2)
        COMPANIES[company] = round(COMPANIES[company] * (1 + change/100), 2)
    print("Stocks updated:", COMPANIES)

scheduler = BackgroundScheduler()
scheduler.add_job(update_stock_prices, 'interval', seconds=UPDATE_INTERVAL)
scheduler.start()

# --- API Endpoints ---

@app.get("/stocks")
def get_stocks():
    """
    Returns current stock prices and % changes
    """
    return {
        "stocks": COMPANIES,
        "changes": stock_changes
    }

@app.post("/trade")
def trade_stock(trade: Trade):
    """
    Buy or sell stocks
    """
    if trade.user_id not in users:
        users[trade.user_id] = {"cash": VIRTUAL_CASH, "portfolio": {}}

    portfolio = users[trade.user_id]["portfolio"]
    cash = users[trade.user_id]["cash"]
    price = COMPANIES.get(trade.company)
    if price is None:
        return {"error": "Company not found"}

    total_cost = price * trade.quantity

    if trade.action == "buy":
        if cash < total_cost:
            return {"error": "Insufficient cash"}
        users[trade.user_id]["cash"] -= total_cost
        portfolio[trade.company] = portfolio.get(trade.company, 0) + trade.quantity
    elif trade.action == "sell":
        if portfolio.get(trade.company, 0) < trade.quantity:
            return {"error": "Not enough stocks to sell"}
        users[trade.user_id]["cash"] += total_cost
        portfolio[trade.company] -= trade.quantity
    else:
        return {"error": "Invalid action"}

    return {
        "portfolio": portfolio,
        "cash": users[trade.user_id]["cash"]
    }

@app.get("/portfolio/{user_id}")
def get_portfolio(user_id: str):
    """
    Get user portfolio and total value
    """
    if user_id not in users:
        return {"cash": VIRTUAL_CASH, "portfolio": {}, "total_value": VIRTUAL_CASH}
    portfolio = users[user_id]["portfolio"]
    cash = users[user_id]["cash"]
    total_value = cash + sum(COMPANIES[c]*q for c,q in portfolio.items())
    return {
        "cash": cash,
        "portfolio": portfolio,
        "total_value": total_value
    }

@app.get("/leaderboard")
def leaderboard():
    """
    Return leaderboard sorted by total portfolio value
    """
    data = []
    for user, info in users.items():
        total_value = info["cash"] + sum(COMPANIES[c]*q for c,q in info["portfolio"].items())
        data.append({"user": user, "total_value": total_value})
    data.sort(key=lambda x: x["total_value"], reverse=True)
    return data

@app.get("/news")
async def get_news():
    """
    Fetch latest business news (requires NewsAPI API key)
    """
    NEWS_API_KEY = "YOUR_NEWSAPI_KEY"  # replace with your key
    url = f"https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey={NEWS_API_KEY}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        articles = resp.json().get("articles", [])
        return [{"title": a["title"], "url": a["url"]} for a in articles[:5]]
