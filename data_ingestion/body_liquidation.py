"""
特徵之「身」v4：槓桿熱度模組（OI 變化率）
數據源：OKX Futures OI / Funding（免費、無金鑰）
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Optional

from data_ingestion.okx_public import fetch_current_funding, fetch_open_interest_series
from utils.logger import setup_logger

logger = setup_logger(__name__)


def fetch_oi_history(symbol: str = "BTC/USDT", period: str = "1h", limit: int = 24) -> Optional[List[float]]:
    try:
        values = []
        for item in fetch_open_interest_series(symbol, period=period, limit=limit):
            value = item.get("openInterest") or item.get("oi") or item.get("oiCcy")
            if value not in (None, ""):
                values.append(float(value))
        return values or None
    except Exception as e:
        logger.error(f"OKX OI History 失敗: {e}")
        return None


def fetch_funding_rate(symbol: str = "BTC/USDT") -> Optional[float]:
    try:
        return fetch_current_funding(symbol)
    except Exception as e:
        logger.error(f"OKX Funding Rate 失敗: {e}")
        return None


def compute_body_score(oi_history: Optional[List[float]], funding: Optional[float]) -> Dict:
    components = []
    if oi_history and len(oi_history) >= 2:
        first, last = oi_history[0], oi_history[-1]
        if first > 0:
            oi_roc = (last - first) / first
            components.append(("oi_roc", math.tanh(oi_roc * 20), 0.6))
    if funding is not None:
        components.append(("funding", math.tanh(funding * 50000), 0.4))
    score = sum(s * w for _, s, w in components) / sum(w for _, _, w in components) if components else 0.0
    label = "槓桿偏多" if score > 0.2 else "槓桿偏空" if score < -0.2 else "槓桿平穩"
    return {"feat_body_leverage": float(score), "body_label": label, "oi_roc": (oi_history[-1] - oi_history[0]) / oi_history[0] if oi_history and len(oi_history) >= 2 and oi_history[0] > 0 else None, "funding": funding}


def get_body_feature(symbol: str = "BTC/USDT") -> Optional[dict]:
    try:
        oi_hist = fetch_oi_history(symbol, period="1h", limit=24)
        funding = fetch_funding_rate(symbol)
        result = compute_body_score(oi_hist, funding)
        return {"timestamp": datetime.utcnow().isoformat() + "Z", "raw_roc": result["feat_body_leverage"], "feat_body_trend": result["feat_body_leverage"], "body_label": result["body_label"], "oi_roc": result["oi_roc"], "funding_rate": funding}
    except Exception as e:
        logger.exception(f"計算 Body (v4) 失敗: {e}")
        return None
