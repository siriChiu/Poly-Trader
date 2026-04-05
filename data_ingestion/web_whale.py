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
        url = "https://api.binance.com/api/v3/trades?symbol=BTCUSDT&limit=1000"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        trades = json.loads(resp.read().decode())
        large = [t for t in trades if float(t.get("qty", 0)) > 1.0]
        # isBuyerMaker=True => seller was maker => passive sell pressure
        maker_sells = sum(1 for t in large if t.get("isBuyerMaker", False))
        total = len(large)
        sell_ratio = maker_sells / total if total > 0 else 0.5
        density = math.tanh(len(large) / 20.0)
        return {
            "feat_web_whale": float(sell_ratio - 0.5),  # -0.5..+0.5, positive = sell pressure
            "feat_web_density": float(density),
            "web_large_trades": len(large),
            "web_sell_ratio": sell_ratio,
        }
    except Exception as e:
        logger.debug(f"Web fetch failed: {e}")
    return {"feat_web_whale": 0.0, "feat_web_density": 0.0,
            "web_large_trades": 0, "web_sell_ratio": 0.5}
