#!/usr/bin/env python3
"""Time-Weighted IC analysis + sell_win stats + market data for Heartbeat."""
import os, sys, json, sqlite3, urllib.request
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
db = sqlite3.connect(os.path.join(os.path.dirname(__file__), "poly_trader.db"))

feat_rows = db.execute("""
    SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body,
           feat_pulse, feat_aura, feat_mind
    FROM features_normalized ORDER BY timestamp
""").fetchall()

label_rows = db.execute("""
    SELECT timestamp, label_sell_win, label_up, future_return_pct
    FROM labels ORDER BY timestamp
""").fetchall()

label_map = {r[0]: {"sell_win": r[1], "up": r[2], "ret": r[3]} for r in label_rows}
feat_cols = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body", "feat_pulse", "feat_aura", "feat_mind"]
sense_names = ["Eye", "Ear", "Nose", "Tongue", "Body", "Pulse", "Aura", "Mind"]

common = sorted(set(r[0] for r in feat_rows) & set(label_map.keys()))
feat_map = {r[0]: {c: r[1+feat_cols.index(c)] for c in feat_cols} for r in feat_rows}

raw_count = db.execute("SELECT COUNT(*) FROM raw_market_data").fetchone()[0]
feat_count = db.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
label_count = db.execute("SELECT COUNT(*) FROM labels").fetchone()[0]
print(f"Raw: {raw_count} / Features: {feat_count} / Labels: {label_count}")
print(f"Common timestamps for IC: {len(common)}")

# Sell win stats
y = [float(label_map[ts]["sell_win"]) for ts in common]
sell_win_rate = np.mean(y)
recent_100 = np.mean(y[-100:]) if len(y) >= 100 else 0
recent_500 = np.mean(y[-500:]) if len(y) >= 500 else 0

consecutive_losses = 0
max_consecutive = 0
for val in y:
    if val == 0:
        consecutive_losses += 1
        max_consecutive = max(max_consecutive, consecutive_losses)
    else:
        consecutive_losses = 0

print(f"\nSell Win Rate (global): {sell_win_rate*100:.2f}%")
print(f"Recent 100: {recent_100*100:.1f}%")
print(f"Recent 500: {recent_500*100:.1f}%")
print(f"Max consecutive losses: {max_consecutive}")

# Global IC
print(f"\n=== GLOBAL IC (full history) ===")
global_ics = {}
for sn, fc in zip(sense_names, feat_cols):
    f_vals = []
    l_vals = []
    for ts in common:
        fv = feat_map.get(ts, {}).get(fc)
        lv = label_map.get(ts, {}).get("sell_win")
        if fv is not None and lv is not None:
            f_vals.append(float(fv))
            l_vals.append(float(lv))
    fa = np.array(f_vals)
    la = np.array(l_vals)
    std_val = float(np.std(fa))
    if std_val < 1e-10 or np.std(la) < 1e-10:
        print(f"{sn:8s}: IC=0.0000 (std=0, unique={len(set(fa))})")
        global_ics[sn] = 0.0
        continue
    r, _ = stats.spearmanr(fa, la)
    global_ics[sn] = round(float(r), 4)
    status = "PASS" if abs(r) >= 0.05 else "FAIL"
    print(f"{sn:8s}: IC={r:+.4f} std={std_val:.6f} unique={len(set(fa))} [{status}]")

global_pass = sum(1 for v in global_ics.values() if abs(v) >= 0.05)
print(f"Global IC Pass Rate: {global_pass}/8 ({global_pass/8*100:.1f}%)")

# Time-Weighted IC (tau=200)
print(f"\n=== TIME-WEIGHTED IC (tau=200, exponential decay) ===")
tau = 200
tw_ics = {}
for sn, fc in zip(sense_names, feat_cols):
    f_vals = []
    l_vals = []
    for ts in common:
        fv = feat_map.get(ts, {}).get(fc)
        lv = label_map.get(ts, {}).get("sell_win")
        if fv is not None and lv is not None:
            f_vals.append(float(fv))
            l_vals.append(float(lv))
    
    fa = np.array(f_vals)
    la = np.array(l_vals)
    if len(fa) < 100 or np.std(fa) < 1e-10:
        print(f"{sn:8s}: SKIP"); continue
    
    weights = np.exp(-np.arange(len(fa))[::-1] / tau)
    weights /= weights.sum()
    
    rx = stats.rankdata(fa)
    ry = stats.rankdata(la)
    
    w_mean_x = np.average(rx, weights=weights)
    w_mean_y = np.average(ry, weights=weights)
    w_cov = np.sum(weights * (rx - w_mean_x) * (ry - w_mean_y))
    w_std_x = np.sqrt(np.sum(weights * (rx - w_mean_x)**2))
    w_std_y = np.sqrt(np.sum(weights * (ry - w_mean_y)**2))
    
    if w_std_x > 0 and w_std_y > 0:
        tw_ic = w_cov / (w_std_x * w_std_y)
    else:
        tw_ic = 0.0
    
    tw_ics[sn] = round(float(tw_ic), 4)
    status = "PASS" if abs(tw_ic) >= 0.05 else "FAIL"
    print(f"{sn:8s}: TW-IC={tw_ic:+.4f} [{status}]")

tw_pass = sum(1 for v in tw_ics.values() if abs(v) >= 0.05)
print(f"TW-IC Pass Rate: {tw_pass}/8 ({tw_pass/8*100:.1f}%)")

# Fetch live market data
print(f"\n=== Market Data ===")
try:
    # BTC price
    req = urllib.request.Request("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
                                  headers={"User-Agent": "PolyTrader"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        btc_data = json.loads(resp.read())
        btc_price = float(btc_data["price"])
    print(f"BTC: ${btc_price:,.0f}")
except Exception as e:
    btc_price = 0
    print(f"BTC: ERROR - {e}")

try:
    # Fear & Greed Index
    req = urllib.request.Request("https://api.alternative.me/fng/?limit=1",
                                  headers={"User-Agent": "PolyTrader"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        fng_data = json.loads(resp.read())["data"][0]
        fng_val = int(fng_data["value"])
        fng_cls = fng_data["value_classification"]
    print(f"FNG: {fng_val} ({fng_cls})")
except Exception as e:
    fng_val = 0
    print(f"FNG: ERROR - {e}")

try:
    # Binance derivatives data
    # Taker buy/sell ratio
    req = urllib.request.Request("https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio?period=4h&limit=1",
                                  headers={"User-Agent": "PolyTrader"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        ls_data = json.loads(resp.read())
        lsr = float(ls_data[0]["longShortRatio"]) if ls_data else 0
    print(f"LSR (4h): {lsr:.4f}")
except Exception as e:
    lsr = 0
    print(f"LSR: ERROR - {e}")

try:
    # Funding rate
    req = urllib.request.Request("https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT",
                                  headers={"User-Agent": "PolyTrader"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        fr_data = json.loads(resp.read())
        funding_rate = float(fr_data["lastFundingRate"])
    print(f"Funding Rate: {funding_rate:.6f}")
except Exception as e:
    funding_rate = 0
    print(f"Funding Rate: ERROR - {e}")

try:
    # Taker buy/sell ratio
    req = urllib.request.Request("https://fapi.binance.com/futures/data/takerlongshortRatio?period=4h&limit=1",
                                  headers={"User-Agent": "PolyTrader"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        taker_data = json.loads(resp.read())
        taker_ratio = float(taker_data[0]["buySellRatio"]) if taker_data else 0
    print(f"Taker B/S Ratio (4h): {taker_ratio:.4f}")
except Exception as e:
    taker_ratio = 0
    print(f"Taker B/S: ERROR - {e}")

try:
    # Open Interest
    req = urllib.request.Request("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT",
                                  headers={"User-Agent": "PolyTrader"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        oi_data = json.loads(resp.read())
        oi = float(oi_data["openInterest"])
    print(f"Open Interest: {oi:,.2f} BTC")
except Exception as e:
    oi = 0
    print(f"OI: ERROR - {e}")

try:
    # VIX
    req = urllib.request.Request("https://finance.yahoo.com/quote/%5EVIX/",
                                  headers={"User-Agent": "PolyTrader"})
    # fallback: use a simpler API
    req = urllib.request.Request("https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=1d",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        vix_data = json.loads(resp.read())
        vix_price = vix_data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    print(f"VIX: {vix_price:.2f}")
except Exception as e:
    vix_price = 0
    print(f"VIX: ERROR (may need alternative source)")

# Save all results
result = {
    "raw_count": raw_count,
    "feat_count": feat_count,
    "label_count": label_count,
    "global_ics": global_ics,
    "tw_ics": tw_ics,
    "sell_win_rate": round(sell_win_rate*100, 2),
    "recent_100": round(recent_100*100, 2),
    "recent_500": round(recent_500*100, 2),
    "max_consecutive_losses": max_consecutive,
    "global_ic_pass": global_pass,
    "tw_ic_pass": tw_pass,
    "btc_price": round(btc_price, 0),
    "fng": fng_val,
    "lsr": round(lsr, 4),
    "funding_rate": funding_rate,
    "taker_ratio": round(taker_ratio, 4),
    "open_interest": round(oi, 2),
    "vix": round(vix_price, 2) if vix_price else "unknown"
}
print(f"\n=== JSON RESULT ===")
print(json.dumps(result, indent=2))

db.close()
