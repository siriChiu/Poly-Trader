#!/usr/bin/env python3
"""Recalculate sensory IC for all 8 senses."""
import os, sys, json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

db_path = os.path.join(os.path.dirname(__file__), "poly_trader.db")
import sqlite3

db = sqlite3.connect(db_path)

# Get features and labels
features = db.execute("SELECT * FROM features_normalized ORDER BY timestamp").fetchall()
columns = [desc[0] for desc in db.execute("SELECT * FROM features_normalized LIMIT 0").description]

labels = db.execute("SELECT timestamp, label FROM labels WHERE label IS NOT NULL ORDER BY timestamp").fetchall()

label_map = {row[0]: row[1] for row in labels}
feat_cols = [c for c in columns if c not in ("id", "timestamp")]

print(f"Total feature rows: {len(features)}")
print(f"Total label rows: {len(labels)}")
print(f"Feature columns: {feat_cols}")

matched_feats = {col: [] for col in feat_cols}
matched_labels = []

for row in features:
    ts = row[columns.index("timestamp")]
    if ts in label_map:
        for j, col in enumerate(feat_cols):
            col_idx = columns.index(col)
            val = row[col_idx]
            if val is not None:
                matched_feats[col].append((ts, float(val)))
        matched_labels.append((ts, label_map[ts]))

from scipy import stats

ics = {}
for col in feat_cols:
    if col not in matched_feats or len(matched_feats[col]) == 0:
        continue
    # Build paired arrays
    lm = {k: v for k, v in matched_feats.items()}
    # Only use timestamps that appear in ALL feature columns
    pass  # handle below differently

# Simpler: build full matrix
ts_to_feats = {}
for row in features:
    ts = row[columns.index("timestamp")]
    ts_to_feats[ts] = {col: row[columns.index(col)] for col in feat_cols}

common_ts = [ts for ts in sorted(ts_to_feats.keys()) if ts in label_map]
print(f"Common timestamps with labels: {len(common_ts)}")

if len(common_ts) == 0:
    print("ERROR: No matching timestamps!")
    sys.exit(1)

# Try to get at least some data
sample_ts = common_ts[:min(10, len(common_ts))]
for ts in sample_ts[:3]:
    print(f"  ts={ts}, label={label_map[ts]}, feats keys: {list(ts_to_feats[ts].keys())[:5]}...")

# Compute IC per feature
for col in feat_cols:
    feat_vals = []
    lab_vals = []
    for ts in common_ts:
        fv = ts_to_feats.get(ts, {}).get(col)
        lv = label_map.get(ts)
        if fv is not None and lv is not None:
            feat_vals.append(float(fv))
            lab_vals.append(float(lv))
    
    if len(feat_vals) < 50:
        ics[col] = {"value": 0, "n": len(feat_vals), "std": 0}
        continue
    
    fa = np.array(feat_vals)
    la = np.array(lab_vals)
    
    if np.std(fa) < 1e-10 or np.std(la) < 1e-10:
        ics[col] = {"value": 0, "n": len(feat_vals), "std": 0}
        continue
    
    try:
        r, p = stats.spearmanr(fa, la)
        ics[col] = {"value": float(r), "n": len(feat_vals), "p": float(p), "std": float(np.std(fa))}
    except Exception as e:
        ics[col] = {"value": None, "n": len(feat_vals), "std": float(np.std(fa)), "error": str(e)}

# Group by sense
sense_names = ["Eye", "Ear", "Nose", "Tongue", "Body", "Pulse", "Aura", "Mind"]
sense_map = {"eye": "Eye", "ear": "Ear", "nose": "Nose", "tongue": "Tongue", 
             "body": "Body", "pulse": "Pulse", "aura": "Aura", "mind": "Mind"}

senses = {name: {"ics": [], "stds": []} for name in sense_names}

for feat, info in ics.items():
    prefix = feat.replace("feat_", "").split("_")[0]
    sense_name = sense_map.get(prefix, None)
    if sense_name and info["value"] is not None:
        senses[sense_name]["ics"].append(info["value"])
        senses[sense_name]["stds"].append(info["std"])
        senses[sense_name]["n"] = info["n"]

print(f"\n{'='*60}")
print(f"Sensory IC Summary (h=4) — N={senses.get('Eye',{}).get('n', 'N/A')}")
print(f"{'='*60}")

for name in sense_names:
    s = senses[name]
    ics_list = s.get("ics", [])
    if ics_list:
        avg = np.mean(ics_list)
        mx = np.max(ics_list)
        mn = np.min(ics_list)
        rng = mx - mn
        count_below = sum(1 for x in ics_list if abs(x) < 0.05)
        print(f"{name:8s}: avg={avg:+.4f} max={mx:+.4f} min={mn:+.4f} avg_std={np.mean(s.get('stds',[0])):.4f} (n={len(ics_list)}, below_005={count_below})")
    else:
        print(f"{name:8s}: no valid IC values")

# Save updated ic_signs
result = {"ic_map": ics, "sensory_summary": {}}
for name in sense_names:
    s = senses[name]
    ics_list = s.get("ics", [])
    if ics_list:
        result["sensory_summary"][name] = {
            "avg": round(float(np.mean(ics_list)), 4),
            "max": round(float(np.max(ics_list)), 4),
            "min": round(float(np.min(ics_list)), 4),
            "count": len(ics_list),
            "below_005": sum(1 for x in ics_list if abs(x) < 0.05)
        }

out_path = os.path.join(os.path.dirname(__file__), "ic_signs_latest.json")
with open(out_path, "w") as f:
    json.dump(result, f, indent=2)
print(f"\nSaved to {out_path}")

db.close()
