import sys
sys.path.insert(0,r"C:\Users\Kazuha\repo\Poly-Trader")
from sqlalchemy import create_engine, text
from config import load_config
cfg=load_config(); e=create_engine(cfg["database"]["url"])
with e.connect() as c:
    r=c.execute(text("SELECT r.timestamp,r.close_price FROM raw_market_data r JOIN features_normalized f ON f.timestamp=r.timestamp ORDER BY r.timestamp DESC LIMIT 1")).fetchone()
    print("JOIN:", r)
with e.connect() as c:
    r=c.execute(text("SELECT timestamp,close_price FROM raw_market_data ORDER BY timestamp DESC LIMIT 1")).fetchone()
    print("Raw last:", r)
