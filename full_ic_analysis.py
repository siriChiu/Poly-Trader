#!/usr/bin/env python3
"""Full IC computation for all 8 primary senses."""
import os, sys, json, sqlite3
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
db = sqlite3.connect(os.path.join(os.path.dirname(__file__), "poly_trader.db"))

# Get features
feat_rows = db.execute("""
    SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body,
           feat_pulse, feat_aura, feat_mind
    FROM features_normalized ORDER BY timestamp
""").fetchall()

# Get labels - use label_sell_win as primary label
label_rows = db.execute("""
    SELECT timestamp, label_sell_win, label_up, future_return_pct
    FROM labels ORDER BY timestamp
""").fetchall()

label_map = {r[0]: {"sell_win": r[1], "up": r[2], "ret": r[3]} for r in label_rows}

feat_cols = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body", "feat_pulse", "feat_aura", "feat_mind"]

# Match timestamps
common = sorted(set(r[0] for r in feat_rows) & set(label_map.keys()))
print(f"Features rows: {len(feat_rows)}")
print(f"Labels rows: {len(label_rows)}")
print(f"Common timestamps: {len(common)}")

# Build arrays
feat_map = {r[0]: {c: r[1+feat_cols.index(c)] for c in feat_cols} for r in feat_rows}

# IC against label_sell_win
print(f"\n{'='*65}")
print(f"IC Analysis — Spearman rank correlation (h=4)")
print(f"{'='*65}")

sense_names = ["Eye", "Ear", "Nose", "Tongue", "Body", "Pulse", "Aura", "Mind"]
ic_results = {}

for sense_name, feat_name in zip(sense_names, feat_cols):
    f_vals = []
    l_vals = []
    for ts in common:
        fv = feat_map.get(ts, {}).get(feat_name)
        lv = label_map.get(ts, {}).get("sell_win")
        if fv is not None and lv is not None:
            f_vals.append(float(fv))
            l_vals.append(float(lv))
    
    n = len(f_vals)
    if n < 50:
        ic_results[sense_name] = {"ic": None, "n": n, "std": 0, "error": "too few samples"}
        print(f"{sense_name:8s}: N={n} (too few)")
        continue
    
    fa = np.array(f_vals)
    la = np.array(l_vals)
    std_val = float(np.std(fa))
    
    if std_val < 1e-10 or np.std(la) < 1e-10:
        ic_results[sense_name] = {"ic": 0.0, "n": n, "std": 0, "unique": int(len(set(fa)))}
        print(f"{sense_name:8s}: IC=0.0000 (std≈0, unique={int(len(set(fa)))})")
        continue
    
    try:
        r, p = stats.spearmanr(fa, la)
        ic_results[sense_name] = {"ic": float(r), "n": n, "p": float(p), "std": std_val}
        status = "OK" if abs(r) >= 0.05 else "FAIL"
        print(f"{sense_name:8s}: IC={r:+.4f}  p={p:.6f}  std={std_val:.6f}  n={n}  [{status}]")
    except Exception as e:
        ic_results[sense_name] = {"ic": None, "n": n, "std": std_val, "error": str(e)}
        print(f"{sense_name:8s}: ERROR: {e}")

# Also compute IC for N=5000 (recent)
n5000 = common[-5000:] if len(common) > 5000 else common
print(f"\n--- Recent N={len(n5000)} ---")
for sense_name, feat_name in zip(sense_names, feat_cols):
    f_vals = []
    l_vals = []
    for ts in n5000:
        fv = feat_map.get(ts, {}).get(feat_name)
        lv = label_map.get(ts, {}).get("sell_win")
        if fv is not None and lv is not None:
            f_vals.append(float(fv))
            l_vals.append(float(lv))
    
    if len(f_vals) < 50:
        continue
    
    fa = np.array(f_vals)
    la = np.array(l_vals)
    if np.std(fa) < 1e-10 or np.std(la) < 1e-10:
        continue
    
    try:
        r, p = stats.spearmanr(fa, la)
        status = "OK" if abs(r) >= 0.05 else "FAIL"
        print(f"{sense_name:8s}: IC={r:+.4f}  p={p:.6f}  [{status}]")
    except:
        pass

# Also check IC against label_up (direction predictability)
print(f"\n--- IC vs label_up (direction) ---")
for sense_name, feat_name in zip(sense_names, feat_cols):
    f_vals = []
    l_vals = []
    for ts in common:
        fv = feat_map.get(ts, {}).get(feat_name)
        lv = label_map.get(ts, {}).get("up")
        if fv is not None and lv is not None:
            f_vals.append(float(fv))
            l_vals.append(float(lv))
    
    if len(f_vals) < 50:
        continue
    
    fa = np.array(f_vals)
    la = np.array(l_vals)
    if np.std(fa) < 1e-10 or np.std(la) < 1e-10:
        continue
    
    try:
        r, p = stats.spearmanr(fa, la)
        status = "OK" if abs(r) >= 0.05 else "FAIL"
        print(f"{sense_name:8s}: IC={r:+.4f}  p={p:.6f}  [{status}]")
    except:
        pass

# Label distribution
sell_win_counts = {}
up_counts = {}
for ts in common:
    lv = label_map[ts]
    sw = lv["sell_win"]
    up = lv["up"]
    sell_win_counts[sw] = sell_win_counts.get(sw, 0) + 1
    up_counts[up] = up_counts.get(up, 0) + 1

print(f"\nLabel distribution (sell_win): {sell_win_counts}")
print(f"Label distribution (up): {up_counts}")

# Check feature value ranges
print(f"\nFeature value statistics:")
for sense_name, feat_name in zip(sense_names, feat_cols):
    vals = [float(feat_map[ts][feat_name]) for ts in common if feat_map.get(ts, {}).get(feat_name) is not None]
    if vals:
        print(f"{sense_name:8s}: mean={np.mean(vals):+.4f} std={np.std(vals):.4f} min={np.min(vals):.4f} max={np.max(vals):.4f} unique={len(set(vals))}")

# Save results
out = {"full_ic": {}, "recent_ic": {}}
for name in sense_names:
    out["full_ic"][name] = ic_results.get(name, {})

out["btc_price_approx"] = 66893
out["fng"] = 9
out["funding_rate"] = 0.00003405
out["open_interest"] = 90220.096
out["timestamp"] = "2026-04-04 05:25"

with open(os.path.join(os.path.dirname(__file__), "ic_recalc_result.json"), "w") as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to ic_recalc_result.json")

db.close()
