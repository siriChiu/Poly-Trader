#!/usr/bin/env python3
import sqlite3, numpy as np
conn = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')

# Last 200 labels - verify the 156 streak
rows = conn.execute('SELECT id, timestamp, label_spot_long_win, regime_label, future_return_pct FROM labels ORDER BY id DESC LIMIT 200').fetchall()

# Count zeros from end
consec_0 = 0
for r in rows:
    if r[2] == 0:
        consec_0 += 1
    else:
        break
print(f"Consecutive zeros from end: {consec_0}")

# Find where the streak started
last_win_idx = None
for i, r in enumerate(rows):
    if r[2] == 1:
        last_win_idx = i
        print(f"Last win at position {i} (id={r[0]}, ts={r[1]}, regime={r[3]}, frp={r[4]})")
        break

# In the 156 zeros, what's the future_return_pct distribution?
zero_rows = rows[:consec_0]
frps = [r[4] for r in zero_rows if r[4] is not None]
print(f"\nIn the {consec_0} zeros, future_return_pct:")
frps_arr = np.array(frps, dtype=float)
print(f"  Count: {len(frps_arr)}")
print(f"  Mean: {np.mean(frps_arr):.6f}")
print(f"  Min: {np.min(frps_arr):.6f}")
print(f"  Max: {np.max(frps_arr):.6f}")
print(f"  How many negative (sell wins if label is short): {np.sum(frps_arr < 0)}")
print(f"  How many positive (price went UP): {np.sum(frps_arr > 0)}")
print(f"  Std: {np.std(frps_arr):.6f}")

# What's the threshold for sell_win?
# sell_win=1 when future_return_pct < -threshold (short profit)
print(f"\nZero sell_win but future_return_pct distribution:")
neg_frps = frps_arr[frps_arr < 0]
pos_frps = frps_arr[frps_arr > 0]
print(f"  Negative frp count: {len(neg_frps)} (should have been sell_win=1)")
print(f"  Positive frp count: {len(pos_frps)} (correctly sell_win=0)")
if len(neg_frps) > 0:
    print(f"  Negative frp mean: {np.mean(neg_frps):.6f}")
    print(f"  Most negative: {np.min(neg_frps):.6f}")
    print(f"  Count with frp < -0.005: {np.sum(neg_frps < -0.005)}")

# Check the actual sell_win label definition in labeling.py
# sell_win_label = 1 if frp < -sell_threshold (short profit)
# With threshold = 0.005 (0.5%), frp < -0.005 → sell_win=1
# So frp > -0.005 → sell_win=0

# If sell_win=0 and frp > 0, price went UP → good (no short taken)
# If sell_win=0 and frp is small negative (>-0.005), price went down but not enough
# If sell_win=0 and frp is strongly negative (<-0.005), this would be a LABELING BUG

strong_neg = frps_arr[frps_arr < -0.005]
if len(strong_neg) > 0:
    print(f"\n  🚨 {len(strong_neg)} rows with frp < -0.5% but sell_win=0 — possible labeling issue")
else:
    print(f"\n  No mislabeled rows (all negative frp > -0.5%)")

# What's the regime distribution in the streak?
from collections import Counter
regimes = [r[3] or 'NULL' for r in zero_rows]
print(f"\nRegime distribution in {consec_0}-row streak: {dict(Counter(regimes))}")

conn.close()
