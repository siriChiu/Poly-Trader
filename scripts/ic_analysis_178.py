#!/usr/bin/env python3
"""Deep IC analysis for heartbeat #178 - regime-aware, rolling windows, time-weighted."""
import sqlite3, json, numpy as np
from scipy import stats
from datetime import datetime

db = sqlite3.connect("poly_trader.db")

# Check columns
feats_cols = [d[0] for d in db.execute("SELECT * FROM features_normalized LIMIT 1").description]
labels_cols = [d[0] for d in db.execute("SELECT * FROM labels LIMIT 1").description]
print("Features columns:", feats_cols)
print("Labels columns:", labels_cols)

has_regime = "regime" in labels_cols
print(f"Has regime column: {has_regime}")

# Get features
feats_query = "SELECT timestamp, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, feat_pulse, feat_aura, feat_mind FROM features_normalized ORDER BY timestamp"
feats = db.execute(feats_query).fetchall()

# Get labels
if has_regime:
    labels_query = "SELECT timestamp, label_spot_long_win, label_up, future_return_pct, regime FROM labels ORDER BY timestamp"
else:
    labels_query = "SELECT timestamp, label_spot_long_win, label_up, future_return_pct FROM labels ORDER BY timestamp"
labels_raw = db.execute(labels_query).fetchall()

# Build label map
if has_regime:
    label_map = {r[0]: {"sell_win": r[1], "up": r[2], "ret": r[3], "regime": r[4]} for r in labels_raw}
else:
    label_map = {r[0]: {"sell_win": r[1], "up": r[2], "ret": r[3], "regime": None} for r in labels_raw}

feat_cols = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body", "feat_pulse", "feat_aura", "feat_mind"]
sense_names = ["Eye", "Ear", "Nose", "Tongue", "Body", "Pulse", "Aura", "Mind"]

feat_map = {r[0]: {c: r[1+feat_cols.index(c)] for c in feat_cols} for r in feats}
common = sorted(set(r[0] for r in feats) & set(label_map.keys()))

print(f"\nFeatures rows: {len(feats)}")
print(f"Labels rows: {len(labels_raw)}")
print(f"Common timestamps: {len(common)}")

# Helper
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

# ===== FULL IC (against sell_win) =====
print(f"\n{'='*70}")
print(f"FULL IC — Spearman vs label_spot_long_win (h=4)")
print(f"{'='*70}")
for sn, fn in zip(sense_names, feat_cols):
    ic, n = calc_ic(sn, fn, common, "sell_win")
    if ic is not None:
        status = "PASS" if abs(ic) >= 0.05 else "FAIL"
        print(f"  {sn:8s}: IC={ic:+.4f}  n={n}  [{status}]")
    else:
        print(f"  {sn:8s}: N/A (n={n})")

# ===== FULL IC (against label_up) =====
print(f"\n--- IC vs label_up (direction) ---")
for sn, fn in zip(sense_names, feat_cols):
    ic, n = calc_ic(sn, fn, common, "up")
    if ic is not None:
        status = "PASS" if abs(ic) >= 0.05 else "FAIL"
        print(f"  {sn:8s}: IC={ic:+.4f}  n={n}  [{status}]")

# ===== RECENT WINDOWS =====
for n_val in [500, 1000, 2000, 3000, 5000]:
    window = common[-n_val:] if len(common) > n_val else common
    print(f"\n--- Recent N={len(window)} (vs sell_win) ---")
    for sn, fn in zip(sense_names, feat_cols):
        ic, n = calc_ic(sn, fn, window, "sell_win")
        if ic is not None:
            status = "PASS" if abs(ic) >= 0.05 else "FAIL"
            print(f"  {sn:8s}: IC={ic:+.4f}  [{status}]")

# ===== REGIME-AWARE IC =====
if has_regime:
    for regime in ["Bear", "Bull", "Chop"]:
        regime_ts = [ts for ts in common if label_map.get(ts, {}).get("regime") == regime]
        if len(regime_ts) < 50:
            print(f"\n--- {regime} regime (N={len(regime_ts)}, too few) ---")
            continue
        print(f"\n--- {regime} regime (N={len(regime_ts)}) ---")
        for sn, fn in zip(sense_names, feat_cols):
            ic, n = calc_ic(sn, fn, regime_ts, "sell_win")
            if ic is not None:
                status = "PASS" if abs(ic) >= 0.05 else "FAIL"
                print(f"  {sn:8s}: IC={ic:+.4f}  [{status}]")

# ===== TIME-WEIGHTED IC (exponential decay) =====
print(f"\n--- Time-Weighted IC (exponential decay) ---")
for tau in [50, 100, 200, 500]:
    print(f"\n  tau={tau} (vs sell_win):")
    n_total = len(common)
    weights = np.exp(-np.arange(n_total)[::-1] / tau)
    weights /= weights.sum()
    
    for sn, fn in zip(sense_names, feat_cols):
        pairs = []
        for ts in common:
            fv = feat_map.get(ts, {}).get(fn)
            lv = label_map.get(ts, {}).get("sell_win")
            if fv is not None and lv is not None:
                pairs.append((float(fv), float(lv)))
        
        if len(pairs) < 50:
            continue
        
        fa = np.array([p[0] for p in pairs])
        la = np.array([p[1] for p in pairs])
        
        # Use only recent portion matching tau scale
        n_use = min(len(pairs), tau * 5)
        fa_r = fa[-n_use:]
        la_r = la[-n_use:]
        w_r = weights[-n_use:]
        w_r = w_r / w_r.sum()
        
        # Weighted Spearman approximation (use Pearson on rank-transformed data)
        from scipy.stats import rankdata
        fa_rank = rankdata(fa_r)
        la_rank = rankdata(la_r)
        
        # Weighted Pearson on ranks
        wr_mean = np.average(fa_rank, weights=w_r)
        wl_mean = np.average(la_rank, weights=w_r)
        cov_wl = np.sum(w_r * (fa_rank - wr_mean) * (la_rank - wl_mean))
        var_wf = np.sum(w_r * (fa_rank - wr_mean) ** 2)
        var_wl2 = np.sum(w_r * (la_rank - wl_mean) ** 2)
        
        if var_wf > 0 and var_wl2 > 0:
            ic_r = cov_wl / np.sqrt(var_wf * var_wl2)
            status = "PASS" if abs(ic_r) >= 0.05 else "FAIL"
            print(f"    {sn:8s}: IC={ic_r:+.4f}  [{status}]")

# ===== LABEL DISTRIBUTION =====
sell_win_counts = {}
up_counts = {}
regime_counts = {}
for ts in common:
    lv = label_map[ts]
    sw = int(lv["sell_win"])
    up = int(lv["up"])
    sell_win_counts[sw] = sell_win_counts.get(sw, 0) + 1
    up_counts[up] = up_counts.get(up, 0) + 1
    if has_regime and lv["regime"]:
        r = lv["regime"]
        regime_counts[r] = regime_counts.get(r, 0) + 1

print(f"\nLabel distribution (sell_win): {sell_win_counts}")
print(f"Label distribution (up): {up_counts}")
if regime_counts:
    print(f"Regime distribution: {regime_counts}")

# ===== SAVE RESULTS =====
result = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "raw_count": len(feats),
    "features_count": len(feats),
    "labels_count": len(common),
    "sell_win_rate": sell_win_counts.get(1, 0) / sum(sell_win_counts.values()) if sell_win_counts else 0,
    "pass_count_sell_win": 0,
    "pass_count_up": 0,
}
db.close()

print(f"\n✅ Analysis complete")
