"""
Fin (魚鰭) — BTC Spot ETF Flow from CoinGlass
"""
import json, os, ssl, math
from datetime import datetime
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)
API_KEY = os.environ.get("COINGLASS_API_KEY", "")


def get_fin_feature():
    try:
        url = "https://open-api.coinglass.com/api/bitcoin/etf/flow-history"
        headers = {}
        if API_KEY:
            headers["X-CG-API-KEY"] = API_KEY
        req = Request(url, headers=headers if headers else {"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        data = json.loads(resp.read().decode())
        if data and data.get("success") and data.get("data"):
            items = data["data"][-7:]  # last 7 days
            net = sum(float(i.get("netInflow", 0) or 0) for i in items)
            # Negative netflow = outflow = bearish for BTC = good for SHORT
            feat = -math.tanh(net / 500_000_000)
            return {
                "feat_fin_netflow": float(feat),
                "fin_raw_netflow": net,
            }
    except Exception as e:
        logger.debug(f"Fin fetch failed: {e}")
    return {"feat_fin_netflow": 0.0, "fin_raw_netflow": 0.0}
