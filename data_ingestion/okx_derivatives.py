"""
OKX 衍生品數據收集器
提供獨立於 K線和 Funding Rate 的新信號：
- 大戶/全市場多空比 (LSR/GSR)
- 主動買賣比 (Taker)
- OI 歷史
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from data_ingestion.okx_public import (
    fetch_current_open_interest,
    fetch_long_short_ratio_series,
    fetch_open_interest_series,
    fetch_taker_volume_series,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _frame_from_rows(rows, value_key: str, output_col: str) -> Optional[pd.DataFrame]:
    records = []
    for row in rows or []:
        value = row.get(value_key) or row.get(output_col)
        ts = row.get("ts") or row.get("timestamp")
        if value in (None, ""):
            continue
        records.append({"timestamp": pd.to_datetime(int(ts), unit="ms") if ts not in (None, "") else pd.NaT, output_col: float(value)})
    if not records:
        return None
    return pd.DataFrame(records).sort_values("timestamp")


def fetch_lsr(symbol: str = "BTC/USDT", period: str = "1h", limit: int = 100) -> Optional[pd.DataFrame]:
    """OKX long/short account ratio proxy for LSR."""
    try:
        return _frame_from_rows(fetch_long_short_ratio_series(symbol, period, limit), "longShortRatio", "longShortRatio")
    except Exception as e:
        logger.error(f"OKX LSR fetch failed: {e}")
        return None


def fetch_gsr(symbol: str = "BTC/USDT", period: str = "1h", limit: int = 100) -> Optional[pd.DataFrame]:
    """OKX global long/short account ratio proxy."""
    return fetch_lsr(symbol, period, limit)


def fetch_taker(symbol: str = "BTC/USDT", period: str = "1h", limit: int = 100) -> Optional[pd.DataFrame]:
    """OKX taker buy/sell ratio."""
    try:
        records = []
        for row in fetch_taker_volume_series(symbol, period, limit):
            buy = row.get("buyVol") or row.get("buyVolume")
            sell = row.get("sellVol") or row.get("sellVolume")
            ts = row.get("ts") or row.get("timestamp")
            if buy in (None, "") or sell in (None, ""):
                continue
            buy_f = float(buy)
            sell_f = float(sell)
            ratio = buy_f / sell_f if sell_f else None
            if ratio is None:
                continue
            records.append({"timestamp": pd.to_datetime(int(ts), unit="ms") if ts not in (None, "") else pd.NaT, "buySellRatio": ratio})
        if not records:
            return None
        return pd.DataFrame(records).sort_values("timestamp")
    except Exception as e:
        logger.error(f"OKX taker fetch failed: {e}")
        return None


def fetch_oi_hist(symbol: str = "BTC/USDT", period: str = "1h", limit: int = 100) -> Optional[pd.DataFrame]:
    try:
        rows = fetch_open_interest_series(symbol, period, limit)
        records = []
        for row in rows:
            oi = row.get("openInterest") or row.get("oi") or row.get("oiCcy")
            ts = row.get("ts") or row.get("timestamp")
            if oi in (None, ""):
                continue
            records.append({"timestamp": pd.to_datetime(int(ts), unit="ms") if ts not in (None, "") else pd.NaT, "sumOpenInterest": float(oi), "sumOpenInterestValue": float(oi)})
        if not records:
            return None
        return pd.DataFrame(records).sort_values("timestamp")
    except Exception as e:
        logger.error(f"OKX OI hist fetch failed: {e}")
        return None


def fetch_oi_current(symbol: str = "BTC/USDT") -> Optional[float]:
    try:
        return fetch_current_open_interest(symbol)
    except Exception as e:
        logger.error(f"OKX OI current fetch failed: {e}")
        return None


def get_derivatives_features(symbol: str = "BTC/USDT") -> Dict:
    lsr_df = fetch_lsr(symbol, "1h", 3)
    gsr_df = fetch_gsr(symbol, "1h", 3)
    taker_df = fetch_taker(symbol, "1h", 3)
    oi_df = fetch_oi_hist(symbol, "1h", 3)
    result: Dict[str, float] = {}
    if lsr_df is not None and len(lsr_df) > 0:
        latest = lsr_df.iloc[-1]
        result["lsr_ratio"] = float(latest["longShortRatio"])
        result["lsr_long_account"] = float(latest["longShortRatio"])
    if gsr_df is not None and len(gsr_df) > 0:
        result["gsr_ratio"] = float(gsr_df.iloc[-1]["longShortRatio"])
    if taker_df is not None and len(taker_df) > 0:
        result["taker_ratio"] = float(taker_df.iloc[-1]["buySellRatio"])
    if oi_df is not None and len(oi_df) > 0:
        result["oi_value"] = float(oi_df.iloc[-1]["sumOpenInterest"])
        result["oi_usd"] = float(oi_df.iloc[-1]["sumOpenInterestValue"])
    logger.info("OKX derivatives: lsr=%s, gsr=%s, taker=%s, oi=%s", result.get("lsr_ratio"), result.get("gsr_ratio"), result.get("taker_ratio"), result.get("oi_value"))
    return result


if __name__ == "__main__":
    for k, v in get_derivatives_features().items():
        print(f"  {k}: {v}")
