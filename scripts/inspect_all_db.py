#!/usr/bin/env python3
"""Inspect all DBs with actual content."""
import sqlite3, os

for db_name in ['market.db', 'poly_trader.db', 'stock.db']:
    db_path = os.path.join('/home/kazuha/Poly-Trader', 'data', db_name)
    if not os.path.exists(db_path):
        continue
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cur.fetchall()
    print(f'\n=== {db_name} ({len(tables)} tables) ===')
    for t in tables:
        cur.execute(f'PRAGMA table_info({t[0]})')
        cols = cur.fetchall()
        cur.execute(f'SELECT COUNT(*) FROM {t[0]}')
        count = cur.fetchone()[0]
        print(f'  {t[0]}: {count} rows, cols: {[c[1] for c in cols]}')
        # Show latest row for context
        cur.execute(f'SELECT * FROM {t[0]} ORDER BY rowid DESC LIMIT 1')
        row = cur.fetchone()
        if row:
            col_names = [c[1] for c in cols]
            print(f'    Latest: {dict(zip(col_names, row))}')
    conn.close()
