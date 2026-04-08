#!/usr/bin/env python3
"""Check label threshold behavior - the key 156-loss streak root cause.

This is a diagnostic script. Run standalone: python scripts/check_label_threshold.py
"""
import sqlite3
import numpy as np

db = '/home/kazuha/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(db)
c = conn.cursor()

# Check label_spot_long_win distribution and future_return stats
try:
    stats = c.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN label_spot_long_win = 1 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN label_spot_long_win = 0 THEN 1 ELSE 0 END) as losses,
            AVG(future_return_pct) as avg_ret,
            MIN(future_return_pct) as min_ret,
            MAX(future_return_pct) as max_ret
        FROM labels 
        WHERE label_spot_long_win IS NOT NULL
    """).fetchone()
    print(f"Labels: total={stats[0]}, wins={stats[1]}, losses={stats[2]}")
    print(f"  return: mean={stats[3]:.6f}, min={stats[4]:.6f}, max={stats[5]:.6f}")
except Exception as e:
    print(f"Label stats error: {e}")
    stats = None

# Check how many returns are very small - these are near-threshold
rows = c.execute("SELECT future_return_pct FROM labels WHERE label_spot_long_win IS NOT NULL").fetchall()
ret_vals = np.array([r[0] for r in rows if r[0] is not None], dtype=float)

print(f"\nTotal return values: {len(ret_vals)}")

conn.close()
