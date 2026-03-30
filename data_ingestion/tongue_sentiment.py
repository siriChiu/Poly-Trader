"""
五感之「舌」：社群情緒與多空對比模組
- Alternative.me 恐惧贪婪指數
- Binance 多空账户比率 (Long/Short Ratio)
"""

import requests
import statistics
from typing import Optional, List, Dict
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

# API endpoints
FNG_URL = "https://api.alternative.me/fng/"
LSR_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"

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

def fetch_fear_greed_index(limit: int = 2) -> Optional[int]:
    """
    获取 Alternative.me 恐惧贪婪指数（Latest）。
    Returns:
        整数 0~100，失败返回 None。
    """
    try:
        session = _create_session()
        resp = session.get(FNG_URL, params={"limit": limit}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("data") and len(data["data"]) > 0:
            value = int(data["data"][0]["value"])
            return value
    except Exception as e:
        logger.error(f"FNG API 请求失败: {e}")
    return None

def fetch_long_short_ratio(symbol: str = "BTCUSDT", period: str = "1d", limit: int = 30) -> Optional[List[float]]:
    """
    获取 Binance 多空账户比率 (Long/Short Ratio)。
    Returns:
        按时间顺序排列的 ratio 列表（从旧到新），失败返回 None。
    """
    try:
        session = _create_session()
        params = {"symbol": symbol, "period": period, "limit": limit}
        resp = session.get(LSR_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        ratios = [float(item["longShortRatio"]) for item in data if "longShortRatio" in item]
        return ratios
    except Exception as e:
        logger.error(f"Binance LSR API 请求失败: {e}")
    return None

def calculate_tongue_features(fng_value: Optional[int], ls_ratios: Optional[List[float]]) -> Optional[dict]:
    """
    计算舌部两个特征：
    - Feat_Tongue_FNG: 恐惧贪婪指数标准化到 0~1
    - Feat_Tongue_LSR: 多空比 Z-score (当前与历史对比)
    若某个来源失败，该特征置为 None。
    """
    features = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "fear_greed_index": fng_value,
        "feat_tongue_fng": None,
        "long_short_ratio": None,
        "feat_tongue_lsr": None
    }

    # FNG 标准化
    if fng_value is not None:
        features["feat_tongue_fng"] = fng_value / 100.0

    # 多空比 Z-score
    if ls_ratios and len(ls_ratios) >= 2:
        current_ratio = ls_ratios[-1]
        mean = statistics.mean(ls_ratios)
        stdev = statistics.stdev(ls_ratios) if len(ls_ratios) > 1 else 0.0
        features["long_short_ratio"] = current_ratio
        if stdev > 0:
            features["feat_tongue_lsr"] = (current_ratio - mean) / stdev
        else:
            features["feat_tongue_lsr"] = 0.0  # 所有值相同，无偏离

    return features

def get_tongue_feature() -> Optional[dict]:
    """
    主函数：合并两个数据源的特征。
    """
    try:
        fng = fetch_fear_greed_index()
        ls_ratios = fetch_long_short_ratio()
        features = calculate_tongue_features(fng, ls_ratios)
        # 如果两个主要特征都为 None，则返回失败
        if features["feat_tongue_fng"] is None and features["feat_tongue_lsr"] is None:
            logger.warning("舌部特征获取失败：所有数据源无效")
            return None
        return features
    except Exception as e:
        logger.exception(f"计算 Tongue 特征时发生错误: {e}")
        return None

if __name__ == "__main__":
    logger.info("开始测试 tongue_sentiment 模块...")
    result = get_tongue_feature()
    if result:
        print(f"[SUCCESS] Tongue 特徵: {result}")
    else:
        print("[FAIL] 无法获取 Tongue 特徵")
