#!/usr/bin/env python3
"""Quick DB inspection for heartbeat."""
import sqlite3
conn = sqlite3.connect("/home/kazuha/Poly-Trader/data/poly_trader.db")
c = conn.cursor()
for t in c.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'").fetchall():
    count = c.execute(f"select count(*) from {t[0]}").fetchone()[0]
    print(f"{t[0]}: {count}")
conn.close()
