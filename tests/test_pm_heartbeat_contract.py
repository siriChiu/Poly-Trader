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

    assert "YELLOW_shadow_or_paper_usable" in text
    assert "under_minimum_exact_live_structure_bucket" in text
    assert "7/50" in text
    assert "gap=43" in text
    assert "Strategy Lab" in text
    assert "Execution Console" in text
    assert "客戶成功" in text
    assert "framework-capture" in text
    assert "ORANGE_framework_capture_risk" in text
    assert "live buy/add" in text or "真實買入 / 加倉" in text
