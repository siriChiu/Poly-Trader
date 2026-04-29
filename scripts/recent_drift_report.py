#!/usr/bin/env python3
"""Recent distribution-aware drift report for canonical simulated_pyramid_win.

Purpose:
- explain TW-IC decay with recent label balance / regime mix facts
- provide machine-readable output for heartbeat summaries + auto-propose

Output:
- data/recent_drift_report.json
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import pstdev
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from data_ingestion.labeling import DEFAULT_LONG_MAX_DD_PCT, DEFAULT_LONG_TP_PCT
from feature_engine.feature_history_policy import FEATURE_KEY_MAP, SOURCE_FEATURE_KEYS
DB_PATH = PROJECT_ROOT / "poly_trader.db"
OUT_PATH = PROJECT_ROOT / "data" / "recent_drift_report.json"
TAIL_ROOT_CAUSE_OUT_PATH = PROJECT_ROOT / "data" / "canonical_tail_root_cause.json"
TARGET_COL = "simulated_pyramid_win"
CANONICAL_HORIZON_MINUTES = 1440
WINDOWS = [100, 250, 500, 1000]
TAIL_ROOT_CAUSE_WINDOW = 100
HIGH_UNDERWATER_RATIO_THRESHOLD = 0.50
TAIL_ROOT_CAUSE_FEATURES = [
    "feat_4h_bias200",
    "feat_4h_dist_swing_low",
    "feat_4h_dist_swing_high",
    "feat_4h_bias50",
    "feat_4h_bias20",
    "feat_4h_rsi14",
    "feat_4h_bb_pct_b",
    "feat_4h_macd_hist",
]
LOW_VARIANCE_STD_RATIO_THRESHOLD = 0.15
LOW_DISTINCT_RATIO_THRESHOLD = 0.10
LOW_DISTINCT_MAX_COUNT = 5
NULL_HEAVY_NON_NULL_RATIO_THRESHOLD = 0.70
FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT = 5
TARGET_PATH_EXAMPLE_LIMIT = 5
WEEKEND_DOMINANT_SHARE_THRESHOLD = 0.5
US_MACRO_MARKET_OPEN_HOUR_UTC = 13
US_MACRO_MARKET_OPEN_MINUTE_UTC = 30
US_MACRO_MARKET_CLOSE_HOUR_UTC = 20
US_MACRO_MARKET_CLOSE_MINUTE_UTC = 0
WEEKDAY_MACRO_CLOSED_SHARE_THRESHOLD = 0.9

EXPECTED_STATIC_FEATURE_RULES = {
    "feat_4h_ma_order": "discrete_regime_feature",
    "feat_vix": "market_hours_macro",
    "feat_dxy": "market_hours_macro",
    "feat_nq_return_1h": "market_hours_macro",
    "feat_nq_return_24h": "market_hours_macro",
}

EXPECTED_COMPRESSED_FEATURE_RULES = {
    "feat_atr_pct": {
        "proxy_col": "raw_volatility",
        "reason": "underlying_raw_volatility_compression",
    },
    "feat_4h_bias200": {
        "proxy_cols": ("raw_close_price", "raw_volatility"),
        "min_required_proxies": 2,
        "reason": "underlying_price_and_volatility_compression",
    },
    "feat_4h_bias50": {
        "proxy_cols": (
            "raw_close_price",
            "raw_volatility",
            "feat_4h_rsi14",
            "feat_4h_bb_pct_b",
            "feat_4h_macd_hist",
        ),
        "min_required_proxies": 4,
        "reason": "coherent_4h_trend_compression",
    },
    "feat_4h_bias20": {
        "proxy_cols": (
            "feat_4h_rsi14",
            "feat_4h_bb_pct_b",
            "feat_4h_macd_hist",
        ),
        "min_required_proxies": 3,
        "reason": "coherent_4h_short_trend_compression",
    },
    "feat_4h_rsi14": {
        "proxy_cols": (
            "raw_close_price",
            "raw_volatility",
            "feat_4h_bias20",
            "feat_4h_bb_pct_b",
            "feat_4h_macd_hist",
        ),
        "min_required_proxies": 4,
        "reason": "coherent_4h_short_trend_oscillator_compression",
    },
    "feat_4h_macd_hist": {
        "proxy_cols": (
            "raw_close_price",
            "raw_volatility",
            "feat_4h_bias50",
            "feat_4h_rsi14",
            "feat_4h_bb_pct_b",
        ),
        "min_required_proxies": 4,
        "reason": "coherent_4h_momentum_compression",
    },
    "feat_4h_dist_bb_lower": {
        "proxy_cols": (
            "raw_close_price",
            "raw_volatility",
            "feat_4h_bb_pct_b",
            "feat_4h_dist_swing_low",
        ),
        "min_required_proxies": 3,
        "reason": "coherent_4h_band_floor_compression",
    },
    "feat_4h_dist_swing_low": {
        "proxy_cols": (
            "raw_close_price",
            "raw_volatility",
            "feat_4h_dist_bb_lower",
            "feat_4h_bb_pct_b",
        ),
        "min_required_proxies": 3,
        "reason": "coherent_4h_support_cluster_compression",
    },
}


def _pct(numerator: int, denominator: int) -> float | None:
    if not denominator:
        return None
    return round(numerator / denominator, 4)


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _counter_to_dict(counter: Counter) -> dict[str, int]:
    return {str(k): int(v) for k, v in counter.items()}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _avg(rows: list[sqlite3.Row], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r[key] is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace(" ", "T")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        try:
            return datetime.fromisoformat(normalized.split(".")[0])
        except ValueError:
            return None


def _is_us_macro_market_open(ts: datetime) -> bool:
    hour = ts.hour
    minute = ts.minute
    if ts.weekday() >= 5:
        return False
    after_open = (hour, minute) >= (US_MACRO_MARKET_OPEN_HOUR_UTC, US_MACRO_MARKET_OPEN_MINUTE_UTC)
    before_close = (hour, minute) < (US_MACRO_MARKET_CLOSE_HOUR_UTC, US_MACRO_MARKET_CLOSE_MINUTE_UTC)
    return after_open and before_close


def _window_time_context(rows: list[sqlite3.Row]) -> dict[str, Any]:
    timestamps = [_parse_timestamp(row["timestamp"]) for row in rows if row["timestamp"] is not None]
    timestamps = [ts for ts in timestamps if ts is not None]
    total = len(timestamps)
    weekend_count = sum(1 for ts in timestamps if ts.weekday() >= 5)
    weekend_share = (weekend_count / total) if total else None
    weekday_count = sum(1 for ts in timestamps if ts.weekday() < 5)
    weekday_market_open_count = sum(1 for ts in timestamps if _is_us_macro_market_open(ts))
    weekday_market_closed_count = max(0, weekday_count - weekday_market_open_count)
    weekday_market_closed_share = (weekday_market_closed_count / weekday_count) if weekday_count else None
    return {
        "parsed_timestamps": total,
        "weekend_count": weekend_count,
        "weekend_share": _round(weekend_share),
        "weekend_dominant": bool(weekend_share is not None and weekend_share >= WEEKEND_DOMINANT_SHARE_THRESHOLD),
        "weekday_count": weekday_count,
        "weekday_market_open_count": weekday_market_open_count,
        "weekday_market_closed_count": weekday_market_closed_count,
        "weekday_market_closed_share": _round(weekday_market_closed_share),
        "weekday_market_closed_dominant": bool(
            weekday_market_closed_share is not None
            and weekday_market_closed_share >= WEEKDAY_MACRO_CLOSED_SHARE_THRESHOLD
        ),
    }


def _expected_static_reason(feature_col: str, window_context: dict[str, Any]) -> str | None:
    rule = EXPECTED_STATIC_FEATURE_RULES.get(feature_col)
    if rule == "discrete_regime_feature":
        return "discrete_regime_feature"
    if rule == "market_hours_macro":
        if window_context.get("weekend_dominant"):
            return "weekend_macro_market_closed"
        if window_context.get("weekday_market_closed_dominant"):
            return "weekday_macro_market_closed"
    return None


def _expected_compressed_details(
    feature_col: str,
    current_rows: list[sqlite3.Row],
    baseline_feature_stats: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    rule = EXPECTED_COMPRESSED_FEATURE_RULES.get(feature_col)
    if not rule:
        return None

    proxy_cols = rule.get("proxy_cols")
    if not proxy_cols:
        proxy_col = rule.get("proxy_col")
        proxy_cols = (proxy_col,) if proxy_col else ()
    proxy_cols = tuple(str(col) for col in proxy_cols if col)
    if not proxy_cols:
        return None

    row_keys = set(current_rows[0].keys()) if current_rows else set()
    if not all(proxy_col in row_keys for proxy_col in proxy_cols):
        return None

    proxy_stats: dict[str, Any] = {}
    compressed_proxy_count = 0
    for proxy_col in proxy_cols:
        proxy_recent = _feature_stats(current_rows, proxy_col)
        proxy_baseline = baseline_feature_stats.get(proxy_col) or {}
        proxy_recent_std = proxy_recent.get("std")
        proxy_baseline_std = proxy_baseline.get("std")
        if not isinstance(proxy_recent_std, (int, float)) or not isinstance(proxy_baseline_std, (int, float)):
            return None
        if proxy_baseline_std <= 0:
            return None

        proxy_std_ratio = proxy_recent_std / proxy_baseline_std
        proxy_details = {
            "recent_std": _round(proxy_recent_std),
            "baseline_std": _round(proxy_baseline_std),
            "std_ratio": _round(proxy_std_ratio),
            "recent_mean": _round(proxy_recent.get("mean")),
            "baseline_mean": _round(proxy_baseline.get("mean")),
            "mean_delta": _round((proxy_recent.get("mean") or 0.0) - (proxy_baseline.get("mean") or 0.0)),
        }
        proxy_stats[proxy_col] = proxy_details
        if proxy_std_ratio <= LOW_VARIANCE_STD_RATIO_THRESHOLD:
            compressed_proxy_count += 1

    min_required = int(rule.get("min_required_proxies") or len(proxy_cols))
    if compressed_proxy_count < min_required:
        return None

    # Heartbeat #1025 contract: ATR compression is expected whenever the underlying raw
    # volatility series compresses too. The proxy mean can rise during a strong bull pocket
    # even while dispersion collapses, so gating on mean direction misclassifies genuine
    # volatility contraction as a feature-pathology blocker.
    # Heartbeat #1026: feat_4h_bias200 should also downgrade to expected compression when
    # BOTH raw price dispersion and raw volatility dispersion collapse together. That keeps
    # recent drift focused on true projection bugs instead of a healthy bull-pocket squeeze.
    # Heartbeat #2026-04-16: feat_4h_macd_hist should likewise downgrade when the broader
    # 4H momentum cluster cools coherently (price + volatility + bias50 + RSI14 + BB%B all
    # compress together). Without this provenance layer, healthy bull-pocket momentum cooling
    # is misreported as a standalone MACD projection blocker.
    # Heartbeat #1027: feat_4h_dist_swing_low is also allowed to downgrade when the broader
    # 4H support cluster compresses coherently (raw price + raw volatility + sibling support
    # distances / BB position). This avoids treating a healthy support squeeze as an isolated
    # swing-low projection failure.
    # Heartbeat #1028: feat_4h_dist_bb_lower follows the same logic. When lower-band distance
    # compression occurs together with raw price/volatility and sibling 4H support proxies,
    # treat it as coherent band-floor compression instead of a standalone projection blocker.
    return {
        "reason": str(rule.get("reason") or "expected_underlying_compression"),
        "proxy_cols": list(proxy_cols),
        "compressed_proxy_count": compressed_proxy_count,
        "min_required_proxies": min_required,
        "proxy_stats": proxy_stats,
    }



def _expected_compressed_reason(
    feature_col: str,
    current_rows: list[sqlite3.Row],
    baseline_feature_stats: dict[str, dict[str, Any]],
) -> str | None:
    details = _expected_compressed_details(feature_col, current_rows, baseline_feature_stats)
    if not details:
        return None
    return str(details.get("reason") or "expected_underlying_compression")


def _overlay_only_reason(feature_col: str) -> str | None:
    clean_key = FEATURE_KEY_MAP.get(feature_col)
    if clean_key in SOURCE_FEATURE_KEYS:
        return "research_sparse_source"
    return None


def _feature_stats(rows: list[sqlite3.Row], feature_col: str) -> dict[str, Any]:
    values = [_safe_float(r[feature_col]) for r in rows]
    numeric_values = [v for v in values if v is not None]
    if not values:
        return {
            "non_null": 0,
            "non_null_ratio": None,
            "distinct": 0,
            "std": None,
            "range": None,
            "mean": None,
        }
    distinct = len({round(v, 8) for v in numeric_values})
    std = pstdev(numeric_values) if len(numeric_values) >= 2 else (0.0 if numeric_values else None)
    value_range = (max(numeric_values) - min(numeric_values)) if numeric_values else None
    mean = (sum(numeric_values) / len(numeric_values)) if numeric_values else None
    return {
        "non_null": len(numeric_values),
        "non_null_ratio": len(numeric_values) / len(values),
        "distinct": distinct,
        "std": std,
        "range": value_range,
        "mean": mean,
    }


def _feature_name_set(rows: list[dict[str, Any]]) -> set[str]:
    return {str(row.get("feature")) for row in rows if row.get("feature")}


def _compute_feature_shift_examples(
    current_rows: list[sqlite3.Row],
    reference_rows: list[sqlite3.Row],
    feature_cols: list[str],
    baseline_feature_stats: dict[str, dict[str, Any]],
    limit: int = FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT,
) -> list[dict[str, Any]]:
    shifts: list[dict[str, Any]] = []
    for feature_col in feature_cols:
        current_stats = _feature_stats(current_rows, feature_col)
        reference_stats = _feature_stats(reference_rows, feature_col)
        current_mean = current_stats.get("mean")
        reference_mean = reference_stats.get("mean")
        if current_mean is None or reference_mean is None:
            continue
        delta = current_mean - reference_mean
        baseline_std = baseline_feature_stats.get(feature_col, {}).get("std")
        delta_vs_baseline_std = None
        if isinstance(baseline_std, (int, float)) and baseline_std > 0:
            delta_vs_baseline_std = abs(delta) / baseline_std
        overlay_only_reason = _overlay_only_reason(feature_col)
        shifts.append(
            {
                "feature": feature_col,
                "current_mean": _round(current_mean),
                "reference_mean": _round(reference_mean),
                "mean_delta": _round(delta),
                "delta_vs_baseline_std": _round(delta_vs_baseline_std),
                "overlay_only_reason": overlay_only_reason,
            }
        )
    shifts.sort(
        key=lambda row: (
            row.get("overlay_only_reason") is not None,
            row.get("delta_vs_baseline_std") is None,
            -(row.get("delta_vs_baseline_std") or 0.0),
            -(abs(row.get("mean_delta") or 0.0)),
            row["feature"],
        )
    )
    non_overlay_shifts = [row for row in shifts if not row.get("overlay_only_reason")]
    if non_overlay_shifts:
        return non_overlay_shifts[:limit]
    return shifts[:limit]


def _compute_feature_diagnostics(
    rows: list[sqlite3.Row],
    feature_cols: list[str],
    baseline_feature_stats: dict[str, dict[str, Any]],
    window_context: dict[str, Any],
) -> dict[str, Any]:
    if not rows or not feature_cols:
        return {
            "feature_count": len(feature_cols),
            "window_rows": len(rows),
            "low_variance_count": 0,
            "low_distinct_count": 0,
            "null_heavy_count": 0,
            "low_variance_examples": [],
            "low_distinct_examples": [],
            "null_heavy_examples": [],
        }

    low_variance_examples: list[dict[str, Any]] = []
    low_distinct_examples: list[dict[str, Any]] = []
    null_heavy_examples: list[dict[str, Any]] = []
    low_variance_map: dict[str, dict[str, Any]] = {}
    low_distinct_map: dict[str, dict[str, Any]] = {}

    for feature_col in feature_cols:
        recent_stats = _feature_stats(rows, feature_col)
        baseline_stats = baseline_feature_stats.get(feature_col) or {}
        recent_std = recent_stats.get("std")
        baseline_std = baseline_stats.get("std")
        recent_distinct = recent_stats.get("distinct") or 0
        baseline_distinct = baseline_stats.get("distinct") or 0
        non_null_ratio = recent_stats.get("non_null_ratio")

        std_ratio = None
        if isinstance(recent_std, (int, float)) and isinstance(baseline_std, (int, float)):
            if baseline_std > 0:
                std_ratio = recent_std / baseline_std
            elif recent_std == 0:
                std_ratio = 0.0

        distinct_ratio = None
        if baseline_distinct > 0:
            distinct_ratio = recent_distinct / baseline_distinct

        if non_null_ratio is not None and non_null_ratio < NULL_HEAVY_NON_NULL_RATIO_THRESHOLD:
            null_heavy_examples.append(
                {
                    "feature": feature_col,
                    "non_null_ratio": _round(non_null_ratio),
                    "non_null": recent_stats.get("non_null"),
                    "window_rows": len(rows),
                }
            )

        expected_static_reason = _expected_static_reason(feature_col, window_context)
        expected_compressed_details = _expected_compressed_details(feature_col, rows, baseline_feature_stats)
        expected_compressed_reason = (
            str(expected_compressed_details.get("reason")) if expected_compressed_details else None
        )
        overlay_only_reason = _overlay_only_reason(feature_col)

        if std_ratio is not None and std_ratio <= LOW_VARIANCE_STD_RATIO_THRESHOLD:
            row = {
                "feature": feature_col,
                "recent_std": _round(recent_std),
                "baseline_std": _round(baseline_std),
                "std_ratio": _round(std_ratio),
                "recent_range": _round(recent_stats.get("range")),
                "baseline_range": _round(baseline_stats.get("range")),
                "recent_distinct": recent_distinct,
                "baseline_distinct": baseline_distinct,
                "distinct_ratio": _round(distinct_ratio),
                "expected_static_reason": expected_static_reason,
                "expected_compressed_reason": expected_compressed_reason,
                "expected_compressed_details": expected_compressed_details,
                "overlay_only_reason": overlay_only_reason,
            }
            low_variance_examples.append(row)
            low_variance_map[feature_col] = row

        is_low_distinct = recent_distinct <= LOW_DISTINCT_MAX_COUNT and (
            recent_distinct <= 1
            or (distinct_ratio is not None and distinct_ratio <= LOW_DISTINCT_RATIO_THRESHOLD)
        )
        if is_low_distinct:
            row = {
                "feature": feature_col,
                "recent_distinct": recent_distinct,
                "baseline_distinct": baseline_distinct,
                "distinct_ratio": _round(distinct_ratio),
                "recent_std": _round(recent_std),
                "baseline_std": _round(baseline_std),
                "std_ratio": _round(std_ratio),
                "expected_static_reason": expected_static_reason,
                "expected_compressed_reason": expected_compressed_reason,
                "expected_compressed_details": expected_compressed_details,
                "overlay_only_reason": overlay_only_reason,
            }
            low_distinct_examples.append(row)
            low_distinct_map[feature_col] = row

    frozen_examples = [
        {
            **low_variance_map[feature],
            "recent_distinct": low_distinct_map[feature].get("recent_distinct"),
            "baseline_distinct": low_distinct_map[feature].get("baseline_distinct"),
            "distinct_ratio": low_distinct_map[feature].get("distinct_ratio"),
            "expected_static_reason": low_distinct_map[feature].get("expected_static_reason") or low_variance_map[feature].get("expected_static_reason"),
            "overlay_only_reason": low_distinct_map[feature].get("overlay_only_reason") or low_variance_map[feature].get("overlay_only_reason"),
        }
        for feature in sorted(set(low_variance_map) & set(low_distinct_map))
    ]
    compressed_examples = [
        row
        for row in low_variance_examples
        if row["feature"] not in low_distinct_map
    ]
    expected_static_examples = [
        row for row in (frozen_examples + compressed_examples) if row.get("expected_static_reason")
    ]
    expected_compressed_examples = [
        row for row in compressed_examples if row.get("expected_compressed_reason")
    ]
    overlay_only_examples = [
        row for row in (frozen_examples + compressed_examples) if row.get("overlay_only_reason")
    ]
    unexpected_frozen_examples = [
        row for row in frozen_examples if not row.get("expected_static_reason") and not row.get("overlay_only_reason")
    ]
    unexpected_compressed_examples = [
        row
        for row in compressed_examples
        if not row.get("expected_static_reason")
        and not row.get("expected_compressed_reason")
        and not row.get("overlay_only_reason")
    ]

    low_variance_examples.sort(key=lambda row: (row.get("std_ratio") is None, row.get("std_ratio", 1e9), row["feature"]))
    low_distinct_examples.sort(key=lambda row: (row.get("distinct_ratio") is None, row.get("distinct_ratio", 1e9), row["feature"]))
    frozen_examples.sort(key=lambda row: (row.get("std_ratio") is None, row.get("std_ratio", 1e9), row["feature"]))
    compressed_examples.sort(key=lambda row: (row.get("std_ratio") is None, row.get("std_ratio", 1e9), row["feature"]))
    expected_static_examples.sort(key=lambda row: (row.get("expected_static_reason") or "", row["feature"]))
    expected_compressed_examples.sort(key=lambda row: (row.get("expected_compressed_reason") or "", row["feature"]))
    overlay_only_examples.sort(key=lambda row: (row.get("overlay_only_reason") or "", row["feature"]))
    unexpected_frozen_examples.sort(key=lambda row: (row.get("std_ratio") is None, row.get("std_ratio", 1e9), row["feature"]))
    unexpected_compressed_examples.sort(key=lambda row: (row.get("std_ratio") is None, row.get("std_ratio", 1e9), row["feature"]))
    null_heavy_examples.sort(key=lambda row: (row.get("non_null_ratio") is None, row.get("non_null_ratio", 1e9), row["feature"]))

    return {
        "feature_count": len(feature_cols),
        "window_rows": len(rows),
        "time_context": window_context,
        "low_variance_count": len(low_variance_examples),
        "low_distinct_count": len(low_distinct_examples),
        "frozen_count": len(frozen_examples),
        "compressed_count": len(compressed_examples),
        "expected_static_count": len(expected_static_examples),
        "expected_compressed_count": len(expected_compressed_examples),
        "overlay_only_count": len(overlay_only_examples),
        "unexpected_frozen_count": len(unexpected_frozen_examples),
        "unexpected_compressed_count": len(unexpected_compressed_examples),
        "null_heavy_count": len(null_heavy_examples),
        "low_variance_examples": low_variance_examples[:FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT],
        "low_distinct_examples": low_distinct_examples[:FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT],
        "frozen_examples": frozen_examples[:FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT],
        "compressed_examples": compressed_examples[:FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT],
        "expected_static_examples": expected_static_examples[:FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT],
        "expected_compressed_examples": expected_compressed_examples[:FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT],
        "overlay_only_examples": overlay_only_examples[:FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT],
        "unexpected_frozen_examples": unexpected_frozen_examples[:FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT],
        "unexpected_compressed_examples": unexpected_compressed_examples[:FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT],
        "null_heavy_examples": null_heavy_examples[:FEATURE_DIAGNOSTIC_EXAMPLE_LIMIT],
    }


def _target_path_examples(rows: list[sqlite3.Row], limit: int = TARGET_PATH_EXAMPLE_LIMIT) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for row in rows[-limit:]:
        examples.append(
            {
                "label_id": row["label_id"],
                "timestamp": row["timestamp"],
                "symbol": row["symbol"],
                "target": int(row["target"]),
                "regime": row["regime"] or "unknown",
                "spot_long_win": _round(_safe_float(row["spot_long_win"])),
                "simulated_pyramid_pnl": _round(_safe_float(row["simulated_pyramid_pnl"])),
                "simulated_pyramid_quality": _round(_safe_float(row["simulated_pyramid_quality"])),
                "simulated_pyramid_drawdown_penalty": _round(_safe_float(row["simulated_pyramid_drawdown_penalty"])),
                "simulated_pyramid_time_underwater": _round(_safe_float(row["simulated_pyramid_time_underwater"])),
                "future_return_pct": _round(_safe_float(row["future_return_pct"])),
                "future_max_drawdown": _round(_safe_float(row["future_max_drawdown"])),
                "future_max_runup": _round(_safe_float(row["future_max_runup"])),
            }
        )
    return examples


def _summarize_target_streak(streak_rows: list[sqlite3.Row]) -> dict[str, Any]:
    if not streak_rows:
        return {
            "target": None,
            "count": 0,
            "start_timestamp": None,
            "end_timestamp": None,
            "regime_counts": {},
            "examples": [],
        }

    regime_counts = Counter((row["regime"] or "unknown") for row in streak_rows)
    return {
        "target": int(streak_rows[0]["target"]),
        "count": len(streak_rows),
        "start_timestamp": streak_rows[0]["timestamp"],
        "end_timestamp": streak_rows[-1]["timestamp"],
        "regime_counts": _counter_to_dict(regime_counts),
        "examples": _target_path_examples(streak_rows, limit=min(3, TARGET_PATH_EXAMPLE_LIMIT)),
    }


def _tail_target_streak(rows: list[sqlite3.Row]) -> dict[str, Any]:
    if not rows:
        return _summarize_target_streak([])

    latest_target = int(rows[-1]["target"])
    streak_rows: list[sqlite3.Row] = []
    for row in reversed(rows):
        if int(row["target"]) != latest_target:
            break
        streak_rows.append(row)
    streak_rows.reverse()
    return _summarize_target_streak(streak_rows)


def _longest_target_streak(rows: list[sqlite3.Row], target_value: int | None = None) -> dict[str, Any]:
    if not rows:
        return _summarize_target_streak([])

    best_rows: list[sqlite3.Row] = []
    current_rows: list[sqlite3.Row] = []
    current_target: int | None = None
    for row in rows:
        row_target = int(row["target"])
        if current_rows and row_target != current_target:
            if (target_value is None or current_target == target_value) and (
                len(current_rows) > len(best_rows)
                or (len(current_rows) == len(best_rows) and current_rows[-1]["timestamp"] > (best_rows[-1]["timestamp"] if best_rows else ""))
            ):
                best_rows = list(current_rows)
            current_rows = []
        if not current_rows:
            current_target = row_target
        current_rows.append(row)

    if current_rows and (target_value is None or current_target == target_value) and (
        len(current_rows) > len(best_rows)
        or (len(current_rows) == len(best_rows) and current_rows[-1]["timestamp"] > (best_rows[-1]["timestamp"] if best_rows else ""))
    ):
        best_rows = list(current_rows)

    return _summarize_target_streak(best_rows)


def _target_path_diagnostics(rows: list[sqlite3.Row]) -> dict[str, Any]:
    if not rows:
        return {
            "window_start_timestamp": None,
            "window_end_timestamp": None,
            "latest_target": None,
            "tail_target_streak": {},
            "longest_target_streak": {},
            "longest_zero_target_streak": {},
            "longest_one_target_streak": {},
            "target_regime_breakdown": {},
            "recent_examples": [],
        }

    target_regime_breakdown = Counter(
        f"{row['regime'] or 'unknown'}:{int(row['target'])}"
        for row in rows
    )
    return {
        "window_start_timestamp": rows[0]["timestamp"],
        "window_end_timestamp": rows[-1]["timestamp"],
        "latest_target": int(rows[-1]["target"]),
        "tail_target_streak": _tail_target_streak(rows),
        "longest_target_streak": _longest_target_streak(rows),
        "longest_zero_target_streak": _longest_target_streak(rows, target_value=0),
        "longest_one_target_streak": _longest_target_streak(rows, target_value=1),
        "target_regime_breakdown": _counter_to_dict(target_regime_breakdown),
        "recent_examples": _target_path_examples(rows),
    }


def _select_adverse_target_streak(path_diag: dict[str, Any] | None) -> dict[str, Any]:
    streak = dict((path_diag or {}).get("longest_zero_target_streak") or {})
    if streak.get("target") is None:
        streak["target"] = 0
    streak.setdefault("count", 0)
    streak.setdefault("start_timestamp", None)
    streak.setdefault("end_timestamp", None)
    streak.setdefault("examples", [])
    return streak


def _format_streak_text(name: str, streak: dict[str, Any] | None, *, default_target: int | None = None) -> str:
    streak = dict(streak or {})
    target = streak.get("target")
    if target is None:
        target = default_target
    count = int(streak.get("count") or 0)
    target_text = "n/a" if target is None else str(target)
    start = streak.get("start_timestamp")
    end = streak.get("end_timestamp")
    text = f"{name}={count}x{target_text}"
    if start and end:
        text += f" since {start} -> {end}"
    return text


def _classify_window(alerts: list[str], metrics: dict[str, Any]) -> str:
    """Distinguish truly suspicious drift from an extreme-but-supported trend pocket.

    Constant-target recent windows are dangerous for calibration even when they are real.
    However, Heartbeat #668 found that some 100% win windows are backed by strong path
    quality (positive pnl, low drawdown, low time-underwater), so governance should not
    automatically describe every such slice as label corruption.
    """
    win_rate = metrics.get("simulated_win_rate")
    avg_pnl = metrics.get("avg_simulated_pnl")
    avg_quality = metrics.get("avg_simulated_quality")
    avg_dd_penalty = metrics.get("avg_drawdown_penalty")
    avg_tuw = metrics.get("avg_time_underwater")

    # Canonical classification must be driven by canonical pyramid outcomes first.
    # `spot_long_win_rate` is still useful as a comparison diagnostic, but it is a
    # legacy/path-aware target and must not veto a clearly healthy canonical pocket.
    # Heartbeat #686 showed that recent canonical pockets can still be genuinely
    # healthy even when time-underwater drifts slightly above the original 0.45
    # cutoff. Treat near-threshold TUW as acceptable if the rest of the canonical
    # quality profile is clearly strong (high win/pnl/quality, low drawdown).
    tuw_supported = (
        isinstance(avg_tuw, (int, float))
        and (
            avg_tuw <= 0.45
            or (
                avg_tuw <= 0.55
                and isinstance(avg_dd_penalty, (int, float)) and avg_dd_penalty <= 0.08
                and isinstance(avg_quality, (int, float)) and avg_quality >= 0.60
            )
        )
    )
    strong_positive_extreme = (
        any(alert in alerts for alert in ("constant_target", "label_imbalance"))
        and isinstance(win_rate, (int, float)) and win_rate >= 0.95
        and isinstance(avg_pnl, (int, float)) and avg_pnl >= 0.01
        and isinstance(avg_quality, (int, float)) and avg_quality >= 0.55
        and isinstance(avg_dd_penalty, (int, float)) and avg_dd_penalty <= 0.20
        and tuw_supported
    )
    # Heartbeat #20260422c: non-constant label-imbalance windows can still be a
    # healthy canonical extreme-trend pocket even when win_rate is below the old
    # 95% cutoff. Keep the classifier conservative by requiring strong positive pnl,
    # quality, and especially low drawdown before downgrading such slices away from
    # distribution_pathology.
    robust_positive_label_imbalance = (
        "label_imbalance" in alerts
        and isinstance(win_rate, (int, float)) and win_rate >= 0.85
        and isinstance(avg_pnl, (int, float)) and avg_pnl >= 0.01
        and isinstance(avg_quality, (int, float)) and avg_quality >= 0.50
        and isinstance(avg_dd_penalty, (int, float)) and avg_dd_penalty <= 0.10
        and tuw_supported
    )
    if strong_positive_extreme or robust_positive_label_imbalance:
        return "supported_extreme_trend"

    if "constant_target" in alerts or "label_imbalance" in alerts:
        return "distribution_pathology"
    if "regime_concentration" in alerts or "regime_shift" in alerts:
        return "regime_concentration"
    return "healthy"


def _reference_window_comparison(
    rows: list[sqlite3.Row],
    reference_rows: list[sqlite3.Row],
    feature_cols: list[str],
    baseline_feature_stats: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not rows or not reference_rows:
        return {}

    current_regimes = Counter((r["regime"] or "unknown") for r in rows)
    reference_regimes = Counter((r["regime"] or "unknown") for r in reference_rows)
    current_total = len(rows)
    reference_total = len(reference_rows)
    current_quality = {
        "win_rate": _round(sum(int(r["target"]) for r in rows) / current_total) if current_total else None,
        "spot_long_win_rate": _avg(rows, "spot_long_win"),
        "avg_simulated_pnl": _avg(rows, "simulated_pyramid_pnl"),
        "avg_simulated_quality": _avg(rows, "simulated_pyramid_quality"),
        "avg_drawdown_penalty": _avg(rows, "simulated_pyramid_drawdown_penalty"),
        "avg_time_underwater": _avg(rows, "simulated_pyramid_time_underwater"),
    }
    reference_quality = {
        "win_rate": _round(sum(int(r["target"]) for r in reference_rows) / reference_total) if reference_total else None,
        "spot_long_win_rate": _avg(reference_rows, "spot_long_win"),
        "avg_simulated_pnl": _avg(reference_rows, "simulated_pyramid_pnl"),
        "avg_simulated_quality": _avg(reference_rows, "simulated_pyramid_quality"),
        "avg_drawdown_penalty": _avg(reference_rows, "simulated_pyramid_drawdown_penalty"),
        "avg_time_underwater": _avg(reference_rows, "simulated_pyramid_time_underwater"),
    }
    current_time_context = _window_time_context(rows)
    reference_time_context = _window_time_context(reference_rows)
    current_diag = _compute_feature_diagnostics(rows, feature_cols, baseline_feature_stats, current_time_context)
    reference_diag = _compute_feature_diagnostics(reference_rows, feature_cols, baseline_feature_stats, reference_time_context)

    current_unexpected_frozen = _feature_name_set(current_diag.get("unexpected_frozen_examples") or [])
    reference_unexpected_frozen = _feature_name_set(reference_diag.get("unexpected_frozen_examples") or [])
    current_unexpected_compressed = _feature_name_set(current_diag.get("unexpected_compressed_examples") or [])
    reference_unexpected_compressed = _feature_name_set(reference_diag.get("unexpected_compressed_examples") or [])
    current_null_heavy = _feature_name_set(current_diag.get("null_heavy_examples") or [])
    reference_null_heavy = _feature_name_set(reference_diag.get("null_heavy_examples") or [])

    regime_share_deltas = {}
    for regime in sorted(set(current_regimes) | set(reference_regimes)):
        current_share = (current_regimes.get(regime, 0) / current_total) if current_total else None
        reference_share = (reference_regimes.get(regime, 0) / reference_total) if reference_total else None
        regime_share_deltas[regime] = {
            "current_share": _round(current_share),
            "reference_share": _round(reference_share),
            "share_delta": _round((current_share or 0.0) - (reference_share or 0.0)),
        }

    def _delta(current_value: float | None, reference_value: float | None) -> float | None:
        if current_value is None or reference_value is None:
            return None
        return _round(current_value - reference_value)

    return {
        "current_rows": current_total,
        "reference_rows": reference_total,
        "current_start_timestamp": rows[0]["timestamp"],
        "current_end_timestamp": rows[-1]["timestamp"],
        "reference_start_timestamp": reference_rows[0]["timestamp"],
        "reference_end_timestamp": reference_rows[-1]["timestamp"],
        "current_quality": current_quality,
        "reference_quality": reference_quality,
        "win_rate_delta_vs_reference": _delta(current_quality.get("win_rate"), reference_quality.get("win_rate")),
        "spot_long_win_rate_delta_vs_reference": _delta(current_quality.get("spot_long_win_rate"), reference_quality.get("spot_long_win_rate")),
        "avg_simulated_pnl_delta_vs_reference": _delta(current_quality.get("avg_simulated_pnl"), reference_quality.get("avg_simulated_pnl")),
        "avg_simulated_quality_delta_vs_reference": _delta(current_quality.get("avg_simulated_quality"), reference_quality.get("avg_simulated_quality")),
        "avg_drawdown_penalty_delta_vs_reference": _delta(current_quality.get("avg_drawdown_penalty"), reference_quality.get("avg_drawdown_penalty")),
        "avg_time_underwater_delta_vs_reference": _delta(current_quality.get("avg_time_underwater"), reference_quality.get("avg_time_underwater")),
        "current_dominant_regime": max(current_regimes, key=current_regimes.get) if current_regimes else None,
        "reference_dominant_regime": max(reference_regimes, key=reference_regimes.get) if reference_regimes else None,
        "regime_share_deltas": regime_share_deltas,
        "new_unexpected_frozen_features": sorted(current_unexpected_frozen - reference_unexpected_frozen),
        "new_unexpected_compressed_features": sorted(current_unexpected_compressed - reference_unexpected_compressed),
        "new_null_heavy_features": sorted(current_null_heavy - reference_null_heavy),
        "top_mean_shift_features": _compute_feature_shift_examples(rows, reference_rows, feature_cols, baseline_feature_stats),
    }


def _compact_window_summary(
    *,
    window_rows: int,
    alerts: list[str],
    interpretation: str,
    win_rate: float | None,
    dominant_regime: str | None,
    dominant_share: float | None,
    quality_metrics: dict[str, Any],
    target_path_diagnostics: dict[str, Any],
    reference_comparison: dict[str, Any],
) -> dict[str, Any]:
    avg_pnl = _safe_float(quality_metrics.get("avg_simulated_pnl"))
    avg_quality = _safe_float(quality_metrics.get("avg_simulated_quality"))
    avg_dd_penalty = _safe_float(quality_metrics.get("avg_drawdown_penalty"))
    tail_streak = target_path_diagnostics.get("tail_target_streak") or {}
    adverse_streak = _select_adverse_target_streak(target_path_diagnostics)
    adverse_count = int(adverse_streak.get("count") or 0)
    positive_quality = bool(
        isinstance(win_rate, (int, float))
        and win_rate >= 0.5
        and isinstance(avg_quality, float)
        and avg_quality > 0
        and (avg_pnl is None or avg_pnl >= 0)
    )

    if positive_quality and any(alert in alerts for alert in ("label_imbalance", "constant_target", "regime_concentration")):
        severity = "medium"
        action_summary = "distribution concentration with adverse tail risk; canonical quality remains positive"
    elif "constant_target" in alerts or adverse_count >= 20 or (avg_quality is not None and avg_quality <= 0) or (avg_pnl is not None and avg_pnl < 0):
        severity = "high"
        action_summary = "negative distribution pathology requires current-window validation"
    elif alerts:
        severity = "medium"
        action_summary = "distribution concentration needs monitoring"
    else:
        severity = "low"
        action_summary = "no actionable recent distribution pathology"

    top_shift = [
        row.get("feature")
        for row in (reference_comparison.get("top_mean_shift_features") or [])[:5]
        if row.get("feature")
    ]
    return {
        "window": window_rows,
        "alerts": list(alerts),
        "severity": severity,
        "interpretation": interpretation,
        "win_rate": _round(win_rate),
        "avg_quality": _round(avg_quality),
        "avg_pnl": _round(avg_pnl),
        "avg_drawdown_penalty": _round(avg_dd_penalty),
        "dominant_regime": dominant_regime,
        "dominant_regime_share": _round(dominant_share),
        "tail_streak": {
            "target": tail_streak.get("target"),
            "count": int(tail_streak.get("count") or 0),
            "start_timestamp": tail_streak.get("start_timestamp"),
            "end_timestamp": tail_streak.get("end_timestamp"),
        },
        "adverse_streak": {
            "target": adverse_streak.get("target"),
            "count": adverse_count,
            "start_timestamp": adverse_streak.get("start_timestamp"),
            "end_timestamp": adverse_streak.get("end_timestamp"),
        },
        "top_shift_features": top_shift,
        "actionable_summary": action_summary,
    }


def _window_summary(
    rows: list[sqlite3.Row],
    baseline_win_rate: float,
    baseline_regimes: Counter,
    feature_cols: list[str],
    baseline_feature_stats: dict[str, dict[str, Any]],
    reference_rows: list[sqlite3.Row] | None = None,
) -> dict[str, Any]:
    total = len(rows)
    wins = sum(int(r["target"]) for r in rows)
    losses = total - wins
    regime_counts = Counter((r["regime"] or "unknown") for r in rows)
    dominant_regime, dominant_count = regime_counts.most_common(1)[0] if regime_counts else (None, 0)
    win_rate = wins / total if total else None
    unique_targets = sorted({int(r["target"]) for r in rows}) if rows else []
    dominant_share = dominant_count / total if total else None
    baseline_dominant_share = (baseline_regimes.get(dominant_regime, 0) / sum(baseline_regimes.values())) if total and dominant_regime else 0.0

    alerts = []
    if len(unique_targets) <= 1:
        alerts.append("constant_target")
    elif win_rate is not None and (win_rate >= 0.8 or win_rate <= 0.2):
        alerts.append("label_imbalance")
    if dominant_share is not None and dominant_share >= 0.9:
        alerts.append("regime_concentration")
    if dominant_share is not None and baseline_dominant_share is not None and dominant_share - baseline_dominant_share >= 0.2:
        alerts.append("regime_shift")

    quality_metrics = {
        "simulated_win_rate": _round(win_rate),
        "spot_long_win_rate": _avg(rows, "spot_long_win"),
        "avg_simulated_pnl": _avg(rows, "simulated_pyramid_pnl"),
        "avg_simulated_quality": _avg(rows, "simulated_pyramid_quality"),
        "avg_drawdown_penalty": _avg(rows, "simulated_pyramid_drawdown_penalty"),
        "avg_time_underwater": _avg(rows, "simulated_pyramid_time_underwater"),
        "avg_future_return_pct": _avg(rows, "future_return_pct"),
        "avg_future_max_runup": _avg(rows, "future_max_runup"),
        "avg_future_max_drawdown": _avg(rows, "future_max_drawdown"),
    }
    window_time_context = _window_time_context(rows)
    feature_diagnostics = _compute_feature_diagnostics(rows, feature_cols, baseline_feature_stats, window_time_context)
    target_path_diagnostics = _target_path_diagnostics(rows)
    interpretation = _classify_window(alerts, quality_metrics)

    reference_comparison = {}
    if reference_rows:
        reference_comparison = _reference_window_comparison(rows, reference_rows, feature_cols, baseline_feature_stats)
    compact_summary = _compact_window_summary(
        window_rows=total,
        alerts=alerts,
        interpretation=interpretation,
        win_rate=_round(win_rate),
        dominant_regime=dominant_regime,
        dominant_share=_round(dominant_share),
        quality_metrics=quality_metrics,
        target_path_diagnostics=target_path_diagnostics,
        reference_comparison=reference_comparison,
    )

    return {
        "rows": total,
        "wins": wins,
        "losses": losses,
        "win_rate": _round(win_rate),
        "win_rate_delta_vs_full": _round((win_rate - baseline_win_rate) if win_rate is not None else None),
        "unique_targets": unique_targets,
        "constant_target": len(unique_targets) <= 1,
        "dominant_regime": dominant_regime,
        "dominant_regime_share": _round(dominant_share),
        "dominant_regime_delta_vs_full": _round((dominant_share - baseline_dominant_share) if dominant_share is not None else None),
        "regime_counts": _counter_to_dict(regime_counts),
        "regime_pct": {k: _pct(v, total) for k, v in _counter_to_dict(regime_counts).items()},
        "quality_metrics": quality_metrics,
        "feature_diagnostics": feature_diagnostics,
        "target_path_diagnostics": target_path_diagnostics,
        "reference_window_comparison": reference_comparison,
        "compact_summary": compact_summary,
        "drift_interpretation": interpretation,
        "alerts": alerts,
    }


def _find_primary_window(window_summaries: dict[str, dict[str, Any]]) -> tuple[str | None, dict[str, Any] | None]:
    def score(item: tuple[str, dict[str, Any]]) -> tuple[int, float, int]:
        _, summary = item
        severity = _alert_severity(summary.get("alerts", []))
        delta = abs(summary.get("win_rate_delta_vs_full") or 0.0)
        rows = int(summary.get("rows") or 0)
        return (severity, delta, rows)

    if not window_summaries:
        return None, None
    label, summary = max(window_summaries.items(), key=score)
    return label, summary


def _alert_severity(alerts: list[str] | tuple[str, ...] | None) -> int:
    alerts = list(alerts or [])
    severity = 0
    if "constant_target" in alerts:
        severity += 4
    if "label_imbalance" in alerts:
        severity += 3
    if "regime_concentration" in alerts:
        severity += 2
    if "regime_shift" in alerts:
        severity += 1
    return severity


def _is_negative_blocking_window(summary: dict[str, Any]) -> bool:
    interpretation = summary.get("drift_interpretation")
    if interpretation not in {"distribution_pathology", "regime_concentration"}:
        return False
    quality = summary.get("quality_metrics") or {}
    win_rate = _safe_float(summary.get("win_rate"))
    avg_pnl = _safe_float(quality.get("avg_simulated_pnl"))
    avg_quality = _safe_float(quality.get("avg_simulated_quality"))
    spot_long_win = _safe_float(quality.get("spot_long_win_rate"))
    return any(
        [
            isinstance(win_rate, float) and win_rate <= 0.25,
            isinstance(avg_pnl, float) and avg_pnl <= 0.0,
            isinstance(avg_quality, float) and avg_quality <= 0.0,
            isinstance(spot_long_win, float) and spot_long_win <= 0.20,
        ]
    )


def _find_blocking_window(window_summaries: dict[str, dict[str, Any]]) -> tuple[str | None, dict[str, Any] | None]:
    def score(item: tuple[str, dict[str, Any]]) -> tuple[int, float, int]:
        _, summary = item
        quality = summary.get("quality_metrics") or {}
        win_rate = _safe_float(summary.get("win_rate")) or 0.5
        avg_pnl = _safe_float(quality.get("avg_simulated_pnl")) or 0.0
        avg_quality = _safe_float(quality.get("avg_simulated_quality")) or 0.0
        negativity = max(0.0, 0.5 - win_rate) + max(0.0, -avg_pnl) + max(0.0, -avg_quality)
        rows = int(summary.get("rows") or 0)
        return (_alert_severity(summary.get("alerts", [])), negativity, rows)

    candidates = [item for item in window_summaries.items() if _is_negative_blocking_window(item[1])]
    if not candidates:
        return None, None
    label, summary = max(candidates, key=score)
    return label, summary


def _row_target(row: sqlite3.Row) -> int | None:
    try:
        return int(row["target"])
    except (TypeError, ValueError, IndexError, KeyError):
        return None


def _mean_for_rows(rows: list[sqlite3.Row], key: str) -> float | None:
    vals = [_safe_float(row[key]) for row in rows if key in row.keys()]
    vals = [value for value in vals if value is not None]
    if not vals:
        return None
    return _round(sum(vals) / len(vals))


def _std_for_rows(rows: list[sqlite3.Row], key: str) -> float | None:
    vals = [_safe_float(row[key]) for row in rows if key in row.keys()]
    vals = [value for value in vals if value is not None]
    if len(vals) < 2:
        return None
    return _round(pstdev(vals))


def _count_loss_path_flags(loss_rows: list[sqlite3.Row]) -> dict[str, Any]:
    tp_miss = 0
    dd_breach = 0
    high_underwater = 0
    for row in loss_rows:
        max_runup = _safe_float(row["future_max_runup"])
        max_drawdown = _safe_float(row["future_max_drawdown"])
        drawdown_penalty = _safe_float(row["simulated_pyramid_drawdown_penalty"])
        underwater = _safe_float(row["simulated_pyramid_time_underwater"])
        if max_runup is not None and max_runup < DEFAULT_LONG_TP_PCT:
            tp_miss += 1
        if (
            (max_drawdown is not None and max_drawdown <= -DEFAULT_LONG_MAX_DD_PCT)
            or (drawdown_penalty is not None and drawdown_penalty >= 1.0)
        ):
            dd_breach += 1
        if underwater is not None and underwater >= HIGH_UNDERWATER_RATIO_THRESHOLD:
            high_underwater += 1

    total_losses = len(loss_rows)
    return {
        "losses": total_losses,
        "tp_miss_count": tp_miss,
        "tp_miss_share": _pct(tp_miss, total_losses),
        "dd_breach_count": dd_breach,
        "dd_breach_share": _pct(dd_breach, total_losses),
        "high_underwater_count": high_underwater,
        "high_underwater_share": _pct(high_underwater, total_losses),
        "avg_time_underwater": _mean_for_rows(loss_rows, "simulated_pyramid_time_underwater"),
        "avg_future_max_runup": _mean_for_rows(loss_rows, "future_max_runup"),
        "avg_future_max_drawdown": _mean_for_rows(loss_rows, "future_max_drawdown"),
        "avg_simulated_pnl": _mean_for_rows(loss_rows, "simulated_pyramid_pnl"),
        "avg_simulated_quality": _mean_for_rows(loss_rows, "simulated_pyramid_quality"),
    }


def _regime_loss_breakdown(rows: list[sqlite3.Row]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    total_rows = len(rows)
    total_losses = sum(1 for row in rows if _row_target(row) == 0)
    for row in rows:
        regime = str(row["regime"] or "unknown")
        entry = buckets.setdefault(regime, {"rows": 0, "wins": 0, "losses": 0})
        entry["rows"] += 1
        if _row_target(row) == 0:
            entry["losses"] += 1
        elif _row_target(row) == 1:
            entry["wins"] += 1
    for entry in buckets.values():
        entry["row_share"] = _pct(entry["rows"], total_rows)
        entry["loss_rate"] = _pct(entry["losses"], entry["rows"])
        entry["share_of_losses"] = _pct(entry["losses"], total_losses)
    return dict(sorted(buckets.items(), key=lambda item: (-int(item[1].get("losses") or 0), item[0])))


def _feature_shift_for_tail_root_cause(
    *,
    loss_rows: list[sqlite3.Row],
    recent_win_rows: list[sqlite3.Row],
    reference_rows: list[sqlite3.Row],
    feature_cols: list[str],
) -> dict[str, Any]:
    available_features = [feature for feature in TAIL_ROOT_CAUSE_FEATURES if feature in feature_cols]
    loss_vs_reference: dict[str, dict[str, Any]] = {}
    loss_vs_recent_wins: dict[str, dict[str, Any]] = {}
    scored_features: list[tuple[float, str]] = []

    for feature in available_features:
        loss_mean = _mean_for_rows(loss_rows, feature)
        reference_mean = _mean_for_rows(reference_rows, feature)
        reference_std = _std_for_rows(reference_rows, feature)
        win_mean = _mean_for_rows(recent_win_rows, feature)
        reference_delta = None
        delta_vs_reference_std = None
        if loss_mean is not None and reference_mean is not None:
            reference_delta = _round(loss_mean - reference_mean)
            if reference_std not in (None, 0):
                delta_vs_reference_std = _round(reference_delta / reference_std)
        win_delta = None
        if loss_mean is not None and win_mean is not None:
            win_delta = _round(loss_mean - win_mean)

        loss_vs_reference[feature] = {
            "current_loss_mean": loss_mean,
            "reference_mean": reference_mean,
            "reference_std": reference_std,
            "mean_delta": reference_delta,
            "delta_vs_reference_std": delta_vs_reference_std,
        }
        loss_vs_recent_wins[feature] = {
            "loss_mean": loss_mean,
            "win_mean": win_mean,
            "mean_delta": win_delta,
        }
        score = abs(delta_vs_reference_std) if delta_vs_reference_std is not None else (abs(reference_delta) if reference_delta is not None else 0.0)
        if score > 0:
            scored_features.append((float(score), feature))

    top_features = [feature for _, feature in sorted(scored_features, key=lambda item: (-item[0], item[1]))[:5]]
    return {
        "loss_vs_reference": loss_vs_reference,
        "loss_vs_recent_wins": loss_vs_recent_wins,
        "top_4h_shift_features": top_features,
    }


def _build_canonical_tail_root_cause(
    rows: list[sqlite3.Row],
    feature_cols: list[str],
    *,
    generated_at: str,
    window: int = TAIL_ROOT_CAUSE_WINDOW,
) -> dict[str, Any]:
    recent_rows = rows[-window:] if len(rows) >= window else list(rows)
    reference_rows = rows[-(window * 2):-window] if len(rows) >= window * 2 else []
    loss_rows = [row for row in recent_rows if _row_target(row) == 0]
    win_rows = [row for row in recent_rows if _row_target(row) == 1]
    regime_breakdown = _regime_loss_breakdown(recent_rows)
    dominant_loss_regime = None
    if regime_breakdown:
        dominant_loss_regime = max(regime_breakdown.items(), key=lambda item: int(item[1].get("losses") or 0))[0]
    feature_shift = _feature_shift_for_tail_root_cause(
        loss_rows=loss_rows,
        recent_win_rows=win_rows,
        reference_rows=reference_rows,
        feature_cols=feature_cols,
    )
    path_breakdown = _count_loss_path_flags(loss_rows)
    top_features = feature_shift.get("top_4h_shift_features") or []
    key_findings: list[str] = []
    if dominant_loss_regime and loss_rows:
        share = (regime_breakdown.get(dominant_loss_regime) or {}).get("share_of_losses")
        key_findings.append(f"最近 {len(recent_rows)} 筆 canonical losses 主要集中在 {dominant_loss_regime}（loss share={share}）。")
    if loss_rows:
        key_findings.append(
            f"loss path：TP miss {path_breakdown['tp_miss_count']}/{len(loss_rows)}、"
            f"DD breach {path_breakdown['dd_breach_count']}/{len(loss_rows)}、"
            f"高 underwater {path_breakdown['high_underwater_count']}/{len(loss_rows)}。"
        )
    if top_features:
        key_findings.append(f"4H feature shift 以 {' / '.join(top_features[:3])} 最明顯。")

    examples = [
        {
            "timestamp": row["timestamp"],
            "regime": row["regime"],
            "future_max_runup": _round(_safe_float(row["future_max_runup"])),
            "future_max_drawdown": _round(_safe_float(row["future_max_drawdown"])),
            "time_underwater": _round(_safe_float(row["simulated_pyramid_time_underwater"])),
        }
        for row in loss_rows[-5:]
    ]

    return {
        "generated_at": generated_at,
        "target_col": TARGET_COL,
        "horizon_minutes": CANONICAL_HORIZON_MINUTES,
        "window": window,
        "rows": len(recent_rows),
        "wins": len(win_rows),
        "losses": len(loss_rows),
        "loss_rate": _pct(len(loss_rows), len(recent_rows)),
        "reference_rows": len(reference_rows),
        "thresholds": {
            "tp_pct": DEFAULT_LONG_TP_PCT,
            "max_dd_pct": DEFAULT_LONG_MAX_DD_PCT,
            "high_underwater_ratio": HIGH_UNDERWATER_RATIO_THRESHOLD,
        },
        "loss_path_breakdown": path_breakdown,
        "regime_breakdown": regime_breakdown,
        "dominant_loss_regime": dominant_loss_regime,
        "feature_shift": {
            "loss_vs_reference": feature_shift.get("loss_vs_reference") or {},
            "loss_vs_recent_wins": feature_shift.get("loss_vs_recent_wins") or {},
        },
        "top_4h_shift_features": top_features,
        "key_findings": key_findings,
        "recent_loss_examples": examples,
    }


def build_report() -> dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    feature_cols = [
        row[1]
        for row in conn.execute("PRAGMA table_info(features_normalized)").fetchall()
        if isinstance(row[1], str) and row[1].startswith("feat_")
    ]
    has_raw_market_data = _table_exists(conn, "raw_market_data")
    raw_market_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(raw_market_data)").fetchall()
        if has_raw_market_data and isinstance(row[1], str)
    }
    feature_select = ",\n            ".join(f"f.{col}" for col in feature_cols)
    feature_select_sql = f",\n            {feature_select}" if feature_select else ""
    raw_select_parts = []
    raw_select_parts.append(
        "r.volatility AS raw_volatility" if "volatility" in raw_market_cols else "NULL AS raw_volatility"
    )
    raw_select_parts.append(
        "r.close_price AS raw_close_price" if "close_price" in raw_market_cols else "NULL AS raw_close_price"
    )
    raw_select_sql = ",\n            " + ",\n            ".join(raw_select_parts)
    raw_join_sql = (
        "\n        LEFT JOIN raw_market_data r\n          ON r.timestamp = l.timestamp AND r.symbol = l.symbol"
        if has_raw_market_data else ""
    )
    rows = conn.execute(
        f"""
        SELECT
            l.id AS label_id,
            l.timestamp,
            l.symbol,
            l.{TARGET_COL} AS target,
            l.label_spot_long_win AS spot_long_win,
            l.simulated_pyramid_pnl,
            l.simulated_pyramid_quality,
            l.simulated_pyramid_drawdown_penalty,
            l.simulated_pyramid_time_underwater,
            l.future_return_pct,
            l.future_max_drawdown,
            l.future_max_runup,
            COALESCE(NULLIF(f.regime_label, ''), NULLIF(l.regime_label, ''), 'unknown') AS regime{feature_select_sql}{raw_select_sql}
        FROM labels l
        LEFT JOIN features_normalized f
          ON f.timestamp = l.timestamp AND f.symbol = l.symbol{raw_join_sql}
        WHERE l.horizon_minutes = ?
          AND l.{TARGET_COL} IS NOT NULL
        ORDER BY l.timestamp
        """,
        (CANONICAL_HORIZON_MINUTES,),
    ).fetchall()
    conn.close()

    total = len(rows)
    baseline_regimes = Counter((r["regime"] or "unknown") for r in rows)
    baseline_win_rate = (sum(int(r["target"]) for r in rows) / total) if total else 0.0
    diagnostic_cols = list(feature_cols)
    if has_raw_market_data:
        diagnostic_cols.extend(["raw_volatility", "raw_close_price"])
    baseline_feature_stats = {col: _feature_stats(rows, col) for col in diagnostic_cols}

    window_summaries: dict[str, dict[str, Any]] = {}
    for window in WINDOWS:
        if total < window:
            continue
        window_rows = rows[-window:]
        reference_rows = rows[-(window * 2):-window] if total >= window * 2 else []
        window_summaries[str(window)] = _window_summary(
            window_rows,
            baseline_win_rate,
            baseline_regimes,
            feature_cols,
            baseline_feature_stats,
            reference_rows=reference_rows,
        )

    primary_window, primary_summary = _find_primary_window(window_summaries)
    primary_alerts = list((primary_summary or {}).get("alerts", []))
    blocking_window, blocking_summary = _find_blocking_window(window_summaries)
    blocking_alerts = list((blocking_summary or {}).get("alerts", []))

    latest_label_timestamp = rows[-1]["timestamp"] if rows else None
    report = {
        "target_col": TARGET_COL,
        "horizon_minutes": CANONICAL_HORIZON_MINUTES,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_meta": {
            "label_rows": total,
            "latest_label_timestamp": latest_label_timestamp,
        },
        "full_sample": {
            "rows": total,
            "win_rate": _round(baseline_win_rate),
            "feature_count": len(feature_cols),
            "regime_counts": _counter_to_dict(baseline_regimes),
            "regime_pct": {k: _pct(v, total) for k, v in _counter_to_dict(baseline_regimes).items()},
        },
        "windows": window_summaries,
        "primary_window": {
            "window": primary_window,
            "alerts": primary_alerts,
            "summary": primary_summary or {},
        },
        "blocking_window": {
            "window": blocking_window,
            "alerts": blocking_alerts,
            "summary": blocking_summary or {},
        },
    }
    canonical_tail_root_cause = _build_canonical_tail_root_cause(
        rows,
        feature_cols,
        generated_at=report["generated_at"],
    )
    if canonical_tail_root_cause is not None:
        report["canonical_tail_root_cause"] = canonical_tail_root_cause
    return report


def main() -> int:
    report = build_report()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2, default=str))
    canonical_tail_root_cause = report.get("canonical_tail_root_cause")
    if isinstance(canonical_tail_root_cause, dict):
        TAIL_ROOT_CAUSE_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        TAIL_ROOT_CAUSE_OUT_PATH.write_text(json.dumps(canonical_tail_root_cause, indent=2, default=str))

    primary = report.get("primary_window", {})
    primary_window = primary.get("window")
    summary = primary.get("summary", {})
    alerts = primary.get("alerts", [])
    blocking = report.get("blocking_window", {})
    blocking_window = blocking.get("window")
    blocking_summary = blocking.get("summary", {})
    blocking_alerts = blocking.get("alerts", [])

    print("近期漂移報告")
    print("=" * 70)
    full = report["full_sample"]
    print(
        f"完整樣本：rows={full['rows']} win_rate={full['win_rate']:.4f} "
        f"feature_count={full.get('feature_count', 0)} regimes={full['regime_pct']}"
    )
    for window, row in report["windows"].items():
        quality = row.get("quality_metrics") or {}
        feature_diag = row.get("feature_diagnostics") or {}
        print(
            f"  最近 {window} 筆：win_rate={row['win_rate']:.4f} delta={row['win_rate_delta_vs_full']:+.4f} "
            f"dominant_regime={row['dominant_regime']} ({row['dominant_regime_share']:.2%}) alerts={row['alerts']} "
            f"interpretation={row.get('drift_interpretation')} avg_pnl={quality.get('avg_simulated_pnl')} "
            f"avg_quality={quality.get('avg_simulated_quality')} avg_dd_penalty={quality.get('avg_drawdown_penalty')} "
            f"feature_diag=variance:{feature_diag.get('low_variance_count', 0)}/{feature_diag.get('feature_count', 0)} "
            f"expected_static:{feature_diag.get('expected_static_count', 0)} "
            f"expected_compressed:{feature_diag.get('expected_compressed_count', 0)} "
            f"overlay_only:{feature_diag.get('overlay_only_count', 0)} "
            f"unexpected_frozen:{feature_diag.get('unexpected_frozen_count', 0)} "
            f"distinct:{feature_diag.get('low_distinct_count', 0)} null_heavy:{feature_diag.get('null_heavy_count', 0)}"
        )

    if primary_window:
        quality = summary.get("quality_metrics") or {}
        feature_diag = summary.get("feature_diagnostics") or {}
        path_diag = summary.get("target_path_diagnostics") or {}
        tail_streak = path_diag.get("tail_target_streak") or {}
        adverse_streak = _select_adverse_target_streak(path_diag)
        print(
            f"主要漂移視窗：最近 {primary_window} 筆 | win_rate={summary.get('win_rate', 0):.4f} "
            f"dominant_regime={summary.get('dominant_regime')} ({(summary.get('dominant_regime_share') or 0):.2%}) "
            f"alerts={alerts} interpretation={summary.get('drift_interpretation')} "
            f"avg_pnl={quality.get('avg_simulated_pnl')} avg_quality={quality.get('avg_simulated_quality')} "
            f"avg_dd_penalty={quality.get('avg_drawdown_penalty')} "
            f"feature_diag=variance:{feature_diag.get('low_variance_count', 0)}/{feature_diag.get('feature_count', 0)} "
            f"expected_static:{feature_diag.get('expected_static_count', 0)} "
            f"expected_compressed:{feature_diag.get('expected_compressed_count', 0)} "
            f"overlay_only:{feature_diag.get('overlay_only_count', 0)} "
            f"unexpected_frozen:{feature_diag.get('unexpected_frozen_count', 0)} "
            f"distinct:{feature_diag.get('low_distinct_count', 0)} null_heavy:{feature_diag.get('null_heavy_count', 0)} "
            f"{_format_streak_text('tail_streak', tail_streak)} "
            f"{_format_streak_text('adverse_streak', adverse_streak, default_target=0)}"
        )
        reference = summary.get("reference_window_comparison") or {}
        if reference:
            print(
                "  ↳ sibling-window contrast: "
                f"prev_win_rate={reference.get('reference_quality', {}).get('win_rate')} "
                f"vs current={reference.get('current_quality', {}).get('win_rate')} "
                f"(Δ={reference.get('win_rate_delta_vs_reference')}), "
                f"prev_quality={reference.get('reference_quality', {}).get('avg_simulated_quality')} "
                f"vs current={reference.get('current_quality', {}).get('avg_simulated_quality')} "
                f"(Δ={reference.get('avg_simulated_quality_delta_vs_reference')}), "
                f"prev_pnl={reference.get('reference_quality', {}).get('avg_simulated_pnl')} "
                f"vs current={reference.get('current_quality', {}).get('avg_simulated_pnl')} "
                f"(Δ={reference.get('avg_simulated_pnl_delta_vs_reference')})"
            )
            top_shift = reference.get("top_mean_shift_features") or []
            if top_shift:
                preview = "/".join(
                    f"{row.get('feature')}({row.get('reference_mean')}→{row.get('current_mean')}, Δσ={row.get('delta_vs_baseline_std')})"
                    for row in top_shift[:3]
                )
                print(f"  ↳ top feature shifts vs sibling window: {preview}")
            new_flags = []
            if reference.get("new_unexpected_frozen_features"):
                new_flags.append("new_frozen=" + "/".join(reference.get("new_unexpected_frozen_features")[:3]))
            if reference.get("new_unexpected_compressed_features"):
                new_flags.append("new_compressed=" + "/".join(reference.get("new_unexpected_compressed_features")[:3]))
            if reference.get("new_null_heavy_features"):
                new_flags.append("new_null_heavy=" + "/".join(reference.get("new_null_heavy_features")[:3]))
            if new_flags:
                print("  ↳ new pathology vs sibling window: " + "; ".join(new_flags))
        recent_examples = path_diag.get("recent_examples") or []
        if recent_examples:
            preview = "; ".join(
                f"{row.get('timestamp')} target={row.get('target')} regime={row.get('regime')} "
                f"q={row.get('simulated_pyramid_quality')} pnl={row.get('simulated_pyramid_pnl')}"
                for row in recent_examples[-3:]
            )
            print(f"  ↳ target-path examples: {preview}")
        adverse_examples = adverse_streak.get("examples") or []
        if adverse_examples:
            adverse_preview = "; ".join(
                f"{row.get('timestamp')} target={row.get('target')} regime={row.get('regime')} "
                f"q={row.get('simulated_pyramid_quality')} pnl={row.get('simulated_pyramid_pnl')}"
                for row in adverse_examples[-3:]
            )
            print(f"  ↳ adverse-streak examples: {adverse_preview}")
    if blocking_window and blocking_window != primary_window:
        blocking_quality = blocking_summary.get("quality_metrics") or {}
        print(
            f"阻塞病態視窗：最近 {blocking_window} 筆 | win_rate={blocking_summary.get('win_rate', 0):.4f} "
            f"dominant_regime={blocking_summary.get('dominant_regime')} ({(blocking_summary.get('dominant_regime_share') or 0):.2%}) "
            f"alerts={blocking_alerts} interpretation={blocking_summary.get('drift_interpretation')} "
            f"avg_pnl={blocking_quality.get('avg_simulated_pnl')} avg_quality={blocking_quality.get('avg_simulated_quality')}"
        )
    print(f"已儲存至 {OUT_PATH}")
    if isinstance(report.get("canonical_tail_root_cause"), dict):
        print(f"canonical tail root cause 已儲存至 {TAIL_ROOT_CAUSE_OUT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
