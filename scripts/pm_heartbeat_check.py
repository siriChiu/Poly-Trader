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
    "PMHQ9_alternative_solution_review",
    "PMHQ10_anti_equilibrium_review",
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
        "alternative-solution",
        "time-to-evidence",
        "anti-equilibrium",
        "customer-value delta",
        "cost-of-delay",
        "red-team PM",
    ],
    "docs/pm/README.md": ["customer-side advocate", "framework-capture", "alternative-solution", "time-to-evidence", "anti-equilibrium", "customer-value delta", "cost-of-delay", "red-team PM"],
    "docs/pm/pm-heartbeat-qa.md": ["PMHQ1_stakeholder_expectation", "PMHQ9_alternative_solution_review", "PMHQ10_anti_equilibrium_review", "framework-capture", "alternative-solution", "time-to-evidence", "anti-equilibrium", "customer-value delta", "cost-of-delay"],
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
            "PM contract and QA playbook include PMHQ0-PMHQ10?",
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
    ]
    artifact_errors: list[str] = []

    probe, error = _load_json_artifact("data/live_predict_probe.json")
    if error:
        artifact_errors.append(error)
    elif probe is not None:
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
            ]
            if snippet and snippet != "None"
        )
        rows = probe.get("current_live_structure_bucket_rows") or details.get(
            "current_live_structure_bucket_rows"
        )
        minimum = probe.get("minimum_support_rows") or details.get("minimum_support_rows")
        gap = probe.get("current_live_structure_bucket_gap_to_minimum") or details.get(
            "current_live_structure_bucket_gap_to_minimum"
        )
        if rows is not None and minimum is not None:
            required.append(f"{rows}/{minimum}")
        if gap is not None:
            required.append(f"gap={gap}")

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
                f"artifact_freshness_status={topk.get('artifact_freshness_status')}",
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

    return required, artifact_errors


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
