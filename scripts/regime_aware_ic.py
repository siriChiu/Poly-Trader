#!/usr/bin/env python3
"""
Regime-aware IC analysis for Poly-Trader.

Core insight (#H122): IC decays as N increases → features are regime-dependent.
This script:
1. Classifies data into regimes (bull/bear/chop)
2. Computes IC per regime
3. Identifies regime-specific effective features
4. Produces IC-by-regime report saved to data/ic_regime_analysis.json

Usage:
    PYTHONPATH=/home/kazuha/Poly-Trader venv/bin/python scripts/regime_aware_ic.py
"""
import json, sys, os
from datetime import datetime

sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

from sqlalchemy import create_engine
import numpy as np
import pandas as pd

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
engine = create_engine(f'sqlite:///{DB_PATH}')

# Load data
features_df = pd.read_sql('SELECT * FROM features_normalized', engine)
labels_df = pd.read_sql('SELECT timestamp, label_up, future_return_pct, horizon_minutes FROM labels', engine)

# Merge on timestamp (floor to seconds)
features_df['ts_key'] = pd.to_datetime(features_df['timestamp'], format='mixed').dt.floor('s')
labels_df['ts_key'] = pd.to_datetime(labels_df['timestamp'], format='mixed').dt.floor('s')
data = features_df.merge(labels_df, on='ts_key', suffixes=('', '_label')).sort_values('timestamp')

print(f"Total merged records: {len(data)}")

# === Regime Classification ===
# Use price momentum (Mind = long-term price deviation) to classify
# We can also use the future_return_pct from labels as a proxy for prior regime

# Method 1: Rolling return-based regime (using label future returns as proxy)
# Positive return periods = bull, negative = bear, near-zero = chop

# Use Mind (price vs SMA deviation) as primary regime indicator
# Positive mind = price above SMA (bull), negative = below SMA (bear)
data['regime'] = 'chop'
if 'feat_mind' in data.columns:
    mind_vals = data['feat_mind'].fillna(0)
    p33 = mind_vals.quantile(0.33)
    p67 = mind_vals.quantile(0.67)
    # Bear: bottom 33%, Bull: top 33%, Chop: middle 34%
    mask_bear = mind_vals < p33
    mask_bull = mind_vals > p67
    data.loc[mask_bear.values, 'regime'] = 'bear'
    data.loc[mask_bull.values, 'regime'] = 'bull'

print(f"\n=== Regime Distribution ===")
print(data['regime'].value_counts().to_string())

# Also add volatility regime
if 'feat_eye' in data.columns:
    window = min(500, len(data))
    eye_rolling_std = data['feat_eye'].rolling(window).std().fillna(0)
    vol_threshold = float(eye_rolling_std.quantile(0.75))
    data['vol_regime'] = np.where(eye_rolling_std.values > vol_threshold, 'high_vol', 'low_vol')
    print(f"\n=== Volatility Regime Distribution ===")
    print(data['vol_regime'].value_counts().to_string())

# === Sensory Features ===
sensory_features = {
    'feat_eye': 'Eye', 'feat_ear': 'Ear', 'feat_nose': 'Nose',
    'feat_tongue': 'Tongue', 'feat_body': 'Body', 'feat_pulse': 'Pulse',
    'feat_aura': 'Aura', 'feat_mind': 'Mind'
}
label_col = 'label_up'

# === IC by Regime ===
print(f"\n{'='*60}")
print(f"  REGIME-AWARE IC ANALYSIS (h=4h)")
print(f"{'='*60}")

regime_ics = {}
regime_summary = {}

for regime_name, regime_data in data.groupby('regime'):
    regime_data = regime_data.dropna(subset=label_col)
    n = len(regime_data)
    print(f"\n--- {regime_name.upper()} regime (n={n}) ---")
    regime_ics[regime_name] = {}
    
    for feat_col, sense_name in sensory_features.items():
        if feat_col not in regime_data.columns:
            continue
        valid = regime_data[[feat_col, label_col]].dropna()
        if len(valid) < 30:
            print(f"  {sense_name:8s}: SKIP (n={len(valid)})")
            continue
        ic = valid[feat_col].corr(valid[label_col])
        p_positive = (ic > 0.0)  # simple binary: is IC positive?
        regime_ics[regime_name][sense_name] = round(float(ic), 4)
        status = "✅" if abs(ic) >= 0.05 else "❌"
        print(f"  {sense_name:8s}: IC={ic:+.4f} {status}")
    
    # Overall stats for this regime
    label_mean = regime_data[label_col].mean()
    label_pos_pct = regime_data[label_col].sum() / n * 100
    regime_summary[regime_name] = {
        'n': n,
        'label_positive_pct': round(label_pos_pct, 1),
    }

# === Overall IC for comparison ===
print(f"\n{'='*60}")
print(f"  OVERALL IC (for comparison)")
print(f"{'='*60}")
overall_ics = {}
for feat_col, sense_name in sensory_features.items():
    valid = data[[feat_col, label_col]].dropna()
    if len(valid) < 30:
        continue
    ic = valid[feat_col].corr(valid[label_col])
    overall_ics[sense_name] = round(float(ic), 4)
    status = "✅" if abs(ic) >= 0.05 else "❌"
    print(f"  {sense_name:8s}: IC={ic:+.4f} {status}")

# === Identify regime-effective features ===
print(f"\n{'='*60}")
print(f"  REGIME-SPECIFIC EFFECTIVE FEATURES (|IC| >= 0.05)")
print(f"{'='*60}")
regime_effective = {}
for regime_name, ics in regime_ics.items():
    effective = {k: v for k, v in ics.items() if abs(v) >= 0.05}
    regime_effective[regime_name] = effective
    if effective:
        print(f"  {regime_name}: {effective}")
    else:
        print(f"  {regime_name}: None above threshold")

# === Recent N=500, N=1000, N=2000, N=5000 IC (replicate original analysis) ===
print(f"\n{'='*60}")
print(f"  IC DECAY BY SAMPLE SIZE (N)")
print(f"{'='*60}")
decay_analysis = {}
for n in [500, 1000, 2000, 3000, 5000]:
    recent = data.tail(n)
    ics = {}
    for feat_col, sense_name in sensory_features.items():
        valid = recent[[feat_col, label_col]].dropna()
        if len(valid) < 10:
            continue
        ic = valid[feat_col].corr(valid[label_col])
        ics[sense_name] = round(float(ic), 4)
    passing = sum(1 for v in ics.values() if abs(v) >= 0.05)
    decay_analysis[f"N={n}"] = ics
    print(f"  N={n:5d}: {passing}/8 above threshold")
    for name, ic in ics.items():
        marker = " ✅" if abs(ic) >= 0.05 else ""
        print(f"    {name:8s}: {ic:+.4f}{marker}")

# Save results
result = {
    'timestamp': datetime.now().isoformat(),
    'total_records': len(data),
    'overall_ics': overall_ics,
    'regime_ics': regime_ics,
    'regime_summary': regime_summary,
    'regime_effective': regime_effective,
    'decay_analysis': decay_analysis,
}

output_path = '/home/kazuha/Poly-Trader/data/ic_regime_analysis.json'
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)
print(f"\nResults saved to {output_path}")
