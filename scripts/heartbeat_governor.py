#!/usr/bin/env python3
"""External governor for the Poly-Trader self-improving heartbeat.

This script intentionally does not ask an LLM whether the heartbeat is healthy.
It derives a compact, persisted control brief from machine-readable artifacts so
scheduled agents receive an externally computed anti-self-certification signal.
The state file is generated runtime data and is ignored by git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = PROJECT_ROOT / "data" / "heartbeat_governor_state.json"
DEFAULT_BRIEF_PATH = PROJECT_ROOT / "data" / "heartbeat_governor_brief.json"
RUNTIME_PROBE_STALE_AFTER_MINUTES = 30.0
MAX_HISTORY = 12


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _first(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _age_minutes(value: Any, now: datetime) -> float | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max((now - parsed.astimezone(timezone.utc)).total_seconds() / 60.0, 0.0)


def _read_truth(root: Path, now: datetime) -> dict[str, Any]:
    live = _load_json(root / "data" / "live_predict_probe.json")
    live_details = _dict(live.get("deployment_blocker_details"))
    support = _dict(live.get("support_progress"))
    if not support:
        support = _dict(live_details.get("support_progress"))
    micro = _load_json(root / "data" / "microstructure_contract.json")
    micro_source = _dict(micro.get("source"))
    micro_freshness = _dict(micro.get("freshness"))
    venue = _load_json(root / "data" / "execution_metadata_smoke.json")
    paper = _load_json(root / "data" / "paper_shadow_outcome_reconciliation.json")
    topk = _load_json(root / "data" / "high_conviction_topk_oos_matrix.json")

    current_rows = _first(
        support.get("current_rows"),
        live.get("current_live_structure_bucket_rows"),
        live_details.get("current_live_structure_bucket_rows"),
    )
    previous_rows = _first(support.get("previous_rows"), live.get("previous_live_structure_bucket_rows"))
    delta = _first(
        support.get("delta_vs_previous"),
        live.get("current_live_structure_bucket_delta_vs_previous"),
    )
    try:
        if delta is None and current_rows is not None and previous_rows is not None:
            delta = int(current_rows) - int(previous_rows)
    except (TypeError, ValueError):
        delta = None

    bucket = _first(
        live.get("current_live_structure_bucket"),
        live_details.get("current_live_structure_bucket"),
        live.get("structure_bucket"),
    )
    blocker = _first(
        live.get("deployment_blocker"),
        live_details.get("deployment_blocker"),
        "unknown_current_live_blocker",
    )
    venue_ready = _first(venue.get("runtime_ready"), venue.get("ready"))
    paper_summary = _dict(paper.get("summary"))
    paper_rehearsal = _dict(paper.get("rehearsal_proof"))
    paper_pending = _first(
        paper.get("pending_count"),
        paper_summary.get("pending_count"),
        paper_rehearsal.get("pending_count"),
    )

    signature_payload = {
        "bucket": bucket,
        "blocker": blocker,
        "support_route": _first(live.get("support_route_verdict"), live_details.get("support_route_verdict")),
        "support_governance_route": _first(live.get("support_governance_route"), live_details.get("support_governance_route")),
        "current_rows": current_rows,
        "minimum_rows": _first(live.get("minimum_support_rows"), live_details.get("minimum_support_rows")),
        "runtime_closure_state": live.get("runtime_closure_state"),
        "micro_status": micro.get("status"),
        "micro_source_status": _first(micro_source.get("freshness_status"), micro_freshness.get("source_status")),
        "topk_deployable_rows": topk.get("deployable_rows"),
        "venue_runtime_ready": venue_ready,
        "paper_pending_count": paper_pending,
    }
    semantic_signature = hashlib.sha256(
        json.dumps(signature_payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()[:20]
    probe_age = _age_minutes(live.get("generated_at"), now)
    micro_age = _age_minutes(micro.get("generated_at"), now)
    return {
        "semantic_signature": semantic_signature,
        "signature_payload": signature_payload,
        "current_live_structure_bucket": bucket,
        "deployment_blocker": blocker,
        "support_current_rows": current_rows,
        "support_previous_rows": previous_rows,
        "support_delta_vs_previous": delta,
        "support_stagnant_run_count": _first(
            support.get("stagnant_run_count"),
            live.get("stagnant_run_count"),
        ),
        "microstructure_status": micro.get("status", "missing_artifact"),
        "microstructure_source_status": _first(micro_source.get("freshness_status"), micro_freshness.get("source_status"), "missing"),
        "microstructure_probe_age_minutes": micro_age,
        "live_probe_age_minutes": probe_age,
        "live_probe_runtime_fresh": probe_age is not None and probe_age <= RUNTIME_PROBE_STALE_AFTER_MINUTES,
        "venue_runtime_ready": venue_ready,
        "paper_pending_count": paper_pending,
        "topk_deployable_rows": topk.get("deployable_rows"),
        "signal": live.get("signal"),
        "should_trade": live.get("should_trade"),
    }


def _choose_branch(truth: dict[str, Any], *, stagnant: bool, repeat_count: int) -> tuple[str, str, list[str]]:
    micro_status = str(truth.get("microstructure_status") or "")
    micro_source = str(truth.get("microstructure_source_status") or "")
    venue_ready = truth.get("venue_runtime_ready") is True
    paper_pending = truth.get("paper_pending_count")
    try:
        paper_has_pending = int(paper_pending or 0) > 0
    except (TypeError, ValueError):
        paper_has_pending = False

    if micro_status in {"blocked_missing_source", "missing_artifact"} or micro_source in {"missing", "stale", "unavailable"}:
        return (
            "map_signal_redesign",
            "LOB/order-flow source or freshness is not proven; improve the signal/source contract before discussing edge or live readiness.",
            [
                "produce or validate one source-backed microstructure artifact",
                "record source, observed_at, freshness, coverage, and forecast lineage",
                "keep live_risk_on_allowed=false until the artifact is fresh and complete",
            ],
        )
    if venue_ready is not True:
        return (
            "venue_lifecycle_proof",
            "venue runtime lifecycle is not proven; advance dry-run/ack/cancel/fill/reconciliation evidence.",
            [
                "run or repair venue lifecycle proof",
                "keep credentials secret-safe and expose booleans only",
                "do not call live adapter or weaken permit/lease gates",
            ],
        )
    if paper_has_pending:
        return (
            "customer_safe_shadow_proof",
            "paper/shadow evidence is pending; resolve or falsify the safe lane instead of repeating status prose.",
            [
                "reconcile pending paper/shadow outcomes",
                "record pending ETA and duplicate-poll guard",
                "keep risk_on_order_enabled=false",
            ],
        )
    if stagnant or repeat_count >= 2:
        return (
            "hard_no_go",
            "the same machine-readable blocker repeated without a verified customer-value delta; name one failed gate and its next artifact.",
            [
                "write one single failed gate",
                "name the exact next artifact that can change it",
                "do not claim progress from timestamp-only or prose-only changes",
            ],
        )
    return (
        "diagnostic_patch",
        "first-pass diagnostic run: select one P0/P1 patch from current evidence.",
        [
            "make one small, reversible, testable change",
            "run a verification command that another agent can repeat",
            "declare the next gate and fallback",
        ],
    )


def evaluate(root: Path = PROJECT_ROOT, state_path: Path = DEFAULT_STATE_PATH, *, now: datetime | None = None) -> dict[str, Any]:
    checked_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    previous = _load_json(state_path)
    truth = _read_truth(root, checked_at)
    signature = truth["semantic_signature"]
    same_signature = signature == previous.get("last_semantic_signature")
    repeat_count = int(previous.get("repeat_count", 0) or 0) + 1 if same_signature else 0
    delta = truth.get("support_delta_vs_previous")
    support_stagnant = delta == 0
    stagnant = same_signature or support_stagnant
    branch, branch_reason, required_evidence = _choose_branch(
        truth,
        stagnant=stagnant,
        repeat_count=repeat_count,
    )
    run_number = int(previous.get("run_number", 0) or 0) + 1
    forced = stagnant or repeat_count >= 2 or branch != "diagnostic_patch"
    brief = {
        "schema_version": 1,
        "generated_at": checked_at.isoformat().replace("+00:00", "Z"),
        "run_number": run_number,
        "anti_self_certification": "active",
        "agent_may_not_self_certify": True,
        "same_semantic_signature": same_signature,
        "repeat_count": repeat_count,
        "support_stagnant": support_stagnant,
        "forced_execution_required": forced,
        "selected_forced_branch": branch,
        "branch_reason": branch_reason,
        "required_evidence": required_evidence,
        "truth": truth,
        "previous_run": {
            "generated_at": previous.get("generated_at"),
            "semantic_signature": previous.get("last_semantic_signature"),
            "selected_branch": previous.get("selected_branch"),
        },
        "hard_rules": [
            "Do not call a checker PASS a product-success claim.",
            "Do not report progress from docs-only or timestamp-only edits.",
            "Do not declare a blocker resolved without a new artifact and an independent verifier.",
            "If forced_execution_required is true, do not produce observation-only status refresh.",
            "Live buy/add remains fail-closed regardless of this heartbeat result.",
        ],
    }
    history_value = previous.get("history")
    history: list[dict[str, Any]] = list(history_value) if isinstance(history_value, list) else []
    history.append(
        {
            "generated_at": brief["generated_at"],
            "run_number": run_number,
            "semantic_signature": signature,
            "same_semantic_signature": same_signature,
            "repeat_count": repeat_count,
            "selected_branch": branch,
            "support_delta_vs_previous": delta,
        }
    )
    state = {
        "schema_version": 1,
        "generated_at": brief["generated_at"],
        "run_number": run_number,
        "last_semantic_signature": signature,
        "repeat_count": repeat_count,
        "selected_branch": branch,
        "history": history[-MAX_HISTORY:],
    }
    brief["state_path"] = str(state_path)
    return {"brief": brief, "state": state}


def _persist(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _text(brief: dict[str, Any]) -> str:
    truth = _dict(brief.get("truth"))
    lines = [
        "POLY-TRADER HEARTBEAT GOVERNOR — MACHINE BRIEF",
        f"run={brief.get('run_number')} generated_at={brief.get('generated_at')}",
        "ANTI_SELF_CERTIFICATION=ACTIVE; agent_may_not_self_certify=true",
        f"same_signature={brief.get('same_semantic_signature')} repeat_count={brief.get('repeat_count')} support_stagnant={brief.get('support_stagnant')}",
        f"forced_execution_required={brief.get('forced_execution_required')}",
        f"selected_forced_branch={brief.get('selected_forced_branch')}",
        f"branch_reason={brief.get('branch_reason')}",
        f"current_bucket={truth.get('current_live_structure_bucket')} blocker={truth.get('deployment_blocker')}",
        f"support={truth.get('support_current_rows')}/{truth.get('signature_payload', {}).get('minimum_rows')} delta={truth.get('support_delta_vs_previous')}",
        f"microstructure={truth.get('microstructure_status')} source={truth.get('microstructure_source_status')} live_probe_fresh={truth.get('live_probe_runtime_fresh')}",
        "REQUIRED_EVIDENCE:",
    ]
    lines.extend(f"- {item}" for item in brief.get("required_evidence", []))
    lines.append("HARD_RULES:")
    lines.extend(f"- {item}" for item in brief.get("hard_rules", []))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--brief-path", type=Path, default=DEFAULT_BRIEF_PATH)
    args = parser.parse_args(argv)
    result = evaluate(args.project_root, args.state_path)
    _persist(args.state_path, result["state"])
    _persist(args.brief_path, result["brief"])
    if args.format == "json":
        print(json.dumps(result["brief"], ensure_ascii=False, indent=2))
    else:
        print(_text(result["brief"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
