"""
Web (網) — Whale Activity via Binance large trades (public, no key)
"""
import json, ssl, math
from datetime import datetime
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_web_feature():
    try:
        url = "https://api.binance.com/api/v3/aggTrades?symbol=BTCUSDT&limit=1000"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        trades = json.loads(resp.read().decode())
        # Use quote notional instead of raw BTC qty so the feature still moves in quieter periods.
        large = []
        for t in trades:
            price = float(t.get("p", 0) or 0)
            qty = float(t.get("q", 0) or 0)
            quote_notional = price * qty
            if quote_notional >= 50_000:
                large.append((t, quote_notional))
        total_notional = sum(notional for _, notional in large)
        if total_notional <= 0:
            return {
                "feat_web_whale": 0.0,
                "feat_web_density": 0.0,
                "web_large_trades": 0,
                "web_sell_ratio": 0.5,
            }
        maker_sell_notional = sum(notional for t, notional in large if t.get("m", False))
        sell_ratio = maker_sell_notional / total_notional
        density = math.tanh(total_notional / 5_000_000)
        imbalance = (sell_ratio - 0.5) * 2.0
        return {
            "feat_web_whale": float(max(-1.0, min(1.0, imbalance))),
            "feat_web_density": float(density),
            "web_large_trades": len(large),
            "web_sell_ratio": float(sell_ratio),
        }
    except Exception as e:
        logger.debug(f"Web fetch failed: {e}")
    return {"feat_web_whale": 0.0, "feat_web_density": 0.0,
            "web_large_trades": 0, "web_sell_ratio": 0.5}
