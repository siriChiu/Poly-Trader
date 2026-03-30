"""
五感之「鼻」：衍生品氣味與資金成本模組
- Binance Futures API: Funding Rate 與 Open Interest
"""

import requests
import math
from typing import Optional, List
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Endpoints
FUNDING_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
OI_HIST_URL = "https://fapi.binance.com/futures/data/openInterestHist"

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

def fetch_funding_rate(symbol: str = "BTCUSDT") -> Optional[float]:
    """
    获取指定交易对的资金费率。
    Returns:
        funding_rate (float)，例如 0.0001 表示 0.01%。
    """
    try:
        session = _create_session()
        resp = session.get(FUNDING_URL, params={"symbol": symbol}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rate = float(data.get("lastFundingRate", 0.0))
        return rate
    except Exception as e:
        logger.error(f"Funding Rate API 请求失败: {e}")
        return None

def fetch_oi_history(symbol: str = "BTCUSDT", period: str = "1d", limit: int = 3) -> Optional[List[dict]]:
    """
    获取未平仓量历史数据 (默认3个点，以计算24小时变化)。
    Returns:
        列表，按时间升序排列，元素包含 {timestamp, openInterest}。
    """
    try:
        session = _create_session()
        params = {"symbol": symbol, "period": period, "limit": limit}
        resp = session.get(OI_HIST_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # 转换数据结构
        oi_list = []
        for item in data:
            oi_list.append({
                "timestamp": datetime.fromtimestamp(item["timestamp"] / 1000),
                "openInterest": float(item["sumOpenInterest"])
            })
        # 按时间排序
        oi_list.sort(key=lambda x: x["timestamp"])
        return oi_list
    except Exception as e:
        logger.error(f"OI History API 请求失败: {e}")
        return None

def sigmoid(x: float) -> float:
    """Sigmoid 函数，将任意实数映射到 (0,1)"""
    return 1 / (1 + math.exp(-x))

def compress_funding_sigmoid(funding_rate: float) -> float:
    """
    将 Funding Rate 通过 Sigmoid 压缩到 -1~1 区间。
    文档：Feat_Nose_Funding = 2 * (1/(1+e^(-x))) - 1，其中 x = funding_rate * 10000
    """
    x = funding_rate * 10000
    s = sigmoid(x)
    return 2 * s - 1

def calculate_oi_roc(oi_history: List[dict]) -> Optional[float]:
    """
    计算未平仓量增长率 (ROC)。默认对比最近两个点（24小时）。
    返回百分比变化 (例如 0.05 表示 5%)。
    """
    if len(oi_history) < 2:
        return None
    prev = oi_history[-2]["openInterest"]
    curr = oi_history[-1]["openInterest"]
    if prev == 0:
        return None
    return (curr - prev) / prev

def get_nose_feature(symbol: str = "BTCUSDT") -> Optional[dict]:
    """
    主函数：整合鼻部两个特征。
    返回：
        {
            "funding_rate_raw": float,
            "feat_nose_funding_sigmoid": float (-1~1),
            "oi_roc": float (百分比),
            "timestamp": str
        }
    """
    try:
        # 1. Funding Rate
        fr = fetch_funding_rate(symbol)
        if fr is None:
            logger.warning("无法获取 Funding Rate")
            return None

        feat_funding = compress_funding_sigmoid(fr)

        # 2. OI 历史与 ROC
        oi_hist = fetch_oi_history(symbol)
        if not oi_hist or len(oi_hist) < 2:
            logger.warning("OI 历史数据不足")
            oi_roc = None
        else:
            oi_roc = calculate_oi_roc(oi_hist)

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "funding_rate_raw": fr,
            "feat_nose_funding_sigmoid": feat_funding,
            "oi_roc": oi_roc
        }
    except Exception as e:
        logger.exception(f"计算 Nose 特征时发生错误: {e}")
        return None

if __name__ == "__main__":
    logger.info("开始测试 nose_futures 模块...")
    result = get_nose_feature()
    if result:
        print(f"[SUCCESS] Nose 特徵: {result}")
    else:
        print("[FAIL] 无法获取 Nose 特徵")
