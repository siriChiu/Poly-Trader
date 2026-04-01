"""
感官之「舌」v3：多因子情緒溫度計

組成：
1. FNG 正規化：(FNG - 50) / 50 → -1~1
2. 波動率信號：高波動 = 恐懼（負值），低波動 = 平靜
3. 資金費率方向：正 = 多頭擁擠（偏負面），負 = 空頭擁擠

數據源：Alternative.me + Binance + Binance Futures（全部免費）
"""

import requests
import math
from typing import Optional, List, Dict
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

FNG_URL = "https://api.alternative.me/fng/"
KLINES_URL = "https://api.binance.com/api/v3/klines"
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


def fetch_fng() -> Optional[int]:
    """恐懼貪婪指數 (0~100)"""
    try:
        session = _create_session()
        resp = session.get(FNG_URL, params={"limit": 1, "format": "json"}, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return int(data[0]["value"]) if data else None
    except Exception as e:
        logger.error(f"FNG API 失敗: {e}")
        return None


def fetch_recent_volatility(symbol: str = "BTCUSDT", hours: int = 24) -> Optional[float]:
    """計算最近 N 小時的相對波動率"""
    try:
        session = _create_session()
        params = {"symbol": symbol, "interval": "1h", "limit": hours}
        resp = session.get(KLINES_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data or len(data) < 2:
            return None
        closes = [float(k[4]) for k in data]
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        import numpy as np
        vol = float(np.std(returns))
        return vol
    except Exception as e:
        logger.error(f"Volatility 計算失敗: {e}")
        return None


def fetch_funding_rate(symbol: str = "BTCUSDT") -> Optional[float]:
    """當前資金費率"""
    try:
        session = _create_session()
        resp = session.get(FUNDING_URL, params={"symbol": symbol}, timeout=10)
        resp.raise_for_status()
        return float(resp.json().get("lastFundingRate", 0))
    except Exception as e:
        logger.error(f"Funding Rate 失敗: {e}")
        return None


def compute_tongue_score(fng: Optional[int], volatility: Optional[float], funding: Optional[float]) -> Dict:
    """
    多因子情緒溫度計：
    - FNG 正規化 (-1~1)
    - 波動率信號 (高波動=恐懼=負值)
    - 資金費率方向 (正=擁擠=負面)
    """
    components = []

    # 因子 A: FNG (40% 權重)
    if fng is not None:
        fng_signal = (fng - 50) / 50  # 0~100 → -1~1
        components.append(("fng", fng_signal, 0.4))

    # 因子 B: 波動率 (30% 權重)
    if volatility is not None:
        # 歷史波動率通常 0.01~0.05，標準化
        vol_signal = -math.tanh(volatility * 50)  # 高波動 = 負值 (恐懼)
        components.append(("volatility", vol_signal, 0.3))

    # 因子 C: 資金費率 (30% 權重)
    if funding is not None:
        fr_signal = -math.tanh(funding * 50000)  # 正費率 = 負值 (擁擠)
        components.append(("funding", fr_signal, 0.3))

    if components:
        total_w = sum(w for _, _, w in components)
        score = sum(s * w for _, s, w in components) / total_w
    else:
        score = 0.0

    # 標籤
    if score > 0.3:
        label = "樂觀"
    elif score < -0.3:
        label = "悲觀"
    else:
        label = "中性"

    return {
        "feat_tongue_sentiment": float(score),
        "tongue_label": label,
        "components": {
            "fng": fng,
            "fng_signal": (fng - 50) / 50 if fng else None,
            "volatility": volatility,
            "vol_signal": -math.tanh(volatility * 50) if volatility else None,
            "funding": funding,
            "fr_signal": -math.tanh(funding * 50000) if funding else None,
        },
    }


def get_tongue_feature(symbol: str = "BTCUSDT") -> Optional[dict]:
    """主函數：計算多因子情緒溫度計"""
    try:
        fng = fetch_fng()
        volatility = fetch_recent_volatility(symbol, hours=24)
        funding = fetch_funding_rate(symbol)

        result = compute_tongue_score(fng, volatility, funding)

        logger.info(
            f"Tongue (v3): score={result['feat_tongue_sentiment']:.4f}, "
            f"label={result['tongue_label']}, "
            f"FNG={fng}, vol={volatility}, FR={funding}"
        )

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "fear_greed_index": fng,
            "feat_tongue_fng": fng / 100.0 if fng is not None else None,
            "feat_tongue_sentiment": result["feat_tongue_sentiment"],
            "tongue_label": result["tongue_label"],
            "volatility": volatility,
            "funding_rate": funding,
        }
    except Exception as e:
        logger.exception(f"計算 Tongue (v3) 失敗: {e}")
        return None
