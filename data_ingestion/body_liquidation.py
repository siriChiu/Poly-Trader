"""
特徵之「身」v4：槓桿熱度模組（OI 變化率）

類比：身體的血液循環 = 市場的槓桿熱度
- OI 增加 = 新資金進場（血液加速）
- OI 減少 = 資金撤出（血液減緩）
- OI 變化率 = 血液流速變化

數據源：Binance Futures OI History（免費、每小時更新）
"""

import requests
import math
from typing import Optional, List, Dict
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

OI_HIST_URL = "https://fapi.binance.com/futures/data/openInterestHist"
FUNDING_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"


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


def fetch_oi_history(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 24) -> Optional[List[float]]:
    """獲取 OI 歷史（最近 N 小時）"""
    try:
        session = _create_session()
        params = {"symbol": symbol, "period": period, "limit": limit}
        resp = session.get(OI_HIST_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [float(d["sumOpenInterest"]) for d in data if "sumOpenInterest" in d]
    except Exception as e:
        logger.error(f"OI History 失敗: {e}")
        return None


def fetch_funding_rate(symbol: str = "BTCUSDT") -> Optional[float]:
    try:
        session = _create_session()
        resp = session.get(FUNDING_URL, params={"symbol": symbol}, timeout=10)
        resp.raise_for_status()
        return float(resp.json().get("lastFundingRate", 0))
    except Exception as e:
        logger.error(f"Funding Rate 失敗: {e}")
        return None


def compute_body_score(oi_history: Optional[List[float]], funding: Optional[float]) -> Dict:
    """
    計算槓桿熱度分數 (-1~1)

    邏輯：
    - OI 上升 + 正資金費率 = 多頭槓桿進場 → 正值（偏多）
    - OI 上升 + 負資金費率 = 空頭槓桿進場 → 負值（偏空）
    - OI 下降 = 槓桿清算 → 接近 0（觀望）
    """
    components = []

    # 因子 A: OI 變化率 (60%)
    if oi_history and len(oi_history) >= 2:
        first = oi_history[0]
        last = oi_history[-1]
        if first > 0:
            oi_roc = (last - first) / first
            oi_signal = math.tanh(oi_roc * 20)  # 放大後壓縮
            components.append(("oi_roc", oi_signal, 0.6))

    # 因子 B: 資金費率方向 (40%)
    if funding is not None:
        fr_signal = math.tanh(funding * 50000)
        components.append(("funding", fr_signal, 0.4))

    if components:
        total_w = sum(w for _, _, w in components)
        score = sum(s * w for _, s, w in components) / total_w
    else:
        score = 0.0

    if score > 0.2:
        label = "槓桿偏多"
    elif score < -0.2:
        label = "槓桿偏空"
    else:
        label = "槓桿平穩"

    return {
        "feat_body_leverage": float(score),
        "body_label": label,
        "oi_roc": (oi_history[-1] - oi_history[0]) / oi_history[0] if oi_history and len(oi_history) >= 2 and oi_history[0] > 0 else None,
        "funding": funding,
    }


def get_body_feature(symbol: str = "BTCUSDT") -> Optional[dict]:
    """主函數：計算槓桿熱度"""
    try:
        oi_hist = fetch_oi_history(symbol, period="1h", limit=24)
        funding = fetch_funding_rate(symbol)

        result = compute_body_score(oi_hist, funding)

        logger.info(
            f"Body (v4): score={result['feat_body_leverage']:.4f}, "
            f"label={result['body_label']}, "
            f"OI_ROC={result['oi_roc']}, FR={funding}"
        )

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "raw_roc": result["feat_body_leverage"],
            "feat_body_trend": result["feat_body_leverage"],
            "body_label": result["body_label"],
            "oi_roc": result["oi_roc"],
            "funding_rate": funding,
        }
    except Exception as e:
        logger.exception(f"計算 Body (v4) 失敗: {e}")
        return None
