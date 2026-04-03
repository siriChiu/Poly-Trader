#!/usr/bin/env python3
"""Deep IC analysis: non-linear IC, lag analysis, interaction terms"""
import sqlite3
import math

DB = '/home/kazuha/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(DB)

# Get all data
cur = conn.execute('SELECT timestamp, label_up FROM labels ORDER BY timestamp')
all_labels = cur.fetchall()
label_dict = {row[0]: row[1] for row in all_labels}

cur = conn.execute('SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, feat_pulse, feat_aura, feat_mind FROM features_normalized ORDER BY timestamp')
all_features = cur.fetchall()

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

# For recent 5000
recent = all_features[-5000:]
pairs = {}
for feat_col, sense_name in sensory_features.items():
    idx = feat_indices[feat_col]
    x = []
    y = []
    for row in recent:
        ts = row[0]
        feat_val = row[idx]
        if ts in label_dict and feat_val is not None:
            x.append(feat_val)
            y.append(label_dict[ts])
    pairs[sense_name] = (x, y)

# Spearman IC (rank correlation)
def spearman_ic(x, y):
    n = len(x)
    if n < 100:
        return None
    
    # Rank x
    x_rank = sorted(range(n), key=lambda i: x[i])
    x_ranks = [0] * n
    for rank, i in enumerate(x_rank):
        x_ranks[i] = rank
    
    # Rank y
    y_rank = sorted(range(n), key=lambda i: y[i])
    y_ranks = [0] * n
    for rank, i in enumerate(y_rank):
        y_ranks[i] = rank
    
    # Compute correlation
    mean_xr = (n - 1) / 2
    mean_yr = (n - 1) / 2
    
    dx = [xr - mean_xr for xr in x_ranks]
    dy = [yr - mean_yr for yr in y_ranks]
    
    num = sum(a * b for a, b in zip(dx, dy))
    dx2 = sum(a * a for a in dx)
    dy2 = sum(b * b for b in dy)
    
    if dx2 < 1e-10 or dy2 < 1e-10:
        return None
    
    return num / math.sqrt(dx2 * dy2)

def point_biserial(x, y):
    """Point-biserial correlation: continuous x vs binary y"""
    n = len(x)
    n1 = sum(y)
    n0 = n - n1
    
    if n1 < 10 or n0 < 10:
        return None, n0, n1
    
    mean_x1 = sum(xi for xi, yi in zip(x, y) if yi == 1) / n1
    mean_x0 = sum(xi for xi, yi in zip(x, y) if yi == 0) / n0
    
    # Pooled std
    ss1 = sum((xi - mean_x1) ** 2 for xi, yi in zip(x, y) if yi == 1)
    ss0 = sum((xi - mean_x0) ** 2 for xi, yi in zip(x, y) if yi == 0)
    sp = math.sqrt((ss1 + ss0) / (n - 2))
    
    if sp < 1e-10:
        return None, n0, n1
    
    return (mean_x1 - mean_x0) / sp * math.sqrt(n0 * n1 / (n * (n - 1))), n0, n1

print("=== DEEP IC ANALYSIS (Recent N=5000) ===")
print("\n--- Spearman Rank Correlation ---")
for name, (x, y) in pairs.items():
    ic = spearman_ic(x, y)
    status = "✅" if ic and abs(ic) >= 0.05 else "❌"
    print(f"  {name:10s}: Spearman IC={ic:+.4f} {status}")

print("\n--- Point-Biserial Correlation ---")
for name, (x, y) in pairs.items():
    ic, n0, n1 = point_biserial(x, y)
    status = "✅" if ic and abs(ic) >= 0.05 else "❌"
    print(f"  {name:10s}: PB IC={ic:+.4f} (n0={n0}, n1={n1}) {status}")

# Check if features have monotonic relationship with label
print("\n--- Quartile Analysis ---")
for name, (x, y) in pairs.items():
    # Sort by feature
    sorted_pairs = sorted(zip(x, y), key=lambda p: p[0])
    n = len(sorted_pairs)
    q_size = n // 4
    
    print(f"\n  {name}:")
    for q in range(4):
        start = q * q_size
        end = start + q_size if q < 3 else n
        q_y = [p[1] for p in sorted_pairs[start:end]]
        win_rate = sum(q_y) / len(q_y) if q_y else 0
        print(f"    Q{q}: win_rate={win_rate:.3f}, n={len(q_y)}")

conn.close()
