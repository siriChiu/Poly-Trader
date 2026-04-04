#!/usr/bin/env python3
"""Heartbeat #202 data collection and IC analysis."""
import sqlite3, json, numpy as np, os, sys

DB = 'poly_trader.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print("=== Poly-Trader Heartbeat #202 Data Collection ===\n")

# List all tables
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print(f"Tables found: {[t[0] for t in tables]}\n")

for t in tables:
    tname = t[0]
    cnt = c.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
    cols = c.execute(f'PRAGMA table_info("{tname}")').fetchall()
    col_names = [col[1] for col in cols]
    print(f"--- {tname}: {cnt} rows ---")
    print(f"  Cols: {col_names}")
    # Show most recent timestamp-like column
    ts_col = None
    for col in cols:
        if any(k in col[1].lower() for k in ['time', 'timestamp', 'datetime', 'date']):
            ts_col = col[1]
            break
    if ts_col:
        latest = c.execute(f'SELECT {ts_col} FROM "{tname}" ORDER BY {ts_col} DESC LIMIT 1').fetchone()
        print(f"  Latest {ts_col}: {latest}")
        oldest = c.execute(f'SELECT {ts_col} FROM "{tname}" ORDER BY {ts_col} ASC LIMIT 1').fetchone()
        print(f"  Oldest {ts_col}: {oldest}")
    print()

# If we find a features table, get feature columns
if any('feature' in t[0].lower() for t in tables):
    ft = [t[0] for t in tables if 'feature' in t[0].lower()][0]
    cols = c.execute(f'PRAGMA table_info("{ft}")').fetchall()
    print(f"\nFeature columns in {ft}:")
    for col in cols:
        col_name = col[1]
        if col_name in ('id', 'timestamp', 'datetime'):
            continue
        try:
            stats = c.execute(f'SELECT AVG({col_name}), COUNT({col_name}) FROM "{ft}"').fetchone()
            unique = c.execute(f'SELECT COUNT(DISTINCT {col_name}) FROM "{ft}"').fetchone()
            print(f"  {col_name}: avg={stats[0]}, non_null={stats[1]}, unique={unique[0]}")
        except:
            pass

# If we find a labels table
if any('label' in t[0].lower() for t in tables):
    lt = [t[0] for t in tables if 'label' in t[0].lower()][0]
    cols = c.execute(f'PRAGMA table_info("{lt}")').fetchall()
    print(f"\nLabel columns in {lt}:")
    col_names = [col[1] for col in cols]
    print(f"  All cols: {col_names}")
    cnt = c.execute(f'SELECT COUNT(*) FROM "{lt}"').fetchone()[0]
    print(f"  Total rows: {cnt}")
    # Get sell_win distribution if it exists
    for col in cols:
        cn = col[1]
        try:
            vals = c.execute(f'SELECT {cn}, COUNT(*) FROM "{lt}" GROUP BY {cn}').fetchall()
            print(f"  {cn} distribution: {vals[:10]}")
        except:
            pass

conn.close()
