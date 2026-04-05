#!/usr/bin/env python3
"""Step 1 & 2: Data collection + IC analysis"""
import sqlite3, json, sys, os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
db_path = PROJECT_ROOT / "poly_trader.db"

db = sqlite3.connect(str(db_path))
cur = db.cursor()

# Step 1: Data collection
print("=" * 60)
print("STEP 1: DATA COLLECTION")
print("=" * 60)

cur.execute("SELECT COUNT(*) FROM raw_market_data")
raw = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM features_normalized")
feat = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM labels WHERE future_return_pct IS NOT NULL")
lbl = cur.fetchone()[0]

# Latest BTC
cur.execute("SELECT close_price, timestamp FROM raw_market_data ORDER BY id DESC LIMIT 1")
btc = cur.fetchone()

# Derivatives info from raw_market_data
cur.execute("SELECT funding_rate, volatility, oi_roc FROM raw_market_data ORDER BY id DESC LIMIT 1")
derivs = cur.fetchone()

# Sell win stats
cur.execute("SELECT COUNT(*), AVG(CASE WHEN future_return_pct < 0 THEN 1 ELSE 0 END) as sell_win FROM labels WHERE future_return_pct IS NOT NULL")
label_stats = cur.fetchone()

# FNG
cur.execute("SELECT fear_greed_index FROM raw_market_data ORDER BY id DESC LIMIT 1")
fng_row = cur.fetchone()

print(f"Raw: {raw}")
print(f"Features: {feat}")
print(f"Labels: {lbl}")
print(f"BTC Price: {btc[0] if btc else 'N/A'}")
print(f"FNG: {fng_row[0] if fng_row else 'N/A'}")
print(f"Derivatives: Funding={derivs[0] if derivs else 'N/A'}, Vol={derivs[1] if derivs else 'N/A'}, OI_ROC={derivs[2] if derivs else 'N/A'}")
print(f"Sell Win Rate: {label_stats[1]*100:.2f}%" if label_stats else "N/A")

# Step 2: IC Analysis
print("\n" + "=" * 60)
print("STEP 2: SENSORY IC ANALYSIS")
print("=" * 60)

try:
    cur.execute("PRAGMA table_info(labels)")
    label_cols = [r[1] for r in cur.fetchall()]
    print(f"Label columns: {label_cols}")
except:
    label_cols = []

try:
    cur.execute("PRAGMA table_info(features_normalized)")
    feat_cols = [r[1] for r in cur.fetchall()]
    print(f"Feature columns ({len(feat_cols)}): {feat_cols[:20]}")
except:
    feat_cols = []

# Try to compute IC for each feature against sell_win (future_return < 0)
# IC = correlation(feature, label)
import numpy as np

cur.execute("SELECT * FROM features_normalized LIMIT 5")
sample = cur.fetchone()
col_names = [d[0] for d in cur.description]

# Get features and labels aligned
if 'future_return_pct' in label_cols:
    print("\nComputing global IC against sell_win label...")
    
    # Build aligned dataset
    query = """
        SELECT COALESCE(f.eye_dist, 0), COALESCE(f.ear_prob, 0), COALESCE(f.tongue_sentiment, 0),
               COALESCE(f.volatility, 0), COALESCE(f.oi_roc, 0), COALESCE(f.vix_value, 0),
               COALESCE(f.dxy_value, 0), COALESCE(f.polymarket_prob, 0), COALESCE(f.stablecoin_mcap, 0),
               COALESCE(f.funding_rate, 0), COALESCE(f.body_label, 0),
               l.future_return_pct, l.rsi, l.macd_hist, l.bb_pct_b
        FROM features_normalized f
        INNER JOIN labels l ON f.id = l.id  -- or however they're joined
        WHERE l.future_return_pct IS NOT NULL
        LIMIT 100
    """
    # First check if we can join
    cur.execute("SELECT COUNT(*) FROM features_normalized")
    feat_count = cur.fetchone()[0]
    print(f"Features rows: {feat_count}")
    
    # Just compute basic IC from features table stats
    # Try to get the data differently - via heartbeat data files
    ic_file = PROJECT_ROOT / "data" / "ic_signs.json"
    if ic_file.exists():
        with open(ic_file) as f:
            ic_data = json.load(f)
        print(f"\nic_signs.json: {json.dumps(ic_data, indent=2)[:500]}")
    
    # Check latest ic heartbeat files
    ic_latest = PROJECT_ROOT / "data" / "ic_heartbeat_latest.json"
    if ic_latest.exists():
        with open(ic_latest) as f:
            ic_lat = json.load(f)
        print(f"\nic_heartbeat_latest.json keys: {list(ic_lat.keys())[:20]}")
        if 'ics' in ic_lat:
            print(f"ICs: {ic_lat['ics']}")
        if 'global_ic' in ic_lat:
            print(f"Global IC: {ic_lat['global_ic']}")

    # Run ic_analysis.py
    print("\n--- Running ic_analysis.py ---")
    os.system(f"cd {PROJECT_ROOT} && python scripts/ic_analysis.py 2>&1 | tail -40")

db.close()
