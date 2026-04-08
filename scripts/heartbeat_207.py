#!/usr/bin/env python3
"""Heartbeat #207 data collection and IC analysis."""
import sqlite3
import numpy as np
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

db_path = '/home/kazuha/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# === STEP 1: Data Collection ===
raw_count = conn.execute('SELECT COUNT(*) FROM raw_market_data').fetchone()[0]
feat_count = conn.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
label_count = conn.execute('SELECT COUNT(*) FROM labels').fetchone()[0]

# BTC price from features (feat_eye is normalized close price)
latest_price_row = conn.execute('SELECT close_price FROM raw_market_data ORDER BY id DESC LIMIT 1').fetchone()
btc_price = latest_price_row[0] if latest_price_row else 0

# FNG from raw_market_data
fng_row = conn.execute('SELECT fear_greed_index FROM raw_market_data ORDER BY id DESC LIMIT 1').fetchone()
fng_val_raw = fng_row[0] if fng_row else 0

# Try to get FNG classification from external data if available
if fng_val_raw and fng_val_raw > 0:
    fng_val = int(fng_val_raw)
    if fng_val <= 25:
        fng_class = 'Extreme Fear'
    elif fng_val <= 45:
        fng_class = 'Fear'
    elif fng_val <= 55:
        fng_class = 'Neutral'
    elif fng_val <= 75:
        fng_class = 'Greed'
    else:
        fng_class = 'Extreme Greed'
else:
    fng_val = 0
    fng_class = 'N/A'

# sell_win stats
sell_win_row = conn.execute('SELECT AVG(label_spot_long_win), COUNT(*) FROM labels WHERE label_spot_long_win IS NOT NULL').fetchone()
global_sw = sell_win_row[0]
sw_count = sell_win_row[1]

# Recent sell_win (last 50)
recent = conn.execute('SELECT label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id DESC LIMIT 50').fetchall()
recent_vals = [r[0] for r in recent if r[0] is not None]
recent_sw = sum(recent_vals) / len(recent_vals) if recent_vals else 0

# Consecutive sell_win=0
all_sw = conn.execute('SELECT label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id DESC').fetchall()
all_sw_vals = [r[0] for r in all_sw]
consec_zeros = 0
for v in all_sw_vals:
    if v == 0:
        consec_zeros += 1
    else:
        break

# NULL regime labels in labels table
null_regime = conn.execute('SELECT COUNT(*) FROM labels WHERE regime_label IS NULL').fetchone()
null_count = null_regime[0]

# Regime distribution
regime_dist = conn.execute('SELECT regime_label, COUNT(*) FROM labels GROUP BY regime_label').fetchall()
print(f"Regime distribution: {[(r[0] or 'NULL', r[1]) for r in regime_dist]}")

# Sell_win by regime
regime_sw = conn.execute("SELECT regime_label, AVG(label_spot_long_win), COUNT(*) FROM labels WHERE label_spot_long_win IS NOT NULL GROUP BY regime_label").fetchall()
for r in regime_sw:
    rl = r[0] or 'NULL'
    print(f"  {rl}: avg sell_win={r[1]:.3f}, n={r[2]}")

# === STEP 2: IC Analysis ===
print(f"\n=== Sensory IC Analysis (h=4) ===")

# Feature columns (excluding 8 dead features that should be NULL anyway)
feature_cols = [
    'feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body',
    'feat_pulse', 'feat_aura', 'feat_mind',
    'feat_vix', 'feat_dxy', 'feat_rsi14', 'feat_macd_hist',
    'feat_atr_pct', 'feat_vwap_dev', 'feat_bb_pct_b'
]

# Get features data - all rows
feat_rows = conn.execute(f"SELECT id, timestamp, {', '.join(feature_cols)} FROM features_normalized ORDER BY id").fetchall()
n_feat = len(feat_rows)

# Get labels
label_rows = conn.execute("SELECT id, timestamp, label_spot_long_win, regime_label FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id").fetchall()
n_label = len(label_rows)

print(f"Features rows: {n_feat}, Labels rows: {n_label}")

if n_feat == 0 or n_label == 0:
    print("ERROR: No data!")
    conn.close()
    exit(1)

# Build arrays - align by matching timestamps
# Features and labels should roughly align by timestamp
# Use timestamp matching for proper alignment
feat_data = {r['id']: r for r in feat_rows}
label_data = {r['id']: r for r in label_rows}

# Find matching IDs
feat_ids = sorted(feat_data.keys())
label_ids = sorted(label_data.keys())

# For proper alignment, match by timestamp
feat_ts = {r['timestamp']: r for r in feat_rows}
label_ts = {r['timestamp']: r for r in label_rows}

# Find common timestamps
common_ts = sorted(set(feat_ts.keys()) & set(label_ts.keys()))
print(f"Common timestamps: {len(common_ts)}")

if len(common_ts) < 100:
    # Fallback: align by position
    min_n = min(n_feat, n_label)
    print(f"Using positional alignment, min_n={min_n}")
    
    feat_arrs = {}
    for fc in feature_cols:
        feat_arrs[fc] = np.array([feat_rows[i][fc] for i in range(min_n)])
    
    sell_win_arr = np.array([label_rows[i][2] for i in range(min_n)], dtype=float)
    regime_arr = [label_rows[i][3] for i in range(min_n)]
else:
    # Align by timestamp
    min_n = len(common_ts)
    print(f"Using timestamp alignment, n={min_n}")
    
    feat_arrs = {}
    for fc in feature_cols:
        feat_arrs[fc] = np.array([feat_ts[ts][fc] for ts in common_ts], dtype=float)
    
    sell_win_arr = np.array([label_ts[ts][2] for ts in common_ts], dtype=float)
    regime_arr = [label_ts[ts][3] for ts in common_ts]

# Calculate IC for each feature
ic_results = []
for fc in feature_cols:
    vals = feat_arrs[fc]
    mask = np.isfinite(vals) & np.isfinite(sell_win_arr)
    v = vals[mask]
    s = sell_win_arr[mask]
    if len(v) < 100:
        continue
    std_val = float(np.std(v))
    unique_count = len(np.unique(v))
    
    if std_val > 1e-10:
        ic = float(np.corrcoef(v, s)[0, 1])
        if np.isnan(ic):
            ic = 0.0
    else:
        ic = 0.0
    
    passed = abs(ic) >= 0.05
    ic_results.append({
        'name': fc,
        'ic': ic,
        'std': std_val,
        'n': len(v),
        'unique': unique_count,
        'passed': passed,
    })

# Print per-feature IC
print("\nPer-feature IC:")
for r in sorted(ic_results, key=lambda x: abs(x['ic']), reverse=True):
    status = "PASS" if r['passed'] else "FAIL"
    print(f"  {r['name']:20s} IC={r['ic']:+.4f} std={r['std']:.4f} n={r['n']} unique={r['unique']} {status}")

# === Regime IC ===
regimes = ['Bull', 'Bear', 'Chop', 'Neutral']
print("\nRegime-wise IC:")
regime_pass_counts = {}
for regime in regimes:
    reg_mask = np.array([r == regime for r in regime_arr])
    if reg_mask.sum() < 100:
        print(f"  {regime}: too few samples ({reg_mask.sum()})")
        regime_pass_counts[regime] = (0, len(feature_cols))
        continue
    
    reg_sw = sell_win_arr[reg_mask]
    reg_passed = 0
    reg_features = []
    for fc in feature_cols:
        vals = feat_arrs[fc][reg_mask]
        mask = np.isfinite(vals) & np.isfinite(reg_sw)
        v = vals[mask]
        s = reg_sw[mask]
        if len(v) < 50:
            continue
        if np.std(v) > 1e-10:
            ic = float(np.corrcoef(v, s)[0, 1])
            if np.isnan(ic): ic = 0
            if abs(ic) >= 0.05:
                reg_passed += 1
                reg_features.append(f"{fc}={ic:+.3f}")
    regime_pass_counts[regime] = (reg_passed, len(feature_cols))
    print(f"  {regime}: {reg_passed}/{len(feature_cols)} passed ({', '.join(reg_features[:5])}...)" if reg_features else f"  {regime}: {reg_passed}/{len(feature_cols)} passed")

# NULL regime IC
null_mask = np.array([r is None for r in regime_arr])
if null_mask.sum() > 0:
    null_sw = sell_win_arr[null_mask]
    null_sw_mean = float(np.mean(null_sw))
    print(f"  NULL regime: {null_mask.sum()} samples, avg sell_win={null_sw_mean:.3f}")

# === Model metrics ===
latest_metric = conn.execute('SELECT * FROM model_metrics ORDER BY id DESC LIMIT 1').fetchone()
if latest_metric:
    print(f"\nLatest model metric (id={latest_metric[0]}):")
    col_names = ['id', 'timestamp', 'train_accuracy', 'cv_accuracy', 'cv_std', 'n_features', 'notes']
    for i, cn in enumerate(col_names):
        print(f"  {cn}: {latest_metric[i]}")

# === Summary ===
passed_count = sum(1 for r in ic_results if r['passed'])
print(f"\n=== Summary ===")
print(f"Raw: {raw_count}, Features: {feat_count}, Labels: {label_count}")
print(f"BTC: ${btc_price:.0f}, FNG: {fng_val} ({fng_class})")
print(f"Global sell_win: {global_sw:.3f}")
print(f"Recent sell_win (last 50): {recent_sw:.3f}")
print(f"Consecutive sell_win=0: {consec_zeros}")
print(f"NULL regime labels: {null_count}")
print(f"Features passing IC threshold: {passed_count}/{len(ic_results)}")
for reg, rc in regime_pass_counts.items():
    print(f"  {reg} regime: {rc[0]}/{rc[1]} passed")

# Output JSON for further processing
output = {
    'raw_count': raw_count,
    'feat_count': feat_count,
    'label_count': label_count,
    'btc_price': btc_price,
    'fng_value': fng_val,
    'fng_class': fng_class,
    'global_sell_win': round(global_sw, 3),
    'recent_sell_win_50': round(recent_sw, 3),
    'consecutive_zeros': consec_zeros,
    'null_regime_labels': null_count,
    'ic_passed': passed_count,
    'ic_total': len(ic_results),
    'feature_ics': ic_results,
    'regime_pass_counts': {k: list(v) for k, v in regime_pass_counts.items()},
}
with open('/tmp/heartbeat_ic.json', 'w') as f:
    json.dump(output, f, indent=2)

conn.close()
print("\nIC data saved to /tmp/heartbeat_ic.json")
