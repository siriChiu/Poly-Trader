#!/usr/bin/env python3
"""Macro data collector — VIX, DXY, NQ from Yahoo Finance."""
from urllib.request import urlopen, Request
import json, ssl, math
from datetime import datetime, timezone

_ctx = ssl.create_default_context()
_HEADERS = {'User-Agent': 'Mozilla/5.0'}

SYMBOLS = {
    '%5EVIX':   ('vix_value', 'vix_timestamp', 'vix_history'),
    'DX-Y.NYB': ('dxy_value', 'dxy_timestamp', 'dxy_history'),
    'NQ=F':     ('nq_value',  'nq_timestamp',  'nq_history'),
}


def _fetch_yahoo(symbol, range_d='5d', interval='1h'):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_d}&interval={interval}"
    req = Request(url, headers=_HEADERS)
    resp = urlopen(req, context=_ctx, timeout=10)
    data = json.loads(resp.read().decode())
    result = data['chart']['result'][0]
    timestamps = result['timestamp']
    closes = result['indicators']['quote'][0]['close']
    return [(ts, c) for ts, c in zip(timestamps, closes) if c is not None]


def fetch_macro_latest():
    result = {}
    for vkey, tkey, histkey in SYMBOLS.values():
        result[vkey] = None
        result[tkey] = None
        result[histkey] = []

    for symbol, (vkey, tkey, histkey) in SYMBOLS.items():
        try:
            data = _fetch_yahoo(symbol)
            for ts, close in data:
                result[vkey] = close
                result[tkey] = datetime.fromtimestamp(ts, tz=timezone.utc)
            result[histkey] = data
        except Exception:
            pass
    return result


def compute_nq_features(hist):
    if not hist or len(hist) < 2:
        return {'feat_nq_return_1h': 0.0, 'feat_nq_return_24h': 0.0}
    latest = hist[-1][1]
    prev_1h = hist[-2][1] if len(hist) >= 2 else latest
    prev_24h = hist[-min(24, len(hist))][1]
    ret_1h = (latest / prev_1h - 1) if prev_1h > 0 else 0
    ret_24h = (latest / prev_24h - 1) if prev_24h > 0 else 0
    return {
        'feat_nq_return_1h': -ret_1h,
        'feat_nq_return_24h': -ret_24h,
    }
