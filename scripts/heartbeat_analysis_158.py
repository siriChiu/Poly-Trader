#!/usr/bin/env python
"""Heartbeat #158 detailed data pipeline and IC analysis."""
import sqlite3
import os
import numpy as np

db_path = os.path.join(os.getcwd(), 'poly_trader.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# === Data counts ===
c.execute('SELECT COUNT(*) FROM raw_market_data')
raw_count = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM features_normalized')
feat_count = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM labels')
label_count = c.fetchone()[0]

# BTC price - check raw_market_data
c.execute('SELECT close_price, timestamp FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')
btc_row = c.fetchone()
btc_price = btc_row[0] if btc_row else None
btc_ts_raw = btc_row[1] if btc_row else None

# Fear & Greed Index
c.execute('SELECT fear_greed_index, timestamp FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')
fng_row = c.fetchone()
fng = fng_row[0] if fng_row else None

# Funding rate
c.execute('SELECT funding_rate FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')
fr_row = c.fetchone()
funding_rate = fr_row[0] if fr_row else None

# OI
c.execute('SELECT volume, oi_roc FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')
oi_row = c.fetchone()
oi = oi_row[1] if oi_row else None

c.execute('SELECT AVG(label_spot_long_win) FROM labels WHERE label_spot_long_win IS NOT NULL')
swr = c.fetchone()[0]
sell_win_rate = swr

# sell_win rate for labels
print(f"Raw market data: {raw_count}")
print(f"Features: {feat_count}")
print(f"Labels: {label_count} (sell_win rate: {sell_win_rate:.4f})")
print(f"BTC price: {btc_price}")
print(f"Fear & Greed: {fng}")
print(f"Funding Rate: {funding_rate}")
print(f"OI ROC: {oi}")

# === Full Feature IC Analysis ===
print("\n=== Feature IC Analysis (full dataset, vs label_spot_long_win) ===")

# Load features - skip id, timestamp, symbol
feat_cols = ['feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body', 'feat_pulse',
             'feat_aura', 'feat_mind', 'feat_whisper', 'feat_tone', 'feat_chorus', 'feat_hype',
             'feat_oracle', 'feat_shock', 'feat_tide', 'feat_storm', 'feat_vix', 'feat_dxy']

# Load all data
c.execute(f"SELECT {', '.join(feat_cols)}, regime_label FROM features_normalized ORDER BY timestamp")
all_feat_rows = c.fetchall()
n_total = len(all_feat_rows)
print(f"Total feature rows: {n_total}")

# Load labels
c.execute("SELECT rowid, label_spot_long_win FROM labels ORDER BY timestamp")
all_labels = c.fetchall()
label_by_row = {row[0]: row[1] for row in all_labels}

# Feature data as arrays
n_features = len(feat_cols)
feat_arrays = {col: [] for col in feat_cols}
label_arrays = {col: [] for col in feat_cols}

for row in all_feat_rows:
    for i, col in enumerate(feat_cols):
        val = row[i]
        if val is not None:
            try:
                feat_arrays[col].append(float(val))
                # Use same index for label - assuming same row count
                idx = len(feat_arrays[col]) - 1
                # Labels should be aligned by position
                label_idx = len(feat_arrays['feat_eye']) - 1 if col == 'feat_eye' else None
            except (ValueError, TypeError):
                continue

# Better approach: assume rows are aligned
feat_data = {col: [] for col in feat_cols}
label_data = []

for row_idx, row in enumerate(all_feat_rows):
    valid = True
    for i, col in enumerate(feat_cols):
        val = row[i]
        if val is None:
            valid = False
            break
        try:
            feat_data[col].append(float(val))
        except (ValueError, TypeError):
            valid = False
            break
    
    if valid and row_idx < len(all_labels):
        lbl = all_labels[row_idx][1]
        if lbl is not None:
            label_data.append(float(lbl))
        else:
            valid = False
    
    if not valid:
        # Clean up partial data
        for col in feat_cols:
            if len(feat_data[col]) > len(label_data):
                feat_data[col] = feat_data[col][:len(label_data)]

n = len(label_data)
print(f"Aligned rows: {n}")

for col in feat_cols:
    vals = np.array(feat_data[col][:n])
    labels = np.array(label_data)
    
    ic = np.corrcoef(vals, labels)[0, 1]
    std = np.std(vals)
    unique = len(np.unique(vals))
    status = "PASS" if abs(ic) >= 0.05 else "FAIL"
    flag = "🔴" if (std < 1e-10 or unique == 1) else ""
    print(f"  {col}: IC={ic:+.4f} [{status}] std={std:.4f} unique={unique} {flag}")

# === Additional market data from raw_market_data ===
print("\n=== Latest Market Data ===")
# Get latest full row
c.execute("SELECT * FROM raw_market_data ORDER BY timestamp DESC LIMIT 1")
latest = c.fetchone()
c.execute("PRAGMA table_info(raw_market_data)")
raw_cols = [r[1] for r in c.fetchall()]
for col, val in zip(raw_cols, latest):
    if val is not None:
        print(f"  {col}: {val}")

# === Regime-aware analysis ===
print("\n=== Regime-Aware IC ===")
regime_idx = len(feat_cols)  # regime_label is the last column
regime_data = {}
for row in all_feat_rows:
    regime = row[regime_idx]
    if regime not in regime_data:
        regime_data[regime] = {col: [] for col in feat_cols}
    for i, col in enumerate(feat_cols):
        val = row[i]
        if val is not None:
            try:
                regime_data[regime][col].append(float(val))
            except (ValueError, TypeError):
                pass

# Load labels aligned with features
c.execute("SELECT label_spot_long_win FROM labels ORDER BY timestamp")
all_label_values = [r[0] for r in c.fetchall() if r[0] is not None]

for regime in ['Bear', 'Bull', 'Chop', 'Neutral']:
    if regime not in regime_data:
        continue
    print(f"\n  {regime}:") 
    for col in feat_cols:
        vals = np.array(regime_data[regime][col])
        if len(vals) < 30 or len(vals) > len(all_label_values):
            continue
        labels = np.array(all_label_values[:len(vals)])
        
        if np.std(vals) < 1e-10:
            continue
            
        ic = np.corrcoef(vals, labels)[0, 1]
        status = "PASS" if abs(ic) >= 0.05 else "FAIL"
        print(f"    {col}: IC={ic:+.4f} [{status}] n={len(vals)}")

conn.close()
print("\n=== Analysis Complete ===")
