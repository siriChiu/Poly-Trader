#!/usr/bin/env python
"""Heartbeat data inspection script."""
import os, sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

from database.models import init_db, RawEvent, RawMarketData, FeaturesNormalized, TradeHistory, Labels

db = init_db("sqlite:///poly_trader.db")

# Counts
raw_evt = db.query(RawEvent).count()
raw_mkt = db.query(RawMarketData).count()
feat = db.query(FeaturesNormalized).count()
# Labels: sell_win based
labels_total = db.query(Labels).count()
sell_win_sum = db.query(Labels.label_sell_win).filter(Labels.label_sell_win != None).all()
sell_win_pos = sum(1 for r in sell_win_sum if r[0] == 1)
sell_win_any = len(sell_win_sum)
# Trade history
trades = db.query(TradeHistory).count()

print(f'raw_events={raw_evt}')
print(f'raw_market_data={raw_mkt}')
print(f'features_norm={feat}')
print(f'labels_total={labels_total}')
print(f'labels_sell_win={sell_win_any} (pos={sell_win_pos})')
print(f'trades={trades}')

# Latest market data
latest = db.query(RawMarketData).order_by(RawMarketData.timestamp.desc()).first()
if latest:
    print(f'latest_btc_price={latest.close_price}')
    print(f'latest_fng={latest.fear_greed_index}')
    print(f'latest_volume={latest.volume}')
    print(f'latest_oi_roc={latest.oi_roc}')
    print(f'latest_funding_rate={latest.funding_rate}')
    print(f'latest_timestamp={latest.timestamp}')
else:
    print('latest_raw=None')

# Check regime distribution in labels
from sqlalchemy import func
regime_counts = db.query(Labels.regime_label, func.count()).group_by(Labels.regime_label).all()
print(f'regime_distribution={regime_counts}')
