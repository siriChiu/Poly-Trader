#!/usr/bin/env python3
"""Inspect DB schema and counts."""
import sqlite3, os
db_path = os.path.join('/home/kazuha/Poly-Trader', 'data', 'poly_trader.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cur.fetchall()
print('Tables:', tables)
for t in tables:
    cur.execute(f'PRAGMA table_info({t[0]})')
    cols = cur.fetchall()
    cur.execute(f'SELECT COUNT(*) FROM {t[0]}')
    count = cur.fetchone()[0]
    print(f'{t[0]}: {count} rows, cols: {[c[1] for c in cols]}')
conn.close()
