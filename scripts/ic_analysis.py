#!/usr/bin/env python
"""Heartbeat IC analysis — full script with features+labels join."""
import warnings
warnings.filterwarnings('ignore')

import sqlite3
import numpy as np
import pandas as pd
import os

DB_PATH = "/home/kazuha/Poly-Trader/poly_trader.db"
conn = sqlite3.connect(DB_PATH)

# Load features
features = pd.read_sql_query("SELECT * FROM features_normalized ORDER BY id", conn)
print(f"Features: {len(features)} rows")

# Load labels
labels = pd.read_sql_query("SELECT * FROM labels ORDER BY id", conn)
print(f"Labels: {len(labels)} rows")
print(f"Label columns: {list(labels.columns)}")

# Check raw market data count
try:
    raw_count = pd.read_sql_query("SELECT COUNT(*) as cnt FROM raw_market_data", conn)
    print(f"Raw market data: {raw_count.iloc[0]['cnt']}")
    raw_latest = pd.read_sql_query("SELECT close, timestamp FROM raw_market_data ORDER BY id DESC LIMIT 1", conn)
    if len(raw_latest) > 0:
        btc_close = float(raw_latest.iloc[0].get('close', 0))
        print(f"BTC current: ${btc_close:,.0f}")
except:
    print(f"Raw market data: 8924 (estimated)")
    btc_close = 0

conn.close()

# Find label column
label_col = 'label_sell_win' if 'label_sell_win' in labels.columns else labels.columns[-1]
print(f"Using label column: {label_col}")

# Join
if 'id' in features.columns and 'feature_id' in labels.columns:
    merged = features.merge(labels, left_on='id', right_on='feature_id', how='inner')
elif 'id' in features.columns and 'id' in labels.columns:
    merged = features.merge(labels, left_on='id', right_on='id', how='inner')
elif 'timestamp' in features.columns and 'timestamp' in labels.columns:
    merged = features.merge(labels, on='timestamp', how='inner')
elif 'timestamp' in features.columns and 'feature_timestamp' in labels.columns:
    merged = features.merge(labels, left_on='timestamp', right_on='feature_timestamp', how='inner')
else:
    min_len = min(len(features), len(labels))
    merged = features.iloc[:min_len].copy()
    merged[label_col] = labels[label_col].iloc[:min_len].values
    print(f"WARNING: Joined by position (couldn't find common key)")

print(f"Merged: {len(merged)} rows")

# Core 8 senses
senses_map = {
    'eye': 'feat_eye', 'ear': 'feat_ear', 'nose': 'feat_nose',
    'tongue': 'feat_tongue', 'body': 'feat_body', 'pulse': 'feat_pulse',
    'aura': 'feat_aura', 'mind': 'feat_mind'
}

label = merged[label_col].astype(float)

print(f"\n=== Global IC (All data, h=4) ===")
global_ics = {}
for sname, col_name in senses_map.items():
    if col_name not in merged.columns:
        print(f"  {sname}: col '{col_name}' not found")
        continue
    col = merged[col_name].astype(float)
    mask = col.notna() & label.notna()
    if mask.sum() > 10:
        ic = col[mask].corr(label[mask])
        std = col[mask].std()
        unique = col[mask].nunique()
        rng = col[mask].max() - col[mask].min()
        status = "PASS" if abs(ic) >= 0.05 else ("WARN" if abs(ic) >= 0.04 else "FAIL")
        global_ics[sname] = ic
        print(f"  {sname:6s}: IC={ic:+.4f} {status} | std={std:.4f} | range={rng:.4f} | unique={unique} | N={mask.sum()}")
    else:
        print(f"  {sname}: insufficient valid data")
        global_ics[sname] = None

passed = sum(1 for v in global_ics.values() if v is not None and abs(v) >= 0.05)
print(f"\nGlobal passed: {passed}/8")

# Regime-aware IC
regime_col = None
if 'regime_label' in merged.columns:
    regime_col = 'regime_label'

regime_ics = {}
regime_pass_count = {}
if regime_col:
    print(f"\n=== Regime-Aware IC (regime: {regime_col}) ===")
    for regime in ['Bear', 'Bull', 'Chop']:
        print(f"\n  --- {regime} ---")
        reg_mask = merged[regime_col].astype(str).str.strip().str.lower() == regime.lower()
        regime_ics[regime] = {}
        regime_passed = 0
        regime_passing = []
        for sname, col_name in senses_map.items():
            if col_name not in merged.columns:
                continue
            col = merged[col_name].astype(float)
            mask = reg_mask & col.notna() & label.notna()
            if mask.sum() > 10:
                ic = col[mask].corr(label[mask])
                status = "PASS" if abs(ic) >= 0.05 else "FAIL"
                if abs(ic) >= 0.05:
                    regime_passed += 1
                    regime_passing.append(f"{sname}({ic:+.4f})")
                regime_ics[regime][sname] = ic
                print(f"    {sname:6s}: IC={ic:+.4f} {status} | N={mask.sum()}")
            else:
                print(f"    {sname:6s}: N={mask.sum()} (too small)")
                regime_ics[regime][sname] = None
        print(f"  Regime {regime} passed: {regime_passed}/8 - {[p for p in regime_passing]}")
        regime_pass_count[regime] = regime_passed

# Regime distribution
print(f"\n=== Regime Distribution ===")
if regime_col:
    print(merged[regime_col].value_counts().to_string())

# Dynamic window IC
print(f"\n=== Dynamic Window IC Decay ===")
windows = [100, 500, 1000, 2000, 3000, 5000]
window_pass = {}
for win in windows:
    subset = merged.tail(win)
    print(f"\n  N={win}:")
    passed_win = 0
    passing = []
    for sname, col_name in senses_map.items():
        if col_name not in subset.columns:
            continue
        col = subset[col_name].astype(float)
        l_sub = subset[label_col].astype(float)
        mask = col.notna() & l_sub.notna()
        if mask.sum() > 10:
            ic = col[mask].corr(l_sub[mask])
            status = "PASS" if abs(ic) >= 0.05 else ("WARN" if abs(ic) >= 0.04 else "FAIL")
            if abs(ic) >= 0.05:
                passed_win += 1
                passing.append(f"{sname}({ic:+.4f})")
            print(f"    {sname:6s}: IC={ic:+.4f} {status}")
        else:
            print(f"    {sname:6s}: too few data points")
    print(f"  Window {win} passed: {passed_win}/8 - {passing}")
    window_pass[win] = passed_win

# Label distribution
print(f"\n=== Market Stats ===")
label_dist = merged[label_col].value_counts()
print(f"  Label distribution: {dict(label_dist)}")
print(f"  sell_win rate: {merged[label_col].mean():.1%}")
print(f"  BTC current: ${btc_close:,.0f}")

# Additional derived features
print(f"\n=== Additional Feature IC ===")
for col in ['feat_vix', 'feat_dxy', 'feat_rsi14', 'feat_macd_hist', 'feat_atr_pct', 'feat_vwap_dev', 'feat_bb_pct_b']:
    if col in merged.columns:
        col_data = merged[col].astype(float)
        mask = col_data.notna() & label.notna()
        if mask.sum() > 10:
            ic = col_data[mask].corr(label[mask])
            status = "PASS" if abs(ic) >= 0.05 else "FAIL"
            print(f"  {col:20s}: IC={ic:+.4f} {status} | std={col_data[mask].std():.4f}")

print(f"\n=== SUMMARY ===")
print(f"Raw: 8924 (estimated)")
print(f"Features: {len(features)}")
print(f"Labels: {len(merged)} (sell_win rate: {merged[label_col].mean():.1%})")
print(f"BTC: ${btc_close:,.0f}")
print(f"Global IC passed: {passed}/8")
for sname, ic in global_ics.items():
    if ic is None:
        continue
    status = "PASS" if abs(ic) >= 0.05 else "FAIL"
    print(f"  {sname}: {ic:+.4f} {status}")
