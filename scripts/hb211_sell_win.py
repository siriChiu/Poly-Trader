#!/usr/bin/env python3
"""Deep dive into sell_win = 0 streak."""
import sqlite3
conn = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')
conn.row_factory = sqlite3.Row

# Examine sell_win distribution in last 200 labels
rows = conn.execute('SELECT id, timestamp, label_spot_long_win, regime_label FROM labels ORDER BY id DESC LIMIT 200').fetchall()

# Check what values exist
vals = [r['label_spot_long_win'] for r in rows]
print(f"Last 200 sell_win values:")
print(f"  Unique values sorted: {sorted(set(vals))}")
print(f"  Mean: {sum([v for v in vals if v is not None])/len([v for v in vals if v is not None]):.3f}")

# Find last occurrence of sell_win=1
last_1_idx = None
for i, v in enumerate(vals):
    if v == 1.0:
        last_1_idx = i
        break
if last_1_idx is not None:
    last_1_row = rows[last_1_idx]
    print(f"  Last sell_win=1 at position {last_1_idx} from end (id={last_1_row['id']}, ts={last_1_row['timestamp']})")
else:
    print(f"  NO sell_win=1 found in last 200!")

# What about in last 1000?
rows1000 = conn.execute('SELECT id, timestamp, label_spot_long_win FROM labels ORDER BY id DESC LIMIT 1000').fetchall()
vals1000 = [r['label_spot_long_win'] for r in rows1000]
wins1000 = sum(1 for v in vals1000 if v == 1.0)
print(f"\n  Last 1000: {wins1000} wins out of {len(vals1000)} ({wins1000/len(vals1000)*100:.1f}%)")

# Find ALL positions of sell_win=1 in last 1000
win_positions = []
for i, v in enumerate(vals1000):
    if v == 1.0:
        win_positions.append((i, rows1000[i]['id'], rows1000[i]['timestamp']))

if win_positions:
    print(f"\n  Recent wins (positions from end):")
    for pos, wid, wts in win_positions[:10]:
        print(f"    pos={pos}, id={wid}, ts={wts}")

# What is label_spot_long_win definition?
# Check a few recent labels where sell_win=1
if win_positions:
    for pos, wid, wts in win_positions[:3]:
        row = conn.execute('SELECT l.*, f.feat_eye, f.feat_mind FROM labels l LEFT JOIN features_normalized f ON f.timestamp = l.timestamp WHERE l.id = ?', (wid,)).fetchone()
        if row and row['feat_mind'] is not None:
            print(f"\n  Win example id={wid}: sell_win={row['label_spot_long_win']}, mind={row['feat_mind']:.4f}, eye={row['feat_eye']:.4f}")
            print(f"    future_return_pct={row['future_return_pct']}, max_drawdown={row['future_max_drawdown']}, max_runup={row['future_max_runup']}")

# Check the last label's sell_win and surrounding context
last = conn.execute('SELECT * FROM labels ORDER BY id DESC LIMIT 1').fetchone()
print(f"\n  Last label (id={last['id']}): sell_win={last['label_spot_long_win']}, return_pct={last['future_return_pct']}, drawdown={last['future_max_drawdown']}, runup={last['future_max_runup']}")

conn.close()
