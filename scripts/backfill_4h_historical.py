#!/usr/bin/env python3
"""回補歷史 4H 特徵到 DB — 從 10% 密度 → 100%"""
import sys, os
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

import math
import sqlite3
import numpy as np
import ccxt
from datetime import datetime

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'

# ─── 4H Indicator Calculations ───

def ema(data, period):
    """Exponential Moving Average."""
    k = 2.0 / (period + 1)
    out = [data[0]]
    for x in data[1:]:
        out.append(out[-1] * (1 - k) + x * k)
    return out

def rsi(closes, period=14):
    n = len(closes)
    out = [50.0] * n
    if n < period + 1:
        return out
    gains = np.maximum(np.diff(closes), 0)
    losses = np.maximum(-np.diff(closes), 0)
    avg_g = np.mean(gains[:period])
    avg_l = np.mean(losses[:period])
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
        rs = avg_g / avg_l if avg_l > 0 else 100
        out[i] = float(100 - 100 / (1 + rs))
    return out

def macd_histogram(closes, fast=12, slow=26, signal=9):
    """Returns exactly len(closes) elements."""
    n = len(closes)
    out = [0.0] * n
    if n < slow + signal:
        return out
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    macd_valid = macd_line[slow - 1:]  # starts at index slow-1
    signal_line = ema(macd_valid, signal)
    hist_valid = [m - s for m, s in zip(macd_valid[signal - 1:], signal_line[signal - 1:])]
    start_idx = (slow - 1) + (signal - 1)  # 32
    for i, v in enumerate(hist_valid):
        if start_idx + i < n:
            out[start_idx + i] = v
    return out

def bollinger_pct_b(closes, period=20, std_mult=2):
    if len(closes) < period:
        return [0.5] * len(closes)
    out = []
    for i in range(len(closes)):
        if i < period - 1:
            out.append(0.5)
            continue
        window = closes[i - period + 1:i + 1]
        ma = np.mean(window)
        std = np.std(window)
        if std < 1e-10:
            out.append(0.5)
        else:
            out.append(float((closes[i] - ma) / (std_mult * std)))
    return out

def swing_highs_lows(highs, lows, window=10):
    """Detect swing high/low points. Returns distance to nearest swing low."""
    n = len(highs)
    swing_lows = []
    for i in range(window, n - window):
        is_low = True
        for j in range(i - window, i + window + 1):
            if j == i:
                continue
            if lows[j] <= lows[i]:
                is_low = False
                break
        if is_low:
            swing_lows.append((i, lows[i]))

    # For each candle, compute distance (%) to nearest swing low
    dist_to_swing = []
    for i in range(n):
        current = lows[i]
        min_dist_pct = 100.0
        for idx, low_val in swing_lows:
            if idx > i:  # Only look at past swing lows
                dist_pct = (current - low_val) / low_val * 100 if low_val > 0 else 100
                if dist_pct < min_dist_pct:
                    min_dist_pct = dist_pct
        dist_to_swing.append(min_dist_pct)
    return dist_to_swing

def ma_order(closes):
    """MA alignment score: +1 if bullish order, -1 if bearish, 0 if mixed."""
    if len(closes) < 200:
        return [0.0] * len(closes)
    ma5 = ema(closes, 5)
    ma10 = ema(closes, 10)
    ma20 = ema(closes, 20)
    ma50 = ema(closes, 50)
    ma100 = ema(closes, 100)
    ma200 = ema(closes, 200)
    out = []
    for i in range(len(closes)):
        if i < 200:
            out.append(0.0)
            continue
        if ma5[i] > ma10[i] > ma20[i] > ma50[i] > ma100[i] > ma200[i]:
            out.append(1.0)
        elif ma5[i] < ma10[i] < ma20[i] < ma50[i] < ma100[i] < ma200[i]:
            out.append(-1.0)
        else:
            out.append(0.0)
    return out

# ─── Main Backfill ───

def main():
    print("=== 4H Historical Backfill ===")
    start = datetime.now()

    # 1. Fetch 2 years of 4H candles from Binance (paginate)
    print("[1/5] Fetching 4H candles from Binance...")
    exchange = ccxt.binance({"enableRateLimit": True})
    # Need ~2200 candles to cover DB range (2025-04 to 2026-04)
    # Use since parameter to paginate backwards
    ohlcv_all = []
    # Start from earliest known DB timestamp
    earliest_ts = int(datetime(2025, 4, 1).timestamp() * 1000)
    since = earliest_ts
    while True:
        ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", since=since, limit=1000)
        if not ohlcv:
            break
        ohlcv_all.extend(ohlcv)
        since = ohlcv[-1][0] + 1
        print(f"  Fetched {len(ohlcv_all)} candles so far...")
        if len(ohlcv) < 1000:
            break
        # Safety: stop if we have enough
        if len(ohlcv_all) >= 3000:
            break
    print(f"  Total: {len(ohlcv_all)} 4H candles")

    # 2. Compute 4H indicators
    print("[2/5] Computing 4H indicators...")
    timestamps_4h = [o[0] for o in ohlcv_all]
    opens = np.array([o[1] for o in ohlcv_all], dtype=float)
    highs = np.array([o[2] for o in ohlcv_all], dtype=float)
    lows = np.array([o[3] for o in ohlcv_all], dtype=float)
    closes = np.array([o[4] for o in ohlcv_all], dtype=float)
    volumes = np.array([o[5] for o in ohlcv_all], dtype=float)

    ma50 = ema(closes.tolist(), 50)
    ma20 = ema(closes.tolist(), 20)
    bias50 = [(c - m) / m * 100 if m > 0 else 0 for c, m in zip(closes, ma50)]
    bias20 = [(c - m) / m * 100 if m > 0 else 0 for c, m in zip(closes, ma20)]
    rsi14 = rsi(closes.tolist(), 14)
    macd_hist = macd_histogram(closes.tolist())
    bb_pct = bollinger_pct_b(closes.tolist())
    ma_ord = ma_order(closes.tolist())

    swing_dists = swing_highs_lows(highs.tolist(), lows.tolist(), window=10)

    # Build lookup: timestamp_ms → 4H features
    print(f"[3/5] Building feature lookup ({len(timestamps_4h)} candles)...")
    feature_map = {}
    for i in range(len(timestamps_4h)):
        ts = timestamps_4h[i]
        feature_map[ts] = {
            'bias50': bias50[i],
            'bias20': bias20[i],
            'rsi14': rsi14[i],
            'macd_hist': macd_hist[i],
            'bb_pct': bb_pct[i],
            'ma_order': ma_ord[i],
            'dist_swing': swing_dists[i],
        }

    # 3. Map to DB timestamps
    print("[4/5] Mapping to DB timestamps...")
    conn = sqlite3.connect(DB_PATH)

    # Get all feature timestamps that need filling
    rows = conn.execute("""
        SELECT id, timestamp FROM features_normalized 
        WHERE feat_4h_bias50 IS NULL 
        ORDER BY timestamp
    """).fetchall()
    total_null = len(rows)
    print(f"  Rows with NULL 4H features: {total_null}")

    # Build sorted list of 4H timestamps for bisect
    ts_list = sorted(feature_map.keys())
    # Use bisect to find nearest previous 4H candle
    import bisect

    updated = 0
    batch_updates = []
    BATCH_SIZE = 500

    for row_id, feat_ts_str in rows:
        # Parse timestamp
        if 'T' in feat_ts_str:
            feat_ts = datetime.fromisoformat(feat_ts_str.replace('Z', '')).timestamp() * 1000
        else:
            feat_ts = datetime.fromisoformat(feat_ts_str).timestamp() * 1000

        # Find nearest 4H candle (previous or same)
        idx = bisect.bisect_right(ts_list, feat_ts) - 1
        if idx < 0:
            continue  # Before any 4H data

        ts_4h = ts_list[idx]
        f = feature_map[ts_4h]

        batch_updates.append((
            f['bias50'], f['bias20'], f['rsi14'], f['macd_hist'],
            f['bb_pct'], f['ma_order'], f['dist_swing'], row_id
        ))
        updated += 1

        if len(batch_updates) >= BATCH_SIZE:
            conn.executemany("""
                UPDATE features_normalized 
                SET feat_4h_bias50=?, feat_4h_bias20=?, feat_4h_rsi14=?, 
                    feat_4h_macd_hist=?, feat_4h_bb_pct_b=?, feat_4h_ma_order=?,
                    feat_4h_dist_swing_low=?
                WHERE id=?
            """, batch_updates)
            conn.commit()
            batch_updates = []
            print(f"  Updated {updated}/{total_null}...")

    # Final batch
    if batch_updates:
        conn.executemany("""
            UPDATE features_normalized 
            SET feat_4h_bias50=?, feat_4h_bias20=?, feat_4h_rsi14=?, 
                feat_4h_macd_hist=?, feat_4h_bb_pct_b=?, feat_4h_ma_order=?,
                feat_4h_dist_swing_low=?
            WHERE id=?
        """, batch_updates)
        conn.commit()

    # 4. Verify
    print("[5/5] Verification...")
    count = conn.execute("SELECT COUNT(*) FROM features_normalized WHERE feat_4h_bias50 IS NOT NULL").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
    print(f"  4H features filled: {count}/{total} ({count/total*100:.1f}%)")

    conn.close()
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  Updated {updated} rows")

    # Re-run IC analysis
    print("\n=== Re-running IC analysis ===")
    from scripts.full_ic import main as ic_main
    ic_main()

if __name__ == '__main__':
    main()
