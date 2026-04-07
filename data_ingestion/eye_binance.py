"""
特徵之「眼」：視覺邊界與流動性模組
- Binance API: Klines + Order Book 找出流動性痛點 (Price Resistance / Support)
"""

import requests
from typing import Optional, Dict, Tuple
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Binance REST endpoints (無需金鑰)
KLINES_URL = "https://api.binance.com/api/v3/klines"
DEPTH_URL = "https://api.binance.com/api/v3/depth"

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

def fetch_current_price(symbol: str = "BTCUSDT") -> Optional[float]:
    """從 klines 末端獲取當前收盤價"""
    try:
        session = _create_session()
        params = {"symbol": symbol, "interval": "4h", "limit": 1}
        resp = session.get(KLINES_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            # kline 結構: [openTime, open, high, low, close, volume, closeTime, ...]
            return float(data[0][4])  # close price
    except Exception as e:
        logger.error(f"获取当前价格失败: {e}")
    return None


def fetch_current_volume(symbol: str = "BTCUSDT") -> Optional[float]:
    """從 klines 末端獲取當前成交量"""
    try:
        session = _create_session()
        params = {"symbol": symbol, "interval": "4h", "limit": 1}
        resp = session.get(KLINES_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            return float(data[0][5])  # volume
    except Exception as e:
        logger.error(f"获取成交量失败: {e}")
    return None

def fetch_order_book(symbol: str = "BTCUSDT", limit: int = 1000) -> Optional[dict]:
    """獲取 Binance 深度圖 (訂單簿)"""
    try:
        session = _create_session()
        params = {"symbol": symbol, "limit": limit}
        resp = session.get(DEPTH_URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"获取 Order Book 失败: {e}")
    return None

def find_liquidity_clusters(order_book: dict) -> Tuple[Optional[float], Optional[float]]:
    """
    從訂單簿中找出掛單量最大的價格點：
    - Price_resistance: 上方的最大掛單量價格
    - Price_support: 下方的最大掛單量價格
    返回 (price_support, price_resistance) 若無則為 None
    """
    if not order_book:
        return None, None

    # Bids (买单，支持位) 和 Asks (卖单，阻力位)
    bids = order_book.get("bids", [])  # 每个 [price, quantity]
    asks = order_book.get("asks", [])

    # 找出 Bids 中 volume 最大的价格
    support = None
    if bids:
        max_bid_volume = -1
        for price_str, qty_str in bids:
            price = float(price_str)
            qty = float(qty_str)
            if qty > max_bid_volume:
                max_bid_volume = qty
                support = price

    # 找出 Asks 中 volume 最大的价格
    resistance = None
    if asks:
        max_ask_volume = -1
        for price_str, qty_str in asks:
            price = float(price_str)
            qty = float(qty_str)
            if qty > max_ask_volume:
                max_ask_volume = qty
                resistance = price

    return support, resistance

def calculate_eye_features(current_price: float, support: Optional[float], resistance: Optional[float]) -> Dict:
    """
    計算「眼」的兩個特徵：
    - Feat_Eye_Up: (Price_resistance - P_current) / P_current
    - Feat_Eye_Down: (P_current - Price_support) / P_current
    若無對應價格，則為 None。
    """
    features = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "current_price": current_price,
        "support_price": support,
        "resistance_price": resistance,
        "feat_eye_up": None,
        "feat_eye_down": None
    }

    if resistance is not None:
        features["feat_eye_up"] = (resistance - current_price) / current_price
    if support is not None:
        features["feat_eye_down"] = (current_price - support) / current_price

    return features

def get_eye_feature(symbol: str = "BTCUSDT") -> Optional[Dict]:
    """
    主函数：整合眼部特征。
    """
    try:
        price = fetch_current_price(symbol)
        if price is None:
            logger.warning("无法获取当前价格")
            return None

        volume = fetch_current_volume(symbol)

        ob = fetch_order_book(symbol)
        support, resistance = find_liquidity_clusters(ob)

        features = calculate_eye_features(price, support, resistance)
        features["volume"] = volume
        return features
    except Exception as e:
        logger.exception(f"计算 Eye 特征时发生错误: {e}")
        return None

if __name__ == "__main__":
    logger.info("开始测试 eye_binance 模块...")
    result = get_eye_feature()
    if result:
        print(f"[SUCCESS] Eye 特徵: {result}")
    else:
        print("[FAIL] 无法获取 Eye 特徵")
