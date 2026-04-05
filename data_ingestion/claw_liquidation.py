"""
Claw (利爪) — Liquidation Heatmap
DataSource: CoinGlass public API (free API key)
"""
import json, os, ssl, math
from datetime import datetime
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)
API_KEY = os.environ.get("COINGLASS_API_KEY", "")


def get_claw_feature(symbol="BTC"):
    try:
        url = "https://open-api.coinglass.com/api/v3/futures/liquidation/history"
        url += f"?symbol={symbol}&interval=4h&limit=6"
        headers = {}
        if API_KEY:
            headers["X-CG-API-KEY"] = API_KEY
        req = Request(url, headers=headers if headers else {"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        data = json.loads(resp.read().decode())
        if data and data.get("success") and data.get("data"):
            items = data["data"][-6:]  # last 24h
            long_liq = sum(float(i.get("longLiquidationUsd", 0) or 0) for i in items)
            short_liq = sum(float(i.get("shortLiquidationUsd", 0) or 0) for i in items)
            total = long_liq + short_liq
            ratio = long_liq / short_liq if short_liq > 0 else 1.0
            # Higher long_liq = more shorts win = good for SHORT strategy
            feat = (ratio - 1.0) / (ratio + 1.0)  # -1..+1, positive = more longs liquidated
            feat_intensity = math.tanh(total / 100_000_000)  # normalize to 0..1
            return {
                "feat_claw": float(feat),
                "feat_claw_intensity": float(feat_intensity),
                "claw_long_liq": long_liq,
                "claw_short_liq": short_liq,
                "claw_ratio": ratio,
            }
    except Exception as e:
        logger.debug(f"Claw fetch failed: {e}")
    return {"feat_claw": 0.0, "feat_claw_intensity": 0.0,
            "claw_long_liq": 0, "claw_short_liq": 0, "claw_ratio": 1.0}
