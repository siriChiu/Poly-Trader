"""
Pulse 脈動感 — BTC 短期波動 / 動量
數據源: Binance OHLCV
"""
import math
import ccxt

def collect_pulse(exchange=None, symbol="BTCUSDT", timeframe="1h", limit=50):
    if exchange is None:
        exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    if not ohlcv or len(ohlcv) < 20:
        return None
    closes = [c[4] for c in ohlcv]
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    realized_vol = (sum(r**2 for r in returns[-20:]) / 20) ** 0.5
    ret_24 = (closes[-1] - closes[-24]) / closes[-24] if len(closes) >= 24 else None
    return {"realized_vol": realized_vol, "ret_24h": ret_24, "returns_history": returns}

def compute_pulse_signal(realized_vol, returns_history):
    if realized_vol is None or returns_history is None or len(returns_history) < 30:
        return 0
    vols = []
    for i in range(20, len(returns_history)):
        chunk = returns_history[max(0,i-19):i+1]
        v = (sum(r**2 for r in chunk) / len(chunk)) ** 0.5
        vols.append(v)
    if len(vols) < 20:
        return 0
    mean_v = sum(vols[:-1]) / (len(vols) - 1)
    std_v = (sum((v - mean_v)**2 for v in vols[:-1]) / max(len(vols) - 2, 1)) ** 0.5
    if std_v == 0:
        return 0
    z = (vols[-1] - mean_v) / std_v
    return math.tanh(z / 2)
