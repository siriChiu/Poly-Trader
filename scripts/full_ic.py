#!/usr/bin/env python3
"""Full IC analysis v4 — proper timestamp-based join with global Spearman and TW-IC.
P0#2: null_count + ic_status
P0#3: Fixed TW-IC and proper JOIN
Usage: python scripts/full_ic.py
"""
import sqlite3, numpy as np, json, os
from pathlib import Path
from scipy import stats
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = str(PROJECT_ROOT / "poly_trader.db")
TAU = 200

conn = sqlite3.connect(DB_PATH)

# Core features to analyze
core_names = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body",
              "feat_pulse", "feat_aura", "feat_mind", "feat_vix", "feat_dxy",
              "feat_rsi14", "feat_macd_hist", "feat_atr_pct", "feat_vwap_dev", "feat_bb_pct_b"]

# Check which columns exist
existing_cols = []
for c in core_names:
    try:
        conn.execute(f"SELECT {c} FROM features_normalized LIMIT 1").fetchone()
        existing_cols.append(c)
    except Exception:
        pass

print(f"Full IC v4 — proper JOIN (timestamp + symbol), {len(existing_cols)} features")
print(f"{'='*70}")

# Proper JOIN on timestamp + symbol
select = ", ".join([f"f.{c}" for c in existing_cols])
query = f"""
    SELECT {select}, l.label_sell_win
    FROM features_normalized f
    INNER JOIN labels l ON f.timestamp = l.timestamp AND f.symbol = l.symbol
    WHERE l.label_sell_win IS NOT NULL
    ORDER BY f.timestamp
"""
rows = conn.execute(query).fetchall()
conn.close()

n = len(rows)
if n < 50:
    print(f"Too few records after JOIN: {n}")
    exit(1)

print(f"Joined rows: {n}")

# Extract arrays
label_idx = len(existing_cols)  # label_sell_win is last column
labels = np.array([r[label_idx] for r in rows], dtype=float)

feat_cols = existing_cols
passing = 0
null_counts = {}
ic_global = {}
ic_tw = {}
ic_status = {}

for ci, col in enumerate(feat_cols):
    vals = np.array([float(r[ci]) if r[ci] is not None else np.nan for r in rows], dtype=float)
    nn = int(np.sum(~np.isnan(vals)))
    null_counts[col] = nn

    # Classify status (P0#2)
    if nn == 0:
        ic_status[col] = "NO_DATA"
        ic_global[col] = 0.0
        ic_tw[col] = 0.0
        print(f"  {col.replace('feat_', ' '):>15s}: N/A  ⚪ NO_DATA")
        continue
    if nn < n * 0.1:
        ic_status[col] = f"LOW({nn}/{n})"
        ic_global[col] = 0.0
        ic_tw[col] = 0.0
        print(f"  {col.replace('feat_', ' '):>15s}: N/A  ⚡ LOW ({nn}/{n})")
        continue

    # Valid mask
    valid = ~np.isnan(labels) & ~np.isnan(vals)
    if valid.sum() < 50:
        ic_global[col] = 0.0
        ic_tw[col] = 0.0
        ic_status[col] = "FAIL(n<50)"
        print(f"  {col.replace('feat_', ' '):>15s}: SKIP (valid={valid.sum()})")
        continue

    # Global Spearman IC
    ic_g, _ = stats.spearmanr(vals[valid], labels[valid])
    ic_g = float(ic_g) if ic_g is not None else 0.0
    ic_global[col] = ic_g

    # TW-IC: weighted Pearson correlation (tau=200)
    v_vals = vals[valid]
    l_vals = labels[valid]
    m = len(v_vals)
    weights = np.exp(-(m - 1 - np.arange(m)) / TAU)
    wm_v = np.average(v_vals, weights=weights)
    wm_l = np.average(l_vals, weights=weights)
    cov = np.average((v_vals - wm_v) * (l_vals - wm_l), weights=weights)
    var_v = np.average((v_vals - wm_v) ** 2, weights=weights)
    var_l = np.average((l_vals - wm_l) ** 2, weights=weights)
    tw = cov / (np.sqrt(var_v * var_l) + 1e-15) if var_v > 0 and var_l > 0 else 0.0
    ic_tw[col] = tw

    # Pass/fail based on global IC
    if abs(ic_g) >= 0.05:
        ic_status[col] = "PASS"
        passing += 1
        status_icon = "✅"
    else:
        ic_status[col] = "FAIL"
        status_icon = "❌"

    delta = tw - ic_g
    print(f"  {col.replace('feat_', ' '):>15s}: Global={ic_g:+.4f} | TW={tw:+.4f} (Δ={delta:+.4f}) {status_icon}")

print(f"\nGlobal: {passing}/{len(feat_cols)} passing (|IC| >= 0.05)")
no_data = [c for c, s in ic_status.items() if s == "NO_DATA"]
if no_data:
    print(f"No Data: {', '.join(no_data[:8])}")
low = [c for c, s in ic_status.items() if "LOW" in s]
if low:
    print(f"Low Data: {', '.join(low[:8])}")

# Save
os.makedirs(PROJECT_ROOT / "model", exist_ok=True)
with open(PROJECT_ROOT / "model" / "ic_signs.json", "w") as f:
    json.dump({
        "ic_global": ic_global,
        "ic_tw": ic_tw,
        "null_counts": null_counts,
        "ic_status": ic_status,
        "total_samples": n,
        "target": "label_sell_win",
        "core_ic_summary": {c: round(ic_global.get(c, 0), 4) for c in feat_cols},
        "tw_ic_summary": {c: round(ic_tw.get(c, 0), 4) for c in feat_cols},
    }, f, indent=2, ensure_ascii=False)

print(f"\nSaved ic_signs.json (n={n}) — {datetime.utcnow().strftime('%H:%M:%S')}")
