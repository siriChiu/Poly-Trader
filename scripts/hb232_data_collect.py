#!/usr/bin/env python3
"""Heartbeat #232 — Data collection + IC analysis"""
import sqlite3, json, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def inspect_db(db_path):
    """Quick table inspection"""
    try:
        db = sqlite3.connect(str(db_path))
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"=== {db_path} ({len(tables)} tables) ===")
        for t in tables:
            tn = t[0]
            cnt = db.execute(f'SELECT COUNT(*) FROM {tn}').fetchone()[0]
            print(f"  {tn}: {cnt} rows")
        db.close()
    except Exception as e:
        print(f"{db_path}: ERROR {e}")

# Check all DBs
for p in ['poly_trader.db', 'data/poly_trader.db', 'data/market.db', 'data/stock.db']:
    fp = ROOT / p
    if fp.exists():
        inspect_db(fp)

# Main analysis on data/poly_trader.db (the one dev_heartbeat.py uses for raw/feat/labels)
# Actually dev_heartbeat.py uses ROOT/"poly_trader.db"
main_db = ROOT / "poly_trader.db"
print(f"\n=== Main DB: {main_db} ===")
db = sqlite3.connect(str(main_db))

# Raw count
raw = db.execute("SELECT COUNT(*) FROM raw_market_data").fetchone()[0]
feat = db.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
labels = db.execute("SELECT COUNT(*) FROM labels WHERE future_return_pct IS NOT NULL").fetchone()[0]
print(f"Raw: {raw}, Features: {feat}, Labels: {labels}")

# Latest BTC
btc = db.execute("SELECT json_extract(data, '$.close'), json_extract(data, '$.timestamp') FROM raw_market_data ORDER BY rowid DESC LIMIT 1").fetchone()
print(f"BTC: {btc}")

# Sell win
sw = db.execute("SELECT COUNT(*), AVG(sell_win) FROM labels").fetchone()
print(f"Labels total: {sw[0]}, sell_win avg: {sw[1]:.4f}")

# Fear Greed
try:
    fng = db.execute("SELECT value, value_classification FROM fear_greed_index ORDER BY timestamp DESC LIMIT 1").fetchone()
    print(f"FNG: {fng}")
except:
    print("FNG: N/A")

# Derivatives
try:
    deriv = db.execute("SELECT close, open_interest, funding_rate, long_short_ratio FROM market_derivatives ORDER BY timestamp DESC LIMIT 1").fetchone()
    print(f"Derivatives: OI={deriv[1]}, Funding={deriv[2]}, LSR={deriv[3]}")
except:
    print("Derivatives: N/A")

# Check for features table (vs features_normalized)
feat_tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%feature%'").fetchall()
print(f"Feature tables: {feat_tables}")

# Check for labels columns
try:
    label_cols = db.execute("PRAGMA table_info(labels)").fetchall()
    print(f"Label columns: {[c[1] for c in label_cols]}")
except:
    print("No labels table in main DB")

# Check for regime
try:
    regime = db.execute("SELECT DISTINCT regime FROM labels WHERE regime IS NOT NULL").fetchall()
    print(f"Regimes: {regime}")
except:
    print("No regime column")

# Check if features_normalized has all expected columns
try:
    feat_cols = db.execute("PRAGMA table_info(features_normalized)").fetchall()
    print(f"Feature columns ({len(feat_cols)}): {[c[1] for c in feat_cols]}")
except:
    print("No features_normalized table")

# Check ic_signs.json
ic_path = ROOT / "ic_signs.json"
if ic_path.exists():
    with open(ic_path) as f:
        ic_data = json.load(f)
    print(f"\n=== ic_signs.json ===")
    print(json.dumps(ic_data, indent=2))
else:
    print("\nNo ic_signs.json found")

db.close()
