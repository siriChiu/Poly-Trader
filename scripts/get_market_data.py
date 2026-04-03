#!/usr/bin/env python3
"""Get BTC price, FNG, and derivatives data."""
import requests
from datetime import datetime

# BTC Price
try:
    r = requests.get('https://api.binance.com/api/v3/ticker/price', params={'symbol': 'BTCUSDT'}, timeout=15)
    if r.status_code == 200:
        btc_price = r.json()['price']
        print(f"BTC=${btc_price}")
    else:
        print("BTC=N/A (API error)")
except Exception as e:
    print(f"BTC=N/A ({e})")

# Fear and Greed Index
try:
    r2 = requests.get('https://api.alternative.me/fng/?limit=1', timeout=15)
    if r2.status_code == 200:
        data = r2.json()['data'][0]
        print(f"FNG={data['value']} ({data['value_classification']})")
    else:
        print("FNG=N/A")
except Exception as e:
    print(f"FNG=N/A ({e})")

# Long/Short Ratio
try:
    r3 = requests.get('https://fapi.binance.com/futures/data/globalLongShortAccountRatio', params={'symbol': 'BTCUSDT', 'period': '4h', 'limit': 1}, timeout=15)
    if r3.status_code == 200 and r3.json():
        print(f"LSR={r3.json()[-1]['longShortRatio']}")
    else:
        print("LSR=N/A")
except Exception as e:
    print(f"LSR=N/A ({e})")

# Taker Buy/Sell
try:
    r4 = requests.get('https://fapi.binance.com/futures/data/takerlongshortRatio', params={'symbol': 'BTCUSDT', 'period': '4h', 'limit': 1}, timeout=15)
    if r4.status_code == 200 and r4.json():
        print(f"Taker={r4.json()[-1]['buySellRatio']}")
    else:
        print("Taker=N/A")
except Exception as e:
    print(f"Taker=N/A ({e})")

# Open Interest
try:
    r5 = requests.get('https://fapi.binance.com/futures/data/openInterestHist', params={'symbol': 'BTCUSDT', 'period': '4h', 'limit': 1}, timeout=15)
    if r5.status_code == 200 and r5.json():
        print(f"OI={r5.json()[-1]['sumOpenInterest']}")
    else:
        print("OI=N/A")
except Exception as e:
    print(f"OI=N/A ({e})")

# Funding Rate
try:
    r6 = requests.get('https://fapi.binance.com/fapi/v1/premiumIndex', params={'symbol': 'BTCUSDT'}, timeout=15)
    if r6.status_code == 200:
        print(f"FR={r6.json()['lastFundingRate']}")
    else:
        print("FR=N/A")
except Exception as e:
    print(f"FR=N/A ({e})")

print(f"Timestamp: {datetime.utcnow().isoformat()}")
