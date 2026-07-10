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
        [sys.executable, "scripts/pm_heartbeat_check.py", "--format", "json"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    assert {check["id"] for check in payload["checks"]} >= {
        "pm_contract_exists",
        "pm_required_docs_exist",
        "pm_entrypoints_exist",
        "pm_qa_gates_complete",
        "AGENTS.md:pm_references",
        "docs/ai-collaboration/PM_HEARTBEAT.md:pm_references",
        "README.md:pm_references",
        "ARCHITECTURE.md:pm_references",
        "pm_status_current_state_fields",
        "pm_customer_safe_alternative_current_truth",
        "pm_paper_shadow_rehearsal_fail_closed_truth",
    }


def test_pm_checker_text_mode_is_question_answer_style() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/pm_heartbeat_check.py", "--format", "text"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Q: PM contract file exists?" in completed.stdout
    assert "A: PASS" in completed.stdout
    assert "RESULT: PASS" in completed.stdout


def test_pm_status_preserves_current_delivery_truth() -> None:
    text = STATUS_PATH.read_text(encoding="utf-8")
    probe = json.loads((PROJECT_ROOT / "data/live_predict_probe.json").read_text(encoding="utf-8"))
    breaker = json.loads((PROJECT_ROOT / "data/circuit_breaker_audit.json").read_text(encoding="utf-8"))
    topk = json.loads((PROJECT_ROOT / "data/high_conviction_topk_oos_matrix.json").read_text(encoding="utf-8"))
    execution = json.loads((PROJECT_ROOT / "data/execution_metadata_smoke.json").read_text(encoding="utf-8"))
    venue_dry_run = json.loads((PROJECT_ROOT / "data/venue_dry_run_proof.json").read_text(encoding="utf-8"))
    q15_support = json.loads((PROJECT_ROOT / "data/q15_support_audit.json").read_text(encoding="utf-8"))
    paper_shadow = json.loads((PROJECT_ROOT / "data/paper_shadow_outcome_reconciliation.json").read_text(encoding="utf-8"))

    details = probe.get("deployment_blocker_details") or {}
    rows = _first_present(probe.get("current_live_structure_bucket_rows"), details.get("current_live_structure_bucket_rows"))
    minimum = _first_present(probe.get("minimum_support_rows"), details.get("minimum_support_rows"))
    gap = _first_present(probe.get("current_live_structure_bucket_gap_to_minimum"), details.get("current_live_structure_bucket_gap_to_minimum"))
    support_route = _first_present(probe.get("support_route_verdict"), details.get("support_route_verdict"))
    support_governance_route = _first_present(probe.get("support_governance_route"), details.get("support_governance_route"))
    progress = probe.get("support_progress") if isinstance(probe.get("support_progress"), dict) else {}
    details_progress = details.get("support_progress") if isinstance(details.get("support_progress"), dict) else {}
    if not progress:
        progress = details_progress
    semantic_progress = progress.get("semantic_signature_progress") if isinstance(progress.get("semantic_signature_progress"), dict) else {}
    semantic_delta = _first_present(progress.get("semantic_signature_delta_vs_previous"), semantic_progress.get("delta_vs_previous"))
    semantic_stagnant = _first_present(progress.get("semantic_signature_stagnant_run_count"), semantic_progress.get("stagnant_run_count"))
    semantic_stalled = _first_present(
        progress.get("semantic_signature_stalled_support_accumulation"),
        semantic_progress.get("stalled_support_accumulation"),
    )
    release = breaker["release_condition"]
    matrix_rows = topk.get("rows") if isinstance(topk.get("rows"), list) else []
    runtime_blocked_rows = [
        row
        for row in matrix_rows
        if row.get("deployment_candidate_tier") == "runtime_blocked_oos_pass"
    ]

    assert "YELLOW_shadow_or_paper_usable" in text
    assert str(probe["deployment_blocker"]) in text
    assert str(probe["allowed_layers_reason"]) in text
    assert str(probe["current_live_structure_bucket"]) in text
    assert str(support_route) in text
    assert str(support_governance_route) in text
    assert f"{rows}/{minimum}" in text
    assert f"gap={gap}" in text
    assert f"allowed_layers_raw={probe['allowed_layers_raw']}" in text
    assert f"allowed_layers={probe['allowed_layers']}" in text
    decision_quality_score = _num_text(probe.get("decision_quality_score"))
    if decision_quality_score is not None:
        assert f"decision_quality_score={decision_quality_score}" in text
    if progress.get("delta_vs_previous") is not None:
        assert f"delta_vs_previous={progress['delta_vs_previous']}" in text
    if progress.get("stagnant_run_count") is not None:
        assert f"stagnant_run_count={progress['stagnant_run_count']}" in text
    if semantic_delta is not None:
        assert f"semantic_signature_delta_vs_previous={semantic_delta}" in text
    if semantic_stagnant is not None:
        assert f"semantic_signature_stagnant_run_count={semantic_stagnant}" in text
    if isinstance(semantic_stalled, bool):
        assert f"semantic_signature_stalled_support_accumulation={str(semantic_stalled).lower()}" in text
    assert str(breaker["verdict"]) in text
    assert f"release_ready={str(release['release_ready']).lower()}" in text
    assert f"{release['current_recent_window_wins']}/{release['recent_window']}" in text
    assert f"additional_recent_window_wins_needed={release['additional_recent_window_wins_needed']}" in text
    assert "Top-K" in text
    assert f"artifact_freshness_status={_topk_freshness_status(topk['generated_at'])}" in text
    assert f"support_context_freshness_status={_topk_live_support_freshness_status(probe['generated_at'])}" in text
    assert f"samples={topk['samples']}" in text
    assert f"row_count={len(matrix_rows)}" in text
    assert f"runtime_blocked_candidate_rows={len(runtime_blocked_rows)}" in text
    assert f"runtime_ready={str(execution['runtime_ready']).lower()}" in text
    assert f"runtime_ready_count={execution['runtime_ready_count']}" in text
    assert f"venues_checked={execution['venues_checked']}" in text
    assert f"venue_dry_run_status={venue_dry_run['status']}" in text
    assert f"order_submission_enabled={str(venue_dry_run['order_submission_enabled']).lower()}" in text
    assert f"risk_on_order_enabled={str(venue_dry_run['risk_on_order_enabled']).lower()}" in text
    assert f"dry_run_only={str(venue_dry_run['dry_run_only']).lower()}" in text
    paper_shadow_summary = paper_shadow.get("summary") or {}
    paper_shadow_proof = paper_shadow.get("rehearsal_proof") or {}
    assert "Paper/shadow worker parity" in text
    assert f"status={paper_shadow['status']}" in text
    assert f"worker_poll_events={paper_shadow_summary['worker_poll_events']}" in text
    assert f"pending_outcomes={paper_shadow_summary['pending_outcomes']}" in text
    assert f"resolved_outcomes={paper_shadow_summary['resolved_outcomes']}" in text
    assert f"awaiting_label_replay={paper_shadow_summary['awaiting_label_replay']}" in text
    assert f"live_order_submitted={str(paper_shadow_summary['live_order_submitted']).lower()}" in text
    assert f"status={paper_shadow_proof['status']}" in text
    assert f"can_poll_workers={str(paper_shadow_proof['can_poll_workers']).lower()}" in text
    assert f"poll_blocked_by_pending_outcome={str(paper_shadow_proof['poll_blocked_by_pending_outcome']).lower()}" in text
    assert f"order_submission_enabled={str(paper_shadow_proof['order_submission_enabled']).lower()}" in text
    assert f"risk_on_order_enabled={str(paper_shadow_proof['risk_on_order_enabled']).lower()}" in text
    assert f"live_order_submitted={str(paper_shadow_proof['live_order_submitted']).lower()}" in text
    assert "current_pending_hours_remaining_hours=" in text
    assert f"artifact_pending_hours_remaining_hours={paper_shadow_proof['pending_hours_remaining_min']}" in text
    assert "pending_hours_remaining_min=" not in text
    q15_equilibrium = q15_support.get("equilibrium_deadlock") or {}
    q15_forced_artifact = q15_equilibrium.get("forced_research_action_artifact") or {}
    q15_forced_branch = (
        q15_support.get("forced_branch_decision")
        or (q15_support.get("active_repair_plan") or {}).get("forced_branch_decision")
        or {}
    )
    if q15_equilibrium.get("verdict"):
        assert f"equilibrium_deadlock={q15_equilibrium['verdict']}" in text
    if q15_equilibrium.get("confirmed") is not None:
        assert f"equilibrium_deadlock_confirmed={str(q15_equilibrium['confirmed']).lower()}" in text
    if q15_forced_artifact.get("required") is not None:
        assert f"forced_research_action_required={str(q15_forced_artifact['required']).lower()}" in text
    if q15_forced_branch.get("status"):
        assert f"forced_branch_status={q15_forced_branch['status']}" in text
    if q15_forced_branch.get("selected_branch"):
        assert f"selected_branch={q15_forced_branch['selected_branch']}" in text
    if q15_forced_branch.get("single_failed_gate"):
        assert f"single_failed_gate={q15_forced_branch['single_failed_gate']}" in text
    if q15_forced_branch.get("next_validation_artifact"):
        assert f"next_validation_artifact={q15_forced_branch['next_validation_artifact']}" in text
    assert "/api/status.execution_surface_contract.live_canary_policy_gate" in text
    assert "Dashboard / Execution Status / Strategy Lab status-only summaries" in text
    for rel_path in pm_heartbeat_check.PM_CURRENT_ARTIFACT_FRESHNESS_PATHS:
        assert f"{rel_path} freshness_status=fresh" in text
    assert "Strategy Lab" in text
    assert "Execution Console" in text
    assert "客戶成功" in text
    assert "framework-capture" in text
    assert "ORANGE_framework_capture_risk" in text
    assert "ORANGE_alternative_solution_required" in text
    assert "alternative-solution" in text
    assert "time-to-evidence" in text
    assert "anti-equilibrium" in text
    assert "customer-value delta" in text
    assert "anti-repeat" in text
    assert "cost-of-delay" in text
    assert "hypothesis inversion" in text
    assert "option portfolio" in text
    assert "red-team PM" in text
    assert "forced-execution" in text
    assert "bounded live-canary" in text
    assert "72h" in text
    assert "Venue lifecycle proof" in text
    assert "Model shadow to decision" in text
    assert "Strategy micro-canary" in text
    assert "live buy/add" in text or "真實買入 / 加倉" in text
    if probe.get("deployment_blocker") == "circuit_breaker_active" or breaker.get("verdict") == "canonical_breaker_active":
        assert "breaker_clear" not in text
        assert "breaker math can be clear" not in text
        assert "熔斷仍 active" in text
    if _support_ready(rows, minimum, gap, support_route):
        assert "尚未建立同一 support identity 的精準樣本" not in text
        assert "current exact support 已達" in text
        assert "單一 support/governance gate" in text
        if support_governance_route == "exact_live_bucket_supported":
            assert "只能當治理 / proxy reference" not in text
            assert "是 exact-support evidence" in text


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
