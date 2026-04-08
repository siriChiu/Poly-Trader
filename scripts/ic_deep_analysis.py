#!/usr/bin/env python
"""IC analysis across different subsets and label types."""
import sqlite3
import numpy as np
from scipy.stats import spearmanr
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'poly_trader.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

feats_map = {
    'Eye': 0, 'Ear': 1, 'Nose': 2, 'Tongue': 3,
    'Body': 4, 'Pulse': 5, 'Aura': 6, 'Mind': 7
}

for label_type, label_idx in [('label_up', 8), ('label_spot_long_win', 9)]:
    print(f"\n=== IC Analysis: {label_type}, by N window ===")
    for n_limit in [1000, 2500, 5000, 8770]:
        cur.execute(f'''SELECT f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue, 
                       f.feat_body, f.feat_pulse, f.feat_aura, f.feat_mind,
                       l.label_up, l.label_spot_long_win
                FROM features_normalized f
                JOIN labels l ON l.timestamp = f.timestamp
                ORDER BY f.timestamp DESC LIMIT {n_limit}''')
        rows = cur.fetchall()
        
        for name, idx in feats_map.items():
            f_vals = np.array([r[idx] for r in rows if r[idx] is not None and r[label_idx] is not None])
            l_vals = np.array([r[label_idx] for r in rows if r[idx] is not None and r[label_idx] is not None])
            
            if len(f_vals) > 50:
                ic, pval = spearmanr(f_vals, l_vals)
                if n_limit == 5000:
                    status = 'PASS' if abs(ic) >= 0.05 else 'FAIL'
                    print(f"  {name}(N={n_limit}): IC={ic:+.4f} p={pval:.4f} [{status}]", end='')

conn.close()
print("\n\nDone")
