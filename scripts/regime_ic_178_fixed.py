#!/usr/bin/env python3
"""Deep IC analysis for heartbeat #178 - regime-aware, rolling windows, time-weighted."""
import sqlite3, json, numpy as np
from scipy import stats
from datetime import datetime

db = sqlite3.connect("/home/kazuha/Poly-Trader/poly_trader.db")

# Features
feats = db.execute("SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, feat_pulse, feat_aura, feat_mind, regime_label FROM features_normalized ORDER BY timestamp").fetchall()

# Labels  
labels_raw = db.execute("SELECT timestamp, label_sell_win, label_up, future_return_pct FROM labels ORDER BY timestamp").fetchall()

label_map = {r[0]: {"sell_win": r[1], "up": r[2], "ret": r[3]} for r in labels_raw}
feat_cols = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body", "feat_pulse", "feat_aura", "feat_mind"]
sense_names = ["Eye", "Ear", "Nose", "Tongue", "Body", "Pulse", "Aura", "Mind"]
feat_map = {r[0]: {c: r[1+feat_cols.index(c)] for c in feat_cols} for r in feats}
common = sorted(set(r[0] for r in feats) & set(label_map.keys()))

# Regime from features
regime_from_feats = {r[0]: r[9] for r in feats}  # index 9 is regime_label

print(f"Features rows: {len(feats)}")
print(f"Labels rows: {len(labels_raw)}")
print(f"Common timestamps: {len(common)}")

def calc_ic(sense_name, feat_name, timestamps, label_key="sell_win"):
    f_vals, l_vals = [], []
    for ts in timestamps:
        fv = feat_map.get(ts, {}).get(feat_name)
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

# ===== REGIME-AWARE IC =====
print(f"\n{'='*70}")
print(f"REGIME-AWARE IC (vs sell_win, h=4)")
print(f"{'='*70}")
for regime_name in ["bear", "bull", "chop", "neutral"]:
    regime_ts = [ts for ts in common if regime_from_feats.get(ts) == regime_name]
    if len(regime_ts) < 50:
        print(f"\n--- {regime_name.title()} (N={len(regime_ts)}, too few) ---")
        passed = 0
        for sn, fn in zip(sense_names, feat_cols):
            ic, n = calc_ic(sn, fn, regime_ts, "sell_win")
            passed += (1 if ic is not None and abs(ic) >= 0.05 else 0)
        print(f"  Regime {regime_name.title()}: {passed}/8 passed")
        continue
    print(f"\n--- {regime_name.title()} (N={len(regime_ts)}) ---")
    passed = 0
    passed_senses = []
    for sn, fn in zip(sense_names, feat_cols):
        ic, n = calc_ic(sn, fn, regime_ts, "sell_win")
        if ic is not None:
            status = "PASS" if abs(ic) >= 0.05 else "FAIL"
            if abs(ic) >= 0.05:
                passed += 1
                passed_senses.append(sn)
            print(f"  {sn:8s}: IC={ic:+.4f}  [{status}]")
    print(f"  >> {regime_name.title()}: {passed}/8 passed ({', '.join(passed_senses) if passed_senses else 'none'})")

db.close()
