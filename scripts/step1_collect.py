#!/usr/bin/env python3
"""Heartbeat data collection - reads DB and prints stats"""
import sqlite3
import sys
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'poly_trader.db')

if not os.path.exists(db_path):
    print(f"ERROR: Database not found at {db_path}")
    sys.exit(1)

db = sqlite3.connect(db_path)

# List all tables
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("TABLES FOUND:")
for t in tables:
    cnt = db.execute(f'SELECT COUNT(*) FROM {t[0]}').fetchone()[0]
    cols = db.execute(f'PRAGMA table_info({t[0]})').fetchall()
    col_names = [c[1] for c in cols]
    print(f"  {t[0]}: {cnt} rows, cols: {col_names[:5]}...")

# Get counts from likely tables
# Try common names
for table_name in ['raw_data', 'raw', 'raw_market_data', 'market_data', 'prices', 'btc_data']:
    try:
        cnt = db.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
        print(f"{table_name} count: {cnt}")
    except:
        pass

for table_name in ['features', 'feature_store', 'feature_data']:
    try:
        cnt = db.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
        print(f"{table_name} count: {cnt}")
    except:
        pass

for table_name in ['labels', 'label_store', 'label_data']:
    try:
        cnt = db.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
        print(f"{table_name} count: {cnt}")
    except:
        pass

# Find latest BTC-like data
for table_name, cols_to_try in [
    ('raw_data', ['close', 'price', 'open', 'timestamp', 'date']),
    ('market_data', ['close', 'price', 'open', 'timestamp', 'date']),
    ('prices', ['close', 'price', 'open', 'timestamp', 'date']),
]:
    try:
        cols = db.execute(f'PRAGMA table_info({table_name})').fetchall()
        col_names = [c[1] for c in cols]
        print(f"\n--- Table: {table_name} ---")
        print(f"Columns: {col_names}")
        # Get last row
        row = db.execute(f'SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 1').fetchone()
        print(f"Last row: {dict(zip(col_names, row))}")
    except:
        pass

db.close()
