import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
import time
from datetime import datetime
import plotly.express as px

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="📈 Virtual Stock Market - Round 2", layout="wide")

# ---------------- GLOBAL SETTINGS ----------------
BACKEND = "http://127.0.0.1:8000"   # <<-- REPLACE with your backend URL
ROUND_DURATION = 15 * 60  # 15 minutes per round
REFRESH_INTERVAL_MS = 1000   # 1 second auto-refresh

# ---------------- AUTO REFRESH ----------------
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="refresh")

# ---------------- SESSION STATE (timer) ----------------
if "round_start" not in st.session_state:
    st.session_state.round_start = time.time()

# ---------------- TEAM LOGIN ----------------
if "team" not in st.session_state:
    st.title("🏁 Virtual Stock Market - Team Login")
    with st.form("login_form"):
        team_name = st.text_input("Enter your Team Name")
        password = st.text_input("Password / PIN (optional)", type="password")
        submitted = st.form_submit_button("Login ✅")

    if submitted and team_name.strip() != "":
        st.session_state["team"] = team_name.strip()
        st.experimental_rerun()
    else:
        st.stop()   # stop rendering dashboard until login
else:
    st.sidebar.success(f"👥 Logged in as: {st.session_state['team']}")
    if st.sidebar.button("🚪 Logout"):
        del st.session_state["team"]
        st.experimental_rerun()

# ---------------- SAFE API CALL ----------------
def fetch_api(endpoint, fallback):
    try:
        url = f"{BACKEND}{endpoint}"
        r = requests.get(url, timeout=4)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"API {endpoint} failed: {e}")
        return fallback

# ---------------- FALLBACK DATA ----------------
FALLBACK_STOCKS = [
    {"symbol": "DEMO1", "name": "Demo Co 1", "price": 120.5, "pct_change": 1.2},
    {"symbol": "DEMO2", "name": "Demo Co 2", "price": 254.0, "pct_change": -0.6},
    {"symbol": "DEMO3", "name": "Demo Co 3", "price": 78.25, "pct_change": 2.8},
    {"symbol": "DEMO4", "name": "Demo Co 4", "price": 430.0, "pct_change": -1.3},
]

FALLBACK_PORTFOLIO = [
    {"Stock": "DEMO1", "Qty": 10, "Price": 120.5, "Value": 1205.0},
    {"Stock": "DEMO2", "Qty": 5, "Price": 254.0, "Value": 1270.0},
]

FALLBACK_LEADERBOARD = [
    {"Team": "Alpha", "Net Worth": 120000},
    {"Team": "Beta", "Net Worth": 115500},
    {"Team": "Gamma", "Net Worth": 110230},
]

FALLBACK_NEWS = [
    {"headline": "Demo: Market opens higher amid optimism"},
    {"headline": "Demo: Tech stocks lead the rally"},
    {"headline": "Demo: Economic data due tomorrow"},
]

# ---------------- TIMER ----------------
elapsed = time.time() - st.session_state.round_start
remaining = max(0, ROUND_DURATION - elapsed)

st.markdown("## ⏳ Event Timer")
if remaining > 0:
    mins, secs = divmod(int(remaining), 60)
    st.success(f"Time Left: {mins:02}:{secs:02}")
else:
    st.error("⏹️ Round Over!")
    st.stop()  # Stop refreshing and halt further rendering

st.divider()

# ---------------- FETCH DATA ----------------
team = st.session_state["team"]
stocks = fetch_api("/stocks", FALLBACK_STOCKS)
portfolio = fetch_api(f"/portfolio/{team}", FALLBACK_PORTFOLIO)
leaderboard = fetch_api("/leaderboard", FALLBACK_LEADERBOARD)
news = fetch_api("/news", FALLBACK_NEWS)

# ---------------- 3D STOCK CHART ----------------
st.markdown("## 📊 Live 3D Stock Market View")
try:
    df_stocks = pd.DataFrame(stocks)
except Exception:
    df_stocks = pd.DataFrame(FALLBACK_STOCKS)

if "price" not in df_stocks.columns:
    df_stocks["price"] = df_stocks.get("Price", pd.Series([p.get("price", 0) for p in stocks]))
if "pct_change" not in df_stocks.columns:
    df_stocks["pct_change"] = df_stocks.get("pct_change", pd.Series([p.get("pct_change", 0) for p in stocks]))
if "volume" not in df_stocks.columns:
    df_stocks = df_stocks.reset_index(drop=True)
    df_stocks["volume"] = [(i + 1) * 1000 for i in range(len(df_stocks))]

df_stocks["label"] = df_stocks.apply(lambda r: f"{r.get('symbol','')}: {r.get('name','')}\nPrice: ₹{r['price']}\nChange: {r['pct_change']}%", axis=1)

fig3d = px.scatter_3d(
    df_stocks,
    x="price",
    y="pct_change",
    z="volume",
    color="pct_change",
    color_continuous_scale=px.colors.diverging.RdYlGn,
    hover_name="symbol",
    hover_data={"name": True, "price": True, "pct_change": True, "volume": True},
    size="price",
    size_max=30,
    title="💎 Price vs % Change vs Volume (3D)",
)

fig3d.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey'), opacity=0.85))
fig3d.update_layout(
    scene=dict(
        xaxis_title='Price (₹)',
        yaxis_title='% Change',
        zaxis_title='Volume',
        xaxis=dict(showgrid=True, gridcolor="lightgray"),
        yaxis=dict(showgrid=True, gridcolor="lightgray"),
        zaxis=dict(showgrid=True, gridcolor="lightgray"),
    ),
    margin=dict(l=0, r=0, t=40, b=0),
    coloraxis_colorbar=dict(title="% Change"),
    template="plotly_white",
)
st.plotly_chart(fig3d, use_container_width=True)
st.divider()

# ---------------- TEAM PORTFOLIO ----------------
st.markdown("## 💼 Your Portfolio")
if isinstance(portfolio, list) and len(portfolio) > 0:
    df_portfolio = pd.DataFrame(portfolio)
    if "Value" not in df_portfolio.columns and "Qty" in df_portfolio.columns and "Price" in df_portfolio.columns:
        df_portfolio["Value"] = df_portfolio["Qty"] * df_portfolio["Price"]
    st.dataframe(df_portfolio, use_container_width=True)
    total_value = df_portfolio['Value'].sum()
    st.info(f"💰 Total Portfolio Value: ₹{total_value}")
else:
    st.warning("No portfolio data available for your team. Showing demo portfolio.")
    st.dataframe(pd.DataFrame(FALLBACK_PORTFOLIO), use_container_width=True)

st.divider()

# ---------------- LEADERBOARD ----------------
st.markdown("## 🏆 Leaderboard")
if isinstance(leaderboard, list) and len(leaderboard) > 0:
    df_lb = pd.DataFrame(leaderboard)
    if "Team" not in df_lb.columns and "team" in df_lb.columns:
        df_lb = df_lb.rename(columns={"team": "Team"})
    if "Net Worth" not in df_lb.columns and "value" in df_lb.columns:
        df_lb = df_lb.rename(columns={"value": "Net Worth"})
    df_lb = df_lb.sort_values(by=df_lb.columns[-1], ascending=False).reset_index(drop=True)
    df_lb.index += 1

    # Highlight top 3
    def highlight_top3(row):
        if row.name == 0: return ['background-color: gold']*len(row)
        if row.name == 1: return ['background-color: silver']*len(row)
        if row.name == 2: return ['background-color: #cd7f32']*len(row)
        return ['']*len(row)

    st.dataframe(df_lb.style.apply(highlight_top3, axis=1), use_container_width=True)
else:
    st.warning("No leaderboard data available. Showing demo leaderboard.")
    st.dataframe(pd.DataFrame(FALLBACK_LEADERBOARD), use_container_width=True)

st.divider()

# ---------------- NEWS ----------------
st.markdown("## 📰 Market News")
if isinstance(news, list) and len(news) > 0:
    for item in news[:5]:  # top 5 latest
        title = item.get("title") or item.get("headline") or item.get("headline_text") or "(no title)"
        url = item.get("url")
        published = item.get("publishedAt") or item.get("time") or None
        timestamp = datetime.now().strftime("%H:%M:%S") if not published else published
        if url:
            st.markdown(f"- 🔗 [{title}]({url})  <span style='color:gray;font-size:12px'> {timestamp}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"- 📝 {title}  <span style='color:gray;font-size:12px'> {timestamp}</span>", unsafe_allow_html=True)
else:
    st.warning("No news available. Showing demo headlines.")
    for d in FALLBACK_NEWS:
        st.info(d["headline"])

st.divider()
st.caption(f"Backend: {BACKEND} • Last refresh: {datetime.now().strftime('%H:%M:%S')}")
