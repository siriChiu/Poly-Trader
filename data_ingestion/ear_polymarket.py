"""
五感之「耳」：市場共識與總經模組
- Polymarket Gamma API: 获取预测市场的概率作为市场情绪参考
"""

import requests
from typing import Optional, Dict, List
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

GAMMA_URL = "https://gamma-api.polymarket.com/events"

TARGET_KEYWORDS = [
    "federal reserve", "fed", "interest rate",
    "inflation", "bitcoin", "crypto",
]


def _create_session(retries: int = 3, backoff_factor: float = 0.5):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_events(query: Optional[str] = None, limit: int = 100) -> Optional[List[dict]]:
    """從 Polymarket Gamma API 獲取事件列表。"""
    try:
        session = _create_session()
        params = {"limit": limit}
        if query:
            params["query"] = query
        resp = session.get(GAMMA_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            return data.get("events", [])
        elif isinstance(data, list):
            return data
        return []
    except Exception as e:
        logger.error(f"Polymarket API 請求失敗: {e}")
    return None


def extract_market_probability(market: dict) -> Optional[float]:
    """
    從市場對象中提取概率 (0~1)。
    嘗試多個字段：outcomePrices, bestBid, lastTradePrice, price
    """
    # 1. outcomePrices: ["0.23", "0.77"] → 取第一個（"Yes" 概率）
    op = market.get("outcomePrices")
    if op:
        try:
            import json
            if isinstance(op, str):
                prices = json.loads(op)
            elif isinstance(op, list):
                prices = op
            else:
                prices = None
            if prices and len(prices) >= 1:
                val = float(prices[0])
                if 0 < val < 1:
                    return val
        except (ValueError, json.JSONDecodeError):
            pass

    # 2. bestBid
    bid = market.get("bestBid")
    if bid is not None:
        try:
            val = float(bid)
            if 0 < val < 1:
                return val
        except (ValueError, TypeError):
            pass

    # 3. lastTradePrice
    ltp = market.get("lastTradePrice")
    if ltp is not None:
        try:
            val = float(ltp)
            if 0 < val < 1:
                return val
        except (ValueError, TypeError):
            pass

    # 4. price (舊字段)
    price = market.get("price")
    if price is not None:
        try:
            val = float(price)
            if 0 < val < 1:
                return val
        except (ValueError, TypeError):
            pass

    return None


def find_best_risk_event(events: List[dict]) -> Optional[dict]:
    """在事件列表中返回最具風險提示意義的事件。"""
    for event in events:
        title = event.get("title", "").lower()
        slug = event.get("slug", "").lower()
        if any(kw in title or kw in slug for kw in ["fed", "interest rate", "inflation"]):
            if event.get("markets"):
                return event
    for event in events:
        if event.get("markets"):
            return event
    return None


def get_ear_feature() -> Optional[dict]:
    """主函數：獲取代表性事件概率作為風險特徵。"""
    try:
        events = fetch_events(query="fed", limit=50)
        if not events:
            events = fetch_events(limit=50)
        if not events:
            return None

        chosen = find_best_risk_event(events)
        if not chosen:
            return None

        markets = chosen.get("markets", [])
        if not markets:
            return None

        prob = extract_market_probability(markets[0])
        if prob is None:
            logger.warning(f"無法從市場提取概率: {chosen.get('title')}")
            return None

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_title": chosen.get("title"),
            "prob": prob,
            "feat_ear_risk": prob,
        }
    except Exception as e:
        logger.exception(f"計算 Ear 特徵時發生錯誤: {e}")
        return None
