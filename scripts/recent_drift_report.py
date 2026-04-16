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
from feature_engine.feature_history_policy import FEATURE_KEY_MAP, SOURCE_FEATURE_KEYS
DB_PATH = PROJECT_ROOT / "poly_trader.db"
OUT_PATH = PROJECT_ROOT / "data" / "recent_drift_report.json"
TARGET_COL = "simulated_pyramid_win"
CANONICAL_HORIZON_MINUTES = 1440
WINDOWS = [100, 250, 500, 1000]
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


def _expected_compressed_reason(
    feature_col: str,
    current_rows: list[sqlite3.Row],
    baseline_feature_stats: dict[str, dict[str, Any]],
) -> str | None:
    rule = EXPECTED_COMPRESSED_FEATURE_RULES.get(feature_col)
    if not rule:
        return None

    proxy_col = rule.get("proxy_col")
    if not proxy_col:
        return None

    proxy_recent = _feature_stats(current_rows, str(proxy_col))
    proxy_baseline = baseline_feature_stats.get(str(proxy_col)) or {}
    proxy_recent_std = proxy_recent.get("std")
    proxy_baseline_std = proxy_baseline.get("std")
    proxy_recent_mean = proxy_recent.get("mean")
    proxy_baseline_mean = proxy_baseline.get("mean")

    if not isinstance(proxy_recent_std, (int, float)) or not isinstance(proxy_baseline_std, (int, float)):
        return None
    if proxy_baseline_std <= 0:
        return None
    proxy_std_ratio = proxy_recent_std / proxy_baseline_std
    if proxy_std_ratio > LOW_VARIANCE_STD_RATIO_THRESHOLD:
        return None
    if not isinstance(proxy_recent_mean, (int, float)) or not isinstance(proxy_baseline_mean, (int, float)):
        return None
    if proxy_recent_mean > proxy_baseline_mean:
        return None
    return str(rule.get("reason") or "expected_underlying_compression")


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
        expected_compressed_reason = _expected_compressed_reason(feature_col, rows, baseline_feature_stats)
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
    if strong_positive_extreme:
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
        "drift_interpretation": interpretation,
        "alerts": alerts,
    }


def _find_primary_window(window_summaries: dict[str, dict[str, Any]]) -> tuple[str | None, dict[str, Any] | None]:
    def score(item: tuple[str, dict[str, Any]]) -> tuple[int, float, int]:
        _, summary = item
        alerts = summary.get("alerts", [])
        severity = 0
        if "constant_target" in alerts:
            severity += 4
        if "label_imbalance" in alerts:
            severity += 3
        if "regime_concentration" in alerts:
            severity += 2
        if "regime_shift" in alerts:
            severity += 1
        delta = abs(summary.get("win_rate_delta_vs_full") or 0.0)
        rows = int(summary.get("rows") or 0)
        return (severity, delta, rows)

    if not window_summaries:
        return None, None
    label, summary = max(window_summaries.items(), key=score)
    return label, summary


def build_report() -> dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    feature_cols = [
        row[1]
        for row in conn.execute("PRAGMA table_info(features_normalized)").fetchall()
        if isinstance(row[1], str) and row[1].startswith("feat_")
    ]
    has_raw_market_data = _table_exists(conn, "raw_market_data")
    feature_select = ",\n            ".join(f"f.{col}" for col in feature_cols)
    feature_select_sql = f",\n            {feature_select}" if feature_select else ""
    raw_select_sql = ",\n            r.volatility AS raw_volatility" if has_raw_market_data else ",\n            NULL AS raw_volatility"
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
        diagnostic_cols.append("raw_volatility")
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

    report = {
        "target_col": TARGET_COL,
        "horizon_minutes": CANONICAL_HORIZON_MINUTES,
        "generated_at": datetime.now(timezone.utc).isoformat(),
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
    }
    return report


def main() -> int:
    report = build_report()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2, default=str))

    primary = report.get("primary_window", {})
    primary_window = primary.get("window")
    summary = primary.get("summary", {})
    alerts = primary.get("alerts", [])

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
        streak_target = tail_streak.get("target")
        streak_target_text = "n/a" if streak_target is None else str(streak_target)
        adverse_streak = path_diag.get("longest_zero_target_streak") if (summary.get("win_rate") or 0) <= 0.5 else path_diag.get("longest_one_target_streak")
        adverse_streak = adverse_streak or {}
        adverse_target = adverse_streak.get("target")
        adverse_target_text = "n/a" if adverse_target is None else str(adverse_target)
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
            f"tail_streak={tail_streak.get('count', 0)}x{streak_target_text} since {tail_streak.get('start_timestamp')} "
            f"adverse_streak={adverse_streak.get('count', 0)}x{adverse_target_text} since {adverse_streak.get('start_timestamp')}"
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
    print(f"已儲存至 {OUT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
