#!/usr/bin/env python3
"""Inspect the real poly_trader.db in project root."""
import sqlite3, os

db_path = '/home/kazuha/Poly-Trader/poly_trader.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cur.fetchall()
print(f'=== poly_trader.db ({len(tables)} tables) ===')
for t in tables:
    cur.execute(f'PRAGMA table_info({t[0]})')
    cols = cur.fetchall()
    cur.execute(f'SELECT COUNT(*) FROM {t[0]}')
    count = cur.fetchone()[0]
    print(f'  {t[0]}: {count} rows, cols: {[c[1] for c in cols]}')
conn.close()
