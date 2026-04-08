#!/usr/bin/env python
"""Check if we need to run collectors to update data."""
import sys, os, json, requests, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Check if collector scripts exist
for script in ['collectors/binance_collector.py', 'collectors/collect_market.py', 'main.py']:
    path = os.path.join(os.path.dirname(__file__), '..', script)
    if os.path.exists(path):
        print(f"EXISTS: {script}")
    else:
        print(f"MISSING: {script}")

# Check current data timestamp vs now
import sqlite3
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'poly_trader.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for table in ['raw_market_data', 'features_normalized', 'labels']:
    cur.execute(f'SELECT MAX(timestamp), COUNT(*) FROM {table}')
    row = cur.fetchone()
    print(f"{table}: max_ts={row[0]}, count={row[1]}")

conn.close()

# Get current BTC price from Binance
try:
    resp = requests.get('https://api.binance.com/api/v3/ticker/price?', params={'symbol': 'BTCUSDT'}, timeout=10)
    if resp.status_code == 200:
        price = resp.json()['price']
        print(f"\nCurrent BTC price from Binance: ${float(price):.2f}")
    else:
        print(f"\nBinance API error: {resp.status_code}")
except Exception as e:
    print(f"\nCould not get Binance price: {e}")

# Get Fear & Greed Index
try:
    resp = requests.get('https://api.alternative.me/fng/', timeout=10)
    if resp.status_code == 200:
        data = resp.json()['data'][0]
        print(f"Fear & Greed: {data['value']} ({data['value_classification']})")
except Exception as e:
    print(f"Could not get FNG: {e}")

# Get derivatives data
try:
    resp = requests.get('https://fapi.binance.com/fapi/v1/premiumIndex?', params={'symbol': 'BTCUSDT'}, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        print(f"Funding Rate: {data.get('lastFundingRate', 'N/A')}")
        print(f"Mark Price: ${float(data.get('markPrice', 0)):.2f}")
except Exception as e:
    print(f"Could not get derivatives: {e}")

# Get Open Interest
try:
    resp = requests.get('https://fapi.binance.com/fapi/v1/openInterest?', params={'symbol': 'BTCUSDT'}, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        print(f"Open Interest: {data.get('openInterest', 'N/A')} BTC")
except Exception as e:
    print(f"Could not get OI: {e}")

print(f"\nCurrent UTC time: {datetime.datetime.utcnow().isoformat()}")
