#!/usr/bin/env python3
"""Heartbeat #232 — Streak analysis + model check"""
import sqlite3, json, math
from pathlib import Path

ROOT = Path(__file__).parent.parent
db = sqlite3.connect(str(ROOT / "poly_trader.db"))

# Detailed streak analysis
labels = db.execute("SELECT id, timestamp, label_spot_long_win, future_return_pct, regime_label FROM labels ORDER BY id").fetchall()
print(f"Total labels: {len(labels)}")

# Full streak analysis from the most recent end
streak_data = []
current_streak = 0
is_loss_streak = True
streaks = []  # list of (type, length, start_id, end_id)
start_id = None

for row in reversed(labels):
    rid, ts, sw, frp, regime = row
    if sw is None or math.isnan(sw):
        continue
    is_win = bool(sw)
    
    if is_loss_streak:
        if not is_win:
            current_streak += 1
        else:
            if current_streak > 0:
                streaks.append(('loss', current_streak))
            is_loss_streak = False
            current_streak = 1
    else:
        if is_win:
            current_streak += 1
        else:
            streaks.append(('win', current_streak))
            is_loss_streak = True
            current_streak = 1

if current_streak > 0:
    streaks.append(('loss' if is_loss_streak else 'win', current_streak))

print(f"\n=== Last 10 streaks ===")
for typ, length in streaks[:10]:
    print(f"  {typ} streak: {length}")

# Recent 50, 100, 200 win rates
recent = [l for l in labels if l[2] is not None and not math.isnan(l[2])]
for window in [50, 100, 200, 500, 1000]:
    subset = recent[-window:]
    if subset:
        wr = sum(l[2] for l in subset) / len(subset)
        print(f"\n  Last {window}: {len(subset)} labels, win_rate={wr:.4f} ({wr*100:.1f}%)")

# Max drawdown analysis
max_dd = db.execute("SELECT AVG(future_max_drawdown) FROM labels WHERE future_max_drawdown IS NOT NULL").fetchone()
max_ru = db.execute("SELECT AVG(future_max_runup) FROM labels WHERE future_max_runup IS NOT NULL").fetchone()
print(f"\nAvg max drawdown: {max_dd[0]:.4f}" if max_dd else "N/A")
print(f"Avg max runup: {max_ru[0]:.4f}" if max_ru else "N/A")

# Model metrics history
metrics = db.execute("SELECT timestamp, cv_accuracy, cv_std, n_features, notes FROM model_metrics ORDER BY id DESC LIMIT 10").fetchall()
print(f"\n=== Model Metrics (last 10) ===")
for m in metrics:
    print(f"  {m[0][:19]} | CV={m[1]:.4f} ± {m[2]:.4f} | n={m[3]} | {m[4]}")

# Check feature distribution shift between first 1000 and last 1000
feat_cols = ['feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind']
all_feats = db.execute(f"SELECT {','.join(feat_cols)} FROM features_normalized ORDER BY id").fetchall()
n_feats = len(all_feats)
print(f"\n=== Feature distribution shift (first 1000 vs last 1000 of {n_feats}) ===")
for i, col_name in enumerate(feat_cols):
    early = [r[i] for r in all_feats[:1000] if r[i] is not None and not math.isnan(r[i])]
    late = [r[i] for r in all_feats[-1000:] if r[i] is not None and not math.isnan(r[i])]
    if early and late:
        e_mean = sum(early) / len(early)
        l_mean = sum(late) / len(late)
        print(f"  {col_name:20s}: early_mean={e_mean:.4f} → late_mean={l_mean:.4f} (Δ={l_mean - e_mean:+.4f})")

db.close()
