#!/usr/bin/env python3
"""Produce a q15 Map/Signal redesign proof without relaxing live gates.

This forced-branch artifact evaluates whether the current q15 support deadlock
can be escaped by a concrete support-identity / bucket-map redesign.  It keeps
three boundaries explicit:

- current exact support remains the live gate;
- historical or semantic candidates are replay inputs, not deployment support;
- live buy/add remains disabled until support, model, venue, breaker, and
  bounded live-canary policy gates all pass.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from q15_support_fill_feasibility_scan import (  # noqa: E402
    DEFAULT_HORIZON_MINUTES,
    DEFAULT_MINIMUM_SUPPORT_ROWS,
    SCAN_WINDOWS,
    _as_int,
    _metric_summary,
    fetch_db_meta,
    fetch_labeled_decision_rows,
    support_identity_from_artifacts,
)

DATA_DIR = PROJECT_ROOT / "data"
DOCS_ANALYSIS_DIR = PROJECT_ROOT / "docs" / "analysis"
PROBE_PATH = DATA_DIR / "live_predict_probe.json"
Q15_AUDIT_PATH = DATA_DIR / "q15_support_audit.json"
SUPPORT_FILL_PATH = DATA_DIR / "q15_support_fill_feasibility.json"
DRIFT_REBASELINE_PATH = DATA_DIR / "q15_drift_rebaseline_backtest.json"
Q15_ROOT_CAUSE_PATH = DATA_DIR / "q15_bucket_root_cause.json"
RECENT_DRIFT_PATH = DATA_DIR / "recent_drift_report.json"
OUT_JSON = DATA_DIR / "q15_map_signal_redesign_proof.json"
OUT_MD = DOCS_ANALYSIS_DIR / "q15_map_signal_redesign_proof.md"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _round_optional(value: Any, digits: int = 4) -> float | None:
    try:
        if value is None:
            return None
        return round(float(value), digits)
    except Exception:
        return None


def _metric_gate(metrics: dict[str, Any], minimum_support_rows: int) -> bool:
    rows = _as_int(metrics.get("rows"), 0)
    win_rate = _round_optional(metrics.get("win_rate"))
    avg_pnl = _round_optional(metrics.get("avg_pnl"))
    avg_drawdown_penalty = _round_optional(metrics.get("avg_drawdown_penalty"))
    return bool(
        rows >= minimum_support_rows
        and win_rate is not None
        and win_rate >= 0.55
        and avg_pnl is not None
        and avg_pnl > 0
        and (avg_drawdown_penalty is None or avg_drawdown_penalty <= 0.25)
    )


def _metric_rejected(metrics: dict[str, Any]) -> bool:
    rows = _as_int(metrics.get("rows"), 0)
    if rows <= 0:
        return False
    win_rate = _round_optional(metrics.get("win_rate"))
    avg_pnl = _round_optional(metrics.get("avg_pnl"))
    avg_drawdown_penalty = _round_optional(metrics.get("avg_drawdown_penalty"))
    return bool(
        (win_rate is not None and win_rate < 0.55)
        or (avg_pnl is not None and avg_pnl <= 0)
        or (avg_drawdown_penalty is not None and avg_drawdown_penalty > 0.25)
    )


def _window_keys(rows: list[dict[str, Any]], support_identity: dict[str, Any]) -> list[int]:
    current_window = _as_int(support_identity.get("calibration_window"), 0)
    windows = {int(window) for window in SCAN_WINDOWS if int(window) > 0}
    if current_window > 0:
        windows.add(current_window)
    if rows:
        windows.add(len(rows))
    return sorted(windows)


def _matches_candidate(row: dict[str, Any], candidate: dict[str, Any], identity: dict[str, Any]) -> bool:
    for field in candidate.get("exact_fields") or []:
        if field == "regime_label" and row.get("regime_label") != identity.get("regime_label"):
            return False
        if field == "regime_gate" and row.get("regime_gate") != identity.get("regime_gate"):
            return False
        if field == "entry_quality_label" and row.get("entry_quality_label") != identity.get("entry_quality_label"):
            return False
        if field == "current_live_structure_bucket" and row.get("structure_bucket") != identity.get("current_live_structure_bucket"):
            return False
        if field == "target_bucket" and row.get("structure_bucket") != candidate.get("target_bucket"):
            return False
        if field == "bucket_suffix" and not str(row.get("structure_bucket") or "").endswith(str(candidate.get("bucket_suffix") or "")):
            return False
    return True


def _evaluate_candidate_windows(
    *,
    rows: list[dict[str, Any]],
    candidate: dict[str, Any],
    support_identity: dict[str, Any],
    minimum_support_rows: int,
) -> dict[str, Any]:
    current_window = _as_int(support_identity.get("calibration_window"), 0)
    evaluations: dict[str, Any] = {}
    for window in _window_keys(rows, support_identity):
        scoped_rows = rows[: min(window, len(rows))]
        matched_rows = [row for row in scoped_rows if _matches_candidate(row, candidate, support_identity)]
        metrics = _metric_summary(matched_rows)
        evaluation = {
            "window": window,
            "same_as_current_calibration_window": window == current_window,
            "rows": len(matched_rows),
            "rows_needed_to_minimum": max(minimum_support_rows - len(matched_rows), 0),
            "ready_by_count": len(matched_rows) >= minimum_support_rows,
            "metric_gate_candidate": _metric_gate(metrics, minimum_support_rows),
            "metric_rejected": _metric_rejected(metrics),
            "metrics": metrics,
            "latest_timestamp": matched_rows[0].get("timestamp") if matched_rows else None,
            "oldest_timestamp": matched_rows[-1].get("timestamp") if matched_rows else None,
        }
        evaluations[str(window)] = evaluation
        if window == len(rows):
            evaluations["all"] = evaluation
    return evaluations


def _candidate_status(
    *,
    candidate: dict[str, Any],
    evaluations: dict[str, Any],
    current_window_key: str,
    minimum_support_rows: int,
) -> str:
    if candidate.get("id") == "current_exact_identity_window":
        return "baseline_current_identity"
    current_eval = evaluations.get(current_window_key) or {}
    all_eval = evaluations.get("all") or {}
    current_rows = _as_int(current_eval.get("rows"), 0)
    if current_eval.get("metric_gate_candidate"):
        return "current_window_replay_candidate_not_deployable"
    if all_eval.get("metric_gate_candidate"):
        if current_rows <= 0:
            return "reference_candidate_current_window_empty"
        if current_eval.get("metric_rejected"):
            return "reference_candidate_current_window_metric_rejected"
        if current_rows < minimum_support_rows:
            return "reference_candidate_current_window_under_minimum"
        return "reference_candidate_current_window_metric_rejected"
    if current_eval.get("ready_by_count") and current_eval.get("metric_rejected"):
        return "current_window_count_ready_metric_rejected"
    if all_eval.get("ready_by_count"):
        return "count_ready_metric_rejected"
    return "insufficient_rows"


def _candidate_matrix(
    *,
    rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    support_identity: dict[str, Any],
    minimum_support_rows: int,
) -> list[dict[str, Any]]:
    current_window_key = str(_as_int(support_identity.get("calibration_window"), 0))
    matrix: list[dict[str, Any]] = []
    for candidate in candidates:
        evaluations = _evaluate_candidate_windows(
            rows=rows,
            candidate=candidate,
            support_identity=support_identity,
            minimum_support_rows=minimum_support_rows,
        )
        matrix.append(
            {
                "id": candidate.get("id"),
                "description": candidate.get("description"),
                "redesign_type": candidate.get("redesign_type"),
                "evidence_role": candidate.get("evidence_role"),
                "target_bucket": candidate.get("target_bucket"),
                "bucket_suffix": candidate.get("bucket_suffix"),
                "exact_fields": candidate.get("exact_fields") or [],
                "relaxed_fields": candidate.get("relaxed_fields") or [],
                "source": candidate.get("source"),
                "status": _candidate_status(
                    candidate=candidate,
                    evaluations=evaluations,
                    current_window_key=current_window_key,
                    minimum_support_rows=minimum_support_rows,
                ),
                "deployable_support": False,
                "live_exposure_allowed": False,
                "window_evaluations": evaluations,
            }
        )
    return matrix


def _exact_lane_bucket_counts(rows: list[dict[str, Any]], identity: dict[str, Any]) -> Counter:
    exact_lane_rows = [
        row
        for row in rows
        if row.get("regime_label") == identity.get("regime_label")
        and row.get("regime_gate") == identity.get("regime_gate")
        and row.get("entry_quality_label") == identity.get("entry_quality_label")
    ]
    return Counter(str(row.get("structure_bucket")) for row in exact_lane_rows if row.get("structure_bucket"))


def _best_historical_exact_lane_bucket(
    *,
    rows: list[dict[str, Any]],
    identity: dict[str, Any],
    exclude: set[str],
    minimum_support_rows: int,
) -> str | None:
    scored: list[tuple[int, float, float, str]] = []
    for bucket, count in _exact_lane_bucket_counts(rows, identity).items():
        if bucket in exclude:
            continue
        matched = [
            row
            for row in rows
            if row.get("regime_label") == identity.get("regime_label")
            and row.get("regime_gate") == identity.get("regime_gate")
            and row.get("entry_quality_label") == identity.get("entry_quality_label")
            and row.get("structure_bucket") == bucket
        ]
        metrics = _metric_summary(matched)
        if count < minimum_support_rows:
            continue
        win_rate = _round_optional(metrics.get("win_rate")) or 0.0
        avg_pnl = _round_optional(metrics.get("avg_pnl")) or 0.0
        scored.append((count, win_rate, avg_pnl, bucket))
    if not scored:
        return None
    scored.sort(key=lambda item: (item[1], item[2], item[0], item[3]), reverse=True)
    return scored[0][3]


def _candidate_inputs(
    *,
    rows: list[dict[str, Any]],
    support_identity: dict[str, Any],
    q15_root_cause: dict[str, Any],
    drift_rebaseline: dict[str, Any],
    minimum_support_rows: int,
) -> list[dict[str, Any]]:
    current_bucket = support_identity.get("current_live_structure_bucket")
    exact_lane = q15_root_cause.get("exact_live_lane") if isinstance(q15_root_cause.get("exact_live_lane"), dict) else {}
    dominant_neighbor_bucket = exact_lane.get("dominant_neighbor_bucket")
    drift_verdict = drift_rebaseline.get("verdict") if isinstance(drift_rebaseline.get("verdict"), dict) else {}
    semantic_candidate_id = drift_verdict.get("selected_candidate_id") or "semantic_entry_quality_family"

    candidates: list[dict[str, Any]] = [
        {
            "id": "current_exact_identity_window",
            "description": "Baseline: current calibration window plus exact regime/gate/entry/bucket identity.",
            "redesign_type": "none",
            "evidence_role": "current_deployable_identity_baseline",
            "target_bucket": current_bucket,
            "exact_fields": ["regime_label", "regime_gate", "entry_quality_label", "current_live_structure_bucket"],
            "relaxed_fields": [],
            "source": "current_support_identity",
        },
        {
            "id": str(semantic_candidate_id),
            "description": "Treat entry quality as a semantic family inside the current regime/gate/bucket.",
            "redesign_type": "semantic_entry_quality_family",
            "evidence_role": "research_candidate_semantic_adapter_required",
            "target_bucket": current_bucket,
            "exact_fields": ["regime_label", "regime_gate", "current_live_structure_bucket"],
            "relaxed_fields": ["entry_quality_label", "calibration_window"],
            "source": "q15_drift_rebaseline_backtest",
        },
    ]

    exclude = {str(current_bucket or "")}
    if dominant_neighbor_bucket:
        exclude.add(str(dominant_neighbor_bucket))
        candidates.extend(
            [
                {
                    "id": "dominant_neighbor_exact_lane",
                    "description": "Root-cause candidate: map current exact lane to the dominant neighboring structure bucket.",
                    "redesign_type": "bucket_map_neighbor",
                    "evidence_role": "root_cause_map_signal_candidate",
                    "target_bucket": dominant_neighbor_bucket,
                    "exact_fields": ["regime_label", "regime_gate", "entry_quality_label", "target_bucket"],
                    "relaxed_fields": ["current_live_structure_bucket", "calibration_window"],
                    "source": "q15_bucket_root_cause.exact_live_lane.dominant_neighbor_bucket",
                },
                {
                    "id": "dominant_neighbor_semantic_family",
                    "description": "Root-cause candidate with entry-quality family relaxation inside the dominant neighboring bucket.",
                    "redesign_type": "bucket_map_neighbor_semantic",
                    "evidence_role": "higher_risk_semantic_map_candidate",
                    "target_bucket": dominant_neighbor_bucket,
                    "exact_fields": ["regime_label", "regime_gate", "target_bucket"],
                    "relaxed_fields": ["entry_quality_label", "current_live_structure_bucket", "calibration_window"],
                    "source": "q15_bucket_root_cause.exact_live_lane.dominant_neighbor_bucket",
                },
            ]
        )

    candidates.extend(
        [
            {
                "id": "q35_boundary_exact_lane",
                "description": "Boundary-review candidate: exact lane rows that already land in q35-style structure buckets.",
                "redesign_type": "q35_boundary_review",
                "evidence_role": "boundary_reference_requires_counterfactual",
                "bucket_suffix": "|q35",
                "exact_fields": ["regime_label", "regime_gate", "entry_quality_label", "bucket_suffix"],
                "relaxed_fields": ["current_live_structure_bucket", "calibration_window"],
                "source": "q15_bucket_root_cause.boundary_review",
            },
            {
                "id": "q35_regime_gate_family",
                "description": "Boundary-review candidate: same regime/gate q35-style rows with entry-quality relaxation.",
                "redesign_type": "q35_boundary_semantic_family",
                "evidence_role": "higher_risk_boundary_reference",
                "bucket_suffix": "|q35",
                "exact_fields": ["regime_label", "regime_gate", "bucket_suffix"],
                "relaxed_fields": ["entry_quality_label", "current_live_structure_bucket", "calibration_window"],
                "source": "q15_bucket_root_cause.boundary_review",
            },
        ]
    )

    best_bucket = _best_historical_exact_lane_bucket(
        rows=rows,
        identity=support_identity,
        exclude=exclude,
        minimum_support_rows=minimum_support_rows,
    )
    if best_bucket:
        candidates.append(
            {
                "id": "best_historical_exact_lane_bucket",
                "description": "Highest historical exact-lane bucket by rows/win/pnl after excluding current and root-cause neighbor buckets.",
                "redesign_type": "historical_bucket_map_reference",
                "evidence_role": "reference_only_bucket_map_candidate",
                "target_bucket": best_bucket,
                "exact_fields": ["regime_label", "regime_gate", "entry_quality_label", "target_bucket"],
                "relaxed_fields": ["current_live_structure_bucket", "calibration_window"],
                "source": "historical_exact_lane_bucket_scan",
            }
        )
    return candidates


def _select_candidate(matrix: list[dict[str, Any]]) -> dict[str, Any] | None:
    replay_ready = [item for item in matrix if item.get("status") == "current_window_replay_candidate_not_deployable"]
    if replay_ready:
        return replay_ready[0]
    root_candidate = next((item for item in matrix if item.get("id") == "dominant_neighbor_exact_lane"), None)
    if root_candidate:
        return root_candidate
    preferred = {
        "reference_candidate_current_window_metric_rejected",
        "reference_candidate_current_window_under_minimum",
        "reference_candidate_current_window_empty",
        "count_ready_metric_rejected",
    }
    return next((item for item in matrix if item.get("status") in preferred), None)


def _best_reference_candidate(matrix: list[dict[str, Any]]) -> dict[str, Any] | None:
    reference = []
    for item in matrix:
        all_eval = (item.get("window_evaluations") or {}).get("all") or {}
        if all_eval.get("metric_gate_candidate"):
            metrics = all_eval.get("metrics") or {}
            reference.append(
                (
                    _round_optional(metrics.get("win_rate")) or 0.0,
                    _round_optional(metrics.get("avg_pnl")) or 0.0,
                    _as_int(all_eval.get("rows"), 0),
                    item,
                )
            )
    if not reference:
        return None
    reference.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    return reference[0][3]


def _verdict(
    *,
    selected: dict[str, Any] | None,
    best_reference: dict[str, Any] | None,
    support_identity: dict[str, Any],
    q15_root_cause: dict[str, Any],
    support_fill: dict[str, Any],
    minimum_support_rows: int,
) -> dict[str, Any]:
    current_window_key = str(_as_int(support_identity.get("calibration_window"), 0))
    selected_windows = (selected or {}).get("window_evaluations", {}) if selected else {}
    selected_current = selected_windows.get(current_window_key, {})
    selected_all = selected_windows.get("all", {})
    best_windows = (best_reference or {}).get("window_evaluations", {}) if best_reference else {}
    best_current = best_windows.get(current_window_key, {})
    best_all = best_windows.get("all", {})
    fill_verdict = support_fill.get("verdict") if isinstance(support_fill.get("verdict"), dict) else {}
    current_exact_rows = _as_int(fill_verdict.get("current_exact_bucket_rows"), 0)

    if selected and selected.get("status") == "current_window_replay_candidate_not_deployable":
        status = "map_signal_candidate_requires_oos_replay_not_deployable"
        decision = "A redesign candidate has current-window rows and basic metrics, but it still requires OOS/Top-K/support/API replay and cannot release live buy/add."
        primary_failed_gate = "oos_replay_required_before_live"
    elif selected and selected.get("status") == "reference_candidate_current_window_metric_rejected":
        status = "map_signal_redesign_reference_only_current_window_rejected"
        decision = "The root-cause map/signal candidate is historically plausible but current-window metrics reject it; keep live fail-closed and do not promote the redesign."
        primary_failed_gate = "current_window_metric_gate"
    elif selected and selected.get("status") in {
        "reference_candidate_current_window_empty",
        "reference_candidate_current_window_under_minimum",
    }:
        status = "map_signal_redesign_reference_only_current_window_unproven"
        decision = "A map/signal redesign candidate exists only as historical/reference evidence; current-window support is empty or under-minimum."
        primary_failed_gate = "current_window_support_gate"
    elif selected:
        status = "map_signal_redesign_no_current_window_deployable_candidate"
        decision = "Map/signal candidates were evaluated but none passed current-window support and metric gates."
        primary_failed_gate = "current_live_support_gate"
    else:
        status = "map_signal_redesign_no_candidate_found"
        decision = "No usable map/signal redesign candidate was found; keep exact-row harvest or hard no-go as the forced branch."
        primary_failed_gate = "map_signal_candidate_missing"

    root_lane = q15_root_cause.get("exact_live_lane") if isinstance(q15_root_cause.get("exact_live_lane"), dict) else {}
    return {
        "status": status,
        "decision": decision,
        "selected_candidate_id": selected.get("id") if selected else None,
        "selected_candidate_status": selected.get("status") if selected else None,
        "selected_redesign_type": selected.get("redesign_type") if selected else None,
        "selected_target_bucket": selected.get("target_bucket") if selected else None,
        "selected_current_window_rows": selected_current.get("rows"),
        "selected_all_history_rows": selected_all.get("rows"),
        "selected_current_window_metrics": selected_current.get("metrics"),
        "selected_all_history_metrics": selected_all.get("metrics"),
        "best_reference_candidate_id": best_reference.get("id") if best_reference else None,
        "best_reference_target_bucket": best_reference.get("target_bucket") if best_reference else None,
        "best_reference_current_window_rows": best_current.get("rows"),
        "best_reference_all_history_rows": best_all.get("rows"),
        "best_reference_all_history_metrics": best_all.get("metrics"),
        "current_exact_bucket_rows": current_exact_rows,
        "minimum_support_rows": minimum_support_rows,
        "gap_to_minimum": max(minimum_support_rows - current_exact_rows, 0),
        "root_cause_verdict": q15_root_cause.get("verdict"),
        "root_cause_candidate_patch_type": q15_root_cause.get("candidate_patch_type"),
        "root_cause_candidate_patch_feature": q15_root_cause.get("candidate_patch_feature"),
        "root_cause_dominant_neighbor_bucket": root_lane.get("dominant_neighbor_bucket"),
        "root_cause_dominant_neighbor_rows": root_lane.get("dominant_neighbor_rows"),
        "root_cause_near_boundary_rows": root_lane.get("near_boundary_rows"),
        "deployable": False,
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "primary_failed_gate": primary_failed_gate,
        "branch_id": "map_signal_redesign_proof",
        "branch_status": "delivered_no_current_window_deployable",
    }


def _recent_drift_context(recent_drift: dict[str, Any]) -> dict[str, Any]:
    windows = recent_drift.get("windows") if isinstance(recent_drift.get("windows"), dict) else {}
    latest = windows.get("100") or {}
    compact = latest.get("compact_summary") if isinstance(latest.get("compact_summary"), dict) else {}
    return {
        "source_generated_at": recent_drift.get("generated_at"),
        "window": 100 if latest else None,
        "win_rate": latest.get("win_rate") if latest else compact.get("win_rate"),
        "dominant_regime": latest.get("dominant_regime") if latest else compact.get("dominant_regime"),
        "dominant_regime_share": latest.get("dominant_regime_share") if latest else compact.get("dominant_regime_share"),
        "alerts": latest.get("alerts") or compact.get("alerts") or [],
    }


def build_report(
    *,
    rows: list[dict[str, Any]],
    support_identity: dict[str, Any],
    q15_root_cause: dict[str, Any] | None = None,
    support_fill: dict[str, Any] | None = None,
    drift_rebaseline: dict[str, Any] | None = None,
    recent_drift: dict[str, Any] | None = None,
    db_meta: dict[str, Any] | None = None,
    source_artifacts: dict[str, Any] | None = None,
    generated_at: str | None = None,
    minimum_support_rows: int = DEFAULT_MINIMUM_SUPPORT_ROWS,
) -> dict[str, Any]:
    q15_root_cause = q15_root_cause or {}
    support_fill = support_fill or {}
    drift_rebaseline = drift_rebaseline or {}
    recent_drift = recent_drift or {}
    candidates = _candidate_inputs(
        rows=rows,
        support_identity=support_identity,
        q15_root_cause=q15_root_cause,
        drift_rebaseline=drift_rebaseline,
        minimum_support_rows=minimum_support_rows,
    )
    matrix = _candidate_matrix(
        rows=rows,
        candidates=candidates,
        support_identity=support_identity,
        minimum_support_rows=minimum_support_rows,
    )
    selected = _select_candidate(matrix)
    best_reference = _best_reference_candidate(matrix)
    report_verdict = _verdict(
        selected=selected,
        best_reference=best_reference,
        support_identity=support_identity,
        q15_root_cause=q15_root_cause,
        support_fill=support_fill,
        minimum_support_rows=minimum_support_rows,
    )
    return {
        "generated_at": generated_at or _utc_now_iso(),
        "artifact": "q15_map_signal_redesign_proof",
        "source_artifacts": source_artifacts or {},
        "support_identity": support_identity,
        "data_coverage": {
            "joined_labeled_rows": len(rows),
            "db_meta": db_meta or {},
        },
        "recent_drift_context": _recent_drift_context(recent_drift),
        "root_cause_context": {
            "artifact": q15_root_cause.get("artifact") or "q15_bucket_root_cause",
            "generated_at": q15_root_cause.get("generated_at"),
            "verdict": q15_root_cause.get("verdict"),
            "candidate_patch_type": q15_root_cause.get("candidate_patch_type"),
            "candidate_patch_feature": q15_root_cause.get("candidate_patch_feature"),
            "candidate_patch": q15_root_cause.get("candidate_patch"),
            "exact_live_lane": q15_root_cause.get("exact_live_lane") or {},
        },
        "verdict": report_verdict,
        "candidate_matrix": matrix,
        "promotion_requirements": [
            "declare a new support identity or bucket-map contract before counting any redesign rows",
            "rerun live probe, q15 support audit, drift rebaseline, walk-forward Top-K, and API/trade guardrail checks",
            "require current calibration-window support and metric gates before any replay candidate can be promoted",
            "keep live buy/add disabled until support, breaker, model, venue lifecycle, and bounded live-canary policy gates all pass",
        ],
        "forbidden_shortcuts": [
            "lower_minimum_support_rows",
            "count_neighbor_or_q35_reference_rows_as_current_exact_support",
            "enable_live_buy_or_add_from_map_signal_proof_alone",
        ],
        "recommended_actions": [
            {
                "id": "reject_current_window_metric_failed_map",
                "priority": "P0" if report_verdict.get("primary_failed_gate") == "current_window_metric_gate" else "P1",
                "selected_candidate_id": report_verdict.get("selected_candidate_id"),
                "selected_target_bucket": report_verdict.get("selected_target_bucket"),
                "live_exposure_allowed": False,
                "success_condition": "If the root-cause map candidate fails current-window metrics, keep it reference-only and move to a different signal redesign or hard no-go.",
            },
            {
                "id": "rerun_oos_if_current_window_candidate_emerges",
                "priority": "P0",
                "best_reference_candidate_id": report_verdict.get("best_reference_candidate_id"),
                "live_exposure_allowed": False,
                "success_condition": "Only a candidate with current-window rows, metrics, OOS replay, support audit, and API guardrail proof may move toward canary readiness.",
            },
        ],
    }


def markdown(report: dict[str, Any]) -> str:
    verdict = report.get("verdict") or {}
    root = report.get("root_cause_context") or {}
    lane = root.get("exact_live_lane") if isinstance(root.get("exact_live_lane"), dict) else {}
    lines = [
        "# q15 Map/Signal redesign proof",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- verdict: **{verdict.get('status')}**",
        f"- decision: {verdict.get('decision')}",
        f"- selected_candidate_id: `{verdict.get('selected_candidate_id')}`",
        f"- selected_target_bucket: `{verdict.get('selected_target_bucket')}`",
        f"- selected_current_window_rows: **{verdict.get('selected_current_window_rows')}**",
        f"- selected_all_history_rows: **{verdict.get('selected_all_history_rows')}**",
        f"- best_reference_candidate_id: `{verdict.get('best_reference_candidate_id')}`",
        f"- current exact support: **{verdict.get('current_exact_bucket_rows')}/{verdict.get('minimum_support_rows')}**",
        f"- live_exposure_allowed: **{verdict.get('live_exposure_allowed')}**",
        f"- order_submission_enabled: **{verdict.get('order_submission_enabled')}**",
        "",
        "## Root-cause context",
        "",
        f"- root verdict: `{root.get('verdict')}`",
        f"- candidate_patch_type: `{root.get('candidate_patch_type')}`",
        f"- candidate_patch_feature: `{root.get('candidate_patch_feature')}`",
        f"- dominant_neighbor_bucket: `{lane.get('dominant_neighbor_bucket')}`",
        f"- dominant_neighbor_rows: `{lane.get('dominant_neighbor_rows')}`",
        f"- near_boundary_rows: `{lane.get('near_boundary_rows')}`",
        "",
        "## Candidate matrix",
        "",
        "| candidate | status | target | current rows | all rows | all win rate | current win rate | deployable |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    current_window_key = str((report.get("support_identity") or {}).get("calibration_window") or "")
    for candidate in report.get("candidate_matrix") or []:
        windows = candidate.get("window_evaluations") or {}
        current = windows.get(current_window_key) or {}
        all_eval = windows.get("all") or {}
        current_metrics = current.get("metrics") or {}
        all_metrics = all_eval.get("metrics") or {}
        target = candidate.get("target_bucket") or candidate.get("bucket_suffix") or ""
        lines.append(
            "| "
            f"`{candidate.get('id')}` | "
            f"`{candidate.get('status')}` | "
            f"`{target}` | "
            f"{current.get('rows')} | "
            f"{all_eval.get('rows')} | "
            f"{all_metrics.get('win_rate')} | "
            f"{current_metrics.get('win_rate')} | "
            f"{candidate.get('deployable_support')} |"
        )
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "This artifact is not deployment clearance. It is a forced-branch proof that evaluates redesign candidates while preserving current exact support as the live gate.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    probe = _load_json(PROBE_PATH)
    q15_audit = _load_json(Q15_AUDIT_PATH)
    support_fill = _load_json(SUPPORT_FILL_PATH)
    drift_rebaseline = _load_json(DRIFT_REBASELINE_PATH)
    q15_root_cause = _load_json(Q15_ROOT_CAUSE_PATH)
    recent_drift = _load_json(RECENT_DRIFT_PATH)
    support_identity = support_identity_from_artifacts(probe, q15_audit)
    minimum_support_rows = _as_int(
        (support_fill.get("verdict") or {}).get("minimum_support_rows")
        or (q15_audit.get("support_route") or {}).get("minimum_support_rows"),
        DEFAULT_MINIMUM_SUPPORT_ROWS,
    )
    rows = fetch_labeled_decision_rows(
        horizon_minutes=_as_int(support_identity.get("horizon_minutes"), DEFAULT_HORIZON_MINUTES)
    )
    report = build_report(
        rows=rows,
        support_identity=support_identity,
        q15_root_cause=q15_root_cause,
        support_fill=support_fill,
        drift_rebaseline=drift_rebaseline,
        recent_drift=recent_drift,
        db_meta=fetch_db_meta(),
        source_artifacts={
            "live_predict_probe_path": str(PROBE_PATH.relative_to(PROJECT_ROOT)),
            "live_predict_probe_generated_at": probe.get("generated_at"),
            "q15_support_audit_path": str(Q15_AUDIT_PATH.relative_to(PROJECT_ROOT)),
            "q15_support_audit_generated_at": q15_audit.get("generated_at"),
            "q15_bucket_root_cause_path": str(Q15_ROOT_CAUSE_PATH.relative_to(PROJECT_ROOT)),
            "q15_bucket_root_cause_generated_at": q15_root_cause.get("generated_at"),
            "q15_drift_rebaseline_backtest_path": str(DRIFT_REBASELINE_PATH.relative_to(PROJECT_ROOT)),
            "q15_drift_rebaseline_backtest_generated_at": drift_rebaseline.get("generated_at"),
            "recent_drift_report_path": str(RECENT_DRIFT_PATH.relative_to(PROJECT_ROOT)),
            "recent_drift_report_generated_at": recent_drift.get("generated_at"),
        },
        minimum_support_rows=minimum_support_rows,
    )
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown(report), encoding="utf-8")
    verdict = report.get("verdict") or {}
    print(
        "q15_map_signal_redesign_proof: "
        f"status={verdict.get('status')} "
        f"selected={verdict.get('selected_candidate_id')} "
        f"target={verdict.get('selected_target_bucket')} "
        f"current_window_rows={verdict.get('selected_current_window_rows')} "
        f"all_rows={verdict.get('selected_all_history_rows')} "
        f"live_exposure_allowed={verdict.get('live_exposure_allowed')} "
        f"json={OUT_JSON} md={OUT_MD}"
    )


if __name__ == "__main__":
    main()
