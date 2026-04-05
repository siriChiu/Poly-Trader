#!/usr/bin/env python3
"""
感官之「Web」v1 — 鏈上巨鯨/交易所淨流向

數據源：Binance 大額交易 + 公開鏈上數據 (免費, 無需 API key)
- Binance /api/v3/trades (最近 1000 筆交易)
- 計算大額交易分佈和方向

邏輯：
- 大量 BTC 流入交易所 → 準備出售 → SHORT 信號
- 大量 BTC 流出交易所 → 長期持有 → 不建議 SHORT
- 大戶買賣比 (Whale Buy/Sell Ratio)
"""
import json
import ssl
import math
from datetime import datetime
from typing import Optional, Dict
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_web_feature() -> Optional[Dict]:
    """
    計算巨鯨活動特徵。
    使用 Binance 大額交易作為代理數據。
    
    返回：
    - feat_web_whale_buy_sell: 大戶買賣比 (0~1, >0.5 偏賣壓)
    - feat_web_large_trade_density: 大額交易密度
    """
    try:
        # 獲取最近 1000 筆 Binance 交易
        url = "https://api.binance.com/api/v3/trades?symbol=BTCUSDT&limit=1000"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        trades = json.loads(resp.read().decode())
        
        # 計算大額交易 (>1 BTC)
        large_trades = [t for t in trades if float(t.get("qty", 0)) > 1.0]
        very_large = [t for t in trades if float(t.get("qty", 0)) > 5.0]
        
        # 估計買賣方向 (基於價格變動和成交量)
        # 假設：成交價靠近 ask = 買方主動, 靠近 bid = 賣方主動
        # Binance  trades 有 isBuyerMaker 欄位：True = seller was maker (buy order)
        maker_buys = sum(1 for t in large_trades if t.get("isBuyerMaker", False))
        maker_sells = len(large_trades) - maker_buys
        
        total = maker_buys + maker_sells
        buy_ratio = maker_buys / total if total > 0 else 0.5
        
        # feat_web: 賣方主導 = high score = good for SHORT
        # isBuyerMaker=True means BUYER was maker = passive buying
        # isBuyerMaker=False means BUYER was taker = active buying (bullish)
        # So False = active buying (bullish), True = passive selling (bearish)
        whale_sell_pressure = maker_buys / total if total > 0 else 0.5
        
        # Large trade density
        density = math.tanh(len(large_trades) / 20.0)  # 20+ large trades → 1.0
        very_large_density = math.tanh(len(very_large) / 5.0)
        
        score = (whale_sell_pressure * 0.7 + very_large_density * 0.3)
        
        logger.info(
            f"Web: large_trades={len(large_trades)}, "
            f"very_large={len(very_large)}, "
            f"buy_ratio={buy_ratio:.3f}, "
            f"sell_pressure={whale_sell_pressure:.3f}, "
            f"feat_web={score:.3f}"
        )
        
        return {
            "feat_web_whale_sell_pressure": whale_sell_pressure,
            "feat_web_large_density": density,
            "feat_web_very_large_density": very_large_density,
            "feat_web": score,
            "whale_buy_ratio": buy_ratio,
            "large_trades": len(large_trades),
            "very_large_trades": len(very_large),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
    except Exception as e:
        logger.warning(f"Web 獲取失敗: {e}")
        return None
