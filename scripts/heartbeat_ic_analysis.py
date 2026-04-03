#!/usr/bin/env python3
"""Poly-Trader Heartbeat - Data Collection + IC Analysis
Uses direct SQLite to avoid database.engine import issues.
"""
import json, os, sys
import numpy as np

sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

import sqlite3

DB_PATH = os.path.join('/home/kazuha/Poly-Trader', 'poly_trader.db')
db = sqlite3.connect(DB_PATH)

# ===== STEP 1: Data Collection =====
raw_count = db.execute("SELECT COUNT(*) FROM raw_market_data").fetchone()[0]
feat_count = db.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
label_count = db.execute("SELECT COUNT(*) FROM labels").fetchone()[0]

pos_count = db.execute("SELECT COUNT(*) FROM labels WHERE label_sell_win = 1").fetchone()[0] or 0
neg_count = db.execute("SELECT COUNT(*) FROM labels WHERE label_sell_win = 0").fetchone()[0] or 0
total = pos_count + neg_count
print(f"Raw: {raw_count} | Features: {feat_count} | Labels: {label_count}")
print(f"Labels: {pos_count} pos / {neg_count} neg ({pos_count/total*100:.1f}% pos)")

# BTC price
latest = db.execute("SELECT close_price, timestamp, funding_rate, fear_greed_index, volume FROM raw_market_data ORDER BY timestamp DESC LIMIT 1").fetchone()
btc_price = latest[0] if latest else None
btc_ts = latest[1] if latest else None
funding_rate = latest[2] if latest and latest[2] else None
fng = latest[3] if latest and latest[3] else None
vol_24h = latest[4] if latest and latest[4] else None
print(f"BTC Price: ${btc_price:,.0f}" if btc_price else "BTC Price: N/A")
print(f"Funding Rate: {funding_rate}")
print(f"FNG: {fng}")

# ===== STEP 2: IC Analysis =====
# Fetch features and labels
feat_rows = db.execute("SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, feat_pulse, feat_aura, feat_mind FROM features_normalized ORDER BY timestamp").fetchall()
feat_labels = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']
feat_fields = ['feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind']

label_rows = db.execute("SELECT timestamp, label_sell_win FROM labels").fetchall()
label_map = {row[0]: row[1] for row in label_rows if row[1] is not None}

# Build feature vectors
feat_data = {name: [] for name in feat_labels}
timestamps = []
for row in feat_rows:
    ts = row[0]
    timestamps.append(ts)
    for i, name in enumerate(feat_labels):
        try:
            feat_data[name].append(float(row[i+1]) if row[i+1] is not None else np.nan)
        except:
            feat_data[name].append(np.nan)

ic_results = {}
print(f"\n=== Full Dataset IC Analysis ({len(timestamps)} samples) ===")
for name in feat_labels:
    fv = np.array(feat_data[name])
    # Match with labels
    matched_f, matched_l = [], []
    for j, ts in enumerate(timestamps):
        if ts in label_map and not np.isnan(fv[j]):
            matched_f.append(fv[j])
            matched_l.append(label_map[ts])
    
    matched_f = np.array(matched_f)
    matched_l = np.array(matched_l)
    
    if len(matched_f) < 100:
        ic_val = 0
    else:
        std_val = np.std(matched_f)
        if std_val < 1e-10:
            ic_val = 0
        else:
            corr = np.corrcoef(matched_f, matched_l)
            ic_val = corr[0, 1] if np.isfinite(corr[0, 1]) else 0
    
    n = len(matched_f)
    unique = len(np.unique(matched_f))
    is_binary = unique <= 2 
    status = "PASS" if abs(ic_val) >= 0.05 else "FAIL"
    binary_note = " *** BINARY" if is_binary else ""
    print(f"  {name:8s}: IC={ic_val:+.4f}  std={np.std(matched_f):.4f}  n={n}  unique={unique}{binary_note}  [{status}]")
    ic_results[name] = {'ic': round(ic_val, 4), 'std': round(float(np.std(matched_f)), 4), 'n': n, 'unique': unique, 'is_binary': is_binary}

# ===== Regime-aware IC =====
print(f"\n=== Regime-aware IC Analysis ===")
n = len(timestamps)
third = n // 3
regime_splits = [
    ("Bear", timestamps[:third]),
    ("Chop", timestamps[third:2*third]),
    ("Bull", timestamps[2*third:]),
]

# Also try with regime_label column if available
try:
    col_info = db.execute("PRAGMA table_info(features_normalized)").fetchall()
    col_names = [c[1] for c in col_info]
    has_regime = 'regime_label' in col_names
except:
    has_regime = False

if has_regime:
    try:
        # Count how many have regime labels
        counts = db.execute("SELECT regime_label, COUNT(*) FROM features_normalized GROUP BY regime_label").fetchall()
        print("Regime distribution from DB:", counts)
    except:
        pass

for regime_name, ts_regime in regime_splits:
    ts_set = set(ts_regime)
    print(f"\n  {regime_name} regime ({len(ts_regime)} samples):")
    passing = 0
    for name in feat_labels:
        fv = np.array(feat_data[name])
        matched_f, matched_l = [], []
        for j, ts in enumerate(timestamps):
            if ts in ts_set and ts in label_map and not np.isnan(fv[j]):
                matched_f.append(fv[j])
                matched_l.append(label_map[ts])
        
        matched_f = np.array(matched_f)
        matched_l = np.array(matched_l)
        
        if len(matched_f) < 50:
            ic_val = 0
        else:
            std_val = np.std(matched_f)
            if std_val < 1e-10:
                ic_val = 0
            else:
                corr = np.corrcoef(matched_f, matched_l)
                ic_val = corr[0, 1] if np.isfinite(corr[0, 1]) else 0
        
        is_binary = len(np.unique(matched_f)) <= 2
        if abs(ic_val) >= 0.05:
            passing += 1
            print(f"    {name:8s}: IC={ic_val:+.4f}  n={len(matched_f)}  *** PASS")
        else:
            print(f"    {name:8s}: IC={ic_val:+.4f}  n={len(matched_f)}")
    ic_results[f'{regime_name}_passing'] = passing
    print(f"    >> {passing}/8 passing threshold (|IC| >= 0.05)")

db.close()

# Save results
output = {
    'raw_count': raw_count,
    'feat_count': feat_count,
    'label_count': label_count,
    'label_pos': pos_count,
    'label_neg': neg_count,
    'btc_price': btc_price,
    'funding_rate': funding_rate,
    'fng': fng,
    'features': ic_results,
    'timestamp': btc_ts
}
os.makedirs('data', exist_ok=True)
with open('data/ic_heartbeat_latest.json', 'w') as f:
    json.dump(output, f, indent=2, default=str)
print(f"\nResults saved to data/ic_heartbeat_latest.json")
