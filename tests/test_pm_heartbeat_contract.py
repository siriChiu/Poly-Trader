from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "docs" / "pm" / "pm-heartbeat-contract.json"
QA_PATH = PROJECT_ROOT / "docs" / "pm" / "pm-heartbeat-qa.md"
STATUS_PATH = PROJECT_ROOT / "docs" / "pm" / "pm-status.md"

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
    rows = probe.get("current_live_structure_bucket_rows") or details.get("current_live_structure_bucket_rows")
    minimum = probe.get("minimum_support_rows") or details.get("minimum_support_rows")
    gap = probe.get("current_live_structure_bucket_gap_to_minimum") or details.get("current_live_structure_bucket_gap_to_minimum")
    support_route = probe.get("support_route_verdict") or details.get("support_route_verdict")
    support_governance_route = probe.get("support_governance_route") or details.get("support_governance_route")
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
    assert "live buy/add" in text or "真實買入 / 加倉" in text
