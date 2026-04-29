#!/usr/bin/env python3
"""Investigate DB schema"""
import sqlite3
conn = sqlite3.connect('/home/kazuha/Poly-Trader/data/poly_trader.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:", tables)
for t in tables:
    tname = t[0]
    cursor.execute(f"PRAGMA table_info({tname})")
    cols = cursor.fetchall()
    print(f"\n  {tname}:")
    for c in cols:
        print(f"    {c[1]} ({c[2]})")
    cursor.execute(f"SELECT COUNT(*) FROM {tname}")
    print(f"    rows: {cursor.fetchone()[0]}")

# Check if features are in raw table
if 'raw_market_data' in [t[0] for t in tables]:
    cursor.execute("SELECT * FROM raw_market_data LIMIT 3")
    rows = cursor.fetchall()
    print("\nraw_market_data sample columns:", [d[0] for d in cursor.description])

conn.close()
