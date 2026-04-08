#!/usr/bin/env python3
"""Full IC analysis for heartbeat #202."""
import sqlite3
import numpy as np

DB = 'poly_trader.db'
conn = sqlite3.connect(DB)

# Get features and labels joined
query = """
SELECT 
    f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue, f.feat_body,
    f.feat_pulse, f.feat_aura, f.feat_mind,
    f.feat_vix, f.feat_dxy, f.feat_rsi14, f.feat_macd_hist, 
    f.feat_atr_pct, f.feat_vwap_dev, f.feat_bb_pct_b,
    l.label_spot_long_win, l.regime_label
FROM features_normalized f
JOIN labels l ON f.timestamp = l.timestamp AND f.symbol = l.symbol
WHERE l.label_spot_long_win IS NOT NULL
"""

rows = conn.execute(query).fetchall()
conn.close()

if not rows:
    print("ERROR: No joined data found!")
    exit(1)

feature_names = [
    'Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind',
    'VIX', 'DXY', 'RSI14', 'MACD_hist', 'ATR_pct', 'VWAP_dev', 'BB%p'
]

# Extract feature columns (first 15), label, and regime string
features = np.array([[r[i] for i in range(15)] for r in rows], dtype=float)
labels = np.array([r[15] for r in rows], dtype=float)
regimes_str = [r[16] for r in rows]

n_total = len(labels)
print(f"=== Heartbeat #202 IC Analysis ===")
print(f"Total samples: {n_total}")
print(f"Label distribution: sell_win=0: {int(sum(labels==0))}, sell_win=1: {int(sum(labels==1))}")
print(f"sell_win rate: {labels.mean():.4f}\n")
# Regime distribution
from collections import Counter
regime_counts = Counter(regimes_str)
print(f"Regime distribution: {dict(regime_counts)}\n")

# Global IC (only where all features are valid)
print("=== Global IC against label_spot_long_win ===")
print(f"{'Feature':<12} {'IC':>8} {'std':>10} {'unique':>8} {'Status':>8}")
print("-" * 64)
global_results = {}
for i, name in enumerate(feature_names):
    feat = features[:, i]
    valid_mask = ~np.isnan(feat)
    feat_valid = feat[valid_mask]
    lbl_valid = labels[valid_mask]
    
    if len(feat_valid) < 100:
        print(f"{name:<12} {'N/A':>8} {'N/A':>10} {'N/A':>8} {'TOO_FEW':>8}")
        continue
    
    std_val = np.std(feat_valid)
    unique_count = len(np.unique(feat_valid))
    
    if std_val < 1e-10:
        ic_val = 0.0
        status = "DEAD"
    else:
        ic_val = np.corrcoef(feat_valid, lbl_valid)[0, 1]
        status = "PASS" if abs(ic_val) >= 0.05 else "FAIL"
    
    global_results[name] = {'ic': ic_val, 'std': std_val, 'unique': unique_count}
    
    arrow = "✅" if status == "PASS" else ("⚠️" if status == "NEAR" else "❌")
    print(f"{arrow} {name:<10} {ic_val:+.4f} {std_val:>10.4f} {unique_count:>8} {status:>8}")

pass_count = sum(1 for v in global_results.values() if abs(v['ic']) >= 0.05)
print(f"\nGlobal PASS: {pass_count}/{len(global_results)}\n")

# Regime IC
print("=== Regime IC ===")
for reg_name in ['bear', 'bull', 'chop', 'neutral']:
    mask = np.array([r == reg_name for r in regimes_str])
    n_regime = int(mask.sum())
    if n_regime < 50:
        print(f"\n  {reg_name.upper()} (n={n_regime}) — too small")
        continue
    reg_labels = labels[mask]
    reg_sell_win = reg_labels.mean()
    pass_count_regime = 0
    print(f"\n  {reg_name.upper()} regime (n={n_regime}, sell_win={reg_sell_win:.3f}):")
    for i, fname in enumerate(feature_names):
        feat = features[mask, i]
        valid_mask = ~np.isnan(feat)
        feat_v = feat[valid_mask]
        lbl_v = reg_labels[valid_mask]
        if len(feat_v) < 30:
            continue
        std_v = np.std(feat_v)
        if std_v < 1e-10:
            ic_val = 0
            status = "DEAD"
        else:
            ic_val = np.corrcoef(feat_v, lbl_v)[0, 1]
            status = "PASS" if abs(ic_val) >= 0.05 else "FAIL"
        if status == "PASS":
            pass_count_regime += 1
        arrow = "✅" if status == "PASS" else "❌"
        print(f"    {arrow} {fname:<10} IC={ic_val:+.4f} (std={std_v:.4f})")
    print(f"  => {reg_name}: {pass_count_regime}/{min(8, len(feature_names))} features PASS")
