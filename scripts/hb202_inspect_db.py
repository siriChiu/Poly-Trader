import sqlite3

for db_path in ["./poly_trader.db", "./data/poly_trader.db", "./scripts/poly_trader.db"]:
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"\n=== {db_path} ===")
        print(f"Tables: {[t[0] for t in tables]}")
        for t in tables:
            name = t[0]
            count = cur.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f"  {name}: {count} rows")
        conn.close()
    except Exception as e:
        print(f"\n=== {db_path} === ERROR: {e}")
