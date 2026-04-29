#!/usr/bin/env python3
"""Update ic_signs.json with correct IC values after timestamp fix."""
import os, json
import sqlite3
import numpy as np
from scipy import stats

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poly_trader.db")
db = sqlite3.connect(db_path)

feel_rows = db.execute("""SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, feat_pulse, feat_aura, feat_mind FROM features_normalized ORDER BY timestamp""").fetchall()
label_rows = db.execute("""SELECT timestamp, label_spot_long_win, label_up FROM labels ORDER BY timestamp""").fetchall()

feel_cols = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body", "feat_pulse", "feat_aura", "feat_mind"]
feel_map = {r[0]: {c: r[1+feel_cols.index(c)] for c in feel_cols} for r in feel_rows}
label_map = {r[0]: {"sw": r[1], "up": r[2]} for r in label_rows}
common = sorted(set(feel_map.keys()) & set(label_map.keys()))

print(f"N={len(common)} matched timestamps")

# IC for each feature column
ic_map = {}
for feat_name in feel_cols:
    f_vals = []
    l_vals = []
    for ts in common:
        fv = feel_map[ts].get(feat_name)
        lv = label_map[ts].get("sw")
        if fv is not None and lv is not None:
            f_vals.append(float(fv))
            l_vals.append(int(lv))
    
    if len(f_vals) < 100:
        continue
    
    fa = np.array(f_vals)
    la = np.array(l_vals)
    if np.std(fa) < 1e-10 or np.std(la) < 1e-10:
        ic_map[feat_name] = 0.0
        continue
    
    try:
        r, p = stats.spearmanr(fa, la)
        ic_map[feat_name] = round(float(r), 6)
    except:
        ic_map[feat_name] = None

# Build sense-level IC (avg across sense column and all lag columns in the DB)
sense_names = ["Eye", "Ear", "Nose", "Tongue", "Body", "Pulse", "Aura", "Mind"]
feat_prefixes = {"Eye": "feat_eye", "Ear": "feat_ear", "Nose": "feat_nose", "Tongue": "feat_tongue",
                  "Body": "feat_body", "Pulse": "feat_pulse", "Aura": "feat_aura", "Mind": "feat_mind"}

neg_feats = []
print("\nSense-level IC (sell_win):")
for name, prefix in feat_prefixes.items():
    val = ic_map.get(prefix)
    if val is not None:
        status = "OK" if abs(val) >= 0.05 else "FAIL"
        print(f"  {name:8s}: IC={val:+.4f} [{status}]")
        if val < 0:
            neg_feats.append(prefix)

recent_ic = {}
recent_ts = common[-5000:]
print(f"\nRecent N={len(recent_ts)} IC (sell_win):")
for name, prefix in feat_prefixes.items():
    f_vals = [float(feel_map[ts].get(prefix, 0)) for ts in recent_ts]
    l_vals = [int(label_map[ts].get("sw", 0)) for ts in recent_ts]
    
    fa = np.array(f_vals)
    la = np.array(l_vals)
    if np.std(fa) < 1e-10 or np.std(la) < 1e-10:
        continue
    
    try:
        r, p = stats.spearmanr(fa, la)
        status = "OK" if abs(r) >= 0.05 else "FAIL"
        print(f"  {name:8s}: IC={r:+.4f} [{status}]")
        recent_ic[name] = round(float(r), 4)
    except:
        pass

# Write ic_signs.json
output = {
    "timestamp": "2026-04-04 05:25",
    "n_matched": len(common),
    "timestamp_fix_applied": True,
    "note": "Timestamps normalized: removed .000000 suffix from features_normalized and raw_market_data",
    "neg_ic_feats": neg_feats,
    "ic_map": {k: v for k, v in ic_map.items() if v is not None},
    "recent_ic": recent_ic,
    "sensory_summary": {
        name: ic_map.get(prefix, None) for name, prefix in feat_prefixes.items()
    }
}

out_path = os.path.join(os.path.dirname(__file__), "ic_signs.json")
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\nUpdated {out_path}")

db.close()
