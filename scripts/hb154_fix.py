#!/usr/bin/env python
"""Heartbeat #154 — Fixed IC analysis with correct label names."""
import sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')
import os
os.chdir('/home/kazuha/Poly-Trader')

import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path('/home/kazuha/Poly-Trader')
DB_PATH = PROJECT_ROOT / 'poly_trader.db'

db = sqlite3.connect(str(DB_PATH))
features = pd.read_sql("SELECT * FROM features_normalized", db)
labels = pd.read_sql("SELECT * FROM labels", db)
db.close()

# Regime values check
print("=== Regime Label Values ===")
print(f"Features regime_label value_counts:\n{features['regime_label'].value_counts()}")
if 'regime_label' in labels.columns:
    print(f"Labels regime_label value_counts:\n{labels['regime_label'].value_counts()}")

# Use actual label columns
print(f"\nlabel_sell_win distribution: {labels['label_sell_win'].value_counts().to_dict()}")
print(f"label_up distribution: {labels['label_up'].value_counts().to_dict()}")
print(f"sell_win rate (computed as future_return_pct<0): {(labels['future_return_pct'] < 0).mean():.4f}")
print(f"label_sell_win rate: {labels['label_sell_win'].mean():.4f}")
print(f"label_up rate: {labels['label_up'].mean():.4f}")

# Merge for analysis
merged = pd.merge(features, labels, on=['timestamp', 'symbol'], how='inner')
print(f"\nMerged rows: {len(merged)}")

# Sensory mapping
sensory_map = {}
for sense in ['eye', 'ear', 'nose', 'tongue', 'body', 'pulse', 'aura', 'mind']:
    col = f'feat_{sense}'
    if col in merged.columns:
        sensory_map[sense.capitalize()] = col
    else:
        sensory_map[sense.capitalize()] = None

# --- Global IC against label_sell_win ---
print("\n=== Global IC (full, against label_sell_win) ===")
global_ics = {}
for sense, col in sensory_map.items():
    if col is None:
        continue
    ic = merged[col].corr(merged['label_sell_win'])
    std = merged[col].std()
    status = "✅" if abs(ic) >= 0.05 else "❌"
    global_ics[sense] = (ic, std)
    print(f"  {sense}: IC={ic:+.4f} {status}  std={std:.4f}")

# Note flip: #153 had negative ICs (against label_up), now positive (against label_sell_win)
# IC magnitude should be the same, just sign flips

# --- Regime-Aware IC ---
print(f"\n=== Regime-Aware IC (against label_sell_win) ===")
regime_cols_present = [c for c in ['regime_label', 'regime'] if c in features.columns]
regime_col = regime_cols_present[0] if regime_cols_present else None

for regime in ['Bear', 'Bull', 'Chop', 'Neutral']:
    mask = merged[regime_col] == regime
    n = mask.sum()
    print(f"\n  {regime} (n={n}):")
    if n < 50:
        print(f"    Too few")
        continue
    pass_count = 0
    for sense, col in sensory_map.items():
        if col is None:
            continue
        sub = merged[mask]
        ic = sub[col].corr(sub['label_sell_win'])
        if abs(ic) >= 0.05:
            pass_count += 1
        status = "✅" if abs(ic) >= 0.05 else "❌"
        print(f"    {sense}: IC={ic:+.4f} {status}")
    print(f"  >> {pass_count}/8 passed")
