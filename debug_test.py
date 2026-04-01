import os
import sys

os.chdir("C:/Users/Kazuha/repo/poly-trader")
sys.path.insert(0, "C:/Users/Kazuha/repo/poly-trader")

from config import load_config
from database.models import init_db, RawMarketData

cfg = load_config()
print("DB URL:", cfg.get("database", {}).get("url"))

session = init_db(cfg["database"]["url"])

# Query RawMarketData with columns that match what's in DB
try:
    count = session.query(RawMarketData).count()
    print("RawMarketData count:", count)
except Exception as e:
    print("RawMarketData query failed:", e)
    # Check what columns SQLAlchemy sees
    cols = [c.key for c in RawMarketData.__table__.columns]
    print("SQLAlchemy columns:", cols)
    
    # What columns does sqlite have?
    import sqlite3
    conn = sqlite3.connect("poly_trader.db")
    c = conn.cursor()
    c.execute("PRAGMA table_info(raw_market_data)")
    db_cols = [r[1] for r in c.fetchall()]
    print("DB columns:", db_cols)
    session.close()
