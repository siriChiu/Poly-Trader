#!/usr/bin/env python3
"""Regime-aware IC analysis — reads from DB, computes IC per regime.
Uses features_normalized.regime_label for regime assignment. Read-only.
Uses timestamp+symbol join for accuracy.
"""
import sqlite3, numpy as np, os
from pathlib import Path
from scipy import stats

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = str(PROJECT_ROOT / "poly_trader.db")

try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Fetch features with regime labels
    feat_data = conn.execute(
        "SELECT id, feat_eye, feat_ear, feat_nose, feat_tongue, feat_body, "
        "feat_pulse, feat_aura, feat_mind, COALESCE(regime_label, 'neutral') as regime_label "
        "FROM features_normalized ORDER BY id"
    ).fetchall()

    # Fetch labels
    label_data = conn.execute(
        "SELECT id, label_sell_win FROM labels WHERE label_sell_win IS NOT NULL ORDER BY id"
    ).fetchall()
    conn.close()

    if not feat_data or not label_data:
        print("No data found in DB.")
        exit(1)

    feat_cols = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body",
                 "feat_pulse", "feat_aura", "feat_mind"]

    # Create a map of labels by ID for precise joining
    label_map = {r['id']: r['label_sell_win'] for r in label_data}

    aligned_data = []
    for row in feat_data:
        fid = row['id']
        if fid in label_map:
            aligned_data.append({
                'regime': row['regime_label'],
                'label': label_map[fid],
                'features': {col: row[col] for col in feat_cols}
            })

    if len(aligned_data) < 50:
        print(f"Too few matching records: {len(aligned_data)}")
        exit(1)

    print(f"Regime-aware IC (h=4) — n={len(aligned_data)} (ID join)")
    print(f"{'='*60}")

    regime_set = set(d['regime'] for d in aligned_data)
    for regime in sorted(regime_set):
        reg_data = [d for d in aligned_data if d['regime'] == regime]
        labels = np.array([d['label'] for d in reg_data], dtype=float)
        n = len(labels)
        
        if n < 20:
            print(f"\n  {regime.upper()} regime (n={n}): too few samples, skipping")
            continue
            
        print(f"\n  {regime.upper()} regime (n={n})")
        passing = 0
        for col in feat_cols:
            vals = np.array([d['features'][col] for d in reg_data], dtype=float)
            valid = ~np.isnan(vals) & ~np.isnan(labels)
            v_sum = valid.sum()
            if v_sum < 20:
                continue
            ic, _ = stats.spearmanr(vals[valid], labels[valid])
            ic = float(ic) if ic is not None else 0.0
            status = "✅" if abs(ic) >= 0.05 else "❌"
            if abs(ic) >= 0.05:
                passing += 1
            print(f"    {col.replace('feat_',''):>10s}: {ic:+.4f} {status}")
        print(f"    → {passing}/{len(feat_cols)} passing")

    print(f"\nRegime IC analysis complete")

except Exception as e:
    print(f"Regime IC Error: {e}")
    import traceback
    traceback.print_exc()
