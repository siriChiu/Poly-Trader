#!/usr/bin/env python3
"""Regime-aware IC analysis for heartbeat #178."""
import sqlite3, numpy as np
from scipy import stats

db = sqlite3.connect("poly_trader.db")

feats = db.execute("SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, feat_pulse, feat_aura, feat_mind FROM features_normalized ORDER BY timestamp").fetchall()
labels_raw = db.execute("SELECT timestamp, label_sell_win, label_up, future_return_pct, regime_label FROM labels ORDER BY timestamp").fetchall()

label_map = {r[0]: {"sell_win": r[1], "up": r[2], "ret": r[3], "regime": r[4]} for r in labels_raw}
feat_cols = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body", "feat_pulse", "feat_aura", "feat_mind"]
sense_names = ["Eye", "Ear", "Nose", "Tongue", "Body", "Pulse", "Aura", "Mind"]
feat_map = {r[0]: {c: r[1+feat_cols.index(c)] for c in feat_cols} for r in feats}
common = sorted(set(r[0] for r in feats) & set(label_map.keys()))

def calc_ic(fn, timestamps, label_key="sell_win"):
    f_vals, l_vals = [], []
    for ts in timestamps:
        fv = feat_map.get(ts, {}).get(fn)
        lv = label_map.get(ts, {}).get(label_key)
        if fv is not None and lv is not None:
            f_vals.append(float(fv))
            l_vals.append(float(lv))
    if len(f_vals) < 50:
        return None, len(f_vals)
    fa, la = np.array(f_vals), np.array(l_vals)
    if np.std(fa) < 1e-10 or np.std(la) < 1e-10:
        return 0.0, len(f_vals)
    try:
        r, _ = stats.spearmanr(fa, la)
        return float(r), len(f_vals)
    except:
        return None, len(f_vals)

# Collect regime assignments
regime_map = {}
for ts in common:
    r = label_map.get(ts, {}).get("regime")
    if r:
        regime_map[ts] = r

regime_ts = {"Bear": [], "Bull": [], "Chop": []}
for ts in common:
    r = regime_map.get(ts, "Chop")
    if r in regime_ts:
        regime_ts[r].append(ts)

print("Regime-aware IC (vs sell_win)")
print("=" * 60)
for regime_name in ["Bear", "Bull", "Chop"]:
    ts_list = regime_ts[regime_name]
    print(f"\n--- {regime_name} (N={len(ts_list)}) ---")
    for sn, fn in zip(sense_names, feat_cols):
        ic, n = calc_ic(fn, ts_list, "sell_win")
        if ic is not None:
            status = "PASS" if abs(ic) >= 0.05 else "FAIL"
            print(f"  {sn:8s}: IC={ic:+.4f}  [{status}]")

print("\nRegime distribution:", {k: len(v) for k, v in regime_ts.items()})
db.close()
