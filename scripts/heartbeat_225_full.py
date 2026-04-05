#!/usr/bin/env python3
"""Heartbeat #225 - Full sensory IC analysis with correct column mapping"""
import sqlite3
import numpy as np
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "poly_trader.db")

conn = sqlite3.connect(DB_PATH)

# Load data with CORRECT column names
raw_df_sql = "SELECT * FROM raw_market_data ORDER BY id"
feat_df_sql = "SELECT * FROM features_normalized ORDER BY rowid"
label_df_sql = "SELECT * FROM labels ORDER BY rowid"

import pandas as pd

raw = pd.read_sql_query(raw_df_sql, conn)
feat = pd.read_sql_query(feat_df_sql, conn)
labels = pd.read_sql_query(label_df_sql, conn)

print(f"Raw: {len(raw)} / Features: {len(feat)} / Labels: {len(labels)}")

# === BTC Price ===
btc_col = 'close_price'  # Correct column name
if btc_col in raw.columns:
    latest_price = raw[btc_col].dropna().iloc[-1]
    print(f"BTC Price: ${latest_price:,.0f}")
    latest_ts = raw['timestamp'].iloc[-1] if 'timestamp' in raw.columns else 'N/A'
    print(f"Latest timestamp: {latest_ts}")

# === Derivatives & Macro ===
fng = raw['fear_greed_index'].dropna().iloc[-1] if 'fear_greed_index' in raw.columns else 'N/A'
print(f"FNG: {fng}")

if 'vix_value' in raw.columns:
    vix = raw['vix_value'].dropna().iloc[-1]
    print(f"VIX: {vix:.2f}")
if 'dxy_value' in raw.columns:
    dxy = raw['dxy_value'].dropna().iloc[-1]
    print(f"DXY: {dxy:.2f}")
if 'funding_rate' in raw.columns:
    fr = raw['funding_rate'].dropna().iloc[-1]
    print(f"Funding Rate: {fr:.6f}")

# === Sell Win Rate ===
# Column name is 'label_sell_win' in DB, not 'sell_win'
target_col = 'label_sell_win'
if target_col not in labels.columns:
    alternatives = [c for c in labels.columns if 'sell' in c.lower() or 'win' in c.lower()]
    if alternatives:
        target_col = alternatives[0]
        print(f"\nWARNING: using '{target_col}' instead of 'label_sell_win'")
    else:
        print("ERROR: No sell_win column found!")
        sys.exit(1)

lbl = labels[target_col].astype(float)
total_valid = lbl.dropna()
sell_win_rate = (total_valid == 1).mean()
recent_100 = lbl.dropna().iloc[-100:]
recent_100_rate = (recent_100 == 1).mean()
recent_500 = lbl.dropna().iloc[-500:]
recent_500_rate = (recent_500 == 1).mean()

print(f"\nSell Win Rate (global): {sell_win_rate*100:.2f}% ({total_valid.shape[0]} samples)")
print(f"Recent 500: {recent_500_rate*100:.2f}%")
print(f"Recent 100: {recent_100_rate*100:.2f}%")

# Check buy_win if available
if 'label_up' in labels.columns:
    up = labels['label_up'].astype(float).dropna()
    buy_win_rate = (up == 1).mean()
    print(f"Buy Win Rate (label_up): {buy_win_rate*100:.2f}%")

# === Consecutive losses ===
lbl_binary = total_valid.astype(int).values
streak = 0
max_streak = 0
start_idx = 0
current_start = 0
for i, v in enumerate(lbl_binary):
    if v == 0:
        if current_start == 0 or lbl_binary[i-1:i].item() == 1:
            current_start = i
        streak += 1
        if streak > max_streak:
            max_streak = streak
    else:
        streak = 0

print(f"\nMax loss streak: {max_streak}")
# Recent streak
recent_100_vals = total_valid.astype(int).iloc[-100:].values
recent_100_loss_streak = 0
for v in reversed(recent_100_vals):
    if v == 0:
        recent_100_loss_streak += 1
    else:
        break
print(f"Recent loss streak (in last 100): {recent_100_loss_streak}")
print(f"Recent 100 win rate: {(recent_100_vals==1).mean()*100:.2f}%")

# === Regime Analysis ===
if 'regime_label' in feat.columns:
    regime = feat['regime_label'].dropna()
    if len(regime) == len(labels):
        combined = pd.DataFrame({'sell_win': lbl, 'regime': regime.values})
        combined_valid = combined.dropna()
        print(f"\n=== Regime Sell Win Rates ===")
        for reg in combined_valid['regime'].unique():
            mask = combined_valid['regime'] == reg
            rate = (combined_valid.loc[mask, 'sell_win'] == 1).mean()
            print(f"  {reg}: {rate*100:.1f}% (n={mask.sum()})")
    else:
        print(f"\nRegime len ({len(regime)}) != Labels len ({len(labels)}), skipping")

# Global IC
print(f"\n=== Global IC (h=4, against {target_col}) ===")

feature_cols = [c for c in feat.columns if c not in ('id', 'timestamp', 'symbol', 'regime_label', 'feature_version', 'feat_vwap_dev', 'feat_bb_pct_b')]
feat_numeric = feat[feature_cols].select_dtypes(include=[np.number])

from scipy.stats import pearsonr

sens_map = {}
for col in feat_numeric.columns:
    cl = col.lower()
    if 'eye' in cl: sens_map[col] = 'Eye'
    elif 'ear' in cl: sens_map[col] = 'Ear'
    elif 'nose' in cl: sens_map[col] = 'Nose'
    elif 'tongue' in cl: sens_map[col] = 'Tongue'
    elif 'body' in cl: sens_map[col] = 'Body'
    elif 'pulse' in cl: sens_map[col] = 'Pulse'
    elif 'aura' in cl: sens_map[col] = 'Aura'
    elif 'mind' in cl: sens_map[col] = 'Mind'
    elif 'vix' in cl: sens_map[col] = 'VIX'
    elif 'dxy' in cl: sens_map[col] = 'DXY'
    elif 'rsi' in cl: sens_map[col] = 'RSI14'
    elif 'macd' in cl: sens_map[col] = 'MACD_hist'
    elif 'atr' in cl: sens_map[col] = 'ATR_pct'
    else: sens_map[col] = 'Other'

sensor_ics = {}
pass_count = 0
print(f"{'Sensor/Feature':<15} {'IC':>10} {'Status'}")
print("-" * 35)

for col in feat_numeric.columns:
    vals = feat_numeric[col].dropna()
    if len(vals) < 100:
        continue
    idx = vals.index
    lbl_aligned = lbl.reindex(idx).dropna()
    common = vals.index.intersection(lbl_aligned.index)
    if len(common) < 100:
        continue
    ic = vals.loc[common].corr(lbl_aligned.loc[common])
    if np.isnan(ic):
        continue
    
    sensor = sens_map.get(col, 'Other')
    if sensor not in sensor_ics:
        sensor_ics[sensor] = []
    sensor_ics[sensor].append((col, ic))
    
    abs_ic = abs(ic)
    status = 'PASS' if abs_ic >= 0.05 else ('NEAR' if abs_ic >= 0.04 else 'FAIL')
    if abs_ic >= 0.05:
        pass_count += 1
    print(f"{col:<15} {ic:+.4f}   {status}")

print(f"\nGlobal pass: {pass_count}/{len(feat_numeric.columns)} features")

# Aggregate by sensor
print(f"\n=== Sensor-Level IC (mean of features) ===")
core = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']
sensor_pass = 0
for s in core:
    ics = sensor_ics.get(s, [])
    if ics:
        mean_ic = np.mean([ic for _, ic in ics])
        status = 'PASS' if abs(mean_ic) >= 0.05 else 'FAIL'
        if abs(mean_ic) >= 0.05:
            sensor_pass += 1
        print(f"  {s:<8}: {mean_ic:+.4f} ({status}, {len(ics)} features)")
    
print(f"Sensor pass: {sensor_pass}/8")

# Also check VIX/DXY/RSI/MACD/ATR
print(f"\n=== Macro/Technical IC ===")
for s in ['VIX', 'DXY', 'RSI14', 'MACD_hist', 'ATR_pct']:
    ics = sensor_ics.get(s, [])
    if ics:
        mean_ic = np.mean([ic for _, ic in ics])
        print(f"  {s:<10}: {mean_ic:+.4f} ({len(ics)} features)")

# === TW-IC (Time-Weighted, tau=200) ===
print(f"\n=== TW-IC (tau=200) ===")
# Simple time-weighted: weight recent more heavily
n = len(lbl)
tw_weights = np.array([np.exp(-i/200.0) for i in range(n-1, -1, -1)])[:n]
for s in core:
    ics_list = sensor_ics.get(s, [])
    if not ics_list:
        continue
    tw_ics = []
    for col, ic_val in ics_list:
        # Recompute with time weighting
        vals = feat_numeric[col].dropna()
        idx = vals.index
        lbl_aligned = lbl.reindex(idx).dropna()
        common = vals.index.intersection(lbl_aligned.index)
        if len(common) < 100:
            continue
        v = vals.loc[common].values
        l = lbl_aligned.loc[common].values
        # Time-weight position
        pos = np.array(common - common[0], dtype=float)
        w = np.exp(-pos/200.0)
        wm = np.mean(w)
        w = w / wm
        cov = np.cov(v, l, aweights=w)[0,1]
        std_v = np.sqrt(np.cov(v, aweights=w))
        std_l = np.sqrt(np.cov(l, aweights=w))
        if std_v > 0 and std_l > 0:
            tw_ic = cov / (std_v * std_l)
        else:
            tw_ic = ic_val  # fallback
        tw_ics.append(tw_ic)
    if tw_ics:
        mean_tw_ic = np.mean(tw_ics)
        status = 'PASS' if abs(mean_tw_ic) >= 0.05 else 'FAIL'
        print(f"  {s}: {mean_tw_ic:+.4f} ({status})")

conn.close()
