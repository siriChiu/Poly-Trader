#!/usr/bin/env python3
"""Verify paper/shadow outcome proof consistency between API and artifact.

The probe compares `/api/execution/overview.paper_shadow_outcome_reconciliation`
with `data/paper_shadow_outcome_reconciliation.json`. It is intentionally
JSON-in/JSON-out so heartbeat runs can use a live API URL, saved payloads, or
test fixtures.  Strict mode keeps the rehearsal lane fail-closed and verifies
schema-v2 quick-read fields mirror the nested proof.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


STABLE_KEYS = (
    "artifact_schema_version",
    "status",
    "rehearsal_status",
    "worker_poll_events",
    "pending_outcomes",
    "resolved_outcomes",
    "awaiting_label_replay",
    "parity_blocked_events",
    "can_poll_workers",
    "poll_blocked_by_pending_outcome",
    "next_reconcile_at",
    "resolution_due_count",
    "reconciliation_due",
    "order_submission_enabled",
    "risk_on_order_enabled",
    "live_order_submitted",
)
QUICK_READ_KEYS = (
    "status",
    "rehearsal_status",
    "worker_poll_events",
    "pending_outcomes",
    "resolved_outcomes",
    "awaiting_label_replay",
    "parity_blocked_events",
    "can_poll_workers",
    "poll_blocked_by_pending_outcome",
    "next_reconcile_at",
    "resolution_due_count",
    "reconciliation_due",
    "order_submission_enabled",
    "risk_on_order_enabled",
    "live_order_submitted",
)
FORBIDDEN_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "api_secret",
    "secret_token",
    "client_secret",
    "password",
    "passphrase",
    "private_key",
    "access_token",
    "refresh_token",
    "authorization",
    "bearer",
)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected top-level JSON object in {path}")
    return payload


def _fetch_json(url: str, *, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(f"failed to fetch JSON from {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"expected top-level JSON object from {url}")
    return payload


def _load_stdin_bundle() -> tuple[dict[str, Any], dict[str, Any]]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("expected JSON bundle on stdin, --overview-file, or --base-url")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("expected top-level JSON object")
    overview = _mapping(
        payload.get("execution_overview")
        or payload.get("overview")
        or payload.get("api_execution_overview")
    )
    artifact = _mapping(
        payload.get("artifact")
        or payload.get("paper_shadow_outcome_artifact")
        or payload.get("paper_shadow_outcome_reconciliation_artifact")
    )
    if not overview:
        raise SystemExit("stdin bundle must include execution_overview")
    return overview, artifact


def _overview_proof(overview_payload: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(overview_payload.get("paper_shadow_outcome_reconciliation"))


def _summary(proof: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(proof.get("summary"))


def _rehearsal_proof(proof: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(proof.get("rehearsal_proof"))


def _quick_read(proof: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(proof.get("quick_read"))


def _stable_signature(proof: Mapping[str, Any]) -> dict[str, Any]:
    summary = _summary(proof)
    rehearsal = _rehearsal_proof(proof)
    signature: dict[str, Any] = {}
    fallback_values = {
        "worker_poll_events": summary.get("worker_poll_events"),
        "pending_outcomes": summary.get("pending_outcomes"),
        "resolved_outcomes": summary.get("resolved_outcomes"),
        "awaiting_label_replay": summary.get("awaiting_label_replay"),
        "parity_blocked_events": summary.get("parity_blocked_events"),
        "can_poll_workers": rehearsal.get("can_poll_workers"),
        "poll_blocked_by_pending_outcome": rehearsal.get("poll_blocked_by_pending_outcome"),
        "next_reconcile_at": rehearsal.get("next_reconcile_at"),
        "resolution_due_count": rehearsal.get("resolution_due_count"),
        "reconciliation_due": _to_int(rehearsal.get("resolution_due_count")) > 0,
        "live_order_submitted": bool(summary.get("live_order_submitted") or rehearsal.get("live_order_submitted")),
        "rehearsal_status": rehearsal.get("status"),
    }
    for key in STABLE_KEYS:
        if key in proof:
            signature[key] = proof.get(key)
        elif key in fallback_values:
            signature[key] = fallback_values[key]
    return signature


def _compare_signatures(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[dict[str, Any]]:
    left_sig = _stable_signature(left)
    right_sig = _stable_signature(right)
    mismatches: list[dict[str, Any]] = []
    for key in sorted(set(left_sig) & set(right_sig)):
        if left_sig[key] != right_sig[key]:
            mismatches.append({"field": key, "overview": left_sig[key], "artifact": right_sig[key]})
    return mismatches


def _required_missing(proof: Mapping[str, Any]) -> list[str]:
    missing = [key for key in STABLE_KEYS if key not in _stable_signature(proof)]
    if not _summary(proof):
        missing.append("summary")
    if not _rehearsal_proof(proof):
        missing.append("rehearsal_proof")
    if not _quick_read(proof):
        missing.append("quick_read")
    return sorted(set(missing))


def _quick_read_mismatches(proof: Mapping[str, Any], source_name: str) -> list[dict[str, Any]]:
    quick = _quick_read(proof)
    if not quick:
        return [{"source": source_name, "field": "quick_read", "expected": "present", "actual": None}]
    signature = _stable_signature(proof)
    mismatches: list[dict[str, Any]] = []
    for key in QUICK_READ_KEYS:
        expected = signature.get(key)
        actual = quick.get(key)
        if expected != actual:
            mismatches.append({"source": source_name, "field": key, "expected": expected, "actual": actual})
    return mismatches


def _secret_like_key_paths(node: Any, path: tuple[str, ...] = ()) -> list[str]:
    paths: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            key_text = str(key)
            lowered = key_text.lower().replace("-", "_")
            if any(fragment in lowered for fragment in FORBIDDEN_KEY_FRAGMENTS):
                paths.append(".".join((*path, key_text)))
                continue
            paths.extend(_secret_like_key_paths(value, (*path, key_text)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            paths.extend(_secret_like_key_paths(item, (*path, str(index))))
    return paths


def _fail_closed(proof: Mapping[str, Any]) -> bool:
    if proof.get("order_submission_enabled") is not False:
        return False
    if proof.get("risk_on_order_enabled") is not False:
        return False
    if proof.get("live_order_submitted") is True:
        return False
    summary = _summary(proof)
    rehearsal = _rehearsal_proof(proof)
    quick = _quick_read(proof)
    for mapping in (summary, rehearsal, quick):
        if mapping.get("order_submission_enabled") is True:
            return False
        if mapping.get("risk_on_order_enabled") is True:
            return False
        if mapping.get("live_order_submitted") is True:
            return False
    for index, entry in enumerate(_list(proof.get("entries"))):
        if not isinstance(entry, dict):
            continue
        for key in ("order_submission_enabled", "risk_on_order_enabled", "live_order_submitted"):
            if entry.get(key) is True:
                return False
        proposal = _mapping(entry.get("proposal"))
        if proposal.get("live_order_submitted") is True:
            return False
    return True


def _pending_guard_ok(proof: Mapping[str, Any]) -> bool:
    signature = _stable_signature(proof)
    pending = _to_int(signature.get("pending_outcomes"))
    if pending <= 0:
        return True
    return bool(
        signature.get("rehearsal_status") == "pending_observation_window"
        and signature.get("can_poll_workers") is False
        and signature.get("poll_blocked_by_pending_outcome") is True
        and signature.get("next_reconcile_at")
    )


def build_summary(
    overview_payload: Mapping[str, Any],
    artifact_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    overview_proof = _overview_proof(overview_payload)
    artifact_proof = _mapping(artifact_payload)
    mismatches = (
        _compare_signatures(overview_proof, artifact_proof)
        if overview_proof and artifact_proof
        else []
    )
    overview_missing = _required_missing(overview_proof) if overview_proof else ["paper_shadow_outcome_reconciliation"]
    artifact_missing = _required_missing(artifact_proof) if artifact_proof else ["paper_shadow_outcome_reconciliation_artifact"]
    quick_read_mismatches = _quick_read_mismatches(overview_proof, "overview") + _quick_read_mismatches(
        artifact_proof,
        "artifact",
    )
    overview_fail_closed = bool(overview_proof and _fail_closed(overview_proof))
    artifact_fail_closed = bool(artifact_proof and _fail_closed(artifact_proof))
    overview_pending_guard_ok = bool(overview_proof and _pending_guard_ok(overview_proof))
    artifact_pending_guard_ok = bool(artifact_proof and _pending_guard_ok(artifact_proof))
    secret_like_key_paths = [
        f"overview.{path}" for path in _secret_like_key_paths(overview_proof)
    ] + [f"artifact.{path}" for path in _secret_like_key_paths(artifact_proof)]
    api_consistent = bool(overview_proof and artifact_proof and not mismatches)
    quick_read_consistent = not quick_read_mismatches
    fail_closed = overview_fail_closed and artifact_fail_closed
    pending_guard_ok = overview_pending_guard_ok and artifact_pending_guard_ok
    schema_version = _stable_signature(overview_proof).get("artifact_schema_version")
    artifact_schema_version = _stable_signature(artifact_proof).get("artifact_schema_version")
    schema_v2 = schema_version == 2 and artifact_schema_version == 2
    strict_ok = bool(
        api_consistent
        and quick_read_consistent
        and fail_closed
        and pending_guard_ok
        and schema_v2
        and not overview_missing
        and not artifact_missing
        and not secret_like_key_paths
    )
    overview_sig = _stable_signature(overview_proof)
    artifact_sig = _stable_signature(artifact_proof)
    return {
        "probe": "paper_shadow_outcome_api_consistency",
        "strict_ok": strict_ok,
        "api_consistent": api_consistent,
        "quick_read_consistent": quick_read_consistent,
        "schema_v2": schema_v2,
        "overview_proof_present": bool(overview_proof),
        "artifact_proof_present": bool(artifact_proof),
        "overview_missing_required_fields": overview_missing,
        "artifact_missing_required_fields": artifact_missing,
        "overview_artifact_mismatches": mismatches,
        "quick_read_mismatches": quick_read_mismatches,
        "overview_fail_closed": overview_fail_closed,
        "artifact_fail_closed": artifact_fail_closed,
        "fail_closed": fail_closed,
        "overview_pending_guard_ok": overview_pending_guard_ok,
        "artifact_pending_guard_ok": artifact_pending_guard_ok,
        "pending_guard_ok": pending_guard_ok,
        "secret_safe": not secret_like_key_paths,
        "secret_like_key_paths": secret_like_key_paths,
        "status": overview_sig.get("status"),
        "artifact_status": artifact_sig.get("status"),
        "rehearsal_status": overview_sig.get("rehearsal_status"),
        "pending_outcomes": overview_sig.get("pending_outcomes"),
        "resolved_outcomes": overview_sig.get("resolved_outcomes"),
        "next_reconcile_at": overview_sig.get("next_reconcile_at"),
        "reconciliation_due": overview_sig.get("reconciliation_due"),
        "order_submission_enabled": overview_sig.get("order_submission_enabled"),
        "risk_on_order_enabled": overview_sig.get("risk_on_order_enabled"),
        "live_order_submitted": overview_sig.get("live_order_submitted"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Fetch live /api/execution/overview from this base URL.")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout for --base-url.")
    parser.add_argument("--overview-file", type=Path, help="Saved /api/execution/overview JSON.")
    parser.add_argument(
        "--artifact-file",
        type=Path,
        help="Standalone data/paper_shadow_outcome_reconciliation.json artifact.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when consistency, quick-read, pending guard, fail-closed, or secret checks fail.",
    )
    parser.add_argument("--compact", action="store_true", help="Emit single-line JSON.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.base_url and args.overview_file:
        raise SystemExit("--base-url and --overview-file are mutually exclusive")
    if args.base_url:
        overview_payload = _fetch_json(f"{args.base_url.rstrip('/')}/api/execution/overview", timeout=args.timeout)
        artifact_payload = _load_json(args.artifact_file) if args.artifact_file else {}
    elif args.overview_file:
        overview_payload = _load_json(args.overview_file)
        artifact_payload = _load_json(args.artifact_file) if args.artifact_file else {}
    else:
        overview_payload, stdin_artifact = _load_stdin_bundle()
        artifact_payload = _load_json(args.artifact_file) if args.artifact_file else stdin_artifact

    summary = build_summary(overview_payload, artifact_payload)
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":") if args.compact else None,
            indent=None if args.compact else 2,
        )
    )
    return 1 if args.strict and not summary["strict_ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
