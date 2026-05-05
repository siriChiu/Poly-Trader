#!/usr/bin/env python3
"""4H 距離特徵回填：用 4H 結構線計算 1m 即時價格到結構線的距離 (%)

核心理念：
  4H K線 → 畫出 MA50, MA200, 布林通道, 支撐線(swing low), 壓力線(swing high)
  1m 價格 → 每分鐘計算到這些水平線的距離百分比
  結果   → 每一分鐘距離都在變，8778 筆都是真實訓練信號（非 ffill 垃圾）

輸出特徵 (直接覆寫現有 feat_4h_* 欄位):
  feat_4h_bias50         : (1m_price - 4H_MA50) / 4H_MA50 * 100
  feat_4h_bias200        : (1m_price - 4H_MA200) / 4H_MA200 * 100
  feat_4h_bias20         : (1m_price - 4H_MA20) / 4H_MA20 * 100
  feat_4h_rsi14          : 1m 所屬時段對應的 4H RSI14 值
  feat_4h_macd_hist      : 1m 所屬時段對應的 4H MACD histogram
  feat_4h_bb_pct_b       : 1m 價格在 4H 布林通道中的位置
  feat_4h_dist_bb_lower  : 1m 價格距 4H 布林下軌距離 (%)
  feat_4h_dist_swing_low : (1m_price - 最近4H支撐) / 4H支撐 * 100
  feat_4h_ma_order       : MA 排列方向 (bullish / bearish / mixed)
  feat_4h_vol_ratio      : 4H 成交量 / 20 期平均量
"""
import sys
import os
import bisect
import sqlite3

import numpy as np
import ccxt
from datetime import datetime, timedelta

sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'


def _resolve_4h_fetch_start(ts_list, warmup_days=400):
    if not ts_list:
        raise ValueError('ts_list is empty')
    earliest_text = str(ts_list[0]).strip().replace('T', ' ').replace('Z', '')
    earliest_dt = datetime.fromisoformat(earliest_text)
    return earliest_dt - timedelta(days=max(int(warmup_days), 1))



def ema(data, period):
    k = 2.0 / (period + 1)
    out = [data[0]]
    for x in data[1:]:
        out.append(out[-1] * (1 - k) + x * k)
    return out


def compute_rsi(closes, period=14):
    n = len(closes)
    out = [50.0] * n
    if n < period + 1:
        return out
    closes_arr = np.array(closes, dtype=float)
    diffs = np.diff(closes_arr)
    gains = np.maximum(diffs, 0)
    losses = np.maximum(-diffs, 0)
    avg_g = np.mean(gains[:period])
    avg_l = np.mean(losses[:period])
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
        rs = avg_g / avg_l if avg_l > 0 else 100
        out[i] = 100.0 - 100.0 / (1.0 + rs)
    return out


def compute_macd_hist(closes, fast=12, slow=26, signal_p=9):
    n = len(closes)
    out = [0.0] * n
    if n < slow + signal_p:
        return out
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    macd_valid = macd_line[slow - 1:]
    signal_arr = ema(macd_valid, signal_p)
    start = (slow - 1) + (signal_p - 1)
    for i, sig in enumerate(signal_arr):
        idx = start + i
        if idx < n and i + signal_p - 1 < len(macd_valid):
            out[idx] = macd_valid[i + signal_p - 1] - sig
    return out


def find_swings_rolling(highs, lows, window=10):
    """Rolling swing levels. After each confirmed swing, the level persists."""
    n = len(highs)
    swing_low_level = [float(lows[0])] * n
    swing_high_level = [float(highs[0])] * n
    cur_low = float(lows[0])
    cur_high = float(highs[0])
    for i in range(window, min(n - window, n)):
        is_low = all(
            lows[j] >= lows[i]
            for j in range(max(0, i - window), min(n, i + window + 1))
            if j != i
        )
        is_high = all(
            highs[j] <= highs[i]
            for j in range(max(0, i - window), min(n, i + window + 1))
            if j != i
        )
        if is_low:
            cur_low = float(lows[i])
        if is_high:
            cur_high = float(highs[i])
        swing_low_level[i] = cur_low
        swing_high_level[i] = cur_high
    # Fill tail
    for i in range(max(0, n - window), n):
        swing_low_level[i] = cur_low
        swing_high_level[i] = cur_high
    return swing_low_level, swing_high_level


def main():
    print("=== 4H 距離特徵回填 ===\n")
    start = datetime.now()

    # ──────────────────────────────
    # 1. 讀 1m 價格
    # ──────────────────────────────
    print("[1/5] Loading 1m prices from raw_market_data...")
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT f.id, f.timestamp, r.close_price
        FROM features_normalized f
        JOIN raw_market_data r
            ON r.timestamp = f.timestamp AND r.symbol = f.symbol
        WHERE r.close_price IS NOT NULL
        ORDER BY f.timestamp
    """).fetchall()

    if not rows:
        print("  ERROR: no 1m prices found")
        return

    id_list    = [r[0] for r in rows]
    ts_list    = [str(r[1]) for r in rows]
    price_list = [float(r[2]) for r in rows]
    print(f"  {len(price_list)} rows")
    print(f"  價格 {min(price_list):,.0f} ~ {max(price_list):,.0f}")
    print(f"  時間 {ts_list[0]} ~ {ts_list[-1]}")

    # ──────────────────────────────
    # 2. 從 OKX 拉 4H K線（分頁，覆蓋完整範圍）
    # ──────────────────────────────
    print("\n[2/5] Fetching 4H candles from OKX...")
    exchange = ccxt.okx({"enableRateLimit": True})
    # 從最早 1m / feature 資料往前抓一段暖機窗口，避免把 2024 歷史誤截成 2025 才開始。
    earliest_dt = _resolve_4h_fetch_start(ts_list, warmup_days=400)
    since_ts = int(earliest_dt.timestamp() * 1000)

    ohlcv_all = []
    while True:
        candles = exchange.fetch_ohlcv(
            "BTC/USDT", "4h", since=since_ts, limit=1000
        )
        if not candles or len(candles) == 0:
            break
        ohlcv_all.extend(candles)
        since_ts = candles[-1][0] + 1
        if len(candles) < 1000:
            break
        print(f"  ...{len(ohlcv_all)} candles so far")

    print(f"  ✅ {len(ohlcv_all)} 4H candles fetched")

    if len(ohlcv_all) < 200:
        print("  ❌ 不足 200 根 4H K線，無法計算 MA200")
        return

    # ──────────────────────────────
    # 3. 計算 4H 結構水平線
    # ──────────────────────────────
    print("\n[3/5] Computing 4H structural levels...")

    # 時間排序
    combined = sorted(zip(
        [o[0] for o in ohlcv_all],
        [o[4] for o in ohlcv_all],
        [o[2] for o in ohlcv_all],
        [o[3] for o in ohlcv_all],
    ))
    ts_4h = np.array([x[0] for x in combined])
    c4h   = np.array([x[1] for x in combined], dtype=float)
    h4h   = np.array([x[2] for x in combined], dtype=float)
    l4h   = np.array([x[3] for x in combined], dtype=float)
    n4h   = len(c4h)

    # 各水平線
    ma20_arr  = ema(c4h.tolist(), 20)
    ma50_arr  = ema(c4h.tolist(), 50)
    ma200_arr = ema(c4h.tolist(), 200)
    rsi14_arr = compute_rsi(c4h.tolist(), 14)
    macd_h_arr = compute_macd_hist(c4h.tolist())
    swing_low, swing_high = find_swings_rolling(h4h.tolist(), l4h.tolist(), window=10)
    vol_ma20 = np.convolve(np.array([o[5] for o in ohlcv_all], dtype=float), np.ones(20) / 20.0, mode='same')
    vol_ratio_arr = np.where(vol_ma20 > 0, np.array([o[5] for o in ohlcv_all], dtype=float) / vol_ma20, 1.0)

    # 布林通道
    bb_upper = [0.0] * n4h
    bb_lower = [0.0] * n4h
    for i in range(19, n4h):
        w = c4h[i - 19 : i + 1]
        m = float(np.mean(w))
        s = float(np.std(w))
        bb_upper[i] = m + 2 * s
        bb_lower[i] = m - 2 * s
    for i in range(19):
        bb_upper[i] = c4h[i] * 1.01
        bb_lower[i] = c4h[i] * 0.99

    # MA 排列方向
    ma_order_arr = [0.0] * n4h
    for i in range(200, n4h):
        if (ma20_arr[i] > ma50_arr[i] > ma200_arr[i]
                and c4h[i] > ma20_arr[i]):
            ma_order_arr[i] = 1.0
        elif (ma20_arr[i] < ma50_arr[i] < ma200_arr[i]
              and c4h[i] < ma20_arr[i]):
            ma_order_arr[i] = -1.0

    # 顯示最新線位
    print(f"  MA50   = {ma50_arr[-1]:>10,.0f}")
    print(f"  MA200  = {ma200_arr[-1]:>10,.0f}")
    print(f"  RSI14  = {rsi14_arr[-1]:>10.1f}")
    print(f"  MACD-H = {macd_h_arr[-1]:>10.1f}")
    print(f"  SwingL = {swing_low[-1]:>10,.0f}")
    print(f"  SwingH = {swing_high[-1]:>10,.0f}")

    # ──────────────────────────────
    # 4. 對每根 1m K線 → 計算到 4H 結構線的距離
    # ──────────────────────────────
    print("\n[4/5] Computing per-1m distance features...")

    ts_4h_sorted = sorted(ts_4h)

    out_bias50  = [0.0] * len(price_list)
    out_bias200 = [0.0] * len(price_list)
    out_bias20  = [0.0] * len(price_list)
    out_rsi14   = [50.0] * len(price_list)
    out_macd_h  = [0.0] * len(price_list)
    out_bb_pct  = [0.5] * len(price_list)
    out_dist_bb_lower = [0.0] * len(price_list)
    out_swing_l = [0.0] * len(price_list)
    out_swing_h = [0.0] * len(price_list)
    out_ma_ord  = [0.0] * len(price_list)
    out_vol_ratio = [1.0] * len(price_list)

    filled = 0
    for i in range(len(price_list)):
        dt = datetime.fromisoformat(ts_list[i])
        ts_ms = int(dt.timestamp() * 1000)
        price = price_list[i]

        # 最近已完成的 4H K線
        pos = bisect.bisect_right(ts_4h_sorted, ts_ms) - 1
        if pos < 200:
            continue

        # 1m 價格到 4H 水平線的距離 %
        if ma50_arr[pos]:
            out_bias50[i] = (price - ma50_arr[pos]) / ma50_arr[pos] * 100.0
        if ma200_arr[pos]:
            out_bias200[i] = (price - ma200_arr[pos]) / ma200_arr[pos] * 100.0
        if ma20_arr[pos]:
            out_bias20[i] = (price - ma20_arr[pos]) / ma20_arr[pos] * 100.0
        out_rsi14[i]  = rsi14_arr[pos]
        out_macd_h[i] = macd_h_arr[pos]
        out_vol_ratio[i] = float(vol_ratio_arr[pos]) if np.isfinite(vol_ratio_arr[pos]) else 1.0
        if swing_low[pos]:
            out_swing_l[i] = (price - swing_low[pos]) / swing_low[pos] * 100.0
        if swing_high[pos]:
            out_swing_h[i] = (price - swing_high[pos]) / swing_high[pos] * 100.0
        out_ma_ord[i] = ma_order_arr[pos]

        # BB %B for 1m price in 4H channel
        bu = bb_upper[pos]
        bl = bb_lower[pos]
        if bu != bl:
            out_bb_pct[i] = (price - bl) / (bu - bl)
        if bl:
            out_dist_bb_lower[i] = (price - bl) / bl * 100.0

        filled += 1

    print(f"  ✅ {filled}/{len(price_list)} rows computed ({filled / len(price_list) * 100:.0f}%)")

    # 分布
    for name, arr in [
        ('bias50',  out_bias50),
        ('bias200', out_bias200),
        ('bias20',  out_bias20),
        ('sw_low',  out_swing_l),
        ('sw_high', out_swing_h),
        ('macd_h',  out_macd_h),
    ]:
        vals = [v for v in arr if v != 0] if name != 'sw_high' else [v for v in out_swing_h if v != 0]
        if vals and name != 'sw_high':
            a = np.array(vals)
            print(f"  {name:8s}: mean={a.mean():+.2f}%  std={a.std():.2f}%  range=[{a.min():+.2f}%, {a.max():+.2f}%]  n={len(vals)}")

    # ──────────────────────────────
    # 5. 寫回 DB
    # ──────────────────────────────
    print("\n[5/5] Writing to DB...")

    BATCH = 2000
    batch = []
    for i in range(len(price_list)):
        batch.append((
            out_bias50[i],  out_bias20[i], out_bias200[i],
            out_rsi14[i],   out_macd_h[i],
            out_bb_pct[i],  out_dist_bb_lower[i], out_ma_ord[i],
            out_swing_l[i], out_vol_ratio[i], id_list[i],
        ))
        if len(batch) >= BATCH:
            conn.executemany("""
                UPDATE features_normalized
                SET feat_4h_bias50=?, feat_4h_bias20=?, feat_4h_bias200=?, feat_4h_rsi14=?,
                    feat_4h_macd_hist=?, feat_4h_bb_pct_b=?, feat_4h_dist_bb_lower=?, feat_4h_ma_order=?,
                    feat_4h_dist_swing_low=?, feat_4h_vol_ratio=?
                WHERE id=?
            """, batch)
            conn.commit()
            batch = []

    if batch:
        conn.executemany("""
            UPDATE features_normalized
            SET feat_4h_bias50=?, feat_4h_bias20=?, feat_4h_bias200=?, feat_4h_rsi14=?,
                feat_4h_macd_hist=?, feat_4h_bb_pct_b=?, feat_4h_dist_bb_lower=?, feat_4h_ma_order=?,
                feat_4h_dist_swing_low=?, feat_4h_vol_ratio=?
            WHERE id=?
        """, batch)
        conn.commit()

    # 驗證
    nn    = conn.execute("SELECT COUNT(*) FROM features_normalized WHERE feat_4h_bias50 != 0").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
    print(f"  ✅ {nn}/{total} ({nn / total * 100:.0f}%) 非零 4H 距離特徵已寫入")

    # 取 3 筆範例
    samples = conn.execute("""
        SELECT f.timestamp,
               r.close_price,
               f.feat_4h_bias50, f.feat_4h_bias200,
               f.feat_4h_rsi14, f.feat_4h_dist_swing_low,
               f.feat_4h_ma_order
        FROM features_normalized f
        JOIN raw_market_data r ON r.timestamp = f.timestamp AND r.symbol = f.symbol
        WHERE f.feat_4h_bias50 != 0
        ORDER BY f.timestamp
        LIMIT 3
    """).fetchall()
    for s in samples:
        print(f"  [{s[0]}] price={s[1]:>8,.0f}  "
              f"b50={s[2]:>+.2f}%  b200={s[3]:>+.2f}%  "
              f"rsi={s[4]:.1f}  dist_L={s[5]:>+.2f}%  "
              f"ord={s[6]:.0f}")

    conn.close()
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n✅ 完成 ({elapsed:.1f}s)")

    # 自動跑 IC 分析
    print("\n=== Re-running IC analysis ===")
    from scripts.full_ic import main as ic_main
    ic_main()


if __name__ == '__main__':
    main()
