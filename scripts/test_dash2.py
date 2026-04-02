import sys
sys.path.insert(0,r"C:\Users\Kazuha\repo\Poly-Trader")
from sqlalchemy import create_engine,text; from config import load_config
e=create_engine(load_config()["database"]["url"])
with e.connect() as c:
    cols=[r[1] for r in c.execute(text("PRAGMA table_info(raw_market_data)")).fetchall()]
    print("raw_market_data cols:",cols)
