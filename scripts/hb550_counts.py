#!/usr/bin/env python3
"""Quick DB counts for heartbeat #550."""
import sqlite3
import os
from datetime import datetime

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(DB_PATH)

for t in ['raw_market_data', 'features_normalized', 'labels']:
    count = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'{t}: {count}')

# Quick sell_win check
sw = conn.execute('SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL').fetchone()[0]
print(f'sell_win: {sw:.4f}')

# Latest timestamps
for t in ['raw_market_data', 'features_normalized', 'labels']:
    ts = conn.execute(f'SELECT MAX(timestamp) FROM {t}').fetchone()[0]
    print(f'{t}_latest: {ts}')

conn.close()
