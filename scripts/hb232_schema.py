#!/usr/bin/env python3
"""Heartbeat #232 — Schema inspection + full data pipeline"""
import sqlite3, json, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
db = sqlite3.connect(str(ROOT / "poly_trader.db"))

# Raw schema
raw_cols = db.execute("PRAGMA table_info(raw_market_data)").fetchall()
print(f"raw_market_data ({len(raw_cols)} cols): {[c[1] for c in raw_cols]}")

# Latest raw
raw_sample = db.execute("SELECT * FROM raw_market_data ORDER BY rowid DESC LIMIT 1").fetchone()
print(f"Latest raw row (first 10 fields): {raw_sample[:10]}")

# BTC price
close_col = [c[1] for c in raw_cols if 'close' in c[1].lower()]
ts_col = [c[1] for c in raw_cols if 'time' in c[1].lower() or 'stamp' in c[1].lower()]
print(f"close col: {close_col}, ts col: {ts_col}")

if close_col and ts_col:
    btc = db.execute(f"SELECT {close_col[0]}, {ts_col[0]} FROM raw_market_data ORDER BY rowid DESC LIMIT 1").fetchone()
    print(f"BTC: close={btc[0]}, time={btc[1]}")

# Labels
label_cols = db.execute("PRAGMA table_info(labels)").fetchall()
print(f"\nlabels ({len(label_cols)} cols): {[c[1] for c in label_cols]}")

# Sell win
sw = db.execute("SELECT COUNT(*), AVG(label_sell_win) FROM labels").fetchone()
print(f"Labels: count={sw[0]}, sell_win_avg={sw[1]:.4f}")

# Consecutive losses
try:
    recent = db.execute("SELECT label_sell_win FROM labels ORDER BY rowid DESC LIMIT 200").fetchall()
    streak = 0
    for r in recent:
        if r[0] == 0:
            streak += 1
        else:
            break
    print(f"Consecutive losses (recent): {streak}")
except:
    print("Can't compute streak")

# Features
feat_cols = db.execute("PRAGMA table_info(features_normalized)").fetchall()
print(f"\nfeatures_normalized ({len(feat_cols)} cols)")
sense_cols = [c[1] for c in feat_cols if any(s in c[1].lower() for s in ['eye','ear','nose','tongue','body','pulse','aura','mind','regime','vix','dxy'])]
print(f"Sense-like columns: {sense_cols}")

# Fear Greed
try:
    fng = db.execute("SELECT * FROM fear_greed_index ORDER BY rowid DESC LIMIT 1").fetchone()
    fng_cols = [c[1] for c in db.execute("PRAGMA table_info(fear_greed_index)").fetchall()]
    print(f"\nfear_greed_index columns: {fng_cols}")
    print(f"Latest FNG: {fng}")
except:
    print("\nNo fear_greed_index table")

# Derivatives
try:
    deriv = db.execute("SELECT * FROM market_derivatives ORDER BY rowid DESC LIMIT 1").fetchone()
    deriv_cols = [c[1] for c in db.execute("PRAGMA table_info(market_derivatives)").fetchall()]
    print(f"\nmarket_derivatives columns: {deriv_cols}")
    print(f"Latest derivatives: {deriv}")
except:
    print("\nNo market_derivatives table")

# IC signs
ic_path = ROOT / "ic_signs.json"
if ic_path.exists():
    with open(ic_path) as f:
        ic_data = json.load(f)
    print(f"\nic_signs.json: {json.dumps(ic_data, indent=2)}")
else:
    print("\nNo ic_signs.json")

# Check model metrics
try:
    metrics = db.execute("SELECT * FROM model_metrics ORDER BY rowid DESC LIMIT 3").fetchall()
    metric_cols = [c[1] for c in db.execute("PRAGMA table_info(model_metrics)").fetchall()]
    print(f"\nmodel_metrics columns: {metric_cols}")
    for m in metrics:
        print(f"  {m}")
except:
    print("\nNo model_metrics or empty")

db.close()

# Now fetch live market data for current prices
import urllib.request
try:
    req = urllib.request.Request("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
    req.add_header('User-Agent', 'Poly-Trader/1.0')
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    print(f"\nLive BTC Price: ${data['bitcoin']['usd']}")
except Exception as e:
    print(f"\nLive BTC Price fetch error: {e}")

try:
    req2 = urllib.request.Request("https://api.alternative.me/fng/")
    req2.add_header('User-Agent', 'Poly-Trader/1.0')
    resp2 = urllib.request.urlopen(req2, timeout=10)
    fng_data = json.loads(resp2.read())
    if fng_data.get('data'):
        latest = fng_data['data'][0]
        print(f"Live FNG: {latest['value']} ({latest['value_classification']})")
except Exception as e:
    print(f"Live FNG fetch error: {e}")
