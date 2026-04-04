#!/usr/bin/env python3
"""VIX/DXY collector — fetches latest macro data and updates newest raw record."""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from urllib.request import urlopen, Request
import json, ssl, sqlite3
from datetime import datetime, timezone

ctx = ssl.create_default_context()
headers = {'User-Agent': 'Mozilla/5.0'}

def fetch_yahoo_latest(symbol, range_str='5d', interval='1h'):
    """Fetch the most recent hourly value from Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_str}&interval={interval}"
    req = Request(url, headers=headers)
    resp = urlopen(req, context=ctx, timeout=15)
    data = json.loads(resp.read().decode())
    result = data['chart']['result'][0]
    timestamps = result['timestamp']
    closes = result['indicators']['quote'][0]['close']
    # Return most recent non-None value
    latest_ts = None
    latest_close = None
    for ts, close in zip(timestamps, closes):
        if close is not None:
            latest_ts = datetime.fromtimestamp(ts, tz=timezone.utc)
            latest_close = close
    return latest_close, latest_ts

def update_latest_raw_vix_dxy():
    """Update the most recent raw_market_data record with VIX and DXY values."""
    vix_val, vix_ts = fetch_yahoo_latest('%5EVIX')
    dxy_val, dxy_ts = fetch_yahoo_latest('DX-Y.NYB')
    
    print(f"VIX: {vix_val} (at {vix_ts})")
    print(f"DXY: {dxy_val} (at {dxy_ts})")
    
    conn = sqlite3.connect(str(PROJECT_ROOT / 'poly_trader.db'))
    cur = conn.cursor()
    
    # Get latest raw record
    latest = cur.execute('SELECT id, timestamp, vix_value, dxy_value FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    if latest is None:
        print("No raw_market_data records found.")
        conn.close()
        return False
    
    record_id = latest[0]
    old_vix = latest[2]
    old_dxy = latest[3]
    print(f"Updating latest raw record (id={record_id}):")
    print(f"  VIX: {old_vix}  -> {vix_val}")
    print(f"  DXY: {old_dxy}  -> {dxy_val}")
    
    cur.execute('UPDATE raw_market_data SET vix_value=?, dxy_value=? WHERE id=?',
                (vix_val, dxy_val, record_id))
    conn.commit()
    conn.close()
    print("✅ Updated successfully.")
    return True

if __name__ == '__main__':
    update_latest_raw_vix_dxy()
