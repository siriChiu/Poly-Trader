#!/usr/bin/env python3
"""Check label_spot_long_win actual distribution and verify labeling pipeline."""
import sqlite3
conn = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')
conn.row_factory = sqlite3.Row

# Distribution of label_spot_long_win
rows = conn.execute("SELECT label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL").fetchall()
vals = [r[0] for r in rows]

# Check if binary
unique_vals = sorted(set(vals[:10000]))
print(f"Unique values in first 10K: {unique_vals[:20]}...")

# Count exact 0 and 1
zeros = sum(1 for v in vals if v == 0.0)
ones = sum(1 for v in vals if v == 1.0)
print(f"Exact zeros: {zeros}, Exact ones: {ones}, Total: {len(vals)}")

# Value ranges
print(f"Min: {min(vals)}, Max: {max(vals)}")
print(f"Mean: {sum(vals)/len(vals):.6f}")

# Values > 0.5 (should be 'wins')
above_05 = sum(1 for v in vals if v > 0.5)
print(f"Values > 0.5: {above_05} / {len(vals)}")

# Values > 0.01
above_01 = sum(1 for v in vals if v > 0.01)
print(f"Values > 0.01: {above_01} / {len(vals)}")

# Check if it's actually returns
print(f"\nSample values:")
samples = conn.execute("SELECT id, label_spot_long_win, future_return_pct, label_up FROM labels ORDER BY RANDOM() LIMIT 5").fetchall()
for s in samples:
    print(f"  id={s[0]} sell_win={s[1]:.8f} frp={s[2]} label_up={s[3]}")

conn.close()
