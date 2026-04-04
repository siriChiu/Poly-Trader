#!/usr/bin/env python3
"""Full IC Analysis - Step 2: Sensory IC Analysis"""
import sqlite3
import numpy as np
from scipy.stats import spearmanr
import json

db = sqlite3.connect('poly_trader.db')

# Get features
feat_cols = [c[1] for c in db.execute('PRAGMA table_info(features_normalized)').fetchall()]
print(f"Feature columns: {feat_cols}")

# Get labels
label_cols = [c[1] for c in db.execute('PRAGMA table_info(labels)').fetchall()][:5]
print(f"Label columns: {label_cols}")

# Fetch data
features = db.execute('SELECT * FROM features_normalized').fetchall()
labels = db.execute('SELECT sell_win, regime FROM labels').fetchall()

n_feat = len(features)
n_label = len(labels)
n = min(n_feat, n_label)
print(f"\nN features: {n_feat}, N labels: {n_label}, Using: {n}")

# Sense mapping
sense_map = {}
for col in feat_cols:
    if col.startswith('feat_eye'): sense_map[col] = 'Eye'
    elif col.startswith('feat_ear'): sense_map[col] = 'Ear'
    elif col.startswith('feat_nose'): sense_map[col] = 'Nose'
    elif col.startswith('feat_tongue'): sense_map[col] = 'Tongue'
    elif col.startswith('feat_body'): sense_map[col] = 'Body'
    elif col.startswith('feat_pulse'): sense_map[col] = 'Pulse'
    elif col.startswith('feat_aura'): sense_map[col] = 'Aura'
    elif col.startswith('feat_mind'): sense_map[col] = 'Mind'
    elif 'rsi' in col.lower(): sense_map[col] = f'RSI({col})'
    elif 'bb' in col.lower(): sense_map[col] = f'BB({col})'
    elif 'macd' in col.lower(): sense_map[col] = f'MACD({col})'
    elif 'atr' in col.lower(): sense_map[col] = f'ATR({col})'
    elif 'vwap' in col.lower(): sense_map[col] = f'VWAP({col})'
    elif 'vol' in col.lower(): sense_map[col] = f'Vol({col})'
    elif 'momentum' in col.lower(): sense_map[col] = f'Mom({col})'
    else: sense_map[col] = f'??({col})'

# Calculate IC for each feature against sell_win
print(f"\n=== IC Analysis (h=4) ===")
ics = {}
for col in feat_cols:
    vals = []
    sw_vals = []
    for i in range(n):
        fv = features[i][feat_cols.index(col)]
        lv = labels[i][0]  # sell_win
        if fv is not None and lv is not None:
            try:
                vals.append(float(fv))
                sw_vals.append(float(lv))
            except (ValueError, TypeError):
                pass
    
    if len(vals) < 100:
        ics[col] = {'ic': None, 'std': 0, 'n': len(vals)}
        print(f"  {col}: IC=NULL (n={len(vals)}, too few)")
        continue
    
    arr = np.array(vals)
    std = np.std(arr)
    unique = len(np.unique(arr))
    
    if std < 1e-10 or unique <= 1:
        ics[col] = {'ic': 0, 'std': 0, 'n': len(vals), 'unique': unique, 'dead': True}
        print(f"  {col}: IC=0 (DEAD, std={std:.6f}, unique={unique})")
        continue
    
    corr, p = spearmanr(vals, sw_vals)
    status = "PASS" if abs(corr) >= 0.05 else "FAIL"
    sense = sense_map.get(col, col)
    ics[col] = {'ic': corr, 'std': std, 'n': len(vals), 'unique': unique, 'sense': sense, 'status': status}
    print(f"  {sense}: IC={corr:+.4f}, std={std:.4f}, unique={unique} [{status}]")

# Summary
passed = {k: v for k, v in ics.items() if v.get('status') == 'PASS'}
print(f"\nPassed: {len(passed)}/{len(ics)}")
if passed:
    for k, v in passed.items():
        print(f"  {v.get('sense', k)}: IC={v['ic']:+.4f}")

# Regime analysis
print(f"\n=== Regime IC Analysis ===")
regimes = {}
for i in range(n):
    sell_win = labels[i][0]
    regime = labels[i][1] if len(labels[i]) > 1 else None
    if sell_win is not None and regime is not None:
        if regime not in regimes:
            regimes[regime] = {'sell_wins': [], 'features': {}}
        regimes[regime]['sell_wins'].append(float(sell_win))
        for col in feat_cols:
            fv = features[i][feat_cols.index(col)]
            if fv is not None:
                try:
                    fv = float(fv)
                    if col not in regimes[regime]['features']:
                        regimes[regime]['features'][col] = {'feat': [], 'sw': []}
                    regimes[regime]['features'][col]['feat'].append(fv)
                    regimes[regime]['features'][col]['sw'].append(float(sell_win))
                except (ValueError, TypeError):
                    pass

for regime_name, data in regimes.items():
    avg_sell_win = np.mean(data['sell_wins'])
    print(f"\n--- {regime_name} (n={len(data['sell_wins'])}, sell_win={avg_sell_win:.4f}) ---")
    regime_passed = 0
    for col, vals in data['features'].items():
        if len(vals['feat']) > 100:
            arr = np.array(vals['feat'])
            std = np.std(arr)
            unique = len(np.unique(arr))
            if std > 1e-10 and unique > 1:
                corr, _ = spearmanr(vals['feat'], vals['sw'])
                status = "PASS" if abs(corr) >= 0.05 else ""
                if abs(corr) >= 0.05:
                    regime_passed += 1
                    sense = sense_map.get(col, col)
                    print(f"    {sense}: IC={corr:+.4f}")
    print(f"  Regime passing: {regime_passed}/{len(data['features'])}")

# Save results
out = {
    'ics': {k: {'ic': v.get('ic'), 'std': v.get('std'), 'sense': v.get('sense'), 'status': v.get('status')} for k, v in ics.items()},
    'passed_count': len(passed),
    'total_features': len(ics),
    'regimes': {k: {'n': len(v['sell_wins']), 'sell_win_avg': np.mean(v['sell_wins'])} for k, v in regimes.items()},
    'timestamp': '2026-04-04 16:37'
}
with open('data/ic_heartbeat_hb194.json', 'w') as f:
    json.dump(out, f, indent=2)

db.close()
