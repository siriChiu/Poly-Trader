#!/usr/bin/env python3
"""Heartbeat #173 — IC analysis and data collection"""
import json
import sqlite3
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

db_path = 'data/poly_trader.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Step 1: Check counts
print("=== Step 1: Data Collection ===")
for table in ['raw_market_data', 'features', 'labels']:
    c.execute(f'SELECT COUNT(*) FROM {table}')
    count = c.fetchone()[0]
    print(f'{table}: {count}')

c.execute('SELECT MAX(timestamp), MIN(timestamp) FROM raw_market_data')
row = c.fetchone()
print(f'Raw data range: {row[0]} to {row[1]}')

# Get latest BTC price
c.execute('SELECT price FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')
btc = c.fetchone()
btc_price = btc[0] if btc else 'N/A'
print(f'Latest BTC: ${btc_price}')

# Check label distribution
c.execute('SELECT AVG(label_spot_long_win), COUNT(*) FROM labels WHERE label_spot_long_win IS NOT NULL')
row = c.fetchone()
print(f'Label sell_win rate: {row[0]:.4f}  (N={row[1]})')

# Step 2: Sensory IC Analysis
print("\n=== Step 2: Sensory IC Analysis ===")
senses = ['eye', 'ear', 'nose', 'tongue', 'body', 'pulse', 'aura', 'mind']

# Get features + labels joined
c.execute(f'''
    SELECT f.timestamp, 
           f.eye, f.ear, f.nose, f.tongue, f.body, f.pulse, f.aura, f.mind,
           l.label_spot_long_win
    FROM features f
    INNER JOIN labels l ON f.timestamp = l.timestamp
    WHERE l.label_spot_long_win IS NOT NULL
    ORDER BY f.timestamp
''')

rows = c.fetchall()
print(f"Total joined records: {len(rows)}")

# Extract arrays
ts_arr = [r[0] for r in rows]
sense_data = {s: [] for s in senses}
labels = []

for r in rows:
    labels.append(int(r[9]))
    for i, s in enumerate(senses):
        sense_data[s].append(r[1+i])

for s in senses:
    sense_data[s] = np.array(sense_data[s], dtype=float)

y = np.array(labels, dtype=float)

def calc_ic(x, y):
    """Pearson correlation = IC"""
    if np.std(x) < 1e-10 or len(x) < 10:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])

print("\n--- Global IC (h=4, all data) ---")
for s in senses:
    ic = calc_ic(sense_data[s], y)
    std = np.std(sense_data[s])
    unique = len(np.unique(sense_data[s]))
    status = "✅" if abs(ic) >= 0.05 else "❌"
    print(f"  {s:8s}: IC={ic:+.4f} {status} | std={std:.6f} | unique={unique}")

# Regime analysis - check if we have regime column
try:
    c.execute('SELECT DISTINCT regime FROM labels LIMIT 10')
    regimes = [r[0] for r in c.fetchall() if r[0] is not None]
    print(f"\n--- Regime-aware IC ---")
    for regime in set(regimes):
        c.execute(f'''
            SELECT f.eye, f.ear, f.nose, f.tongue, f.body, f.pulse, f.aura, f.mind,
                   l.label_spot_long_win
            FROM features f
            INNER JOIN labels l ON f.timestamp = l.timestamp
            WHERE l.label_spot_long_win IS NOT NULL AND l.regime = ?
        ''', (regime,))
        regime_rows = c.fetchall()
        print(f"  Regime: {regime} (N={len(regime_rows)})")
        for i, s in enumerate(senses):
            arr = np.array([float(r[i]) for r in regime_rows], dtype=float)
            lbl = np.array([float(r[8]) for r in regime_rows], dtype=float)
            ic = calc_ic(arr, lbl)
            status = "✅" if abs(ic) >= 0.05 else "❌"
            print(f"    {s:8s}: IC={ic:+.4f} {status}")
except Exception as e:
    print(f"  Regime column not found: {e}")

# Recent 100 rows IC
print(f"\n--- Recent 100 IC ---")
recent_n = 100
for s in senses:
    recent = sense_data[s][-recent_n:]
    recent_labels = y[-recent_n:]
    ic = calc_ic(recent, recent_labels)
    std = np.std(recent)
    unique = len(np.unique(recent))
    status = "✅" if abs(ic) >= 0.05 else "❌"
    warning = " 🚨 COLLAPSE" if (unique < 10 and std < 0.01) else ""
    print(f"  {s:8s}: IC={ic:+.4f} {status} | std={std:.6f} | unique={unique}{warning}")

# Dynamic window IC
print(f"\n--- Dynamic Window IC ---")
for window in [500, 1000, 2000]:
    if window > len(y):
        continue
    wn = y[-window:]
    print(f"  N={window}:")
    for s in senses:
        ws = sense_data[s][-window:]
        ic = calc_ic(ws, wn)
        status = "✅" if abs(ic) >= 0.05 else "❌"
        print(f"    {s:8s}: IC={ic:+.4f} {status}")

conn.close()
print("\n=== IC Analysis Complete ===")
