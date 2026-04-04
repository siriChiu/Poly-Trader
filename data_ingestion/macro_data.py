#!/usr/bin/env python3
"""VIX/DXY collector module — live fetches macro data from Yahoo Finance."""
from urllib.request import urlopen, Request
import json, ssl
from datetime import datetime, timezone

_ctx = ssl.create_default_context()
_HEADERS = {'User-Agent': 'Mozilla/5.0'}


def fetch_vix_dxy_latest():
    """Fetch the most recent VIX and DXY values from Yahoo Finance.
    
    Returns:
        dict: {'vix_value': float|None, 'dxy_value': float|None,
               'vix_timestamp': datetime|None, 'dxy_timestamp': datetime|None}
    """
    result = {'vix_value': None, 'dxy_value': None,
              'vix_timestamp': None, 'dxy_timestamp': None}
    
    for symbol, vkey, tkey in [('%5EVIX', 'vix_value', 'vix_timestamp'),
                                 ('DX-Y.NYB', 'dxy_value', 'dxy_timestamp')]:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1h"
            req = Request(url, headers=_HEADERS)
            resp = urlopen(req, context=_ctx, timeout=10)
            data = json.loads(resp.read().decode())
            result_data = data['chart']['result'][0]
            timestamps = result_data['timestamp']
            closes = result_data['indicators']['quote'][0]['close']
            # Find most recent non-None
            for ts, close in zip(timestamps, closes):
                if close is not None:
                    result[vkey] = close
                    result[tkey] = datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass  # Keep as None if fetch fails
    
    return result
