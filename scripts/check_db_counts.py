#!/usr/bin/env python3
"""Check DB counts for heartbeat."""
import sqlite3, json, os

db_path = os.path.join(os.getcwd(), 'data', 'poly_trader.db')
if not os.path.exists(db_path):
    print('DB not found at', db_path)
    # Try fallback
    db_path = os.path.join(os.getcwd(), 'poly_trader.db')
    if not os.path.exists(db_path):
        print('Fallback DB also not found')
        exit(1)
    else:
        print('Using fallback DB at', db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print('Tables:', tables)

# Count rows in key tables
for t in tables:
    cursor.execute(f'SELECT COUNT(*) FROM [{t}]')
    cnt = cursor.fetchone()[0]
    print(f'  {t}: {cnt} rows')

# Get latest BTC price
try:
    cursor.execute("SELECT * FROM market_data ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        # Get column names
        cols = [d[0] for d in cursor.description]
        print(f'\nLatest market data row:')
        for c, v in zip(cols, row):
            print(f'  {c}: {v}')
except Exception as e:
    print(f'Error reading market_data: {e}')

# Get latest FNG
try:
    cursor.execute("SELECT * FROM fear_greed_index ORDER BY date DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        cols = [d[0] for d in cursor.description]
        print(f'\nLatest FNG row:')
        for c, v in zip(cols, row):
            print(f'  {c}: {v}')
except Exception as e:
    print(f'Error reading fear_greed_index: {e}')

# Get derivatives data
try:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%deriv%'")
    deriv_tables = [r[0] for r in cursor.fetchall()]
    for dt in deriv_tables:
        cursor.execute(f'SELECT COUNT(*) FROM [{dt}]')
        cnt = cursor.fetchone()[0]
        print(f'Derivatives table {dt}: {cnt} rows')
except Exception as e:
    print(f'Error checking derivatives: {e}')

conn.close()
