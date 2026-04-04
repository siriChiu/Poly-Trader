"""
Nadaraya-Watson Envelope + Proven Technical Indicators v1
=========================================================
Core indicators proven in crypto markets, replacing low-IC senses.

New Senses (7 new features):
  feat_nw_upper   — NW Envelope Upper Band (resistance zone)
  feat_nw_lower   — NW Envelope Lower Band (support zone)
  feat_nw_width   — NW Bandwidth (volatility expansion)
  feat_rsi14      — RSI 14-period (momentum oscillator)
  feat_macd_hist  — MACD Histogram (trend momentum)
  feat_bb_width   — Bollinger Band %B / Width (volatility channel)
  feat_atr_pct    — ATR % of price (normalized volatility)
  feat_vwap_dev    — VWAP deviation (fair value proxy)

Data source: Binance OHLCV via ccxt (no additional APIs needed)
Dependencies: numpy, scipy (both already installed)
"""

import numpy as np
from scipy.signal import savgol_filter
from typing import Optional, Dict, List, Tuple


def nadaraya_watson_envelope(
    closes: np.ndarray,
    lookback: int = 64,
    bandwidth: float = 4.0,
    mult: float = 3.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Nadaraya-Watson Envelope with Gaussian kernel.
    
    Modern, adaptive support/resistance — much better than simple moving averages.
    The NW filter smooths price with adaptive bandwidth, creating a dynamic
    envelope that expands/contracts with market conditions.
    
    Args:
        closes: Price series (1D array)
        lookback: Smoothing window (larger = smoother but more lag)
        bandwidth: Kernel bandwidth (smaller = tighter envelope)
        mult: Envelope multiplier for upper/lower bands
    
    Returns:
        (nw_smoothed, upper_band, lower_band, bandwidth) all same length as closes
    """
    n = len(closes)
    smoothed = np.zeros(n)
    
    for i in range(n):
        weights = np.exp(-0.5 * ((np.arange(n) - i) / bandwidth) ** 2)
        smoothed[i] = np.sum(closes * weights) / np.sum(weights)
    
    # Calculate deviation from smoothed price
    deviation = np.abs(closes - smoothed)
    # Use rolling std of deviation for adaptive envelope
    roll_std = np.zeros(n)
    for i in range(n):
        start = max(0, i - lookback + 1)
        roll_std[i] = np.std(deviation[start:i+1]) if (i - start + 1) > 5 else np.std(deviation[:i+1])
    
    upper = smoothed + mult * roll_std
    lower = smoothed - mult * roll_std
    width = (upper - lower) / smoothed  # Normalized bandwidth
    
    return smoothed, upper, lower, width


def rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index — momentum oscillator (0-100)."""
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    
    avg_gain = np.zeros(len(prices))
    avg_loss = np.zeros(len(prices))
    avg_gain[:period] = np.mean(gains[:period]) if len(gains) >= period else np.mean(gains)
    avg_loss[:period] = np.mean(losses[:period]) if len(losses) >= period else np.mean(losses)
    
    for i in range(period, len(prices)):
        avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
        avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period
    
    rs = np.where(avg_loss == 0, 100, avg_gain / avg_loss)
    return 100 - 100 / (1 + rs)


def macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MACD (Moving Average Convergence Divergence).
    
    Returns: (macd_line, signal_line, histogram)
    """
    def ema(x, n):
        k = 2 / (n + 1)
        result = np.zeros(len(x))
        result[0] = x[0]
        for i in range(1, len(x)):
            result[i] = x[i] * k + result[i-1] * (1 - k)
        return result
    
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def bollinger_bands(prices: np.ndarray, period: int = 20, std_mult: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Bollinger Bands.
    
    Returns: (middle, upper, lower, percent_b)
    """
    n = len(prices)
    middle = np.zeros(n)
    std = np.zeros(n)
    
    for i in range(period - 1, n):
        window = prices[i-period+1:i+1]
        middle[i] = np.mean(window)
        std[i] = np.std(window)
    
    upper = middle + std_mult * std
    lower = middle - std_mult * std
    
    # %B — where price sits within the bands
    width = upper - lower
    percent_b = np.where(width > 0, (prices - lower) / width, 0.5)
    
    return middle, upper, lower, percent_b


def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range — volatility measure."""
    n = len(closes)
    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
    
    atr_val = np.zeros(n)
    atr_val[0] = np.mean(tr[:period]) if len(tr) >= period else np.mean(tr)
    for i in range(1, n):
        atr_val[i] = (atr_val[i-1] * (period-1) + tr[i]) / period
    
    return atr_val


def vwap(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
    """Volume Weighted Average Price."""
    typical_price = (highs + lows + closes) / 3
    cum_tp = np.cumsum(typical_price * volumes)
    cum_vol = np.cumsum(volumes)
    return np.where(cum_vol > 0, cum_tp / cum_vol, closes)


def compute_technical_features(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
) -> Dict[str, float]:
    """Compute all technical indicators from OHLCV data.
    
    Returns dict of normalized features (0-1 range where possible).
    Only returns the LATEST values.
    """
    n = len(closes)
    if n < 64:  # Minimum for NW envelope
        return {}
    
    closes_f = closes.astype(float)
    highs_f = highs.astype(float)
    lows_f = lows.astype(float)
    volumes_f = volumes.astype(float)
    
    result = {}
    
    # 1-3: Nadaraya-Watson Envelope (3 features)
    nw_smoothed, nw_upper, nw_lower, nw_width = nadaraya_watson_envelope(closes_f)
    latest_price = closes_f[-1]
    
    # Distance from upper band (normalized) — price near upper = overbought bias
    result["feat_nw_upper"] = float((latest_price - nw_smoothed[-1]) / nw_smoothed[-1]) if nw_smoothed[-1] != 0 else 0
    
    # Distance from lower band — price near lower = oversold bias
    result["feat_nw_lower"] = float((latest_price - nw_smoothed[-1]) / nw_smoothed[-1])
    
    # NW Bandwidth — volatility expansion/contraction
    result["feat_nw_width"] = float(nw_width[-1])
    
    # 4: RSI 14 (0-100, normalize to 0-1)
    rsi_vals = rsi(closes_f, period=14)
    result["feat_rsi14"] = float(rsi_vals[-1]) / 100.0
    
    # 5: MACD Histogram (normalize by price)
    macd_line, sig_line, hist = macd(closes_f)
    result["feat_macd_hist"] = float(hist[-1] / latest_price) if latest_price != 0 else 0
    
    # 6: Bollinger %B (already 0-1)
    _, _, _, bb_pct_b = bollinger_bands(closes_f)
    result["feat_bb_pct_b"] = float(bb_pct_b[-1])
    
    # 7: ATR as % of price
    atr_val = atr(highs_f, lows_f, closes_f, period=14)
    result["feat_atr_pct"] = float(atr_val[-1] / latest_price) if latest_price != 0 else 0
    
    # 8: VWAP deviation (normalize by price)
    vwap_vals = vwap(highs_f, lows_f, closes_f, volumes_f)
    result["feat_vwap_dev"] = float((latest_price - vwap_vals[-1]) / latest_price) if latest_price != 0 else 0
    
    return result


def compute_ic_for_indicator(
    indicators: Dict[str, List[float]],
    labels: List[float],
) -> Dict[str, Dict]:
    """Compute Information Coefficient (Spearman correlation) for each indicator.
    
    indicators: {feat_name: [values]}, labels: [0 or 1 sell_win]
    """
    from scipy import stats
    
    results = {}
    for feat_name, values in indicators.items():
        # Align values and labels
        pairs = [(v, l) for v, l in zip(values, labels) if v is not None and l is not None]
        if len(pairs) < 30:
            results[feat_name] = {"ic": 0.0, "count": len(pairs), "status": "insufficient_data"}
            continue
        
        vals = [p[0] for p in pairs]
        labs = [p[1] for p in pairs]
        
        # Check for constant
        if np.std(vals) < 1e-10:
            results[feat_name] = {"ic": 0.0, "count": len(pairs), "status": "constant"}
            continue
        
        corr, p_value = stats.spearmanr(vals, labs)
        abs_ic = abs(corr) if corr is not None else 0
        status = "✅ PASS" if abs_ic >= 0.05 else "❌ FAIL"
        
        results[feat_name] = {
            "ic": round(float(corr) if corr else 0, 4),
            "abs_ic": round(abs_ic, 4),
            "p_value": round(float(p_value) if p_value else 1.0, 6),
            "count": len(pairs),
            "status": status
        }
    
    return results


def fetch_binance_ohlcv(
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    limit: int = 300,
) -> Optional[Dict[str, np.ndarray]]:
    """Fetch OHLCV from Binance via ccxt.
    
    Returns dict with 'closes', 'highs', 'lows', 'volumes' arrays.
    """
    try:
        import ccxt
        exchange = ccxt.binance({"enableRateLimit": True})
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv or len(ohlcv) < 1:
            return None
        
        ohlcv = np.array(ohlcv)
        return {
            "timestamps": ohlcv[:, 0],
            "opens": ohlcv[:, 1],
            "highs": ohlcv[:, 2],
            "lows": ohlcv[:, 3],
            "closes": ohlcv[:, 4],
            "volumes": ohlcv[:, 5],
        }
    except ImportError:
        # Fallback: try to construct from raw market data in DB
        try:
            from config import load_config
            from database.models import RawMarketData
            from sqlalchemy import create_engine, text
            
            cfg = load_config()
            engine = create_engine(cfg["database"]["url"])
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT close_price FROM raw_market_data
                    WHERE close_price IS NOT NULL
                    ORDER BY timestamp DESC
                    LIMIT 300
                """)).fetchall()
            
            if not rows:
                return None
            
            closes = np.array([r[0] for r in reversed(rows)])
            # Estimate highs/lows/volumes from close
            # This is a fallback — quality will be limited
            return {
                "closes": closes,
                "highs": closes * 1.005,  # Approximate
                "lows": closes * 0.995,
                "volumes": np.ones(len(closes)),  # Placeholder
            }
        except Exception as e:
            print(f"Fallback also failed: {e}")
            return None
    except Exception as e:
        print(f"ccxt error: {e}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("Technical Indicators IC Analysis")
    print("=" * 60)
    
    # Fetch data
    ohlcv = fetch_binance_ohlcv("BTC/USDT", "4h", limit=500)
    if not ohlcv:
        print("Failed to fetch OHLCV data")
        exit(1)
    
    closes = ohlcv["closes"]
    highs = ohlcv["highs"]
    lows = ohlcv["lows"]
    volumes = ohlcv["volumes"]
    
    print(f"\nFetched {len(closes)} candles (4h timeframe)")
    print(f"Price range: ${closes[0]:.0f} → ${closes[-1]:.0f}")
    
    # Compute features for each point in history
    features_history = {}
    feat_names = ["feat_nw_upper", "feat_nw_lower", "feat_nw_width",
                   "feat_rsi14", "feat_macd_hist", "feat_bb_pct_b",
                   "feat_atr_pct", "feat_vwap_dev"]
    
    print("\n--- Computing indicators for each historical point ---")
    for i in range(64, len(closes)):
        # For NW we need at least 64 points of history
        sub_closes = closes[:i+1]
        sub_highs = highs[:i+1]
        sub_lows = lows[:i+1]
        sub_vols = volumes[:i+1]
        
        ind = compute_technical_features(sub_closes, sub_highs, sub_lows, sub_vols)
        for fn in feat_names:
            features_history.setdefault(fn, []).append(ind.get(fn))
    
    print(f"Historical feature count: {len(features_history.get('feat_rsi14', []))}")
    
    # Now we need labels for IC computation
    # Since we don't have direct label mapping to these candles,
    # use a simple proxy: price change 24h ahead (≈ 6 4h bars)
    horizon = 6
    labels = []
    valid_features = {fn: [] for fn in feat_names}
    
    for i in range(len(closes) - horizon - 64):
        current_price = closes[64 + i]
        future_price = closes[64 + i + horizon]
        ret_pct = (future_price - current_price) / current_price
        
        # label_sell_win = 1 if price drops (short wins)
        label = 1 if ret_pct < -0.005 else 0
        
        labels.append(label)
        for fn in feat_names:
            if i < len(features_history.get(fn, [])):
                valid_features[fn].append(features_history[fn][i])
    
    print(f"Labeled samples: {len(labels)}")
    print(f"Label distribution: {sum(labels)} sell_wins / {len(labels) - sum(labels)} non-wins")
    
    # Compute IC
    ic_results = compute_ic_for_indicator(valid_features, labels)
    
    print("\n" + "=" * 60)
    print("IC Results (Spearman correlation vs sell_win)")
    print("=" * 60)
    print(f"{'Feature':<20} {'IC':>8} {'|IC|':>6} {'p-value':>10} {'Status':>12}")
    print("-" * 60)
    
    sorted_results = sorted(ic_results.items(), key=lambda x: abs(x[1].get("ic", 0)), reverse=True)
    
    for name, res in sorted_results:
        ic = res.get("ic", 0)
        abs_ic = res.get("abs_ic", 0)
        p_val = res.get("p_value", 1)
        status = res.get("status", "?")
        print(f"{name:<20} {ic:>+8.4f} {abs_ic:>6.4f} {p_val:>10.6f} {status:>12}")
    
    # Summary
    passing = [n for n, r in ic_results.items() if r.get("abs_ic", 0) >= 0.05]
    print(f"\n✅ Passing indicators (|IC| >= 0.05): {len(passing)}/8")
    for p in passing:
        print(f"  - {p}: IC = {ic_results[p]['ic']:+.4f}")
    
    failing = [n for n, r in ic_results.items() if r.get("abs_ic", 0) < 0.05]
    print(f"\n❌ Failing indicators (|IC| < 0.05): {len(failing)}/8")
    for f in failing:
        print(f"  - {f}: IC = {ic_results[f]['ic']:+.4f}")
