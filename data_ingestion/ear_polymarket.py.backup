"""
特徵之「耳」v4：市場共識模組 - 改進版

改進：使用資金費率變化和多空比變化的原始值，增加特徵變異數
數據源（全部免費）：
1. 資金費率歷史（Binance Futures API）
2. 多空帳戶比（Binance Futures API）
"""

import requests
import math
from typing import Optional, List
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

FUNDING_HIST_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
LSR_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"

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

def fetch_funding_history(symbol: str = "BTCUSDT", limit: int = 8) -> Optional[List[float]]:
    """最近 N 次資金費率"""
    try:
        session = _create_session()
        resp = session.get(FUNDING_HIST_URL, params={"symbol": symbol, "limit": limit}, timeout=10)
        resp.raise_for_status()
        return [float(d["fundingRate"]) for d in resp.json()]
    except Exception as e:
        logger.error(f"Funding history 失敗: {e}")
        return None

def fetch_lsr_history(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 12) -> Optional[List[float]]:
    """多空帳戶比歷史"""
    try:
        session = _create_session()
        params = {"symbol": symbol, "period": period, "limit": limit}
        resp = session.get(LSR_URL, params=params, timeout=10)
        resp.raise_for_status()
        return [float(d["longShortRatio"]) for d in resp.json() if "longShortRatio" in d]
    except Exception as e:
        logger.error(f"LSR history 失敗: {e}")
        return None

def get_ear_feature(symbol: str = "BTCUSDT") -> Optional[dict]:
    """
    計算市場共識特徵（改進版）。
    使用資金費率變化和多空比變化的原始值。
    返回任意實數特徵值（會由前處理器進行ECDF正規化）。
    """
    try:
        funding_hist = fetch_funding_history(symbol, limit=8)
        lsr_hist = fetch_lsr_history(symbol)

        # 計算資金費率變化（最舊到最新）
        fr_change = 0.0
        if funding_hist and len(funding_hist) >= 2:
            fr_change = funding_hist[-1] - funding_hist[0]

        # 計算多空比變化（最舊到最新）
        lsr_change = 0.0
        if lsr_hist and len(lsr_hist) >= 2:
            lsr_change = lsr_hist[-1] - lsr_hist[0]

        # 組合得分：調整權重以使兩個分量具有相似的幅度
        # 資金費率通常在1e-4量級，所以乘以10000
        # 多空比通常在1附近變化，所以乘以1
        score = fr_change * 10000.0 + lsr_change * 1.0

        logger.info(
            f"Ear v4: fr_change={fr_change:.6f}, lsr_change={lsr_change:.6f}, score={score:.6f}"
        )

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "prob": score,   
            "feat_ear_risk": score
        }
    except Exception as e:
        logger.exception(f"計算 Ear (v4) 時發生錯誤: {e}")
        return None

if __name__ == "__main__":
    logger.info("開始測試 ear_polymarket 模組 v4...")
    result = get_ear_feature()
    if result:
        print(f"[SUCCESS] Ear 特徵: {result}")
    else:
        print("[FAIL] 無法獲取 Ear 特徵")