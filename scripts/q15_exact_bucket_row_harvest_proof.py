#!/usr/bin/env python3
"""Produce a current exact-bucket row-harvest proof without relaxing live gates.

The q15 support audit uses `exact_bucket_row_harvest_proof` as the forced branch
when the current support identity has not reached minimum rows.  This artifact
turns that branch into a standalone, rerunnable proof:

- current exact rows and gap are measured from the same support identity;
- support movement is separated from deployment readiness;
- proxy, neighbor, semantic, or reference rows never become live support here.
"""

from __future__ import annotations

import json
import sys
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
OUT_JSON = DATA_DIR / "q15_exact_bucket_row_harvest_proof.json"
OUT_MD = DOCS_ANALYSIS_DIR / "q15_exact_bucket_row_harvest_proof.md"


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


def _support_progress_from_artifacts(
    probe: dict[str, Any],
    q15_audit: dict[str, Any],
) -> dict[str, Any]:
    progress = probe.get("support_progress")
    if isinstance(progress, dict):
        return progress
    route = q15_audit.get("support_route") if isinstance(q15_audit.get("support_route"), dict) else {}
    progress = route.get("support_progress")
    if isinstance(progress, dict):
        return progress
    active = q15_audit.get("active_repair_plan") if isinstance(q15_audit.get("active_repair_plan"), dict) else {}
    if active:
        return {
            "status": active.get("support_status"),
            "current_rows": active.get("current_rows"),
            "minimum_support_rows": active.get("minimum_support_rows"),
            "gap_to_minimum": active.get("gap_to_minimum"),
            "stagnant_run_count": active.get("stagnant_run_count"),
            "semantic_signature_delta_vs_previous": active.get("semantic_signature_delta_vs_previous"),
            "semantic_signature_stagnant_run_count": active.get("semantic_signature_stagnant_run_count"),
            "semantic_signature_stalled_support_accumulation": active.get("semantic_signature_stalled_support_accumulation"),
        }
    return {}


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


def _window_rows(
    rows: list[dict[str, Any]],
    support_identity: dict[str, Any],
    minimum_support_rows: int,
) -> dict[str, Any]:
    calibration_window = _as_int(support_identity.get("calibration_window"), 0)
    scoped_rows = rows[: min(calibration_window, len(rows))] if calibration_window > 0 else rows
    exact_identity_rows = [row for row in scoped_rows if _matches_exact_identity(row, support_identity)]
    exact_bucket_rows = [row for row in exact_identity_rows if _matches_exact_bucket(row, support_identity)]
    non_bucket_identity_rows = [row for row in exact_identity_rows if not _matches_exact_bucket(row, support_identity)]
    exact_bucket_symbol_modes = {
        mode: sum(1 for row in exact_bucket_rows if str(row.get("symbol_join_mode") or "unknown") == mode)
        for mode in sorted({str(row.get("symbol_join_mode") or "unknown") for row in exact_bucket_rows})
    }
    canonical_recovered_rows = [
        row
        for row in exact_bucket_rows
        if row.get("symbol_join_mode") == "canonical_symbol"
        and row.get("symbol") != row.get("label_symbol")
    ]
    return {
        "calibration_window": calibration_window,
        "scope_rows": len(scoped_rows),
        "exact_identity_rows": len(exact_identity_rows),
        "exact_bucket_rows": len(exact_bucket_rows),
        "non_bucket_identity_rows": len(non_bucket_identity_rows),
        "minimum_support_rows": minimum_support_rows,
        "rows_needed_to_minimum": max(minimum_support_rows - len(exact_bucket_rows), 0),
        "support_ready_by_count": len(exact_bucket_rows) >= minimum_support_rows,
        "exact_bucket_metrics": _metric_summary(exact_bucket_rows),
        "latest_exact_bucket_timestamp": exact_bucket_rows[0].get("timestamp") if exact_bucket_rows else None,
        "oldest_exact_bucket_timestamp": exact_bucket_rows[-1].get("timestamp") if exact_bucket_rows else None,
        "sample_exact_bucket_timestamps": [row.get("timestamp") for row in exact_bucket_rows[:5]],
        "symbol_alignment": {
            "join_policy": "timestamp_plus_canonical_symbol_latest_feature_and_label_id",
            "canonical_symbol_transform": "remove_slash",
            "exact_bucket_symbol_join_modes": exact_bucket_symbol_modes,
            "exact_bucket_canonical_symbol_recovered_rows": len(canonical_recovered_rows),
            "sample_recovered_pairs": [
                {
                    "timestamp": row.get("timestamp"),
                    "feature_symbol": row.get("symbol"),
                    "label_symbol": row.get("label_symbol"),
                }
                for row in canonical_recovered_rows[:5]
            ],
            "evidence_role": "data_alignment_cleanup_not_deployment_clearance",
            "live_exposure_allowed": False,
        },
        "sample_non_bucket_identity_buckets": sorted(
            {
                str(row.get("structure_bucket"))
                for row in non_bucket_identity_rows[:20]
                if row.get("structure_bucket")
            }
        ),
    }


def _verdict(
    *,
    harvest_window: dict[str, Any],
    support_progress: dict[str, Any],
    support_fill: dict[str, Any],
    minimum_support_rows: int,
) -> dict[str, Any]:
    fill_verdict = support_fill.get("verdict") if isinstance(support_fill.get("verdict"), dict) else {}
    current_rows = _as_int(support_progress.get("current_rows"), harvest_window.get("exact_bucket_rows", 0))
    if current_rows != harvest_window.get("exact_bucket_rows"):
        current_rows = _as_int(harvest_window.get("exact_bucket_rows"), current_rows)
    previous_rows_raw = support_progress.get("previous_rows")
    previous_rows = _as_int(previous_rows_raw, 0) if previous_rows_raw is not None else None
    delta_raw = support_progress.get("delta_vs_previous")
    delta_vs_previous = _as_int(delta_raw, current_rows - (previous_rows or 0)) if delta_raw is not None else None
    gap = max(minimum_support_rows - current_rows, 0)
    support_gate_ready = current_rows >= minimum_support_rows

    if support_gate_ready:
        status = "exact_bucket_row_harvest_support_ready_remaining_gates"
        primary_failed_gate = "remaining_live_gates"
        decision = (
            "Current exact bucket rows meet minimum support; this artifact proves support movement only, "
            "so live buy/add still waits for model, venue, API guardrail, and bounded-canary gates."
        )
    elif current_rows <= 0:
        status = "exact_bucket_row_harvest_no_current_rows"
        primary_failed_gate = "current_live_support_gate"
        decision = "No current exact bucket rows are available; keep exact-row harvest or hard no-go as the forced branch."
    elif delta_vs_previous is not None and delta_vs_previous > 0:
        status = "exact_bucket_row_harvest_positive_delta_under_minimum"
        primary_failed_gate = "current_live_support_gate"
        decision = (
            "Current exact support has positive movement but remains under the minimum; keep live fail-closed "
            "and continue exact-row harvest."
        )
    elif delta_vs_previous == 0:
        status = "exact_bucket_row_harvest_stalled_under_minimum"
        primary_failed_gate = "support_accumulation_stalled"
        decision = (
            "Current exact support is still under minimum and has no positive delta; anti-equilibrium forced "
            "execution must not fall back to observation-only."
        )
    else:
        status = "exact_bucket_row_harvest_under_minimum_progress_unproven"
        primary_failed_gate = "current_live_support_gate"
        decision = "Current exact support remains under minimum and progress history is incomplete; keep live fail-closed."

    return {
        "status": status,
        "decision": decision,
        "current_exact_bucket_rows": current_rows,
        "previous_rows": previous_rows,
        "delta_vs_previous": delta_vs_previous,
        "semantic_signature_delta_vs_previous": support_progress.get("semantic_signature_delta_vs_previous"),
        "stagnant_run_count": support_progress.get("stagnant_run_count"),
        "semantic_signature_stagnant_run_count": support_progress.get("semantic_signature_stagnant_run_count"),
        "minimum_support_rows": minimum_support_rows,
        "gap_to_minimum": gap,
        "rows_needed_to_minimum": gap,
        "support_gate_ready": support_gate_ready,
        "deployable": False,
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "primary_failed_gate": primary_failed_gate,
        "time_to_evidence_bucket": fill_verdict.get("time_to_evidence_bucket"),
        "missing_capability_class": fill_verdict.get("missing_capability_class"),
        "alternative_solution_required": fill_verdict.get("alternative_solution_required", not support_gate_ready),
        "row_harvest_evidence_role": "current_exact_support_movement_not_deployment_clearance",
    }


def build_report(
    *,
    rows: list[dict[str, Any]],
    support_identity: dict[str, Any],
    probe: dict[str, Any] | None = None,
    q15_audit: dict[str, Any] | None = None,
    support_fill: dict[str, Any] | None = None,
    db_meta: dict[str, Any] | None = None,
    generated_at: str | None = None,
    minimum_support_rows: int = DEFAULT_MINIMUM_SUPPORT_ROWS,
) -> dict[str, Any]:
    probe = probe or {}
    q15_audit = q15_audit or {}
    support_fill = support_fill or {}
    support_progress = _support_progress_from_artifacts(probe, q15_audit)
    harvest_window = _window_rows(rows, support_identity, minimum_support_rows)
    verdict = _verdict(
        harvest_window=harvest_window,
        support_progress=support_progress,
        support_fill=support_fill,
        minimum_support_rows=minimum_support_rows,
    )
    return {
        "generated_at": generated_at or _utc_now_iso(),
        "artifact": "q15_exact_bucket_row_harvest_proof",
        "purpose": "Prove exact current-bucket support movement without converting it into deployment clearance.",
        "source_artifacts": {
            "live_predict_probe_generated_at": probe.get("generated_at"),
            "q15_support_audit_generated_at": q15_audit.get("generated_at"),
            "q15_support_fill_feasibility_generated_at": support_fill.get("generated_at"),
        },
        "support_identity": support_identity,
        "db_meta": db_meta or {},
        "harvest_window": harvest_window,
        "support_progress": {
            "status": support_progress.get("status"),
            "reason": support_progress.get("reason"),
            "regression_basis": support_progress.get("regression_basis"),
            "current_rows": support_progress.get("current_rows"),
            "previous_rows": support_progress.get("previous_rows"),
            "delta_vs_previous": support_progress.get("delta_vs_previous"),
            "stagnant_run_count": support_progress.get("stagnant_run_count"),
            "stalled_support_accumulation": support_progress.get("stalled_support_accumulation"),
            "semantic_signature_delta_vs_previous": support_progress.get("semantic_signature_delta_vs_previous"),
            "semantic_signature_stagnant_run_count": support_progress.get("semantic_signature_stagnant_run_count"),
            "semantic_signature_stalled_support_accumulation": support_progress.get(
                "semantic_signature_stalled_support_accumulation"
            ),
            "previous_route_changed": support_progress.get("previous_route_changed"),
            "previous_support_route_verdict": support_progress.get("previous_support_route_verdict"),
            "previous_support_governance_route": support_progress.get("previous_support_governance_route"),
        },
        "verdict": verdict,
        "promotion_requirements": [
            "current_exact_bucket_rows >= minimum_support_rows under the same support identity",
            "support audit confirms the current identity is deployable support, not proxy/reference support",
            "high-conviction Top-K or model deployment row remains deployable under fresh live overlay",
            "venue lifecycle proof passes with credential, ack, cancel, fill, and reconciliation evidence",
            "bounded live-canary policy is configured before any live buy/add pilot",
        ],
        "forbidden_shortcuts": [
            "lower_minimum_support_rows",
            "count_non_bucket_identity_rows_as_exact_support",
            "count_neighbor_or_reference_rows_as_current_exact_support",
            "enable_live_buy_or_add_from_row_harvest_proof_alone",
        ],
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
    }


def markdown(report: dict[str, Any]) -> str:
    verdict = report.get("verdict") if isinstance(report.get("verdict"), dict) else {}
    harvest = report.get("harvest_window") if isinstance(report.get("harvest_window"), dict) else {}
    progress = report.get("support_progress") if isinstance(report.get("support_progress"), dict) else {}
    identity = report.get("support_identity") if isinstance(report.get("support_identity"), dict) else {}
    symbol_alignment = harvest.get("symbol_alignment") if isinstance(harvest.get("symbol_alignment"), dict) else {}
    lines = [
        "# q15 Exact Bucket Row Harvest Proof",
        "",
        f"- generated_at: `{report.get('generated_at', '—')}`",
        f"- artifact: **{report.get('artifact', '—')}**",
        f"- verdict: **{verdict.get('status', '—')}**",
        f"- decision: {verdict.get('decision', '—')}",
        f"- current_live_structure_bucket: `{identity.get('current_live_structure_bucket', '—')}`",
        f"- current exact rows: `{verdict.get('current_exact_bucket_rows', '—')}/{verdict.get('minimum_support_rows', '—')}`",
        f"- previous rows: `{verdict.get('previous_rows', '—')}`",
        f"- delta_vs_previous: `{verdict.get('delta_vs_previous', '—')}`",
        f"- rows_needed_to_minimum: `{verdict.get('rows_needed_to_minimum', '—')}`",
        f"- primary_failed_gate: `{verdict.get('primary_failed_gate', '—')}`",
        f"- live_exposure_allowed: `{str(verdict.get('live_exposure_allowed')).lower()}`",
        "",
        "## Current Calibration Window",
        f"- calibration_window: `{harvest.get('calibration_window', '—')}`",
        f"- exact_identity_rows: `{harvest.get('exact_identity_rows', '—')}`",
        f"- exact_bucket_rows: `{harvest.get('exact_bucket_rows', '—')}`",
        f"- non_bucket_identity_rows: `{harvest.get('non_bucket_identity_rows', '—')}`",
        f"- latest_exact_bucket_timestamp: `{harvest.get('latest_exact_bucket_timestamp', '—')}`",
        f"- oldest_exact_bucket_timestamp: `{harvest.get('oldest_exact_bucket_timestamp', '—')}`",
        "",
        "## Symbol Alignment",
        f"- join_policy: `{symbol_alignment.get('join_policy', '—')}`",
        f"- exact_bucket_symbol_join_modes: `{symbol_alignment.get('exact_bucket_symbol_join_modes', {})}`",
        f"- exact_bucket_canonical_symbol_recovered_rows: `{symbol_alignment.get('exact_bucket_canonical_symbol_recovered_rows', '—')}`",
        "- operator meaning: canonical symbol recovery is data cleanup evidence, not deployment clearance.",
        "",
        "## Support Progress",
        f"- status: `{progress.get('status', '—')}`",
        f"- regression_basis: `{progress.get('regression_basis', '—')}`",
        f"- stagnant_run_count: `{progress.get('stagnant_run_count', '—')}`",
        f"- semantic_signature_delta_vs_previous: `{progress.get('semantic_signature_delta_vs_previous', '—')}`",
        "",
        "## Safety Boundary",
        "- This artifact is not deployment clearance.",
        "- Positive row movement only proves support accumulation; live buy/add remains blocked until support, model, venue, API guardrail, and bounded-canary gates all pass.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    probe = _load_json(PROBE_PATH)
    q15_audit = _load_json(Q15_AUDIT_PATH)
    support_fill = _load_json(SUPPORT_FILL_PATH)
    support_identity = support_identity_from_artifacts(probe, q15_audit)
    minimum = _as_int(
        probe.get("minimum_support_rows")
        or (probe.get("deployment_blocker_details") or {}).get("minimum_support_rows")
        or DEFAULT_MINIMUM_SUPPORT_ROWS,
        DEFAULT_MINIMUM_SUPPORT_ROWS,
    )
    rows = fetch_labeled_decision_rows(
        horizon_minutes=_as_int(support_identity.get("horizon_minutes"), DEFAULT_HORIZON_MINUTES)
    )
    report = build_report(
        rows=rows,
        support_identity=support_identity,
        probe=probe,
        q15_audit=q15_audit,
        support_fill=support_fill,
        db_meta=fetch_db_meta(),
        generated_at=_utc_now_iso(),
        minimum_support_rows=minimum,
    )
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(markdown(report), encoding="utf-8")
    verdict = report["verdict"]
    print(
        "q15_exact_bucket_row_harvest_proof: "
        f"status={verdict.get('status')} "
        f"rows={verdict.get('current_exact_bucket_rows')}/{verdict.get('minimum_support_rows')} "
        f"delta={verdict.get('delta_vs_previous')} "
        f"gap={verdict.get('gap_to_minimum')} "
        f"live_exposure_allowed={verdict.get('live_exposure_allowed')} "
        f"json={OUT_JSON} md={OUT_MD}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
