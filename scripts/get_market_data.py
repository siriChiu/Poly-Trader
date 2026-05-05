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

from database.models import RawMarketData, init_db
from datetime import datetime

session = init_db()
try:
    ticker = fetch_ticker('BTC/USDT')
    price = float(ticker.get('last')) if ticker else None
    if price:
        session.add(RawMarketData(timestamp=datetime.utcnow(), symbol='BTC/USDT', close_price=price, volume=float(ticker.get('vol24h') or 0)))
        session.commit()
        print(f'OKX price: {price}')

    lsr = last_float(fetch_long_short_ratio_series('BTC/USDT', period='4h', limit=1), 'longShortRatio', 'ratio')
    print(f'OKX LSR: {lsr}')

    row = (fetch_taker_volume_series('BTC/USDT', period='4h', limit=1) or [{}])[-1]
    buy = float(row.get('buyVol') or row.get('buyVolume') or 0)
    sell = float(row.get('sellVol') or row.get('sellVolume') or 0)
    print(f'OKX taker: {buy / sell if sell else None}')

    oi = fetch_current_open_interest('BTC/USDT')
    print(f'OKX OI: {oi}')

    funding = fetch_current_funding('BTC/USDT')
    print(f'OKX funding: {funding}')
finally:
    session.close()
