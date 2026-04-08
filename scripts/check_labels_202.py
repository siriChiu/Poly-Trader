#!/usr/bin/env python3
"""Check label pipeline status, recent sell_win, and why labels are stuck."""
import sqlite3
import numpy as np

DB = 'poly_trader.db'
conn = sqlite3.connect(DB)

# Recent sell_win (last N by timestamp)
for window in [50, 100, 500]:
    r = conn.execute(f"""
        SELECT label_spot_long_win
        FROM labels 
        WHERE label_spot_long_win IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT {window}
    """).fetchall()
    vals = [x[0] for x in r]
    recent_win = np.mean(vals)
    print(f"sell_win (last {window}): {recent_win:.3f} (n={len(vals)})")

# Find the gap: features exist but no labels
print("\n=== Finding the label generation gap ===")
# Get all feature timestamps
feature_ts = conn.execute("""
    SELECT DISTINCT timestamp FROM features_normalized ORDER BY timestamp DESC
""").fetchall()
feature_ts_set = set(t[0] for t in feature_ts)

# Get all label timestamps
label_ts = conn.execute("""
    SELECT DISTINCT timestamp FROM labels ORDER BY timestamp DESC
""").fetchall()
label_ts_set = set(t[0] for t in label_ts)

missing = feature_ts_set - label_ts_set
print(f"Feature timestamps without labels: {len(missing)}")
if missing:
    sorted_missing = sorted(missing, reverse=True)
    print(f"Latest missing: {sorted_missing[:5]}")
    print(f"Earliest missing: {sorted_missing[-5:]}")

# Check the labeling.py script
print("\n=== Label generation logic ===")
with open('data_ingestion/labeling.py', 'r') as f:
    content = f.read()
    # Show key parts
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if any(k in line.lower() for k in ['def ', 'label_sell', 'sql', 'insert', 'where timestamp', 'future_return']):
            print(f"  line {i+1}: {line.strip()}")

# Check if there's a cron job or scheduler
print("\n=== Checking scheduler/cron ===")
import os
for root, dirs, files in os.walk('.'):
    if 'venv' in root or '.git' in root or '__pycache__' in root:
        continue
    for f in files:
        if f.endswith('.py') and any(k in f.lower() for k in ['schedul', 'cron', 'runner', 'collect', 'heartbeat']):
            print(f"  {root}/{f}")

conn.close()
