#!/usr/bin/env python3
"""Check for consecutive loss streaks and threshold artifacts (P0 #H390)."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "poly_trader.db"
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

# Get labels ordered by timestamp
rows = conn.execute("""
    SELECT timestamp, label_spot_long_win, future_return_pct, horizon_minutes,
           regime_label, label_up
    FROM labels
    WHERE label_spot_long_win IS NOT NULL
    ORDER BY timestamp
""").fetchall()

print(f"Total labels: {len(rows)}")

# Find the longest loss streak (consecutive 0s in label_spot_long_win)
max_streak = 0
max_start = 0
max_end = 0
current_streak = 0
current_start = 0
# Also find the longest win streak
max_win_streak = 0
win_start = 0
win_end = 0
current_win_streak = 0
current_win_start = 0

for i, row in enumerate(rows):
    if row['label_spot_long_win'] == 0:
        if current_streak == 0:
            current_start = i
        current_streak += 1
        if current_streak > max_streak:
            max_streak = current_streak
            max_start = current_start
            max_end = i
    else:
        current_streak = 0

    if row['label_spot_long_win'] == 1:
        if current_win_streak == 0:
            current_win_start = i
        current_win_streak += 1
        if current_win_streak > max_win_streak:
            max_win_streak = current_win_streak
            win_start = current_win_start
            win_end = i
    else:
        current_win_streak = 0

print(f"\nLongest LOSS streak: {max_streak} (#{max_start} to #{max_end})")
print(f"  Start: {rows[max_start][0]}")
print(f"  End:   {rows[max_end][0]}")

print(f"\nLongest WIN streak: {max_win_streak} (#{win_start} to #{win_end})")
print(f"  Start: {rows[win_start][0]}")
print(f"  End:   {rows[win_end][0]}")

# Check the recent tail (last 300 rows) for current streak momentum
recent_losses = 0
for i in range(len(rows)-1, -1, -1):
    if rows[i]['label_spot_long_win'] == 0:
        recent_losses += 1
    else:
        break

recent_wins = 0
for i in range(len(rows)-1, -1, -1):
    if rows[i]['label_spot_long_win'] == 1:
        recent_wins += 1
    else:
        break

print(f"\nCurrent tail: last {recent_losses} are losses, last {recent_wins} are wins")

# Check distribution by regime
print("\n=== Recent (last 500 rows) ===")
recent = rows[-500:]
sell_wins = sum(1 for r in recent if r['label_spot_long_win'] == 1)
sell_losses = sum(1 for r in recent if r['label_spot_long_win'] == 0)
print(f"  Win rate: {sell_wins}/{sell_wins+sell_losses} = {sell_wins/(sell_wins+sell_losses):.4f}")

# Check regime distribution in recent rows
regime_counts = {}
regime_wins = {}
for r in recent:
    regime = r['regime_label'] or 'unknown'
    regime_counts[regime] = regime_counts.get(regime, 0) + 1
    if r['label_spot_long_win'] == 1:
        regime_wins[regime] = regime_wins.get(regime, 0) + 1

print(f"  Regimes: {regime_counts}")
for regime in regime_counts:
    w = regime_wins.get(regime, 0)
    total = regime_counts[regime]
    print(f"    {regime}: {w}/{total} = {w/total:.4f}" if total > 0 else f"    {regime}: 0/{total}")

# Check future_return_pct distribution
frps = [r['future_return_pct'] for r in rows if r['future_return_pct'] is not None]
print(f"\nfuture_return_pct stats:")
print(f"  Count: {len(frps)}")
print(f"  Min: {min(frps):.6f}")
print(f"  Max: {max(frps):.6f}")
print(f"  Mean: {sum(frps)/len(frps):.6f}")

# Check the actual threshold used
zero_count = sum(1 for r in frps if abs(r) < 0.0005)
print(f"  Near-zero (< 0.05%): {zero_count} ({zero_count/len(frps)*100:.1f}%)")

# Check horizon_minutes distribution
hms = [r['horizon_minutes'] for r in rows if r['horizon_minutes'] is not None]
if hms:
    print(f"\nhorizon_minutes stats:")
    print(f"  Unique values: {set(hms)}")
    print(f"  Most common: {max(set(hms), key=hms.count)}")

conn.close()
