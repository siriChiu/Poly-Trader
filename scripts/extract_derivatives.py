#!/usr/bin/env python3
"""Extract latest derivatives data from raw_market_data"""
import sqlite3
import json

db_path = 'poly_trader.db'
conn = sqlite3.connect(db_path)

# Get columns
cols = [d[0] for d in conn.execute('SELECT * FROM raw_market_data LIMIT 1').description]

# Get latest row
r = conn.execute('SELECT * FROM raw_market_data ORDER BY id DESC LIMIT 1').fetchone()

print("Latest raw_market_data:")
for c, v in zip(cols, r):
    print(f"  {c}: {v}")

# Also get latest from features_normalized to check VIX/DXY
fcols = [d[0] for d in conn.execute('SELECT * FROM features_normalized LIMIT 1').description]
f = conn.execute('SELECT * FROM features_normalized ORDER BY id DESC LIMIT 1').fetchone()
print("\nLatest features_normalized:")
for c, v in zip(fcols, f):
    print(f"  {c}: {v}")

# Check labels latest
lcols = [d[0] for d in conn.execute('SELECT * FROM labels LIMIT 1').description]
l = conn.execute('SELECT * FROM labels WHERE label_sell_win IS NOT NULL ORDER BY id DESC LIMIT 1').fetchone()
print("\nLatest labels (with sell_win):")
for c, v in zip(lcols, l):
    print(f"  {c}: {v}")

# Count sell_win stats
stats = conn.execute("SELECT COUNT(*) as total, SUM(label_sell_win) as wins, AVG(label_sell_win) as win_rate FROM labels WHERE label_sell_win IS NOT NULL").fetchone()
print(f"\nLabel stats: total={stats[0]}, wins={stats[1]}, win_rate={stats[2]:.2%}")

conn.close()
