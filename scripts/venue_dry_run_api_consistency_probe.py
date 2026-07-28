#!/usr/bin/env python3
"""Verify venue dry-run proof consistency across API surfaces.

The probe compares `/api/status.venue_dry_run_proof`,
`/api/execution/overview.venue_dry_run_proof`, and optionally the standalone
`data/venue_dry_run_proof.json` artifact.  It is intentionally JSON-in/JSON-out
so heartbeat runs can use curl output, saved payloads, or test fixtures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


SCALAR_KEYS = (
    "artifact",
    "status",
    "generated_at",
    "symbol",
    "credential_present",
    "credentials_configured_any",
    "runtime_ready",
    "runtime_ready_count",
    "venues_checked",
    "live_exposure_allowed",
    "order_submission_enabled",
    "risk_on_order_enabled",
    "dry_run_only",
    "secrets_redacted",
)
LIFECYCLE_KEYS = (
    "order_preview",
    "ack_simulation",
    "cancel_simulation",
    "fill_simulation",
    "reconciliation_check",
    "local_lifecycle_rehearsal",
)
LIFECYCLE_FIELD_KEYS = (
    "status",
    "scope",
    "venue",
    "runtime_backed",
    "order_submission_enabled",
    "risk_on_order_enabled",
    "dry_run_only",
    "live_order_submitted",
    "events",
    "checks",
)
VENUE_KEYS = (
    "adapter_supported",
    "enabled_in_config",
    "credentials_configured",
    "credential_present",
    "proof_state",
    "readiness_state",
    "runtime_ready",
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
ALLOWED_SECRETISH_KEYS = {"secrets_redacted"}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected top-level JSON object in {path}")
    return payload


def _payload_sha256(payload: Mapping[str, Any]) -> str | None:
    try:
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(canonical).hexdigest()


def _load_stdin_bundle() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("expected JSON bundle on stdin or --status-file/--overview-file")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("expected top-level JSON object")
    status = _mapping(payload.get("status") or payload.get("api_status"))
    overview = _mapping(
        payload.get("execution_overview")
        or payload.get("overview")
        or payload.get("api_execution_overview")
    )
    artifact = _mapping(
        payload.get("artifact")
        or payload.get("venue_dry_run_artifact")
        or payload.get("venue_dry_run_proof_artifact")
    )
    if not status or not overview:
        raise SystemExit("stdin bundle must include status and execution_overview objects")
    return status, overview, artifact


def _status_proof(status_payload: Mapping[str, Any]) -> dict[str, Any]:
    execution = _mapping(status_payload.get("execution"))
    surface = _mapping(status_payload.get("execution_surface_contract"))
    for candidate in (
        status_payload.get("venue_dry_run_proof"),
        execution.get("venue_dry_run_proof"),
        surface.get("venue_dry_run_proof"),
    ):
        if isinstance(candidate, dict):
            return candidate
    return {}


def _overview_proof(overview_payload: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(overview_payload.get("venue_dry_run_proof"))


def _block_status(proof: Mapping[str, Any], block_key: str) -> Any:
    block = _mapping(proof.get(block_key))
    return block.get("status")


def _comparable_signature(proof: Mapping[str, Any]) -> dict[str, Any]:
    signature: dict[str, Any] = {}
    for key in SCALAR_KEYS:
        if key in proof:
            signature[key] = proof.get(key)
    for block_key in LIFECYCLE_KEYS:
        block = _mapping(proof.get(block_key))
        for field in LIFECYCLE_FIELD_KEYS:
            if field in block:
                signature[f"{block_key}.{field}"] = block.get(field)
    venues_by_name: dict[str, dict[str, Any]] = {}
    for row in _list(proof.get("venues")):
        if not isinstance(row, dict):
            continue
        venue = str(row.get("venue") or "").strip().lower()
        if not venue:
            continue
        venue_sig = {key: row.get(key) for key in VENUE_KEYS if key in row}
        for block_key in LIFECYCLE_KEYS:
            status = _block_status(row, block_key)
            if status is not None:
                venue_sig[f"{block_key}.status"] = status
        venues_by_name[venue] = venue_sig
    if venues_by_name:
        signature["venues"] = venues_by_name
    return signature


def _required_missing(proof: Mapping[str, Any]) -> list[str]:
    missing = [
        key
        for key in (
            "status",
            "runtime_ready",
            "order_submission_enabled",
            "risk_on_order_enabled",
            "dry_run_only",
            "secrets_redacted",
        )
        if key not in proof
    ]
    for block_key in LIFECYCLE_KEYS:
        if "status" not in _mapping(proof.get(block_key)):
            missing.append(f"{block_key}.status")
    return missing


def _compare_signatures(
    left_name: str,
    left: Mapping[str, Any],
    right_name: str,
    right: Mapping[str, Any],
) -> list[dict[str, Any]]:
    left_sig = _comparable_signature(left)
    right_sig = _comparable_signature(right)
    mismatches: list[dict[str, Any]] = []
    for key in sorted(set(left_sig) & set(right_sig)):
        if left_sig[key] != right_sig[key]:
            mismatches.append(
                {
                    "field": key,
                    left_name: left_sig[key],
                    right_name: right_sig[key],
                }
            )
    return mismatches


def _secret_like_key_paths(node: Any, path: tuple[str, ...] = ()) -> list[str]:
    paths: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            key_text = str(key)
            lowered = key_text.lower().replace("-", "_")
            if lowered not in ALLOWED_SECRETISH_KEYS and any(
                fragment in lowered for fragment in FORBIDDEN_KEY_FRAGMENTS
            ):
                paths.append(".".join((*path, key_text)))
                continue
            paths.extend(_secret_like_key_paths(value, (*path, key_text)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            paths.extend(_secret_like_key_paths(item, (*path, str(index))))
    return paths


def _is_false(value: Any) -> bool:
    return value is False


def _is_true(value: Any) -> bool:
    return value is True


def _fail_closed(proof: Mapping[str, Any]) -> bool:
    if proof.get("order_submission_enabled") is not False:
        return False
    if proof.get("risk_on_order_enabled") is not False:
        return False
    if proof.get("live_exposure_allowed") is True:
        return False
    for block_key in LIFECYCLE_KEYS:
        block = _mapping(proof.get(block_key))
        if block.get("order_submission_enabled") is True:
            return False
        if block.get("risk_on_order_enabled") is True:
            return False
        if block.get("live_order_submitted") is True:
            return False
    return True


def _local_lifecycle_rehearsal_failures(proof: Mapping[str, Any]) -> list[str]:
    rehearsal = _mapping(proof.get("local_lifecycle_rehearsal"))
    if not rehearsal:
        return ["local_lifecycle_rehearsal_missing"]

    failures: list[str] = []
    if rehearsal.get("status") != "passed_local_state_machine_runtime_unverified":
        failures.append("status")
    if rehearsal.get("scope") != "local_contract_rehearsal_not_exchange_proof":
        failures.append("scope")
    for field, expected in (
        ("runtime_backed", False),
        ("dry_run_only", True),
        ("order_submission_enabled", False),
        ("risk_on_order_enabled", False),
        ("live_order_submitted", False),
    ):
        if rehearsal.get(field) is not expected:
            failures.append(field)

    events = _list(rehearsal.get("events"))
    sequences = [event.get("sequence") for event in events if isinstance(event, dict)]
    event_types = [event.get("event_type") for event in events if isinstance(event, dict)]
    states = [event.get("state") for event in events if isinstance(event, dict)]
    if sequences != [1, 2, 3, 4, 5]:
        failures.append("event_sequence")
    if event_types != [
        "order_previewed",
        "ack_recorded",
        "partial_fill_recorded",
        "cancel_recorded",
        "ledger_reconciled",
    ]:
        failures.append("event_types")
    if states != ["previewed", "open", "partially_filled", "canceled", "reconciled"]:
        failures.append("event_states")

    # Recompute quantity invariants from the event payload.  The writer's
    # boolean ``checks`` are useful diagnostics, but trusting them alone would
    # let a tampered or divergent API payload self-certify impossible fills.
    partial_fill = _mapping(events[2]) if len(events) > 2 else {}
    reconciliation = _mapping(events[4]) if len(events) > 4 else {}

    def _finite_number(value: Any) -> float | None:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
        number = float(value)
        return number if math.isfinite(number) else None

    requested = _finite_number(partial_fill.get("requested_units"))
    filled = _finite_number(partial_fill.get("filled_units"))
    remaining = _finite_number(partial_fill.get("remaining_units"))
    reconciled_filled = _finite_number(reconciliation.get("filled_units"))
    canceled = _finite_number(reconciliation.get("canceled_units"))
    if any(value is None for value in (requested, filled, remaining, reconciled_filled, canceled)):
        failures.append("quantity_fields_missing_or_invalid")
    else:
        assert requested is not None
        assert filled is not None
        assert remaining is not None
        assert reconciled_filled is not None
        assert canceled is not None
        if not (requested > 0 and 0 <= filled <= requested):
            failures.append("filled_qty_lte_requested_qty_recomputed")
        if not (remaining >= 0 and remaining == requested - filled):
            failures.append("remaining_qty_matches_recomputed")
        if reconciled_filled != filled:
            failures.append("reconciled_filled_qty_matches_recomputed")
        if not (canceled >= 0 and canceled == remaining):
            failures.append("canceled_qty_matches_remaining_recomputed")
        if reconciled_filled + canceled != requested:
            failures.append("ledger_match_recomputed")

    checks = _mapping(rehearsal.get("checks"))
    for field in (
        "transition_order_valid",
        "filled_qty_lte_requested_qty",
        "remaining_qty_matches",
        "terminal_state_canceled",
        "ledger_match",
    ):
        if checks.get(field) is not True:
            failures.append(field)
    if checks.get("live_adapter_called") is not False:
        failures.append("live_adapter_called")
    return list(dict.fromkeys(failures))


def build_summary(
    status_payload: Mapping[str, Any],
    overview_payload: Mapping[str, Any],
    artifact_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    status_proof = _status_proof(status_payload)
    overview_proof = _overview_proof(overview_payload)
    artifact_proof = _mapping(artifact_payload)

    status_overview_mismatches = (
        _compare_signatures("status", status_proof, "overview", overview_proof)
        if status_proof and overview_proof
        else []
    )
    artifact_status_mismatches = (
        _compare_signatures("artifact", artifact_proof, "status", status_proof)
        if artifact_proof and status_proof
        else []
    )
    artifact_overview_mismatches = (
        _compare_signatures("artifact", artifact_proof, "overview", overview_proof)
        if artifact_proof and overview_proof
        else []
    )
    secret_like_key_paths = [
        f"status.{path}" for path in _secret_like_key_paths(status_proof)
    ] + [
        f"overview.{path}" for path in _secret_like_key_paths(overview_proof)
    ]
    lifecycle_statuses = {
        key: {
            "status": _block_status(status_proof, key),
            "overview": _block_status(overview_proof, key),
            "artifact": _block_status(artifact_proof, key) if artifact_proof else None,
        }
        for key in LIFECYCLE_KEYS
    }
    api_consistent = bool(status_proof and overview_proof and not status_overview_mismatches)
    artifact_consistent = (
        True
        if not artifact_proof
        else bool(
            status_proof
            and overview_proof
            and not artifact_status_mismatches
            and not artifact_overview_mismatches
        )
    )
    status_fail_closed = bool(status_proof and _fail_closed(status_proof))
    overview_fail_closed = bool(overview_proof and _fail_closed(overview_proof))
    local_lifecycle_rehearsal_failures = list(
        dict.fromkeys(
            [
                *(_local_lifecycle_rehearsal_failures(status_proof) if status_proof else ["status_proof_missing"]),
                *(_local_lifecycle_rehearsal_failures(overview_proof) if overview_proof else ["overview_proof_missing"]),
                *(_local_lifecycle_rehearsal_failures(artifact_proof) if artifact_proof else []),
            ]
        )
    )
    local_lifecycle_rehearsal_valid = not local_lifecycle_rehearsal_failures
    status_missing = _required_missing(status_proof) if status_proof else ["venue_dry_run_proof"]
    overview_missing = _required_missing(overview_proof) if overview_proof else ["venue_dry_run_proof"]
    secret_safe = bool(
        status_proof
        and overview_proof
        and _is_true(status_proof.get("secrets_redacted"))
        and _is_true(overview_proof.get("secrets_redacted"))
        and not secret_like_key_paths
    )
    fail_closed = status_fail_closed and overview_fail_closed
    strict_ok = bool(
        api_consistent
        and artifact_consistent
        and fail_closed
        and secret_safe
        and local_lifecycle_rehearsal_valid
        and not status_missing
        and not overview_missing
    )
    return {
        "probe": "venue_dry_run_api_consistency",
        "strict_ok": strict_ok,
        "api_consistent": api_consistent,
        "artifact_consistent": artifact_consistent,
        "status_proof_present": bool(status_proof),
        "overview_proof_present": bool(overview_proof),
        "artifact_proof_present": bool(artifact_proof),
        "artifact_generated_at": artifact_proof.get("generated_at") if artifact_proof else None,
        "artifact_payload_sha256": _payload_sha256(artifact_proof) if artifact_proof else None,
        "status_missing_required_fields": status_missing,
        "overview_missing_required_fields": overview_missing,
        "status_overview_mismatches": status_overview_mismatches,
        "artifact_status_mismatches": artifact_status_mismatches,
        "artifact_overview_mismatches": artifact_overview_mismatches,
        "status_fail_closed": status_fail_closed,
        "overview_fail_closed": overview_fail_closed,
        "fail_closed": fail_closed,
        "secret_safe": secret_safe,
        "secret_like_key_paths": secret_like_key_paths,
        "local_lifecycle_rehearsal_valid": local_lifecycle_rehearsal_valid,
        "local_lifecycle_rehearsal_failures": local_lifecycle_rehearsal_failures,
        "status": status_proof.get("status"),
        "overview_status": overview_proof.get("status"),
        "artifact_status": artifact_proof.get("status") if artifact_proof else None,
        "runtime_ready": status_proof.get("runtime_ready"),
        "runtime_ready_count": status_proof.get("runtime_ready_count"),
        "venues_checked": status_proof.get("venues_checked"),
        "order_submission_enabled": status_proof.get("order_submission_enabled"),
        "risk_on_order_enabled": status_proof.get("risk_on_order_enabled"),
        "dry_run_only": status_proof.get("dry_run_only"),
        "lifecycle_statuses": lifecycle_statuses,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status-file", type=Path, help="Saved /api/status JSON.")
    parser.add_argument(
        "--overview-file", type=Path, help="Saved /api/execution/overview JSON."
    )
    parser.add_argument(
        "--artifact-file",
        type=Path,
        help="Optional standalone venue_dry_run_proof JSON artifact.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when consistency, fail-closed, or secret-safety checks fail.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit single-line JSON instead of pretty-printed JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.status_file or args.overview_file:
        if not args.status_file or not args.overview_file:
            raise SystemExit("--status-file and --overview-file must be provided together")
        status_payload = _load_json(args.status_file)
        overview_payload = _load_json(args.overview_file)
        artifact_payload = _load_json(args.artifact_file) if args.artifact_file else {}
    else:
        status_payload, overview_payload, stdin_artifact = _load_stdin_bundle()
        artifact_payload = _load_json(args.artifact_file) if args.artifact_file else stdin_artifact

    summary = build_summary(status_payload, overview_payload, artifact_payload)
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
