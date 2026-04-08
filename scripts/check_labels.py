#!/usr/bin/env python
"""Check label quality and distribution."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'poly_trader.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Check label columns
print("=== Label Column Stats ===")
cur.execute('''SELECT 
    COUNT(*) as total,
    AVG(future_return_pct) as avg_ret,
    MIN(future_return_pct) as min_ret,
    MAX(future_return_pct) as max_ret,
    AVG(future_max_drawdown) as avg_dd,
    AVG(future_max_runup) as avg_ru,
    AVG(horizon_minutes) as avg_horizon,
    SUM(CASE WHEN label_up=1 THEN 1 ELSE 0 END) as pos,
    SUM(CASE WHEN label_up=0 THEN 1 ELSE 0 END) as neg,
    SUM(CASE WHEN label_spot_long_win=1 THEN 1 ELSE 0 END) as sellpos,
    SUM(CASE WHEN label_spot_long_win=0 THEN 1 ELSE 0 END) as sellneg
FROM labels''')
row = cur.fetchone()
names = ['total', 'avg_ret', 'min_ret', 'max_ret', 'avg_dd', 'avg_ru', 'avg_horizon', 'pos', 'neg', 'sellpos', 'sellneg']
for n, v in zip(names, row):
    print(f"  {n}: {v}")

# Check label_up vs label_spot_long_win agreement
cur.execute('''SELECT 
    SUM(CASE WHEN label_up=label_spot_long_win THEN 1 ELSE 0 END) as agree,
    SUM(CASE WHEN label_up!=label_spot_long_win THEN 1 ELSE 0 END) as disagree,
    COUNT(*) as total
FROM labels''')
row = cur.fetchone()
print(f"\nLabel agreement: agree={row[0]}, disagree={row[1]}, total={row[2]}")

# If disagree > 0, show samples
if row[1] > 0:
    cur.execute('''SELECT timestamp, future_return_pct, future_max_drawdown, future_max_runup, label_up, label_spot_long_win
    FROM labels WHERE label_up != label_spot_long_win LIMIT 10''')
    for r in cur.fetchall():
        print(f"  {r[0]}: ret={r[1]:.4f}, dd={r[2]:.4f}, ru={r[3]:.4f}, up={r[4]}, sell_win={r[5]}")

# Check regime distribution
cur.execute('''SELECT regime_label, COUNT(*) FROM features_normalized GROUP BY regime_label''')
print(f"\nRegime distribution:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Future return distribution
cur.execute('''SELECT 
    (SELECT COUNT(*) FROM labels WHERE future_return_pct > 0.005) as pos_05,
    (SELECT COUNT(*) FROM labels WHERE future_return_pct < -0.005) as neg_05,
    (SELECT COUNT(*) FROM labels WHERE ABS(future_return_pct) <= 0.005) as near_zero
FROM labels''')
row = cur.fetchone()
print(f"\nFuture return distribution (threshold=0.5%):")
print(f"  > 0.5%: {row[0]}")
print(f"  < -0.5%: {row[1]}")  
print(f"  |ret| <= 0.5%: {row[2]}")

conn.close()
