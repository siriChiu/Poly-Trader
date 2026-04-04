#!/usr/bin/env python
"""Heartbeat Step 2: Full Sensory IC Analysis"""
import sqlite3
import numpy as np
import pandas as pd
import json
import sys

DB_PATH = "/home/kazuha/Poly-Trader/poly_trader.db"

if not __name__ == "__main__":
    raise RuntimeError("Run this script directly")

conn = sqlite3.connect(DB_PATH)

# Load data
raw_df = pd.read_sql_query("SELECT * FROM raw_market_data ORDER BY timestamp", conn)
feat_df = pd.read_sql_query("SELECT * FROM features_normalized ORDER BY timestamp", conn)
label_df = pd.read_sql_query("SELECT * FROM labels ORDER BY timestamp", conn)
conn.close()

print(f"Raw: {len(raw_df)}, Features: {len(feat_df)}, Labels: {len(label_df)}")
print()

# Latest market data
latest = raw_df.iloc[-1]
cols_raw = raw_df.columns.tolist()
btc_price = None
for c in cols_raw:
    if 'price' in c.lower() and 'btc' in c.lower():
        btc_price = latest[c]
        break
    if 'price' in c.lower():
        btc_price = latest[c]

fng = None
for c in cols_raw:
    if 'fng' in c.lower() or 'fear' in c.lower():
        fng = latest[c]
        break

deriv_data = {}
for c in cols_raw:
    cl = c.lower()
    if any(x in cl for x in ['lsr', 'gsr', 'taker', 'open_interest', 'funding', 'oi']):
        deriv_data[c] = latest[c] if pd.notnull(latest[c]) else 'NULL'

print(f"BTC Price: ${btc_price}")
print(f"FNG: {fng}")
print(f"Derivatives: {deriv_data}")
print()

# Feature columns (exclude metadata)
meta_cols = {'id', 'timestamp', 'created_at', 'updated_at'}
feature_cols = [c for c in feat_df.columns if c.lower() not in meta_cols]
feat_data = feat_df[feature_cols].select_dtypes(include=[np.number])

# Label: use sell_win
label_cols = label_df.columns.tolist()
target_col = None
for c in label_cols:
    cl = c.lower()
    if 'sell_win' in cl:
        target_col = c
        break
if not target_col:
    for c in label_cols:
        if c.lower() not in meta_cols and label_df[c].dtype in ['float64', 'int64']:
            target_col = c
            break

print(f"Target column: {target_col}")
label_series = label_df[target_col].astype(float)

# Global IC
def compute_ic_for_column(col_name):
    vals = feat_data[col_name].dropna()
    if len(vals) < 100:
        return None
    idx = vals.index
    lbl = label_series.reindex(idx).dropna()
    common = vals.index.intersection(lbl.index)
    if len(common) < 100:
        return None
    ic = vals.loc[common].corr(lbl.loc[common])
    return ic if not np.isnan(ic) else None

# Map features to sensors
def get_sensor(col_name):
    cl = col_name.lower()
    sensor_map = [
        ('eye', 'Eye'), ('ear', 'Ear'), ('nose', 'Nose'), ('tongue', 'Tongue'),
        ('body', 'Body'), ('pulse', 'Pulse'), ('aura', 'Aura'), ('mind', 'Mind'),
        ('vix', 'VIX'), ('dxy', 'DXY')
    ]
    for key, sensor in sensor_map:
        if key in cl:
            return sensor
    return 'Other'

# Compute IC for all features
print("=== Global IC (against sell_win) ===\n")
sensor_features = {}
sensor_ics = {}

for col in feat_data.columns:
    sensor = get_sensor(col)
    ic = compute_ic_for_column(col)
    if ic is None:
        continue
    
    if sensor not in sensor_features:
        sensor_features[sensor] = []
    sensor_features[sensor].append((col, ic))
    
    if sensor not in sensor_ics:
        sensor_ics[sensor] = []
    sensor_ics[sensor].append(ic)

core_sensors = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']
print(f"{'Sensor':<10} {'AVG IC':>8} {'N':>4} {'Status'} {'Features'}")
print("-" * 80)

pass_count = 0
for sensor in core_sensors:
    ics = sensor_ics.get(sensor, [])
    if not ics:
        print(f"{sensor:<10} {'N/A':>8} {'0':>4} ❌ NO DATA")
        continue
    avg_ic = np.mean(ics)
    med_ic = np.median(ics)
    abs_ic = abs(avg_ic)
    status = '✅ PASS' if abs_ic >= 0.05 else ('❌ 近線' if abs_ic >= 0.04 else '❌')
    if abs_ic >= 0.05:
        pass_count += 1
    n = len(ics)
    print(f"{sensor:<10} {avg_ic:+.4f}  {n:4d}  {status}")
    for fname, fic in sorted(sensor_features[sensor], key=lambda x: abs(x[1]), reverse=True)[:3]:
        print(f"         {fname}: {fic:+.4f}")
    if n > 3:
        print(f"         ... and {n-3} more")

print(f"\n✅ 全域達標: {pass_count}/8")

# Feature quality
print("\n=== Feature Quality Check ===\n")
for sensor in core_sensors:
    for col, ic in sensor_features.get(sensor, [])[:3]:
        vals = feat_data[col]
        std = vals.std() if len(vals) > 1 else 0
        uniq = vals.nunique()
        flag = ''
        if std < 0.001 and uniq < 10:
            flag = ' ⚠️ QUASI-DISCRETE (std≈0, unique<10)'
        print(f"  {col}: mean={vals.mean():.4f}, std={std:.6f}, unique={uniq}, IC={ic:+.4f}{flag}")

# Sell win rates
print("\n=== Sell Win Rates ===\n")
valid_labels = label_series.dropna()
global_rate = (valid_labels == 1).mean() if len(valid_labels) > 0 else 0
print(f"Global sell_win rate: {global_rate:.3f}")
recent_500 = valid_labels.iloc[-500:]
recent_100 = valid_labels.iloc[-100:]
print(f"Recent (last 500): {(recent_500 == 1).mean():.3f} (n={len(recent_500)})")
print(f"Recent (last 100): {(recent_100 == 1).mean():.3f} (n={len(recent_100)})")

# Regime analysis
print("\n=== Regime Analysis ===\n")
if 'regime' in feat_df.columns:
    regime_vals = pd.to_numeric(feat_df['regime'], errors='coerce').dropna()
    sell_win = label_series.dropna()
    regime_clean = pd.Series(regime_vals)
    
    # Match indices as much as possible
    regime_series = feat_df['regime']
    combined = pd.DataFrame({
        'sell_win': label_series,
        'regime': regime_series
    }).dropna()
    
    regime_ics = {}
    for regime_name in sorted(combined['regime'].unique()):
        mask = combined['regime'] == regime_name
        subset = combined[mask]
        
        # Check IC per sensor for this regime
        regime_sensors = {}
        for sensor in core_sensors:
            sensor_cols = [c for c in feat_data.columns if get_sensor(c) == sensor]
            ics = []
            for col in sensor_cols:
                vals = feat_data[col].dropna()
                idx = vals.index
                lbl = subset['sell_win'].reindex(idx).dropna()
                common = vals.index.intersection(lbl.index)
                if len(common) < 50:
                    continue
                ic = vals.loc[common].corr(lbl.loc[common])
                if not np.isnan(ic):
                    ics.append(ic)
            if ics:
                regime_sensors[sensor] = np.mean(ics)
        
        reg_rate = (subset['sell_win'] == 1).mean()
        print(f"Regime: {regime_name}")
        print(f"  sell_win rate: {reg_rate:.3f} (n={len(subset)})")
        print(f"  Sensor ICs:")
        reg_pass = 0
        for sensor in core_sensors:
            ic_val = regime_sensors.get(sensor, 0)
            abs_ic = abs(ic_val)
            status = '✅' if abs_ic >= 0.05 else '❌'
            if abs_ic >= 0.05:
                reg_pass += 1
            print(f"    {sensor}: {ic_val:+.4f} {status}")
        print(f"  達標: {reg_pass}/8\n")
        
        regime_ics[regime_name] = regime_sensors
    else:
        print("No regime data found\n")

# Sell win rate agreement
label_up_col = None
for c in label_cols:
    if 'label_up' in c.lower():
        label_up_col = c
        break

if label_up_col and 'sell_win' in str(target_col).lower():
    sell_win_series = label_df.get(target_col, pd.Series())
    label_up_series = label_df.get(label_up_col, pd.Series())
    if len(sell_win_series) > 0 and len(label_up_series) > 0:
        common = sell_win_series.dropna().index.intersection(label_up_series.dropna().index)
        if len(common) > 100:
            agreement = (sell_win_series.loc[common] == label_up_series.loc[common]).mean()
            print(f"\nsell_win vs label_up agreement: {agreement:.3f}")

print("\n=== Key Findings ===")
print(f"- 全域達標: {pass_count}/8")
print(f"- 全域 sell_win rate: {global_rate:.3f}")
print(f"- 近期 sell_win (500): {(recent_500 == 1).mean():.3f}")
print(f"- 近期 sell_win (100): {(recent_100 == 1).mean():.3f}")
print(f"- BTC: ${btc_price}")
