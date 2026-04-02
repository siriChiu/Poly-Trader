import sqlite3
conn = sqlite3.connect(r"C:\Users\Kazuha\repo\Poly-Trader\poly_trader.db")
print("labels columns:", [r[1] for r in conn.execute("PRAGMA table_info(labels)").fetchall()])
print("labels sample:", conn.execute("SELECT * FROM labels LIMIT 2").fetchall())
conn.close()
