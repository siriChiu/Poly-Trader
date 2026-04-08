"""
Claw (利爪) — Liquidation Heatmap
DataSource: CoinGlass API (requires API key for v4 endpoints)
"""
import json
import math
import os
import ssl
from urllib.error import HTTPError
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)
API_KEY = os.getenv("COINGLASS_API_KEY", "")


def _missing_auth_response(message: str):
    return {
        "feat_claw": None,
        "feat_claw_intensity": None,
        "claw_long_liq": None,
        "claw_short_liq": None,
        "claw_ratio": None,
        "_meta": {"status": "auth_missing", "message": message},
    }


def get_claw_feature(symbol="BTCUSDT"):
    if not API_KEY:
        return _missing_auth_response("COINGLASS_API_KEY is missing; liquidation history endpoint requires CoinGlass v4 auth.")
    try:
        url = "https://open-api-v4.coinglass.com/api/futures/liquidation/history"
        url += f"?exchange=Binance&symbol={symbol}&interval=4h&limit=6"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "CG-API-KEY": API_KEY,
        }
        req = Request(url, headers=headers)
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        data = json.loads(resp.read().decode())
        if isinstance(data, dict) and str(data.get("code")) == "401":
            return _missing_auth_response(data.get("msg") or "CoinGlass liquidation endpoint rejected the API key.")
        if data and data.get("data"):
            items = data["data"][-6:]  # last 24h in 4h buckets
            long_liq = sum(float(i.get("longLiquidationUsd", 0) or 0) for i in items)
            short_liq = sum(float(i.get("shortLiquidationUsd", 0) or 0) for i in items)
            total = long_liq + short_liq
            ratio = long_liq / short_liq if short_liq > 0 else 1.0
            # Higher long_liq = more downside liquidation pressure.
            feat = (ratio - 1.0) / (ratio + 1.0)
            feat_intensity = math.tanh(total / 100_000_000)
            return {
                "feat_claw": float(feat),
                "feat_claw_intensity": float(feat_intensity),
                "claw_long_liq": long_liq,
                "claw_short_liq": short_liq,
                "claw_ratio": ratio,
                "_meta": {"status": "ok"},
            }
        return {
            "feat_claw": None,
            "feat_claw_intensity": None,
            "claw_long_liq": None,
            "claw_short_liq": None,
            "claw_ratio": None,
            "_meta": {"status": "no_data", "message": "CoinGlass liquidation response returned no rows."},
        }
    except HTTPError as e:
        logger.debug(f"Claw HTTP error: {e}")
        return {
            "feat_claw": None,
            "feat_claw_intensity": None,
            "claw_long_liq": None,
            "claw_short_liq": None,
            "claw_ratio": None,
            "_meta": {"status": "http_error", "message": f"HTTP {e.code}: {e.reason}"},
        }
    except Exception as e:
        logger.debug(f"Claw fetch failed: {e}")
        return {
            "feat_claw": None,
            "feat_claw_intensity": None,
            "claw_long_liq": None,
            "claw_short_liq": None,
            "claw_ratio": None,
            "_meta": {"status": "fetch_error", "message": str(e)},
        }
