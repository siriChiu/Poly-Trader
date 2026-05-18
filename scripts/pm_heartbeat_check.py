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
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "docs" / "pm" / "pm-heartbeat-contract.json"
QA_PATH = PROJECT_ROOT / "docs" / "pm" / "pm-heartbeat-qa.md"

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

REQUIRED_DOC_REFERENCES = {
    "AGENTS.md": ["PM_HEARTBEAT.md", "docs/pm/README.md"],
    "PM_HEARTBEAT.md": [
        "docs/pm/README.md",
        "docs/pm/pm-heartbeat-qa.md",
        "docs/pm/pm-status.md",
        "scripts/pm_heartbeat_check.py",
        "customer-side advocate",
        "framework-capture",
    ],
    "docs/pm/README.md": ["customer-side advocate", "framework-capture"],
    "docs/pm/pm-heartbeat-qa.md": ["PMHQ1_stakeholder_expectation", "framework-capture"],
    "README.md": ["docs/pm/README.md", "scripts/pm_heartbeat_check.py"],
    "ARCHITECTURE.md": ["docs/pm", "PM_HEARTBEAT.md"],
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
            "PM contract and QA playbook include PMHQ0-PMHQ8?",
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


def _check_pm_status_current_state() -> list[CheckResult]:
    status_path = PROJECT_ROOT / "docs" / "pm" / "pm-status.md"
    if not status_path.exists():
        return [
            CheckResult(
                "pm_status_exists",
                "PM status doc exists?",
                False,
                "docs/pm/pm-status.md",
            )
        ]
    text = status_path.read_text(encoding="utf-8")
    required = [
        "YELLOW_shadow_or_paper_usable",
        "circuit_breaker_active",
        "release_ready=false",
        "9/50",
        "additional_recent_window_wins_needed=6",
        "exact_bucket_unsupported_block",
        "no_support_proxy",
        "0/50",
        "gap=50",
        "Strategy Lab",
        "Execution Console",
        "客戶成功",
        "framework-capture",
        "Next-hour gate",
    ]
    missing = [snippet for snippet in required if snippet not in text]
    return [
        CheckResult(
            "pm_status_current_state_fields",
            "PM status contains decision, blocker, usable lanes, and next gate?",
            not missing,
            "ok" if not missing else ", ".join(missing),
        )
    ]


def run_checks() -> dict[str, Any]:
    contract, results = _load_contract()
    if contract is not None:
        results.extend(_check_required_docs(contract))
        results.extend(_check_entrypoints(contract))
        results.extend(_check_question_gates(contract))
        results.extend(_check_doc_references())
        results.extend(_check_pm_status_current_state())

    ok = all(result.ok for result in results)
    return {
        "ok": ok,
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
    args = parser.parse_args(argv)

    payload = run_checks()
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_format_text(payload))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
