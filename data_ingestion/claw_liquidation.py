import requests
import json
import os
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)

COINGLASS_API_KEY = os.environ.get("COINGLASS_API_KEY", "")

def _cg_get(path, params=None):
    if not COINGLASS_API_KEY:
        return None
    headers = {"Content-Type": "application/json", "coinglassSecret": COINGLASS_API_KEY}
    try:
        r = requests.get(f"https://open-api-v3.coinglass.com{path}", params=params or {}, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def get_claw_feature(symbol="BTC"):
    """
    清算地圖特徵：
    - 多頭清算密集區 = 價格磁鐵 (向下吸)
    - 空頭清算密集區 = 上漲燃料
    - feat_claw_liquidation_ratio: 多頭vs空頭清算比例
    - feat_claw_total_1h: 最近1h總清算量(百萬USDT)
    - feat_claw_long_ratio: 多頭清算佔比 (越高=越有利SHORT)
    """
    params = {"exchange": "Binance", "symbol": symbol, "period": "1h", "limit": 24}
    data = _cg_get("/api/futures/liquidation/history", params)

    if not data or data.get("code") != 2000 or not data.get("data", {}).get("items"):
        return None

    items = data["data"]["items"]
    long_liq = sum(float(it.get("liquidatedLong", 0) or 0) for it in items)
    short_liq = sum(float(it.get("liquidatedShort", 0) or 0) for it in items)
    total = long_liq + short_liq

    long_ratio = long_liq / total if total > 0 else 0.5
    recent_1h = items[-1] if items else {}
    liq_1h = (float(recent_1h.get("liquidatedLong", 0) or 0) +
              float(recent_1h.get("liquidatedShort", 0) or 0)) / 1_000_000

    logger.info(f"Claw: long_liq={long_liq/1e6:.1f}M, short_liq={short_liq/1e6:.1f}M, ratio={long_ratio:.3f}")
    return {
        "feat_claw_long_ratio": long_ratio,
        "feat_claw_total_1h": liq_1h,
        "raw_long_liq": long_liq,
        "raw_short_liq": short_liq,
    }
