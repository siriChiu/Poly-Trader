import sqlite3, os, json

db = '/home/kazuha/Poly-Trader/data/market.db'
print(f"DB exists: {os.path.exists(db)}")
print(f"DB size: {os.path.getsize(db)} bytes")

conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(f"Tables: {[r[0] for r in c.fetchall()]}")

for t in ['raw_4h', 'features', 'close_prices']:
    try:
        c.execute(f'SELECT COUNT(*) FROM {t}')
        print(f"{t}: {c.fetchone()[0]} rows")
    except Exception as e:
        print(f"{t}: ERROR - {e}")
    try:
        c.execute(f'PRAGMA table_info({t})')
        cols = [r[1] for r in c.fetchall()]
        print(f"  Columns: {cols}")
    except Exception as e:
        print(f"  Columns: ERROR - {e}")
    try:
        c.execute(f'SELECT * FROM {t} LIMIT 1')
        print(f"  Sample: {c.fetchone()}")
    except Exception as e:
        print(f"  Sample: ERROR - {e}")
conn.close()
