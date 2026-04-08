"""
Fin (魚鰭) — BTC Spot ETF Flow from CoinGlass
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
ETF_URL = "https://open-api-v4.coinglass.com/api/etf/bitcoin/flow-history"


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


def _missing_auth_response(message: str):
    return {
        "feat_fin_netflow": None,
        "fin_raw_netflow": None,
        "_meta": {"status": "auth_missing", "message": message},
    }


def get_fin_feature():
    if not API_KEY:
        return _missing_auth_response("COINGLASS_API_KEY is missing; ETF flow endpoint requires CoinGlass v4 auth.")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "CG-API-KEY": API_KEY,
        }
        req = Request(ETF_URL, headers=headers)
        resp = urlopen(req, context=ssl.create_default_context(), timeout=12)
        data = json.loads(resp.read().decode())
        if isinstance(data, dict) and str(data.get("code")) == "401":
            return _missing_auth_response(data.get("msg") or "CoinGlass ETF endpoint rejected the API key.")
        items = data.get("data") if isinstance(data, dict) else None
        if data and items:
            recent = items[-7:] if len(items) > 7 else items
            net = _parse_netflow(recent)
            if net is not None:
                # Negative netflow = outflow = bearish for BTC = good for SHORT/defensive signal
                feat = -math.tanh(net / 500_000_000)
                return {
                    "feat_fin_netflow": float(feat),
                    "fin_raw_netflow": float(net),
                    "_meta": {"status": "ok"},
                }
            return {
                "feat_fin_netflow": None,
                "fin_raw_netflow": None,
                "_meta": {"status": "no_data", "message": "CoinGlass ETF response did not contain usable net-flow fields."},
            }
    except HTTPError as e:
        logger.debug(f"Fin HTTP error: {e}")
        return {
            "feat_fin_netflow": None,
            "fin_raw_netflow": None,
            "_meta": {"status": "http_error", "message": f"HTTP {e.code}: {e.reason}"},
        }
    except Exception as e:
        logger.debug(f"Fin fetch failed: {e}")
        return {
            "feat_fin_netflow": None,
            "fin_raw_netflow": None,
            "_meta": {"status": "fetch_error", "message": str(e)},
        }
    return {
        "feat_fin_netflow": None,
        "fin_raw_netflow": None,
        "_meta": {"status": "no_data", "message": "CoinGlass ETF endpoint returned no rows."},
    }
