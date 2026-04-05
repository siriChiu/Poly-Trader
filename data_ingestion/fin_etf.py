"""
感官之 Fin (魚鰭) — BTC 現貨 ETF 資金流

數據源：CoinGlass ETF flow history endpoint (免費)
- GET /api/bitcoin/etf/flow-history

提取：淨流入/流出、累積流量、ETF AUM 佔比變化
"""
import json
import os
import ssl
import math
from typing import Dict, Optional
from datetime import datetime
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)

COINGLASS_API_KEY = os.environ.get("COINGLASS_API_KEY", "")


def _request(path, params=None):
    url = f"https://open-api.coinglass.com{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url += f"?{qs}"
    headers = {"Content-Type": "application/json"}
    if COINGLASS_API_KEY:
        headers["coinglassSecret"] = COINGLASS_API_KEY
    try:
        req = Request(url, headers=headers)
        resp = urlopen(req, context=ssl.create_default_context(), timeout=12)
        return json.loads(resp.read().decode())
    except Exception:
        return None


def get_fin_feature() -> Optional[Dict]:
    data = _request("/api/bitcoin/etf/flow-history", {"interval": "day", "limit": 30})
    if not data or data.get("code") != 2000 or not data.get("data"):
        logger.warning("ETF flow fetch failed")
        return None

    items = data["data"]["items"] if isinstance(data["data"], dict) else data["data"]

    net_flows = []
    for it in items:
        net = float(it.get("netInflow", 0) or 0)
        net_flows.append(net)

    latest_5d = net_flows[-5:] if len(net_flows) >= 5 else net_flows
    cum_5d = sum(latest_5d)

    # feat_fin: cumulative 5-day net flow, normalized via sigmoid
    # +$1B net inflow in 5d → very bullish → low SHORT signal (score ~0)
    # -$1B net outflow → bearish → high SHORT signal (score ~1)
    fin_score = 1.0 / (1.0 + math.exp(-cum_5d / 500_000_000))  # sigmoid centered at 0, scale=500M

    # Also compute trend: last 2d vs prev 3d
    trend_2d = sum(net_flows[-2:]) if len(net_flows) >= 2 else 0
    trend_3d = sum(net_flows[-5:-2]) if len(net_flows) >= 5 else 0
    trend = (trend_2d - trend_3d) if len(net_flows) >= 5 else 0

    logger.info(f"Fin: cum_5d=${cum_5d/1e9:.2f}B, fin_score={fin_score:.3f}, trend_2d=${trend_2d/1e9:.2f}B, trend_3d=${trend_3d/1e9:.2f}B")

    return {
        "feat_fin_5day_cum": cum_5d,
        "feat_fin_5day_score": fin_score,
        "feat_fin_trend": trend,
    }
