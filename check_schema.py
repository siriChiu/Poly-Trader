#!/usr/bin/env python3
"""Check database schema"""
import sqlite3

db_path = "/home/kazuha/Poly-Trader/poly_trader.db"
db = sqlite3.connect(db_path)

# List all tables
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])

for table in tables:
    name = table[0]
    cols = db.execute(f"PRAGMA table_info({name})").fetchall()
    print(f"\nTable '{name}':")
    for col in cols:
        print(f"  {col[1]:30s} {col[2]}")

# Count rows
for table in tables:
    name = table[0]
    try:
        cnt = db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"  {name}: {cnt} rows")
    except:
        pass

db.close()
