#!/usr/bin/env python3
"""Heartbeat #157 - Full IC Analysis with ALL 22 features"""
import sqlite3, os, sys, json
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')
import numpy as np

db = sqlite3.connect('poly_trader.db')

# Get all feature columns
cols = db.execute('PRAGMA table_info(features_normalized)').fetchall()
all_feature_cols = [c[1] for c in cols if c[1].startswith('feat_') and c[1] not in ('feat_vix', 'feat_dxy')]
# Separate VIX/DXY as macro features
macro_cols = ['feat_vix', 'feat_dxy']

# Original 8 senses
orig_names = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']
orig_fields = ['feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind']

# New advanced features
adv_fields = [f for f in all_feature_cols if f not in orig_fields]
adv_names = [f.replace('feat_', '').title() for f in adv_fields]

# Build SELECT for all features
select_cols = 'timestamp, ' + ', '.join(all_feature_cols)
feat_rows = db.execute(f'SELECT {select_cols} FROM features_normalized ORDER BY timestamp').fetchall()

# Labels
labels_rows = db.execute('SELECT timestamp, label_sell_win FROM labels WHERE label_sell_win IS NOT NULL').fetchall()
label_map = {r[0]: r[1] for r in labels_rows}

# Build feature dict
timestamps = []
feat_data = {}
for f in all_feature_cols:
    feat_data[f] = []

for row in feat_rows:
    ts = row[0]
    timestamps.append(ts)
    for i, f in enumerate(all_feature_cols):
        try:
            feat_data[f].append(float(row[i+1]) if row[i+1] is not None else np.nan)
        except:
            feat_data[f].append(np.nan)

# Full dataset IC for ALL features
print('=== Full IC (all 22 features) ===')
ic_results = {}
for f in all_feature_cols:
    fv = np.array(feat_data[f])
    mf, ml = [], []
    for j, ts in enumerate(timestamps):
        if ts in label_map and not np.isnan(fv[j]):
            mf.append(fv[j])
            ml.append(label_map[ts])
    mf, ml = np.array(mf), np.array(ml)
    n = len(mf)
    std_val = np.std(mf)
    unique = len(np.unique(mf))
    if n < 100 or std_val < 1e-10:
        ic_val = 0
    else:
        c = np.corrcoef(mf, ml)
        ic_val = c[0,1] if np.isfinite(c[0,1]) else 0
    status = 'PASS' if abs(ic_val) >= 0.05 else 'FAIL'
    print(f'  {f:20s}: IC={ic_val:+.4f}  std={std_val:.4f}  n={n}  unique={unique}  [{status}]')
    ic_results[f] = {'ic': round(ic_val, 4), 'std': round(float(std_val), 4), 'n': n, 'unique': unique}

# Regime-aware IC with all features
print('\n=== Regime-Aware IC (regime_label column) ===')
try:
    all_feats_query = db.execute(f'SELECT timestamp, regime_label FROM features_normalized').fetchall()
    regime_map = {r[0]: r[1] for r in all_feats_query if r[1] is not None}
except:
    regime_map = {}

regime_results = {}
for regime in ['bear', 'bull', 'chop']:
    ts_set = set(ts for ts, r in regime_map.items() if r == regime)
    print(f'\n  {regime.upper()} ({len(ts_set)} samples):')
    passing = []
    for f in all_feature_cols:
        fv = np.array(feat_data[f])
        mf, ml = [], []
        for j, ts in enumerate(timestamps):
            if ts in ts_set and ts in label_map and not np.isnan(fv[j]):
                mf.append(fv[j])
                ml.append(label_map[ts])
        mf, ml = np.array(mf), np.array(ml)
        n = len(mf)
        if n < 50 or np.std(mf) < 1e-10:
            ic_val = 0
        else:
            c = np.corrcoef(mf, ml)
            ic_val = c[0,1] if np.isfinite(c[0,1]) else 0
        status = 'PASS' if abs(ic_val) >= 0.05 else 'FAIL'
        if abs(ic_val) >= 0.05:
            passing.append(f'{f}({ic_val:+.3f})')
        print(f'    {f:20s}: IC={ic_val:+.4f}  n={n}  [{status}]')
    regime_results[regime] = {'passing': len(passing), 'total': len(all_feature_cols), 'features': passing}
    print(f'    >> {len(passing)}/{len(all_feature_cols)} passing')

# Dynamic window
print('\n=== Dynamic Window IC (22 features) ===')
for window in [200, 500, 1000, 2000, 4600]:
    tail_ts_set = set(timestamps[-window:])
    passing = []
    for f in all_feature_cols:
        fv = np.array(feat_data[f])
        mf, ml = [], []
        for j, ts in enumerate(timestamps):
            if ts in tail_ts_set and ts in label_map and not np.isnan(fv[j]):
                mf.append(fv[j])
                ml.append(label_map[ts])
        mf, ml = np.array(mf), np.array(ml)
        if len(mf) < 50 or np.std(mf) < 1e-10:
            ic_val = 0
        else:
            c = np.corrcoef(mf, ml)
            ic_val = c[0,1] if np.isfinite(c[0,1]) else 0
        if abs(ic_val) >= 0.05:
            passing.append(f'{f}({ic_val:+.3f})')
    print(f'  N={window:>4d}: {len(passing)}/{len(all_feature_cols)} passing -- {passing}')

# Save full results
output = {
    'full_ic': ic_results,
    'regime_ic': regime_results,
    'n_features': len(all_feature_cols),
    'feature_names': all_feature_cols,
}
with open('data/ic_full_hb157.json', 'w') as f:
    json.dump(output, f, indent=2)
print(f'\nSaved to data/ic_full_hb157.json')

db.close()
