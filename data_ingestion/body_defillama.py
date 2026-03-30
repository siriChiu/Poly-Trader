"""
五感之「身」：鏈上宏觀資金水位模組 (v2 - TVL 版本)

數據源：DefiLlama TVL (免費，無需 Key)
特徵：DeFi 總鎖倉量 (TVL) 7 日變化率，離散化為 -1/0/1
      或連續 ROC 值（供後續模型使用）
"""

import requests
from typing import Optional, Tuple
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

# TVL 歷史 API
TVL_URL = "https://api.llama.fi/v2/historicalChainTvl"
# 舊 API（穩定幣，保留備用）
STABLECOIN_URL = "https://stablecoins.llama.fi/stablecoincharts/all"


def _create_session(retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
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


def fetch_tvl_history(timeout: int = 15) -> Optional[list]:
    """
    抓取全網 DeFi TVL 歷史數據。
    Returns: list of {date: timestamp, tvl: float}
    """
    try:
        session = _create_session()
        resp = session.get(TVL_URL, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        logger.error(f"Unexpected TVL response type: {type(data)}")
        return None
    except requests.RequestException as e:
        logger.error(f"DefiLlama TVL API 請求失敗: {e}")
        return None


def calculate_tvl_roc(tvl_data: list, lookback_days: int = 7) -> Tuple[float, int]:
    """
    計算 TVL 的 N 日變化率 (ROC) 並離散化為 -1/0/1。

    Args:
        tvl_data: DefiLlama TVL 歷史列表，按時間升序
        lookback_days: 回看天數（預設 7 天）

    Returns:
        (raw_roc, discrete)
        - raw_roc: 浮點數變化率（如 0.05 表示 5%）
        - discrete: -1 (資金撤出), 0 (持平), 1 (流入)
    """
    if not tvl_data or len(tvl_data) < lookback_days + 1:
        logger.warning(f"TVL 數據不足 ({len(tvl_data) if tvl_data else 0} 筆)")
        return 0.0, 0

    current = tvl_data[-1]
    past = tvl_data[-(lookback_days + 1)]

    current_tvl = current.get("tvl", 0)
    past_tvl = past.get("tvl", 0)

    if past_tvl <= 0:
        return 0.0, 0

    raw_roc = (current_tvl - past_tvl) / past_tvl

    # 離散化閾值：±2%（TVL 波動比穩定幣大得多）
    threshold = 0.02
    if raw_roc > threshold:
        discrete = 1
    elif raw_roc < -threshold:
        discrete = -1
    else:
        discrete = 0

    return raw_roc, discrete


def get_body_feature() -> Optional[dict]:
    """
    主函數：抓取 TVL 數據並返回特徵字典。
    Returns:
        {
            "timestamp": str,
            "raw_roc": float,
            "feat_body_trend": int (-1/0/1),
            "current_tvl": float (USD)
        }
    """
    try:
        tvl_data = fetch_tvl_history()
        if not tvl_data:
            logger.warning("TVL 數據為空，嘗試穩定幣 API")
            return None

        raw_roc, discrete = calculate_tvl_roc(tvl_data, lookback_days=7)
        current_tvl = tvl_data[-1].get("tvl", 0)

        logger.info(f"Body (TVL): roc={raw_roc:.4f}, trend={discrete}, tvl=${current_tvl/1e9:.1f}B")

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "raw_roc": raw_roc,
            "feat_body_trend": discrete,
            "current_tvl": current_tvl,
        }
    except Exception as e:
        logger.exception(f"計算 Body (TVL) 特徵時發生錯誤: {e}")
        return None


if __name__ == "__main__":
    logger.info("開始測試 body_defillama (TVL) 模組...")
    result = get_body_feature()
    if result:
        print(f"[SUCCESS] Body 特徵: {result}")
    else:
        print("[FAIL] 無法獲取 Body 特徵")
