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

# Taker buy/sell volume — Binance API deprecated (404), use LSR ratio as proxy
try:
    req = urllib.request.urlopen('https://fapi.binance.com/futures/data/takerBuySellVol?symbol=BTCUSDT&period=5m&limit=1', timeout=10)
    tkr = json.loads(req.read())
    results['taker_buy_sell_ratio'] = tkr[0]['buySellRatio']
except Exception:
    try:
        # Fallback: derive taker proxy from existing LSR data
        lsr_val = float(results.get('long_short_ratio', 1.0))
        results['taker_buy_sell_ratio'] = lsr_val  # LSR as proxy
        results['taker_note'] = 'taker API deprecated, using LSR proxy'
    except Exception as e:
        results['taker_error'] = f'Binance taker API deprecated + LSR fallback failed: {e}'

# Fear & Greed Index
try:
    req = urllib.request.urlopen('https://api.alternative.me/fng/?limit=1', timeout=10)
    fng_data = json.loads(req.read())
    fng_val = fng_data['data'][0]['value']
    results['fear_greed'] = int(fng_val)
    results['fear_greed_label'] = fng_data['data'][0]['value_classification']
except Exception as e:
    results['fng_error'] = str(e)

with open('/home/kazuha/Poly-Trader/data/live_market_data.json', 'w') as f:
    json.dump(results, f, indent=2)

print(json.dumps(results, indent=2))
