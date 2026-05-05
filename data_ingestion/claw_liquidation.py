"""
Claw (利爪) — Liquidation Heatmap
Primary datasource: Coinalyze liquidation history.
Legacy fallback: CoinGlass v4 liquidation history when Coinalyze is unavailable.
"""

import json
import math
import os
import ssl
import time
from functools import lru_cache
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import load_config
from utils.logger import setup_logger

logger = setup_logger(__name__)
COINGLASS_API_KEY = os.getenv("COINGLASS_API_KEY", "")
COINALYZE_URL = "https://api.coinalyze.net/v1/liquidation-history"
COINGLASS_URL = "https://open-api-v4.coinglass.com/api/futures/liquidation/history"
COINALYZE_SYMBOL_MAP = {
    "BTC/USDT": "BTC/USDT_PERP.A",
}


@lru_cache(maxsize=1)
def _get_coinalyze_api_key() -> str:
    try:
        cfg = load_config()
    except Exception:
        return ""
    return str((cfg or {}).get("coinalyze", {}).get("api_key") or "").strip()


def _empty_response(status: str, message: str | None = None):
    return {
        "feat_claw": None,
        "feat_claw_intensity": None,
        "claw_long_liq": None,
        "claw_short_liq": None,
        "claw_ratio": None,
        "_meta": {"status": status, "message": message},
    }


def _normalize_liquidation_features(long_liq: float, short_liq: float, source: str):
    total = float(long_liq + short_liq)
    ratio = float(long_liq / short_liq) if short_liq > 0 else (float(long_liq) if long_liq > 0 else 1.0)
    feat = float((ratio - 1.0) / (ratio + 1.0))
    # Coinalyze liquidation history is denominated in base asset for many venues;
    # use a gentler scale than the old USD-based CoinGlass normalization.
    intensity_scale = 50.0 if source == "coinalyze" else 100_000_000.0
    feat_intensity = float(math.tanh(total / intensity_scale))
    return {
        "feat_claw": feat,
        "feat_claw_intensity": feat_intensity,
        "claw_long_liq": float(long_liq),
        "claw_short_liq": float(short_liq),
        "claw_ratio": ratio,
        "_meta": {"status": "ok", "source": source},
    }


def _fetch_from_coinalyze(symbol: str):
    api_key = _get_coinalyze_api_key()
    if not api_key:
        return _empty_response("auth_missing", "coinalyze.api_key is missing in config.yaml.")

    market_symbol = COINALYZE_SYMBOL_MAP.get(symbol, f"{symbol}_PERP.A")
    now = int(time.time())
    params = {
        "symbols": market_symbol,
        "interval": "4hour",
        "from": now - 24 * 3600,
        "to": now,
    }
    req = Request(f"{COINALYZE_URL}?{urlencode(params)}", headers={"api_key": api_key, "User-Agent": "Mozilla/5.0"})
    try:
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        payload = json.loads(resp.read().decode())
        if not isinstance(payload, list) or not payload:
            return _empty_response("no_data", "Coinalyze liquidation response returned no rows.")
        history = payload[0].get("history") or []
        if not history:
            return _empty_response("no_data", "Coinalyze liquidation history is empty.")
        recent = history[-6:]
        long_liq = sum(float(item.get("l") or 0.0) for item in recent)
        short_liq = sum(float(item.get("s") or 0.0) for item in recent)
        if long_liq <= 0 and short_liq <= 0:
            return _empty_response("no_data", "Coinalyze liquidation history had no usable values.")
        return _normalize_liquidation_features(long_liq, short_liq, "coinalyze")
    except HTTPError as exc:
        return _empty_response("http_error", f"Coinalyze HTTP {exc.code}: {exc.reason}")
    except Exception as exc:
        logger.debug(f"Claw Coinalyze fetch failed: {exc}")
        return _empty_response("fetch_error", str(exc))


def _fetch_from_coinglass(symbol: str):
    if not COINGLASS_API_KEY:
        return _empty_response("auth_missing", "COINGLASS_API_KEY is missing; liquidation history endpoint requires CoinGlass v4 auth.")
    try:
        url = f"{COINGLASS_URL}?exchange=OKX&symbol={symbol}&interval=4h&limit=6"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0", "CG-API-KEY": COINGLASS_API_KEY})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        data = json.loads(resp.read().decode())
        if isinstance(data, dict) and str(data.get("code")) == "401":
            return _empty_response("auth_missing", data.get("msg") or "CoinGlass liquidation endpoint rejected the API key.")
        items = data.get("data") if isinstance(data, dict) else None
        if not items:
            return _empty_response("no_data", "CoinGlass liquidation response returned no rows.")
        recent = items[-6:]
        long_liq = sum(float(i.get("longLiquidationUsd", 0) or 0.0) for i in recent)
        short_liq = sum(float(i.get("shortLiquidationUsd", 0) or 0.0) for i in recent)
        if long_liq <= 0 and short_liq <= 0:
            return _empty_response("no_data", "CoinGlass liquidation response had no usable values.")
        return _normalize_liquidation_features(long_liq, short_liq, "coinglass")
    except HTTPError as exc:
        return _empty_response("http_error", f"CoinGlass HTTP {exc.code}: {exc.reason}")
    except Exception as exc:
        logger.debug(f"Claw CoinGlass fetch failed: {exc}")
        return _empty_response("fetch_error", str(exc))


def get_claw_feature(symbol="BTC/USDT"):
    result = _fetch_from_coinalyze(symbol)
    if result.get("_meta", {}).get("status") == "ok":
        return result

    fallback = _fetch_from_coinglass(symbol)
    if fallback.get("_meta", {}).get("status") == "ok":
        fallback["_meta"]["fallback_after"] = result.get("_meta")
        return fallback

    # Prefer the Coinalyze failure reason when both are unavailable because the
    # user explicitly configured this source in config.yaml.
    return result if result.get("_meta", {}).get("status") != "auth_missing" or not COINGLASS_API_KEY else fallback
