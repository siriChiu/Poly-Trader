"""Investigate the 151 ALL-ZERO sell_win labels on 2026-04-04."""
import sqlite3

conn = sqlite3.connect("poly_trader.db")
cur = conn.cursor()

# Check the distribution of returns for 2026-04-04 labels
cur.execute("""
    SELECT future_return_pct, label_spot_long_win, timestamp
    FROM labels
    WHERE timestamp >= '2026-04-04' AND timestamp < '2026-04-05'
    ORDER BY timestamp
    LIMIT 20
""")
print("=== First 20 labels from 2026-04-04 ===")
for r in cur.fetchall():
    print(f"  ts={r[2]} | ret={r[0]:.6f} | sell_win={r[1]}")

# Stats for April 4th labels
cur.execute("""
    SELECT 
        COUNT(*) as total,
        MIN(future_return_pct) as min_ret,
        MAX(future_return_pct) as max_ret,
        AVG(future_return_pct) as avg_ret,
        AVG(CAST(label_spot_long_win AS FLOAT)) as avg_sell_win
    FROM labels
    WHERE timestamp >= '2026-04-04' AND timestamp < '2026-04-05'
""")
r = cur.fetchone()
print(f"\n=== April 4 stats ===")
print(f"  Total labels: {r[0]}")
print(f"  Min return: {r[1]:.6f}")
print(f"  Max return: {r[2]:.6f}")
print(f"  Avg return: {r[3]:.6f}")
print(f"  Avg sell_win: {r[4]:.3f}")

# Compare to previous days (April 1-3)
cur.execute("""
    SELECT 
        COUNT(*) as total,
        MIN(future_return_pct) as min_ret,
        MAX(future_return_pct) as max_ret,
        AVG(future_return_pct) as avg_ret,
        AVG(CAST(label_spot_long_win AS FLOAT)) as avg_sell_win
    FROM labels
    WHERE timestamp >= '2026-04-01' AND timestamp < '2026-04-04'
""")
r = cur.fetchone()
print(f"\n=== April 1-3 stats ===")
print(f"  Total labels: {r[0]}")
print(f"  Min return: {r[1]:.6f}")
print(f"  Max return: {r[2]:.6f}")
print(f"  Avg return: {r[3]:.6f}")
print(f"  Avg sell_win: {r[4]:.3f}")

# Check if these new labels have proper regime assignments
cur.execute("""
    SELECT f.regime_label, AVG(CAST(l.label_spot_long_win AS FLOAT)), COUNT(*)
    FROM labels l
    LEFT JOIN features_normalized f ON l.timestamp = f.timestamp
    WHERE l.timestamp >= '2026-04-04' AND l.timestamp < '2026-04-05'
    GROUP BY f.regime_label
""")
print(f"\n=== April 4 by regime ===")
for r in cur.fetchall():
    print(f"  regime={r[0]}: sell_win={r[1]:.3f}, count={r[2]}")

conn.close()
