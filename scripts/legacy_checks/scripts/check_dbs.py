import sqlite3, os, json

for db_name in ['data/stock.db', 'data/market.db']:
    db_path = db_name
    if not os.path.exists(db_path):
        print(f'{db_path}: NOT FOUND')
        continue
    sz = os.path.getsize(db_path)
    print(f'{db_path}: {sz} bytes')
    if sz == 0:
        continue
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    print(f'  Tables ({len(tables)}): {tables[:20]}')
    for t in tables[:5]:
        c.execute(f'SELECT COUNT(*) FROM {t}')
        cnt = c.fetchone()[0]
        print(f'  {t}: {cnt} rows')
        c.execute(f'PRAGMA table_info({t})')
        cols = [r[1] for r in c.fetchall()]
        print(f'    Columns: {cols}')
        if cnt > 0:
            c.execute(f'SELECT * FROM {t} LIMIT 1')
            print(f'    Sample: {c.fetchone()}')
    conn.close()
    print()
