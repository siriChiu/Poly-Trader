#!/usr/bin/env python3
"""
感官之「 Fin 」v1 — 鏈上巨鯨模組

數據源：Whale Alert API (免費) + Binance 大額交易
- wss://leviathan.whale-alert.io/ws (實時鯨魚警報)
- Binance 大額成交 (>50 BTC per trade)

邏輯：
- 鯨魚流入交易所 → 準備出售 → SHORT 信號
- 鯨魚流出交易所 → 長期持有 → 看漲
- 短時間內大量轉帳 = 即將有大動作

免費 API key: https://developer.whale-alert.io/
"""
import json
import os
import ssl
from datetime import datetime
from typing import Optional, Dict
from urllib.request import urlopen, Request
from utils.logger import setup_logger
import math

logger = setup_logger(__name__)

WHALE_ALERT_API_KEY = os.environ.get("WHALE_ALERT_API_KEY", "")
WHALE_ALERT_URL = "https://api.whale-alert.io/v1/transactions"


def fetch_whale_transactions(hours: int = 4, min_usd: int = 1_000_000) -> Optional[list]:
    """獲取最近 N 小時的巨額交易。"""
    if not WHALE_ALERT_API_KEY:
        logger.debug("WHALE_ALERT_API_KEY 未設置，使用 Binance 替代")
        return _fetch_binance_large_trades()

    try:
        from datetime import timedelta
        start_ts = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
        url = (f"{WHALE_ALERT_URL}?api_key={WHALE_ALERT_API_KEY}"
               f"&min_amount=100&start={start_ts}&limit=50")
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        data = json.loads(resp.read().decode())
        return data.get("transactions", [])
    except Exception as e:
        logger.debug(f"Whale Alert API failed: {e}")
        return _fetch_binance_large_trades()


def _fetch_binance_large_trades() -> Optional[list]:
    """Binance 大額交易替代方案。"""
    try:
        url = "https://api.binance.com/api/v3/trades"
        params = {"symbol": "BTCUSDT", "limit": 1000}
        import urllib.parse
        qs = urllib.parse.urlencode(params)
        req = Request(f"{url}?{qs}", headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        trades = json.loads(resp.read().decode())
        # 過濾大額 (>50 BTC ≈ $3,000,000+)
        large = [t for t in trades if float(t.get("qty", 0)) > 50]
        return large
    except Exception as e:
        logger.debug(f"Binance large trades failed: {e}")
        return []


def get_fin_feature() -> Optional[Dict]:
    """
    計算巨鯨活動特徵。

    返回：
    - feat_whale_exchange_inflow: 流入交易所
    - feat_whale_exchange_outflow: 流出交易所
    - feat_whale_large_trades: 大額交易數
    """
    transactions = fetch_whale_transactions()
    if not transactions:
        return {
            "feat_whale_exchange_inflow": 0.0,
            "feat_whale_exchange_outflow": 0.0,
            "feat_whale_large_trades": 0,
        }

    # 統計交易所流入/流出
    exchange_keywords = ["binance", "coinbase", "kraken", "bitfinex", "huobi", "okx", "bybit",
                         "gate", "kucoin", "gemini", "bitstamp", "ftx"]

    inflow_count = 0
    outflow_count = 0
    total_inflow_usd = 0
    total_outflow_usd = 0
    large_trades = 0

    for tx in transactions:
        btc_amount = float(tx.get("amount", 0))
        usd_value = float(tx.get("amount_usd", 0))
        from_addr = str(tx.get("from", "")).lower()
        to_addr = str(tx.get("to", "")).lower()

        # 檢查是否與交易所有關
        from_exchange = any(kw in from_addr for kw in exchange_keywords)
        to_exchange = any(kw in to_addr for kw in exchange_keywords)

        if to_exchange and not from_exchange:
            inflow_count += 1
            total_inflow_usd += usd_value
        elif from_exchange and not to_exchange:
            outflow_count += 1
            total_outflow_usd += usd_value

        if usd_value > 10_000_000:  # > $10M 超大額
            large_trades += 1

    # 淨流向 (正=流入, 負=流出)
    net_flow = total_inflow_usd - total_outflow_usd
    whale_score = math.tanh(net_flow / 50_000_000)  # ±50M → ±1

    # 大額交易密度
    trade_density_score = math.tanh(large_trades / 5.0)  # 5+ large trades → 1

    logger.info(
        f"Fin (鯨魚): inflow={inflow_count} (${total_inflow_usd:,.0f}), "
        f"outflow={outflow_count} (${total_outflow_usd:,.0f}), "
        f"large_trades={large_trades}, "
        f"net_score={whale_score:+.3f}, density={trade_density_score:.3f}"
    )

    return {
        "feat_whale_netflow": float(whale_score),
        "feat_whale_density": float(trade_density_score),
        "whale_inflow_count": inflow_count,
        "whale_outflow_count": outflow_count,
        "total_inflow_usd": total_inflow_usd,
        "total_outflow_usd": total_outflow_usd,
        "whale_large_trades": large_trades,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
