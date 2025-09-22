import streamlit as st
import requests
import json
import os
import pandas as pd
import plotly.express as px
import time
from streamlit_autorefresh import st_autorefresh   # ✅ added

st.set_page_config(page_title="📈 Virtual Stock Market", layout="wide")

# Backend URL from environment variable or default
BACKEND = os.environ.get("BACKEND", "https://virtual-stock-market-7mxp.onrender.com")

# ---- Session State ----
if "team" not in st.session_state:
    st.session_state.team = None
if "round_start" not in st.session_state:
    st.session_state.round_start = time.time()  # timestamp when participant enters

ROUND_DURATION = 15 * 60  # 15 minutes

# ---- Auto-refresh every 1 second ----
st_autorefresh(interval=1000, key="refresh")

# ---- Utility Functions ----
def fetch_stocks():
    return requests.get(f"{BACKEND}/stocks", timeout=6).json()

def fetch_leaderboard():
    return requests.get(f"{BACKEND}/leaderboard", timeout=6).json()

def fetch_news():
    return requests.get(f"{BACKEND}/news", timeout=6).json()

def fetch_portfolio(team):
    r = requests.get(f"{BACKEND}/portfolio/{team}", timeout=6)
    if r.status_code == 200:
        return r.json()
    return None

def init_team(team):
    r = requests.post(f"{BACKEND}/init_team", json={"team": team})
    return r.json() if r.status_code == 200 else None

def trade(team, symbol, qty):
    r = requests.post(f"{BACKEND}/trade", json={"team": team, "symbol": symbol, "qty": qty})
    return r.json() if r.status_code == 200 else None

# ---- Starting Page: Team Registration / Login ----
if st.session_state.team is None:
    st.title("👥 Register or Login Your Team")
    team_name_input = st.text_input("Enter Team Name")
    if st.button("Continue"):
        if team_name_input.strip() == "":
            st.warning("Please enter a valid team name.")
        else:
            # Try to create team first
            res = init_team(team_name_input)
            if res:
                st.success(f"Team '{team_name_input}' created with ₹{res['cash']:.2f}")
                st.session_state.team = team_name_input
                st.session_state.round_start = time.time()
            else:
                # If creation failed, try to fetch portfolio (login)
                port = fetch_portfolio(team_name_input)
                if port:
                    st.info(f"Team '{team_name_input}' already exists. Logged in successfully.")
                    st.session_state.team = team_name_input
                    st.session_state.round_start = time.time()
                else:
                    st.error("Error occurred. Try another team name.")
    st.stop()  # Stop execution until team is registered/logged in

# ---- Main Dashboard ----
team_name = st.session_state.team

# ---- Countdown Timer (Live) ----
elapsed = time.time() - st.session_state.round_start
remaining = ROUND_DURATION - elapsed
if remaining <= 0:
    st.warning("⏹️ Trading round has ended!")
    trading_allowed = False
else:
    mins, secs = divmod(int(remaining), 60)
    st.info(f"⏱️ Time Remaining: {mins:02d}:{secs:02d}")
    trading_allowed = True
