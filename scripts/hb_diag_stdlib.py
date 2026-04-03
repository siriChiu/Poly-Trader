#!/usr/bin/env python3
"""Heartbeat #105: Additional diagnostics using only stdlib"""
import sqlite3
import os

DB = '/home/kazuha/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(DB)

# Latest raw data
cur = conn.execute('SELECT MAX(timestamp) FROM raw_market_data')
latest_ts = cur.fetchone()[0]
cur = conn.execute('SELECT close_price, btc_price, fear_greed_index, funding_rate, polymarket_prob FROM raw_market_data WHERE timestamp = ?', (latest_ts,))
row = cur.fetchone()
if row:
    print(f'Latest raw: ts={latest_ts}')
    print(f'  close_price={row[0]}')
    print(f'  btc_price={row[1]}')
    print(f'  fng={row[2]}')
    print(f'  funding_rate={row[3]}')
    print(f'  polymarket_prob={row[4]}')

# Counts
for table in ['raw_market_data', 'features_normalized', 'labels']:
    cur = conn.execute(f'SELECT COUNT(*) FROM {table}')
    print(f'{table}: {cur.fetchone()[0]}')

cur = conn.execute('SELECT label_up, COUNT(*) FROM labels WHERE label_up IS NOT NULL GROUP BY label_up')
print('Label distribution:')
for row in cur.fetchall():
    print(f'  label_up={row[0]}: {row[1]}')

# Aura diagnosis
cur = conn.execute('SELECT DISTINCT feat_aura FROM features_normalized WHERE feat_aura IS NOT NULL')
vals = [r[0] for r in cur.fetchall()]
print(f'\nAura unique values: {sorted(vals)[:20]}')
for v in sorted(vals)[:5]:
    cur2 = conn.execute('SELECT COUNT(*) FROM features_normalized WHERE feat_aura = ?', (v,))
    print(f'  aura={v}: {cur2.fetchone()[0]} samples')

# Check if most aura values are 0 or 1
cur = conn.execute('SELECT feat_aura, COUNT(*) as cnt FROM features_normalized WHERE feat_aura IS NOT NULL GROUP BY feat_aura ORDER BY cnt DESC LIMIT 5')
print('\nAura top 5:')
for row in cur.fetchall():
    print(f'  aura={row[0]}: {row[1]} samples')

# Funding rate stats
cur = conn.execute('SELECT MIN(funding_rate), MAX(funding_rate), AVG(funding_rate), COUNT(*) FROM raw_market_data WHERE funding_rate IS NOT NULL')
row = cur.fetchone()
print(f'\nFunding rate: min={row[0]}, max={row[1]}, avg={row[2]}, count={row[3]}')

conn.close()
