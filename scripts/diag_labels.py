#!/usr/bin/env python3
"""Quick data diagnostics for heartbeat."""
import sqlite3

db = 'data/poly_trader.db'
conn = sqlite3.connect(db)
c = conn.cursor()

# List all tables
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f'Tables: {[t[0] for t in tables]}')

for t in tables:
    tname = t[0]
    cnt = c.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
    cols = c.execute(f'PRAGMA table_info("{tname}")').fetchall()
    col_names = [col[1] for col in cols]
    print(f'\n--- {tname} (rows={cnt}) ---')
    print(f'Cols: {col_names}')
    # Check timestamp-like column
    for col in cols:
        if 'time' in col[1].lower() or 'ts' in col[1].lower() or 'date' in col[1].lower():
            sample = c.execute(f'SELECT {col[1]} FROM "{tname}" ORDER BY {col[1]} DESC LIMIT 3').fetchall()
            print(f'  {col[1]} latest 3: {sample}')
            break

conn.close()
