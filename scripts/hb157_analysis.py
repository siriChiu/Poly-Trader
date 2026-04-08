#!/usr/bin/env python3
"""Heartbeat #157 - Comprehensive IC Analysis"""
import sys, json, os, sqlite3
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')
import numpy as np

db = sqlite3.connect('poly_trader.db')

# Fetch features and labels
feat_rows = db.execute('SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, feat_pulse, feat_aura, feat_mind FROM features_normalized ORDER BY timestamp').fetchall()
labels_rows = db.execute('SELECT timestamp, label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL').fetchall()
label_map = {r[0]: r[1] for r in labels_rows}

feat_names = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']
feats = {n: [] for n in feat_names}
timestamps = []
for row in feat_rows:
    ts = row[0]
    timestamps.append(ts)
    for i, n in enumerate(feat_names):
        try:
            feats[n].append(float(row[i+1]) if row[i+1] is not None else np.nan)
        except:
            feats[n].append(np.nan)

# Dynamic window analysis
print('=== Dynamic Window IC Analysis ===')
for window in [200, 300, 400, 500, 600, 800, 1000, 2000]:
    tail_ts = timestamps[-window:]
    tail_set = set(tail_ts)
    passing = []
    details = []
    for name in feat_names:
        fv = np.array(feats[name])
        mf, ml = [], []
        for j, ts in enumerate(timestamps):
            if ts in tail_set and ts in label_map and not np.isnan(fv[j]):
                mf.append(fv[j])
                ml.append(label_map[ts])
        mf = np.array(mf)
        ml = np.array(ml)
        if len(mf) < 50 or np.std(mf) < 1e-10:
            ic = 0
        else:
            c = np.corrcoef(mf, ml)
            ic = c[0,1] if np.isfinite(c[0,1]) else 0
        if abs(ic) >= 0.05:
            passing.append(f'{name}({ic:+.3f})')
        details.append(f'{name}({ic:+.3f})')
    print(f'  N={window:>4d}: {len(passing)}/8 passing -- {passing}')

# Proper regime IC using regime_label column
print('\n=== Proper Regime IC (regime_label column) ===')
regime_data = db.execute('SELECT timestamp, regime_label FROM features_normalized WHERE regime_label IS NOT NULL ORDER BY timestamp').fetchall()
regime_map = {r[0]: r[1] for r in regime_data}

regime_results = {}
for regime in ['bear', 'bull', 'chop']:
    ts_set = set(ts for ts, r in regime_map.items() if r == regime)
    passing_count = 0
    print(f'\n  {regime.upper()} (from DB: {len(ts_set)} samples):')
    for name in feat_names:
        fv = np.array(feats[name])
        mf, ml = [], []
        for j, ts in enumerate(timestamps):
            if ts in ts_set and ts in label_map and not np.isnan(fv[j]):
                mf.append(fv[j])
                ml.append(label_map[ts])
        mf, ml = np.array(mf), np.array(ml)
        if len(mf) < 50 or np.std(mf) < 1e-10:
            ic = 0
        else:
            c = np.corrcoef(mf, ml)
            ic = c[0,1] if np.isfinite(c[0,1]) else 0
        status = 'PASS' if abs(ic) >= 0.05 else 'FAIL'
        if abs(ic) >= 0.05:
            passing_count += 1
        print(f'    {name:8s}: IC={ic:+.4f}  n={len(mf)}  [{status}]')
    regime_results[regime] = passing_count
    print(f'    >> {passing_count}/8 passing')

# Regime distribution
counts = db.execute('SELECT regime_label, COUNT(*) FROM features_normalized GROUP BY regime_label').fetchall()
print(f'\nRegime distribution: {counts}')

# Also fetch derivatives data if available
try:
    latest = db.execute('SELECT close_price, timestamp, funding_rate, fear_greed_index, volume FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    print(f'\nLatest BTC: ${latest[0]:,.0f}, FNG: {latest[3]}, Funding: {latest[2]}')
except Exception as e:
    print(f'\nCould not fetch market data: {e}')

# Model performance check
try:
    model_files = [f for f in os.listdir('/home/kazuha/Poly-Trader/models') if f.endswith('.pkl')]
    print(f'\nSaved models: {model_files}')
except Exception as e:
    print(f'\nNo models directory or models: {e}')

db.close()
