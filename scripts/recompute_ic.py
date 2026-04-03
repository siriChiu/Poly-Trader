#!/usr/bin/env python
"""Heartbeat Step 2: Recompute IC after label fix."""
import sqlite3
import numpy as np
from scipy.stats import spearmanr
import os, json

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'poly_trader.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Check timestamp formats
cur.execute("SELECT timestamp FROM features_normalized LIMIT 3")
f_ts = cur.fetchall()
cur.execute("SELECT timestamp FROM labels LIMIT 3")
l_ts = cur.fetchall()
print(f"Feature ts fmt: {[r[0] for r in f_ts]}")
print(f"Label ts fmt:   {[r[0] for r in l_ts]}")

# Use the label data we just computed with proper horizon
# Join features with labels - use inner join on exact timestamp
# Since we just fixed labels, the timestamp should match exactly
query = """
SELECT f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue, 
       f.feat_body, f.feat_pulse, f.feat_aura, f.feat_mind,
       l.label_up, l.label_sell_win, l.future_return_pct, l.future_max_drawdown, l.future_max_runup
FROM features_normalized f
INNER JOIN labels l ON l.timestamp = f.timestamp AND l.symbol = f.symbol
WHERE l.horizon_minutes = 240
ORDER BY f.timestamp DESC
"""

cur.execute(query)
rows = cur.fetchall()
print(f"\nJoined rows (exact match, 4h horizon): {len(rows)}")

if len(rows) < 100:
    # Fallback: nearest timestamp match
    print("Exact join failed, using nearest match...")
    cur.execute("SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, feat_pulse, feat_aura, feat_mind FROM features_normalized ORDER BY timestamp DESC")
    feat_rows = cur.fetchall()
    
    # Get all labels
    cur.execute("SELECT timestamp, label_up, label_sell_win, future_return_pct, horizon_minutes FROM labels WHERE horizon_minutes = 240")
    labels = cur.fetchall()
    label_map = {r[0]: r[1:] for r in labels}  # timestamp -> (label_up, sell_win, ret)
    
    rows = []
    matched = 0
    for fr in feat_rows:
        ts = fr[0]
        if ts in label_map:
            rows.append(fr[1:] + label_map[ts])
            matched += 1
    
    print(f"Nearest match found {matched} pairs")

if len(rows) < 100:
    print(f"Still only {len(rows)} joined rows. Cannot compute meaningful ICs.")
    conn.close()
    exit(1)

# Take recent window
n_limit = min(5000, len(rows))
rows = rows[:n_limit]
print(f"Using {len(rows)} rows for IC analysis")

# Label columns (after 8 features + label_up + label_sell_win + ret + dd + ru)
# Row indices: 0=eye, 1=ear, 2=nose, 3=tongue, 4=body, 5=pulse, 6=aura, 7=mind
#             8=label_up, 9=label_sell_win, 10=future_ret, 11=max_dd, 12=max_ru

sense_names = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']
ic_results = {}

for label_type, l_idx, l_name in [
    ('label_up', 8, 'label_up'),
    ('sell_win', 9, 'sell_win'),
]:
    print(f"\n=== IC Analysis vs {l_name} (N={len(rows)}) ===")
    for sense_name, f_idx in zip(sense_names, range(8)):
        vals = [r[f_idx] for r in rows]
        labs = [r[l_idx] for r in rows]
        
        valid = [(v, l) for v, l in zip(vals, labs) if v is not None and l is not None]
        if len(valid) < 100:
            print(f"  {sense_name}: N={len(valid)} (too few)")
            continue
        
        f_arr = np.array([v for v, l in valid])
        l_arr = np.array([l for v, l in valid])
        
        std = float(np.std(f_arr))
        unique = len(np.unique(f_arr))
        
        if std < 1e-10:
            print(f"  {sense_name}: CONSTANT (std≈0), unique={unique}")
            ic_results[sense_name] = {'ic': 'NaN', 'std': 0, 'pval': 1, 'label': l_name}
            continue
        
        try:
            ic, pval = spearmanr(f_arr, l_arr)
            status = 'PASS' if abs(ic) >= 0.05 else 'FAIL'
            print(f"  {sense_name}: IC={ic:+.4f} (p={pval:.4f}), std={std:.4f}, unique={unique} [{status}]")
            ic_results[sense_name] = {'ic': round(float(ic), 4), 'std': round(std, 4), 'pval': round(float(pval), 4), 'label': l_name}
        except:
            print(f"  {sense_name}: ERROR")
            ic_results[sense_name] = {'ic': 'Error', 'std': std, 'pval': 1, 'label': l_name}

conn.close()

# Save
output = {
    'n': len(rows),
    'labels': 'label_up' if ic_results.get('Eye', {}).get('label') == 'label_up' else 'sell_win',
    'ics': ic_results
}
with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'ic_signs.json'), 'w') as f:
    json.dump(output, f, indent=2)

print(f"\nResults saved to data/ic_signs.json")
