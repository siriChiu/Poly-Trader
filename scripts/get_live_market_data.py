#!/usr/bin/env python3
"""Get current BTC price and derivatives from public APIs"""
import json, urllib.request

results = {}

# BTC price from CoinGecko
try:
    req = urllib.request.urlopen('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', timeout=10)
    btc_data = json.loads(req.read())
    results['btc_price'] = btc_data['bitcoin']['usd']
except Exception as e:
    results['btc_price_error'] = str(e)

# Binance Ticker 24h
try:
    req = urllib.request.urlopen('https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT', timeout=10)
    ticker = json.loads(req.read())
    results['price_change_pct'] = float(ticker['priceChangePercent'])
    results['quote_volume'] = float(ticker['quoteVolume'])
except Exception as e:
    results['binance_24h_error'] = str(e)

# Funding rate
try:
    req = urllib.request.urlopen('https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT', timeout=10)
    funding = json.loads(req.read())
    results['funding_rate'] = funding['lastFundingRate']
    results['mark_price'] = funding['markPrice']
except Exception as e:
    results['funding_error'] = str(e)

# Open Interest
try:
    req = urllib.request.urlopen('https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT', timeout=10)
    oi = json.loads(req.read())
    results['open_interest'] = oi['openInterest']
except Exception as e:
    results['oi_error'] = str(e)

# Long/Short ratio
try:
    req = urllib.request.urlopen('https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1', timeout=10)
    lsr = json.loads(req.read())
    results['long_short_ratio'] = lsr[0]['longShortRatio']
except Exception as e:
    results['lsr_error'] = str(e)

# Taker buy/sell volume
try:
    req = urllib.request.urlopen('https://fapi.binance.com/fapi/v1/takerlongshortratio?symbol=BTCUSDT&period=5m&limit=1', timeout=10)
    tkr = json.loads(req.read())
    results['taker_buy_sell_ratio'] = tkr[0]['buySellRatio']
except Exception as e:
    results['taker_error'] = str(e)

with open('/home/kazuha/Poly-Trader/data/live_market_data.json', 'w') as f:
    json.dump(results, f, indent=2)

print(json.dumps(results, indent=2))
