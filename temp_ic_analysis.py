"""Sensory IC Analysis for Heartbeat."""
import json, os, sqlite3
import numpy as np
import warnings
warnings.filterwarnings('ignore')

db_path = '/home/kazuha/Poly-Trader/data/feature_data.db'
conn = sqlite3.connect(db_path)

import pandas as pd
features_df = pd.read_sql('SELECT * FROM features ORDER BY timestamp', conn)
labels_df = pd.read_sql('SELECT * FROM labels ORDER BY timestamp', conn)

merged = features_df.merge(labels_df, on='timestamp', how='inner')
print(f"Features rows: {len(features_df)}")
print(f"Labels rows: {len(labels_df)}")
print(f"Common timestamps: {len(merged)}")

merged = merged.sort_values('timestamp').reset_index(drop=True)
n = len(merged)

tau = 200
sensory_cols = ['feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind']
sense_names = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']

print("\n=== Time-Weighted IC (tau=200, exponential decay) ===")
tw_ics = {}
for col, name in zip(sensory_cols, sense_names):
    if col not in merged.columns or 'sell_win' not in merged.columns:
        print(f"{name}: SKIP (column missing)"); continue
    
    x = merged[col].values.astype(float)
    y = merged['sell_win'].values.astype(float)
    
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    
    if len(x) < 100:
        print(f"{name}: SKIP (n={len(x)} < 100)"); continue
    
    weights = np.exp(-np.arange(len(x))[::-1] / tau)
    weights /= weights.sum()
    
    from scipy.stats import rankdata
    rx = rankdata(x)
    ry = rankdata(y)
    
    w_mean_x = np.average(rx, weights=weights)
    w_mean_y = np.average(ry, weights=weights)
    w_cov = np.sum(weights * (rx - w_mean_x) * (ry - w_mean_y))
    w_std_x = np.sqrt(np.sum(weights * (rx - w_mean_x)**2))
    w_std_y = np.sqrt(np.sum(weights * (ry - w_mean_y)**2))
    
    if w_std_x > 0 and w_std_y > 0:
        tw_ic = w_cov / (w_std_x * w_std_y)
    else:
        tw_ic = 0.0
    
    status = "PASS" if abs(tw_ic) >= 0.05 else "FAIL"
    tw_ics[name] = round(float(tw_ic), 4)
    print(f"{name:8s}: TW-IC={tw_ic:+.4f} [{status}] (n={len(x)})")

passed = sum(1 for v in tw_ics.values() if abs(v) >= 0.05)
print(f"\nTW-IC Pass Rate: {passed}/8 ({passed/8*100:.1f}%)")

y = merged['sell_win'].values.astype(float)
sell_win_rate = y.mean()
recent_100 = y[-100:].mean() if len(y) >= 100 else 0
recent_500 = y[-500:].mean() if len(y) >= 500 else 0

consecutive_losses = 0
max_consecutive = 0
for val in y:
    if val == 0:
        consecutive_losses += 1
        max_consecutive = max(max_consecutive, consecutive_losses)
    else:
        consecutive_losses = 0

print(f"\nSell Win Rate (global): {sell_win_rate*100:.2f}%")
print(f"Recent 100: {recent_100*100:.1f}%")
print(f"Recent 500: {recent_500*100:.1f}%")
print(f"Max consecutive losses: {max_consecutive}")
print(f"Label counts: 0={int((y==0).sum())}, 1={int((y==1).sum())}")

# Print TW-IC as JSON for easy parsing
print(f"\nTW-IC JSON: {json.dumps(tw_ics)}")

conn.close()
