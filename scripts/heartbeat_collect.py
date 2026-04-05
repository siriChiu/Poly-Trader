#!/usr/bin/env python3
"""Heartbeat data collection — Step 1"""
import sqlite3, json, os, sys
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "poly_trader.db"
if not db_path.exists():
    print(f"ERROR: DB not found at {db_path}")
    sys.exit(1)

db = sqlite3.connect(str(db_path))
cur = db.cursor()

# Counts
cur.execute("SELECT COUNT(*) FROM raw_market_data")
raw = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM features")
feat = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM labels")
lbl = cur.fetchone()[0]

# Latest BTC
cur.execute("SELECT json_extract(data, '$.close'), json_extract(data, '$.timestamp') FROM raw_market_data ORDER BY rowid DESC LIMIT 1")
btc = cur.fetchone()

# Derivatives
try:
    cur.execute("SELECT close, open_interest, funding_rate, long_short_ratio FROM market_derivatives ORDER BY timestamp DESC LIMIT 1")
    derivs = cur.fetchone()
except:
    derivs = None

# Sell win stats
cur.execute("SELECT COUNT(*), AVG(sell_win) FROM labels")
label_stats = cur.fetchone()

# FNG
try:
    cur.execute("SELECT value, value_classification FROM fear_greed_index ORDER BY timestamp DESC LIMIT 1")
    fng = cur.fetchone()
except:
    fng = None

db.close()

print(f"Raw: {raw}")
print(f"Features: {feat}")
print(f"Labels: {lbl}")
print(f"BTC Price: {btc[0] if btc else 'N/A'}")
print(f"BTC Timestamp: {btc[1] if btc else 'N/A'}")
if derivs:
    print(f"Derivatives: LSR={derivs[3]}, OI={derivs[1]}, Funding={derivs[2]}")
else:
    print("Derivatives: N/A")
if fng:
    print(f"FNG: {fng[0]} ({fng[1]})")
else:
    print("FNG: N/A")
print(f"Sell Win: count={label_stats[0]}, avg={label_stats[1]:.4f}")
