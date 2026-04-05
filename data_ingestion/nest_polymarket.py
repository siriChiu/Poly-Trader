"""
Nest (巢) — Polymarket BTC direction probability from CLOB API
"""
import json, ssl
from datetime import datetime
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_nest_feature():
    try:
        # Get active BTC markets from Polymarket Gamma API
        url = "https://gamma-api.polymarket.com/markets?closed=false&limit=5&tag=crypto"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        data = json.loads(resp.read().decode())
        # Find BTC "up/down" market
        btc_down_prob = None
        for m in data:
            title = m.get("question", "").lower()
            if "bitcoin" in title or "btc" in title:
                outcomes = m.get("outcomes", [])
                prices = m.get("outcomePrices", [])
                if len(outcomes) >= 2 and len(prices) >= 2:
                    # First outcome is usually "Yes" = price goes up
                    # Second is "No" = price goes down
                    if isinstance(prices[1], str):
                        btc_down_prob = float(prices[1])
                    else:
                        btc_down_prob = float(prices[1])
                    break

        if btc_down_prob is not None:
            return {
                "feat_nest_pred": float(btc_down_prob - 0.5),
                "nest_raw_prob": btc_down_prob,
            }
    except Exception as e:
        logger.debug(f"Nest fetch failed: {e}")
    return {"feat_nest_pred": 0.0, "nest_raw_prob": 0.5}
