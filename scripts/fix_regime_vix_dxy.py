#!/usr/bin/env python3
"""
P0 Fix #H160: Fill regime_label, feat_vix, feat_dxy for features_normalized records where they are NULL.
Computes regime from price action, fetches latest VIX/DXY from Yahoo Finance.
"""
import sqlite3
import sys
from pathlib import Path
from urllib.request import urlopen, Request
import json, ssl
from datetime import datetime, timezone, timedelta
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

ctx = ssl.create_default_context()
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def fetch_yahoo_latest(symbol, range_str='6mo', interval='1d'):
    """Fetch daily price from Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_str}&interval={interval}"
    req = Request(url, headers=headers)
    try:
        resp = urlopen(req, context=ctx, timeout=15)
        data = json.loads(resp.read().decode())
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        series = {}
        for ts, close in zip(timestamps, closes):
            if close is not None:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
                series[dt] = close
        return series
    except Exception as e:
        print(f"Warning: Yahoo fetch failed for {symbol}: {e}")
        return {}

def compute_regime_for_timestamp(conn, ts_str):
    """Compute regime label for a given timestamp based on price action."""
    ts = datetime.fromisoformat(ts_str)
    ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
    
    # Get 288 hours (12 days) of price data before this timestamp
    rows = conn.execute(
        "SELECT close_price FROM raw_market_data WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 288",
        (ts_str,)
    ).fetchall()
    
    if len(rows) < 72:
        return None
    
    closes = np.array([r[0] for r in reversed(rows)], dtype=float)
    closes = closes[~np.isnan(closes)]
    
    if len(closes) < 72:
        return None
    
    # Calculate moving averages
    sma_20 = np.mean(closes[-20:])
    sma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else np.mean(closes)
    sma_144 = np.mean(closes[-144:]) if len(closes) >= 144 else np.mean(closes)
    
    price = closes[-1]
    
    # Bull: price > sma_20 > sma_50 > sma_144
    # Bear: price < sma_20 < sma_50 < sma_144
    # Chop: mixed signals
    
    bull_signals = sum([price > sma_20, sma_20 > sma_50, sma_50 > sma_144])
    bear_signals = sum([price < sma_20, sma_20 < sma_50, sma_50 < sma_144])
    
    if bull_signals >= 2:
        return 'bull'
    elif bear_signals >= 2:
        return 'bear'
    else:
        return 'chop'

def find_nearest_vix_dxy(target_ts, vix_series, dxy_series):
    """Find nearest VIX/DXY values within ±2 days."""
    best_vix = None
    best_dxy = None
    best_vix_d = float('inf')
    best_dxy_d = float('inf')
    
    for k, v in vix_series.items():
        d = abs((target_ts - k).total_seconds())
        if d < 172800 and d < best_vix_d:
            best_vix_d = d
            best_vix = v
    
    for k, v in dxy_series.items():
        d = abs((target_ts - k).total_seconds())
        if d < 172800 and d < best_dxy_d:
            best_dxy_d = d
            best_dxy = v
    
    return best_vix, best_dxy

def main():
    print("=== P0 Fix #H160: Fill regime_label, feat_vix, feat_dxy ===")
    
    conn = sqlite3.connect(str(PROJECT_ROOT / 'poly_trader.db'))
    
    # 1. Fetch VIX and DXY data (1y range for better coverage)
    print("\nFetching macro data from Yahoo Finance...")
    vix_daily = fetch_yahoo_latest('%5EVIX', '1y')
    dxy_daily = fetch_yahoo_latest('DX-Y.NYB', '1y')
    print(f"VIX: {len(vix_daily)} daily points, range: {min(vix_daily.values()):.2f}-{max(vix_daily.values()):.2f}" if vix_daily else "VIX: empty")
    print(f"DXY: {len(dxy_daily)} daily points, range: {min(dxy_daily.values()):.2f}-{max(dxy_daily.values()):.2f}" if dxy_daily else "DXY: empty")
    
    # 2. Find records with NULL feat_vix, feat_dxy, or regime_label
    total = conn.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
    vix_null = conn.execute('SELECT COUNT(*) FROM features_normalized WHERE feat_vix IS NULL').fetchone()[0]
    dxy_null = conn.execute('SELECT COUNT(*) FROM features_normalized WHERE feat_dxy IS NULL').fetchone()[0]
    regime_null = conn.execute("SELECT COUNT(*) FROM features_normalized WHERE regime_label IS NULL OR regime_label = ''").fetchone()[0]
    
    print(f"\nFeatures: {total} total")
    print(f"  NULL VIX: {vix_null}")
    print(f"  NULL DXY: {dxy_null}")
    print(f"  NULL/empty regime: {regime_null}")
    
    # 3. Fix VIX/DXY in features_normalized from raw_market_data
    if vix_null > 0 or dxy_null > 0:
        print("\nBackfilling VIX/DXY...")
        
        # First, backfill raw_market_data with Yahoo data
        raw_rows = conn.execute(
            "SELECT id, timestamp, close_price FROM raw_market_data WHERE vix_value IS NULL ORDER BY timestamp"
        ).fetchall()
        print(f"  raw_market_data rows needing VIX: {len(raw_rows)}")
        
        backfilled_raw = 0
        for row_id, ts_str, _ in raw_rows:
            try:
                ts = datetime.fromisoformat(ts_str)
                ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
            except:
                continue
            
            vix_val, dxy_val = find_nearest_vix_dxy(ts_naive, vix_daily, dxy_daily)
            if vix_val is not None or dxy_val is not None:
                conn.execute(
                    "UPDATE raw_market_data SET vix_value=?, dxy_value=? WHERE id=?",
                    (vix_val, dxy_val, row_id)
                )
                backfilled_raw += 1
        
        conn.commit()
        print(f"  Backfilled raw_market_data: {backfilled_raw} rows")
        
        # Now copy from raw_market_data to features_normalized
        vix_updated = conn.execute("""
            UPDATE features_normalized 
            SET feat_vix = (
                SELECT r.vix_value FROM raw_market_data r 
                WHERE r.timestamp = features_normalized.timestamp
            )
            WHERE feat_vix IS NULL 
            AND EXISTS (
                SELECT 1 FROM raw_market_data r 
                WHERE r.timestamp = features_normalized.timestamp AND r.vix_value IS NOT NULL
            )
        """).rowcount
        conn.commit()
        print(f"  Updated features_normalized feat_vix: {vix_updated}")
        
        dxy_updated = conn.execute("""
            UPDATE features_normalized 
            SET feat_dxy = (
                SELECT r.dxy_value FROM raw_market_data r 
                WHERE r.timestamp = features_normalized.timestamp
            )
            WHERE feat_dxy IS NULL 
            AND EXISTS (
                SELECT 1 FROM raw_market_data r 
                WHERE r.timestamp = features_normalized.timestamp AND r.dxy_value IS NOT NULL
            )
        """).rowcount
        conn.commit()
        print(f"  Updated features_normalized feat_dxy: {dxy_updated}")
    
    # 4. Fix regime_label for NULL/empty records
    if regime_null > 0:
        print(f"\nComputing regime labels for {regime_null} records...")
        
        null_rows = conn.execute(
            "SELECT id, timestamp FROM features_normalized WHERE regime_label IS NULL OR regime_label = '' ORDER BY timestamp"
        ).fetchall()
        
        updated_regime = 0
        for row_id, ts_str in null_rows:
            regime = compute_regime_for_timestamp(conn, ts_str)
            if regime:
                conn.execute(
                    "UPDATE features_normalized SET regime_label=? WHERE id=?",
                    (regime, row_id)
                )
                updated_regime += 1
            
            if updated_regime % 100 == 0:
                conn.commit()
        
        conn.commit()
        print(f"  Updated regime_label: {updated_regime}/{len(null_rows)}")
    
    # 5. Verify
    print("\n=== Verification ===")
    total = conn.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
    vix_count = conn.execute('SELECT COUNT(*) FROM features_normalized WHERE feat_vix IS NOT NULL').fetchone()[0]
    dxy_count = conn.execute('SELECT COUNT(*) FROM features_normalized WHERE feat_dxy IS NOT NULL').fetchone()[0]
    regime_counts = conn.execute(
        "SELECT regime_label, COUNT(*) FROM features_normalized GROUP BY regime_label ORDER BY COUNT(*) DESC"
    ).fetchall()
    
    print(f"Total features: {total}")
    print(f"  VIX filled: {vix_count}/{total} ({vix_count/total*100:.1f}%)")
    print(f"  DXY filled: {dxy_count}/{total} ({dxy_count/total*100:.1f}%)")
    for regime, count in regime_counts:
        print(f"  regime='{regime}': {count}")
    
    conn.close()
    print("\n✅ P0 Fix #H160 complete")

if __name__ == "__main__":
    main()
