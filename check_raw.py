import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from config import load_config
from database.models import init_db, RawMarketData

cfg = load_config()
session = init_db(cfg["database"]["url"])

rows = session.query(RawMarketData).order_by(RawMarketData.timestamp.desc()).limit(10).all()
for r in rows:
    print(f"ts={r.timestamp}: price={r.close_price}, fng={r.fear_greed_index}, funding={r.funding_rate}, body={r.stablecoin_mcap}")

# Count non-null values
total = session.query(RawMarketData).count()
fr_count = session.query(RawMarketData).filter(RawMarketData.funding_rate.isnot(None)).count()
fng_count = session.query(RawMarketData).filter(RawMarketData.fear_greed_index.isnot(None)).count()
body_count = session.query(RawMarketData).filter(RawMarketData.stablecoin_mcap.isnot(None)).count()
print(f"\nTotal: {total}, funding_rate: {fr_count}, fng: {fng_count}, body: {body_count}")

session.close()
