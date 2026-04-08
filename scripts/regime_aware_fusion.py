#!/usr/bin/env python3
"""
Regime-aware feature fusion for Poly-Trader.

Creates ic_regime_weights.json: per-regime, per-sense IC weights.
These weights enable regime-aware ensemble predictions:
- Detect current regime
- Weight senses by their regime-specific IC
- Skip low-IC senses entirely

This directly addresses #H122: IC decay resolved by regime segmentation.

Usage:
    PYTHONPATH=/home/kazuha/Poly-Trader venv/bin/python scripts/regime_aware_fusion.py
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
labels_df = pd.read_sql('SELECT timestamp, label_up, label_spot_long_win FROM labels', engine)

features_df['ts_key'] = pd.to_datetime(features_df['timestamp'], format='mixed').dt.floor('s')
labels_df['ts_key'] = pd.to_datetime(labels_df['timestamp'], format='mixed').dt.floor('s')
data = features_df.merge(labels_df, on='ts_key', suffixes=('_feat', '_label'))

# Sort by the original timestamp (could come from either table)
if 'timestamp_feat' in data.columns:
    data = data.sort_values('timestamp_feat')
elif 'timestamp_label' in data.columns:
    data = data.sort_values('timestamp_label')
else:
    data = data.sort_index()

# === Regime classification (same as regime_aware_ic.py) ===
data['regime'] = 'chop'
if 'feat_mind' in data.columns:
    mind_vals = data['feat_mind'].fillna(0)
    p33 = mind_vals.quantile(0.33)
    p67 = mind_vals.quantile(0.67)
    mask_bear = mind_vals < p33
    mask_bull = mind_vals > p67
    data.loc[mask_bear.values, 'regime'] = 'bear'
    data.loc[mask_bull.values, 'regime'] = 'bull'

sensory_features = {
    'feat_eye': 'Eye', 'feat_ear': 'Ear', 'feat_nose': 'Nose',
    'feat_tongue': 'Tongue', 'feat_body': 'Body', 'feat_pulse': 'Pulse',
    'feat_aura': 'Aura', 'feat_mind': 'Mind'
}

# === Compute regime IC weights ===
regime_weights = {}
IC_THRESHOLD = 0.05

for regime_name, regime_data in data.groupby('regime'):
    regime_weights[regime_name] = {}
    label_col = 'label_up'
    regime_data = regime_data.dropna(subset=[label_col])
    
    ics = {}
    for feat_col, sense_name in sensory_features.items():
        if feat_col not in regime_data.columns:
            continue
        valid = regime_data[[feat_col, label_col]].dropna()
        if len(valid) < 30:
            continue
        ic = valid[feat_col].corr(valid[label_col])
        ics[sense_name] = ic
    
    # Normalize ICs to weights (absolute value, only if above threshold)
    total_abs_ic = sum(abs(v) for v in ics.values() if abs(v) >= IC_THRESHOLD)
    
    for sense_name, ic in ics.items():
        regime_weights[regime_name][sense_name] = {
            'ic': round(float(ic), 4),
            'weight': 0.0,
            'above_threshold': bool(abs(ic) >= IC_THRESHOLD),
        }
        if total_abs_ic > 0 and abs(ic) >= IC_THRESHOLD:
            regime_weights[regime_name][sense_name]['weight'] = round(abs(ic) / total_abs_ic, 4)

# === Also compute label balance per regime ===
label_balance = {}
for regime_name, regime_data in data.groupby('regime'):
    label_col = 'label_up'
    regime_data_clean = regime_data.dropna(subset=[label_col])
    pos = regime_data_clean[label_col].sum()
    neg = len(regime_data_clean) - pos
    label_balance[regime_name] = {
        'total': len(regime_data_clean),
        'positive': int(pos),
        'negative': int(neg),
        'pos_pct': round(pos / len(regime_data_clean) * 100, 1),
    }

# === Sell-win label balance ===
sellwin_balance = None
if 'label_spot_long_win' in data.columns:
    sw = data.dropna(subset=['label_spot_long_win'])
    sellwin_balance = {
        'total': len(sw),
        'wins': int(sw['label_spot_long_win'].sum()),
        'losses': int(len(sw) - sw['label_spot_long_win'].sum()),
        'win_rate': round(float(sw['label_spot_long_win'].sum() / len(sw) * 100), 1),
    }

result = {
    'timestamp': datetime.now().isoformat(),
    'ic_threshold': IC_THRESHOLD,
    'regime_weights': regime_weights,
    'label_balance': label_balance,
    'sell_win_balance': sellwin_balance,
    'regime_detection': {
        'method': 'feat_mind quantiles',
        'bear': f'feat_mind < {float(mind_vals.quantile(0.33)):.4f}',
        'chop': f'between p33 and p67',
        'bull': f'feat_mind > {float(mind_vals.quantile(0.67)):.4f}',
    },
}

output_path = '/home/kazuha/Poly-Trader/data/ic_regime_weights.json'
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)

print(f"Regime-aware IC weights saved to {output_path}")
print()
for regime, weights in regime_weights.items():
    above = [k for k, v in weights.items() if v['above_threshold']]
    print(f"{regime:6s}: {len(above)}/8 senses above threshold → {above if above else '(none)'}")
