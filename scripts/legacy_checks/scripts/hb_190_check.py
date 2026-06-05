#!/usr/bin/env python3
"""Heartbeat check: VIX status and data collection status"""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('poly_trader.db')

# Check schema
cols = conn.execute("PRAGMA table_info(raw_market_data)").fetchall()
print("raw_market_data columns:")
for c in cols:
    print(f"  {c[1]} ({c[2]})")

# Check latest raw for VIX
col_names = [c[1] for c in cols]
select_cols = [c for c in ['timestamp', 'vix_value', 'dxy_value', 'btc_open', 'btc_close', 'regime_label'] if c in col_names]
if not select_cols:
    select_cols = ['timestamp']

query = f"SELECT {', '.join(select_cols)} FROM raw_market_data ORDER BY timestamp DESC LIMIT 3"
row = conn.execute(query).fetchall()
print(f'\nLatest raw rows ({len(row)}):')
for r in row:
    print(r)

# Count entries in last 12h
cutoff = (datetime.now() - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
count = conn.execute(
    "SELECT COUNT(*) FROM raw_market_data WHERE timestamp >= ?",
    (cutoff,)
).fetchone()[0]
print(f'\nNew rows in last 12h: {count}')

# How many null VIX
null_vix = conn.execute('SELECT COUNT(*) FROM raw_market_data WHERE vix_value IS NULL').fetchone()[0]
total = conn.execute('SELECT COUNT(*) FROM raw_market_data').fetchone()[0]
print(f'VIX NULL count: {null_vix}/{total}')

# DXY null count
if 'dxy_value' in col_names:
    null_dxy = conn.execute('SELECT COUNT(*) FROM raw_market_data WHERE dxy_value IS NULL').fetchone()[0]
    print(f'DXY NULL count: {null_dxy}/{total}')

conn.close()
