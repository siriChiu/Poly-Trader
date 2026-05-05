"""
特徵之「鼻」：衍生品氣味與資金成本模組
- OKX Futures API: Funding Rate 與 Open Interest
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import List, Optional

from data_ingestion.okx_public import fetch_current_funding, fetch_open_interest_series, last_float
from utils.logger import setup_logger

logger = setup_logger(__name__)


def fetch_funding_rate(symbol: str = "BTC/USDT") -> Optional[float]:
    try:
        return fetch_current_funding(symbol)
    except Exception as e:
        logger.error(f"OKX Funding Rate API 失敗: {e}")
        return None


def fetch_oi_history(symbol: str = "BTC/USDT", period: str = "1d", limit: int = 3) -> Optional[List[dict]]:
    try:
        rows = fetch_open_interest_series(symbol, period=period, limit=limit)
        oi_list = []
        for item in rows:
            value = item.get("openInterest") or item.get("oi") or item.get("oiCcy")
            if value in (None, ""):
                continue
            ts = item.get("ts") or item.get("timestamp")
            oi_list.append({"timestamp": datetime.fromtimestamp(int(ts) / 1000) if ts not in (None, "") else datetime.utcnow(), "openInterest": float(value)})
        oi_list.sort(key=lambda x: x["timestamp"])
        return oi_list
    except Exception as e:
        logger.error(f"OKX OI History API 失敗: {e}")
        return None


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def compress_funding_sigmoid(funding_rate: float) -> float:
    return 2 * sigmoid(funding_rate * 10000) - 1


def calculate_oi_roc(oi_history: List[dict]) -> Optional[float]:
    if len(oi_history) < 2:
        return None
    prev = oi_history[-2]["openInterest"]
    curr = oi_history[-1]["openInterest"]
    if prev == 0:
        return None
    return (curr - prev) / prev


def get_nose_feature(symbol: str = "BTC/USDT") -> Optional[dict]:
    try:
        fr = fetch_funding_rate(symbol)
        if fr is None:
            logger.warning("無法取得 OKX Funding Rate")
            return None
        feat_funding = compress_funding_sigmoid(fr)
        oi_hist = fetch_oi_history(symbol)
        oi_roc = calculate_oi_roc(oi_hist) if oi_hist and len(oi_hist) >= 2 else None
        return {"timestamp": datetime.utcnow().isoformat() + "Z", "funding_rate_raw": fr, "feat_nose_funding_sigmoid": feat_funding, "oi_roc": oi_roc}
    except Exception as e:
        logger.exception(f"計算 Nose 特徵時發生錯誤: {e}")
        return None


if __name__ == "__main__":
    logger.info("開始測試 nose_futures 模組...")
    result = get_nose_feature()
    print(f"[SUCCESS] Nose 特徵: {result}" if result else "[FAIL] 無法取得 Nose 特徵")
