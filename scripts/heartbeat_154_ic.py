#!/usr/bin/env python
"""Heartbeat #154 — Full IC analysis for all senses (SQLite-based)."""
import sqlite3
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

import numpy as np

try:
    import pandas as pd
except ImportError:
    print("pandas not found, using sqlite3 only")
    pd = None

PROJECT_ROOT = Path('/home/kazuha/Poly-Trader')
DB_PATH = PROJECT_ROOT / 'poly_trader.db'

def load_data_sql():
    """Load data directly from SQLite."""
    db = sqlite3.connect(str(DB_PATH))
    
    # Raw data count
    raw_count = db.execute("SELECT COUNT(*) FROM raw_market_data").fetchone()[0]
    feat_count = db.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
    label_count = db.execute("SELECT COUNT(*) FROM labels WHERE future_return_pct IS NOT NULL").fetchone()[0]
    
    # Get column names
    features_cols = [row[1] for row in db.execute("PRAGMA table_info(features_normalized)").fetchall()]
    labels_cols = [row[1] for row in db.execute("PRAGMA table_info(labels)").fetchall()]
    
    print(f"Raw: {raw_count} | Features: {feat_count} | Labels: {label_count}")
    print(f"Features cols ({len(features_cols)}): {features_cols[:30]}{'...' if len(features_cols) > 30 else ''}")
    print(f"Labels cols ({len(labels_cols)}): {labels_cols}")
    
    # Load full data for IC analysis
    if pd is not None:
        features = pd.read_sql("SELECT * FROM features_normalized", db)
        labels = pd.read_sql("SELECT * FROM labels", db)
        
        # Ensure sell_win exists
        if 'sell_win' not in labels.columns:
            print("WARNING: sell_win not in labels, computing from future_return_pct")
            labels['sell_win'] = (labels['future_return_pct'] < 0).astype(int)
        
        sell_win_rate = labels['sell_win'].mean()
        print(f"sell_win rate: {sell_win_rate:.4f}")
        
        db.close()
        return features, labels
    else:
        db.close()
        return None, None

# Sensory feature mapping - build dynamically
def build_sensory_map(features_df):
    sensory_map = {}
    for c in features_df.columns:
        lower_c = c.lower()
        for sense in ['eye', 'ear', 'nose', 'tongue', 'body', 'pulse', 'aura', 'mind']:
            if sense in lower_c:
                sensory_map.setdefault(sense.capitalize(), []).append(c)
                break
    # Ensure all senses present
    for sense in ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']:
        sensory_map.setdefault(sense, [])
    return sensory_map

def calc_ic(series, label_series):
    """Calculate Pearson IC."""
    valid_mask = series.notna() & label_series.notna()
    if valid_mask.sum() < 30:
        return 0.0
    return series[valid_mask].corr(label_series[valid_mask], method='pearson')

# Main
features, labels = load_data_sql()
if features is None:
    print("ERROR: No data")
    sys.exit(1)

sensory_map = build_sensory_map(features)
for sense in ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']:
    print(f"{sense}: {sensory_map[sense]}")

# --- Global IC ---
label_col = 'sell_win'
print("\n=== Global IC (full dataset, against sell_win) ===")
global_ics = {}
for sense in ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']:
    cols = sensory_map[sense]
    if not cols:
        global_ics[sense] = (0.0, 0.0)
        print(f"{sense}: N/A (no features)")
        continue
    sense_data = features[cols].mean(axis=1)
    ic = sense_data.corr(labels[label_col], method='pearson')
    std = sense_data.std()
    rng = sense_data.max() - sense_data.min()
    nunique = sense_data.nunique()
    global_ics[sense] = (ic, std)
    status = "✅" if abs(ic) >= 0.05 else "❌"
    print(f"  {sense}: IC={ic:+.4f} {status}  std={std:.4f}  range={rng:.4f}  unique={nunique}")

# --- Regime-Aware IC ---
regime_col = None
for c in ['regime', 'market_regime', 'regime_label']:
    if c in features.columns:
        regime_col = c
        break

if regime_col:
    print(f"\n=== Regime-Aware IC (against sell_win, regime='{regime_col}') ===")
    for regime in ['Bear', 'Bull', 'Chop', 'Neutral']:
        mask = features[regime_col] == regime
        regime_count = mask.sum()
        if regime_count < 50:
            print(f"\n  {regime}: too few ({regime_count}), skipping")
            continue
        print(f"\n  {regime} (n={regime_count}):")
        pass_count = 0
        for sense in ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']:
            cols = sensory_map[sense]
            if not cols:
                continue
            s_data = features.loc[mask, cols].mean(axis=1)
            l_data = labels.loc[mask, label_col]
            ic = calc_ic(s_data, l_data)
            if abs(ic) >= 0.05:
                pass_count += 1
            status = "✅" if abs(ic) >= 0.05 else "❌"
            print(f"    {sense}: IC={ic:+.4f} {status}")
        print(f"  >> {pass_count}/8 passed (IC >= 0.05)")
else:
    print("\nWARNING: No regime column found")

# --- Dynamic Window IC ---
print("\n=== Dynamic Window IC (tail, against sell_win) ===")
for window in [200, 500, 1000]:
    print(f"\n  N={window} (tail):")
    tail = features.tail(window)
    tail_labels = labels.tail(window)
    pass_count = 0
    passed_senses = []
    for sense in ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']:
        cols = sensory_map[sense]
        if not cols:
            continue
        s_data = tail[cols].mean(axis=1)
        l_data = tail_labels[label_col]
        ic = calc_ic(s_data, l_data)
        if abs(ic) >= 0.05:
            pass_count += 1
            passed_senses.append(f"{sense}({ic:+.3f})")
        status = "✅" if abs(ic) >= 0.05 else "❌"
    print(f"    {pass_count}/8 passed: {', '.join(passed_senses) if passed_senses else 'ALL FAIL'}")

# --- Market data ---
print(f"\n=== Market Data ===")
db = sqlite3.connect(str(DB_PATH))
try:
    row = db.execute("SELECT close, fng_value, long_short_ratio FROM raw_market_data ORDER BY rowid DESC LIMIT 1").fetchone()
    if row:
        print(f"BTC latest close: ${row[0]:,.0f}")
        print(f"FNG: {row[1]}")
        print(f"LSR: {row[2]:.2f}" if row[2] else "LSR: N/A")
except:
    print("Could not fetch latest market data")
db.close()

# --- Model check ---
print(f"\n=== Model Check ===")
try:
    sys.path.insert(0, str(PROJECT_ROOT))
    from model.predictor import train_predictor_result, load_predictor
    # Just check if files exist
    print("Model module imports OK")
except Exception as e:
    print(f"Model import: {e}")
