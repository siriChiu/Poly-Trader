#!/usr/bin/env python3
"""Inspect the database tables"""
import sqlite3, os

db_path = '/home/kazuha/Poly-Trader/poly_trader.db'
if os.path.exists(db_path):
    db = sqlite3.connect(db_path)
    tables = db.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()
    print("Tables:", tables)
    for t in tables:
        name = t[0]
        count = db.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]
        cols = db.execute(f'PRAGMA table_info({name})').fetchall()
        col_names = [c[1] for c in cols]
        print(f"\n  {name}: {count} rows, cols={col_names}")
    db.close()
else:
    print(f"DB not found: {db_path}")
