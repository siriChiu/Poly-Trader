"""
特徵之「耳」v3：市場共識模組
新版方案：OKX Futures 資金費率 + 多空比綜合共識
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import List, Optional

from data_ingestion.okx_public import fetch_funding_history, fetch_long_short_ratio_series
from utils.logger import setup_logger

logger = setup_logger(__name__)


def fetch_funding_history_values(symbol: str = "BTC/USDT", limit: int = 8) -> Optional[List[float]]:
    try:
        values = []
        for row in fetch_funding_history(symbol, limit=limit):
            value = row.get("fundingRate")
            if value not in (None, ""):
                values.append(float(value))
        return values or None
    except Exception as e:
        logger.error(f"OKX funding history 失敗: {e}")
        return None


def fetch_lsr_history(symbol: str = "BTC/USDT", period: str = "1h", limit: int = 12) -> Optional[List[float]]:
    try:
        values = []
        for row in fetch_long_short_ratio_series(symbol, period=period, limit=limit):
            value = row.get("longShortRatio") or row.get("ratio")
            if value not in (None, ""):
                values.append(float(value))
        return values or None
    except Exception as e:
        logger.error(f"OKX LSR history 失敗: {e}")
        return None


def get_ear_feature(symbol: str = "BTC/USDT") -> Optional[dict]:
    try:
        funding_hist = fetch_funding_history_values(symbol, limit=8)
        lsr_hist = fetch_lsr_history(symbol)
        components = []
        if funding_hist and len(funding_hist) >= 2:
            recent, older = funding_hist[-1], funding_hist[0]
            components.append(("fr_dir", math.tanh(recent * 100000), 0.3))
            components.append(("fr_trend", math.tanh((recent - older) * 200000), 0.2))
        if lsr_hist and len(lsr_hist) >= 2:
            recent_lsr, older_lsr = lsr_hist[-1], lsr_hist[0]
            components.append(("lsr", -math.tanh(((recent_lsr - older_lsr) / max(older_lsr, 0.01)) * 5), 0.3))
        if funding_hist:
            components.append(("fr_abs", math.tanh(funding_hist[-1] * 50000), 0.2))
        score = sum(s * w for _, s, w in components) / sum(w for _, _, w in components) if components else 0.0
        prob = (score + 1) / 2
        return {"timestamp": datetime.utcnow().isoformat() + "Z", "prob": prob, "feat_ear_risk": prob}
    except Exception as e:
        logger.exception(f"計算 Ear (v3) 時發生錯誤: {e}")
        return None
