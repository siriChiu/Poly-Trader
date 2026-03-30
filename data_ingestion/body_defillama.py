"""
五感之「身」：鏈上宏觀資金水位模組
來源：DefiLlama API (免費，無需 Key)
"""

import requests
from typing import Optional, Tuple
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

API_URL = "https://stablecoins.llama.fi/stablecoincharts/all"


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


def fetch_stablecoin_chart(timeout: int = 10) -> Optional[list]:
    """抓取全網穩定幣市值歷史數據。"""
    try:
        session = _create_session()
        resp = session.get(API_URL, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            return data.get("all")
        elif isinstance(data, list):
            return data
        else:
            logger.error(f"Unexpected response type: {type(data)}")
            return None
    except requests.RequestException as e:
        logger.error(f"DefiLlama API 請求失敗: {e}")
        return None


def _extract_total_usd(item: dict) -> float:
    """
    從 DefiLlama 圖表數據點提取 totalCirculatingUSD。
    支持兩種格式：
    1. totalCirculatingUSD: float (舊版)
    2. totalCirculatingUSD: dict (新版，按幣種拆分)
       → 需加總所有 peggedUSD 值
    """
    val = item.get("totalCirculatingUSD")
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        # 新版：按 peggedUSD 加總
        total = 0.0
        for v in val.values():
            if isinstance(v, (int, float)):
                total += float(v)
        return total
    return 0.0


def calculate_body_trend(chart_data: list) -> Tuple[float, int]:
    """計算最近7天的穩定幣總市值變化率 (ROC) 並離散化為 -1/0/1。"""
    if not chart_data or len(chart_data) < 8:
        raise ValueError("chart_data 數據不足，至少需要8個點")

    today_usd = _extract_total_usd(chart_data[-1])
    week_ago_usd = _extract_total_usd(chart_data[-8])

    if week_ago_usd == 0:
        logger.warning("Week ago USD is zero, using fallback")
        return 0.0, 0

    raw_roc = (today_usd - week_ago_usd) / week_ago_usd

    threshold = 0.005
    if raw_roc > threshold:
        discrete = 1
    elif raw_roc < -threshold:
        discrete = -1
    else:
        discrete = 0

    return raw_roc, discrete


def get_body_feature() -> Optional[dict]:
    """主函數：抓取數據並返回特徵字典。"""
    try:
        chart = fetch_stablecoin_chart()
        if not chart:
            return None
        raw_roc, discrete = calculate_body_trend(chart)
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "raw_roc": raw_roc,
            "feat_body_trend": discrete,
        }
    except Exception as e:
        logger.exception(f"計算 Body 特徵時發生錯誤: {e}")
        return None
