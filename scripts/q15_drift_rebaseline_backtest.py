#!/usr/bin/env python3
"""Produce a drift-aware q15 rebaseline proof without relaxing live gates.

This forced-branch artifact answers the anti-equilibrium question raised by the
q15 support audit: if the current exact support identity remains 0/50, is there
a structurally plausible semantic/rebaseline candidate, and does it still have
fresh-window evidence?  The answer is governance-only.  It never turns
reference/proxy rows into deployable support and never enables live buy/add.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

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
    _support_identity_compression_proof,
    fetch_db_meta,
    fetch_labeled_decision_rows,
    support_identity_from_artifacts,
)

DATA_DIR = PROJECT_ROOT / "data"
DOCS_ANALYSIS_DIR = PROJECT_ROOT / "docs" / "analysis"
PROBE_PATH = DATA_DIR / "live_predict_probe.json"
Q15_AUDIT_PATH = DATA_DIR / "q15_support_audit.json"
SUPPORT_FILL_PATH = DATA_DIR / "q15_support_fill_feasibility.json"
RECENT_DRIFT_PATH = DATA_DIR / "recent_drift_report.json"
OUT_JSON = DATA_DIR / "q15_drift_rebaseline_backtest.json"
OUT_MD = DOCS_ANALYSIS_DIR / "q15_drift_rebaseline_backtest.md"


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


def _matches_candidate(row: dict[str, Any], candidate: dict[str, Any], identity: dict[str, Any]) -> bool:
    for field in candidate.get("exact_fields") or []:
        if field == "calibration_window":
            continue
        if field == "regime_label" and row.get("regime_label") != identity.get("regime_label"):
            return False
        if field == "regime_gate" and row.get("regime_gate") != identity.get("regime_gate"):
            return False
        if field == "entry_quality_label" and row.get("entry_quality_label") != identity.get("entry_quality_label"):
            return False
        if field == "current_live_structure_bucket" and row.get("structure_bucket") != identity.get("current_live_structure_bucket"):
            return False
    return True


def _window_keys(rows: list[dict[str, Any]], support_identity: dict[str, Any]) -> list[int]:
    current_window = _as_int(support_identity.get("calibration_window"), 0)
    windows = {int(window) for window in SCAN_WINDOWS if int(window) > 0}
    if current_window > 0:
        windows.add(current_window)
    if rows:
        windows.add(len(rows))
    return sorted(windows)


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
) -> str:
    if candidate.get("id") == "current_exact_identity_window":
        return "baseline_current_identity"
    all_eval = evaluations.get("all") or {}
    current_eval = evaluations.get(current_window_key) or {}
    if all_eval.get("metric_gate_candidate") and current_eval.get("metric_gate_candidate"):
        return "candidate_ready_for_oos_replay_not_deployable"
    if all_eval.get("metric_gate_candidate") and _as_int(current_eval.get("rows"), 0) <= 0:
        return "reference_candidate_current_window_empty"
    if all_eval.get("metric_gate_candidate"):
        return "reference_candidate_current_window_under_minimum"
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
                "evidence_role": candidate.get("evidence_role"),
                "exact_fields": candidate.get("exact_fields") or [],
                "relaxed_fields": candidate.get("relaxed_fields") or [],
                "source_compression_rows": candidate.get("rows"),
                "source_metric_gate_candidate": candidate.get("metric_gate_candidate"),
                "status": _candidate_status(
                    candidate=candidate,
                    evaluations=evaluations,
                    current_window_key=current_window_key,
                ),
                "deployable_support": False,
                "live_exposure_allowed": False,
                "window_evaluations": evaluations,
            }
        )
    return matrix


def _recent_drift_context(recent_drift: dict[str, Any]) -> dict[str, Any]:
    windows = recent_drift.get("windows") if isinstance(recent_drift.get("windows"), dict) else {}
    latest = windows.get("100") or {}
    quality = latest.get("quality_metrics") if isinstance(latest.get("quality_metrics"), dict) else {}
    compact = latest.get("compact_summary") if isinstance(latest.get("compact_summary"), dict) else {}
    return {
        "source_generated_at": recent_drift.get("generated_at"),
        "window": 100 if latest else None,
        "win_rate": latest.get("win_rate") if latest else compact.get("win_rate"),
        "dominant_regime": latest.get("dominant_regime") if latest else compact.get("dominant_regime"),
        "dominant_regime_share": latest.get("dominant_regime_share") if latest else compact.get("dominant_regime_share"),
        "avg_pnl": quality.get("avg_simulated_pnl"),
        "avg_quality": quality.get("avg_simulated_quality"),
        "avg_drawdown_penalty": quality.get("avg_drawdown_penalty"),
        "alerts": latest.get("alerts") or compact.get("alerts") or [],
    }


def _select_candidate(
    matrix: list[dict[str, Any]],
    support_fill: dict[str, Any],
) -> dict[str, Any] | None:
    selected_id = (support_fill.get("support_identity_compression_proof") or {}).get("selected_candidate_id")
    if selected_id:
        selected = next((candidate for candidate in matrix if candidate.get("id") == selected_id), None)
        if selected:
            return selected
    preferred_statuses = {
        "candidate_ready_for_oos_replay_not_deployable",
        "reference_candidate_current_window_under_minimum",
        "reference_candidate_current_window_empty",
    }
    return next((candidate for candidate in matrix if candidate.get("status") in preferred_statuses), None)


def _verdict(
    *,
    selected: dict[str, Any] | None,
    support_fill: dict[str, Any],
    support_identity: dict[str, Any],
    minimum_support_rows: int,
) -> dict[str, Any]:
    fill_verdict = support_fill.get("verdict") if isinstance(support_fill.get("verdict"), dict) else {}
    current_rows = _as_int(fill_verdict.get("current_exact_bucket_rows"), 0)
    current_window_key = str(_as_int(support_identity.get("calibration_window"), 0))
    selected_current = (selected or {}).get("window_evaluations", {}).get(current_window_key, {}) if selected else {}
    selected_all = (selected or {}).get("window_evaluations", {}).get("all", {}) if selected else {}
    if current_rows >= minimum_support_rows:
        status = "current_identity_support_ready_rebaseline_not_needed"
        decision = "current exact support already meets minimum; rebaseline proof is not the primary gate, but live buy/add still waits for remaining gates."
    elif selected is None:
        status = "no_rebaseline_candidate_found"
        decision = "No semantic/rebaseline candidate has enough evidence; keep exact-row harvest or hard no-go as the forced branch."
    elif selected.get("status") == "candidate_ready_for_oos_replay_not_deployable":
        status = "candidate_requires_oos_replay_not_deployable"
        decision = "A drift-window candidate has enough rows and basic metrics, but it still requires OOS/Top-K/support-audit/API guardrail replay before any deployment claim."
    else:
        status = "reference_candidate_found_but_current_window_unproven"
        decision = "A historical semantic candidate exists, but current calibration-window evidence is empty or under-minimum; it is reference-only and cannot release live buy/add."
    return {
        "status": status,
        "decision": decision,
        "selected_candidate_id": selected.get("id") if selected else None,
        "selected_candidate_status": selected.get("status") if selected else None,
        "selected_candidate_evidence_role": selected.get("evidence_role") if selected else None,
        "selected_all_history_rows": selected_all.get("rows"),
        "selected_current_window_rows": selected_current.get("rows"),
        "selected_current_window_key": current_window_key,
        "current_exact_bucket_rows": current_rows,
        "minimum_support_rows": minimum_support_rows,
        "gap_to_minimum": max(minimum_support_rows - current_rows, 0),
        "deployable": False,
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "primary_failed_gate": "current_live_support_gate",
        "branch_id": "drift_rebaseline_backtest",
        "branch_status": "delivered_reference_only",
    }


def _candidate_inputs(
    *,
    rows: list[dict[str, Any]],
    support_fill: dict[str, Any],
    support_identity: dict[str, Any],
    minimum_support_rows: int,
) -> list[dict[str, Any]]:
    proof = support_fill.get("support_identity_compression_proof")
    if isinstance(proof, dict) and isinstance(proof.get("candidates"), list):
        return [item for item in proof["candidates"] if isinstance(item, dict)]
    current_window = _as_int(support_identity.get("calibration_window"), 0)
    current_rows = rows[: min(current_window, len(rows))] if current_window > 0 else []
    generated = _support_identity_compression_proof(
        rows=rows,
        current_rows=current_rows,
        support_identity=support_identity,
        minimum_support_rows=minimum_support_rows,
    )
    return [item for item in generated.get("candidates") or [] if isinstance(item, dict)]


def build_report(
    *,
    rows: list[dict[str, Any]],
    support_identity: dict[str, Any],
    support_fill: dict[str, Any] | None = None,
    q15_support_audit: dict[str, Any] | None = None,
    recent_drift: dict[str, Any] | None = None,
    db_meta: dict[str, Any] | None = None,
    source_artifacts: dict[str, Any] | None = None,
    generated_at: str | None = None,
    minimum_support_rows: int = DEFAULT_MINIMUM_SUPPORT_ROWS,
) -> dict[str, Any]:
    support_fill = support_fill or {}
    q15_support_audit = q15_support_audit or {}
    recent_drift = recent_drift or {}
    candidates = _candidate_inputs(
        rows=rows,
        support_fill=support_fill,
        support_identity=support_identity,
        minimum_support_rows=minimum_support_rows,
    )
    matrix = _candidate_matrix(
        rows=rows,
        candidates=candidates,
        support_identity=support_identity,
        minimum_support_rows=minimum_support_rows,
    )
    selected = _select_candidate(matrix, support_fill)
    report_verdict = _verdict(
        selected=selected,
        support_fill=support_fill,
        support_identity=support_identity,
        minimum_support_rows=minimum_support_rows,
    )
    forced_branch = q15_support_audit.get("forced_branch_decision") if isinstance(q15_support_audit.get("forced_branch_decision"), dict) else {}
    return {
        "generated_at": generated_at or _utc_now_iso(),
        "artifact": "q15_drift_rebaseline_backtest",
        "source_artifacts": source_artifacts or {},
        "support_identity": support_identity,
        "data_coverage": {
            "joined_labeled_rows": len(rows),
            "db_meta": db_meta or {},
        },
        "current_forced_branch": {
            "status": forced_branch.get("status"),
            "selected_branch": forced_branch.get("selected_branch"),
            "single_failed_gate": forced_branch.get("single_failed_gate"),
            "decision_clock": forced_branch.get("decision_clock"),
        },
        "recent_drift_context": _recent_drift_context(recent_drift),
        "verdict": report_verdict,
        "candidate_matrix": matrix,
        "promotion_requirements": [
            "declare a new support_identity / semantic bucket contract before using any relaxed candidate",
            "rerun drift-aware replay, walk-forward OOS Top-K, q15 support audit, live probe, and API/trade guardrail checks",
            "keep current exact support rows separate from reference/rebaseline rows",
            "keep live buy/add fail-closed until support, breaker, model, venue lifecycle, and bounded live-canary policy gates all pass",
        ],
        "forbidden_shortcuts": [
            "lower_minimum_support_rows",
            "count_reference_or_rebaseline_rows_as current exact support",
            "enable_live_buy_or_add_from_rebaseline_proof_alone",
        ],
        "recommended_actions": [
            {
                "id": "rerun_oos_under_selected_semantic_candidate",
                "priority": "P0" if report_verdict.get("selected_candidate_id") else "P1",
                "selected_candidate_id": report_verdict.get("selected_candidate_id"),
                "live_exposure_allowed": False,
                "success_condition": "OOS/Top-K/support-audit replay passes under an explicit new identity; otherwise record hard no-go.",
            },
            {
                "id": "keep_current_exact_support_gate_fail_closed",
                "priority": "P0",
                "current_exact_bucket_rows": report_verdict.get("current_exact_bucket_rows"),
                "minimum_support_rows": minimum_support_rows,
                "live_exposure_allowed": False,
                "success_condition": (
                    f"current exact support reaches at least {minimum_support_rows} rows "
                    "before any risk-on live action."
                ),
            },
        ],
    }


def markdown(report: dict[str, Any]) -> str:
    verdict = report.get("verdict") or {}
    drift = report.get("recent_drift_context") or {}
    lines = [
        "# q15 drift-aware rebaseline backtest",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- verdict: **{verdict.get('status')}**",
        f"- decision: {verdict.get('decision')}",
        f"- selected_candidate_id: `{verdict.get('selected_candidate_id')}`",
        f"- selected_current_window_rows: **{verdict.get('selected_current_window_rows')}**",
        f"- selected_all_history_rows: **{verdict.get('selected_all_history_rows')}**",
        f"- current exact support: **{verdict.get('current_exact_bucket_rows')}/{verdict.get('minimum_support_rows')}**",
        f"- live_exposure_allowed: **{verdict.get('live_exposure_allowed')}**",
        f"- order_submission_enabled: **{verdict.get('order_submission_enabled')}**",
        "",
        "## Recent drift context",
        "",
        f"- source_generated_at: `{drift.get('source_generated_at')}`",
        f"- window: `{drift.get('window')}`",
        f"- win_rate: `{drift.get('win_rate')}`",
        f"- dominant_regime: `{drift.get('dominant_regime')}` / share `{drift.get('dominant_regime_share')}`",
        f"- avg_pnl: `{drift.get('avg_pnl')}` / avg_quality `{drift.get('avg_quality')}` / drawdown_penalty `{drift.get('avg_drawdown_penalty')}`",
        "",
        "## Candidate matrix",
        "",
        "| candidate | status | all rows | current-window rows | relaxed fields | deployable |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    current_window_key = str((report.get("support_identity") or {}).get("calibration_window") or "")
    for candidate in report.get("candidate_matrix") or []:
        windows = candidate.get("window_evaluations") or {}
        all_rows = (windows.get("all") or {}).get("rows")
        current_rows = (windows.get(current_window_key) or {}).get("rows")
        lines.append(
            "| "
            f"{candidate.get('id')} | {candidate.get('status')} | {all_rows} | {current_rows} | "
            f"{','.join(candidate.get('relaxed_fields') or []) or '—'} | {candidate.get('deployable_support')} |"
        )
    lines.extend(["", "## Promotion requirements", ""])
    for item in report.get("promotion_requirements") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Forbidden shortcuts", ""])
    for item in report.get("forbidden_shortcuts") or []:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Operator conclusion",
        "",
        "This artifact can nominate a semantic/rebaseline candidate for replay, but it is not deployment clearance. Current live buy/add remains fail-closed.",
    ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    probe = _load_json(PROBE_PATH)
    q15_audit = _load_json(Q15_AUDIT_PATH)
    support_fill = _load_json(SUPPORT_FILL_PATH)
    recent_drift = _load_json(RECENT_DRIFT_PATH)
    identity = support_identity_from_artifacts(probe, q15_audit)
    rows = fetch_labeled_decision_rows(
        horizon_minutes=_as_int(identity.get("horizon_minutes"), DEFAULT_HORIZON_MINUTES),
    )
    report = build_report(
        rows=rows,
        support_identity=identity,
        support_fill=support_fill,
        q15_support_audit=q15_audit,
        recent_drift=recent_drift,
        db_meta=fetch_db_meta(),
        source_artifacts={
            "live_predict_probe_path": str(PROBE_PATH.relative_to(PROJECT_ROOT)),
            "live_predict_probe_generated_at": probe.get("generated_at"),
            "q15_support_audit_path": str(Q15_AUDIT_PATH.relative_to(PROJECT_ROOT)),
            "q15_support_audit_generated_at": q15_audit.get("generated_at"),
            "q15_support_fill_feasibility_path": str(SUPPORT_FILL_PATH.relative_to(PROJECT_ROOT)),
            "q15_support_fill_feasibility_generated_at": support_fill.get("generated_at"),
            "recent_drift_report_path": str(RECENT_DRIFT_PATH.relative_to(PROJECT_ROOT)),
            "recent_drift_report_generated_at": recent_drift.get("generated_at"),
        },
        minimum_support_rows=_as_int(
            (support_fill.get("verdict") or {}).get("minimum_support_rows")
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
        "q15_drift_rebaseline_backtest: "
        f"status={verdict['status']} selected={verdict.get('selected_candidate_id')} "
        f"current_window_rows={verdict.get('selected_current_window_rows')} "
        f"all_rows={verdict.get('selected_all_history_rows')} "
        f"live_exposure_allowed={verdict.get('live_exposure_allowed')} "
        f"json={OUT_JSON} md={OUT_MD}"
    )


if __name__ == "__main__":
    main()
