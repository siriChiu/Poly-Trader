#!/usr/bin/env python3
"""Check ALL DB files for heartbeat."""
import sqlite3, os

base = os.path.join(os.getcwd())
db_files = []
for root, dirs, files in os.walk(base):
    for f in files:
        if f.endswith('.db'):
            db_files.append(os.path.join(root, f))

for db_path in db_files:
    print(f'\n=== {db_path} ===')
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        for t in tables:
            cursor.execute(f'SELECT COUNT(*) FROM [{t}]')
            cnt = cursor.fetchone()[0]
            print(f'  {t}: {cnt} rows')
        
        # Check for market data tables
        for t in tables:
            if 'market' in t.lower() or 'btc' in t.lower() or 'price' in t.lower():
                cursor.execute(f'SELECT * FROM [{t}] ORDER BY rowid DESC LIMIT 1')
                row = cursor.fetchone()
                if row:
                    cols = [d[0] for d in cursor.description]
                    print(f'  Latest {t}:')
                    for c, v in zip(cols, row):
                        print(f'    {c}: {v}')
        
        # Check for fear_greed or similar
        for t in tables:
            if 'fear' in t.lower() or 'fng' in t.lower() or 'deriv' in t.lower():
                cursor.execute(f'SELECT * FROM [{t}] ORDER BY rowid DESC LIMIT 1')
                row = cursor.fetchone()
                if row:
                    cols = [d[0] for d in cursor.description]
                    print(f'  Latest {t}:')
                    for c, v in zip(cols, row):
                        print(f'    {c}: {v}')
        
        conn.close()
    except Exception as e:
        print(f'  Error: {e}')
