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

# Polymarket Gamma API endpoint
GAMMA_URL = "https://gamma-api.polymarket.com/events"

# 我们关注的经济事件关键词（可根据需要扩展）
TARGET_KEYWORDS = [
    "federal reserve",
    "fed",
    "interest rate",
    "inflation",
    "bitcoin",
    "crypto"
]

def _create_session(retries: int = 3, backoff_factor: float = 0.5):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def fetch_events(query: Optional[str] = None, limit: int = 100) -> Optional[List[dict]]:
    """
    从 Polymarket Gamma API 获取事件列表。
    Args:
        query: 搜索关键词，如 "fed"
        limit: 返回事件数量
    Returns:
        事件列表，每个事件包含 markets 等字段
    """
    try:
        session = _create_session()
        params = {"limit": limit}
        if query:
            params["query"] = query
        resp = session.get(GAMMA_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # 兼容：可能返回 {"events": [...]} 或直接 [...]
        if isinstance(data, dict):
            return data.get("events", [])
        elif isinstance(data, list):
            return data
        else:
            logger.error(f"Unexpected response type: {type(data)}")
            return []
    except Exception as e:
        logger.error(f"Polymarket API 请求失败: {e}")
    return None

def extract_market_probability(event: dict, target_market_idx: int = 0) -> Optional[float]:
    """
    从事件中提取第一个市场的价格作为概率（0~1）。
    如果事件有多个市场，取指定索引。
    """
    markets = event.get("markets", [])
    if not markets:
        return None
    try:
        # 取首个市场
        market = markets[target_market_idx]
        # price 字段代表概率（例如 0.73）
        price = float(market.get("price", 0.0))
        return price
    except (IndexError, ValueError, TypeError) as e:
        logger.warning(f"提取市场概率失败: {e}")
    return None

def find_best_risk_event(events: List[dict]) -> Optional[dict]:
    """
    在事件列表中，返回一个最具风险提示意义的事件概率。
    策略：优先包含 "fed" 或 "inflation" 的事件。
    """
    for event in events:
        title = event.get("title", "").lower()
        slug = event.get("slug", "").lower()
        # 检查是否为宏观经济相关
        if any(kw in title or kw in slug for kw in ["fed", "interest rate", "inflation"]):
            return event
    # 如果没有宏观经济相关，返回第一个有市场的事件
    for event in events:
        if event.get("markets"):
            return event
    return None

def get_ear_feature() -> Optional[dict]:
    """
    主函数：获取一个代表性的事件概率作为风险特征。
    返回格式：
        {
            "timestamp": str,
            "event_title": str,
            "prob": float (0~1),
            "feat_ear_risk": float (等同于 prob，数值越高风险越大)
        }
    """
    try:
        # 1. 尝试搜索 "fed" 相关事件
        events = fetch_events(query="fed", limit=50)
        if not events:
            logger.warning("未找到 Fed 相关事件")
            events = fetch_events(limit=50)  # 获取默认热门事件

        if not events:
            logger.warning("Polymarket 无可用事件")
            return None

        chosen = find_best_risk_event(events)
        if not chosen:
            return None

        prob = extract_market_probability(chosen)
        if prob is None:
            return None

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_title": chosen.get("title"),
            "prob": prob,
            "feat_ear_risk": prob  # 直接使用
        }
    except Exception as e:
        logger.exception(f"计算 Ear 特征时发生错误: {e}")
        return None

if __name__ == "__main__":
    logger.info("开始测试 ear_polymarket 模块...")
    result = get_ear_feature()
    if result:
        print(f"[SUCCESS] Ear 特徵: {result}")
    else:
        print("[FAIL] 无法获取 Ear 特徵")
