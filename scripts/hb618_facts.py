#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB = Path('/home/kazuha/Poly-Trader/poly_trader.db')
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

for table in ['raw_market_data', 'features_normalized', 'labels', 'raw_events']:
    count = conn.execute(f'SELECT COUNT(*) AS c FROM {table}').fetchone()['c']
    print(f'{table}: {count}')

rate = conn.execute(
    'SELECT AVG(CAST(simulated_pyramid_win AS FLOAT)) AS r FROM labels WHERE horizon_minutes=1440 AND simulated_pyramid_win IS NOT NULL'
).fetchone()['r']
print(f'simulated_pyramid_win_1440_rate: {rate}')

print('raw_event_source_subtypes:')
rows = conn.execute(
    'SELECT source, subtype, COUNT(*) AS c FROM raw_events GROUP BY source, subtype ORDER BY source, subtype'
).fetchall()
for row in rows:
    print(f"  {row['source']}::{row['subtype']}={row['c']}")

interesting = ['claw_snapshot', 'fang_snapshot', 'fin_snapshot', 'web_snapshot', 'scales_snapshot', 'nest_snapshot']
for subtype in interesting:
    count = conn.execute('SELECT COUNT(*) AS c FROM raw_events WHERE subtype=?', (subtype,)).fetchone()['c']
    print(f'{subtype}: {count}')
