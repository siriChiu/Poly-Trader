#!/usr/bin/env python
"""Check feature columns for degenerate/stale values."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'poly_trader.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Check feature columns in recent window
query = """
SELECT 
    COUNT(*),
    COUNT(DISTINCT feat_eye) as eye_unique,
    COUNT(DISTINCT feat_ear) as ear_unique,
    COUNT(DISTINCT feat_nose) as nose_unique,
    COUNT(DISTINCT feat_tongue) as tongue_unique,
    COUNT(DISTINCT feat_body) as body_unique,
    COUNT(DISTINCT feat_pulse) as pulse_unique,
    COUNT(DISTINCT feat_aura) as aura_unique,
    COUNT(DISTINCT feat_mind) as mind_unique,
    MIN(feat_eye), MAX(feat_eye),
    MIN(feat_ear), MAX(feat_ear),
    MIN(feat_nose), MAX(feat_nose),
    MIN(feat_tongue), MAX(feat_tongue),
    MIN(feat_body), MAX(feat_body),
    MIN(feat_pulse), MAX(feat_pulse),
    MIN(feat_aura), MAX(feat_aura),
    MIN(feat_mind), MAX(feat_mind)
FROM features_normalized
WHERE id > (SELECT MAX(id) - 5000 FROM features_normalized)
"""
cur.execute(query)
row = cur.fetchone()
cols = ['count', 'eye_uq', 'ear_uq', 'nose_uq', 'tongue_uq', 'body_uq', 
        'pulse_uq', 'aura_uq', 'mind_uq', 
        'eye_min', 'eye_max', 'ear_min', 'ear_max',
        'nose_min', 'nose_max', 'tongue_min', 'tongue_max',
        'body_min', 'body_max', 'pulse_min', 'pulse_max',
        'aura_min', 'aura_max', 'mind_min', 'mind_max']

for name, val in zip(cols, row):
    print(f"  {name}: {val}")

# Check raw data columns that feed features
print("\n=== Raw data feeders ===")
query2 = """
SELECT 
    COUNT(*) as cnt,
    COUNT(eye_dist) as eye_nn, 
    COUNT(ear_prob) as ear_nn,
    COUNT(tongue_sentiment) as tongue_nn,
    COUNT(volatility) as vol_nn,
    COUNT(oi_roc) as oi_nn,
    COUNT(funding_rate) as fr_nn,
    AVG(funding_rate) as fr_avg,
    AVG(eye_dist) as eye_avg,
    AVG(ear_prob) as ear_avg
FROM raw_market_data
WHERE id > (SELECT MAX(id) - 5000 FROM raw_market_data)
"""
cur.execute(query2)
row2 = cur.fetchone()
cols2 = ['cnt', 'eye_nn', 'ear_nn', 'tongue_nn', 'vol_nn', 'oi_nn', 'fr_nn',
         'fr_avg', 'eye_avg', 'ear_avg']
for name, val in zip(cols2, row2):
    print(f"  {name}: {val}")

# Check what feature_version values exist
cur.execute('SELECT DISTINCT feature_version, COUNT(*) FROM features_normalized GROUP BY feature_version')
print(f"\n=== Feature versions ===")
for row in cur.fetchall():
    print(f"  version={row[0]}: count={row[1]}")

conn.close()
