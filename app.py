import requests
import random
import time
import concurrent.futures

BACKEND = "https://virtual-stock-market-7mxp.onrender.com"  # change if needed
NUM_TEAMS = 20
DURATION = 300  # seconds (5 minutes)

def init_team(team):
    try:
        r = requests.post(f"{BACKEND}/init_team", json={"team": team}, timeout=5)
        if r.status_code == 200:
            print(f"[+] Team {team} initialized")
        else:
            print(f"[!] Team {team} init failed ({r.status_code})")
    except Exception as e:
        print(f"[ERROR] Init team {team}: {e}")

def random_trade(team, symbols):
    try:
        symbol = random.choice(symbols)
        qty = random.randint(1, 10)
        buy_or_sell = random.choice([1, -1])  # buy or sell
        payload = {"team": team, "symbol": symbol, "qty": qty * buy_or_sell}
        r = requests.post(f"{BACKEND}/trade", json=payload, timeout=5)
        if r.status_code != 200:
            print(f"[!] Trade failed for {team} on {symbol}")
    except Exception as e:
        print(f"[ERROR] Trade {team}: {e}")

def fetch_symbols():
    try:
        r = requests.get(f"{BACKEND}/stocks", timeout=5)
        if r.status_code == 200:
            return [s["symbol"] for s in r.json()]
    except:
        pass
    return []

def team_loop(team, symbols, end_time):
    while time.time() < end_time:
        random_trade(team, symbols)
        # Fetch portfolio occasionally to simulate dashboard
        if random.random() < 0.3:
            try:
                requests.get(f"{BACKEND}/portfolio/{team}", timeout=5)
            except:
                pass
        time.sleep(random.uniform(0.5, 2.0))  # random gap between trades

def run_test():
    symbols = fetch_symbols()
    if not symbols:
        print("[!] Could not fetch stock symbols. Check backend first.")
        return

    teams = [f"Team_{i+1}" for i in range(NUM_TEAMS)]
    for t in teams:
        init_team(t)

    print(f"[INFO] Starting load test with {NUM_TEAMS} teams for {DURATION} seconds...")
    end_time = time.time() + DURATION

    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_TEAMS) as executor:
        futures = [executor.submit(team_loop, t, symbols, end_time) for t in teams]
        for f in concurrent.futures.as_completed(futures):
            pass

    print("[INFO] Load test completed. Fetching final leaderboard...")
    try:
        r = requests.get(f"{BACKEND}/leaderboard", timeout=5)
        if r.status_code == 200:
            leaderboard = r.json()
            leaderboard = sorted(leaderboard, key=lambda x: x["portfolio_value"], reverse=True)
            print("\n=== FINAL LEADERBOARD ===")
            for i, team in enumerate(leaderboard[:5], 1):
                print(f"{i}. {team['team']} - ₹{team['portfolio_value']:.2f}")
        else:
            print("[!] Could not fetch leaderboard")
    except Exception as e:
        print(f"[ERROR] Fetch leaderboard: {e}")

if __name__ == "__main__":
    run_test()
