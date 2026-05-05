"""
特徵之「眼」：視覺邊界與流動性模組
- OKX API: Klines + Order Book 找出流動性痛點 (Price Resistance / Support)
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Tuple

from data_ingestion.okx_public import fetch_candles, fetch_order_book as fetch_okx_order_book
from utils.logger import setup_logger

logger = setup_logger(__name__)


def fetch_current_price(symbol: str = "BTC/USDT") -> Optional[float]:
    """從 OKX 4H candle 末端獲取當前收盤價。"""
    try:
        rows = fetch_candles(symbol, "4h", limit=1)
        if rows:
            return float(rows[0][4])
    except Exception as e:
        logger.error(f"OKX current price fetch failed: {e}")
    return None


def fetch_current_volume(symbol: str = "BTC/USDT") -> Optional[float]:
    """從 OKX 4H candle 末端獲取當前成交量。"""
    try:
        rows = fetch_candles(symbol, "4h", limit=1)
        if rows:
            return float(rows[0][5])
    except Exception as e:
        logger.error(f"OKX volume fetch failed: {e}")
    return None


def fetch_order_book(symbol: str = "BTC/USDT", limit: int = 400) -> Optional[dict]:
    """獲取 OKX 深度圖 (訂單簿)。"""
    try:
        return fetch_okx_order_book(symbol, limit=limit)
    except Exception as e:
        logger.error(f"OKX order book fetch failed: {e}")
    return None


def find_liquidity_clusters(order_book: dict) -> Tuple[Optional[float], Optional[float]]:
    """從訂單簿中找出掛單量最大的支撐與阻力價格。"""
    if not order_book:
        return None, None
    bids = order_book.get("bids", [])
    asks = order_book.get("asks", [])
    support = None
    if bids:
        max_bid_volume = -1.0
        for row in bids:
            if len(row) < 2:
                continue
            price = float(row[0])
            qty = float(row[1])
            if qty > max_bid_volume:
                max_bid_volume = qty
                support = price
    resistance = None
    if asks:
        max_ask_volume = -1.0
        for row in asks:
            if len(row) < 2:
                continue
            price = float(row[0])
            qty = float(row[1])
            if qty > max_ask_volume:
                max_ask_volume = qty
                resistance = price
    return support, resistance


def calculate_eye_features(current_price: float, support: Optional[float], resistance: Optional[float]) -> Dict:
    features = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "current_price": current_price,
        "support_price": support,
        "resistance_price": resistance,
        "feat_eye_up": None,
        "feat_eye_down": None,
    }
    if resistance is not None:
        features["feat_eye_up"] = (resistance - current_price) / current_price
    if support is not None:
        features["feat_eye_down"] = (current_price - support) / current_price
    return features


def get_eye_feature(symbol: str = "BTC/USDT") -> Optional[Dict]:
    try:
        price = fetch_current_price(symbol)
        if price is None:
            logger.warning("無法取得 OKX current price")
            return None
        volume = fetch_current_volume(symbol)
        support, resistance = find_liquidity_clusters(fetch_order_book(symbol) or {})
        features = calculate_eye_features(price, support, resistance)
        features["volume"] = volume
        return features
    except Exception as e:
        logger.exception(f"計算 Eye 特徵時發生錯誤: {e}")
        return None


if __name__ == "__main__":
    logger.info("開始測試 eye_okx 模組...")
    result = get_eye_feature()
    print(f"[SUCCESS] Eye 特徵: {result}" if result else "[FAIL] 無法取得 Eye 特徵")
