from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "docs" / "ai-collaboration" / "pm" / "pm-heartbeat-contract.json"
QA_PATH = PROJECT_ROOT / "docs" / "ai-collaboration" / "pm" / "pm-heartbeat-qa.md"
STATUS_PATH = PROJECT_ROOT / "docs" / "ai-collaboration" / "pm" / "pm-status.md"
TOPK_STALE_AFTER_MINUTES = 60.0
TOPK_LIVE_SUPPORT_STALE_AFTER_MINUTES = 30.0
PM_CHECK_PATH = PROJECT_ROOT / "scripts" / "pm_heartbeat_check.py"
PM_CHECK_SPEC = importlib.util.spec_from_file_location("pm_heartbeat_check_test_module", PM_CHECK_PATH)
pm_heartbeat_check = importlib.util.module_from_spec(PM_CHECK_SPEC)
assert PM_CHECK_SPEC.loader is not None
sys.modules[PM_CHECK_SPEC.name] = pm_heartbeat_check
PM_CHECK_SPEC.loader.exec_module(pm_heartbeat_check)


def _first_present(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _num_text(value, digits: int = 4):
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


def _topk_freshness_status(generated_at):
    try:
        generated_dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    except ValueError:
        return "unavailable"
    if generated_dt.tzinfo is None:
        generated_dt = generated_dt.replace(tzinfo=timezone.utc)
    age_minutes = max((datetime.now(timezone.utc) - generated_dt.astimezone(timezone.utc)).total_seconds(), 0.0) / 60.0
    return "fresh" if age_minutes <= TOPK_STALE_AFTER_MINUTES else "stale"


def _topk_live_support_freshness_status(generated_at):
    try:
        generated_dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    except ValueError:
        return "unavailable"
    if generated_dt.tzinfo is None:
        generated_dt = generated_dt.replace(tzinfo=timezone.utc)
    age_minutes = max((datetime.now(timezone.utc) - generated_dt.astimezone(timezone.utc)).total_seconds(), 0.0) / 60.0
    return "fresh" if age_minutes <= TOPK_LIVE_SUPPORT_STALE_AFTER_MINUTES else "stale"


def _support_ready(rows, minimum, gap, support_route) -> bool:
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


def test_pm_heartbeat_contract_is_machine_readable() -> None:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert payload["purpose"].startswith("Poly-Trader PM heartbeat contract")

    entrypoints = payload["entrypoints"]
    for key in [
        "pm_charter",
        "pm_readme",
        "pm_qa_playbook",
        "pm_status",
        "pm_validator",
        "pm_validator_test",
        "engineering_heartbeat",
        "engineering_harness",
        "high_conviction_topk_api_consistency_probe",
        "venue_api_consistency_probe",
        "customer_safe_alternative_proof",
        "customer_safe_alternative_api_consistency_probe",
        "paper_shadow_outcome_reconciliation",
        "paper_shadow_outcome_reconciliation_cli",
        "paper_shadow_outcome_api_consistency_probe",
    ]:
        rel_path = entrypoints[key]
        assert (PROJECT_ROOT / rel_path).exists(), rel_path

    gate_ids = {gate["id"] for gate in payload["question_gates"]}
    assert gate_ids == set(REQUIRED_GATE_IDS)
    pmhq2 = next(gate for gate in payload["question_gates"] if gate["id"] == "PMHQ2_artifact_truth")
    assert "data/customer_safe_alternative_proof.json" in pmhq2["required_evidence"]
    assert "data/paper_shadow_outcome_reconciliation.json" in pmhq2["required_evidence"]
    signals = {signal["name"]: signal for signal in payload["agent_readable_signals"]}
    assert "data/customer_safe_alternative_proof.json" in signals["customer_safe_usable_lane_truth"]["paths"]
    assert "scripts/high_conviction_topk_api_consistency_probe.py" in signals["customer_safe_usable_lane_truth"]["paths"]
    assert "/api/models/leaderboard.high_conviction_topk" in signals["customer_safe_usable_lane_truth"]["paths"]
    assert "scripts/customer_safe_alternative_api_consistency_probe.py" in signals["customer_safe_usable_lane_truth"]["paths"]
    assert "/api/execution/overview.customer_safe_alternative_proof" in signals["customer_safe_usable_lane_truth"]["paths"]
    assert "data/paper_shadow_outcome_reconciliation.json" in signals["paper_shadow_rehearsal_truth"]["paths"]
    assert "scripts/paper_shadow_outcome_api_consistency_probe.py" in signals["paper_shadow_rehearsal_truth"]["paths"]
    assert "/api/execution/overview.paper_shadow_outcome_reconciliation" in signals["paper_shadow_rehearsal_truth"]["paths"]
    invariant_ids = {item["id"] for item in payload["mechanical_invariants"]}
    assert "pm_customer_safe_alternative_current_truth" in invariant_ids
    assert "pm_paper_shadow_rehearsal_fail_closed_truth" in invariant_ids
    assert payload["customer_advocacy_policy"]["stance"] == "customer_side_advocate"
    assert payload["framework_capture_guard"]["verdict_when_process_blocks_value"] == "framework_capture_risk"
    assert "ORANGE_framework_capture_risk" in payload["pm_decision_states"]
    assert "ORANGE_alternative_solution_required" in payload["pm_decision_states"]
    assert payload["alternative_solution_guard"]["trigger"].startswith("verification horizon")
    anti_equilibrium = payload["anti_equilibrium_guard"]
    assert anti_equilibrium["risk_name"] == "pm_convergence_to_waiting_equilibrium"
    for required in ["customer-value delta", "anti-repeat result", "cost-of-delay estimate", "hypothesis inversion", "option portfolio", "red-team PM challenge"]:
        assert required in anti_equilibrium["required_fields"]
    forced = payload["forced_execution_pivot_guard"]
    assert forced["risk_name"] == "pm_convergence_to_observation_only_status"
    assert "Venue lifecycle proof" in forced["required_lanes"]
    assert "Model shadow to decision" in forced["required_lanes"]
    assert "Strategy micro-canary readiness" in forced["required_lanes"]
    assert "72h" in forced["decision_clock"]
    assert "adapter-pre cap enforcement" in forced["bounded_live_canary_boundary"]["live_buy_add_requires"]

    qa_text = QA_PATH.read_text(encoding="utf-8")
    for gate_id in REQUIRED_GATE_IDS:
        assert gate_id in qa_text


def test_pm_heartbeat_checker_passes() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/pm_heartbeat_check.py", "--contract-only", "--format", "json"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    check_ids = {check["id"] for check in payload["checks"]}
    assert check_ids >= {
        "pm_contract_exists",
        "pm_required_docs_exist",
        "pm_entrypoints_exist",
        "pm_qa_gates_complete",
        "AGENTS.md:pm_references",
        "docs/ai-collaboration/PM_HEARTBEAT.md:pm_references",
        "README.md:pm_references",
        "ARCHITECTURE.md:pm_references",
    }
    assert "pm_status_current_state_fields" not in check_ids
    assert "pm_customer_safe_alternative_current_truth" not in check_ids
    assert "pm_live_canary_pivot_current_truth" not in check_ids


def test_pm_checker_text_mode_is_question_answer_style() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/pm_heartbeat_check.py", "--contract-only", "--format", "text"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Q: PM contract file exists?" in completed.stdout
    assert "A: PASS" in completed.stdout
    assert "RESULT: PASS" in completed.stdout


def test_pm_status_is_snapshot_not_release_source_of_truth() -> None:
    text = STATUS_PATH.read_text(encoding="utf-8")

    assert "this file is not a release source of truth" in text
    assert "python scripts/pm_heartbeat_check.py --format text" in text
    assert "--contract-only" in text
    assert "must never authorize Promotion, Live, order submission, or risk-on behavior" in text
    assert "must remain fail-closed" in text


def test_pm_checker_flags_stale_current_artifacts(monkeypatch) -> None:
    now = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)
    fresh = now - timedelta(minutes=5)
    stale = now - timedelta(
        minutes=pm_heartbeat_check.PM_CURRENT_ARTIFACT_STALE_AFTER_MINUTES + 1
    )

    def fake_load_json_artifact(rel_path: str):
        generated_at = stale if rel_path == "data/recent_drift_report.json" else fresh
        return {"generated_at": generated_at.isoformat()}, None

    monkeypatch.setattr(
        pm_heartbeat_check,
        "_load_json_artifact",
        fake_load_json_artifact,
    )

    snippets, errors = pm_heartbeat_check._pm_current_artifact_freshness_snippets(now=now)

    assert "data/recent_drift_report.json freshness_status=stale" in snippets
    assert any("data/recent_drift_report.json stale current artifact" in error for error in errors)


def test_pm_checker_flags_live_canary_pivot_drift(monkeypatch) -> None:
    artifacts = {
        "data/live_canary_structural_pivot.json": {
            "current_truth": {
                "structure_bucket": "STALE|old|q00",
                "support_rows": 1,
                "minimum_support_rows": 50,
                "support_gap": 49,
                "deployment_blocker": "circuit_breaker_active",
                "release_ready": False,
                "recent_window_wins": 0,
                "additional_recent_window_wins_needed": 15,
                "deployable_rows": 0,
                "venue_runtime_ready": False,
            },
            "micro_canary_gate": {
                "micro_canary_ready": False,
                "order_submission_enabled": False,
                "single_failed_gate_for_72h_decision": "circuit_breaker_gate",
            },
            "structural_decision": {
                "single_failed_gate_for_72h_decision": "circuit_breaker_gate",
            },
            "hard_no_go_now": {
                "order_submission_enabled": False,
            },
        },
        "data/live_predict_probe.json": {
            "deployment_blocker": "circuit_breaker_active",
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
            "current_live_structure_bucket_rows": 6,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 44,
        },
        "data/circuit_breaker_audit.json": {
            "release_condition": {
                "release_ready": False,
                "current_recent_window_wins": 0,
                "additional_recent_window_wins_needed": 15,
            },
        },
        "data/high_conviction_topk_oos_matrix.json": {
            "deployable_rows": 0,
        },
        "data/execution_metadata_smoke.json": {
            "runtime_ready": False,
        },
    }

    def fake_load_json_artifact(rel_path: str):
        return artifacts[rel_path], None

    monkeypatch.setattr(
        pm_heartbeat_check,
        "_load_json_artifact",
        fake_load_json_artifact,
    )

    result = pm_heartbeat_check._check_live_canary_pivot_current_truth()[0]

    assert result.ok is False
    assert "structure_bucket" in result.detail
    assert "support_rows" in result.detail


def test_pm_checker_flags_customer_safe_summary_drift(monkeypatch) -> None:
    artifacts = {
        "data/customer_safe_alternative_proof.json": {
            "summary": {
                "canary_ready": False,
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "support_ready": False,
                "topk_deployable": False,
                "venue_runtime_ready": False,
                "breaker_release_ready": False,
                "blocking_gate": "circuit_breaker_gate",
                "primary_blocking_gate": "circuit_breaker_gate",
                "blocking_gates": ["circuit_breaker_gate", "current_live_support_gate"],
                "support_rows": 99,
                "minimum_support_rows": 50,
                "support_gap": 0,
                "support_route_verdict": "exact_bucket_supported",
                "support_governance_route": "exact_live_bucket_supported",
                "deployment_blocker": "circuit_breaker_active",
                "current_live_structure_bucket": "BLOCK|bias200_below_min|q00",
                "current_recent_window_wins": 9,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 6,
                "topk_risk_qualified_rows": 6,
                "topk_runtime_blocked_candidate_rows": 6,
                "topk_deployable_rows": 0,
                "venue_status": "blocked_missing_runtime_backed_proof",
                "venue_runtime_ready_count": 0,
            },
            "live_exposure_allowed": False,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "support_rows": 99,
            "minimum_support_rows": 50,
            "support_gap": 0,
            "blocking_gate": "circuit_breaker_gate",
            "primary_blocking_gate": "circuit_breaker_gate",
            "blocking_gates": ["circuit_breaker_gate", "current_live_support_gate"],
            "breaker_release_ready": False,
            "current_recent_window_wins": 9,
            "required_recent_window_wins": 15,
            "additional_recent_window_wins_needed": 6,
            "topk_deployable_rows": 0,
            "topk_risk_qualified_rows": 6,
            "topk_runtime_blocked_candidate_rows": 6,
            "venue_runtime_ready": False,
            "venue_status": "blocked_missing_runtime_backed_proof",
            "live_deployment_gate": {
                "canary_ready": False,
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "support_ready": False,
                "topk_deployable": False,
                "venue_runtime_ready": False,
                "breaker_release_ready": False,
                "blocking_gate": "circuit_breaker_gate",
                "primary_blocking_gate": "circuit_breaker_gate",
                "blocking_gates": ["circuit_breaker_gate", "current_live_support_gate"],
            },
            "current_live_support": {
                "current_rows": 0,
                "minimum_support_rows": 50,
                "gap_to_minimum": 50,
                "support_route_verdict": "exact_bucket_unsupported_block",
                "support_governance_route": "exact_live_lane_proxy_available",
                "deployment_blocker": "circuit_breaker_active",
                "structure_bucket": "BLOCK|bias200_below_min|q00",
            },
            "circuit_breaker_gate": {
                "release_ready": False,
                "current_recent_window_wins": 9,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 6,
            },
            "topk_shadow_candidate_context": {
                "risk_qualified_rows": 6,
                "runtime_blocked_candidate_rows": 6,
                "deployable_rows": 0,
            },
            "venue_runtime_proof": {
                "status": "blocked_missing_runtime_backed_proof",
                "runtime_ready_count": 0,
            },
        },
        "data/live_predict_probe.json": {
            "deployment_blocker": "circuit_breaker_active",
            "current_live_structure_bucket": "BLOCK|bias200_below_min|q00",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "support_route_verdict": "exact_bucket_unsupported_block",
            "support_governance_route": "exact_live_lane_proxy_available",
        },
        "data/circuit_breaker_audit.json": {
            "release_condition": {
                "release_ready": False,
                "current_recent_window_wins": 9,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 6,
            },
        },
        "data/high_conviction_topk_oos_matrix.json": {
            "deployable_rows": 0,
            "risk_qualified_rows": 6,
            "runtime_blocked_candidate_rows": 6,
        },
        "data/venue_dry_run_proof.json": {
            "runtime_ready": False,
            "status": "blocked_missing_runtime_backed_proof",
            "runtime_ready_count": 0,
        },
    }

    def fake_load_json_artifact(rel_path: str):
        return artifacts[rel_path], None

    monkeypatch.setattr(
        pm_heartbeat_check,
        "_load_json_artifact",
        fake_load_json_artifact,
    )

    result = pm_heartbeat_check._check_customer_safe_alternative_current_truth()[0]

    assert result.ok is False
    assert "support_rows" in result.detail
    assert "support_gap" in result.detail
    assert "support_route_verdict" in result.detail


def test_pm_checker_flags_unsafe_paper_shadow_rehearsal(monkeypatch) -> None:
    artifacts = {
        "data/paper_shadow_outcome_reconciliation.json": {
            "generated_at": "2026-06-04T05:00:00Z",
            "status": "recording_pending_outcomes",
            "rehearsal_status": "pending_observation_window",
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
            "worker_poll_events": 1,
            "pending_outcomes": 1,
            "resolved_outcomes": 0,
            "awaiting_label_replay": 0,
            "parity_blocked_events": 0,
            "can_poll_workers": True,
            "poll_blocked_by_pending_outcome": False,
            "next_reconcile_at": None,
            "pending_hours_remaining_min": None,
            "resolution_due_count": 0,
            "reconciliation_due": False,
            "summary": {
                "worker_poll_events": 1,
                "resolved_outcomes": 0,
                "pending_outcomes": 1,
                "awaiting_label_replay": 0,
                "parity_blocked_events": 0,
                "live_order_submitted": False,
            },
            "rehearsal_proof": {
                "status": "pending_observation_window",
                "can_poll_workers": True,
                "poll_blocked_by_pending_outcome": False,
                "next_reconcile_at": None,
                "order_submission_enabled": True,
                "risk_on_order_enabled": False,
                "live_order_submitted": False,
            },
        }
    }

    def fake_load_json_artifact(rel_path: str):
        return artifacts[rel_path], None

    monkeypatch.setattr(
        pm_heartbeat_check,
        "_load_json_artifact",
        fake_load_json_artifact,
    )

    result = pm_heartbeat_check._check_paper_shadow_rehearsal_fail_closed_truth()[0]

    assert result.ok is False
    assert "order_submission_enabled" in result.detail
    assert "poll_blocked_by_pending_outcome" in result.detail
    assert "can_poll_workers" in result.detail


def test_pm_checker_flags_paper_shadow_quick_read_drift(monkeypatch) -> None:
    artifacts = {
        "data/paper_shadow_outcome_reconciliation.json": {
            "generated_at": "2026-06-04T05:00:00Z",
            "status": "recording_pending_outcomes",
            "rehearsal_status": "pending_observation_window",
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
            "worker_poll_events": 1,
            "pending_outcomes": 1,
            "resolved_outcomes": 0,
            "awaiting_label_replay": 0,
            "parity_blocked_events": 0,
            "can_poll_workers": False,
            "poll_blocked_by_pending_outcome": True,
            "next_reconcile_at": "2026-06-05T00:00:00Z",
            "pending_hours_remaining_min": 1.0,
            "resolution_due_count": 0,
            "reconciliation_due": False,
            "summary": {
                "worker_poll_events": 1,
                "resolved_outcomes": 0,
                "pending_outcomes": 1,
                "awaiting_label_replay": 0,
                "parity_blocked_events": 0,
                "live_order_submitted": False,
            },
            "rehearsal_proof": {
                "status": "pending_observation_window",
                "can_poll_workers": False,
                "poll_blocked_by_pending_outcome": True,
                "next_reconcile_at": "2026-06-05T00:00:00Z",
                "pending_hours_remaining_min": 1.0,
                "resolution_due_count": 0,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "live_order_submitted": False,
            },
            "quick_read": {
                "status": "recording_pending_outcomes",
                "rehearsal_status": "pending_observation_window",
                "worker_poll_events": 1,
                "pending_outcomes": 0,
                "resolved_outcomes": 0,
                "awaiting_label_replay": 0,
                "parity_blocked_events": 0,
                "can_poll_workers": False,
                "poll_blocked_by_pending_outcome": True,
                "next_reconcile_at": "2026-06-05T00:00:00Z",
                "pending_hours_remaining_min": 1.0,
                "resolution_due_count": 0,
                "reconciliation_due": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "live_order_submitted": False,
            },
        }
    }

    def fake_load_json_artifact(rel_path: str):
        return artifacts[rel_path], None

    monkeypatch.setattr(
        pm_heartbeat_check,
        "_load_json_artifact",
        fake_load_json_artifact,
    )

    result = pm_heartbeat_check._check_paper_shadow_rehearsal_fail_closed_truth()[0]

    assert result.ok is False
    assert "quick_read.pending_outcomes" in result.detail
