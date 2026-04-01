"""
Binance 衍生品數據收集器
提供獨立於 K線和 Funding Rate 的新信號：
- 大戶持倉比 (LSR)
- 多空人數比 (GSR)
- 主動買賣比 (Taker)
- OI 歷史
"""

import requests
import pandas as pd
import numpy as np
from typing import Optional, Dict
from utils.logger import setup_logger

logger = setup_logger(__name__)
BASE_URL = "https://fapi.binance.com"


def fetch_lsr(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 500) -> Optional[pd.DataFrame]:
    """大戶持倉比 (Top Trader Long/Short Ratio)"""
    try:
        r = requests.get(f"{BASE_URL}/futures/data/topLongShortPositionRatio",
                        params={"symbol": symbol, "period": period, "limit": limit}, timeout=15)
        data = r.json()
        if not data:
            return None
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
        df['longShortRatio'] = df['longShortRatio'].astype(float)
        df['longAccount'] = df['longAccount'].astype(float)
        return df[['timestamp', 'longShortRatio', 'longAccount']].sort_values('timestamp')
    except Exception as e:
        logger.error(f"LSR fetch failed: {e}")
        return None


def fetch_gsr(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 500) -> Optional[pd.DataFrame]:
    """多空人數比 (Global Long/Short Account Ratio)"""
    try:
        r = requests.get(f"{BASE_URL}/futures/data/globalLongShortAccountRatio",
                        params={"symbol": symbol, "period": period, "limit": limit}, timeout=15)
        data = r.json()
        if not data:
            return None
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
        df['longShortRatio'] = df['longShortRatio'].astype(float)
        return df[['timestamp', 'longShortRatio']].sort_values('timestamp')
    except Exception as e:
        logger.error(f"GSR fetch failed: {e}")
        return None


def fetch_taker(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 500) -> Optional[pd.DataFrame]:
    """主動買賣比 (Taker Buy/Sell Ratio)"""
    try:
        r = requests.get(f"{BASE_URL}/futures/data/takerlongshortRatio",
                        params={"symbol": symbol, "period": period, "limit": limit}, timeout=15)
        data = r.json()
        if not data:
            return None
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
        df['buySellRatio'] = df['buySellRatio'].astype(float)
        return df[['timestamp', 'buySellRatio']].sort_values('timestamp')
    except Exception as e:
        logger.error(f"Taker fetch failed: {e}")
        return None


def fetch_oi_hist(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 500) -> Optional[pd.DataFrame]:
    """持倉量歷史 (Open Interest History)"""
    try:
        r = requests.get(f"{BASE_URL}/futures/data/openInterestHist",
                        params={"symbol": symbol, "period": period, "limit": limit}, timeout=15)
        data = r.json()
        if not data:
            return None
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
        df['sumOpenInterest'] = df['sumOpenInterest'].astype(float)
        df['sumOpenInterestValue'] = df['sumOpenInterestValue'].astype(float)
        return df[['timestamp', 'sumOpenInterest', 'sumOpenInterestValue']].sort_values('timestamp')
    except Exception as e:
        logger.error(f"OI hist fetch failed: {e}")
        return None


def fetch_oi_current(symbol: str = "BTCUSDT") -> Optional[float]:
    """當前 OI"""
    try:
        r = requests.get(f"{BASE_URL}/fapi/v1/openInterest",
                        params={"symbol": symbol}, timeout=10)
        data = r.json()
        return float(data['openInterest'])
    except Exception as e:
        logger.error(f"OI current fetch failed: {e}")
        return None


def get_derivatives_features(symbol: str = "BTCUSDT") -> Dict:
    """收集所有衍生品特徵（最新一筆）"""
    import time
    
    lsr_df = fetch_lsr(symbol, "1h", 3)
    time.sleep(0.2)
    gsr_df = fetch_gsr(symbol, "1h", 3)
    time.sleep(0.2)
    taker_df = fetch_taker(symbol, "1h", 3)
    time.sleep(0.2)
    oi_df = fetch_oi_hist(symbol, "1h", 3)
    
    result = {}
    if lsr_df is not None and len(lsr_df) > 0:
        latest = lsr_df.iloc[-1]
        result['lsr_ratio'] = float(latest['longShortRatio'])
        result['lsr_long_account'] = float(latest['longAccount'])
    if gsr_df is not None and len(gsr_df) > 0:
        result['gsr_ratio'] = float(gsr_df.iloc[-1]['longShortRatio'])
    if taker_df is not None and len(taker_df) > 0:
        result['taker_ratio'] = float(taker_df.iloc[-1]['buySellRatio'])
    if oi_df is not None and len(oi_df) > 0:
        result['oi_value'] = float(oi_df.iloc[-1]['sumOpenInterest'])
        result['oi_usd'] = float(oi_df.iloc[-1]['sumOpenInterestValue'])
    
    logger.info(f"Derivatives: lsr={result.get('lsr_ratio')}, gsr={result.get('gsr_ratio')}, "
                f"taker={result.get('taker_ratio')}, oi={result.get('oi_value')}")
    return result


if __name__ == "__main__":
    feat = get_derivatives_features()
    for k, v in feat.items():
        print(f"  {k}: {v}")
