import sqlite3

for db_path in ['./poly_trader.db', './data/poly_trader.db', './scripts/poly_trader.db']:
    print(f"\n=== {db_path} ===")
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        print(f"Tables: {tables}")
        for t in tables:
            c.execute(f"SELECT COUNT(*) FROM [{t}]")
            print(f"  {t}: {c.fetchone()[0]} rows")
            c.execute(f"PRAGMA table_info([{t}])")
            cols = c.fetchall()
            if cols:
                col_names = [r[1] for r in cols]
                print(f"  Columns: {col_names[:20]}")
                c.execute(f"SELECT * FROM [{t}] LIMIT 2")
                print(f"  Sample: {c.fetchall()}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
