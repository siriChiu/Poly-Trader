#!/usr/bin/env python3
"""Quick DB counts for heartbeat #266."""
import sqlite3, os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'poly_trader.db')
conn = sqlite3.connect(db_path)

tables = ['raw_market_data', 'features_normalized', 'labels']
for t in tables:
    count = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'{t}: {count}')

# sell_win rate
row = conn.execute('SELECT AVG(CAST(label_sell_win AS FLOAT)), COUNT(*) FROM labels WHERE label_sell_win IS NOT NULL').fetchone()
if row[0] is not None:
    print(f'sell_win: {row[0]:.4f} (n={row[1]})')

# Latest timestamp
ts = conn.execute('SELECT MAX(timestamp) FROM raw_market_data').fetchone()[0]
print(f'latest_raw_ts: {ts}')

conn.close()
