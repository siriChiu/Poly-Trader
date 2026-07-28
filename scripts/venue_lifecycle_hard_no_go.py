#!/usr/bin/env python3
"""Build a single-gate, secret-safe venue lifecycle hard-no-go receipt.

The receipt binds the final heartbeat governor brief to the independently
verified venue dry-run artifact. It never reads venue credentials or calls an
exchange adapter. A valid receipt proves only that the forced venue branch has
one explicit next gate while live buy/add remains fail-closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOVERNOR = PROJECT_ROOT / "data" / "heartbeat_governor_brief.json"
DEFAULT_VENUE_PROOF = PROJECT_ROOT / "data" / "venue_dry_run_proof.json"
DEFAULT_VERIFICATION = PROJECT_ROOT / "data" / "venue_dry_run_api_consistency_verification.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "venue_lifecycle_hard_no_go.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected top-level JSON object: {path}")
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


def _venue_row(venue_proof: Mapping[str, Any], venue_name: str) -> dict[str, Any]:
    for raw_row in venue_proof.get("venues") or []:
        row = _mapping(raw_row)
        if str(row.get("venue") or "").strip().lower() == venue_name:
            return row
    return {}


def _stage_status(venue: Mapping[str, Any], stage: str) -> Any:
    return _mapping(venue.get(stage)).get("status")


def _single_failed_gate(okx: Mapping[str, Any]) -> tuple[str | None, str]:
    if not okx or okx.get("adapter_supported") is not True:
        return (
            "okx_adapter_and_metadata_gate",
            "OKX adapter/metadata capability is unavailable, so no secret-safe sandbox lifecycle can start.",
        )
    if okx.get("enabled_in_config") is not True:
        return (
            "okx_config_enablement_gate",
            "OKX is not enabled in the execution configuration, so runtime lifecycle proof remains fail-closed.",
        )
    if okx.get("credentials_configured") is not True:
        return (
            "okx_sandbox_credentials_and_runtime_binding_gate",
            "OKX public metadata is reachable, but sandbox/runtime credentials are not configured, so no exchange-backed acknowledgement, partial fill, cancel, or reconciliation lifecycle can be observed safely.",
        )
    if okx.get("runtime_ready") is not True:
        return (
            "okx_runtime_lifecycle_evidence_gate",
            "OKX credentials are configured, but independently verified runtime acknowledgement, fill/no-fill, cancel, and ledger reconciliation evidence is incomplete.",
        )
    return None, "OKX venue runtime lifecycle is already ready; a venue hard-no-go receipt is not valid."


def build_receipt(
    governor: Mapping[str, Any],
    venue_proof: Mapping[str, Any],
    verification: Mapping[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    truth = _mapping(governor.get("truth"))
    signature = _mapping(truth.get("signature_payload"))
    okx = _venue_row(venue_proof, "okx")
    local_rehearsal = _mapping(venue_proof.get("local_lifecycle_rehearsal"))
    local_checks = _mapping(local_rehearsal.get("checks"))
    failed_gate, gate_reason = _single_failed_gate(okx)

    verifier_fields = {
        key: verification.get(key)
        for key in (
            "strict_ok",
            "api_consistent",
            "artifact_consistent",
            "artifact_proof_present",
            "fail_closed",
            "secret_safe",
            "local_lifecycle_rehearsal_valid",
        )
    }
    venue_proof_payload_sha256 = _payload_sha256(venue_proof)
    verification_bound_to_venue_proof = bool(
        venue_proof_payload_sha256 is not None
        and verification.get("artifact_proof_present") is True
        and verification.get("artifact_generated_at") == venue_proof.get("generated_at")
        and verification.get("artifact_payload_sha256") == venue_proof_payload_sha256
    )
    verifier_ok = bool(
        all(value is True for value in verifier_fields.values())
        and verification_bound_to_venue_proof
    )
    secret_like_key_paths = verification.get("secret_like_key_paths")
    if not isinstance(secret_like_key_paths, list):
        secret_like_key_paths = []

    safety = {
        "credentials_exposed": False,
        "live_adapter_called": local_checks.get("live_adapter_called") is True,
        "live_order_submitted": local_rehearsal.get("live_order_submitted") is True,
        "order_submission_enabled": venue_proof.get("order_submission_enabled") is True,
        "risk_on_order_enabled": venue_proof.get("risk_on_order_enabled") is True,
        "live_buy_add_allowed": False,
        "safe_fallbacks": ["paper_shadow", "wait_hold", "reduce_sell", "diagnostics"],
    }
    safety_ok = not any(
        safety[key]
        for key in (
            "credentials_exposed",
            "live_adapter_called",
            "live_order_submitted",
            "order_submission_enabled",
            "risk_on_order_enabled",
        )
    )
    branch_ok = governor.get("selected_forced_branch") == "venue_lifecycle_proof"
    receipt_valid = bool(branch_ok and failed_gate and verifier_ok and safety_ok)

    return {
        "generated_at": generated_at or _now_iso(),
        "artifact": "venue_lifecycle_hard_no_go",
        "receipt_valid": receipt_valid,
        "heartbeat_governor_run": governor.get("run_number"),
        "selected_forced_branch": governor.get("selected_forced_branch"),
        "governor_current_bucket": truth.get("current_live_structure_bucket"),
        "governor_current_blocker": truth.get("deployment_blocker"),
        "governor_support_rows": truth.get("support_current_rows"),
        "governor_minimum_support_rows": signature.get("minimum_rows"),
        "governor_support_delta": truth.get("support_delta_vs_previous"),
        "verdict": "hard_no_go_single_failed_gate",
        "single_failed_gate": failed_gate,
        "gate_reason": gate_reason,
        "current_evidence": {
            "venue_dry_run_proof_generated_at": venue_proof.get("generated_at"),
            "okx_adapter_supported": okx.get("adapter_supported") is True,
            "okx_enabled_in_config": okx.get("enabled_in_config") is True,
            "okx_credentials_configured": okx.get("credentials_configured") is True,
            "okx_proof_state": okx.get("proof_state"),
            "runtime_ready": venue_proof.get("runtime_ready") is True,
            "runtime_ready_count": venue_proof.get("runtime_ready_count"),
            "venues_checked": venue_proof.get("venues_checked"),
            "lifecycle_statuses": {
                "ack_simulation": _stage_status(okx, "ack_simulation"),
                "cancel_simulation": _stage_status(okx, "cancel_simulation"),
                "fill_simulation": _stage_status(okx, "fill_simulation"),
                "reconciliation_check": _stage_status(okx, "reconciliation_check"),
            },
            "local_rehearsal_status": local_rehearsal.get("status"),
            "local_rehearsal_scope": local_rehearsal.get("scope"),
        },
        "independent_verifier": {
            "artifact": "data/venue_dry_run_api_consistency_verification.json",
            **verifier_fields,
            "artifact_generated_at": verification.get("artifact_generated_at"),
            "artifact_payload_sha256": verification.get("artifact_payload_sha256"),
            "venue_proof_payload_sha256": venue_proof_payload_sha256,
            "bound_to_venue_proof": verification_bound_to_venue_proof,
            "secret_like_key_paths": secret_like_key_paths,
        },
        "safety": safety,
        "next_validation_artifact": "data/okx_runtime_lifecycle_proof.json",
        "success_condition": "Secret-safe sandbox/runtime-backed OKX proof records one bounded order lifecycle with acknowledgement, partial fill or explicit no-fill, cancel acknowledgement, and independently recomputed ledger reconciliation; all live buy/add gates remain separate and fail-closed.",
        "failure_fallback": "Keep paper/shadow, wait/hold, reduce/sell, and diagnostics available; do not relax support, venue, permit, lease, or bounded-canary gates.",
        "time_to_evidence": "within_week_or_unknown_without_credentials",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--governor", type=Path, default=DEFAULT_GOVERNOR)
    parser.add_argument("--venue-proof", type=Path, default=DEFAULT_VENUE_PROOF)
    parser.add_argument("--verification", type=Path, default=DEFAULT_VERIFICATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    receipt = build_receipt(
        _read_json(args.governor),
        _read_json(args.venue_proof),
        _read_json(args.verification),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact": receipt["artifact"],
                "receipt_valid": receipt["receipt_valid"],
                "heartbeat_governor_run": receipt["heartbeat_governor_run"],
                "single_failed_gate": receipt["single_failed_gate"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 1 if args.strict and not receipt["receipt_valid"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
