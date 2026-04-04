#!/usr/bin/env python3
"""Heartbeat data collection script - Step 1 & 2"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'poly_trader.db')

if not os.path.exists(db_path):
    print(f"ERROR: Database not found at {db_path}")
    sys.exit(1)

db = sqlite3.connect(db_path)
db.row_factory = sqlite3.Row

# Raw counts
raw = db.execute("SELECT COUNT(*) as c FROM raw_market_data").fetchone()["c"]
feat = db.execute("SELECT COUNT(*) as c FROM feature_store").fetchone()["c"]
labels = db.execute("SELECT COUNT(*) as c FROM label_store").fetchone()["c"]

print(f"COUNTS|Raw:{raw}|Features:{feat}|Labels:{labels}")

# Latest BTC price with previous for change calculation
rows = db.execute("SELECT price, timestamp FROM raw_market_data ORDER BY rowid DESC LIMIT 2").fetchall()
if len(rows) >= 2:
    current_price = rows[0]["price"]
    prev_price = rows[1]["price"]
    change_pct = (current_price - prev_price) / prev_price * 100
    print(f"BTC|${current_price:.0f}|Change:+{change_pct:.2f}%" if change_pct >= 0 else f"BTC|${current_price:.0f}|Change:{change_pct:.2f}%")
    print(f"BTC_TS|{rows[0]['timestamp']}")
elif len(rows) == 1:
    print(f"BTC|${rows[0]['price']:.0f}|Change:N/A")

# sell_win stats
sw = db.execute("SELECT AVG(sell_win) as sw FROM label_store WHERE sell_win IS NOT NULL").fetchone()
print(f"SOLD_WIN_GLOBAL|{sw['sw']:.4f}")

for n in [500, 100, 50]:
    recent = db.execute(f"SELECT AVG(sell_win) as sw FROM (SELECT sell_win FROM label_store WHERE sell_win IS NOT NULL ORDER BY rowid DESC LIMIT {n})").fetchone()
    print(f"SELL_WIN_{n}|{recent['sw']:.4f}")

# Fear & Greed
fng = db.execute("SELECT value FROM fear_greed_index ORDER BY timestamp DESC LIMIT 1").fetchone()
if fng:
    print(f"FNG|{fng['value']}")

# Funding rate
fr = db.execute("SELECT value FROM funding_rate ORDER BY timestamp DESC LIMIT 1").fetchone()
if fr:
    print(f"FUNDING_RATE|{fr['value']}")

# Derivatives
derivs = db.execute("SELECT * FROM derivatives ORDER BY timestamp DESC LIMIT 1").fetchone()
if derivs:
    print(f"LSR|{derivs['lsr']}")
    print(f"TAKER|{derivs['taker']}")
    print(f"OI|{derivs['open_interest']}")
    print(f"GSR|{derivs.get('gsr', 'N/A')}")

# VIX
vix = db.execute("SELECT value FROM vix_index ORDER BY timestamp DESC LIMIT 1").fetchone()
if vix:
    print(f"VIX|{vix['value']:.2f}")

# DXY
dxy = db.execute("SELECT value FROM dxy_index ORDER BY timestamp DESC LIMIT 1").fetchone()
if dxy:
    print(f"DXY|{dxy['value']:.2f}")

# IC Analysis - calculate IC for all features against sell_win
# IC = Spearman correlation of feature with sell_win
from scipy.stats import spearmanr
import numpy as np

feature_cols = db.execute("PRAGMA table_info(feature_store)").fetchall()
col_names = [r["name"] for r in feature_cols]
exclude_cols = ["rowid"]  # exclude non-feature columns

# Map of feature -> sensory name
sense_map = {
    "feat_eye": "Eye", "feat_nose": "Nose", "feat_ear": "Ear",
    "feat_ear_zscore": "Ear", "feat_mind": "Mind", "feat_tongue": "Tongue",
    "feat_body": "Body", "feat_pulse": "Pulse", "feat_aura": "Aura",
    "feat_rsi_14": "RSI14", "feat_macd_hist": "MACD_hist",
    "feat_bb_pct": "BB%p", "feat_atr_pct": "ATR_pct",
    "feat_vwap_dev": "VWAP_dev",
    "feat_vol_ratio": "VolRatio", "feat_volume_zscore": "VolZ",
    "feat_momentum_4h": "Mom4h", "feat_momentum_24h": "Mom24h",
}

# Also check for placeholder features
placeholders = ["whisper", "tone", "chorus", "hype", "oracle", "shock", "tide", "storm"]

# Get all feature values
all_data = db.execute("SELECT * FROM feature_store").fetchall()

if not all_data:
    print("ERROR: No feature data found")
    db.close()
    sys.exit(1)

# Get sell_win labels
labels_data = db.execute("SELECT sell_win FROM label_store").fetchall()

# Build arrays
col_types = {r["name"]: r["type"] for r in feature_cols}
print(f"\n--- IC Analysis (h=4) ---")

feature_ics = []
ic_results = {}

for col in col_names:
    if col in exclude_cols or col == "sell_win":
        continue
    
    # Get feature values
    vals = [row[col] for row in all_data if row[col] is not None]
    n_valid = len(vals)
    
    if n_valid < 100:
        # Too few valid values
        std_val = 0
        unique_count = len(set([row[col] for row in all_data]))
        print(f"IC|{col}|null|std:null|unique:{unique_count}|valid:{n_valid}|DEAD")
        feature_ics.append((col, None, 0))
        continue
    
    arr = np.array(vals, dtype=float)
    std_val = np.std(arr)
    unique_count = len(np.unique(arr))
    
    if std_val < 1e-10:
        print(f"IC|{col}|0.0000|std:0|unique:{unique_count}|valid:{n_valid}|DEAD")
        feature_ics.append((col, 0.0, 0))
        continue
    
    # Get corresponding sell_win values
    valid_indices = [i for i, row in enumerate(all_data) if row[col] is not None]
    sw_vals = [labels_data[i]["sell_win"] for i in valid_indices if i < len(labels_data) and labels_data[i]["sell_win"] is not None]
    feat_vals = [float(all_data[i][col]) for i in valid_indices if i < len(labels_data) and labels_data[i]["sell_win"] is not None]
    
    if len(sw_vals) < 100:
        print(f"IC|{col}|N/A|std:{std_val:.4f}|unique:{unique_count}|label_mismatch|DEAD")
        feature_ics.append((col, None, std_val))
        continue
    
    corr, pvalue = spearmanr(feat_vals, sw_vals)
    status = "PASS" if abs(corr) >= 0.05 else "FAIL"
    
    sense_name = sense_map.get(col, col)
    print(f"IC|{col}|{corr:+.4f}|std:{std_val:.4f}|unique:{unique_count}|{status}")
    
    # Track by sensory name
    if sense_name not in ic_results:
        ic_results[sense_name] = []
    ic_results[sense_name].append((col, corr, std_val, status))

# Also check for placeholder features
for ph in placeholders:
    for col in col_names:
        if ph in col.lower():
            vals = [row[col] for row in all_data]
            unique_count = len(set([v for v in vals if v is not None]))
            non_null = sum(1 for v in vals if v is not None)
            print(f"IC|{col}|NULL|std:0|unique:{unique_count}|valid:{non_null}|PLACEHOLDER_DEAD")
            break

print("\n--- Summary ---")
passed = [(col, corr, std) for col, corr, std in feature_ics if corr is not None and abs(corr) >= 0.05]
failed = [(col, corr, std) for col, corr, std in feature_ics if corr is None or abs(corr) < 0.05]
print(f"Passed IC≥0.05: {len(passed)}/{len(feature_ics)}")

db.close()
