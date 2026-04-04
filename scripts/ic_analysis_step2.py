#!/usr/bin/env python3
"""Step 2: Sensory IC Analysis for Poly-Trader heartbeat — full computation"""
import sqlite3
import numpy as np
from datetime import datetime

db_path = 'poly_trader.db'
conn = sqlite3.connect(db_path)

# Load features and labels together
query = """
SELECT 
    f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue, f.feat_body,
    f.feat_pulse, f.feat_aura, f.feat_mind,
    f.regime_label,
    l.label_sell_win
FROM features_normalized f
INNER JOIN labels l ON f.timestamp = l.timestamp AND f.symbol = l.symbol
WHERE l.label_sell_win IS NOT NULL
ORDER BY f.timestamp
"""

rows = conn.execute(query).fetchall()
conn.close()

if not rows:
    print("ERROR: No data found")
    exit(1)

# Parse into arrays
feature_names = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']
n = len(rows)
print(f"Total samples: {n}")

# Build arrays
label = np.array([r[9] for r in rows], dtype=float)
senses = []
for i in range(8):
    vals = np.array([r[i] for r in rows], dtype=float)
    # Handle NaN
    mask = ~np.isnan(vals) & ~np.isnan(label)
    valid_vals = vals[mask]
    valid_labels = label[mask]
    
    if len(valid_vals) < 100:
        print(f"WARNING: {feature_names[i]} has only {len(valid_vals)} valid samples")
        continue
        
    ic = np.corrcoef(valid_vals, valid_labels)[0, 1]
    std = np.std(valid_vals)
    
    senses.append({
        'name': feature_names[i],
        'ic': float(ic),
        'std': float(std),
        'range': float(np.ptp(valid_vals)),
        'unique_count': len(np.unique(valid_vals.round(6))),
        'abs_ic': float(abs(ic)),
        'passes': abs(ic) >= 0.05
    })

print(f"\n{'='*70}")
print(f"全域 IC Analysis (N={n}, h=4h, vs label_sell_win)")
print(f"{'='*70}")

for s in sorted(senses, key=lambda x: abs(x['ic']), reverse=True):
    status = "✅" if s['passes'] else "❌"
    print(f"  {s['name']:8s} IC={s['ic']:+.4f} | std={s['std']:.4f} | range={s['range']:.4f} | uniq={s['unique_count']:5d} | {status}")

passing = sum(1 for s in senses if s['passes'])
print(f"\n達標 (|IC| >= 0.05): {passing}/8")

# --- Regime-Aware IC ---
print(f"\n{'='*70}")
print(f"Regime-Aware IC (分割 3 等分)")
print(f"{'='*70}")

# Regime labels
conn2 = sqlite3.connect(db_path)
regime_query = """
SELECT 
    f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue, f.feat_body,
    f.feat_pulse, f.feat_aura, f.feat_mind,
    f.regime_label,
    l.label_sell_win
FROM features_normalized f
INNER JOIN labels l ON f.timestamp = l.timestamp AND f.symbol = l.symbol
WHERE l.label_sell_win IS NOT NULL
ORDER BY f.timestamp
"""
rows2 = conn2.execute(regime_query).fetchall()
conn2.close()

n2 = len(rows2)
third = n2 // 3
regimes = {
    'Bear': (0, third),
    'Bull': (third, 2*third),
    'Chop': (2*third, n2)
}

print(f"\n分割點: Bear=[0:{third}], Bull=[{third}:{2*third}], Chop=[{2*third}:{n2}]")

for regime_name, (start, end) in regimes.items():
    sub_rows = rows2[start:end]
    if not sub_rows:
        continue
    
    regime_label = np.array([r[9] for r in sub_rows], dtype=float)
    print(f"\n--- {regime_name} (N={len(sub_rows)}, sell_win={regime_label.mean():.1%}) ---")
    
    for i, name in enumerate(feature_names):
        vals = np.array([r[i] for r in sub_rows], dtype=float)
        mask = ~np.isnan(vals) & ~np.isnan(regime_label)
        valid_vals = vals[mask]
        valid_labels = regime_label[mask]
        
        if len(valid_vals) < 30:
            continue
        
        ic = np.corrcoef(valid_vals, valid_labels)[0, 1]
        status = "✅" if abs(ic) >= 0.05 else "❌"
        print(f"  {name:8s} IC={ic:+.4f} | {status}")

# --- Dynamic Window IC ---
print(f"\n{'='*70}")
print(f"動態窗口 IC 衰減")
print(f"{'='*70}")

# Build full feature matrix for windowed analysis
feat_matrix = []
for i in range(8):
    col = np.array([r[i] for r in rows], dtype=float)
    feat_matrix.append(col)

for win in [500, 1000, 2000, 3000, 5000]:
    if win > n:
        break
    sub_labels = label[-win:]
    print(f"\n--- N={win} ---")
    pass_count = 0
    passing_senses = []
    for i, name in enumerate(feature_names):
        sub_vals = feat_matrix[i][-win:]
        mask = ~np.isnan(sub_vals) & ~np.isnan(sub_labels)
        valid_vals = sub_vals[mask]
        valid_labels = sub_labels[mask]
        
        if len(valid_vals) < 30:
            continue
        
        ic = np.corrcoef(valid_vals, valid_labels)[0, 1]
        passes = abs(ic) >= 0.05
        if passes:
            pass_count += 1
            passing_senses.append(f"{name}({ic:+.3f})")
    
    status = ','.join(passing_senses) if passing_senses else "全滅"
    print(f"  達標: {pass_count}/8 — {status}")

# Save results for later use
results = {
    'global_ic': {s['name']: {'ic': s['ic'], 'passes': s['passes']} for s in senses},
    'global_passing': passing,
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'n_samples': n,
    'label_mean': float(label.mean())
}
    
with open('scripts/ic_results.json', 'w') as f:
    json.dump(results, f, indent=2)
    
print(f"\nResults saved to scripts/ic_results.json")
