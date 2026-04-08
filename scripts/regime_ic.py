#!/usr/bin/env python
"""Regime IC & VIX/DXY analysis - fixed"""
import sqlite3
import numpy as np
import pandas as pd

DB_PATH = "/home/kazuha/Poly-Trader/poly_trader.db"
conn = sqlite3.connect(DB_PATH)

feat_df = pd.read_sql_query("SELECT * FROM features_normalized ORDER BY timestamp", conn)
label_df = pd.read_sql_query("SELECT * FROM labels ORDER BY timestamp", conn)
raw_df = pd.read_sql_query("SELECT * FROM raw_market_data ORDER BY timestamp", conn)
conn.close()

# Ensure both DFs use aligned indices
feat_df = feat_df.sort_values('timestamp').reset_index(drop=True)
# label_df may have different length - align by position
label_spot_long_win = pd.to_numeric(label_df['label_spot_long_win'], errors='coerce')

# Regime IC analysis
regime_vals = feat_df['regime_label']
core_sensors = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']
sensor_col_map = {'Eye': 'feat_eye', 'Ear': 'feat_ear', 'Nose': 'feat_nose', 
                  'Tongue': 'feat_tongue', 'Body': 'feat_body', 'Pulse': 'feat_pulse',
                  'Aura': 'feat_aura', 'Mind': 'feat_mind'}

regimes = sorted(regime_vals.unique())
regime_table = {}

for reg in regimes:
    reg_mask = regime_vals == reg
    reg_df = feat_df[reg_mask].copy()
    reg_indices = reg_df.index.tolist()
    
    # Get labels for these indices (aligned by position)
    n_feat = len(feat_df)
    n_labels = len(label_spot_long_win)
    
    print(f"\n--- Regime: {reg} (n={len(reg_df)}, feat_indices: {reg_indices[:3]}...{reg_indices[-3:]}) ---")
    
    reg_pass = 0
    sell_wins = []
    for sensor in core_sensors:
        col = sensor_col_map[sensor]
        if col not in feat_df.columns:
            continue
        
        sensor_vals = feat_df.loc[reg_indices, col]
        
        # Align with labels by index position
        valid_indices = []
        for i in reg_indices:
            if i < n_labels and not pd.isna(label_spot_long_win.iloc[i]) and not pd.isna(sensor_vals[i]):
                valid_indices.append(i)
        
        if len(valid_indices) < 50:
            print(f"  {sensor}: N/A (valid n={len(valid_indices)})")
            continue
        
        s_vals = feat_df.loc[valid_indices, col].values.astype(float)
        l_vals = label_spot_long_win.iloc[valid_indices].values.astype(float)
        
        ic = np.corrcoef(s_vals, l_vals)[0, 1]
        abs_ic = abs(ic) if not np.isnan(ic) else 0
        status = '✅' if abs_ic >= 0.05 else '❌'
        if abs_ic >= 0.05:
            reg_pass += 1
        print(f"  {sensor}: {ic:+.4f} {status}")
    
    # Sell win rate in this regime
    for i in reg_indices:
        if i < n_labels and not pd.isna(label_spot_long_win.iloc[i]):
            sell_wins.append(label_spot_long_win.iloc[i])
    
    if sell_wins:
        sell_win_rate = np.mean(sell_wins)
        print(f"  Sell win rate: {sell_win_rate:.3f} (n={len(sell_wins)})")
    else:
        sell_win_rate = 0
        print(f"  Sell win rate: N/A")
    
    regime_table[reg] = {'pass': reg_pass, 'sell_win': sell_win_rate}

print("\n" + "="*60)

# VIX and DXY analysis
print("=== VIX IC ===\n")
for reg in regimes:
    reg_mask = regime_vals == reg
    reg_indices = feat_df[reg_mask].index.tolist()
    
    valid = []
    for i in reg_indices:
        if i < n_labels and not pd.isna(label_spot_long_win.iloc[i]) and not pd.isna(feat_df.loc[i, 'feat_vix']):
            valid.append(i)
    
    if len(valid) < 50:
        print(f"  VIX ({reg}): N/A (n={len(valid)})")
        continue
    
    vix_vals = feat_df.loc[valid, 'feat_vix'].values.astype(float)
    l_vals = label_spot_long_win.iloc[valid].values.astype(float)
    ic = np.corrcoef(vix_vals, l_vals)[0, 1]
    abs_ic = abs(ic) if not np.isnan(ic) else 0
    status = '✅' if abs_ic >= 0.05 else '❌'
    print(f"  VIX ({reg}): {ic:+.4f} {status}")

print("\n=== DXY IC ===\n")
for reg in regimes:
    reg_mask = regime_vals == reg
    reg_indices = feat_df[reg_mask].index.tolist()
    
    valid = []
    for i in reg_indices:
        if i < n_labels and not pd.isna(label_spot_long_win.iloc[i]) and not pd.isna(feat_df.loc[i, 'feat_dxy']):
            valid.append(i)
    
    if len(valid) < 50:
        print(f"  DXY ({reg}): N/A (n={len(valid)})")
        continue
    
    dxy_vals = feat_df.loc[valid, 'feat_dxy'].values.astype(float)
    l_vals = label_spot_long_win.iloc[valid].values.astype(float)
    ic = np.corrcoef(dxy_vals, l_vals)[0, 1]
    abs_ic = abs(ic) if not np.isnan(ic) else 0
    status = '✅' if abs_ic >= 0.05 else '❌'
    print(f"  DXY ({reg}): {ic:+.4f} {status}")

# Global IC
print("\n=== Global VIX/DXY IC ===\n")
vix_valid = []
dxy_valid = []
for i in range(min(n_feat, n_labels)):
    if not pd.isna(label_spot_long_win.iloc[i]):
        if not pd.isna(feat_df.loc[i, 'feat_vix']):
            vix_valid.append(i)
        if not pd.isna(feat_df.loc[i, 'feat_dxy']):
            dxy_valid.append(i)

if len(vix_valid) >= 50:
    vix_vals = feat_df.loc[vix_valid, 'feat_vix'].values.astype(float)
    l_vals = label_spot_long_win.iloc[vix_valid].values.astype(float)
    ic = np.corrcoef(vix_vals, l_vals)[0, 1]
    print(f"  VIX (Global): {ic:+.4f}")

if len(dxy_valid) >= 50:
    dxy_vals = feat_df.loc[dxy_valid, 'feat_dxy'].values.astype(float)
    l_vals = label_spot_long_win.iloc[dxy_valid].values.astype(float)
    ic = np.corrcoef(dxy_vals, l_vals)[0, 1]
    print(f"  DXY (Global): {ic:+.4f}")

# Summary table
print("\n=== Regime Summary ===")
print(f"{'Regime':<12} {'Pass':>8} {'Sell Win':>12}")
print("-" * 32)
for reg, data in sorted(regime_table.items()):
    print(f"{reg:<12} {data['pass']:>4}/8      {data['sell_win']:>10.3f}")
