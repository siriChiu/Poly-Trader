#!/usr/bin/env python3
"""Heartbeat #174 — Full IC analysis with all metrics needed"""
import sqlite3
import numpy as np
from pathlib import Path

db_path = Path(__file__).parent.parent / 'poly_trader.db'
if not db_path.exists():
    db_path = Path('.') / 'poly_trader.db'
conn = sqlite3.connect(str(db_path))
c = conn.cursor()

# Step 1: Check tables and counts
print("=== Step 1: Data Collection ===")
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print('Tables:', tables[:20])

for t in tables:
    c.execute(f'SELECT COUNT(*) FROM {t}')
    print(f'  {t}: {c.fetchone()[0]}')

# Raw data info
if 'raw_market_data' in tables:
    c.execute('SELECT MAX(timestamp), MIN(timestamp) FROM raw_market_data')
    row = c.fetchone()
    print(f'Raw data range: {row[0]} to {row[1]}')
    c.execute('SELECT close_price FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')
    btc = c.fetchone()
    if btc: print(f'Latest BTC: ${btc[0]}')

# Feature counts 
feat_table = 'features' if 'features' in tables else ('features_normalized' if 'features_normalized' in tables else 'unknown')
print(f'Feature table: {feat_table}')
c.execute(f'SELECT COUNT(*) FROM {feat_table}')
print(f'Features count: {c.fetchone()[0]}')

# Label info
if 'labels' in tables:
    c.execute('SELECT AVG(label_sell_win), COUNT(*) FROM labels WHERE label_sell_win IS NOT NULL')
    row = c.fetchone()
    print(f'Label sell_win rate: {row[0]:.4f}  (N={row[1] if row[1] else 0})')

# Check for funding rate / FNG / derivatives
for col_name in ['funding_rate', 'fear_greed_index', 'fng', 'btc_price', 'price']:
    try:
        if feat_table != 'unknown':
            c.execute(f'PRAGMA table_info({feat_table})')
            cols = [r[1] for r in c.fetchall()]
            if col_name in cols:
                c.execute(f'SELECT {col_name} FROM {feat_table} ORDER BY rowid DESC LIMIT 1')
                val = c.fetchone()
                print(f'Latest {col_name}: {val[0] if val else "N/A"}')
    except:
        pass

# Step 2: Sensory IC Analysis
print("\n=== Step 2: Sensory IC Analysis ===")
senses = ['eye', 'ear', 'nose', 'tongue', 'body', 'pulse', 'aura', 'mind']

# Determine the actual column names for senses
if feat_table != 'unknown':
    c.execute(f'PRAGMA table_info({feat_table})')
    feat_cols = [r[1] for r in c.fetchall()]
    print(f'Feature columns: {feat_cols}')

# Determine the actual sense column names in the features table
sense_col_map = {}
for s in senses:
    for cn in feat_cols:
        if cn == f'feat_{s}':
            sense_col_map[s] = cn
            break
    # Fallback: partial match
    if s not in sense_col_map:
        for cn in feat_cols:
            if s.lower() in cn.lower():
                sense_col_map[s] = cn
                break

print(f'Sense column mapping: {sense_col_map}')

# Check if labels table has regime column
has_regime = False
if 'labels' in tables:
    c.execute('PRAGMA table_info(labels)')
    label_cols = [r[1] for r in c.fetchall()]
    has_regime = 'regime' in label_cols
    print(f'Labels table columns: {label_cols}')

# Get features + labels joined
sense_cols = list(sense_col_map.values())
if has_regime:
    query = f'''
        SELECT f.timestamp, {", ".join(sense_cols)}, l.label_sell_win, l.regime
        FROM {feat_table} f
        INNER JOIN labels l ON f.timestamp = l.timestamp
        WHERE l.label_sell_win IS NOT NULL
        ORDER BY f.timestamp
    '''
else:
    query = f'''
        SELECT f.timestamp, {", ".join(sense_cols)}, l.label_sell_win
        FROM {feat_table} f
        INNER JOIN labels l ON f.timestamp = l.timestamp
        WHERE l.label_sell_win IS NOT NULL
        ORDER BY f.timestamp
    '''

c.execute(query)
rows = c.fetchall()
print(f"Total joined records: {len(rows)}")

if not rows:
    print("ERROR: No joined records found!")
    conn.close()
    exit(1)

# Extract arrays
ts_arr = [r[0] for r in rows]
idx_senses = list(range(1, len(sense_cols) + 1))
label_idx = len(sense_cols) + 1
regime_idx = len(sense_cols) + 2 if has_regime else None

sense_data = {s: [] for s in senses}
labels = []
regimes = []

for r in rows:
    labels.append(float(r[label_idx]))
    for i, s in enumerate(senses):
        val = r[idx_senses[i]]
        sense_data[s].append(float(val) if val is not None else 0.0)
    if has_regime:
        regimes.append(r[regime_idx] if r[regime_idx] is not None else 'Unknown')

for s in senses:
    sense_data[s] = np.array(sense_data[s], dtype=float)

y = np.array(labels, dtype=float)

def calc_ic(x, y):
    """Pearson correlation = IC"""
    if np.std(x) < 1e-10 or len(x) < 10:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])

print("\n--- Global IC (all data) ---")
global_ics = {}
for s in senses:
    ic = calc_ic(sense_data[s], y)
    std = np.std(sense_data[s])
    unique = len(np.unique(sense_data[s]))
    status = "PASS" if abs(ic) >= 0.05 else "FAIL"
    global_ics[s] = ic
    print(f"  {s:8s}: IC={ic:+.4f} {status} | std={std:.6f} | unique={unique}")

# Regime analysis
if has_regime:
    print("\n--- Regime-aware IC ---")
    regime_ics = {}
    for regime in sorted(set(regimes)):
        mask = np.array([r == regime for r in regimes])
        if mask.sum() < 10:
            continue
        regime_ics[regime] = {}
        print(f"  Regime: {regime} (N={mask.sum()})")
        for s in senses:
            ic = calc_ic(sense_data[s][mask], y[mask])
            regime_ics[regime][s] = ic
            status = "PASS" if abs(ic) >= 0.05 else "FAIL"
            print(f"    {s:8s}: IC={ic:+.4f} {status}")

# Recent 100 rows IC
print(f"\n--- Recent 100 IC ---")
recent_n = 100
recent_ics = {}
for s in senses:
    recent = sense_data[s][-recent_n:]
    recent_labels = y[-recent_n:]
    ic = calc_ic(recent, recent_labels)
    std = np.std(recent)
    unique = len(np.unique(recent))
    status = "PASS" if abs(ic) >= 0.05 else "FAIL"
    warning = " COLLAPSE" if (unique < 10 and std < 0.01) else ""
    recent_ics[s] = ic
    print(f"  {s:8s}: IC={ic:+.4f} {status} | std={std:.6f} | unique={unique}{warning}")

# Dynamic window IC
print(f"\n--- Dynamic Window IC ---")
dynamic_ics = {}
for window in [500, 1000, 2000, 3000, 5000]:
    if window > len(y):
        continue
    wn = y[-window:]
    dynamic_ics[window] = {}
    print(f"  N={window}:")
    for s in senses:
        ws = sense_data[s][-window:]
        ic = calc_ic(ws, wn)
        dynamic_ics[window][s] = ic
        status = "PASS" if abs(ic) >= 0.05 else "FAIL"
        print(f"    {s:8s}: IC={ic:+.4f} {status}")

conn.close()
print("\n=== IC Analysis Complete ===")
