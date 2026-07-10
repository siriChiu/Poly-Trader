#!/usr/bin/env python3
"""Validate the Poly-Trader heartbeat harness contract.

The checker intentionally uses only the Python standard library so heartbeat agents can
run it before installing the full ML stack.  It validates the repo-native maps, Q&A
gates, and cross-document references that make the heartbeat agent-readable.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "docs" / "ai-collaboration" / "harness" / "heartbeat-harness-contract.json"
QA_PATH = PROJECT_ROOT / "docs" / "ai-collaboration" / "harness" / "heartbeat-qa.md"

REQUIRED_GATE_IDS = [
    "HQ0_context_map",
    "HQ1_goal_and_boundary",
    "HQ2_current_truth",
    "HQ3_missing_capability",
    "HQ4_patch_contract",
    "HQ5_verification_loop",
    "HQ6_docs_sync",
    "HQ7_failure_escalation",
    "HQ9_anti_equilibrium_execution",
    "HQ8_user_report",
]

REQUIRED_DOC_REFERENCES = {
    "AGENTS.md": ["docs/ai-collaboration/HEARTBEAT.md", "docs/ai-collaboration/harness/README.md"],
    "docs/ai-collaboration/AI_AGENT_ROLE.md": ["docs/ai-collaboration/HEARTBEAT.md", "docs/ai-collaboration/harness/heartbeat-qa.md", "反平衡", "bounded live-canary"],
    "docs/ai-collaboration/HEARTBEAT.md": [
        "docs/ai-collaboration/harness/README.md",
        "docs/ai-collaboration/harness/heartbeat-qa.md",
        "PM heartbeat",
        "scripts/heartbeat_harness_check.py",
        "anti-equilibrium",
        "bounded live-canary",
        "observation-only",
    ],
    "ARCHITECTURE.md": ["docs/ai-collaboration/harness", "scripts/heartbeat_harness_check.py"],
    "README.md": ["docs/ai-collaboration/harness/README.md", "scripts/heartbeat_harness_check.py"],
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


def _load_contract() -> tuple[dict[str, Any] | None, list[CheckResult]]:
    if not CONTRACT_PATH.exists():
        return None, [
            CheckResult(
                "contract_exists",
                "Harness contract file exists?",
                False,
                str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
            )
        ]

    try:
        return json.loads(CONTRACT_PATH.read_text(encoding="utf-8")), [
            CheckResult(
                "contract_exists",
                "Harness contract file exists?",
                True,
                str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
            )
        ]
    except json.JSONDecodeError as exc:
        return None, [
            CheckResult(
                "contract_json_valid",
                "Harness contract JSON is parseable?",
                False,
                f"{exc.msg} at line {exc.lineno} column {exc.colno}",
            )
        ]


def _repo_path(path_value: str) -> Path:
    return PROJECT_ROOT / path_value


def _check_required_docs(contract: dict[str, Any]) -> list[CheckResult]:
    results: list[CheckResult] = []
    docs = contract.get("required_docs", [])
    if not isinstance(docs, list) or not docs:
        return [
            CheckResult(
                "required_docs_declared",
                "Contract declares required docs?",
                False,
                "required_docs missing or empty",
            )
        ]

    missing: list[str] = []
    for item in docs:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            missing.append("<invalid required_docs item>")
            continue
        rel = item["path"]
        if not _repo_path(rel).exists():
            missing.append(rel)

    results.append(
        CheckResult(
            "required_docs_exist",
            "All required harness docs exist?",
            not missing,
            "ok" if not missing else ", ".join(missing),
        )
    )
    return results


def _check_entrypoints(contract: dict[str, Any]) -> list[CheckResult]:
    entrypoints = contract.get("entrypoints", {})
    if not isinstance(entrypoints, dict) or not entrypoints:
        return [
            CheckResult(
                "entrypoints_declared",
                "Contract declares entrypoints?",
                False,
                "entrypoints missing or empty",
            )
        ]

    missing = [
        str(path)
        for path in entrypoints.values()
        if isinstance(path, str) and not _repo_path(path).exists()
    ]
    return [
        CheckResult(
            "entrypoints_exist",
            "All harness entrypoints exist?",
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
            "qa_gates_complete",
            "Contract and QA playbook include HQ0-HQ9?",
            not missing_contract and not missing_qa,
            "ok"
            if not missing_contract and not missing_qa
            else f"contract missing={missing_contract}; qa missing={missing_qa}",
        )
    ]


def _check_pm_handoff_contract(contract: dict[str, Any]) -> list[CheckResult]:
    qa_text = QA_PATH.read_text(encoding="utf-8") if QA_PATH.exists() else ""
    heartbeat_text = (PROJECT_ROOT / "docs/ai-collaboration/HEARTBEAT.md").read_text(encoding="utf-8")
    readme_text = (PROJECT_ROOT / "docs" / "ai-collaboration" / "harness" / "README.md").read_text(encoding="utf-8")
    signals = contract.get("agent_readable_signals", [])
    signal_names = {
        item.get("name")
        for item in signals
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    snippets = [
        ("docs/ai-collaboration/HEARTBEAT.md", heartbeat_text, "上一輪 PM heartbeat"),
        ("docs/ai-collaboration/harness/heartbeat-qa.md", qa_text, "上一輪 PM heartbeat"),
        ("docs/ai-collaboration/harness/README.md", readme_text, "PM handoff"),
    ]
    missing = [path for path, text, snippet in snippets if snippet not in text]
    if "previous_pm_heartbeat_handoff" not in signal_names:
        missing.append("contract signal previous_pm_heartbeat_handoff")
    return [
        CheckResult(
            "pm_handoff_required",
            "Engineering heartbeat requires previous PM heartbeat handoff?",
            not missing,
            "ok" if not missing else ", ".join(missing),
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
                f"{rel_path}:references",
                f"{rel_path} links to its harness dependencies?",
                not missing,
                "ok" if not missing else ", ".join(missing),
            )
        )
    return results


def run_checks() -> dict[str, Any]:
    contract, results = _load_contract()
    if contract is not None:
        results.extend(_check_required_docs(contract))
        results.extend(_check_entrypoints(contract))
        results.extend(_check_question_gates(contract))
        results.extend(_check_pm_handoff_contract(contract))
        results.extend(_check_doc_references())

    ok = all(result.ok for result in results)
    return {
        "ok": ok,
        "contract_path": str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
        "checks": [result.as_dict() for result in results],
    }


def _format_text(payload: dict[str, Any]) -> str:
    lines = ["Poly-Trader heartbeat harness check"]
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
