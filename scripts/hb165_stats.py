import sys, os
sys.path.insert(0, os.path.dirname(__file__))

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import load_config
from database.models import init_db, FeaturesNormalized, Labels, MarketData
from sqlalchemy import func
from datetime import datetime

cfg = load_config()
session = init_db(cfg['database']['url'])

# Data counts
raw_count = session.query(func.count()).select_from(FeaturesNormalized).scalar()
labels_count = session.query(func.count()).select_from(Labels).scalar()
sell_wins = session.query(func.sum(Labels.label_spot_long_win)).filter(Labels.label_spot_long_win.isnot(None)).scalar()

# BTC price
btc_rows = session.query(MarketData).filter(MarketData.symbol=='BTCUSDT').order_by(MarketData.timestamp.desc()).limit(1).all()

# Feature columns
feat_cols = [c.key for c in FeaturesNormalized.__table__.columns if c.key.startswith('feat_')]

# Latest label timestamp
latest_label = session.query(func.max(Labels.timestamp)).scalar()

print(f"Raw features: {raw_count}")
print(f"Labels: {labels_count}")
print(f"Sell wins: {sell_wins} ({sell_wins/labels_count*100:.1f}%)" if sell_wins else f"Sell wins: {sell_wins}")
print(f"Feature cols ({len(feat_cols)}): {feat_cols}")
print(f"Latest BTC price: {btc_rows[0].price if btc_rows else 'N/A'}")
print(f"Latest label ts: {latest_label}")

session.close()
