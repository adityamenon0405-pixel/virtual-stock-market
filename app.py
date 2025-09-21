# frontend/app.py
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

# ------------------ CONFIG ------------------
# Set your backend URL here (Render deployment URL)
BACKEND_URL = st.secrets.get("backend_url", "http://localhost:8000")

st.set_page_config(page_title="Virtual Stock Trader", page_icon="📈", layout="wide")

# ------------------ SESSION STATE ------------------
if "portfolio_id" not in st.session_state:
    st.session_state.portfolio_id = None
    st.session_state.name = None

# Check if "leaderboard-only" view is requested
params = st.experimental_get_query_params()
leaderboard_only = params.get("view", [""])[0] == "leaderboard"

# ------------------ FUNCTIONS ------------------
def fetch_prices():
    r = requests.get(f"{BACKEND_URL}/prices", timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_portfolio(pid):
    r = requests.get(f"{BACKEND_URL}/portfolio/{pid}", timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_leaderboard():
    r = requests.get(f"{BACKEND_URL}/leaderboard", timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_news(symbols):
    q = ",".join(symbols)
    r = requests.get(f"{BACKEND_URL}/news", params={"symbols": q}, timeout=10)
    r.raise_for_status()
    return r.json()

def register_team(name):
    resp = requests.post(f"{BACKEND_URL}/register", json={"name": name}, timeout=10)
    resp.raise_for_status()
    return resp.json()

def execute_trade(symbol, qty):
    payload = {"portfolio_id": st.session_state.portfolio_id, "symbol": symbol, "qty": int(qty)}
    r = requests.post(f"{BACKEND_URL}/trade", json=payload, timeout=10)
    return r

def fmt_pct(x):
    if x > 0:
        return f"▲ {x:.2f}%"
    elif x < 0:
        return f"▼ {abs(x):.2f}%"
    return f"{x:.2f}%"

def color_pct(val):
    if val > 0: return 'color: green'
    if val < 0: return 'color: red'
    return ''

# ------------------ LEADERBOARD-ONLY VIEW ------------------
if leaderboard_only:
    st.title("🏆 Live Leaderboard")
    while True:
        lb = fetch_leaderboard()
        if lb:
            df = pd.DataFrame(lb)
            df.index += 1
            st.dataframe(df[["name","total"]].rename(columns={"name":"Team","total":"Portfolio Value"}), use_container_width=True, height=500)
        else:
            st.write("No participants yet.")
        st.write("🔄 Auto-refreshing every 10 seconds...")
        time.sleep(10)
        st.experimental_rerun()

# ------------------ MAIN DASHBOARD ------------------
st.title("📈 Virtual Stock Market — Event Edition")
st.write("Virtual cash: ₹100,000. Prices auto-update. Leaderboard & news included.")

# --- Sidebar for Registration/Login ---
with st.sidebar:
    st.header("Team / Login")
    if st.session_state.portfolio_id is None:
        team_name = st.text_input("Team name", value="", key="teamname")
        if st.button("Join / Register"):
            if not team_name.strip():
                st.warning("Choose a team name.")
            else:
                obj = register_team(team_name.strip())
                st.session_state.portfolio_id = obj["id"]
                st.session_state.name = obj["name"]
                st.success(f"Registered as {obj['name']}")
                st.experimental_rerun()
    else:
        st.write(f"Logged in as **{st.session_state.name}**")
        if st.button("Logout"):
            st.session_state.portfolio_id = None
            st.session_state.name = None
            st.experimental_rerun()

# ------------------ PAGE LAYOUT ------------------
col1, col2 = st.columns([3,1])

# Fetch prices
prices_data = fetch_prices()
prices = prices_data["prices"]
df = pd.DataFrame(prices).sort_values("pct_change", ascending=False)
display_df = df[["symbol","name","price","pct_change","last_update"]].copy()
display_df["change"] = display_df["pct_change"].apply(fmt_pct)
display_df["last_update"] = display_df["last_update"].apply(lambda x: datetime.fromtimestamp(x).strftime("%H:%M:%S"))
display_df = display_df[["symbol","name","price","change","last_update"]]

# --- Market Table & Trading ---
with col1:
    st.subheader("Market — Prices (auto-updates)")
    st.write(f"Last updated: {datetime.fromtimestamp(prices_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
    st.dataframe(display_df.style.applymap(lambda x: 'color: green' if '▲' in str(x) else ('color: red' if '▼' in str(x) else ''), subset=["change"]), use_container_width=True)

    st.markdown("---")
    st.subheader("Trade")
    if st.session_state.get("portfolio_id") is None:
        st.info("Register a team from sidebar to trade.")
    else:
        trade_symbol = st.selectbox("Symbol", display_df["symbol"].tolist())
        trade_qty = st.number_input("Quantity (positive buy, negative sell)", value=0, step=1)
        if st.button("Execute Trade"):
            r = execute_trade(trade_symbol, trade_qty)
            if r.status_code == 200:
                st.success("Trade executed!")
            else:
                st.error(r.json().get("detail","Error executing trade"))
            st.experimental_rerun()

# --- Portfolio & Leaderboard ---
with col2:
    st.subheader("Your Portfolio")
    if st.session_state.get("portfolio_id"):
        p = fetch_portfolio(st.session_state.portfolio_id)
        st.metric("Total Value (₹)", f"{p['total_value']:.2f}")
        st.metric("Cash (₹)", f"{p['cash']:.2f}")
        st.write("Holdings")
        if p["holdings_detail"]:
            hdf = pd.DataFrame(p["holdings_detail"])
            st.dataframe(hdf.style.format({"price":"{:.2f}","value":"{:.2f}"}))
        else:
            st.write("— no holdings —")
    else:
        st.write("Register to see portfolio.")

    st.markdown("---")
    st.subheader("Leaderboard")
    lb = fetch_leaderboard()
    if lb:
        for i, item in enumerate(lb, start=1):
            st.write(f"**{i}. {item['name']}** — ₹{item['total']:.2f}")
    else:
        st.write("No participants yet.")

# --- News Section ---
st.markdown("---")
st.subheader("Latest News for Top Movers")
top_symbols = df["symbol"].head(3).tolist()
news = fetch_news(top_symbols)
if news.get("articles"):
    for a in news["articles"]:
        if a.get("source") == "Admin":
            st.markdown(f"**🚨 {a.get('title')}** — *{a.get('source')}*")
        else:
            st.write(f"**{a.get('title')}** — *{a.get('source')}*")
        if a.get("url"):
            st.write(a.get("url"))
        st.write(a.get("description",""))
        st.write("---")
else:
    st.write("No news available.")

# --- Auto Refresh ---
st.write("")
countdown = st.empty()
for i in range(15,0,-1):
    countdown.write(f"Refreshing in {i}s — (press F5 to reload immediately)")
    time.sleep(1)
st.experimental_rerun()
