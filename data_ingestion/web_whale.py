"""
Web (網) — Whale Activity via OKX large trades (public, no key)
"""
from __future__ import annotations

import math

from data_ingestion.okx_public import fetch_trades
from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_web_feature(symbol: str = "BTC/USDT"):
    try:
        trades = fetch_trades(symbol, limit=100)
        large = []
        for t in trades:
            price = float(t.get("px", 0) or 0)
            qty = float(t.get("sz", 0) or 0)
            quote_notional = price * qty
            if quote_notional >= 50_000:
                large.append((t, quote_notional))
        total_notional = sum(notional for _, notional in large)
        if total_notional <= 0:
            return {"feat_web_whale": 0.0, "feat_web_density": 0.0, "web_large_trades": 0, "web_sell_ratio": 0.5}
        sell_notional = sum(notional for t, notional in large if str(t.get("side", "")).lower() == "sell")
        sell_ratio = sell_notional / total_notional
        density = math.tanh(total_notional / 5_000_000)
        imbalance = (sell_ratio - 0.5) * 2.0
        return {"feat_web_whale": float(max(-1.0, min(1.0, imbalance))), "feat_web_density": float(density), "web_large_trades": len(large), "web_sell_ratio": float(sell_ratio)}
    except Exception as e:
        logger.debug(f"OKX web whale fetch failed: {e}")
    return {"feat_web_whale": None, "feat_web_density": None, "web_large_trades": None, "web_sell_ratio": None}
