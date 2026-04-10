#!/usr/bin/env python3
"""Backfill core technical indicator history into features_normalized.

Goal: restore chart coverage for RSI14 / MACD-hist / ATR% / VWAP dev / BB%B.
This script computes indicators once over the full raw price series, then updates
matching feature rows by (timestamp, symbol) in batches.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/kazuha/Poly-Trader")

from feature_engine.technical_indicators import rsi, macd, bollinger_bands, atr, vwap

DB_PATH = Path("/home/kazuha/Poly-Trader/poly_trader.db")
SYMBOL = "BTCUSDT"
BATCH = 2000


def build_volume_series(close: np.ndarray, raw_volume: pd.Series) -> np.ndarray:
    """Construct a per-row volume series without forward/backward filling.

    Real observed volume is kept as-is. Missing or non-positive points are replaced only
    at those exact rows with a local price-move proxy so the backfill does not smear
    future/past volume information across time.
    """
    parsed = pd.to_numeric(raw_volume, errors="coerce")
    proxy = pd.Series(close).diff().abs().fillna(1.0)
    proxy = proxy.mask(proxy <= 0, 1.0)
    combined = parsed.where(parsed.notna() & (parsed > 0), proxy)
    return combined.to_numpy(dtype=float)


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT r.timestamp, r.symbol, r.close_price, r.volume
        FROM raw_market_data r
        WHERE r.symbol = ? AND r.close_price IS NOT NULL
        ORDER BY r.timestamp ASC
        """,
        (SYMBOL,),
    ).fetchall()

    if not rows:
        raise SystemExit("No raw rows found")

    df = pd.DataFrame([dict(r) for r in rows])
    close = df["close_price"].astype(float).to_numpy()
    raw_volume = pd.to_numeric(df["volume"], errors="coerce")
    vol = build_volume_series(close, raw_volume)

    high_est = close * 1.005
    low_est = close * 0.995

    rsi_vals = rsi(close, period=14)
    macd_line, sig_line, hist = macd(close)
    _, _, _, bb_pct_b = bollinger_bands(close)
    atr_vals = atr(high_est, low_est, close, period=14)
    vwap_vals = vwap(high_est, low_est, close, vol)

    updates = []
    for i, row in enumerate(rows):
        price = close[i]
        rsi14 = float(rsi_vals[i]) / 100.0 if np.isfinite(rsi_vals[i]) else None
        macd_hist = float(hist[i] / price) if price and np.isfinite(hist[i]) else None
        bb = float(bb_pct_b[i]) if np.isfinite(bb_pct_b[i]) else None
        atr_pct = float(atr_vals[i] / price) if price and np.isfinite(atr_vals[i]) else None
        vwap_dev = float((price - vwap_vals[i]) / price) if price and np.isfinite(vwap_vals[i]) else None
        updates.append((rsi14, macd_hist, atr_pct, vwap_dev, bb, row["timestamp"], row["symbol"]))

    total = 0
    for i in range(0, len(updates), BATCH):
        batch = updates[i:i + BATCH]
        conn.executemany(
            """
            UPDATE features_normalized
            SET feat_rsi14 = ?,
                feat_macd_hist = ?,
                feat_atr_pct = ?,
                feat_vwap_dev = ?,
                feat_bb_pct_b = ?
            WHERE timestamp = ? AND symbol = ?
            """,
            batch,
        )
        conn.commit()
        total += len(batch)
        print(f"updated {total}/{len(updates)}")

    result = conn.execute(
        """
        SELECT
          COUNT(*) AS total,
          SUM(CASE WHEN feat_rsi14 IS NOT NULL THEN 1 ELSE 0 END) AS rsi14,
          SUM(CASE WHEN feat_macd_hist IS NOT NULL THEN 1 ELSE 0 END) AS macd_hist,
          SUM(CASE WHEN feat_atr_pct IS NOT NULL THEN 1 ELSE 0 END) AS atr_pct,
          SUM(CASE WHEN feat_vwap_dev IS NOT NULL THEN 1 ELSE 0 END) AS vwap_dev,
          SUM(CASE WHEN feat_bb_pct_b IS NOT NULL THEN 1 ELSE 0 END) AS bb_pct_b
        FROM features_normalized
        WHERE symbol = ?
        """,
        (SYMBOL,),
    ).fetchone()

    print({key: result[key] for key in result.keys()})
    conn.close()


if __name__ == "__main__":
    main()
