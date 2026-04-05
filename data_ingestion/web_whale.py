"""
感官之 Web (網) — 鏈上巨鯨/交易所淨流入流出

數據源：Binance 大額交易 + 公開鏈上數據
- Binance /api/v3/trades (免費, K線)
- Whale Alert API (可選)

提取：交易所 BTC 淨流入/流出、大額轉帳頻率
"""
import json
import ssl
import math
from typing import Dict, Optional
from datetime import datetime
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)

# 用 Binance top holder ratio 和 exchange reserve 作為代理數據
# 免費、穩定、無需 API key
BINANCE_LS_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"


def get_web_feature() -> Optional[Dict]:
    """獲取交易所多空比(大帳戶) 和 大戶淨頭寸變化。"""
    # 大戶多空比 (accounts > 2M+ notional)
    try:
        url = "https://fapi.binance.com/futures/data/topLongShortAccountRatio"
        params = "symbol=BTCUSDT&period=4h&limit=24"
        req = Request(f"{url}?{params}", headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())

        ratios = [float(d["topLongShortAccountRatio"]) for d in data if "topLongShortAccountRatio" in d]

        if ratios and len(ratios) >= 2:
            recent = ratios[-1]
            older = ratios[0]
            change = (recent - older) / max(older, 0.01)

            # feat_web: top account LS ratio change
            # rising ratio = more long → bullish (bad for SHORT)
            # falling ratio = reducing long → bearish (good for SHORT)
            web_score = -math.tanh(change * 5)  # negative: more shorts = higher score = bullish for short
            web_score = (web_score + 1) / 2  # normalize to 0-1
        else:
            web_score = 0.5
            recent = 0
            change = 0

        logger.info(f"Web: top_acct_ratio={recent:.3f}, change={change:.3f}, feat_web={web_score:.3f}")

        return {
            "feat_web_top_lsr": recent,
            "feat_web_lsr_change": change,
            "feat_web": web_score,
        }
    except Exception as e:
        logger.warning(f"Web 獲取失敗: {e}")
        return None
