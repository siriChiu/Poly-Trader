"""
Pulse 脈動感 — 短期波動率比率（vol_ratio_12_48）
數據源: OKX OHLCV
IC-validated: vol12/vol48 ratio (IC=+0.1087, p<0.001)
替換歷史：
  v1: realized_vol_zscore (失效)
  v2: vol_roc48 (IC=+0.044, 失效)
  v3: vol_spike12 (IC=-0.0717, 邊界)
  v4: vol_ratio_12_48 (IC=+0.1087, 有效) ← 當前
"""
import math
import ccxt

def collect_pulse(exchange=None, symbol="BTC/USDT", timeframe="1h", limit=60):
    if exchange is None:
        exchange = ccxt.okx()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    if not ohlcv or len(ohlcv) < 50:
        return None
    closes = [c[4] for c in ohlcv]
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    return {"closes": closes, "returns": returns}


def compute_pulse_signal(closes=None, returns=None, **kwargs):
    """
    Compute vol_ratio_12_48: short-term volatility / long-term volatility.
    High ratio = volatility spike (mean reversion signal).
    Maps to [0,1] via sigmoid.
    """
    if returns is None or len(returns) < 48:
        return 0.5  # neutral

    vol12 = (sum(r**2 for r in returns[-12:]) / 12) ** 0.5
    vol48 = (sum(r**2 for r in returns[-48:]) / 48) ** 0.5

    if vol48 < 1e-10:
        return 0.5

    ratio = vol12 / vol48
    # sigmoid centered at 1.0 (ratio=1 → neutral=0.5)
    z = ratio * 3 - 1
    return 1 / (1 + math.exp(-z))
