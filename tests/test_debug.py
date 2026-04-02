import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from config import load_config
from database.models import init_db, RawMarketData

cfg = load_config()
session = init_db(cfg["database"]["url"])
row = session.query(RawMarketData).first()
print(f"has eye_dist: {hasattr(row, 'eye_dist')}")
print(f"eye_dist = {row.eye_dist}")
print(f"ear_prob = {row.ear_prob}")
print(f"stablecoin_mcap = {row.stablecoin_mcap}")
session.close()
