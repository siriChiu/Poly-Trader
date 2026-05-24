from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "docs" / "pm" / "pm-heartbeat-contract.json"
QA_PATH = PROJECT_ROOT / "docs" / "pm" / "pm-heartbeat-qa.md"
STATUS_PATH = PROJECT_ROOT / "docs" / "pm" / "pm-status.md"


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
    ]:
        rel_path = entrypoints[key]
        assert (PROJECT_ROOT / rel_path).exists(), rel_path

    gate_ids = {gate["id"] for gate in payload["question_gates"]}
    assert gate_ids == set(REQUIRED_GATE_IDS)
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
        "PM_HEARTBEAT.md:pm_references",
        "README.md:pm_references",
        "ARCHITECTURE.md:pm_references",
        "pm_status_current_state_fields",
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

    details = probe.get("deployment_blocker_details") or {}
    rows = _first_present(probe.get("current_live_structure_bucket_rows"), details.get("current_live_structure_bucket_rows"))
    minimum = _first_present(probe.get("minimum_support_rows"), details.get("minimum_support_rows"))
    gap = _first_present(probe.get("current_live_structure_bucket_gap_to_minimum"), details.get("current_live_structure_bucket_gap_to_minimum"))
    support_route = _first_present(probe.get("support_route_verdict"), details.get("support_route_verdict"))
    support_governance_route = _first_present(probe.get("support_governance_route"), details.get("support_governance_route"))
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
    assert str(breaker["verdict"]) in text
    assert f"release_ready={str(release['release_ready']).lower()}" in text
    assert f"{release['current_recent_window_wins']}/{release['recent_window']}" in text
    assert f"additional_recent_window_wins_needed={release['additional_recent_window_wins_needed']}" in text
    assert "Top-K" in text
    assert f"artifact_freshness_status={topk['artifact_freshness_status']}" in text
    assert f"samples={topk['samples']}" in text
    assert f"row_count={len(matrix_rows)}" in text
    assert f"runtime_blocked_candidate_rows={len(runtime_blocked_rows)}" in text
    assert f"runtime_ready={str(execution['runtime_ready']).lower()}" in text
    assert f"runtime_ready_count={execution['runtime_ready_count']}" in text
    assert f"venues_checked={execution['venues_checked']}" in text
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
