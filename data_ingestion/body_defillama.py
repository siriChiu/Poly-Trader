"""
五感之「身」：鏈上宏觀資金水位模組
來源：DefiLlama API (免費，無需 Key)
"""

import requests
import time
from typing import Optional, Tuple
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

# API 端點
API_URL = "https://stablecoins.llama.fi/stablecoincharts/all"

def _create_session(retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    """建立具有重試機制的 requests.Session"""
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

def fetch_stablecoin_chart(timeout: int = 10) -> Optional[list]:
    """
    抓取全网稳定币市值历史数据。
    Returns:
        数据列表，每个元素包含 date 和 totalCirculatingUSD。
    """
    try:
        session = _create_session()
        resp = session.get(API_URL, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        # 根据实际响应，可能是 {"all": [...]} 或直接为 [...]
        if isinstance(data, dict):
            return data.get("all")
        elif isinstance(data, list):
            return data
        else:
            logger.error(f"Unexpected response type: {type(data)}")
            return None
    except requests.RequestException as e:
        logger.error(f"DefiLlama API 请求失败: {e}")
        return None

def calculate_body_trend(chart_data: list) -> Tuple[float, int]:
    """
    计算最近7天的稳定币总市值变化率 (ROC) 并离散化为 -1/0/1。
    Args:
        chart_data: DefiLlama 返回的 all 数组。
    Returns:
        (raw_roc, discrete_trend)
        - raw_roc: 浮点数变化率（如 0.0123 表示 1.23%）
        - discrete_trend: -1 (资金撤出), 0 (停滞), 1 (流入)
    """
    if not chart_data or len(chart_data) < 8:
        raise ValueError("chart_data 数据不足，至少需要8个点以计算7日变化")

    # 数组按时间排序，最后一个是今天，倒数第8个是7天前
    today = chart_data[-1]
    week_ago = chart_data[-8]

    today_usd = today.get("totalCirculatingUSD", 0.0)
    week_ago_usd = week_ago.get("totalCirculatingUSD", 0.0)

    if week_ago_usd == 0:
        raise ValueError("7天前的市值为0，无法计算ROC")

    raw_roc = (today_usd - week_ago_usd) / week_ago_usd

    # 离散化阈值 0.5%
    threshold = 0.005
    if raw_roc > threshold:
        discrete = 1
    elif raw_roc < -threshold:
        discrete = -1
    else:
        discrete = 0

    return raw_roc, discrete

def get_body_feature() -> Optional[dict]:
    """
    主函数：抓取数据并返回特徵字典。
    返回格式：
        {
            "raw_roc": 0.0123,
            "feat_body_trend": 1
        }
    若失败返回 None。
    """
    try:
        chart = fetch_stablecoin_chart()
        if not chart:
            return None
        raw_roc, discrete = calculate_body_trend(chart)
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "raw_roc": raw_roc,
            "feat_body_trend": discrete
        }
    except Exception as e:
        logger.exception(f"计算 Body 特徵时发生错误: {e}")
        return None

# 單元測試 (若直接執行此文件)
if __name__ == "__main__":
    logger.info("开始测试 body_defillama 模块...")
    result = get_body_feature()
    if result:
        print(f"[SUCCESS] Body 特徵: {result}")
    else:
        print("[FAIL] 无法获取 Body 特徵")
