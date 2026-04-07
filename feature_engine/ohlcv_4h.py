"""
4H 時間框架 + 支撐線偵測 + 乖離率指標
====================================
完全基於你實際在做交易的方式：
- 4H OHLC K 線（不是 1 分鐘線）
- 4H 技術指標（RSI/MACD/Bollinger 都基於 4H）
- 支撐線偵測（swing low + MA50/MA200）
- 乖離率（價格 vs MA 的距離 / 標準差）
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime


def resample_to_ohlcv(timestamps, closes, highs, lows, volumes, timeframe_minutes=240):
    """把任意時間間隔的價格數據聚合為 OHLCV K 線。
    
    Args:
        timestamps: Unix timestamp in ms (from ccxt)
        closes: close prices
        highs: high prices
        lows: low prices
        volumes: volumes
        timeframe_minutes: target timeframe in minutes (default 240 = 4H)
    
    Returns:
        dict with arrays of 4H candles
    """
    ts = np.array(timestamps, dtype=float)
    c = np.array(closes, dtype=float)
    h = np.array(highs, dtype=float)
    l = np.array(lows, dtype=float)
    v = np.array(volumes, dtype=float)
    
    # Group by timeframe buckets
    tf_ms = timeframe_minutes * 60 * 1000
    bucket_starts = (ts // tf_ms) * tf_ms
    
    unique_buckets = np.unique(bucket_starts)
    
    agg_ts = []
    agg_open = []
    agg_high = []
    agg_low = []
    agg_close = []
    agg_vol = []
    
    for bucket in unique_buckets:
        mask = bucket_starts == bucket
        if mask.sum() == 0:
            continue
        agg_ts.append(bucket)
        agg_open.append(c[mask][0])  # first close in bucket = open
        agg_high.append(h[mask].max())
        agg_low.append(l[mask].min())
        agg_close.append(c[mask][-1])  # last close in bucket = close
        agg_vol.append(v[mask].sum())
    
    return {
        "timestamps": np.array(agg_ts),
        "opens": np.array(agg_open),
        "highs": np.array(agg_high),
        "lows": np.array(agg_low),
        "closes": np.array(agg_close),
        "volumes": np.array(agg_vol),
    }


def ema_series(data: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    result = np.zeros(len(data))
    k = 2.0 / (period + 1)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = data[i] * k + result[i - 1] * (1 - k)
    return result


def compute_4h_indicators(candles: dict, max_idx: int = None) -> dict:
    """計算單一 4H K 線收盤時的所有指標。
    
    返回從 candle 0 到 max_idx 的所有歷史指標值（用於 backtest）
    如果 max_idx=None，返回全部。
    
    回傳: dict with 4H indicator arrays
    """
    closes = candles["closes"].astype(float)
    highs = candles["highs"].astype(float)
    lows = candles["lows"].astype(float)
    volumes = candles["volumes"].astype(float)
    
    n = len(closes)
    if max_idx is not None:
        closes = closes[:max_idx + 1]
        highs = highs[:max_idx + 1]
        lows = lows[:max_idx + 1]
        volumes = volumes[:max_idx + 1]
        n = len(closes)
    
    result = {}
    
    # ─── 4H 均線 (MA) ───
    # MA20 = 20 * 4H = 80H（短期趨勢）
    # MA50 = 50 * 4H = 200H ≈ 8.3天（中期趨勢 = 你說的觀測線）
    # MA200 = 200 * 4H = 800H ≈ 33天（長期趨勢）
    for period, name in [(20, "ma20"), (50, "ma50"), (200, "ma200")]:
        if n >= period:
            ma_vals = np.zeros(n)
            for i in range(period - 1, n):
                ma_vals[i] = closes[i - period + 1:i + 1].mean()
            result[f"4h_{name}"] = ma_vals
    
    # ─── 4H 乖離率 (Bias) ───
    # 乖離率 = (價格 - MA) / MA * 100
    # 乖離率越負 = 越接近/跌破支撐 = 潛在買點
    # 乖離率越正 = 遠離支撐 = 潛在賣點
    for period, name in [(20, "bias20"), (50, "bias50"), (200, "bias200")]:
        if n >= period:
            ma = result[f"4h_ma{period}"]
            result[f"4h_{name}"] = np.where(ma != 0, (closes - ma) / ma * 100, 0)
    
    # ─── 4H 布林通道 (20, 2σ) ───
    if n >= 20:
        bb_mid = np.zeros(n)
        bb_std = np.zeros(n)
        for i in range(19, n):
            window = closes[i - 19:i + 1]
            bb_mid[i] = window.mean()
            bb_std[i] = window.std()
        result["4h_bb_mid"] = bb_mid
        result["4h_bb_upper"] = bb_mid + 2 * bb_std
        result["4h_bb_lower"] = bb_mid - 2 * bb_std
        bb_width = (bb_mid + 2 * bb_std) - (bb_mid - 2 * bb_std)
        result["4h_bb_pct_b"] = np.where(
            bb_width > 0,
            (closes - (bb_mid - 2 * bb_std)) / bb_width,
            0.5
        )
        # 價格距離布林下軌（支撐線代理）
        result["4h_dist_bb_lower"] = (closes - result["4h_bb_lower"]) / closes * 100
    
    # ─── 4H RSI (14) ───
    result["4h_rsi14"] = compute_rsi_4h(closes, 14)
    
    # ─── 4H MACD (12, 26, 9) ───
    result["4h_macd"], result["4h_macd_signal"], result["4h_macd_hist"] = \
        compute_macd_4h(closes)
    
    # ─── Swing Low / Swing High (支撐線/阻力線代理) ───
    # 用 5 根 K 線的局部高低點作為支撐/阻力
    result["4h_swing_low"], result["4h_swing_high"] = compute_swing_levels(closes, lows, highs, lookback=5)
    
    # 距最近 swing low 的距離（%）
    result["4h_dist_swing_low"] = np.where(
        result["4h_swing_low"] > 0,
        (closes - result["4h_swing_low"]) / closes * 100,
        0
    )
    
    # ─── 價格 vs MA50 排序 ───
    # price_above_ma20_above_ma50 = 強烈多頭 → 不做空
    # price_below_ma20_below_ma50 = 強烈空頭 → 做空機會
    if "4h_ma20" in result and "4h_ma50" in result:
        result["4h_ma_order"] = np.zeros(n)
        # +2: price > ma20 > ma50 (bullish alignment)
        # +1: price > ma20 > ma50 false but price > ma20 (partial bullish)
        # 0: neutral / choppy
        # -1: price < ma20 < ma50 (bearish alignment)
        mask_bull_align = (closes > result["4h_ma20"]) & (result["4h_ma20"] > result["4h_ma50"])
        mask_bear_align = (closes < result["4h_ma20"]) & (result["4h_ma20"] < result["4h_ma50"])
        result["4h_ma_order"][mask_bull_align] = 1
        result["4h_ma_order"][mask_bear_align] = -1
    
    # ─── 4H 成交量確認 ───
    # 放量下跌 = 有效跌破 / 放量上漲 = 有效突破
    if n >= 20:
        vol_ma20 = np.zeros(n)
        for i in range(19, n):
            vol_ma20[i] = volumes[i - 19:i + 1].mean()
        result["4h_vol_ma20"] = vol_ma20
        result["4h_vol_ratio"] = np.where(vol_ma20 > 0, volumes / vol_ma20, 1)
    
    return result


def compute_rsi_4h(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI 計算（4H 時間框架，每根 K 線算一次）。"""
    n = len(closes)
    result = np.full(n, 50.0)  # default neutral
    deltas = np.diff(closes)
    
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    
    avg_gain = np.zeros(n)
    avg_loss = np.zeros(n)
    
    if n <= period:
        return result
    
    # Initial average
    avg_gain[period] = gains[:period].mean()
    avg_loss[period] = losses[:period].mean()
    
    for i in range(period + 1, n):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period
    
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100)
    result[period:] = 100 - 100 / (1 + rs[period:])
    return result


def compute_macd_4h(closes: np.ndarray, fast=12, slow=26, signal=9):
    """MACD 計算（4H 時間框架）。"""
    ema_fast = ema_series(closes, fast)
    ema_slow = ema_series(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema_series(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_swing_levels(closes: np.ndarray, lows: np.ndarray, highs: np.ndarray, lookback: int = 5):
    """偵測 swing low / swing high 作為支撐/阻力線。
    
    Swing low = local minimum where price is lower than surrounding `lookback` bars
    """
    n = len(closes)
    swing_low = np.zeros(n)
    swing_high = np.zeros(n)
    
    # Current support = most recent swing low below current price
    last_swing_low = 0.0
    last_swing_high = 0.0
    
    for i in range(lookback, n - lookback):
        is_swing_low = True
        is_swing_high = True
        for j in range(1, lookback + 1):
            if lows[i] >= lows[i - j]:
                is_swing_low = False
            if highs[i] <= highs[i - j]:
                is_swing_high = False
            if lows[i] >= lows[i + j]:
                is_swing_low = False
            if highs[i] <= highs[i + j]:
                is_swing_high = False
        
        if is_swing_low:
            last_swing_low = lows[i]
        if is_swing_high:
            last_swing_high = highs[i]
        
        swing_low[i] = last_swing_low
        swing_high[i] = last_swing_high
    
    # Fill remaining
    for i in range(n - lookback, n):
        swing_low[i] = last_swing_low
        swing_high[i] = last_swing_high
    
    return swing_low, swing_high


def compute_4h_features_single(candles: dict, indicator_idx: int = None) -> Dict[str, float]:
    """計算單一時間點的 4H 特徵值（用於即時 prediction）。
    
    Args:
        candles: dict with full OHLCV history (from Binance or DB)
        indicator_idx: which candle index to compute for (default: last)
    
    Returns:
        dict of feature values for the latest 4H candle
    """
    if indicator_idx is None:
        indicator_idx = len(candles["closes"]) - 1
    
    indicators = compute_4h_indicators(candles, max_idx=indicator_idx)
    idx = indicator_idx
    
    features = {}
    features["4h_close"] = float(candles["closes"][idx])
    features["4h_close_time"] = int(candles["timestamps"][idx])
    
    # MA features
    for name in ["ma20", "ma50", "ma200"]:
        key = f"4h_{name}"
        if key in indicators:
            features[f"feat_4h_{name}"] = float(indicators[key][idx])
        else:
            features[f"feat_4h_{name}"] = None
    
    # Bias features (乖離率)
    for name in ["bias20", "bias50", "bias200"]:
        key = f"4h_{name}"
        if key in indicators:
            features[f"feat_4h_{name}"] = float(indicators[key][idx])
        else:
            features[f"feat_4h_{name}"] = None
    
    # Bollinger
    if "4h_bb_pct_b" in indicators:
        features["feat_4h_bb_pct_b"] = float(indicators["4h_bb_pct_b"][idx])
    else:
        features["feat_4h_bb_pct_b"] = 0.5
    
    if "4h_dist_bb_lower" in indicators:
        features["feat_4h_dist_bb_lower"] = float(indicators["4h_dist_bb_lower"][idx])
    else:
        features["feat_4h_dist_bb_lower"] = 0
    
    # RSI
    if "4h_rsi14" in indicators:
        features["feat_4h_rsi14"] = float(indicators["4h_rsi14"][idx])
    else:
        features["feat_4h_rsi14"] = 50
    
    # MACD
    if "4h_macd_hist" in indicators:
        features["feat_4h_macd_hist"] = float(indicators["4h_macd_hist"][idx])
    else:
        features["feat_4h_macd_hist"] = 0
    
    # Swing low distance
    if "4h_dist_swing_low" in indicators:
        features["feat_4h_dist_swing_low"] = float(indicators["4h_dist_swing_low"][idx])
    else:
        features["feat_4h_dist_swing_low"] = 0
    
    # MA alignment
    if "4h_ma_order" in indicators:
        features["feat_4h_ma_order"] = float(indicators["4h_ma_order"][idx])
    else:
        features["feat_4h_ma_order"] = 0
    
    # Volume ratio
    if "4h_vol_ratio" in indicators:
        features["feat_4h_vol_ratio"] = float(indicators["4h_vol_ratio"][idx])
    else:
        features["feat_4h_vol_ratio"] = 1
    
    return features


def backtest_4h_strategy(candles: dict, strategy_signals: list) -> dict:
    """簡單回測引擎：根據 4H 策略信號計算勝率。
    
    strategy_signals: list of (idx, action) tuples
        action = "SELL" means test if short would have been profitable
        action = "HOLD" means do nothing
    
    Returns:
        dict with backtest results
    """
    closes = candles["closes"].astype(float)
    n = len(closes)
    
    results = []
    for idx, action in strategy_signals:
        if idx + 1 >= n:
            continue
        
        entry_price = closes[idx]
        # Exit after N 4H candles (1, 3, 6 = 4h, 12h, 24h)
        for horizon_candles in [1, 3, 6]:
            if idx + horizon_candles >= n:
                continue
            exit_price = closes[idx + horizon_candles]
            ret_pct = (exit_price - entry_price) / entry_price
            
            # For SELL/SHORT: negative return = profit
            sell_win = 1 if ret_pct < 0 else 0
            
            results.append({
                "entry_idx": idx + 1,  # actually next candle's open
                "exit_idx": idx + horizon_candles,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return_pct": ret_pct,
                "sell_win": sell_win,
                "horizon_4h": horizon_candles,
                "horizon_hours": horizon_candles * 4,
            })
    
    if not results:
        return {"total": 0}
    
    total = len(results)
    wins = sum(r["sell_win"] for r in results)
    win_rate = wins / total if total > 0 else 0
    
    return {
        "total": total,
        "wins": wins,
        "losses": total - wins,
        "win_rate": win_rate,
        "avg_return": np.mean([r["return_pct"] for r in results]),
    }


# ============================================================
# 策略範例：基於 4H 支撐線 + 乖離率的做空信號
# ============================================================

def generate_sell_signals_from_4h(candles: dict) -> list:
    """根據 4H 指標生成 SELL 信號。
    
    做空條件（符合越多越好，至少 3 項）：
    1. 價格在 MA20 附近或以內 1%（接近短期阻力）
    2. MACD histogram < 0（空頭動能）
    3. RSI14 在 40-70 之間（不超賣也不超買）
    4. 布林 %B 在 0.5-0.9（在上半部但沒破頂）
    5. 價格在 MA50 以上（有下跌空間）
    6. 距離最近 swing high < 1%（接近阻力位）
    """
    indicators = compute_4h_indicators(candles)
    n = len(candles["closes"])
    
    signals = []
    
    for i in range(50, n - 1):
        closes_i = candles["closes"][i]
        
        rsi = indicators.get("4h_rsi14", [50] * n)
        macd_hist = indicators.get("4h_macd_hist", [0] * n)
        bias50 = indicators.get("4h_bias50", [0] * n)
        bias20 = indicators.get("4h_bias20", [0] * n)
        bb_pct = indicators.get("4h_bb_pct_b", [0.5] * n)
        dist_swing_high = indicators.get("4h_dist_swing_high", indicators.get("4h_dist_swing_low", [0] * n))
        ma20 = indicators.get("4h_ma20", closes_i)
        ma50 = indicators.get("4h_ma50", closes_i)
        
        # Count conditions
        score = 0
        
        # 1. MACD histogram < 0 (bearish momentum)
        if macd_hist[i] < 0:
            score += 1
        
        # 2. RSI between 40-70 (not oversold, not overbought)
        if 40 <= rsi[i] <= 70:
            score += 1
        
        # 3. Price above MA50 but bias50 < 3% (room to fall)
        if bias50[i] > 0 and bias50[i] < 3:
            score += 1
        
        # 4. Bollinger %B in upper half (0.5-0.9)
        if 0.5 <= bb_pct[i] <= 0.9:
            score += 1
        
        # 5. Price close to MA20 (within 1%)
        if abs(bias20[i]) < 1.5:
            score += 1
        
        # Need at least 3 out of 5 conditions
        if score >= 3:
            signals.append((i, "SELL"))
    
    return signals


if __name__ == "__main__":
    import ccxt
    
    print("=" * 60)
    print("4H Timeframe Analysis — Support Line + Bias Strategy")
    print("=" * 60)
    
    # Fetch 4H data from Binance
    exchange = ccxt.binance({"enableRateLimit": True})
    ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=1000)
    
    candles = {
        "timestamps": np.array([o[0] for o in ohlcv]),
        "opens": np.array([o[1] for o in ohlcv]),
        "highs": np.array([o[2] for o in ohlcv]),
        "lows": np.array([o[3] for o in ohlcv]),
        "closes": np.array([o[4] for o in ohlcv]),
        "volumes": np.array([o[5] for o in ohlcv]),
    }
    
    print(f"\nLoaded {len(candles['closes'])} 4H candles")
    print(f"Date range: {datetime.fromtimestamp(candles['timestamps'][0]/1000).strftime('%Y-%m-%d')} → {datetime.fromtimestamp(candles['timestamps'][-1]/1000).strftime('%Y-%m-%d')}")
    print(f"Price range: ${candles['closes'][0]:.0f} → ${candles['closes'][-1]:.0f}")
    
    # Generate sell signals
    signals = generate_sell_signals_from_4h(candles)
    print(f"\nGenerated {len(signals)} SELL signals")
    
    # Backtest
    for horizon in [1, 3, 6]:
        horizon_signals = [(idx, action) for idx, action in signals if True]
        result = backtest_4h_strategy(candles, horizon_signals)
        
        # Filter by horizon
        filtered = [r for r in [
            dict(
                entry_idx=s[0], exit_idx=s[0] + horizon,
                entry_price=float(candles["closes"][s[0]]),
                exit_price=float(candles["closes"][min(s[0] + horizon, len(candles["closes"]) - 1)]),
                return_pct=float((candles["closes"][min(s[0] + horizon, len(candles["closes"]) - 1)] - candles["closes"][s[0]]) / candles["closes"][s[0]]),
                sell_win=1 if (candles["closes"][min(s[0] + horizon, len(candles["closes"]) - 1)] - candles["closes"][s[0]]) / candles["closes"][s[0]] < 0 else 0
            ) for s in signals if s[0] + horizon < len(candles["closes"])
        ]]
        
        if filtered:
            total = len(filtered)
            wins = sum(r["sell_win"] for r in filtered)
            print(f"\n  Horizon {horizon*4}H ({horizon} candles):")
            print(f"    Trades: {total}")
            print(f"    Win rate: {wins/total:.1%} ({wins}/{total})")
            print(f"    Avg return: {np.mean([r['return_pct'] for r in filtered]):.4f}")
