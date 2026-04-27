#!/usr/bin/env python3
"""IC calculation with proper timestamp matching (strip microseconds)."""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'

def strip_microseconds(ts_str):
    """Normalize timestamp by removing microseconds for matching."""
    if ts_str is None:
        return None
    # Remove .000000 if present
    return ts_str.split('.')[0] if '.' in ts_str else ts_str

def pearson_ic(x, y):
    """Calculate Pearson correlation coefficient."""
    n = len(x)
    if n < 10:
        return None, n
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = sum((xi - mean_x) ** 2 for xi in x)
    den_y = sum((yi - mean_y) ** 2 for yi in y)
    if den_x < 1e-30 or den_y < 1e-30:
        return None, n
    return num / (den_x ** 0.5 * den_y ** 0.5), n

conn = sqlite3.connect(DB_PATH)

# Get features with timestamps
cur = conn.execute("SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, feat_pulse, feat_aura, feat_mind FROM features_normalized ORDER BY timestamp")
all_features = cur.fetchall()

# Get labels - normalize timestamps
cur = conn.execute("SELECT timestamp, label_up FROM labels WHERE label_up IS NOT NULL")
all_labels = cur.fetchall()
# Strip microseconds for matching
label_dict = {strip_microseconds(row[0]): row[1] for row in all_labels}

sensory_features = {
    'feat_eye': 'Eye', 'feat_ear': 'Ear', 'feat_nose': 'Nose',
    'feat_tongue': 'Tongue', 'feat_body': 'Body', 'feat_pulse': 'Pulse',
    'feat_aura': 'Aura', 'feat_mind': 'Mind'
}
feat_indices = {
    'feat_eye': 1, 'feat_ear': 2, 'feat_nose': 3,
    'feat_tongue': 4, 'feat_body': 5, 'feat_pulse': 6,
    'feat_aura': 7, 'feat_mind': 8
}

# Check matching
matched = 0
for row in all_features:
    if strip_microseconds(row[0]) in label_dict:
        matched += 1
print(f"Matched feature-label pairs: {matched} / {len(all_features)}")

def calc_ics(data_rows, label_dict):
    """Calculate IC for all senses."""
    results = {}
    for feat_col, sense_name in sensory_features.items():
        idx = feat_indices[feat_col]
        pairs = []
        for row in data_rows:
            ts = strip_microseconds(row[0])
            feat_val = row[idx]
            if ts in label_dict and feat_val is not None:
                pairs.append((feat_val, label_dict[ts]))
        
        if len(pairs) < 10:
            print(f"  {sense_name:8s}: SKIP (n={len(pairs)})")
            results[sense_name] = {'ic': None, 'n': len(pairs), 'std': None}
            continue
        
        x = [p[0] for p in pairs]
        y = [p[1] for p in pairs]
        ic, n = pearson_ic(x, y)
        std_val = (sum((xi - sum(x)/len(x))**2 for xi in x) / len(x)) ** 0.5
        range_val = (min(x), max(x))
        unique_count = len(set(x))
        
        status = ""
        if ic is None:
            status = "(NaN - constant/variance too low)"
        elif abs(ic) < 0.05:
            status = "⚠️ BELOW 0.05 THRESHOLD"
        else:
            status = "✅"
            
        print(f"  {sense_name:8s}: IC={ic:+.4f} (std={std_val:.4f}, n={n}, unique={unique_count}, range=[{range_val[0]:.4f}, {range_val[1]:.4f}) {status}")
        results[sense_name] = {
            'ic': round(ic, 4) if ic is not None else None,
            'n': n,
            'std': round(std_val, 4),
            'unique': unique_count,
            'range': [round(range_val[0], 4), round(range_val[1], 4)],
            'status': 'ok' if ic is not None and abs(ic) >= 0.05 else 'warning' if ic is not None else 'nan'
        }
    return results

# Full dataset IC
print("\n=== Full Dataset IC (N={}) ===".format(len(all_features)))
ics_full = calc_ics(all_features, label_dict)

# Recent 5000 IC
recent_data = all_features[-5000:] if len(all_features) > 5000 else all_features
print(f"\n=== Recent Data IC (last 5000, N={len(recent_data)}) ===")
ics_recent = calc_ics(recent_data, label_dict)

# Save to ic_signs.json
result = {
    'timestamp': datetime.now().isoformat(),
    'n_records': len(all_features),
    'n_matched': matched,
    'ics_full': {k: v['ic'] for k, v in ics_full.items()},
    'ics_recent': {k: v['ic'] for k, v in ics_recent.items()},
    'stats': ics_recent  # Full stats from recent data
}
json_path = '/home/kazuha/Poly-Trader/data/ic_signs.json'
os.makedirs(os.path.dirname(json_path), exist_ok=True)
with open(json_path, 'w') as f:
    json.dump(result, f, indent=2, default=str)
print(f"\nIC results saved to {json_path}")

# Summary
print("\n=== IC STATUS SUMMARY (Recent N=5000) ===")
for sense, data in ics_recent.items():
    ic_val = data['ic']
    if ic_val is None:
        print(f"  {sense}: NaN ❌")
    elif abs(ic_val) < 0.05:
        print(f"  {sense}: {ic_val:+.4f} ❌ BELOW THRESHOLD")
    else:
        print(f"  {sense}: {ic_val:+.4f} ✅")

conn.close()
