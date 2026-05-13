from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "docs" / "harness" / "heartbeat-harness-contract.json"
QA_PATH = PROJECT_ROOT / "docs" / "harness" / "heartbeat-qa.md"

REQUIRED_GATE_IDS = [
    "HQ0_context_map",
    "HQ1_goal_and_boundary",
    "HQ2_current_truth",
    "HQ3_missing_capability",
    "HQ4_patch_contract",
    "HQ5_verification_loop",
    "HQ6_docs_sync",
    "HQ7_failure_escalation",
    "HQ8_user_report",
]


def test_heartbeat_harness_contract_is_machine_readable() -> None:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert payload["definition_reference"]["url"].endswith("/harness-engineering/")

    entrypoints = payload["entrypoints"]
    for key in [
        "agent_map",
        "heartbeat_charter",
        "harness_readme",
        "qa_playbook",
        "validator",
        "validator_test",
    ]:
        rel_path = entrypoints[key]
        assert (PROJECT_ROOT / rel_path).exists(), rel_path

    gate_ids = {gate["id"] for gate in payload["question_gates"]}
    assert gate_ids == set(REQUIRED_GATE_IDS)

    qa_text = QA_PATH.read_text(encoding="utf-8")
    for gate_id in REQUIRED_GATE_IDS:
        assert gate_id in qa_text


def test_heartbeat_harness_checker_passes() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/heartbeat_harness_check.py", "--format", "json"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    assert {check["id"] for check in payload["checks"]} >= {
        "contract_exists",
        "required_docs_exist",
        "entrypoints_exist",
        "qa_gates_complete",
        "AGENTS.md:references",
        "HEARTBEAT.md:references",
        "README.md:references",
    }


def test_harness_checker_text_mode_is_question_answer_style() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/heartbeat_harness_check.py", "--format", "text"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Q: Harness contract file exists?" in completed.stdout
    assert "A: PASS" in completed.stdout
    assert "RESULT: PASS" in completed.stdout
