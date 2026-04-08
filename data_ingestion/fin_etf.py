"""
Fin (魚鰭) — BTC Spot ETF Flow from CoinGlass
"""
import json, os, ssl, math
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)
API_KEY = os.getenv("COINGLASS_API_KEY", "")
ETF_URL = "https://open-api.coinglass.com/api/bitcoin/etf/flow-history"


def _parse_netflow(items):
    if not items:
        return None
    total_net = 0.0
    found = False
    for item in items:
        if item is None:
            continue
        if item.get("netInflow") is not None:
            total_net += float(item.get("netInflow") or 0.0)
            found = True
            continue
        inflow = item.get("inflow")
        outflow = item.get("outflow")
        if inflow is not None or outflow is not None:
            total_net += float(inflow or 0.0) - float(outflow or 0.0)
            found = True
    return total_net if found else None


def get_fin_feature():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        if API_KEY:
            headers["X-CG-API-KEY"] = API_KEY
        req = Request(ETF_URL, headers=headers)
        resp = urlopen(req, context=ssl.create_default_context(), timeout=12)
        data = json.loads(resp.read().decode())
        items = data.get("data") if isinstance(data, dict) else None
        if data and data.get("success") and items:
            recent = items[-7:] if len(items) > 7 else items
            net = _parse_netflow(recent)
            if net is not None:
                # Negative netflow = outflow = bearish for BTC = good for SHORT
                feat = -math.tanh(net / 500_000_000)
                return {
                    "feat_fin_netflow": float(feat),
                    "fin_raw_netflow": float(net),
                }
    except Exception as e:
        logger.debug(f"Fin fetch failed: {e}")
    return {"feat_fin_netflow": 0.0, "fin_raw_netflow": 0.0}
