#!/usr/bin/env python3
"""Backfill raw data + features + labels for a requested backtest window."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable

import pandas as pd
from sqlalchemy import func

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config
from data_ingestion.backfill_historical import fetch_okx_klines
from data_ingestion.labeling import generate_future_return_labels, save_labels_to_db
from database.models import FeaturesNormalized, Labels, RawMarketData, init_db
from feature_engine.preprocessor import backfill_missing_feature_rows
from scripts import backfill_4h_distance as backfill_4h_distance_module
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _parse_ts(value: Optional[Any]) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("T", " ")
    if normalized.endswith("Z"):
        normalized = normalized[:-1]
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        dt = datetime.strptime(normalized[:19], "%Y-%m-%d %H:%M:%S")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _range_summary(query, time_attr: str = "timestamp") -> Dict[str, Any]:
    rows = query.order_by(getattr(query.column_descriptions[0]["entity"], time_attr)).all()
    if not rows:
        return {"start": None, "end": None, "count": 0}
    timestamps = [getattr(row, time_attr) for row in rows if getattr(row, time_attr) is not None]
    if not timestamps:
        return {"start": None, "end": None, "count": 0}
    return {
        "start": _iso(min(timestamps)),
        "end": _iso(max(timestamps)),
        "count": len(rows),
    }


def collect_coverage(session, symbol: str = "BTCUSDT", horizon_hours: int = 24) -> Dict[str, Dict[str, Any]]:
    symbol_key = str(symbol or "BTCUSDT").replace("/", "")
    raw = (
        session.query(RawMarketData)
        .filter(func.replace(RawMarketData.symbol, "/", "") == symbol_key)
    )
    features = (
        session.query(FeaturesNormalized)
        .filter((func.replace(FeaturesNormalized.symbol, "/", "") == symbol_key) | (FeaturesNormalized.symbol.is_(None)))
        .filter(FeaturesNormalized.feat_4h_bias50.isnot(None))
    )
    labels = (
        session.query(Labels)
        .filter(func.replace(Labels.symbol, "/", "") == symbol_key)
        .filter(Labels.horizon_minutes == horizon_hours * 60)
    )
    return {
        "raw": _range_summary(raw),
        "features": _range_summary(features),
        "labels": _range_summary(labels),
    }


def compute_missing_range(
    coverage: Dict[str, Dict[str, Any]],
    *,
    target_start: Any,
    target_end: Any,
) -> Dict[str, Any]:
    start_dt = _parse_ts(target_start)
    end_dt = _parse_ts(target_end)
    if start_dt is None:
        raise ValueError("target_start is required")
    if end_dt is None:
        end_dt = datetime.utcnow()
    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    raw_start = _parse_ts(coverage.get("raw", {}).get("start"))
    feature_start = _parse_ts(coverage.get("features", {}).get("start"))
    label_start = _parse_ts(coverage.get("labels", {}).get("start"))
    raw_end = _parse_ts(coverage.get("raw", {}).get("end"))
    feature_end = _parse_ts(coverage.get("features", {}).get("end"))
    label_end = _parse_ts(coverage.get("labels", {}).get("end"))

    missing_raw_start = raw_start is None or start_dt < raw_start
    missing_feature_start = feature_start is None or start_dt < feature_start
    missing_label_start = label_start is None or start_dt < label_start
    missing_raw_end = raw_end is None or end_dt > raw_end
    missing_feature_end = feature_end is None or end_dt > feature_end
    missing_label_end = label_end is None or end_dt > label_end
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    requested_until = max(now_utc, end_dt)
    requested_days = max(1, int((requested_until - start_dt).total_seconds() / 86400) + 2)

    return {
        "target_start": _iso(start_dt),
        "target_end": _iso(end_dt),
        "requested_days": requested_days,
        "missing_raw_start": missing_raw_start,
        "missing_feature_start": missing_feature_start,
        "missing_label_start": missing_label_start,
        "missing_raw_end": missing_raw_end,
        "missing_feature_end": missing_feature_end,
        "missing_label_end": missing_label_end,
        "needs_backfill": (
            missing_raw_start
            or missing_feature_start
            or missing_label_start
            or missing_raw_end
            or missing_feature_end
            or missing_label_end
        ),
    }


def fetch_and_store_raw_history(session, symbol: str, days: int) -> int:
    df = fetch_okx_klines(symbol=symbol, interval="1h", days=days)
    if df.empty:
        return 0
    existing = {
        row[0]
        for row in session.query(RawMarketData.timestamp)
        .filter(func.replace(RawMarketData.symbol, "/", "") == str(symbol or "").replace("/", ""))
        .all()
    }
    inserted = 0
    for row in df.itertuples(index=False):
        ts = row.timestamp.to_pydatetime() if hasattr(row.timestamp, "to_pydatetime") else row.timestamp
        if ts in existing:
            continue
        session.add(
            RawMarketData(
                timestamp=ts,
                symbol=symbol,
                close_price=float(row.close),
                volume=float(row.volume) if row.volume is not None else None,
            )
        )
        existing.add(ts)
        inserted += 1
    if inserted:
        session.commit()
    return inserted


def _ccxt_symbol(symbol: str) -> str:
    value = str(symbol or "BTCUSDT").strip().upper().replace("-", "/")
    if "/" in value:
        return value
    for quote in ("USDT", "USDC", "USD"):
        if value.endswith(quote) and len(value) > len(quote):
            return f"{value[:-len(quote)]}/{quote}"
    return value


def fetch_okx_klines_for_range(
    *,
    symbol: str,
    target_start: Any,
    target_end: Any,
    interval: str = "1h",
) -> pd.DataFrame:
    """Fetch every OHLCV page inside an explicit historical repair window.

    The normal bounded collector intentionally returns at most 300 bars.  That
    is suitable for heartbeats but cannot repair a gap that is older than the
    most recent 300 bars, so this helper advances an exchange cursor page by
    page only when an operator explicitly repairs a missing backtest window.
    """
    start_dt = _parse_ts(target_start)
    end_dt = _parse_ts(target_end)
    if start_dt is None or end_dt is None or end_dt < start_dt:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    try:
        import ccxt
    except ImportError as exc:  # pragma: no cover - production dependency
        raise RuntimeError("ccxt is required for explicit historical gap repair") from exc

    interval_seconds = {"1h": 3600, "4h": 14_400, "1d": 86_400}.get(str(interval).lower(), 3600)
    start_ms = int(start_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(end_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
    cursor_ms = start_ms
    rows: List[List[Any]] = []
    exchange = ccxt.okx({"enableRateLimit": True})

    while cursor_ms <= end_ms:
        page = exchange.fetch_ohlcv(_ccxt_symbol(symbol), timeframe=interval, since=cursor_ms, limit=300)
        if not page:
            break
        page = [row for row in page if row and len(row) >= 6 and start_ms <= int(row[0]) <= end_ms]
        if page:
            rows.extend(page)
        newest_ms = max(int(row[0]) for row in page) if page else cursor_ms
        next_cursor_ms = newest_ms + interval_seconds * 1000
        if next_cursor_ms <= cursor_ms:
            break
        cursor_ms = next_cursor_ms

    if not rows:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    deduped = {int(row[0]): row for row in rows}
    return pd.DataFrame(
        [
            {
                "timestamp": pd.to_datetime(ts, unit="ms"),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
            for ts, row in sorted(deduped.items())
        ]
    )


def fetch_and_store_raw_gap_range(
    session,
    *,
    symbol: str,
    target_start: Any,
    target_end: Any,
) -> int:
    """Fill one detected interior raw-data gap without re-fetching all history."""
    df = fetch_okx_klines_for_range(
        symbol=symbol,
        target_start=target_start,
        target_end=target_end,
    )
    if df.empty:
        return 0
    existing = {
        row[0]
        for row in session.query(RawMarketData.timestamp)
        .filter(func.replace(RawMarketData.symbol, "/", "") == str(symbol or "").replace("/", ""))
        .all()
    }
    inserted = 0
    for row in df.itertuples(index=False):
        ts = row.timestamp.to_pydatetime() if hasattr(row.timestamp, "to_pydatetime") else row.timestamp
        if ts in existing:
            continue
        session.add(
            RawMarketData(
                timestamp=ts,
                symbol=symbol,
                close_price=float(row.close),
                volume=float(row.volume) if row.volume is not None else None,
            )
        )
        existing.add(ts)
        inserted += 1
    if inserted:
        session.commit()
    return inserted


def run_backfill_pipeline(
    session,
    *,
    symbol: str = "BTCUSDT",
    target_start: Any,
    target_end: Any | None = None,
    horizon_hours: int = 24,
    apply_changes: bool = False,
    interior_gap_ranges: Optional[List[Dict[str, Any]]] = None,
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    coverage_before = collect_coverage(session, symbol=symbol, horizon_hours=horizon_hours)
    plan = compute_missing_range(coverage_before, target_start=target_start, target_end=target_end)
    actions = {
        "raw_rows_inserted": 0,
        "feature_rows_inserted": 0,
        "four_h_distance_refreshed": False,
        "labels_saved": 0,
    }

    repair_ranges = [
        item for item in (interior_gap_ranges or [])
        if isinstance(item, dict) and item.get("start") and item.get("end")
    ]
    plan["interior_gap_count"] = len(repair_ranges)
    plan["needs_backfill"] = bool(plan["needs_backfill"] or repair_ranges)

    if apply_changes and plan["needs_backfill"]:
        if progress_callback:
            progress_callback("plan", {"plan": plan, "coverage_before": coverage_before})
        if plan["missing_raw_start"] or plan["missing_raw_end"]:
            if progress_callback:
                progress_callback("raw", {"requested_days": plan["requested_days"]})
            actions["raw_rows_inserted"] = fetch_and_store_raw_history(session, symbol, plan["requested_days"])
        if repair_ranges:
            if progress_callback:
                progress_callback("raw_gap_repair", {"gap_count": len(repair_ranges)})
            for gap in repair_ranges:
                actions["raw_rows_inserted"] += fetch_and_store_raw_gap_range(
                    session,
                    symbol=symbol,
                    target_start=gap["start"],
                    target_end=gap["end"],
                )
        if (
            plan["missing_raw_start"]
            or plan["missing_raw_end"]
            or plan["missing_feature_start"]
            or plan["missing_feature_end"]
            or repair_ranges
        ):
            if progress_callback:
                progress_callback("features", {"symbol": symbol})
            actions["feature_rows_inserted"] = backfill_missing_feature_rows(session, symbol=symbol, lookback_days=None)
            if progress_callback:
                progress_callback("4h_distance", {"symbol": symbol})
            backfill_4h_distance_module.main()
            actions["four_h_distance_refreshed"] = True
        if (
            plan["missing_raw_start"]
            or plan["missing_raw_end"]
            or plan["missing_feature_start"]
            or plan["missing_feature_end"]
            or plan["missing_label_start"]
            or plan["missing_label_end"]
            or repair_ranges
        ):
            if progress_callback:
                progress_callback("labels", {"horizon_hours": horizon_hours})
            labels_df = generate_future_return_labels(session, symbol=symbol, horizon_hours=horizon_hours)
            if not labels_df.empty:
                save_labels_to_db(session, labels_df, symbol=symbol, horizon_hours=horizon_hours)
                actions["labels_saved"] = len(labels_df)

    coverage_after = collect_coverage(session, symbol=symbol, horizon_hours=horizon_hours)
    result = {
        "dry_run": not apply_changes,
        "coverage_before": coverage_before,
        "plan": plan,
        "actions": actions,
        "coverage_after": coverage_after,
    }
    if progress_callback:
        progress_callback("complete", result)
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill Poly-Trader raw/features/labels for a requested backtest range")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--start", required=True, help="Requested backtest start time, e.g. 2024-04-16T00:00:00Z")
    parser.add_argument("--end", default=None, help="Requested backtest end time")
    parser.add_argument("--horizon-hours", type=int, default=24)
    parser.add_argument("--apply", action="store_true", help="Actually write data instead of dry-run summary")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    cfg = load_config()
    session = init_db(cfg["database"]["url"])
    try:
        result = run_backfill_pipeline(
            session,
            symbol=args.symbol,
            target_start=args.start,
            target_end=args.end,
            horizon_hours=args.horizon_hours,
            apply_changes=args.apply,
        )
    finally:
        session.close()

    logger.info("backfill result: %s", result)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
