#!/usr/bin/env python3
"""Validate the Poly-Trader PM heartbeat harness contract.

The checker is intentionally stdlib-only so scheduled PM heartbeats can run it
without relying on the full ML/web dependency stack.  It validates PM maps,
Q&A gates, cross-links to engineering truth, and repo entry references.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "docs" / "ai-collaboration" / "pm" / "pm-heartbeat-contract.json"
QA_PATH = PROJECT_ROOT / "docs" / "ai-collaboration" / "pm" / "pm-heartbeat-qa.md"
TOPK_STALE_AFTER_MINUTES = 60.0
TOPK_LIVE_SUPPORT_STALE_AFTER_MINUTES = 30.0
PM_CURRENT_ARTIFACT_STALE_AFTER_MINUTES = 24.0 * 60.0
PM_CURRENT_ARTIFACT_FRESHNESS_PATHS = (
    "data/live_predict_probe.json",
    "data/live_decision_quality_drilldown.json",
    "data/circuit_breaker_audit.json",
    "data/recent_drift_report.json",
    "data/execution_metadata_smoke.json",
    "data/venue_dry_run_proof.json",
    "data/q15_support_fill_feasibility.json",
    "data/q15_exact_bucket_row_harvest_proof.json",
    "data/q15_drift_rebaseline_backtest.json",
    "data/q15_map_signal_redesign_proof.json",
    "data/customer_safe_alternative_proof.json",
    "data/live_canary_structural_pivot.json",
    "data/no_trade_lane_replay.json",
    "data/paper_shadow_outcome_reconciliation.json",
    "data/microstructure_contract.json",
)

REQUIRED_GATE_IDS = [
    "PMHQ0_context_map",
    "PMHQ1_stakeholder_expectation",
    "PMHQ2_artifact_truth",
    "PMHQ3_conflict_diagnosis",
    "PMHQ4_engineering_claim_audit",
    "PMHQ5_delivery_ladder",
    "PMHQ6_action_contract",
    "PMHQ7_deadlock_escape",
    "PMHQ8_customer_report",
    "PMHQ9_alternative_solution_review",
    "PMHQ10_anti_equilibrium_review",
    "PMHQ11_forced_execution_pivot",
]

REQUIRED_DOC_REFERENCES = {
    "AGENTS.md": ["docs/ai-collaboration/PM_HEARTBEAT.md", "docs/ai-collaboration/pm/README.md"],
    "docs/ai-collaboration/PM_HEARTBEAT.md": [
        "docs/ai-collaboration/pm/README.md",
        "docs/ai-collaboration/pm/pm-heartbeat-qa.md",
        "docs/ai-collaboration/pm/pm-status.md",
        "scripts/pm_heartbeat_check.py",
        "customer-side advocate",
        "framework-capture",
        "alternative-solution",
        "time-to-evidence",
        "anti-equilibrium",
        "customer-value delta",
        "cost-of-delay",
        "red-team PM",
        "forced-execution",
        "bounded live-canary",
        "72h",
    ],
    "docs/ai-collaboration/pm/README.md": ["customer-side advocate", "framework-capture", "alternative-solution", "time-to-evidence", "anti-equilibrium", "customer-value delta", "cost-of-delay", "red-team PM", "forced-execution", "bounded live-canary", "72h"],
    "docs/ai-collaboration/pm/pm-heartbeat-qa.md": ["PMHQ1_stakeholder_expectation", "PMHQ9_alternative_solution_review", "PMHQ10_anti_equilibrium_review", "PMHQ11_forced_execution_pivot", "framework-capture", "alternative-solution", "time-to-evidence", "anti-equilibrium", "customer-value delta", "cost-of-delay", "forced-execution", "bounded live-canary", "72h"],
    "README.md": ["docs/ai-collaboration/pm/README.md", "scripts/pm_heartbeat_check.py"],
    "ARCHITECTURE.md": ["docs/ai-collaboration/pm", "docs/ai-collaboration/PM_HEARTBEAT.md"],
}


@dataclass(frozen=True)
class CheckResult:
    id: str
    question: str
    ok: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "ok": self.ok,
            "detail": self.detail,
        }


def _repo_path(path_value: str) -> Path:
    return PROJECT_ROOT / path_value


def _artifact_freshness_fields(
    generated_at: Any,
    *,
    stale_after_minutes: float,
    now: datetime | None = None,
) -> dict[str, Any]:
    checked_at = now or datetime.now(timezone.utc)
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    checked_at = checked_at.astimezone(timezone.utc)
    payload: dict[str, Any] = {
        "artifact_freshness_status": "unavailable",
        "artifact_freshness_reason": "missing_generated_at",
        "artifact_age_minutes": None,
        "artifact_stale_after_minutes": stale_after_minutes,
        "artifact_deployment_blocking": True,
    }
    if not generated_at:
        return payload
    try:
        generated_dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    except ValueError:
        payload["artifact_freshness_reason"] = "invalid_generated_at"
        return payload
    if generated_dt.tzinfo is None:
        generated_dt = generated_dt.replace(tzinfo=timezone.utc)
    age_minutes = max((checked_at - generated_dt.astimezone(timezone.utc)).total_seconds(), 0.0) / 60.0
    status = "fresh" if age_minutes <= stale_after_minutes else "stale"
    payload.update(
        {
            "artifact_freshness_status": status,
            "artifact_freshness_reason": "artifact_within_policy" if status == "fresh" else "artifact_older_than_policy",
            "artifact_age_minutes": age_minutes,
            "artifact_deployment_blocking": status != "fresh",
        }
    )
    return payload


def _topk_freshness_fields(generated_at: Any, *, now: datetime | None = None) -> dict[str, Any]:
    return _artifact_freshness_fields(
        generated_at,
        stale_after_minutes=TOPK_STALE_AFTER_MINUTES,
        now=now,
    )


def _topk_live_support_freshness_fields(
    generated_at: Any,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    freshness = _artifact_freshness_fields(
        generated_at,
        stale_after_minutes=TOPK_LIVE_SUPPORT_STALE_AFTER_MINUTES,
        now=now,
    )
    return {
        "support_context_freshness_status": freshness.get("artifact_freshness_status"),
        "support_context_freshness_reason": freshness.get("artifact_freshness_reason"),
        "support_context_age_minutes": freshness.get("artifact_age_minutes"),
        "support_context_stale_after_minutes": freshness.get("artifact_stale_after_minutes"),
        "support_context_deployment_blocking": freshness.get("artifact_deployment_blocking"),
    }


def _load_contract() -> tuple[dict[str, Any] | None, list[CheckResult]]:
    if not CONTRACT_PATH.exists():
        return None, [
            CheckResult(
                "pm_contract_exists",
                "PM contract file exists?",
                False,
                str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
            )
        ]

    try:
        return json.loads(CONTRACT_PATH.read_text(encoding="utf-8")), [
            CheckResult(
                "pm_contract_exists",
                "PM contract file exists?",
                True,
                str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
            )
        ]
    except json.JSONDecodeError as exc:
        return None, [
            CheckResult(
                "pm_contract_json_valid",
                "PM contract JSON is parseable?",
                False,
                f"{exc.msg} at line {exc.lineno} column {exc.colno}",
            )
        ]


def _check_required_docs(contract: dict[str, Any]) -> list[CheckResult]:
    docs = contract.get("required_docs", [])
    if not isinstance(docs, list) or not docs:
        return [
            CheckResult(
                "pm_required_docs_declared",
                "PM contract declares required docs?",
                False,
                "required_docs missing or empty",
            )
        ]

    missing: list[str] = []
    invalid: list[str] = []
    for item in docs:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            invalid.append("<invalid required_docs item>")
            continue
        rel = item["path"]
        if not _repo_path(rel).exists():
            missing.append(rel)

    detail = "ok" if not missing and not invalid else ", ".join(invalid + missing)
    return [
        CheckResult(
            "pm_required_docs_exist",
            "All PM required docs exist?",
            not missing and not invalid,
            detail,
        )
    ]


def _check_entrypoints(contract: dict[str, Any]) -> list[CheckResult]:
    entrypoints = contract.get("entrypoints", {})
    if not isinstance(entrypoints, dict) or not entrypoints:
        return [
            CheckResult(
                "pm_entrypoints_declared",
                "PM contract declares entrypoints?",
                False,
                "entrypoints missing or empty",
            )
        ]

    missing = [
        rel
        for rel in entrypoints.values()
        if isinstance(rel, str) and not _repo_path(rel).exists()
    ]
    return [
        CheckResult(
            "pm_entrypoints_exist",
            "All PM entrypoints exist?",
            not missing,
            "ok" if not missing else ", ".join(missing),
        )
    ]


def _check_question_gates(contract: dict[str, Any]) -> list[CheckResult]:
    gates = contract.get("question_gates", [])
    gate_ids = {
        gate.get("id")
        for gate in gates
        if isinstance(gate, dict) and isinstance(gate.get("id"), str)
    }
    missing_contract = [gate_id for gate_id in REQUIRED_GATE_IDS if gate_id not in gate_ids]

    qa_text = QA_PATH.read_text(encoding="utf-8") if QA_PATH.exists() else ""
    missing_qa = [gate_id for gate_id in REQUIRED_GATE_IDS if gate_id not in qa_text]

    return [
        CheckResult(
            "pm_qa_gates_complete",
            "PM contract and QA playbook include PMHQ0-PMHQ11?",
            not missing_contract and not missing_qa,
            "ok"
            if not missing_contract and not missing_qa
            else f"contract missing={missing_contract}; qa missing={missing_qa}",
        )
    ]


def _check_doc_references() -> list[CheckResult]:
    results: list[CheckResult] = []
    for rel_path, required_snippets in REQUIRED_DOC_REFERENCES.items():
        path = PROJECT_ROOT / rel_path
        if not path.exists():
            results.append(
                CheckResult(
                    f"{rel_path}:exists",
                    f"{rel_path} exists?",
                    False,
                    rel_path,
                )
            )
            continue
        text = path.read_text(encoding="utf-8")
        missing = [snippet for snippet in required_snippets if snippet not in text]
        results.append(
            CheckResult(
                f"{rel_path}:pm_references",
                f"{rel_path} links to PM heartbeat dependencies?",
                not missing,
                "ok" if not missing else ", ".join(missing),
            )
        )
    return results


def _load_json_artifact(rel_path: str) -> tuple[dict[str, Any] | None, str | None]:
    path = PROJECT_ROOT / rel_path
    if not path.exists():
        return None, f"{rel_path} missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"{rel_path} invalid JSON at line {exc.lineno} column {exc.colno}"
    if not isinstance(payload, dict):
        return None, f"{rel_path} root is not an object"
    return payload, None


def _bool_snippet(name: str, value: Any) -> str | None:
    if isinstance(value, bool):
        return f"{name}={'true' if value else 'false'}"
    return None


def _num_text(value: Any, digits: int = 4) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.{digits}f}"


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _support_ready(rows: Any, minimum: Any, gap: Any, support_route: Any) -> bool:
    rows_int = _as_int(rows)
    minimum_int = _as_int(minimum)
    gap_int = _as_int(gap)
    return bool(
        support_route == "exact_bucket_supported"
        or (
            rows_int is not None
            and minimum_int is not None
            and rows_int >= minimum_int
            and (gap_int is None or gap_int <= 0)
        )
    )


def _pm_current_artifact_freshness_snippets(
    *,
    now: datetime | None = None,
) -> tuple[list[str], list[str]]:
    required: list[str] = []
    artifact_errors: list[str] = []
    for rel_path in PM_CURRENT_ARTIFACT_FRESHNESS_PATHS:
        payload, error = _load_json_artifact(rel_path)
        if error:
            artifact_errors.append(error)
            continue
        assert payload is not None
        freshness = _artifact_freshness_fields(
            payload.get("generated_at"),
            stale_after_minutes=PM_CURRENT_ARTIFACT_STALE_AFTER_MINUTES,
            now=now,
        )
        status = freshness.get("artifact_freshness_status")
        required.append(f"{rel_path} freshness_status={status}")
        if status != "fresh":
            age = _num_text(freshness.get("artifact_age_minutes"), digits=2)
            stale_after = _num_text(freshness.get("artifact_stale_after_minutes"), digits=1)
            reason = freshness.get("artifact_freshness_reason")
            artifact_errors.append(
                f"{rel_path} stale current artifact "
                f"(freshness_status={status}, age_min={age}, stale_after_min={stale_after}, reason={reason})"
            )
    return required, artifact_errors


def _pm_status_required_snippets() -> tuple[list[str], list[str]]:
    """Build PM status checks from current runtime artifacts, not stale literals.

    The PM heartbeat can legitimately change from q00/circuit-breaker to
    q15/support-under-minimum (or the reverse).  Hard-coding one historical
    blocker lets PM status pass while contradicting the live probe.  These
    snippets make the checker a current-state guardrail.
    """

    required = [
        "YELLOW_shadow_or_paper_usable",
        "Strategy Lab",
        "Execution Console",
        "客戶成功",
        "framework-capture",
        "alternative-solution",
        "time-to-evidence",
        "ORANGE_alternative_solution_required",
        "Next-hour gate",
        "anti-equilibrium",
        "customer-value delta",
        "anti-repeat",
        "cost-of-delay",
        "hypothesis inversion",
        "option portfolio",
        "red-team PM",
        "forced-execution",
        "bounded live-canary",
        "72h",
        "Venue lifecycle proof",
        "Model shadow to decision",
        "Strategy micro-canary",
        "request-time runtime truth",
        "?refresh=true",
        "auto-queue stale Top-K matrix refresh",
        "refreshes stale live support probe",
        "serialize request-time ML cold-load",
        "hc_refreshing",
        "hc_refresh_reason",
        "hc_support_context_refresh_status",
        "hc_support_context_status",
        "hc_live_truth_freshness_status",
        "Microstructure / dynamic edge contract",
        "microstructure_contract",
        "decision_status=observation_only",
        "forecast_edge_bps=None",
    ]
    artifact_errors: list[str] = []
    freshness_required, freshness_errors = _pm_current_artifact_freshness_snippets()
    required.extend(freshness_required)
    artifact_errors.extend(freshness_errors)

    live_probe_generated_at: Any = None
    probe, error = _load_json_artifact("data/live_predict_probe.json")
    if error:
        artifact_errors.append(error)
    elif probe is not None:
        live_probe_generated_at = probe.get("generated_at")
        details = probe.get("deployment_blocker_details") or {}
        required.extend(
            snippet
            for snippet in [
                str(probe.get("deployment_blocker")),
                str(probe.get("allowed_layers_reason")),
                str(probe.get("execution_guardrail_reason")),
                str(probe.get("current_live_structure_bucket")),
                str(probe.get("support_route_verdict") or details.get("support_route_verdict")),
                str(probe.get("support_governance_route") or details.get("support_governance_route")),
                f"allowed_layers_raw={probe.get('allowed_layers_raw')}",
                f"allowed_layers={probe.get('allowed_layers')}",
                (
                    f"decision_quality_score={_num_text(probe.get('decision_quality_score'))}"
                    if _num_text(probe.get("decision_quality_score")) is not None
                    else None
                ),
            ]
            if snippet and snippet != "None"
        )
        rows = _first_present(probe.get("current_live_structure_bucket_rows"), details.get("current_live_structure_bucket_rows"))
        minimum = _first_present(probe.get("minimum_support_rows"), details.get("minimum_support_rows"))
        gap = _first_present(probe.get("current_live_structure_bucket_gap_to_minimum"), details.get("current_live_structure_bucket_gap_to_minimum"))
        if rows is not None and minimum is not None:
            required.append(f"{rows}/{minimum}")
        if gap is not None:
            required.append(f"gap={gap}")
        progress = probe.get("support_progress") if isinstance(probe.get("support_progress"), dict) else {}
        details_progress = details.get("support_progress") if isinstance(details.get("support_progress"), dict) else {}
        if not progress:
            progress = details_progress
        semantic_progress = progress.get("semantic_signature_progress") if isinstance(progress.get("semantic_signature_progress"), dict) else {}
        for snippet in [
            (
                f"delta_vs_previous={progress.get('delta_vs_previous')}"
                if progress.get("delta_vs_previous") is not None
                else None
            ),
            (
                f"stagnant_run_count={progress.get('stagnant_run_count')}"
                if progress.get("stagnant_run_count") is not None
                else None
            ),
            (
                f"semantic_signature_delta_vs_previous={_first_present(progress.get('semantic_signature_delta_vs_previous'), semantic_progress.get('delta_vs_previous'))}"
                if _first_present(progress.get("semantic_signature_delta_vs_previous"), semantic_progress.get("delta_vs_previous")) is not None
                else None
            ),
            (
                f"semantic_signature_stagnant_run_count={_first_present(progress.get('semantic_signature_stagnant_run_count'), semantic_progress.get('stagnant_run_count'))}"
                if _first_present(progress.get("semantic_signature_stagnant_run_count"), semantic_progress.get("stagnant_run_count")) is not None
                else None
            ),
            _bool_snippet(
                "semantic_signature_stalled_support_accumulation",
                _first_present(
                    progress.get("semantic_signature_stalled_support_accumulation"),
                    semantic_progress.get("stalled_support_accumulation"),
                ),
            ),
        ]:
            if snippet:
                required.append(snippet)

    breaker, error = _load_json_artifact("data/circuit_breaker_audit.json")
    if error:
        artifact_errors.append(error)
    elif breaker is not None:
        required.append(str(breaker.get("verdict")))
        release_condition = breaker.get("release_condition") or {}
        release_ready = _bool_snippet("release_ready", release_condition.get("release_ready"))
        if release_ready:
            required.append(release_ready)
        wins = release_condition.get("current_recent_window_wins")
        window = release_condition.get("recent_window")
        additional = release_condition.get("additional_recent_window_wins_needed")
        if wins is not None and window is not None:
            required.append(f"{wins}/{window}")
        if additional is not None:
            required.append(f"additional_recent_window_wins_needed={additional}")

    topk, error = _load_json_artifact("data/high_conviction_topk_oos_matrix.json")
    if error:
        artifact_errors.append(error)
    elif topk is not None:
        freshness = _topk_freshness_fields(topk.get("generated_at"))
        live_support_freshness = _topk_live_support_freshness_fields(
            live_probe_generated_at
        )
        rows = topk.get("rows") if isinstance(topk.get("rows"), list) else []
        runtime_blocked = [
            row
            for row in rows
            if isinstance(row, dict)
            and row.get("deployment_candidate_tier") == "runtime_blocked_oos_pass"
        ]
        required.extend(
            snippet
            for snippet in [
                "Top-K",
                f"artifact_freshness_status={freshness.get('artifact_freshness_status')}",
                f"support_context_freshness_status={live_support_freshness.get('support_context_freshness_status')}",
                f"support_context_deployment_blocking={str(live_support_freshness.get('support_context_deployment_blocking')).lower()}",
                f"samples={topk.get('samples')}",
                f"row_count={len(rows)}",
                f"runtime_blocked_candidate_rows={len(runtime_blocked)}",
            ]
            if snippet and "None" not in snippet
        )

    execution, error = _load_json_artifact("data/execution_metadata_smoke.json")
    if error:
        artifact_errors.append(error)
    elif execution is not None:
        runtime_ready = _bool_snippet("runtime_ready", execution.get("runtime_ready"))
        if runtime_ready:
            required.append(runtime_ready)
        for key in ("runtime_ready_count", "venues_checked", "ok_count"):
            if execution.get(key) is not None:
                required.append(f"{key}={execution[key]}")

    venue_dry_run, error = _load_json_artifact("data/venue_dry_run_proof.json")
    if error:
        artifact_errors.append(error)
    elif venue_dry_run is not None:
        required.extend(
            snippet
            for snippet in [
                "data/venue_dry_run_proof.json",
                f"venue_dry_run_status={venue_dry_run.get('status')}",
                _bool_snippet("order_submission_enabled", venue_dry_run.get("order_submission_enabled")),
                _bool_snippet("risk_on_order_enabled", venue_dry_run.get("risk_on_order_enabled")),
                _bool_snippet("dry_run_only", venue_dry_run.get("dry_run_only")),
            ]
            if snippet and "None" not in snippet
        )

    no_trade, error = _load_json_artifact("data/no_trade_lane_replay.json")
    if error:
        artifact_errors.append(error)
    elif no_trade is not None:
        decision = no_trade.get("replay_decision") if isinstance(no_trade.get("replay_decision"), dict) else {}
        checks = no_trade.get("machine_checks") if isinstance(no_trade.get("machine_checks"), dict) else {}
        required.extend(
            snippet
            for snippet in [
                "No-trade lane replay",
                "data/no_trade_lane_replay.json",
                f"verdict={decision.get('verdict')}",
                _bool_snippet("validated", decision.get("validated")),
                _bool_snippet("deployable", decision.get("deployable")),
                _bool_snippet("buy_add_support_closure_allowed", decision.get("buy_add_support_closure_allowed")),
                _bool_snippet("checks_all_passed", checks.get("all_passed")),
            ]
            if snippet and "None" not in snippet
        )

    worker_outcome, error = _load_json_artifact("data/paper_shadow_outcome_reconciliation.json")
    if error:
        artifact_errors.append(error)
    elif worker_outcome is not None:
        summary = worker_outcome.get("summary") if isinstance(worker_outcome.get("summary"), dict) else {}
        proof = worker_outcome.get("rehearsal_proof") if isinstance(worker_outcome.get("rehearsal_proof"), dict) else {}
        required.extend(
            snippet
            for snippet in [
                "Paper/shadow worker parity",
                "data/paper_shadow_outcome_reconciliation.json",
                f"status={worker_outcome.get('status')}",
                f"worker_poll_events={summary.get('worker_poll_events')}",
                f"pending_outcomes={summary.get('pending_outcomes')}",
                f"resolved_outcomes={summary.get('resolved_outcomes')}",
                f"awaiting_label_replay={summary.get('awaiting_label_replay')}",
                _bool_snippet("live_order_submitted", summary.get("live_order_submitted")),
                f"status={proof.get('status')}",
                _bool_snippet("can_poll_workers", proof.get("can_poll_workers")),
                _bool_snippet("poll_blocked_by_pending_outcome", proof.get("poll_blocked_by_pending_outcome")),
                _bool_snippet("order_submission_enabled", proof.get("order_submission_enabled")),
                _bool_snippet("risk_on_order_enabled", proof.get("risk_on_order_enabled")),
                _bool_snippet("live_order_submitted", proof.get("live_order_submitted")),
                (
                    "current_pending_hours_remaining_hours="
                    if proof.get("next_reconcile_at")
                    else None
                ),
                (
                    f"artifact_pending_hours_remaining_hours={proof.get('pending_hours_remaining_min')}"
                    if proof.get("pending_hours_remaining_min") is not None
                    else None
                ),
            ]
            if snippet and "None" not in snippet
        )

    return required, artifact_errors


def _check_pm_status_current_state() -> list[CheckResult]:
    status_path = PROJECT_ROOT / "docs" / "ai-collaboration" / "pm" / "pm-status.md"
    if not status_path.exists():
        return [
            CheckResult(
                "pm_status_exists",
                "PM status doc exists?",
                False,
                "docs/ai-collaboration/pm/pm-status.md",
            )
        ]
    text = status_path.read_text(encoding="utf-8")
    required, artifact_errors = _pm_status_required_snippets()
    missing = [snippet for snippet in required if snippet not in text]
    forbidden: list[str] = []
    breaker, breaker_error = _load_json_artifact("data/circuit_breaker_audit.json")
    if breaker_error:
        artifact_errors.append(breaker_error)
    elif breaker is not None:
        release_condition = breaker.get("release_condition") or {}
        if breaker.get("verdict") == "canonical_breaker_active" or release_condition.get("release_ready") is False:
            forbidden.extend(["breaker_clear", "breaker math can be clear"])
    probe, probe_error = _load_json_artifact("data/live_predict_probe.json")
    if probe_error:
        artifact_errors.append(probe_error)
    elif probe is not None:
        details = probe.get("deployment_blocker_details") or {}
        rows = _first_present(probe.get("current_live_structure_bucket_rows"), details.get("current_live_structure_bucket_rows"))
        minimum = _first_present(probe.get("minimum_support_rows"), details.get("minimum_support_rows"))
        gap = _first_present(probe.get("current_live_structure_bucket_gap_to_minimum"), details.get("current_live_structure_bucket_gap_to_minimum"))
        support_route = _first_present(probe.get("support_route_verdict"), details.get("support_route_verdict"))
        governance_route = _first_present(probe.get("support_governance_route"), details.get("support_governance_route"))
        if _support_ready(rows, minimum, gap, support_route):
            forbidden.append("尚未建立同一 support identity 的精準樣本")
            if governance_route == "exact_live_bucket_supported":
                forbidden.append("support_governance_route=exact_live_bucket_supported` 只能當治理 / proxy reference")
    forbidden_present = [snippet for snippet in forbidden if snippet in text]
    detail_parts = []
    if missing:
        detail_parts.append("missing=" + ", ".join(missing))
    if forbidden_present:
        detail_parts.append("forbidden=" + ", ".join(forbidden_present))
    if artifact_errors:
        detail_parts.append("artifact_errors=" + ", ".join(artifact_errors))
    ok = not missing and not forbidden_present and not artifact_errors
    return [
        CheckResult(
            "pm_status_current_state_fields",
            "PM status matches current live artifacts, decision, usable lanes, and next gate?",
            ok,
            "ok" if ok else "; ".join(detail_parts),
        )
    ]


def _check_live_canary_pivot_current_truth() -> list[CheckResult]:
    """Ensure the forced-execution pivot is generated from the current artifacts."""

    artifact_errors: list[str] = []
    pivot, error = _load_json_artifact("data/live_canary_structural_pivot.json")
    if error:
        artifact_errors.append(error)
    probe, error = _load_json_artifact("data/live_predict_probe.json")
    if error:
        artifact_errors.append(error)
    breaker, error = _load_json_artifact("data/circuit_breaker_audit.json")
    if error:
        artifact_errors.append(error)
    topk, error = _load_json_artifact("data/high_conviction_topk_oos_matrix.json")
    if error:
        artifact_errors.append(error)
    execution, error = _load_json_artifact("data/execution_metadata_smoke.json")
    if error:
        artifact_errors.append(error)

    if artifact_errors:
        return [
            CheckResult(
                "pm_live_canary_pivot_current_truth",
                "Live-canary structural pivot matches current artifacts?",
                False,
                "artifact_errors=" + ", ".join(artifact_errors),
            )
        ]

    assert pivot is not None
    assert probe is not None
    assert breaker is not None
    assert topk is not None
    assert execution is not None

    truth = pivot.get("current_truth") if isinstance(pivot.get("current_truth"), dict) else {}
    gate = pivot.get("micro_canary_gate") if isinstance(pivot.get("micro_canary_gate"), dict) else {}
    decision = pivot.get("structural_decision") if isinstance(pivot.get("structural_decision"), dict) else {}
    hard_no_go = pivot.get("hard_no_go_now") if isinstance(pivot.get("hard_no_go_now"), dict) else {}
    details = probe.get("deployment_blocker_details") if isinstance(probe.get("deployment_blocker_details"), dict) else {}
    release = breaker.get("release_condition") if isinstance(breaker.get("release_condition"), dict) else {}
    topk_live_support_freshness = _topk_live_support_freshness_fields(probe.get("generated_at"))
    topk_support_context_deployment_blocking = topk_live_support_freshness.get("support_context_deployment_blocking")
    topk_support_context_status = (
        "stale_live_probe_shadow_only"
        if topk_support_context_deployment_blocking
        else "fresh_live_probe_overlay"
    )
    topk_live_truth_overlay_blocker = (
        topk_live_support_freshness.get("support_context_freshness_reason")
        if topk_support_context_deployment_blocking
        else "—"
    )

    rows = _first_present(
        probe.get("current_live_structure_bucket_rows"),
        details.get("current_live_structure_bucket_rows"),
    )
    minimum = _first_present(
        probe.get("minimum_support_rows"),
        details.get("minimum_support_rows"),
    )
    gap = _first_present(
        probe.get("current_live_structure_bucket_gap_to_minimum"),
        details.get("current_live_structure_bucket_gap_to_minimum"),
    )
    topk_deployable_rows = _first_present(
        topk.get("deployable_rows"),
        topk.get("deployable_count"),
    )

    mismatches: list[str] = []
    expected_pairs = {
        "structure_bucket": (
            truth.get("structure_bucket"),
            _first_present(
                probe.get("current_live_structure_bucket"),
                details.get("current_live_structure_bucket"),
            ),
        ),
        "support_rows": (truth.get("support_rows"), rows),
        "minimum_support_rows": (truth.get("minimum_support_rows"), minimum),
        "support_gap": (truth.get("support_gap"), gap),
        "deployment_blocker": (
            truth.get("deployment_blocker"),
            _first_present(probe.get("deployment_blocker"), details.get("deployment_blocker")),
        ),
        "release_ready": (truth.get("release_ready"), release.get("release_ready")),
        "recent_window_wins": (
            truth.get("recent_window_wins"),
            release.get("current_recent_window_wins"),
        ),
        "additional_recent_window_wins_needed": (
            truth.get("additional_recent_window_wins_needed"),
            release.get("additional_recent_window_wins_needed"),
        ),
        "deployable_rows": (truth.get("deployable_rows"), topk_deployable_rows),
        "venue_runtime_ready": (truth.get("venue_runtime_ready"), execution.get("runtime_ready")),
    }
    for field, (actual, expected) in expected_pairs.items():
        if actual != expected:
            mismatches.append(f"{field}: pivot={actual!r} current={expected!r}")

    primary_gate = gate.get("single_failed_gate_for_72h_decision")
    if decision.get("single_failed_gate_for_72h_decision") != primary_gate:
        mismatches.append("structural_decision.single_failed_gate_for_72h_decision differs from micro_canary_gate")
    if hard_no_go.get("order_submission_enabled") != gate.get("order_submission_enabled"):
        mismatches.append("hard_no_go_now.order_submission_enabled differs from micro_canary_gate")
    if gate.get("micro_canary_ready") and primary_gate != "none":
        mismatches.append("micro_canary_ready true while single_failed_gate_for_72h_decision is not none")
    if not gate.get("micro_canary_ready") and gate.get("order_submission_enabled"):
        mismatches.append("order_submission_enabled true while micro_canary_ready false")

    return [
        CheckResult(
            "pm_live_canary_pivot_current_truth",
            "Live-canary structural pivot matches current artifacts?",
            not mismatches,
            "ok" if not mismatches else "; ".join(mismatches),
        )
    ]


def _check_customer_safe_alternative_current_truth() -> list[CheckResult]:
    """Ensure the customer-safe proof's quick-read summary cannot drift."""

    artifact_errors: list[str] = []
    proof, error = _load_json_artifact("data/customer_safe_alternative_proof.json")
    if error:
        artifact_errors.append(error)
    probe, error = _load_json_artifact("data/live_predict_probe.json")
    if error:
        artifact_errors.append(error)
    breaker, error = _load_json_artifact("data/circuit_breaker_audit.json")
    if error:
        artifact_errors.append(error)
    topk, error = _load_json_artifact("data/high_conviction_topk_oos_matrix.json")
    if error:
        artifact_errors.append(error)
    venue_dry_run, error = _load_json_artifact("data/venue_dry_run_proof.json")
    if error:
        artifact_errors.append(error)

    if artifact_errors:
        return [
            CheckResult(
                "pm_customer_safe_alternative_current_truth",
                "Customer-safe alternative proof summary matches current artifacts?",
                False,
                "artifact_errors=" + ", ".join(artifact_errors),
            )
        ]

    assert proof is not None
    assert probe is not None
    assert breaker is not None
    assert topk is not None
    assert venue_dry_run is not None

    summary = proof.get("summary") if isinstance(proof.get("summary"), dict) else {}
    gate = proof.get("live_deployment_gate") if isinstance(proof.get("live_deployment_gate"), dict) else {}
    support = proof.get("current_live_support") if isinstance(proof.get("current_live_support"), dict) else {}
    topk_ctx = proof.get("topk_shadow_candidate_context") if isinstance(proof.get("topk_shadow_candidate_context"), dict) else {}
    venue = proof.get("venue_runtime_proof") if isinstance(proof.get("venue_runtime_proof"), dict) else {}
    circuit = proof.get("circuit_breaker_gate") if isinstance(proof.get("circuit_breaker_gate"), dict) else {}
    portfolio = proof.get("alternative_solution_portfolio") if isinstance(proof.get("alternative_solution_portfolio"), dict) else {}
    alternative_solutions = proof.get("alternative_solutions") if isinstance(proof.get("alternative_solutions"), list) else []
    blocked_live_lanes = proof.get("blocked_live_lanes") if isinstance(proof.get("blocked_live_lanes"), list) else []
    next_customer_actions = proof.get("next_customer_actions") if isinstance(proof.get("next_customer_actions"), list) else []
    details = probe.get("deployment_blocker_details") if isinstance(probe.get("deployment_blocker_details"), dict) else {}
    release = breaker.get("release_condition") if isinstance(breaker.get("release_condition"), dict) else {}
    topk_live_support_freshness = _topk_live_support_freshness_fields(probe.get("generated_at"))
    topk_support_context_deployment_blocking = topk_live_support_freshness.get(
        "support_context_deployment_blocking"
    )
    topk_support_context_status = (
        "stale_live_probe_shadow_only"
        if topk_support_context_deployment_blocking
        else "fresh_live_probe_overlay"
    )
    topk_live_truth_overlay_blocker = (
        topk_live_support_freshness.get("support_context_freshness_reason")
        if topk_support_context_deployment_blocking
        else "—"
    )

    rows = _first_present(
        probe.get("current_live_structure_bucket_rows"),
        details.get("current_live_structure_bucket_rows"),
    )
    minimum = _first_present(
        probe.get("minimum_support_rows"),
        details.get("minimum_support_rows"),
    )
    gap = _first_present(
        probe.get("current_live_structure_bucket_gap_to_minimum"),
        details.get("current_live_structure_bucket_gap_to_minimum"),
    )

    mismatches: list[str] = []
    if not summary:
        mismatches.append("summary missing")

    expected_pairs = {
        "live_exposure_allowed": (summary.get("live_exposure_allowed"), gate.get("live_exposure_allowed")),
        "order_submission_enabled": (summary.get("order_submission_enabled"), gate.get("order_submission_enabled")),
        "risk_on_order_enabled": (summary.get("risk_on_order_enabled"), gate.get("risk_on_order_enabled")),
        "canary_ready": (summary.get("canary_ready"), gate.get("canary_ready")),
        "support_ready": (summary.get("support_ready"), gate.get("support_ready")),
        "topk_deployable": (summary.get("topk_deployable"), gate.get("topk_deployable")),
        "venue_runtime_ready": (summary.get("venue_runtime_ready"), gate.get("venue_runtime_ready")),
        "breaker_release_ready": (summary.get("breaker_release_ready"), circuit.get("release_ready")),
        "blocking_gate": (summary.get("blocking_gate"), gate.get("blocking_gate")),
        "primary_blocking_gate": (summary.get("primary_blocking_gate"), gate.get("primary_blocking_gate")),
        "blocking_gates": (summary.get("blocking_gates"), gate.get("blocking_gates")),
        "support_rows": (summary.get("support_rows"), support.get("current_rows")),
        "minimum_support_rows": (summary.get("minimum_support_rows"), support.get("minimum_support_rows")),
        "support_gap": (summary.get("support_gap"), support.get("gap_to_minimum")),
        "support_route_verdict": (summary.get("support_route_verdict"), support.get("support_route_verdict")),
        "support_governance_route": (summary.get("support_governance_route"), support.get("support_governance_route")),
        "deployment_blocker": (summary.get("deployment_blocker"), support.get("deployment_blocker")),
        "current_live_structure_bucket": (summary.get("current_live_structure_bucket"), support.get("structure_bucket")),
        "current_recent_window_wins": (summary.get("current_recent_window_wins"), circuit.get("current_recent_window_wins")),
        "required_recent_window_wins": (summary.get("required_recent_window_wins"), circuit.get("required_recent_window_wins")),
        "additional_recent_window_wins_needed": (
            summary.get("additional_recent_window_wins_needed"),
            circuit.get("additional_recent_window_wins_needed"),
        ),
        "topk_risk_qualified_rows": (summary.get("topk_risk_qualified_rows"), topk_ctx.get("risk_qualified_rows")),
        "topk_runtime_blocked_candidate_rows": (
            summary.get("topk_runtime_blocked_candidate_rows"),
            topk_ctx.get("runtime_blocked_candidate_rows"),
        ),
        "topk_deployable_rows": (summary.get("topk_deployable_rows"), topk_ctx.get("deployable_rows")),
        "topk_support_context_status": (
            summary.get("topk_support_context_status"),
            topk_ctx.get("support_context_status"),
        ),
        "topk_support_context_freshness_status": (
            summary.get("topk_support_context_freshness_status"),
            topk_ctx.get("support_context_freshness_status"),
        ),
        "topk_support_context_freshness_reason": (
            summary.get("topk_support_context_freshness_reason"),
            topk_ctx.get("support_context_freshness_reason"),
        ),
        "topk_support_context_deployment_blocking": (
            summary.get("topk_support_context_deployment_blocking"),
            topk_ctx.get("support_context_deployment_blocking"),
        ),
        "topk_live_truth_overlay_blocker": (
            summary.get("topk_live_truth_overlay_blocker"),
            topk_ctx.get("live_truth_overlay_blocker"),
        ),
        "venue_status": (summary.get("venue_status"), venue.get("status")),
        "venue_runtime_ready_count": (summary.get("venue_runtime_ready_count"), venue.get("runtime_ready_count")),
        "blocked_live_lane_count": (summary.get("blocked_live_lane_count"), len(blocked_live_lanes)),
        "alternative_solution_required": (
            summary.get("alternative_solution_required"),
            proof.get("alternative_solution_required"),
        ),
        "alternative_solution_option_count": (
            summary.get("alternative_solution_option_count"),
            len(alternative_solutions),
        ),
        "alternative_solution_options": (
            summary.get("alternative_solution_options"),
            len(alternative_solutions),
        ),
        "selected_alternative_solution": (
            summary.get("selected_alternative_solution"),
            proof.get("selected_alternative_solution"),
        ),
        "selected_alternative": (
            summary.get("selected_alternative"),
            proof.get("selected_alternative_solution"),
        ),
        "selected_next_customer_artifact": (
            summary.get("selected_next_customer_artifact"),
            proof.get("selected_next_customer_artifact"),
        ),
        "selected_next_artifact": (
            summary.get("selected_next_artifact"),
            proof.get("selected_next_customer_artifact"),
        ),
        "next_customer_action_count": (summary.get("next_customer_action_count"), len(next_customer_actions)),
    }
    top_level_mirrors = [
        "live_exposure_allowed",
        "order_submission_enabled",
        "risk_on_order_enabled",
        "support_rows",
        "minimum_support_rows",
        "support_gap",
        "blocking_gate",
        "primary_blocking_gate",
        "blocking_gates",
        "breaker_release_ready",
        "current_recent_window_wins",
        "required_recent_window_wins",
        "additional_recent_window_wins_needed",
        "topk_deployable_rows",
        "topk_risk_qualified_rows",
        "topk_runtime_blocked_candidate_rows",
        "topk_support_context_status",
        "topk_support_context_freshness_status",
        "topk_support_context_freshness_reason",
        "topk_support_context_deployment_blocking",
        "topk_live_truth_overlay_blocker",
        "venue_runtime_ready",
        "venue_status",
        "blocked_live_lane_count",
        "alternative_solution_required",
        "alternative_solution_option_count",
        "alternative_solution_options",
        "selected_alternative_solution",
        "selected_alternative",
        "selected_next_customer_artifact",
        "selected_next_artifact",
        "next_customer_action_count",
    ]
    for field in top_level_mirrors:
        expected_pairs[f"top_level.{field}"] = (proof.get(field), summary.get(field))
    current_pairs = {
        "current.support_rows": (summary.get("support_rows"), rows),
        "current.minimum_support_rows": (summary.get("minimum_support_rows"), minimum),
        "current.support_gap": (summary.get("support_gap"), gap),
        "current.support_route_verdict": (
            summary.get("support_route_verdict"),
            _first_present(probe.get("support_route_verdict"), details.get("support_route_verdict")),
        ),
        "current.support_governance_route": (
            summary.get("support_governance_route"),
            _first_present(probe.get("support_governance_route"), details.get("support_governance_route")),
        ),
        "current.deployment_blocker": (
            summary.get("deployment_blocker"),
            _first_present(probe.get("deployment_blocker"), details.get("deployment_blocker")),
        ),
        "current.current_live_structure_bucket": (
            summary.get("current_live_structure_bucket"),
            _first_present(probe.get("current_live_structure_bucket"), details.get("current_live_structure_bucket")),
        ),
        "current.breaker_release_ready": (summary.get("breaker_release_ready"), release.get("release_ready")),
        "current.current_recent_window_wins": (
            summary.get("current_recent_window_wins"),
            release.get("current_recent_window_wins"),
        ),
        "current.required_recent_window_wins": (
            summary.get("required_recent_window_wins"),
            release.get("required_recent_window_wins"),
        ),
        "current.additional_recent_window_wins_needed": (
            summary.get("additional_recent_window_wins_needed"),
            release.get("additional_recent_window_wins_needed"),
        ),
        "current.topk_deployable_rows": (summary.get("topk_deployable_rows"), topk.get("deployable_rows")),
        "current.topk_risk_qualified_rows": (summary.get("topk_risk_qualified_rows"), topk.get("risk_qualified_rows")),
        "current.topk_runtime_blocked_candidate_rows": (
            summary.get("topk_runtime_blocked_candidate_rows"),
            topk.get("runtime_blocked_candidate_rows"),
        ),
        "current.topk_support_context_status": (
            summary.get("topk_support_context_status"),
            topk_support_context_status,
        ),
        "current.topk_support_context_freshness_status": (
            summary.get("topk_support_context_freshness_status"),
            topk_live_support_freshness.get("support_context_freshness_status"),
        ),
        "current.topk_support_context_freshness_reason": (
            summary.get("topk_support_context_freshness_reason"),
            topk_live_support_freshness.get("support_context_freshness_reason"),
        ),
        "current.topk_support_context_deployment_blocking": (
            summary.get("topk_support_context_deployment_blocking"),
            topk_live_support_freshness.get("support_context_deployment_blocking"),
        ),
        "current.topk_live_truth_overlay_blocker": (
            summary.get("topk_live_truth_overlay_blocker"),
            topk_live_truth_overlay_blocker,
        ),
        "current.venue_runtime_ready": (summary.get("venue_runtime_ready"), venue_dry_run.get("runtime_ready")),
        "current.venue_status": (summary.get("venue_status"), venue_dry_run.get("status")),
        "current.venue_runtime_ready_count": (
            summary.get("venue_runtime_ready_count"),
            venue_dry_run.get("runtime_ready_count"),
        ),
    }
    expected_pairs.update(current_pairs)
    for field, (actual, expected) in expected_pairs.items():
        if actual != expected:
            mismatches.append(f"{field}: proof={actual!r} current={expected!r}")

    live_enabled = summary.get("live_exposure_allowed") is True
    all_gates_ready = all(
        summary.get(field) is True
        for field in ("support_ready", "topk_deployable", "venue_runtime_ready", "breaker_release_ready")
    )
    if live_enabled and not all_gates_ready:
        mismatches.append("live_exposure_allowed true while one or more live gates are false")
    if not live_enabled:
        for field in ("order_submission_enabled", "risk_on_order_enabled"):
            if summary.get(field) is True:
                mismatches.append(f"{field} true while live_exposure_allowed false")
    if summary.get("blocking_gate") == "none" and not all_gates_ready:
        mismatches.append("blocking_gate none while one or more live gates are false")
    if portfolio:
        if proof.get("alternative_solution_option_count") != portfolio.get("option_count"):
            mismatches.append("alternative_solution_option_count differs from portfolio.option_count")
        if proof.get("alternative_solution_options") != portfolio.get("option_count"):
            mismatches.append("alternative_solution_options differs from portfolio.option_count")
        if proof.get("selected_alternative_solution") != portfolio.get("selected_option"):
            mismatches.append("selected_alternative_solution differs from portfolio.selected_option")
        if proof.get("selected_alternative") != portfolio.get("selected_option"):
            mismatches.append("selected_alternative differs from portfolio.selected_option")
        if proof.get("selected_next_customer_artifact") != portfolio.get("selected_next_artifact"):
            mismatches.append("selected_next_customer_artifact differs from portfolio.selected_next_artifact")
        if proof.get("selected_next_artifact") != portfolio.get("selected_next_artifact"):
            mismatches.append("selected_next_artifact differs from portfolio.selected_next_artifact")
    if proof.get("alternative_solution_required") is True and len(alternative_solutions) < 3:
        mismatches.append("alternative_solution_required true while fewer than 3 alternative_solutions are exposed")
    for idx, option in enumerate(alternative_solutions):
        if not isinstance(option, dict):
            mismatches.append(f"alternative_solutions[{idx}] is not an object")
            continue
        for field in ("deployable", "live_exposure_allowed", "order_submission_enabled", "risk_on_order_enabled"):
            if option.get(field) is not False:
                mismatches.append(f"alternative_solutions[{idx}].{field} expected False, got {option.get(field)!r}")
    if not live_enabled:
        if not blocked_live_lanes:
            mismatches.append("live_exposure_allowed false while blocked_live_lanes is empty")
        if not next_customer_actions:
            mismatches.append("live_exposure_allowed false while next_customer_actions is empty")
        for idx, lane in enumerate(blocked_live_lanes):
            if not isinstance(lane, dict):
                mismatches.append(f"blocked_live_lanes[{idx}] is not an object")
                continue
            for field in ("live_exposure_allowed", "order_submission_enabled", "risk_on_order_enabled"):
                if lane.get(field) is not False:
                    mismatches.append(f"blocked_live_lanes[{idx}].{field} expected False, got {lane.get(field)!r}")
            if not lane.get("blocked_actions"):
                mismatches.append(f"blocked_live_lanes[{idx}].blocked_actions missing")
            release_condition = lane.get("release_condition") if isinstance(lane.get("release_condition"), dict) else {}
            if release_condition.get("support_rows") != summary.get("support_rows"):
                mismatches.append(f"blocked_live_lanes[{idx}].release_condition.support_rows differs from summary")
            if release_condition.get("primary_blocking_gate") != summary.get("primary_blocking_gate"):
                mismatches.append(f"blocked_live_lanes[{idx}].release_condition.primary_blocking_gate differs from summary")
        for idx, action in enumerate(next_customer_actions):
            if not isinstance(action, dict):
                mismatches.append(f"next_customer_actions[{idx}] is not an object")
                continue
            for field in ("live_exposure_allowed", "order_submission_enabled", "risk_on_order_enabled"):
                if action.get(field) is not False:
                    mismatches.append(f"next_customer_actions[{idx}].{field} expected False, got {action.get(field)!r}")

    return [
        CheckResult(
            "pm_customer_safe_alternative_current_truth",
            "Customer-safe alternative proof summary matches current artifacts?",
            not mismatches,
            "ok" if not mismatches else "; ".join(mismatches),
        )
    ]


def _check_paper_shadow_rehearsal_fail_closed_truth() -> list[CheckResult]:
    """Ensure paper/shadow rehearsal proof stays a no-live-order safe lane."""

    artifact, error = _load_json_artifact("data/paper_shadow_outcome_reconciliation.json")
    if error:
        return [
            CheckResult(
                "pm_paper_shadow_rehearsal_fail_closed_truth",
                "Paper/shadow rehearsal proof remains fail-closed?",
                False,
                error,
            )
        ]

    assert artifact is not None
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    proof = artifact.get("rehearsal_proof") if isinstance(artifact.get("rehearsal_proof"), dict) else {}
    quick_read = artifact.get("quick_read") if isinstance(artifact.get("quick_read"), dict) else {}
    mismatches: list[str] = []
    if not summary:
        mismatches.append("summary missing")
    if not proof:
        mismatches.append("rehearsal_proof missing")
    if not quick_read:
        mismatches.append("quick_read missing")

    false_fields = {
        "artifact.order_submission_enabled": artifact.get("order_submission_enabled"),
        "artifact.risk_on_order_enabled": artifact.get("risk_on_order_enabled"),
        "artifact.live_order_submitted": artifact.get("live_order_submitted"),
        "summary.live_order_submitted": summary.get("live_order_submitted"),
        "rehearsal_proof.order_submission_enabled": proof.get("order_submission_enabled"),
        "rehearsal_proof.risk_on_order_enabled": proof.get("risk_on_order_enabled"),
        "rehearsal_proof.live_order_submitted": proof.get("live_order_submitted"),
    }
    if quick_read:
        false_fields.update(
            {
                "quick_read.order_submission_enabled": quick_read.get("order_submission_enabled"),
                "quick_read.risk_on_order_enabled": quick_read.get("risk_on_order_enabled"),
                "quick_read.live_order_submitted": quick_read.get("live_order_submitted"),
            }
        )
    for field, value in false_fields.items():
        if value is not False:
            mismatches.append(f"{field} expected False, got {value!r}")

    pending = _as_int(summary.get("pending_outcomes")) or 0
    expected_top_level = {
        "rehearsal_status": proof.get("status"),
        "worker_poll_events": _as_int(summary.get("worker_poll_events")) or 0,
        "pending_outcomes": pending,
        "resolved_outcomes": _as_int(summary.get("resolved_outcomes")) or 0,
        "awaiting_label_replay": _as_int(summary.get("awaiting_label_replay")) or 0,
        "parity_blocked_events": _as_int(summary.get("parity_blocked_events")) or 0,
        "can_poll_workers": proof.get("can_poll_workers"),
        "poll_blocked_by_pending_outcome": proof.get("poll_blocked_by_pending_outcome"),
        "next_reconcile_at": proof.get("next_reconcile_at"),
        "pending_hours_remaining_min": proof.get("pending_hours_remaining_min"),
        "resolution_due_count": _as_int(proof.get("resolution_due_count")) or 0,
    }
    for field, expected in expected_top_level.items():
        if artifact.get(field) != expected:
            mismatches.append(f"artifact.{field} expected {expected!r}, got {artifact.get(field)!r}")
        if quick_read and quick_read.get(field) != expected:
            mismatches.append(f"quick_read.{field} expected {expected!r}, got {quick_read.get(field)!r}")
    reconciliation_due = expected_top_level["resolution_due_count"] > 0
    if artifact.get("reconciliation_due") is not reconciliation_due:
        mismatches.append(
            f"artifact.reconciliation_due expected {reconciliation_due!r}, got {artifact.get('reconciliation_due')!r}"
        )
    if quick_read and quick_read.get("reconciliation_due") is not reconciliation_due:
        mismatches.append(
            f"quick_read.reconciliation_due expected {reconciliation_due!r}, got {quick_read.get('reconciliation_due')!r}"
        )

    if pending > 0:
        if proof.get("poll_blocked_by_pending_outcome") is not True:
            mismatches.append("pending_outcomes > 0 while poll_blocked_by_pending_outcome is not true")
        if proof.get("can_poll_workers") is not False:
            mismatches.append("pending_outcomes > 0 while can_poll_workers is not false")
        if not proof.get("next_reconcile_at"):
            mismatches.append("pending_outcomes > 0 while next_reconcile_at is missing")

    return [
        CheckResult(
            "pm_paper_shadow_rehearsal_fail_closed_truth",
            "Paper/shadow rehearsal proof remains fail-closed?",
            not mismatches,
            "ok" if not mismatches else "; ".join(mismatches),
        )
    ]


def run_checks(*, contract_only: bool = False) -> dict[str, Any]:
    contract, results = _load_contract()
    if contract is not None:
        results.extend(_check_required_docs(contract))
        results.extend(_check_entrypoints(contract))
        results.extend(_check_question_gates(contract))
        results.extend(_check_doc_references())
        if not contract_only:
            results.extend(_check_pm_status_current_state())
            results.extend(_check_customer_safe_alternative_current_truth())
            results.extend(_check_paper_shadow_rehearsal_fail_closed_truth())
            results.extend(_check_live_canary_pivot_current_truth())

    ok = all(result.ok for result in results)
    return {
        "ok": ok,
        "scope": "contract" if contract_only else "full_runtime",
        "contract_path": str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
        "checks": [result.as_dict() for result in results],
    }


def _format_text(payload: dict[str, Any]) -> str:
    lines = ["Poly-Trader PM heartbeat harness check"]
    for check in payload["checks"]:
        status = "PASS" if check["ok"] else "FAIL"
        lines.append(f"Q: {check['question']}")
        lines.append(f"A: {status} — {check['detail']}")
        lines.append("")
    lines.append(f"RESULT: {'PASS' if payload['ok'] else 'FAIL'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--contract-only",
        action="store_true",
        help="Validate deterministic PM harness contracts without volatile runtime artifacts.",
    )
    args = parser.parse_args(argv)

    payload = run_checks(contract_only=args.contract_only)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_format_text(payload))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
