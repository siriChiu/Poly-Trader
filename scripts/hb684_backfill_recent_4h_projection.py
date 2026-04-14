from __future__ import annotations

from bisect import bisect_right
from datetime import datetime
from pathlib import Path
import sys

import ccxt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from database.models import FeaturesNormalized, init_db
from feature_engine.ohlcv_4h import compute_4h_indicators

DB_URL = f"sqlite:///{PROJECT_ROOT / 'poly_trader.db'}"
session = init_db(DB_URL)

try:
    target_rows = (
        session.query(FeaturesNormalized)
        .filter(FeaturesNormalized.timestamp >= "2026-04-11 00:00:00")
        .filter(
            (FeaturesNormalized.feat_4h_bias50.is_(None))
            | (FeaturesNormalized.feat_4h_dist_bb_lower.is_(None))
            | (FeaturesNormalized.feat_4h_dist_swing_low.is_(None))
            | (FeaturesNormalized.feat_4h_vol_ratio.is_(None))
        )
        .order_by(FeaturesNormalized.timestamp)
        .all()
    )
    print(f"candidate_rows={len(target_rows)}")
    if not target_rows:
        raise SystemExit(0)

    exchange = ccxt.binance({"enableRateLimit": True})
    ohlcv = exchange.fetch_ohlcv("BTC/USDT", "4h", limit=1000)
    print(f"fetched_4h_candles={len(ohlcv)}")
    candles = {
        "timestamps": np.array([row[0] for row in ohlcv], dtype=np.int64),
        "opens": np.array([row[1] for row in ohlcv], dtype=float),
        "highs": np.array([row[2] for row in ohlcv], dtype=float),
        "lows": np.array([row[3] for row in ohlcv], dtype=float),
        "closes": np.array([row[4] for row in ohlcv], dtype=float),
        "volumes": np.array([row[5] for row in ohlcv], dtype=float),
    }
    indicators = compute_4h_indicators(candles)
    ts_list = candles["timestamps"].tolist()

    def gv(name: str, idx: int, default: float | None = None):
        arr = indicators.get(name)
        if arr is None or idx < 0 or idx >= len(arr):
            return default
        val = arr[idx]
        if val is None:
            return default
        try:
            f = float(val)
        except (TypeError, ValueError):
            return default
        if np.isfinite(f):
            return f
        return default

    updated = 0
    for row in target_rows:
        ts_ms = int(datetime.fromisoformat(str(row.timestamp)).timestamp() * 1000)
        idx = bisect_right(ts_list, ts_ms) - 1
        if idx < 0:
            continue
        row.feat_4h_bias50 = gv("4h_bias50", idx)
        row.feat_4h_bias20 = gv("4h_bias20", idx)
        row.feat_4h_bias200 = gv("4h_bias200", idx)
        row.feat_4h_rsi14 = gv("4h_rsi14", idx)
        row.feat_4h_macd_hist = gv("4h_macd_hist", idx)
        row.feat_4h_bb_pct_b = gv("4h_bb_pct_b", idx, 0.5)
        row.feat_4h_dist_bb_lower = gv("4h_dist_bb_lower", idx, 0.0)
        row.feat_4h_ma_order = gv("4h_ma_order", idx, 0.0)
        row.feat_4h_dist_swing_low = gv("4h_dist_swing_low", idx, 0.0)
        row.feat_4h_vol_ratio = gv("4h_vol_ratio", idx, 1.0)
        updated += 1
    session.commit()
    print(f"done updated={updated}")
finally:
    session.close()
