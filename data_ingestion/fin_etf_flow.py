#!/usr/bin/env python3
"""
感官之「Fin (Fins)」v1 — ETF 資金流向模組

數據源：CoinGlass ETF Flow API (免費)
- /api/bitcoin/etf/flow-history

邏輯：
- ETF 淨流入 > 0 → 機構買入 → 看漲
- ETF 淨流出 > 0 → 機構撤出 → 看跌 (SHORT 信號)
- 連續淨流出 = 結構性賣壓

環境變數: COINGLASS_API_KEY (可選，但有 key 更穩定)
"""
import json
import os
import ssl
from datetime import datetime
from typing import Optional, Dict
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)

COINGLASS_API_KEY = os.environ.get("COINGLASS_API_KEY", "")
ETF_URL = "https://open-api.coinglass.com/api/bitcoin/etf/flow-history"


def fetch_etf_flows(days: int = 7) -> Optional[list]:
    """獲取最近 N 天 ETF 流量。"""
    try:
        headers = {}
        if COINGLASS_API_KEY:
            headers["X-CG-API-KEY"] = COINGLASS_API_KEY
        req = Request(ETF_URL, headers=headers)
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        data = json.loads(resp.read().decode())
        if data and data.get("success") and data.get("data"):
            return data["data"][-days:] if len(data["data"]) > days else data["data"]
    except Exception as e:
        logger.debug(f"ETF flow fetch failed: {e}")
    return None


def get_fin_feature() -> Optional[Dict]:
    """
    計算 ETF 流向特徵。
    
    返回：
    - feat_etf_netflow: 淨流量 (正規化)
    - raw_flow_in: 總流入
    - raw_flow_out: 總流出
    - netflow_trend: 趋势 (正=流入加速, 負=流出加速)
    """
    flows = fetch_etf_flows(7)
    if not flows:
        return {
            "feat_etf_netflow": 0.0,
            "raw_flow_in": 0,
            "raw_flow_out": 0,
            "netflow_trend": 0.0,
        }
    
    total_in = sum(float(f.get("inflow", 0) or 0) for f in flows)
    total_out = sum(float(f.get("outflow", 0) or 0) for f in flows)
    net_flow = total_in - total_out
    
    # 趨勢：最近 2 天 vs 之前 5 天
    recent_net = sum(
        (float(f.get("inflow", 0) or 0) - float(f.get("outflow", 0) or 0))
        for f in flows[-2:]
    )
    older_net = sum(
        (float(f.get("inflow", 0) or 0) - float(f.get("outflow", 0) or 0))
        for f in flows[:-2]
    )
    trend = recent_net - older_net  # 正值 = 流入加速，負值 = 流出加速
    
    # 正規化
    import math
    norm = math.tanh(net_flow / 500_000_000)  # ±500M → ±1
    norm_trend = math.tanh(trend / 200_000_000)  # ±200M → ±1
    
    logger.info(
        f"Fin (ETF): inflow=${total_in:,.0f}, outflow=${total_out:,.0f}, "
        f"net=${net_flow:,.0f} ({norm:+.3f}), trend={norm_trend:+.3f}"
    )
    
    return {
        "feat_etf_netflow": float(norm),
        "feat_etf_trend": float(norm_trend),
        "raw_flow_in": total_in,
        "raw_flow_out": total_out,
        "netflow_trend": trend,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
