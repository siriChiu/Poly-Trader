#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_ingestion.okx_public import (
    fetch_current_funding,
    fetch_current_open_interest,
    fetch_long_short_ratio_series,
    fetch_taker_volume_series,
    fetch_ticker,
    last_float,
)

import urllib.request

results = {}

try:
    req = urllib.request.urlopen('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', timeout=10)
    btc_data = json.loads(req.read())
    results['btc_price'] = btc_data['bitcoin']['usd']
except Exception as e:
    results['btc_price_error'] = str(e)

try:
    ticker = fetch_ticker('BTC/USDT')
    if ticker:
        results['price_change_pct'] = float(ticker.get('sodUtc8') or ticker.get('sodUtc0') or 0.0)
        results['quote_volume'] = float(ticker.get('volCcy24h') or ticker.get('vol24h') or 0.0)
        results['okx_last'] = float(ticker.get('last'))
except Exception as e:
    results['okx_24h_error'] = str(e)

try:
    funding = fetch_current_funding('BTC/USDT')
    results['funding_rate'] = funding
except Exception as e:
    results['funding_error'] = str(e)

try:
    oi = fetch_current_open_interest('BTC/USDT')
    results['open_interest'] = oi
except Exception as e:
    results['oi_error'] = str(e)

try:
    lsr_rows = fetch_long_short_ratio_series('BTC/USDT', period='5m', limit=1)
    results['long_short_ratio'] = last_float(lsr_rows, 'longShortRatio', 'ratio')
except Exception as e:
    results['lsr_error'] = str(e)

try:
    taker_rows = fetch_taker_volume_series('BTC/USDT', period='5m', limit=1)
    row = taker_rows[-1] if taker_rows else {}
    buy = float(row.get('buyVol') or row.get('buyVolume') or 0)
    sell = float(row.get('sellVol') or row.get('sellVolume') or 0)
    results['taker_buy_sell_ratio'] = buy / sell if sell else results.get('long_short_ratio')
except Exception:
    try:
        results['taker_buy_sell_ratio'] = float(results.get('long_short_ratio', 1.0))
        results['taker_note'] = 'using OKX LSR proxy'
    except Exception as e:
        results['taker_error'] = f'OKX taker + LSR fallback failed: {e}'

try:
    req = urllib.request.urlopen('https://api.alternative.me/fng/?limit=1', timeout=10)
    fng_data = json.loads(req.read())
    fng_val = fng_data['data'][0]['value']
    results['fear_greed'] = int(fng_val)
    results['fear_greed_label'] = fng_data['data'][0]['value_classification']
except Exception as e:
    results['fng_error'] = str(e)

with open(PROJECT_ROOT / 'data/live_market_data.json', 'w') as f:
    json.dump(results, f, indent=2)
print(json.dumps(results, indent=2))
