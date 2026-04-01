"""
Mind 認知感 — BTC/ETH 成交量比作為支配度 proxy
數據源: Binance ETH/BTC volume ratio
高 ratio = 資金在 BTC (避險) -> 偏空
低 ratio = 資金流向山寨 (risk-on) -> 偏多
"""
import math
import ccxt

def collect_mind(exchange=None, symbol_btc="BTCUSDT", symbol_eth="ETHUSDT", timeframe="1d", limit=7):
    if exchange is None:
        exchange = ccxt.binance()
    btc_data = exchange.fetch_ohlcv(symbol_btc, timeframe, limit=limit)
    eth_data = exchange.fetch_ohlcv(symbol_eth, timeframe, limit=limit)
    if not btc_data or not eth_data:
        return None
    btc_vol = sum(c[5] for c in btc_data if c[5] is not None)
    eth_vol = sum(c[5] for c in eth_data if c[5] is not None)
    total = btc_vol + eth_vol
    ratio = btc_vol / total if total > 0 else 0.5
    return {"btc_vo l": btc_vol, "eth_vo l": eth_vol, "ratio": ratio}

def compute_mind_signal(ratio, ratio_history=None):
    if ratio is None:
        return 0
    if ratio_history and len(ratio_history) >= 7:
        median_ratio = sorted(ratio_history)[len(ratio_history) // 2]
        z = (ratio - median_ratio) / 0.05
    else:
        z = (ratio - 0.55) / 0.05
    return math.tanh(z / 2)
