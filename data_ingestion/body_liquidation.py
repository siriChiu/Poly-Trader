"""
五感之「身」v3：清算痛點模組 (Liquidation Heatmap)

核心概念：價格像磁鐵，自動往「高爆倉痛點」吸過去（獵殺流動性）
數據源：
  1. Coinglass API v4（需 API Key，提供清算熱圖數據）
  2. Binance Futures OI + 資金費率（免費，間接估算）
  3. 期貨溢價（Futures Premium）作為清算壓力代理

特徵計算：
  - 近端清算密度：當前價格 ±2% 範圍內的清算量佔比
  - 清算偏向：上方清算 vs 下方清算的比例
  - 壓力指數：結合 OI、資金費率、溢價的綜合壓力分數
"""

import requests
import math
from typing import Optional, Dict, List
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Binance Futures endpoints (免費)
OPEN_INTEREST_URL = "https://fapi.binance.com/futures/data/openInterestHist"
LONG_SHORT_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
TAKER_URL = "https://fapi.binance.com/futures/data/takerlongshortRatio"
FUNDING_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"


def _create_session(retries: int = 3, backoff_factor: float = 0.5):
    session = requests.Session()
    retry = Retry(
        total=retries, read=retries, connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# ─────────────────────────────────────────
# Binance Futures 數據
# ─────────────────────────────────────────

def fetch_futures_oi(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 24) -> Optional[List[dict]]:
    """獲取期貨 OI 歷史"""
    try:
        session = _create_session()
        params = {"symbol": symbol, "period": period, "limit": limit}
        resp = session.get(OPEN_INTEREST_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [{"timestamp": d["timestamp"], "oi": float(d["sumOpenInterest"])} for d in data]
    except Exception as e:
        logger.error(f"OI API 失敗: {e}")
        return None


def fetch_funding_rate(symbol: str = "BTCUSDT") -> Optional[float]:
    """獲取當前資金費率"""
    try:
        session = _create_session()
        resp = session.get(FUNDING_URL, params={"symbol": symbol}, timeout=10)
        resp.raise_for_status()
        return float(resp.json().get("lastFundingRate", 0))
    except Exception as e:
        logger.error(f"Funding Rate API 失敗: {e}")
        return None


def fetch_long_short_ratio(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 24) -> Optional[List[float]]:
    """獲取多空帳戶比"""
    try:
        session = _create_session()
        params = {"symbol": symbol, "period": period, "limit": limit}
        resp = session.get(LONG_SHORT_URL, params=params, timeout=10)
        resp.raise_for_status()
        return [float(d["longShortRatio"]) for d in resp.json()]
    except Exception as e:
        logger.error(f"Long/Short Ratio API 失敗: {e}")
        return None


def fetch_futures_price(symbol: str = "BTCUSDT") -> Optional[float]:
    """獲取期貨當前價格"""
    try:
        session = _create_session()
        resp = session.get(KLINES_URL, params={"symbol": symbol, "interval": "1h", "limit": 1}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return float(data[0][4]) if data else None
    except Exception as e:
        logger.error(f"Futures price API 失敗: {e}")
        return None


# ─────────────────────────────────────────
# 清算壓力特徵計算
# ─────────────────────────────────────────

def calculate_liquidation_pressure(
    oi_history: Optional[List[dict]],
    funding_rate: Optional[float],
    ls_ratios: Optional[List[float]],
    current_price: Optional[float],
) -> Dict:
    """
    計算清算壓力綜合特徵。

    邏輯：
    1. OI 快速增長 + 高資金費率 = 大量槓桿多頭 → 上方清算壓力大
    2. OI 快速增長 + 負資金費率 = 大量槓桿空頭 → 下方清算壓力大
    3. 多空比極端（>3 或 <0.5）= 單邊擁擠 → 反向清算壓力

    Returns:
        {
            "feat_body_liquidation": float (-1~1),
              正值 = 上方清算壓力大（價格傾向上漲獵殺空頭）
              負值 = 下方清算壓力大（價格傾向下跌獵殺多頭）
            "oi_roc": float,
            "funding_rate_raw": float,
            "ls_ratio": float,
            "pressure_direction": str ("up" / "down" / "neutral")
        }
    """
    result = {
        "feat_body_liquidation": 0.0,
        "oi_roc": None,
        "funding_rate_raw": funding_rate,
        "ls_ratio": None,
        "pressure_direction": "neutral",
    }

    # 1. OI 變化率
    oi_roc = 0.0
    if oi_history and len(oi_history) >= 2:
        prev = oi_history[0]["oi"]
        curr = oi_history[-1]["oi"]
        if prev > 0:
            oi_roc = (curr - prev) / prev
        result["oi_roc"] = oi_roc

    # 2. 多空比
    ls_ratio = None
    if ls_ratios and len(ls_ratios) >= 1:
        ls_ratio = ls_ratios[-1]
        result["ls_ratio"] = ls_ratio

    # 3. 綜合壓力計算
    # 各因子標準化後加權
    components = []

    # 因子 A: 資金費率（正=多頭付費=上方清算壓力）
    if funding_rate is not None:
        # sigmoid 壓縮到 -1~1
        fr_compressed = 2 / (1 + math.exp(-funding_rate * 50000)) - 1
        components.append(("funding", fr_compressed, 0.4))

    # 因子 B: OI 增長率（正增長=槓桿增加=清算風險升高）
    if oi_roc != 0:
        oi_signal = math.tanh(oi_roc * 10)  # tanh 壓縮
        # OI 增長 + 多頭擁擠 → 上方壓力
        # OI 增長 + 空頭擁擠 → 下方壓力
        direction = 1 if (ls_ratio is None or ls_ratio > 1) else -1
        components.append(("oi", oi_signal * direction, 0.3))

    # 因子 C: 多空比偏離（極端值=擁擠=反向清算壓力）
    if ls_ratio is not None:
        # 偏離 1.0 的程度，極端高=多頭擁擠=下跌清算壓力（負值）
        ls_deviation = (ls_ratio - 1.0) / max(ls_ratio, 1.0)
        ls_signal = -math.tanh(ls_deviation * 2)  # 反向：擁擠越高=反向壓力越大
        components.append(("ls_ratio", ls_signal, 0.3))

    # 加權合併
    if components:
        total_weight = sum(w for _, _, w in components)
        weighted_sum = sum(val * w for _, val, w in components)
        pressure = weighted_sum / total_weight if total_weight > 0 else 0
        result["feat_body_liquidation"] = float(pressure)

        if pressure > 0.1:
            result["pressure_direction"] = "up"  # 上方清算多，價格傾向上漲獵殺
        elif pressure < -0.1:
            result["pressure_direction"] = "down"  # 下方清算多，價格傾下跌獵殺

    return result


def get_body_feature(symbol: str = "BTCUSDT") -> Optional[dict]:
    """
    主函數：抓取清算相關數據並返回特徵。
    """
    try:
        oi_hist = fetch_futures_oi(symbol, period="1h", limit=24)
        funding = fetch_funding_rate(symbol)
        ls_ratios = fetch_long_short_ratio(symbol, period="1h", limit=24)
        price = fetch_futures_price(symbol)

        result = calculate_liquidation_pressure(oi_hist, funding, ls_ratios, price)

        logger.info(
            f"Body (清算壓力): feat={result['feat_body_liquidation']:.4f}, "
            f"direction={result['pressure_direction']}, "
            f"OI_ROC={result['oi_roc']}, "
            f"FR={funding}, "
            f"LS={result['ls_ratio']}"
        )

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "raw_roc": result["feat_body_liquidation"],  # 兼容 preprocessor
            "feat_body_trend": result["feat_body_liquidation"],
            "pressure_direction": result["pressure_direction"],
            "oi_roc": result["oi_roc"],
            "funding_rate_raw": result["funding_rate_raw"],
            "ls_ratio": result["ls_ratio"],
        }
    except Exception as e:
        logger.exception(f"計算 Body (清算壓力) 特徵時發生錯誤: {e}")
        return None


if __name__ == "__main__":
    logger.info("開始測試 body_liquidation 模組...")
    result = get_body_feature()
    if result:
        print(f"[SUCCESS] Body (清算) 特徵: {result}")
    else:
        print("[FAIL] 無法獲取 Body 特徵")
