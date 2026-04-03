#!/usr/bin/env python3
"""Debug matching between features and labels."""
import sqlite3

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(DB_PATH)

# Schema
for table in ['raw_market_data', 'features_normalized', 'labels']:
    print(f"\n=== {table} ===")
    cur = conn.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        print(f"  {row}")
    
    # Sample timestamps
    cur = conn.execute(f"SELECT timestamp FROM {table} LIMIT 5")
    rows = cur.fetchall()
    print(f"  Sample timestamps: {rows}")
    
    # Count
    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
    print(f"  Total: {cur.fetchone()[0]}")

# Check timestamp overlap
cur = conn.execute("SELECT COUNT(DISTINCT timestamp) FROM features_normalized")
feat_ts = cur.fetchone()[0]
print(f"\nDistinct feature timestamps: {feat_ts}")

cur = conn.execute("SELECT COUNT(DISTINCT timestamp) FROM labels")
label_ts = cur.fetchone()[0]
print(f"Distinct label timestamps: {label_ts}")

# Direct match count
cur = conn.execute("""
    SELECT COUNT(*) FROM features_normalized f
    INNER JOIN labels l ON f.timestamp = l.timestamp
""")
direct_match = cur.fetchone()[0]
print(f"\nDirect timestamp match: {direct_match}")

# Near match (within 1 hour = 3600 seconds)
cur = conn.execute("""
    SELECT COUNT(*) FROM features_normalized f
    INNER JOIN labels l ON ABS(CAST(f.timestamp AS INTEGER) - CAST(l.timestamp AS INTEGER)) < 3600
""")
near_match_1h = cur.fetchone()[0]
print(f"Near match (within 1h): {near_match_1h}")

# Near match (within 4 hours = 14400 seconds)
cur = conn.execute("""
    SELECT COUNT(*) FROM features_normalized f
    INNER JOIN labels l ON ABS(CAST(f.timestamp AS INTEGER) - CAST(l.timestamp AS INTEGER)) < 14400
""")
near_match_4h = cur.fetchone()[0]
print(f"Near match (within 4h): {near_match_4h}")

# Check for NaN-like values in features
for feat in ['feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind']:
    cur = conn.execute(f"SELECT COUNT(*), COUNT({feat}), COUNT(*) - COUNT({feat}) FROM features_normalized")
    row = cur.fetchone()
    print(f"\n{feat}: total={row[0]}, not_null={row[1]}, null={row[2]}")

conn.close()
