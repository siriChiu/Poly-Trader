"""
特徵之「耳」v3：市場共識模組

舊版問題：Polymarket 免費 API 返回 ~5.7e-8 概率，無任何資訊量
新版方案：Binance Futures 資金費率 + 多空比綜合共識

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
    計算市場共識特徵。
    返回 prob (0~1), feat_ear_risk (0~1)
    """
    try:
        funding_hist = fetch_funding_history(symbol, limit=8)
        lsr_hist = fetch_lsr_history(symbol)

        components = []

        # 因子 A: 資金費率趨勢
        if funding_hist and len(funding_hist) >= 2:
            recent = funding_hist[-1]
            older = funding_hist[0]
            fr_direction = math.tanh(recent * 100000)
            fr_trend = math.tanh((recent - older) * 200000)
            components.append(("fr_dir", fr_direction, 0.3))
            components.append(("fr_trend", fr_trend, 0.2))

        # 因子 B: 多空比變化
        if lsr_hist and len(lsr_hist) >= 2:
            recent_lsr = lsr_hist[-1]
            older_lsr = lsr_hist[0]
            lsr_change = (recent_lsr - older_lsr) / max(older_lsr, 0.01)
            lsr_signal = -math.tanh(lsr_change * 5)  # 反向
            components.append(("lsr", lsr_signal, 0.3))

        # 因子 C: 資金費率絕對值
        if funding_hist:
            current_fr = funding_hist[-1]
            fr_abs = math.tanh(current_fr * 50000)
            components.append(("fr_abs", fr_abs, 0.2))

        if components:
            total_w = sum(w for _, _, w in components)
            score = sum(s * w for _, s, w in components) / total_w
        else:
            score = 0.0

        # 正規化到 0~1
        prob = (score + 1) / 2

        logger.info(
            f"Ear: score={score:.4f}, prob={prob:.4f}, "
            f"FR={funding_hist[-1] if funding_hist else None}, "
            f"LSR={lsr_hist[-1] if lsr_hist else None}"
        )

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "prob": prob,
            "feat_ear_risk": prob,
        }
    except Exception as e:
        logger.exception(f"計算 Ear (v3) 時發生錯誤: {e}")
        return None
