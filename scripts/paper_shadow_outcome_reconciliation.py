#!/usr/bin/env python3
"""Refresh and validate the paper/shadow worker 24h outcome proof.

This CLI wraps the control-plane reconciliation builder so heartbeat and PM
checks can rerun the same operator proof without using API routes. It never
submits orders; strict mode only verifies the artifact remains fail-closed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.models import init_db
from execution.control_plane import (
    PAPER_SHADOW_OUTCOME_ARTIFACT_PATH,
    build_paper_shadow_outcome_reconciliation,
)

DEFAULT_DB_URL = f"sqlite:///{PROJECT_ROOT / 'poly_trader.db'}"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "ready", "passed"}
    return bool(value)


def _to_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _resolve_db_url(db_url: str) -> str:
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
        rel_path = db_url[len("sqlite:///") :]
        return f"sqlite:///{PROJECT_ROOT / rel_path}"
    return db_url


def _artifact_from_result(result: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(result.get("artifact"))


def _load_config_db_url(config_path: Path | None) -> str:
    path = config_path or (PROJECT_ROOT / "config.yaml")
    if not path.exists():
        return DEFAULT_DB_URL
    try:
        import yaml

        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return DEFAULT_DB_URL
    if not isinstance(payload, dict):
        return DEFAULT_DB_URL
    database = payload.get("database") if isinstance(payload.get("database"), dict) else {}
    raw_url = str(database.get("url") or DEFAULT_DB_URL).strip()
    return _resolve_db_url(raw_url or DEFAULT_DB_URL)


def strict_failures(artifact: Mapping[str, Any]) -> list[str]:
    summary = _mapping(artifact.get("summary"))
    proof = _mapping(artifact.get("rehearsal_proof"))
    quick_read = _mapping(artifact.get("quick_read"))
    entries = artifact.get("entries") if isinstance(artifact.get("entries"), list) else []
    failures: list[str] = []

    top_level_flags = {
        "artifact.order_submission_enabled": artifact.get("order_submission_enabled"),
        "artifact.risk_on_order_enabled": artifact.get("risk_on_order_enabled"),
        "artifact.live_order_submitted": artifact.get("live_order_submitted"),
        "summary.live_order_submitted": summary.get("live_order_submitted"),
        "rehearsal_proof.order_submission_enabled": proof.get("order_submission_enabled"),
        "rehearsal_proof.risk_on_order_enabled": proof.get("risk_on_order_enabled"),
        "rehearsal_proof.live_order_submitted": proof.get("live_order_submitted"),
    }
    if quick_read:
        top_level_flags.update(
            {
                "quick_read.order_submission_enabled": quick_read.get("order_submission_enabled"),
                "quick_read.risk_on_order_enabled": quick_read.get("risk_on_order_enabled"),
                "quick_read.live_order_submitted": quick_read.get("live_order_submitted"),
            }
        )
    for name, value in top_level_flags.items():
        if _as_bool(value):
            failures.append(f"{name}_true")

    pending = _to_int(summary.get("pending_outcomes"))
    resolved = _to_int(summary.get("resolved_outcomes"))
    awaiting_label = _to_int(summary.get("awaiting_label_replay"))
    proof_status = str(proof.get("status") or "")
    if pending > 0:
        if proof.get("poll_blocked_by_pending_outcome") is not True:
            failures.append("pending_outcome_poll_not_blocked")
        if proof.get("can_poll_workers") is not False:
            failures.append("pending_outcome_can_poll_workers_not_false")
        if not proof.get("next_reconcile_at"):
            failures.append("pending_outcome_next_reconcile_at_missing")
        if proof_status != "pending_observation_window":
            failures.append(f"pending_outcome_unexpected_proof_status_{proof_status or 'missing'}")
    if resolved > 0 and proof_status != "resolved_evidence_ready":
        failures.append(f"resolved_outcome_unexpected_proof_status_{proof_status or 'missing'}")
    if awaiting_label > 0 and proof_status != "label_replay_required":
        failures.append(f"awaiting_label_unexpected_proof_status_{proof_status or 'missing'}")

    if quick_read:
        expected_quick_values = {
            "status": artifact.get("status"),
            "rehearsal_status": proof.get("status"),
            "worker_poll_events": _to_int(summary.get("worker_poll_events")),
            "pending_outcomes": pending,
            "resolved_outcomes": resolved,
            "awaiting_label_replay": awaiting_label,
            "parity_blocked_events": _to_int(summary.get("parity_blocked_events")),
            "can_poll_workers": proof.get("can_poll_workers"),
            "poll_blocked_by_pending_outcome": proof.get("poll_blocked_by_pending_outcome"),
            "next_reconcile_at": proof.get("next_reconcile_at"),
            "pending_hours_remaining_min": proof.get("pending_hours_remaining_min"),
            "resolution_due_count": _to_int(proof.get("resolution_due_count")),
        }
        for key, expected in expected_quick_values.items():
            if quick_read.get(key) != expected:
                failures.append(f"quick_read.{key}_mismatch")
        if quick_read.get("reconciliation_due") is not (_to_int(proof.get("resolution_due_count")) > 0):
            failures.append("quick_read.reconciliation_due_mismatch")

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        for key in ("order_submission_enabled", "risk_on_order_enabled", "live_order_submitted"):
            if _as_bool(entry.get(key)):
                failures.append(f"entries[{index}].{key}_true")
        proposal = _mapping(entry.get("proposal"))
        if _as_bool(proposal.get("live_order_submitted")):
            failures.append(f"entries[{index}].proposal.live_order_submitted_true")

    return failures


def summarize_reconciliation_result(result: Mapping[str, Any]) -> dict[str, Any]:
    artifact = _artifact_from_result(result)
    summary = _mapping(artifact.get("summary"))
    proof = _mapping(artifact.get("rehearsal_proof"))
    failures = strict_failures(artifact)
    resolution_due_count = _to_int(proof.get("resolution_due_count"))
    return {
        "probe": "paper_shadow_outcome_reconciliation",
        "strict_ok": not failures,
        "artifact_path": result.get("artifact_path"),
        "persisted": bool(result.get("persisted")),
        "status": artifact.get("status"),
        "rehearsal_status": proof.get("status"),
        "worker_poll_events": _to_int(summary.get("worker_poll_events")),
        "pending_outcomes": _to_int(summary.get("pending_outcomes")),
        "resolved_outcomes": _to_int(summary.get("resolved_outcomes")),
        "awaiting_label_replay": _to_int(summary.get("awaiting_label_replay")),
        "parity_blocked_events": _to_int(summary.get("parity_blocked_events")),
        "can_poll_workers": proof.get("can_poll_workers"),
        "poll_blocked_by_pending_outcome": proof.get("poll_blocked_by_pending_outcome"),
        "next_reconcile_at": proof.get("next_reconcile_at"),
        "pending_hours_remaining_min": proof.get("pending_hours_remaining_min"),
        "resolution_due_count": resolution_due_count,
        "reconciliation_due": resolution_due_count > 0,
        "order_submission_enabled": artifact.get("order_submission_enabled"),
        "risk_on_order_enabled": artifact.get("risk_on_order_enabled"),
        "live_order_submitted": bool(summary.get("live_order_submitted") or proof.get("live_order_submitted")),
        "blockers": failures,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", help="SQLAlchemy DB URL. Defaults to config.yaml database.url.")
    parser.add_argument("--db-path", type=Path, help="SQLite DB path. Overrides --db-url.")
    parser.add_argument("--config", type=Path, help="Config file used to resolve the default DB URL.")
    parser.add_argument("--artifact-path", type=Path, default=PAPER_SHADOW_OUTCOME_ARTIFACT_PATH)
    parser.add_argument("--limit", type=int, default=100, help="Maximum worker events to reconcile.")
    parser.add_argument("--persist", action="store_true", help="Persist the refreshed artifact.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when fail-closed proof is violated.")
    parser.add_argument("--compact", action="store_true", help="Emit single-line JSON summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db_url = f"sqlite:///{args.db_path.resolve()}" if args.db_path else (args.db_url or _load_config_db_url(args.config))
    session = init_db(db_url)
    try:
        result = build_paper_shadow_outcome_reconciliation(
            session,
            persist=bool(args.persist),
            artifact_path=args.artifact_path,
            limit=args.limit,
        )
    finally:
        close = getattr(session, "close", None)
        if callable(close):
            close()

    summary = summarize_reconciliation_result(result)
    json.dump(
        summary,
        sys.stdout,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":") if args.compact else None,
        indent=None if args.compact else 2,
    )
    sys.stdout.write("\n")
    return 0 if summary["strict_ok"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
