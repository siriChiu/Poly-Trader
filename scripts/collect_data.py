#!/usr/bin/env python3
"""Collect current data snapshot for heartbeat."""
import sys, os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from database.models import RawMarketData, FeaturesNormalized, Labels, init_db
from sqlalchemy import func
import os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_URL = f"sqlite:///{BASE}/poly_trader.db"
session = init_db(DB_URL)
raw_count = session.query(func.count(RawMarketData.id)).scalar()
feat_count = session.query(func.count(FeaturesNormalized.id)).scalar()
label_count = session.query(func.count(Labels.id)).scalar()
print(f"DB: raw={raw_count}, features={feat_count}, labels={label_count}")

# BTC price
import requests
r = requests.get('https://api.binance.com/api/v3/ticker/price', params={'symbol': 'BTCUSDT'})
if r.status_code == 200:
    btc_price = r.json()['price']
    print(f"BTC=${btc_price}")

# FNG
r2 = requests.get('https://api.alternative.me/fng/?limit=1')
if r2.status_code == 200:
    data = r2.json()['data'][0]
    print(f"FNG={data['value']} ({data['value_classification']})")

# Derivatives
r3 = requests.get('https://fapi.binance.com/futures/data/globalLongShortAccountRatio', params={'symbol': 'BTCUSDT', 'period': '4h', 'limit': 1})
if r3.status_code == 200 and r3.json():
    print(f"LSR={r3.json()[-1]['longShortRatio']}")

r4 = requests.get('https://fapi.binance.com/futures/data/takerlongshortRatio', params={'symbol': 'BTCUSDT', 'period': '4h', 'limit': 1})
if r4.status_code == 200 and r4.json():
    print(f"Taker={r4.json()[-1]['buySellRatio']}")

r5 = requests.get('https://fapi.binance.com/futures/data/openInterestHist', params={'symbol': 'BTCUSDT', 'period': '4h', 'limit': 1})
if r5.status_code == 200 and r5.json():
    print(f"OI={r5.json()[-1]['sumOpenInterest']}")

r6 = requests.get('https://fapi.binance.com/fapi/v1/premiumIndex', params={'symbol': 'BTCUSDT'})
if r6.status_code == 200:
    print(f"FR={r6.json()['lastFundingRate']}")

session.close()
print(f"Timestamp: {__import__('datetime').datetime.utcnow().isoformat()}")
