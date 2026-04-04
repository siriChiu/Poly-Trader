import sqlite3, os, json

db_files = []
for root, dirs, files in os.walk('/home/kazuha/Poly-Trader/data'):
    for f in files:
        path = os.path.join(root, f)
        sz = os.path.getsize(path)
        db_files.append((path, sz))

# Sort by size
db_files.sort(key=lambda x: x[1], reverse=True)
print("All files in data/ directory:")
for p, sz in db_files[:30]:
    print(f"  {p}: {sz} bytes")

# Check all db files
for path, sz in db_files:
    if not path.endswith('.db'):
        continue
    if sz == 0:
        print(f"\n{path}: EMPTY")
        continue
    conn = sqlite3.connect(path)
    c = conn.cursor()
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        print(f"\n{path}: {len(tables)} tables")
        for t in tables[:8]:
            c.execute(f'SELECT COUNT(*) FROM {t}')
            cnt = c.fetchone()[0]
            print(f'  {t}: {cnt} rows')
            if cnt > 0:
                c.execute(f'PRAGMA table_info({t})')
                cols = [r[1] for r in c.fetchall()]
                n_cols = len(cols)
                print(f'    Cols({n_cols}): {cols[:20]}')
                c.execute(f'SELECT * FROM {t} LIMIT 1')
                row = c.fetchone()
                print(f'    Sample: {str(row)[:200]}...')
    except Exception as e:
        print(f"  Error: {e}")
    conn.close()
