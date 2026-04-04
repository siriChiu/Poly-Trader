#!/usr/bin/env python
"""Heartbeat Step 2: IC Analysis"""
import json
import os
import sys
import warnings
warnings.filterwarnings('ignore')

try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("ERROR: numpy/pandas not installed", file=sys.stderr)
    sys.exit(1)

HERMES_HOME = os.path.expanduser("~/.hermes")
DB_PATH = os.path.join(HERMES_HOME, "poly_trader", "data", "market.db")

if not os.path.exists(DB_PATH):
    print(f"ERROR: DB not found at {DB_PATH}")
    sys.exit(1)

def load_data():
    pd_db = __import__('pandas').read_sql_query
    
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    
    try:
        raw_df = pd.read_sql_query("SELECT * FROM market_data ORDER BY timestamp", conn)
    except Exception as e:
        print(f"ERROR reading market_data: {e}")
        raw_df = pd.DataFrame()
    
    try:
        feat_df = pd.read_sql_query("SELECT * FROM feature_data ORDER BY timestamp", conn)
    except Exception as e:
        print(f"ERROR reading feature_data: {e}")
        feat_df = pd.DataFrame()
    
    try:
        label_df = pd.read_sql_query("SELECT * FROM label_data ORDER BY timestamp", conn)
    except Exception as e:
        print(f"ERROR reading label_data: {e}")
        label_df = pd.DataFrame()
    
    conn.close()
    return raw_df, feat_df, label_df

def compute_ic(features_df, label_series):
    """Compute IC (Information Coefficient) for each feature."""
    ics = {}
    for col in features_df.columns:
        vals = features_df[col].dropna()
        if len(vals) < 100:
            continue
        idx = vals.index
        lbl = label_series.reindex(idx).dropna()
        common = vals.index.intersection(lbl.index)
        if len(common) < 100:
            continue
        ic = vals.loc[common].corr(lbl.loc[common])
        ics[col] = ic
    return ics

def sensor_from_feature(name):
    """Map feature name to sensor (Eye, Ear, Nose, Tongue, Body, Pulse, Aura, Mind)."""
    name_lower = name.lower()
    if 'eye' in name_lower:
        return 'Eye'
    elif 'ear' in name_lower:
        return 'Ear'
    elif 'nose' in name_lower:
        return 'Nose'
    elif 'tongue' in name_lower:
        return 'Tongue'
    elif 'body' in name_lower:
        return 'Body'
    elif 'pulse' in name_lower:
        return 'Pulse'
    elif 'aura' in name_lower:
        return 'Aura'
    elif 'mind' in name_lower or 'regime' in name_lower:
        return 'Mind'
    elif 'vix' in name_lower:
        return 'VIX'
    elif 'dxy' in name_lower:
        return 'DXY'
    return 'Other'

def main():
    print("=== Step 2: Sensory IC Analysis ===\n")
    
    raw_df, feat_df, label_df = load_data()
    
    print(f"Raw data: {len(raw_df)} rows")
    print(f"Features: {len(feat_df)} rows")
    print(f"Labels: {len(label_df)} rows")
    print()
    
    if len(raw_df) == 0 or len(feat_df) == 0 or len(label_df) == 0:
        print("ERROR: Empty dataframes")
        return
    
    # Get latest BTC price and market data
    latest_raw = raw_df.iloc[-1]
    btc_price = latest_raw.get('btc_price', 'N/A')
    fng = latest_raw.get('fng', 'N/A')
    print(f"Latest BTC: ${btc_price}")
    print(f"Latest FNG: {fng}")
    
    # Derivatives data
    lsr = latest_raw.get('lsr', 'N/A')
    gsr = latest_raw.get('gsr', 'N/A')
    taker = latest_raw.get('taker_buy_ratio', latest_raw.get('taker', 'N/A'))
    oi = latest_raw.get('open_interest', latest_raw.get('oi', 'N/A'))
    fr = latest_raw.get('funding_rate', 'N/A')
    print(f"LSR: {lsr} | GSR: {gsr} | Taker: {taker} | OI: {oi} | FR: {fr}")
    print()
    
    # Use sell_win as the target
    if 'sell_win' not in label_df.columns:
        # Fallback: use label_up or first numeric column
        print("WARNING: sell_win not in label_data, using first numeric column")
        numeric_cols = label_df.select_dtypes(include=[np.number]).columns
        target_col = numeric_cols[0] if len(numeric_cols) > 0 else None
    else:
        target_col = 'sell_win'
    
    if target_col is None:
        print("ERROR: No target column found")
        return
    
    label_series = label_df[target_col].astype(float)
    
    # Feature columns (exclude timestamp, id, etc.)
    feature_cols = [c for c in feat_df.columns if c not in ('id', 'timestamp', 'created_at', 'updated_at')]
    feature_data = feat_df[feature_cols].select_dtypes(include=[np.number])
    
    # Global IC
    print("=== Global IC (h=4, against sell_win) ===\n")
    
    # Group by sensor
    sensor_features = {}
    for col in feature_data.columns:
        sensor = sensor_from_feature(col)
        if sensor not in sensor_features:
            sensor_features[sensor] = []
        sensor_features[sensor].append(col)
    
    sensor_ics = {}
    for sensor, cols in sensor_features.items():
        ics = []
        for col in cols:
            vals = feature_data[col].dropna()
            if len(vals) < 100:
                continue
            idx = vals.index
            lbl = label_series.reindex(idx).dropna()
            common = vals.index.intersection(lbl.index)
            if len(common) < 100:
                continue
            ic = vals.loc[common].corr(lbl.loc[common])
            if not np.isnan(ic):
                ics.append(ic)
        if ics:
            sensor_ics[sensor] = np.mean(ics) / len(ics) * len(ics)  # Actually compute mean properly
            sensor_ics[sensor] = np.mean(ics)
    
    core_sensors = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']
    print(f"{'Sensor':<10} {'IC':>8} {'Status'}")
    print(f"{'-'*30}")
    pass_count = 0
    for sensor in core_sensors:
        ic_val = sensor_ics.get(sensor, 0)
        abs_ic = abs(ic_val)
        status = '✅ PASS' if abs_ic >= 0.05 else ('❌ 近線' if abs_ic >= 0.04 else '❌')
        if abs_ic >= 0.05:
            pass_count += 1
        print(f"{sensor:<10} {ic_val:+.4f}   {status}")
    
    print(f"\n全域達標: {pass_count}/8\n")
    
    # Feature quality check
    print("=== Feature Quality ===\n")
    for sensor in core_sensors:
        cols = sensor_features.get(sensor, [])
        for col in cols[:3]:  # Check first 3 per sensor
            vals = feature_data[col]
            std = vals.std()
            uniq = vals.nunique()
            flag = ''
            if std < 0.001 and uniq < 10:
                flag = ' ⚠️ QUASI-DISCRETE'
            print(f"  {col}: std={std:.6f}, unique={uniq}{flag}")
    
    # Sell win rates
    print("\n=== Sell Win Rates ===\n")
    valid_labels = label_series.dropna()
    overall_rate = (valid_labels == 1).mean()
    print(f"Global sell_win rate: {overall_rate:.3f}")
    
    # Recent rates
    recent_500 = valid_labels.iloc[-500:]
    recent_100 = valid_labels.iloc[-100:]
    print(f"Recent (last 500): {(recent_500 == 1).mean():.3f}")
    print(f"Recent (last 100): {(recent_100 == 1).mean():.3f}")
    
    # Regime analysis if available
    if 'regime' in feat_df.columns:
        print("\n=== Regime Analysis ===\n")
        regime_vals = feat_df['regime'].dropna()
        combined = pd.DataFrame({
            'sell_win': label_series,
            'regime': regime_vals
        }).dropna()
        
        for regime_name in combined['regime'].unique():
            mask = combined['regime'] == regime_name
            subset = combined[mask]
            rate = (subset['sell_win'] == 1).mean()
            print(f"  {regime_name}: sell_win={rate:.3f} (n={len(subset)})")
    
    return sensor_ics, btc_price, len(raw_df), len(feat_df), len(label_df)

if __name__ == '__main__':
    result = main()
    if result:
        sensor_ics = result[0]
        print(f"\n=== IC Summary ===")
        for sensor, ic in sorted(sensor_ics.items()):
            print(f"  {sensor}: {ic:+.4f}")
