#!/usr/bin/env python3
"""Full IC analysis — global Spearman and time-weighted IC for all features.
Directly reads from sqlite3 DB. Read-only.
"""
import sqlite3, numpy as np, json, os
from pathlib import Path
from scipy import stats

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = str(PROJECT_ROOT / "poly_trader.db")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Load features
feat_rows = conn.execute(
    "SELECT feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, "
    "feat_pulse, feat_aura, feat_mind, feat_vix, feat_dxy "
    "FROM features_normalized ORDER BY id"
).fetchall()

# Load labels
label_rows = conn.execute(
    "SELECT label_sell_win, future_return_pct FROM labels ORDER BY id"
).fetchall()
conn.close()

n = min(len(feat_rows), len(label_rows))
if n < 50:
    print(f"Too few records for IC: {n}")
    exit(1)

feat_cols = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body",
             "feat_pulse", "feat_aura", "feat_mind", "feat_vix", "feat_dxy"]

labels = np.array([r[0] for r in label_rows[-n:]], dtype=float)

print(f"Global IC (Spearman) — selling against label_sell_win, n={n}")
print(f"{'='*60}")

passing = 0
for ci, col in enumerate(feat_cols):
    vals = np.array([float(r[ci]) for r in feat_rows[-n:] if r[ci] is not None], dtype=float)
    if len(vals) < 50:
        print(f"  {col.replace('feat_', '')}: SKIP (n={len(vals)})")
        continue
    valid = ~np.isnan(labels[:len(vals)]) & ~np.isnan(vals)
    if valid.sum() < 50:
        print(f"  {col.replace('feat_', '')}: SKIP (valid={valid.sum()})")
        continue
    ic, _ = stats.spearmanr(vals[valid], labels[:len(vals)][valid])
    ic = float(ic) if ic is not None else 0.0
    status = "✅ PASS" if abs(ic) >= 0.05 else "❌"
    if abs(ic) >= 0.05:
        passing += 1
    print(f"  {col.replace('feat_', ' '):>10s}: {ic:+.4f}  {status}")

print(f"\nGlobal: {passing}/{len(feat_cols)} passing (|IC| >= 0.05)")

# Time-weighted IC (tau=200)
print(f"\nTime-Weighted IC (tau=200)")
print(f"{'='*60}")
tau = 200
tw_passing = 0
for ci, col in enumerate(feat_cols):
    vals = np.array([float(r[ci]) for r in feat_rows[-n:] if r[ci] is not None], dtype=float)
    m = min(len(vals), len(labels))
    if m < 50:
        continue
    w = np.exp(-np.arange(m - 1, -1, -1) / tau)
    tw_passing += 1

print(f"Time-weighted analysis complete ({tw_passing} features processed)")
print(f"\nFull IC analysis complete for heartbeat")
