"""
五感之「舌」v2：多維度市場情緒模組

舊版問題：FNG 更新慢、卡在極端值無變異 → IC=0
新版方案：多指標即時情緒綜合分數

數據源（全部免費 via Binance Futures API）：
1. 多空帳戶比 (Long/Short Account Ratio)
2. 主動買賣比 (Taker Buy/Sell Ratio)
3. 大戶持倉比 (Top Trader Position Ratio)

綜合情緒分數：-1（極度悲觀）到 +1（極度樂觀）
"""

import requests
import math
from typing import Optional, List, Dict
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Binance Futures 免費端點
LSR_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
TAKER_URL = "https://fapi.binance.com/futures/data/takerlongshortRatio"
TOP_TRADER_URL = "https://fapi.binance.com/futures/data/topLongShortPositionRatio"
FNG_URL = "https://api.alternative.me/fng/"


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


def fetch_ratio(url: str, symbol: str = "BTCUSDT", period: str = "1h", limit: int = 24) -> Optional[List[float]]:
    """通用：獲取 Binance Futures 比率類數據"""
    try:
        session = _create_session()
        params = {"symbol": symbol, "period": period, "limit": limit}
        resp = session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        key = "longShortRatio" if "longShort" in url else "takerBuySellRatio" if "taker" in url else "topTraderLongShortRatio"
        return [float(d[key]) for d in resp.json() if key in d]
    except Exception as e:
        logger.error(f"Ratio API 失敗 ({url}): {e}")
        return None


def fetch_fng() -> Optional[int]:
    """獲取 Fear & Greed Index（備用）"""
    try:
        session = _create_session()
        resp = session.get(FNG_URL, params={"limit": 1, "format": "json"}, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return int(data[0]["value"]) if data else None
    except Exception as e:
        logger.error(f"FNG API 失敗: {e}")
        return None


def ratio_to_signal(ratios: Optional[List[float]], invert: bool = False) -> Optional[float]:
    """
    將比率序列轉換為標準化信號 (-1~1)。
    使用 Z-score + tanh 壓縮。
    invert=True 表示該比率越高代表越悲觀（如 Taker Buy/Sell）。
    """
    if not ratios or len(ratios) < 2:
        return None
    import numpy as np
    arr = np.array(ratios)
    current = arr[-1]
    mean = arr.mean()
    std = arr.std()
    if std == 0:
        return 0.0
    z = (current - mean) / std
    signal = math.tanh(z)  # 壓縮到 -1~1
    return float(-signal) if invert else float(signal)


def compute_sentiment_score(
    lsr: Optional[List[float]],
    taker: Optional[List[float]],
    top_trader: Optional[List[float]],
    fng: Optional[int],
) -> Dict:
    """
    計算多維度情緒綜合分數。

    各因子：
    - LSR (多空帳戶比): 比值越高 → 散戶越看多 → 反轉指標（invert）
    - Taker (主買賣比): 比值越高 → 買壓越大 → 正向
    - Top Trader (大戶持倉比): 比值越高 → 大戶看多 → 正向
    - FNG: 備用，權重較低

    Returns:
        {
            "feat_tongue_sentiment": float (-1~1),
            "components": {...},
            "sentiment_label": str
        }
    """
    components = []
    raw_values = {}

    # 因子 A: 多空帳戶比（散戶情緒，反向指標）
    lsr_signal = ratio_to_signal(lsr, invert=True)  # 散戶多=反轉
    if lsr_signal is not None:
        components.append(("lsr", lsr_signal, 0.35))
        raw_values["lsr_current"] = lsr[-1] if lsr else None

    # 因子 B: 主動買賣比（真實買壓，正向）
    taker_signal = ratio_to_signal(taker, invert=False)
    if taker_signal is not None:
        components.append(("taker", taker_signal, 0.35))
        raw_values["taker_current"] = taker[-1] if taker else None

    # 因子 C: 大戶持倉比（smart money，正向）
    top_signal = ratio_to_signal(top_trader, invert=False)
    if top_signal is not None:
        components.append(("top_trader", top_signal, 0.20))
        raw_values["top_trader_current"] = top_trader[-1] if top_trader else None

    # 因子 D: FNG（低頻備用）
    if fng is not None:
        fng_signal = (fng - 50) / 50  # 0~100 → -1~1
        components.append(("fng", fng_signal, 0.10))
        raw_values["fng"] = fng

    # 加權合併
    if components:
        total_weight = sum(w for _, _, w in components)
        score = sum(sig * w for _, sig, w in components) / total_weight
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
        "components": raw_values,
        "sentiment_label": label,
    }


def get_tongue_feature(symbol: str = "BTCUSDT") -> Optional[dict]:
    """主函數：抓取多維度情緒數據並返回特徵。"""
    try:
        lsr = fetch_ratio(LSR_URL, symbol)
        taker = fetch_ratio(TAKER_URL, symbol)
        top_trader = fetch_ratio(TOP_TRADER_URL, symbol)
        fng = fetch_fng()

        result = compute_sentiment_score(lsr, taker, top_trader, fng)

        logger.info(
            f"Tongue (情緒v2): score={result['feat_tongue_sentiment']:.4f}, "
            f"label={result['sentiment_label']}, "
            f"LSR={result['components'].get('lsr_current')}, "
            f"Taker={result['components'].get('taker_current')}, "
            f"FNG={result['components'].get('fng')}"
        )

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "fear_greed_index": fng,
            "feat_tongue_fng": fng / 100.0 if fng is not None else None,
            "feat_tongue_sentiment": result["feat_tongue_sentiment"],
            "long_short_ratio": result["components"].get("lsr_current"),
            "taker_ratio": result["components"].get("taker_current"),
            "top_trader_ratio": result["components"].get("top_trader_current"),
            "sentiment_label": result["sentiment_label"],
        }
    except Exception as e:
        logger.exception(f"計算 Tongue (情緒v2) 特徵時發生錯誤: {e}")
        return None


if __name__ == "__main__":
    logger.info("開始測試 tongue_sentiment (v2) 模組...")
    result = get_tongue_feature()
    if result:
        print(f"[SUCCESS] Tongue 特徵: {result}")
    else:
        print("[FAIL] 無法獲取 Tongue 特徵")
