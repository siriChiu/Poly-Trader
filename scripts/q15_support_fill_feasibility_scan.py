#!/usr/bin/env python3
"""Scan whether the current q15 support gap can be filled by history/backfill.

Purpose:
- distinguish a true raw-data/support harvest gap from a semantic/window gap
- keep deployment fail-closed when older/proxy rows have enough count but do not
  match the current support identity (especially calibration_window)

Inputs:
- poly_trader.db (features_normalized + labels)
- data/live_predict_probe.json
- data/q15_support_audit.json (optional context)

Outputs:
- data/q15_support_fill_feasibility.json
- docs/analysis/q15_support_fill_feasibility.md
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DB_PATH = PROJECT_ROOT / "poly_trader.db"
PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
Q15_AUDIT_PATH = PROJECT_ROOT / "data" / "q15_support_audit.json"
OUT_JSON = PROJECT_ROOT / "data" / "q15_support_fill_feasibility.json"
OUT_MD = PROJECT_ROOT / "docs" / "analysis" / "q15_support_fill_feasibility.md"

BUCKET_SEMANTIC_SIGNATURE = "live_structure_bucket:q15_support_identity:v2"
DEFAULT_TARGET_COL = "simulated_pyramid_win"
DEFAULT_HORIZON_MINUTES = 1440
DEFAULT_MINIMUM_SUPPORT_ROWS = 50
SCAN_WINDOWS = (100, 200, 600, 1000, 5000)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _round_optional(value: Any, digits: int = 4) -> float | None:
    try:
        if value is None:
            return None
        return round(float(value), digits)
    except Exception:
        return None


def _avg(rows: Iterable[dict[str, Any]], key: str) -> float | None:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        try:
            values.append(float(value))
        except Exception:
            continue
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    wins = [row.get("simulated_pyramid_win") for row in rows if row.get("simulated_pyramid_win") is not None]
    return {
        "rows": len(rows),
        "win_rate": _avg(rows, "simulated_pyramid_win"),
        "target_counts": dict(Counter(str(int(v)) for v in wins)) if wins else {},
        "avg_pnl": _avg(rows, "simulated_pyramid_pnl"),
        "avg_quality": _avg(rows, "simulated_pyramid_quality"),
        "avg_drawdown_penalty": _avg(rows, "simulated_pyramid_drawdown_penalty"),
        "avg_time_underwater": _avg(rows, "simulated_pyramid_time_underwater"),
    }


def _symbol_alignment_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize strict vs canonical symbol joins for support-count auditability."""

    mode_counts = Counter(str(row.get("symbol_join_mode") or "unknown") for row in rows)
    recovered_rows = [
        row
        for row in rows
        if row.get("symbol_join_mode") == "canonical_symbol"
        and row.get("symbol") != row.get("label_symbol")
    ]
    return {
        "join_policy": "timestamp_plus_canonical_symbol_latest_feature_and_label_id",
        "canonical_symbol_transform": "remove_slash",
        "dedupe_policy": "max_id_per_timestamp_canonical_symbol_for_features_and_labels",
        "total_joined_rows": len(rows),
        "strict_symbol_rows": int(mode_counts.get("strict_symbol") or 0),
        "canonical_symbol_rows": int(mode_counts.get("canonical_symbol") or 0),
        "unknown_symbol_mode_rows": int(mode_counts.get("unknown") or 0),
        "canonical_symbol_recovered_rows": len(recovered_rows),
        "sample_recovered_pairs": [
            {
                "timestamp": row.get("timestamp"),
                "feature_symbol": row.get("symbol"),
                "label_symbol": row.get("label_symbol"),
            }
            for row in recovered_rows[:5]
        ],
        "live_exposure_allowed": False,
        "evidence_role": "data_alignment_cleanup_not_deployment_clearance",
    }


def support_identity_from_artifacts(
    probe: dict[str, Any],
    q15_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the current support identity from the live probe, with q15 audit fallback."""

    q15_audit = q15_audit or {}
    current_live = q15_audit.get("current_live") if isinstance(q15_audit.get("current_live"), dict) else {}
    audit_route = q15_audit.get("support_route") if isinstance(q15_audit.get("support_route"), dict) else {}
    audit_identity = audit_route.get("support_identity") if isinstance(audit_route.get("support_identity"), dict) else {}
    blocker = probe.get("deployment_blocker_details") if isinstance(probe.get("deployment_blocker_details"), dict) else {}

    current_bucket = (
        probe.get("current_live_structure_bucket")
        or blocker.get("structure_bucket")
        or current_live.get("current_live_structure_bucket")
        or audit_identity.get("current_live_structure_bucket")
    )
    return {
        "target_col": probe.get("target_col") or audit_identity.get("target_col") or DEFAULT_TARGET_COL,
        "horizon_minutes": _as_int(
            probe.get("horizon_minutes")
            or current_live.get("decision_quality_horizon_minutes")
            or audit_identity.get("horizon_minutes"),
            DEFAULT_HORIZON_MINUTES,
        ),
        "current_live_structure_bucket": current_bucket,
        "regime_label": probe.get("regime_label") or current_live.get("regime_label") or audit_identity.get("regime_label"),
        "regime_gate": probe.get("regime_gate") or current_live.get("regime_gate") or audit_identity.get("regime_gate"),
        "entry_quality_label": (
            probe.get("entry_quality_label")
            or current_live.get("entry_quality_label")
            or audit_identity.get("entry_quality_label")
        ),
        "calibration_window": _as_int(
            probe.get("decision_quality_calibration_window")
            or current_live.get("decision_quality_calibration_window")
            or audit_identity.get("calibration_window"),
            0,
        ),
        "bucket_semantic_signature": audit_identity.get("bucket_semantic_signature") or BUCKET_SEMANTIC_SIGNATURE,
    }


def fetch_db_meta(db_path: Path = DB_PATH) -> dict[str, Any]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    meta: dict[str, Any] = {}
    for table in ("features_normalized", "labels", "raw_market_data"):
        try:
            row = conn.execute(
                f"SELECT COUNT(*) AS count, MIN(timestamp) AS min_ts, MAX(timestamp) AS max_ts FROM {table}"
            ).fetchone()
        except sqlite3.Error:
            continue
        meta[table] = dict(row) if row is not None else {}
    conn.close()
    return meta


def fetch_labeled_decision_rows(
    *,
    db_path: Path = DB_PATH,
    horizon_minutes: int = DEFAULT_HORIZON_MINUTES,
) -> list[dict[str, Any]]:
    """Return production-style historical live-decision rows, newest first."""

    # Lazy import keeps unit tests for pure summarization helpers independent of the app DB/model stack.
    from model.predictor import _build_live_decision_profile

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    query = """
        WITH feature_latest AS (
            SELECT
                timestamp,
                REPLACE(COALESCE(symbol, ''), '/', '') AS symbol_key,
                MAX(id) AS feature_id
            FROM features_normalized
            GROUP BY timestamp, REPLACE(COALESCE(symbol, ''), '/', '')
        ),
        label_latest AS (
            SELECT
                timestamp,
                REPLACE(COALESCE(symbol, ''), '/', '') AS symbol_key,
                MAX(id) AS label_id
            FROM labels
            WHERE horizon_minutes = ?
              AND simulated_pyramid_win IS NOT NULL
            GROUP BY timestamp, REPLACE(COALESCE(symbol, ''), '/', '')
        )
        SELECT
            f.timestamp,
            f.symbol,
            l.symbol AS label_symbol,
            f.regime_label,
            f.feat_4h_bias200,
            f.feat_4h_bias50,
            f.feat_4h_bb_pct_b,
            f.feat_4h_dist_bb_lower,
            f.feat_4h_dist_swing_low,
            f.feat_nose,
            f.feat_pulse,
            f.feat_ear,
            l.simulated_pyramid_win,
            l.simulated_pyramid_pnl,
            l.simulated_pyramid_quality,
            l.simulated_pyramid_drawdown_penalty,
            l.simulated_pyramid_time_underwater
        FROM feature_latest fl
        JOIN features_normalized f ON f.id = fl.feature_id
        JOIN label_latest ll
          ON ll.timestamp = fl.timestamp
         AND ll.symbol_key = fl.symbol_key
        JOIN labels l ON l.id = ll.label_id
        ORDER BY f.timestamp DESC
    """
    raw_rows = conn.execute(query, (horizon_minutes,)).fetchall()
    conn.close()

    summarized_rows: list[dict[str, Any]] = []
    for row in raw_rows:
        # This mirrors model.predictor._infer_live_decision_quality_contract: historical rows are
        # re-bucketed through the same live decision-profile logic before support diagnostics count them.
        hist_features = {
            "regime_label": row["regime_label"],
            "feat_4h_bias200": row["feat_4h_bias200"],
            "feat_4h_bias50": row["feat_4h_bias50"],
            "feat_4h_bb_pct_b": row["feat_4h_bb_pct_b"],
            "feat_4h_dist_bb_lower": row["feat_4h_dist_bb_lower"],
            "feat_4h_dist_swing_low": row["feat_4h_dist_swing_low"],
            "feat_nose": row["feat_nose"],
            "feat_pulse": row["feat_pulse"],
            "feat_ear": row["feat_ear"],
        }
        profile = _build_live_decision_profile(hist_features)
        summarized_rows.append(
            {
                "timestamp": row["timestamp"],
                "symbol": row["symbol"],
                "label_symbol": row["label_symbol"],
                "symbol_join_mode": "strict_symbol" if row["symbol"] == row["label_symbol"] else "canonical_symbol",
                "regime_label": profile.get("regime_label"),
                "regime_gate": profile.get("regime_gate"),
                "entry_quality_label": profile.get("entry_quality_label"),
                "structure_bucket": profile.get("structure_bucket"),
                "simulated_pyramid_win": row["simulated_pyramid_win"],
                "simulated_pyramid_pnl": row["simulated_pyramid_pnl"],
                "simulated_pyramid_quality": row["simulated_pyramid_quality"],
                "simulated_pyramid_drawdown_penalty": row["simulated_pyramid_drawdown_penalty"],
                "simulated_pyramid_time_underwater": row["simulated_pyramid_time_underwater"],
            }
        )
    return summarized_rows


def _matches_exact_identity(row: dict[str, Any], identity: dict[str, Any]) -> bool:
    return (
        row.get("regime_label") == identity.get("regime_label")
        and row.get("regime_gate") == identity.get("regime_gate")
        and row.get("entry_quality_label") == identity.get("entry_quality_label")
    )


def _matches_exact_bucket(row: dict[str, Any], identity: dict[str, Any]) -> bool:
    return _matches_exact_identity(row, identity) and row.get("structure_bucket") == identity.get(
        "current_live_structure_bucket"
    )


def _compression_candidate(
    *,
    candidate_id: str,
    description: str,
    rows: list[dict[str, Any]],
    relaxed_fields: list[str],
    exact_fields: list[str],
    minimum_support_rows: int,
    evidence_role: str,
) -> dict[str, Any]:
    """Summarize one support-identity compression candidate.

    These candidates are research/governance proof only. They never become deployable
    support by count alone; live buy/add remains behind support-audit replay plus
    execution/venue gates.
    """

    metrics = _metric_summary(rows)
    win_rate = metrics.get("win_rate")
    avg_pnl = metrics.get("avg_pnl")
    avg_drawdown_penalty = metrics.get("avg_drawdown_penalty")
    ready_by_count = len(rows) >= minimum_support_rows
    metric_gate_candidate = bool(
        ready_by_count
        and win_rate is not None
        and win_rate >= 0.55
        and avg_pnl is not None
        and avg_pnl > 0
        and (avg_drawdown_penalty is None or avg_drawdown_penalty <= 0.25)
    )
    return {
        "id": candidate_id,
        "description": description,
        "rows": len(rows),
        "rows_needed_to_minimum": max(minimum_support_rows - len(rows), 0),
        "ready_by_count": ready_by_count,
        "metric_gate_candidate": metric_gate_candidate,
        "metrics": metrics,
        "exact_fields": exact_fields,
        "relaxed_fields": relaxed_fields,
        "evidence_role": evidence_role,
        "latest_timestamp": rows[0].get("timestamp") if rows else None,
        "oldest_timestamp": rows[-1].get("timestamp") if rows else None,
        "deployable_support": False,
        "live_exposure_allowed": False,
    }


def _support_identity_compression_proof(
    *,
    rows: list[dict[str, Any]],
    current_rows: list[dict[str, Any]],
    support_identity: dict[str, Any],
    minimum_support_rows: int,
) -> dict[str, Any]:
    """Find non-deployable structural alternatives to the dead exact-key loop."""

    current_bucket = support_identity.get("current_live_structure_bucket")
    current_regime = support_identity.get("regime_label")
    current_gate = support_identity.get("regime_gate")
    current_entry_label = support_identity.get("entry_quality_label")

    exact_full_rows = [row for row in rows if _matches_exact_bucket(row, support_identity)]
    regime_gate_bucket_rows = [
        row
        for row in rows
        if row.get("regime_label") == current_regime
        and row.get("regime_gate") == current_gate
        and row.get("structure_bucket") == current_bucket
    ]
    gate_bucket_rows = [
        row
        for row in rows
        if row.get("regime_gate") == current_gate and row.get("structure_bucket") == current_bucket
    ]
    bucket_only_rows = [row for row in rows if row.get("structure_bucket") == current_bucket]
    current_exact_rows = [row for row in current_rows if _matches_exact_bucket(row, support_identity)]

    candidates = [
        _compression_candidate(
            candidate_id="current_exact_identity_window",
            description="Baseline: current calibration_window + regime + gate + entry label + bucket exactly as live state.",
            rows=current_exact_rows,
            relaxed_fields=[],
            exact_fields=["calibration_window", "regime_label", "regime_gate", "entry_quality_label", "current_live_structure_bucket"],
            minimum_support_rows=minimum_support_rows,
            evidence_role="current_deployable_identity_baseline",
        ),
        _compression_candidate(
            candidate_id="rebaseline_calibration_window_only",
            description="Treat calibration_window as rebaseline context while keeping regime/gate/entry/bucket exact; requires replay/OOS before promotion.",
            rows=exact_full_rows,
            relaxed_fields=["calibration_window"],
            exact_fields=["regime_label", "regime_gate", "entry_quality_label", "current_live_structure_bucket"],
            minimum_support_rows=minimum_support_rows,
            evidence_role="research_candidate_rebaseline_required",
        ),
        _compression_candidate(
            candidate_id="semantic_entry_quality_family",
            description="Treat entry_quality_label as semantic family inside the same regime/gate/bucket; stricter than bucket-only, looser than exact label.",
            rows=regime_gate_bucket_rows,
            relaxed_fields=["calibration_window", "entry_quality_label"],
            exact_fields=["regime_label", "regime_gate", "current_live_structure_bucket"],
            minimum_support_rows=minimum_support_rows,
            evidence_role="research_candidate_semantic_adapter_required",
        ),
        _compression_candidate(
            candidate_id="regime_gate_bucket_family",
            description="Treat regime_label as context while keeping gate and bucket exact; higher drift risk, requires explicit go/no-go.",
            rows=gate_bucket_rows,
            relaxed_fields=["calibration_window", "entry_quality_label", "regime_label"],
            exact_fields=["regime_gate", "current_live_structure_bucket"],
            minimum_support_rows=minimum_support_rows,
            evidence_role="research_candidate_high_drift_risk",
        ),
        _compression_candidate(
            candidate_id="bucket_only_family",
            description="Bucket-only family; diagnostic lower bound only, never direct deployable support.",
            rows=bucket_only_rows,
            relaxed_fields=["calibration_window", "entry_quality_label", "regime_label", "regime_gate"],
            exact_fields=["current_live_structure_bucket"],
            minimum_support_rows=minimum_support_rows,
            evidence_role="diagnostic_only_too_loose_for_deployment",
        ),
    ]
    selectable = [
        candidate
        for candidate in candidates[1:]
        if candidate.get("ready_by_count") and candidate.get("metric_gate_candidate")
    ]
    selected = selectable[0] if selectable else None
    return {
        "artifact": "support_identity_compression_proof",
        "purpose": "Break the repeated exact-bucket support collection loop by testing structural identity compression candidates without relaxing live gates.",
        "anti_treadmill": True,
        "decision": "candidate_found_not_deployable" if selected else "no_safe_compression_candidate_found",
        "selected_candidate_id": selected.get("id") if selected else None,
        "selected_candidate_rows": selected.get("rows") if selected else 0,
        "selected_candidate_metrics": selected.get("metrics") if selected else {},
        "candidates": candidates,
        "promotion_requirements": [
            "rerun replay/OOS/Top-K under the proposed compressed identity",
            "rerun q15 support audit with the new identity as the explicit support contract",
            "keep proxy/reference rows non-deployable until governance accepts the new identity",
            "keep /api/trade buy/add fail-closed until exact support, bounded live-canary policy, and venue lifecycle proof all pass",
        ],
        "forbidden_shortcuts": [
            "lower_minimum_support_rows",
            "count_reference_rows_as_current_exact_support",
            "enable_live_buy_or_add_from_this proof alone",
        ],
        "live_exposure_allowed": False,
    }


def _missing_capability_class(classification: str) -> str:
    """Classify PM-facing missing capability without loosening deployment gates."""

    return {
        "current_identity_support_ready": "Review",
        "current_calibration_window_data_gap": "Tool/Data",
        "semantic_window_gap_not_raw_backfill_gap": "Constraint/Review",
        "true_support_under_minimum": "Signal/Support",
        "no_exact_bucket_history": "Map/Signal",
    }.get(classification, "Review")


def _time_to_evidence_bucket(
    *,
    classification: str,
    current_rows: int,
    minimum_support_rows: int,
    current_window_filled: bool,
) -> str:
    """Produce a PM heartbeat time-to-evidence bucket from measured support facts."""

    gap = max(minimum_support_rows - current_rows, 0)
    if classification == "current_identity_support_ready":
        return "ready_for_remaining_live_execution_gates"
    if classification == "current_calibration_window_data_gap" and not current_window_filled:
        return "next_heartbeat_after_label_backfill"
    if classification == "semantic_window_gap_not_raw_backfill_gap":
        return "semantic_rebaseline_review_required_before_reference_rows_count"
    if classification == "no_exact_bucket_history":
        return "unknown_until_bucket_map_or_signal_redesign"
    if current_rows > 0 and gap <= 20:
        return "same_day_or_next_heartbeat_if_exact_identity_keeps_accumulating"
    if current_rows > 0:
        return "within_week_if_exact_identity_keeps_accumulating"
    return "unknown_until_exact_identity_rows_start_accumulating"


def _pm_delivery_pressure(
    *,
    classification: str,
    current_rows: int,
    minimum_support_rows: int,
    current_window_filled: bool,
    best_reference: dict[str, Any],
) -> dict[str, Any]:
    """PM handoff lane: avoid endless wait by naming next proof and alternatives."""

    gap = max(minimum_support_rows - current_rows, 0)
    if current_rows >= minimum_support_rows:
        engineering_next_gate = (
            f"exact current support rows {current_rows}/{minimum_support_rows} already meet minimum; "
            "keep deployable=false until circuit breaker, Top-K deployability, and venue/execution gates pass; "
            "reference rows stay non-deployable unless identity is deliberately rebaselined and reverified"
        )
    else:
        engineering_next_gate = (
            f"exact current support rows {current_rows}/{minimum_support_rows} must reach minimum; "
            f"gap={gap}; reference rows stay non-deployable until identity is deliberately rebaselined and reverified"
        )
    time_bucket = _time_to_evidence_bucket(
        classification=classification,
        current_rows=current_rows,
        minimum_support_rows=minimum_support_rows,
        current_window_filled=current_window_filled,
    )
    alternatives = [
        {
            "id": "paper_shadow_decision_support_sleeve",
            "role": "customer_usable_now",
            "next_artifact": "data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy",
            "live_exposure_allowed": False,
        },
        {
            "id": "semantic_rebaseline_review",
            "role": "support_policy_alternative",
            "next_artifact": "OOS + Top-K + support audit replay under any proposed new calibration_window identity",
            "live_exposure_allowed": False,
            "reference_window": best_reference.get("window_key"),
            "reference_rows": best_reference.get("exact_bucket_rows"),
        },
        {
            "id": "venue_dry_run_readiness_proof",
            "role": "delivery_risk_reduction",
            "next_artifact": "OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only",
            "live_exposure_allowed": False,
        },
    ]
    return {
        "time_to_evidence_bucket": time_bucket,
        "missing_capability_class": _missing_capability_class(classification),
        "alternative_solution_required": classification != "current_identity_support_ready",
        "selected_next_alternative_artifact": alternatives[0]["next_artifact"],
        "customer_safe_lane": "paper/shadow decision-support; no buy/add live exposure",
        "engineering_next_gate": engineering_next_gate,
        "alternative_solutions": alternatives,
    }


def build_feasibility_report(
    *,
    rows: list[dict[str, Any]],
    support_identity: dict[str, Any],
    db_meta: dict[str, Any] | None = None,
    q15_audit: dict[str, Any] | None = None,
    source_artifacts: dict[str, Any] | None = None,
    generated_at: str | None = None,
    windows: Iterable[int] = SCAN_WINDOWS,
    minimum_support_rows: int = DEFAULT_MINIMUM_SUPPORT_ROWS,
) -> dict[str, Any]:
    """Summarize whether exact-bucket support can be closed by historical data."""

    q15_audit = q15_audit or {}
    calibration_window = _as_int(support_identity.get("calibration_window"), 0)
    normalized_windows = sorted({int(w) for w in windows if int(w) > 0} | ({calibration_window} if calibration_window > 0 else set()))
    if rows:
        normalized_windows.append(len(rows))

    window_scan: dict[str, Any] = {}
    for window in normalized_windows:
        scoped_rows = rows[: min(window, len(rows))]
        exact_identity_rows = [row for row in scoped_rows if _matches_exact_identity(row, support_identity)]
        exact_bucket_rows = [row for row in exact_identity_rows if _matches_exact_bucket(row, support_identity)]
        same_regime_bucket_rows = [
            row
            for row in scoped_rows
            if row.get("regime_label") == support_identity.get("regime_label")
            and row.get("structure_bucket") == support_identity.get("current_live_structure_bucket")
        ]
        any_scope_bucket_rows = [
            row for row in scoped_rows if row.get("structure_bucket") == support_identity.get("current_live_structure_bucket")
        ]
        window_key = str(window) if window != len(rows) else "all"
        same_calibration_identity = window == calibration_window
        support_ready_by_count = len(exact_bucket_rows) >= minimum_support_rows
        bucket_counts = Counter(str(row.get("structure_bucket")) for row in exact_identity_rows if row.get("structure_bucket"))
        window_scan[window_key] = {
            "calibration_window": window,
            "scope_rows": len(scoped_rows),
            "exact_identity_rows": len(exact_identity_rows),
            "exact_bucket_rows": len(exact_bucket_rows),
            "same_regime_bucket_rows": len(same_regime_bucket_rows),
            "any_scope_bucket_rows": len(any_scope_bucket_rows),
            "rows_needed_to_minimum": max(minimum_support_rows - len(exact_bucket_rows), 0),
            "support_ready_by_count": support_ready_by_count,
            "same_calibration_identity_as_current": same_calibration_identity,
            "deployment_promotable_under_current_identity": bool(support_ready_by_count and same_calibration_identity),
            "evidence_role": "current_support_identity" if same_calibration_identity else "reference_only_calibration_window_mismatch",
            "semantic_mismatched_fields_vs_current": [] if same_calibration_identity else ["calibration_window"],
            "exact_bucket_metrics": _metric_summary(exact_bucket_rows),
            "exact_lane_bucket_counts": dict(bucket_counts.most_common(8)),
            "latest_exact_bucket_timestamp": exact_bucket_rows[0].get("timestamp") if exact_bucket_rows else None,
            "oldest_exact_bucket_timestamp": exact_bucket_rows[-1].get("timestamp") if exact_bucket_rows else None,
        }

    current_key = str(calibration_window) if str(calibration_window) in window_scan else None
    current_scan = window_scan.get(current_key or "", {})
    reference_candidates = [
        {"window_key": key, **scan}
        for key, scan in window_scan.items()
        if not scan.get("same_calibration_identity_as_current")
    ]
    best_reference = max(reference_candidates, key=lambda item: int(item.get("exact_bucket_rows") or 0), default={})
    full_scan = window_scan.get("all") or (list(window_scan.values())[-1] if window_scan else {})
    current_rows = int(current_scan.get("exact_bucket_rows") or 0)
    current_scoped_rows = rows[: min(calibration_window, len(rows))] if calibration_window > 0 else []
    current_exact_identity_rows = int(current_scan.get("exact_identity_rows") or 0)
    current_exact_identity_non_bucket_rows = max(current_exact_identity_rows - current_rows, 0)
    joined_rows = len(rows)
    current_window_filled = bool(calibration_window > 0 and joined_rows >= calibration_window)

    if current_rows >= minimum_support_rows:
        classification = "current_identity_support_ready"
        can_backfill_close_current_identity = False
        reason = "current support_identity already has enough exact-bucket rows; deployment should depend on the remaining live/execution gates."
    elif not current_window_filled:
        classification = "current_calibration_window_data_gap"
        can_backfill_close_current_identity = True
        reason = "current calibration window is not fully populated with labeled rows; historical/label backfill may add rows before semantic rebaseline is considered."
    elif int(best_reference.get("exact_bucket_rows") or 0) >= minimum_support_rows:
        classification = "semantic_window_gap_not_raw_backfill_gap"
        can_backfill_close_current_identity = False
        reason = (
            "older calibration windows have enough exact-bucket rows by count, but they mismatch the current "
            "support_identity on calibration_window; they are reference-only unless governance deliberately rebaselines the identity."
        )
    elif int(full_scan.get("exact_bucket_rows") or 0) > 0:
        classification = "true_support_under_minimum"
        can_backfill_close_current_identity = False
        reason = "current identity is missing support and full history also remains under minimum; collect forward exact rows or redesign the bucket."
    else:
        classification = "no_exact_bucket_history"
        can_backfill_close_current_identity = False
        reason = "no exact-bucket rows were found under current bucket semantics; this is a support-harvest/design gap, not a backtest-results gap."

    q15_route = q15_audit.get("support_route") if isinstance(q15_audit.get("support_route"), dict) else {}
    active_repair = q15_audit.get("active_repair_plan") if isinstance(q15_audit.get("active_repair_plan"), dict) else {}
    pm_pressure = _pm_delivery_pressure(
        classification=classification,
        current_rows=current_rows,
        minimum_support_rows=minimum_support_rows,
        current_window_filled=current_window_filled,
        best_reference=best_reference,
    )
    compression_proof = _support_identity_compression_proof(
        rows=rows,
        current_rows=current_scoped_rows,
        support_identity=support_identity,
        minimum_support_rows=minimum_support_rows,
    )
    verdict = {
        "classification": classification,
        "reason": reason,
        "can_historical_backfill_close_current_identity": can_backfill_close_current_identity,
        "can_count_reference_windows_as_deployable": False,
        "current_calibration_window": calibration_window,
        "current_exact_identity_rows": current_exact_identity_rows,
        "current_exact_identity_non_bucket_rows": current_exact_identity_non_bucket_rows,
        "current_exact_bucket_rows": current_rows,
        "minimum_support_rows": minimum_support_rows,
        "gap_to_minimum": max(minimum_support_rows - current_rows, 0),
        "best_reference_window": best_reference.get("window_key"),
        "best_reference_exact_bucket_rows": best_reference.get("exact_bucket_rows"),
        "best_reference_evidence_role": best_reference.get("evidence_role"),
        "q15_support_route_verdict": q15_route.get("verdict"),
        "q15_support_governance_route": q15_route.get("support_governance_route"),
        "q15_active_repair_phase": active_repair.get("phase"),
        "live_exposure_allowed": bool(active_repair.get("live_exposure_allowed", False)),
        "shadow_or_paper_allowed": bool(active_repair.get("shadow_or_paper_allowed", True)),
        **pm_pressure,
    }

    current_bucket = support_identity.get("current_live_structure_bucket") or "unknown_bucket"
    current_regime = support_identity.get("regime_label") or "unknown_regime"
    current_gate = support_identity.get("regime_gate") or "unknown_gate"
    current_entry_label = support_identity.get("entry_quality_label") or "unknown_entry_quality"
    current_support_ready = current_rows >= minimum_support_rows
    if current_support_ready:
        keep_description = (
            "維持 deployable=false / allowed_layers=0；"
            f"current support identity exact rows {current_rows}/{minimum_support_rows} 已達門檻，"
            "但 support gate 不是 deployment closure；reference windows 仍不可直接算作額外 deployment support。"
        )
        keep_success = "current support_identity exact rows 維持 >= minimum，且 circuit breaker / Top-K / venue / execution gates 同步通過。"
        collect_success = f"current_exact_bucket_rows 維持 >= {minimum_support_rows} 且 remaining live/execution gates 進入驗證。"
    else:
        keep_description = (
            "維持 deployable=false / allowed_layers=0；"
            f"current support identity exact rows {current_rows}/{minimum_support_rows}，"
            "未達門檻前 reference windows 不可直接算作 deployment support。"
        )
        keep_success = "current support_identity exact rows >= minimum 且 live/execution gates 同步通過。"
        collect_success = f"current_exact_bucket_rows >= {minimum_support_rows}"
    actions = [
        {
            "id": "keep_deployment_fail_closed",
            "priority": "P0",
            "description": keep_description,
            "success_condition": keep_success,
            "current_rows": current_rows,
            "rows_needed": max(minimum_support_rows - current_rows, 0),
            "current_calibration_window": calibration_window,
        },
        {
            "id": "collect_forward_exact_current_identity_rows",
            "priority": "P0",
            "description": (
                f"繼續收集與 current calibration_window={calibration_window}、"
                f"regime={current_regime}、gate={current_gate}、"
                f"entry_label={current_entry_label}、bucket={current_bucket} "
                "完全一致的真實 labeled rows。"
            ),
            "success_condition": collect_success,
            "current_rows": current_rows,
            "rows_needed": max(minimum_support_rows - current_rows, 0),
            "current_calibration_window": calibration_window,
        },
        {
            "id": "semantic_rebaseline_if_using_older_windows",
            "priority": "P1",
            "description": (
                f"若要採用 reference window={best_reference.get('window_key')} "
                "的 rows 或改變 calibration_window policy，必須先改 support_identity，"
                "重跑 OOS、Top-K、support audit、API/trade guardrail，"
                "而不是把舊 rows 直接補進 current identity。"
            ),
            "success_condition": "新 identity 全欄位一致且重新驗證後仍 rows>=minimum、risk metrics 合格。",
            "reference_window": best_reference.get("window_key"),
            "reference_rows": best_reference.get("exact_bucket_rows"),
            "current_calibration_window": calibration_window,
        },
        {
            "id": "support_identity_compression_proof",
            "priority": "P0",
            "description": (
                "停止把主解法寫成反覆蒐集同一 exact key；改交付 support identity compression proof，"
                f"目前選中候選={compression_proof.get('selected_candidate_id')}，"
                "但所有候選都維持 deployable=false，直到 replay/OOS/Top-K/support audit/API guardrail 重跑通過。"
            ),
            "success_condition": "選定 compressed identity 後重跑治理證據；未完成前 buy/add live exposure 仍 fail-closed。",
            "selected_candidate_id": compression_proof.get("selected_candidate_id"),
            "live_exposure_allowed": False,
        },
    ]

    return {
        "generated_at": generated_at or _utc_now_iso(),
        "artifact": "q15_support_fill_feasibility",
        "source_artifacts": source_artifacts or {},
        "support_identity": support_identity,
        "data_coverage": {
            "joined_labeled_rows": joined_rows,
            "current_calibration_window_filled": current_window_filled,
            "db_meta": db_meta or {},
            "symbol_alignment": _symbol_alignment_summary(rows),
        },
        "verdict": verdict,
        "support_identity_compression_proof": compression_proof,
        "window_scan": window_scan,
        "recommended_actions": actions,
    }


def markdown(report: dict[str, Any]) -> str:
    verdict = report.get("verdict") or {}
    identity = report.get("support_identity") or {}
    compression = report.get("support_identity_compression_proof") or {}
    coverage = report.get("data_coverage") or {}
    source_artifacts = report.get("source_artifacts") or {}
    lines = [
        "# current support-fill feasibility scan (q15/q35 compatibility)",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- source live probe generated_at: `{source_artifacts.get('live_predict_probe_generated_at')}`",
        f"- source q15 audit generated_at: `{source_artifacts.get('q15_support_audit_generated_at')}`",
        f"- classification: **{verdict.get('classification')}**",
        f"- reason: {verdict.get('reason')}",
        f"- current exact bucket rows (deployable support candidate): **{verdict.get('current_exact_bucket_rows')}/{verdict.get('minimum_support_rows')}**",
        f"- current exact identity rows before bucket filter: **{verdict.get('current_exact_identity_rows')}** "
        f"(non-current-bucket: **{verdict.get('current_exact_identity_non_bucket_rows')}**; reference only, not deployment support)",
        f"- gap_to_minimum: **{verdict.get('gap_to_minimum')}**",
        f"- historical backfill can close current identity: **{verdict.get('can_historical_backfill_close_current_identity')}**",
        f"- reference windows deployable by count alone: **{verdict.get('can_count_reference_windows_as_deployable')}**",
        "",
        "## Scanned current support identity",
        "",
        "This section is the current support identity captured by the source artifacts above. Re-check `/api/status` before treating it as the latest live bucket.",
        "",
    ]
    for key in (
        "target_col",
        "horizon_minutes",
        "current_live_structure_bucket",
        "regime_label",
        "regime_gate",
        "entry_quality_label",
        "calibration_window",
        "bucket_semantic_signature",
    ):
        lines.append(f"- {key}: `{identity.get(key)}`")

    lines.extend([
        "",
        "## Data coverage",
        "",
        f"- joined labeled rows: **{coverage.get('joined_labeled_rows')}**",
        f"- current calibration window filled: **{coverage.get('current_calibration_window_filled')}**",
    ])
    symbol_alignment = coverage.get("symbol_alignment") if isinstance(coverage.get("symbol_alignment"), dict) else {}
    if symbol_alignment:
        lines.extend([
            f"- symbol join policy: `{symbol_alignment.get('join_policy')}`",
            f"- canonical symbol recovered rows: **{symbol_alignment.get('canonical_symbol_recovered_rows')}** "
            f"(strict={symbol_alignment.get('strict_symbol_rows')}, canonical={symbol_alignment.get('canonical_symbol_rows')})",
            "- symbol alignment evidence role: data cleanup only; live exposure remains fail-closed until all live gates pass.",
        ])
    db_meta = coverage.get("db_meta") or {}
    for table, meta in db_meta.items():
        lines.append(
            f"- {table}: count={meta.get('count')}, range=`{meta.get('min_ts')}` → `{meta.get('max_ts')}`"
        )

    lines.extend([
        "",
        "## PM delivery pressure",
        "",
        f"- time_to_evidence_bucket: `{verdict.get('time_to_evidence_bucket')}`",
        f"- missing_capability_class: `{verdict.get('missing_capability_class')}`",
        f"- alternative_solution_required: **{verdict.get('alternative_solution_required')}**",
        f"- selected_next_alternative_artifact: {verdict.get('selected_next_alternative_artifact')}",
        f"- customer_safe_lane: {verdict.get('customer_safe_lane')}",
        f"- engineering_next_gate: {verdict.get('engineering_next_gate')}",
        "",
        "### Alternative-solution candidates",
        "",
    ])
    for item in verdict.get("alternative_solutions") or []:
        lines.append(
            f"- `{item.get('id')}` ({item.get('role')}): {item.get('next_artifact')} "
            f"/ live_exposure_allowed={item.get('live_exposure_allowed')}"
        )

    lines.extend([
        "",
        "## Support identity compression proof",
        "",
        f"- decision: **{compression.get('decision')}**",
        f"- selected_candidate_id: `{compression.get('selected_candidate_id')}`",
        f"- selected_candidate_rows: **{compression.get('selected_candidate_rows')}**",
        f"- live_exposure_allowed: **{compression.get('live_exposure_allowed')}**",
        "- operator meaning: this is a structural redesign proof, not deployment clearance; buy/add remains fail-closed.",
        "",
        "| candidate | rows | count-ready | metric-candidate | relaxed fields | deployable | metrics |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ])
    for candidate in compression.get("candidates") or []:
        metrics = candidate.get("metrics") or {}
        metric_text = (
            f"win={metrics.get('win_rate')}, pnl={metrics.get('avg_pnl')}, "
            f"dd={metrics.get('avg_drawdown_penalty')}"
        )
        lines.append(
            "| "
            f"{candidate.get('id')} | {candidate.get('rows')} | {candidate.get('ready_by_count')} | "
            f"{candidate.get('metric_gate_candidate')} | {','.join(candidate.get('relaxed_fields') or []) or '—'} | "
            f"{candidate.get('deployable_support')} | {metric_text} |"
        )
    lines.extend([
        "",
        "Promotion requirements before any live buy/add:",
    ])
    for requirement in compression.get("promotion_requirements") or []:
        lines.append(f"- {requirement}")

    lines.extend([
        "",
        "## Window scan",
        "",
        "| window | exact identity rows | exact bucket rows | role | promotable | latest exact bucket | metrics |",
        "| --- | ---: | ---: | --- | --- | --- | --- |",
    ])
    for key, scan in (report.get("window_scan") or {}).items():
        metrics = scan.get("exact_bucket_metrics") or {}
        metrics_text = (
            f"win={metrics.get('win_rate')}, pnl={metrics.get('avg_pnl')}, "
            f"quality={metrics.get('avg_quality')}"
        )
        lines.append(
            "| "
            f"{key} | {scan.get('exact_identity_rows')} | {scan.get('exact_bucket_rows')} | "
            f"{scan.get('evidence_role')} | {scan.get('deployment_promotable_under_current_identity')} | "
            f"{scan.get('latest_exact_bucket_timestamp')} | {metrics_text} |"
        )

    lines.extend(["", "## Recommended actions", ""])
    for action in report.get("recommended_actions") or []:
        lines.append(f"- **{action.get('id')}** ({action.get('priority')}): {action.get('description')}")
        lines.append(f"  - success: {action.get('success_condition')}")

    lines.extend([
        "",
        "## Operator conclusion",
        "",
        "舊窗口 / full-history rows 可以當治理參考與 rebaseline 候選，但在 `calibration_window` 不吻合前，不能把它們直接補成 current deployment support rows。",
    ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    probe = _load_json(PROBE_PATH)
    q15_audit = _load_json(Q15_AUDIT_PATH)
    identity = support_identity_from_artifacts(probe, q15_audit)
    rows = fetch_labeled_decision_rows(
        db_path=DB_PATH,
        horizon_minutes=_as_int(identity.get("horizon_minutes"), DEFAULT_HORIZON_MINUTES),
    )
    report = build_feasibility_report(
        rows=rows,
        support_identity=identity,
        db_meta=fetch_db_meta(DB_PATH),
        q15_audit=q15_audit,
        source_artifacts={
            "live_predict_probe_path": str(PROBE_PATH.relative_to(PROJECT_ROOT)),
            "live_predict_probe_generated_at": probe.get("generated_at"),
            "q15_support_audit_path": str(Q15_AUDIT_PATH.relative_to(PROJECT_ROOT)),
            "q15_support_audit_generated_at": q15_audit.get("generated_at"),
        },
        minimum_support_rows=_as_int(
            probe.get("minimum_support_rows")
            or (q15_audit.get("support_route") or {}).get("minimum_support_rows"),
            DEFAULT_MINIMUM_SUPPORT_ROWS,
        ),
    )
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown(report), encoding="utf-8")
    verdict = report["verdict"]
    print(
        "current support-fill feasibility: "
        f"{verdict['classification']} rows={verdict['current_exact_bucket_rows']}/"
        f"{verdict['minimum_support_rows']} identity_rows={verdict.get('current_exact_identity_rows')} "
        f"non_bucket_identity_rows={verdict.get('current_exact_identity_non_bucket_rows')} best_reference="
        f"{verdict.get('best_reference_window')}:{verdict.get('best_reference_exact_bucket_rows')} "
        f"time_to_evidence={verdict.get('time_to_evidence_bucket')} "
        f"missing_capability={verdict.get('missing_capability_class')}"
    )


if __name__ == "__main__":
    main()
