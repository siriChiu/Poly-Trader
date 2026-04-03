#!/usr/bin/env python3
"""Inspect database schema and compute IC for all senses."""
import os, sys, json
import sqlite3
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

db = sqlite3.connect(os.path.join(os.path.dirname(__file__), "poly_trader.db"))

# List tables
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables])

for t in tables:
    tname = t[0]
    cols = db.execute(f'SELECT * FROM {tname} LIMIT 1').description
    print(f'  {tname} columns: {[c[0] for c in cols]}')
    cnt = db.execute(f'SELECT COUNT(*) FROM {tname}').fetchone()[0]
    print(f'  {tname} rows: {cnt}')

# Now figure out which table has labels
# Check labels table schema specifically
if 'labels' in [t[0] for t in tables]:
    label_rows = db.execute("SELECT * FROM labels LIMIT 5").fetchall()
    label_cols = [d[0] for d in db.execute("SELECT * FROM labels LIMIT 0").description]
    print(f"\nLabels table columns: {label_cols}")
    print(f"Sample rows: {label_rows[:3]}")

# Check features_normalized
if 'features_normalized' in [t[0] for t in tables]:
    fn_cols = [d[0] for d in db.execute("SELECT * FROM features_normalized LIMIT 0").description]
    print(f"\nFeatures columns ({len(fn_cols)}): {fn_cols}")

db.close()
