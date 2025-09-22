# frontend/streamlit_app.py
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import math

st.set_page_config(page_title="Virtual Stock Market — Event", layout="wide")

BACKEND = st.secrets.get("BACKEND_URL") or st.sidebar.text_input("Backend URL (eg https://your-backend.onrender.com)", value="http://localhost:8000")

st.title("📈 Virtual Stock Market — Live Dashboard")
team = st.sidebar.text_input("Team name", value="Team-A")
if st.sidebar.button("Create team / reset (if new)"):
    r = requests.post(f"{BACKEND}/init_team", json={"team": team})
    st.sidebar.write(r.json())

st.sidebar.write("Virtual cash: ₹100,000 per team")

auto_refresh = st.sidebar.checkbox("Auto-refresh every 10s", value=True)
refresh_interval = st.sidebar.number_input("Refresh interval (seconds)", min_value=5, max_value=60, value=10)

# trading panel
st.sidebar.subheader("Quick Trade")
symbol = st.sidebar.text_input("Symbol (e.g. APPL)", value="APPL")
qty = st.sidebar.number_input("Quantity (positive buy, negative sell)", value=1, step=1)
if st.sidebar.button("Execute Trade"):
    payload = {"team": team, "symbol": symbol.upper(), "qty": int(qty)}
    try:
        r = requests.post(f"{BACKEND}/trade", json=payload, timeout=8)
        st.sidebar.write(r.json())
    except Exception as e:
        st.sidebar.error(str(e))

# auto refresh helper
if auto_refresh:
    st_autorefresh = st.experimental_get_query_params().get("autorefresh", ["0"])[0]
    # use st.experimental_rerun with timer
    st.write("")  # placeholder


def fetch_all():
    stocks = requests.get(f"{BACKEND}/stocks", timeout=6).json()
    portfolio = {}
    try:
        portfolio = requests.get(f"{BACKEND}/portfolio/{team}", timeout=6).json()
    except:
        portfolio = {"error":"couldn't fetch portfolio"}
    leaderboard = requests.get(f"{BACKEND}/leaderboard", timeout=6).json()
    news = requests.get(f"{BACKEND}/news", timeout=6).json()
    return stocks, portfolio, leaderboard, news

stocks, portfolio, leaderboard, news = fetch_all()

# Stocks table with color coding
st.subheader("Market — Live Prices")
df = pd.DataFrame(stocks)
if not df.empty:
    df_display = df[["symbol","name","price","last_price","pct_change","updated_at"]].copy()
    df_display["updated_at"] = df_display["updated_at"].apply(lambda t: datetime.fromtimestamp(t).strftime("%H:%M:%S"))
    # Colorize pct_change column using HTML
    def make_row_html(row):
        pct = row["pct_change"]
        color = "green" if pct > 0 else ("red" if pct < 0 else "black")
        sign = "+" if pct > 0 else ""
        return f"""<tr>
<td><b>{row['symbol']}</b></td>
<td>{row['name']}</td>
<td>₹{row['price']}</td>
<td>₹{row['last_price']}</td>
<td style="color:{color}">{sign}{row['pct_change']}%</td>
<td>{row['updated_at']}</td>
</tr>"""
    rows_html = "\n".join(df_display.apply(make_row_html, axis=1).tolist())
    table_html = f"""
    <table style="width:100%; border-collapse: collapse;">
    <thead><tr><th>Symbol</th><th>Name</th><th>Price</th><th>Prev</th><th>% Change</th><th>Updated</th></tr></thead>
    <tbody>{rows_html}</tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.write("No stocks found")

# Portfolio & holdings
st.subheader(f"Your Portfolio — {team}")
if "error" in portfolio:
    st.error(portfolio["error"])
else:
    st.write(f"Cash: ₹{portfolio['cash']}")
    st.write(f"Portfolio value (cash + holdings): ₹{portfolio['portfolio_value']}")
    holdings = portfolio.get("holdings", {})
    if holdings:
        hold_df = pd.DataFrame([
            {"symbol": s, "qty": d["qty"], "price": d["price"], "value": d["value"]}
            for s,d in holdings.items()
        ])
        st.table(hold_df)
    else:
        st.write("No holdings yet")

# Leaderboard
st.subheader("Leaderboard")
lb_df = pd.DataFrame(leaderboard)
if not lb_df.empty:
    lb_df.index = lb_df.index + 1
    st.table(lb_df)
else:
    st.write("No teams yet")

# News
st.subheader("Latest news")
articles = news.get("articles", [])
for a in articles:
    title = a.get("title")
    url = a.get("url")
    source = a.get("source","")
    if url:
        st.markdown(f"- [{title}]({url}) — *{source}*")
    else:
        st.markdown(f"- {title}")

# Auto-refresh loop
if auto_refresh:
    st.experimental_rerun()

# Footer
st.markdown("---")
st.markdown("Tip: Run multiple browser windows (or use the projector) to show the leaderboard to the audience.")
