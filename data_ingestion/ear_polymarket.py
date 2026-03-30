"""
五感之「耳」v3：市場共識模組

舊版問題：Polymarket 免費 API 返回的事件概率全是近零值（~5.7e-08），資訊無效
新版方案：用 Binance Futures 的資金費率方向 + 多空比變化作為市場共識代理

邏輯：
- 資金費率為正且上升 → 多頭佔優 → 共識偏多
- 資金費率為負且下降 → 空頭佔優 → 共識偏空
- 多空比變化趨勢 → 共識方向的確認
"""

import requests
import math
from typing import Optional, List
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

FUNDING_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
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
    """獲取最近 N 次資金費率（每 8 小時一次）。"""
    try:
        session = _create_session()
        resp = session.get(FUNDING_HIST_URL, params={"symbol": symbol, "limit": limit}, timeout=10)
        resp.raise_for_status()
        return [float(d["fundingRate"]) for d in resp.json()]
    except Exception as e:
        logger.error(f"Funding history 失敗: {e}")
        return None


def fetch_lsr_history(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 12) -> Optional[List[float]]:
    """獲取多空帳戶比歷史。"""
    try:
        session = _create_session()
        params = {"symbol": symbol, "period": period, "limit": limit}
        resp = session.get(LSR_URL, params=params, timeout=10)
        resp.raise_for_status()
        return [float(d["longShortRatio"]) for d in resp.json() if "longShortRatio" in d]
    except Exception as e:
        logger.error(f"LSR history 失敗: {e}")
        return None


def compute_consensus_score(
    funding_history: Optional[List[float]],
    lsr_history: Optional[List[float]],
) -> dict:
    """
    計算市場共識分數 (-1~1)。

    正值 = 共識偏多（資金費率為正 + 多空比上升）
    負值 = 共識偏空
    """
    components = []

    # 因子 A: 資金費率趨勢（最近 8 次的變化方向）
    if funding_history and len(funding_history) >= 2:
        recent = funding_history[-1]
        older = funding_history[0]
        # 資金費率方向 + 變化
        fr_direction = math.tanh(recent * 100000)  # 當前方向
        fr_trend = math.tanh((recent - older) * 200000)  # 變化趨勢
        components.append(("fr_direction", fr_direction, 0.3))
        components.append(("fr_trend", fr_trend, 0.2))

    # 因子 B: 多空比趨勢
    if lsr_history and len(lsr_history) >= 2:
        recent_lsr = lsr_history[-1]
        older_lsr = lsr_history[0]
        lsr_change = (recent_lsr - older_lsr) / max(older_lsr, 0.01)
        lsr_signal = math.tanh(lsr_change * 5)
        # 多空比上升 = 多頭增加 = 可能過熱（反向信號的一部分）
        components.append(("lsr_trend", -lsr_signal, 0.3))  # 反向

    # 因子 C: 資金費率絕對值（正=多頭付費=偏多）
    if funding_history and len(funding_history) >= 1:
        current_fr = funding_history[-1]
        fr_abs = math.tanh(current_fr * 50000)
        components.append(("fr_abs", fr_abs, 0.2))

    # 加權合併
    if components:
        total_w = sum(w for _, _, w in components)
        score = sum(s * w for _, s, w in components) / total_w
    else:
        score = 0.0

    # 共識標籤
    if score > 0.2:
        label = "偏多"
    elif score < -0.2:
        label = "偏空"
    else:
        label = "中性"

    return {
        "feat_ear_consensus": float(score),
        "consensus_label": label,
        "current_funding": funding_history[-1] if funding_history else None,
        "current_lsr": lsr_history[-1] if lsr_history else None,
    }


def get_ear_feature(symbol: str = "BTCUSDT") -> Optional[dict]:
    """主函數：計算市場共識特徵。"""
    try:
        funding_hist = fetch_funding_history(symbol, limit=8)
        lsr_hist = fetch_lsr_history(symbol, limit=12)

        result = compute_consensus_score(funding_hist, lsr_hist)

        logger.info(
            f"Ear (共識v3): score={result['feat_ear_consensus']:.4f}, "
            f"label={result['consensus_label']}, "
            f"FR={result['current_funding']}, "
            f"LSR={result['current_lsr']}"
        )

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "prob": result["feat_ear_consensus"],  # 兼容 collector
            "feat_ear_risk": result["feat_ear_consensus"],
            "consensus_label": result["consensus_label"],
        }
    except Exception as e:
        logger.exception(f"計算 Ear (共識v3) 特徵時發生錯誤: {e}")
        return None
