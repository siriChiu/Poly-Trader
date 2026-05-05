"""OKX-only public market data helpers.

These helpers centralize every unauthenticated exchange data request used by the
legacy sensing/backfill scripts.  The project is intentionally OKX-only now:
callers should import this module instead of reaching non-OKX exchange REST endpoints.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

OKX_BASE_URL = "https://www.okx.com"


def normalize_okx_inst_id(symbol: str = "BTC/USDT", *, swap: bool = False) -> str:
    """Normalize BTCUSDT / BTC/USDT / BTC-USDT into OKX instId form.

    Legacy callers still pass Binance-style concatenated symbols such as
    ``BTCUSDT``.  OKX public/private APIs require hyphenated instrument IDs
    (``BTC-USDT`` and ``BTC-USDT-SWAP``), so normalize those legacy symbols at
    the boundary instead of letting collectors hit OKX with invalid instIds.
    """
    value = str(symbol or "BTC/USDT").strip().upper().replace("/", "-").replace("_", "-")
    if not value:
        value = "BTC-USDT"
    had_swap_suffix = value.endswith("-SWAP") or value.endswith("SWAP")
    value = value.removesuffix("-SWAP").removesuffix("SWAP").strip("-")
    if "-" not in value:
        for quote in ("USDT", "USDC", "USD"):
            if value.endswith(quote) and len(value) > len(quote):
                value = f"{value[:-len(quote)]}-{quote}"
                break
    if swap or had_swap_suffix:
        value = value.removesuffix("-SWAP") + "-SWAP"
    return value


def normalize_okx_bar(interval: str = "1h") -> str:
    value = str(interval or "1h").strip()
    mapping = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1H",
        "2h": "2H",
        "4h": "4H",
        "6h": "6H",
        "12h": "12H",
        "1d": "1D",
        "1D": "1D",
    }
    return mapping.get(value, mapping.get(value.lower(), value))


def normalize_okx_rubik_period(period: str = "1h") -> str:
    """Normalize OKX trading-data periods.

    Several OKX rubik endpoints only accept 5m, 1H, or 1D.  Keep the
    fallback exchange-native and bounded rather than silently calling a
    different venue when scripts request unsupported 4H/6H-style buckets.
    """
    value = str(period or "1h").strip().lower()
    if value in {"5m", "5min"}:
        return "5m"
    if value in {"1d", "1day", "24h"}:
        return "1D"
    return "1H"


def _create_session(retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def okx_get(path: str, params: Optional[Dict[str, Any]] = None, *, timeout: int = 15) -> Dict[str, Any]:
    session = _create_session()
    resp = session.get(f"{OKX_BASE_URL}{path}", params=params or {}, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    if str(payload.get("code", "0")) not in {"0", ""}:
        raise RuntimeError(f"OKX API error {payload.get('code')}: {payload.get('msg')}")
    return payload


def okx_data(path: str, params: Optional[Dict[str, Any]] = None, *, timeout: int = 15) -> List[Any]:
    payload = okx_get(path, params, timeout=timeout)
    data = payload.get("data")
    return data if isinstance(data, list) else []


def fetch_candles(symbol: str = "BTC/USDT", interval: str = "1h", limit: int = 100, *, history: bool = False) -> List[List[Any]]:
    path = "/api/v5/market/history-candles" if history else "/api/v5/market/candles"
    return okx_data(
        path,
        {
            "instId": normalize_okx_inst_id(symbol),
            "bar": normalize_okx_bar(interval),
            "limit": max(1, min(int(limit), 300)),
        },
    )


def fetch_klines_df(symbol: str = "BTC/USDT", interval: str = "1h", days: int = 30, limit: int = 300) -> pd.DataFrame:
    """Fetch recent OKX candles as timestamp/open/high/low/close/volume DataFrame.

    OKX public candle endpoints are newest-first; the returned frame is sorted
    ascending.  For long historical ranges this intentionally stays bounded and
    fail-closed rather than silently using another exchange.
    """
    # Keep calls bounded for heartbeat safety while covering the requested range
    # when it fits inside OKX's single-call public limit.
    interval_l = str(interval or "1h").lower()
    per_day = 24
    if interval_l.endswith("h"):
        try:
            per_day = max(1, int(24 / max(1, int(interval_l[:-1]))))
        except Exception:
            per_day = 24
    elif interval_l.endswith("m"):
        try:
            per_day = max(1, int(24 * 60 / max(1, int(interval_l[:-1]))))
        except Exception:
            per_day = 24
    elif interval_l.endswith("d"):
        per_day = 1
    request_limit = max(1, min(int(limit), int(days) * per_day + 5, 300))
    rows = fetch_candles(symbol, interval, request_limit, history=bool(days and days > 2))
    records: List[Dict[str, Any]] = []
    cutoff = datetime.utcnow() - timedelta(days=int(days))
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            continue
        ts = pd.to_datetime(int(row[0]), unit="ms")
        if ts.to_pydatetime() < cutoff:
            continue
        records.append(
            {
                "timestamp": ts,
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
        )
    if not records:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    return pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)


def fetch_ticker(symbol: str = "BTC/USDT") -> Dict[str, Any]:
    data = okx_data("/api/v5/market/ticker", {"instId": normalize_okx_inst_id(symbol)})
    return data[0] if data else {}


def fetch_order_book(symbol: str = "BTC/USDT", limit: int = 400) -> Dict[str, Any]:
    data = okx_data(
        "/api/v5/market/books",
        {"instId": normalize_okx_inst_id(symbol), "sz": max(1, min(int(limit), 400))},
    )
    return data[0] if data else {"bids": [], "asks": []}


def fetch_trades(symbol: str = "BTC/USDT", limit: int = 100) -> List[Dict[str, Any]]:
    data = okx_data(
        "/api/v5/market/trades",
        {"instId": normalize_okx_inst_id(symbol), "limit": max(1, min(int(limit), 500))},
    )
    return [row for row in data if isinstance(row, dict)]


def fetch_current_funding(symbol: str = "BTC/USDT") -> Optional[float]:
    data = okx_data("/api/v5/public/funding-rate", {"instId": normalize_okx_inst_id(symbol, swap=True)})
    if not data:
        return None
    value = data[0].get("fundingRate")
    return float(value) if value not in (None, "") else None


def fetch_funding_history(symbol: str = "BTC/USDT", limit: int = 100) -> List[Dict[str, Any]]:
    data = okx_data(
        "/api/v5/public/funding-rate-history",
        {"instId": normalize_okx_inst_id(symbol, swap=True), "limit": max(1, min(int(limit), 100))},
    )
    return [row for row in data if isinstance(row, dict)]


def fetch_current_open_interest(symbol: str = "BTC/USDT") -> Optional[float]:
    data = okx_data(
        "/api/v5/public/open-interest",
        {"instType": "SWAP", "instId": normalize_okx_inst_id(symbol, swap=True)},
    )
    if not data:
        return None
    value = data[0].get("oi") or data[0].get("oiCcy")
    return float(value) if value not in (None, "") else None


def fetch_open_interest_series(symbol: str = "BTC/USDT", period: str = "1H", limit: int = 24) -> List[Dict[str, Any]]:
    # OKX trading-data/rubik endpoints are public and exchange-native.
    data = okx_data(
        "/api/v5/rubik/stat/contracts/open-interest-volume",
        {"ccy": normalize_okx_inst_id(symbol).split("-")[0], "period": normalize_okx_rubik_period(period), "limit": max(1, min(int(limit), 100))},
    )
    rows = []
    for row in data:
        if isinstance(row, dict):
            rows.append(row)
        elif isinstance(row, (list, tuple)) and len(row) >= 2:
            rows.append({"ts": row[0], "openInterest": row[1]})
    return rows


def fetch_long_short_ratio_series(symbol: str = "BTC/USDT", period: str = "1H", limit: int = 24) -> List[Dict[str, Any]]:
    data = okx_data(
        "/api/v5/rubik/stat/contracts/long-short-account-ratio",
        {"ccy": normalize_okx_inst_id(symbol).split("-")[0], "period": normalize_okx_rubik_period(period), "limit": max(1, min(int(limit), 100))},
    )
    rows = []
    for row in data:
        if isinstance(row, dict):
            rows.append(row)
        elif isinstance(row, (list, tuple)) and len(row) >= 2:
            rows.append({"ts": row[0], "longShortRatio": row[1]})
    return rows


def fetch_taker_volume_series(symbol: str = "BTC/USDT", period: str = "1H", limit: int = 24) -> List[Dict[str, Any]]:
    data = okx_data(
        "/api/v5/rubik/stat/taker-volume",
        {"ccy": normalize_okx_inst_id(symbol).split("-")[0], "instType": "CONTRACTS", "period": normalize_okx_rubik_period(period), "limit": max(1, min(int(limit), 100))},
    )
    rows = []
    for row in data:
        if isinstance(row, dict):
            rows.append(row)
        elif isinstance(row, (list, tuple)) and len(row) >= 3:
            rows.append({"ts": row[0], "sellVol": row[1], "buyVol": row[2]})
    return rows


def last_float(rows: Iterable[Dict[str, Any]], *keys: str) -> Optional[float]:
    for row in reversed(list(rows)):
        for key in keys:
            value = row.get(key)
            if value not in (None, ""):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
    return None
