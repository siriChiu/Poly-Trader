#!/usr/bin/env python3
"""Heartbeat #105: Recompute Aura features with new v12 formula (price_sma144_deviation)"""
import sqlite3
import os
from datetime import datetime

DB = '/home/kazuha/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(DB)

# Get all raw market data ordered by timestamp
cur = conn.execute('SELECT timestamp, close_price FROM raw_market_data ORDER BY timestamp')
raw_data = cur.fetchall()

print(f"Total raw data: {len(raw_data)} rows")
print(f"Time range: {raw_data[0][0]} to {raw_data[-1][0]}")

# Get all feature timestamps
cur = conn.execute('SELECT timestamp FROM features_normalized ORDER BY timestamp')
feature_rows = cur.fetchall()
feat_timestamps = [row[0] for row in feature_rows]
print(f"Total features: {len(feat_timestamps)}")

# Build index for raw data lookup
raw_ts_idx = {}
for i, (ts, _) in enumerate(raw_data):
    raw_ts_idx[ts] = i

# Recompute Aura for each feature
updated = 0
errors = 0
for feat_ts in feat_timestamps:
    if feat_ts not in raw_ts_idx:
        continue
    idx = raw_ts_idx[feat_ts]
    # Get close prices up to this point
    close_prices = [float(raw_data[j][1]) for j in range(idx + 1)]
    
    if len(close_prices) >= 145:
        sma144 = sum(close_prices[-144:]) / 144
        if sma144 > 0:
            new_aura = (close_prices[-1] - sma144) / sma144
        else:
            new_aura = 0.0
    elif len(close_prices) >= 25:
        sma24 = sum(close_prices[-24:]) / 24
        if sma24 > 0:
            new_aura = (close_prices[-1] - sma24) / sma24
        else:
            new_aura = 0.0
    else:
        new_aura = 0.0

    conn.execute('UPDATE features_normalized SET feat_aura = ? WHERE timestamp = ?', (new_aura, feat_ts))
    updated += 1
    if updated % 1000 == 0:
        conn.commit()
        print(f"  ... updated {updated}/{len(feat_timestamps)}")

conn.commit()
print(f"\nTotal updated: {updated}")

# Verify Aura distribution
cur = conn.execute('SELECT MIN(feat_aura), MAX(feat_aura), AVG(feat_aura), COUNT(*), COUNT(DISTINCT feat_aura) FROM features_normalized WHERE feat_aura IS NOT NULL')
row = cur.fetchone()
print(f"Aura stats: min={row[0]:.6f}, max={row[1]:.6f}, avg={row[2]:.6f}, count={row[3]}, distinct={row[4]}")

# Sample some values
cur = conn.execute('SELECT feat_aura FROM features_normalized WHERE feat_aura IS NOT NULL ORDER BY timestamp DESC LIMIT 10')
print(f"Latest 10 aura values:")
for row in cur.fetchall():
    print(f"  {row[0]:.6f}")

# Sample from different positions
cur = conn.execute('SELECT feat_aura FROM features_normalized WHERE feat_aura IS NOT NULL ORDER BY RANDOM() LIMIT 10')
print(f"Random 10 aura values:")
for row in cur.fetchall():
    print(f"  {row[0]:.6f}")

conn.close()
