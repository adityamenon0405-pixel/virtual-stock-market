import asyncio
import random
import time
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Optional
import os
import httpx

app = FastAPI(title="Simulated Stock Market API with Admin Features")

STARTING_CASH = 100000
UPDATE_MIN = 60
UPDATE_MAX = 120
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "supersecret123")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")  # optional

class TickerState(BaseModel):
    symbol: str
    name: str
    price: float
    prev_close: float
    last_update: float

tickers: Dict[str, TickerState] = {}
portfolios: Dict[str, dict] = {}
injected_news: list = []

INITIAL_TICKERS = {
    "ACME": "Acme Corp",
    "ORCL": "Oracle-ish",
    "GLOB": "GloboTech",
    "NOVA": "Nova Systems",
    "RIVR": "Riverbank Ltd",
    "ZENX": "ZenX Labs",
    "TITN": "Titan Motors",
    "ASTR": "Astra Foods",
    "PHAZ": "Phaz Pharma",
    "SOLA": "Sola Energy"
}

def init_tickers():
    now = time.time()
    for s, n in INITIAL_TICKERS.items():
        price = round(random.uniform(50, 500), 2)
        tickers[s] = TickerState(symbol=s, name=n, price=price, prev_close=price, last_update=now)

async def simulate_ticker(symbol: str):
    while True:
        await asyncio.sleep(random.randint(UPDATE_MIN, UPDATE_MAX))
        t = tickers.get(symbol)
        if not t: return
        base_move = random.gauss(0, 0.6)
        spike = random.random() < 0.03
        if spike:
            base_move += random.choice([-1, 1]) * random.uniform(3, 10)
        pct = base_move / 100.0
        t.price = round(max(0.01, t.price * (1 + pct)), 2)
        t.last_update = time.time()
        tickers[symbol] = t

async def start_simulators():
    await asyncio.sleep(0.5)
    tasks = [asyncio.create_task(simulate_ticker(s)) for s in tickers.keys()]
    await asyncio.gather(*tasks)

@app.on_event("startup")
async def startup_event():
    init_tickers()
    asyncio.create_task(start_simulators())

class RegisterIn(BaseModel):
    name: str

class TradeIn(BaseModel):
    portfolio_id: str
    symbol: str
    qty: int

@app.get("/tickers")
def get_tickers():
    return [t.dict() for t in tickers.values()]

@app.get("/prices")
def get_prices():
    result = []
    for t in tickers.values():
        pct = ((t.price - t.prev_close)/t.prev_close)*100 if t.prev_close else 0
        result.append({
            "symbol": t.symbol,
            "name": t.name,
            "price": t.price,
            "prev_close": t.prev_close,
            "pct_change": round(pct,2),
            "last_update": t.last_update
        })
    return {"timestamp": time.time(), "prices": result}

@app.post("/register")
def register(r: RegisterIn):
    pid = f"p{int(time.time()*1000)}{random.randint(1000,9999)}"
    portfolios[pid] = {
        "id": pid,
        "name": r.name,
        "cash": STARTING_CASH,
        "holdings": {},
        "created_at": time.time()
    }
    return portfolios[pid]

@app.post("/trade")
def trade(t: TradeIn):
    if t.portfolio_id not in portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if t.symbol not in tickers:
        raise HTTPException(status_code=404, detail="Ticker not found")
    p = portfolios[t.portfolio_id]
    price = tickers[t.symbol].price
    total = round(price * abs(t.qty), 2)
    if t.qty > 0:
        if p["cash"] < total:
            raise HTTPException(status_code=400, detail="Insufficient cash")
        p["cash"] -= total
        p["holdings"][t.symbol] = p["holdings"].get(t.symbol,0) + t.qty
    else:
        available = p["holdings"].get(t.symbol,0)
        need = abs(t.qty)
        if available < need:
            raise HTTPException(status_code=400, detail="Insufficient holdings")
        p["holdings"][t.symbol] = available - need
        p["cash"] += total
        if p["holdings"][t.symbol]==0:
            del p["holdings"][t.symbol]
    portfolios[t.portfolio_id] = p
    return {"status": "ok", "portfolio": p}

@app.get("/portfolio/{pid}")
def get_portfolio(pid: str):
    if pid not in portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    p = portfolios[pid].copy()
    holdings_detail=[]
    total_holdings_value=0
    for sym, qty in p["holdings"].items():
        price = tickers[sym].price
        val = round(price*qty,2)
        holdings_detail.append({"symbol": sym, "qty": qty, "price": price, "value": val})
        total_holdings_value += val
    p["holdings_detail"]=holdings_detail
    p["holdings_value"]=round(total_holdings_value,2)
    p["total_value"]=round(p["cash"]+total_holdings_value,2)
    return p

@app.get("/leaderboard")
def get_leaderboard(limit:int=10):
    board=[]
    for p in portfolios.values():
        total = p["cash"]
        for sym,qty in p["holdings"].items():
            total += tickers[sym].price*qty
        board.append({"id":p["id"],"name":p["name"],"total":round(total,2)})
    board.sort(key=lambda x:x["total"],reverse=True)
    return board[:limit]

@app.get("/news")
async def get_news(symbols: Optional[str]=None, q: Optional[str]=None):
    query = q or symbols or "stock market"
    articles = []
    if injected_news:
        articles.extend(injected_news[-5:])
    if NEWSAPI_KEY:
        url = "https://newsapi.org/v2/everything"
        params = {"q":query,"pageSize":8,"sortBy":"publishedAt","language":"en","apiKey":NEWSAPI_KEY}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            if resp.status_code==200:
                j = resp.json()
                real_articles=[{"title":a.get("title"),"url":a.get("url"),"source":a.get("source",{}).get("name"),"publishedAt":a.get("publishedAt"),"description":a.get("description")} for a in j.get("articles",[])]
                articles.extend(real_articles[:5])
            else:
                articles.append({"title":f"Error fetching news: {resp.status_code}","source":"NewsAPI"})
    else:
        articles.append({"title":f"{query}: Market reacts to news","source":"SimNews","publishedAt":time.ctime()})
    return {"query":query,"articles":articles[-8:]}

@app.post("/admin/reset")
def admin_reset(secret: str = Query(...)):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    init_tickers()
    portfolios.clear()
    injected_news.clear()
    return {"status":"reset_done","message":"Market, portfolios, and news cleared"}

@app.post("/admin/news")
def admin_news(title: str, description: str="", source: str="Admin", secret: str = Query(...)):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    article = {"title":title,"description":description,"source":source,"publishedAt":time.ctime()}
    injected_news.append(article)
    return {"status":"ok","article":article}
