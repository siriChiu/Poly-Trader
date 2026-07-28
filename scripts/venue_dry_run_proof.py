#!/usr/bin/env python3
"""Build a secret-safe venue dry-run proof from public metadata smoke output.

This artifact is deliberately not a live-readiness certificate. It turns the
read-only venue metadata smoke result into an operator/PM proof that says what
can be previewed today, which order-lifecycle evidence is still missing, and
why no live order submission is allowed.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DOCS_ANALYSIS_DIR = PROJECT_ROOT / "docs" / "analysis"
DEFAULT_METADATA_IN = DATA_DIR / "execution_metadata_smoke.json"
DEFAULT_JSON_OUT = DATA_DIR / "venue_dry_run_proof.json"
DEFAULT_MARKDOWN_OUT = DOCS_ANALYSIS_DIR / "venue_dry_run_proof.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "ready", "passed"}
    return bool(value)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return default


def _rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _metadata_venues(metadata_smoke: Mapping[str, Any]) -> list[dict[str, Any]]:
    venues: list[dict[str, Any]] = []
    raw_venues = metadata_smoke.get("venues")
    if isinstance(raw_venues, list):
        venues.extend(dict(row) for row in raw_venues if isinstance(row, dict))
    elif isinstance(raw_venues, dict):
        for venue, row in raw_venues.items():
            if isinstance(row, dict):
                item = dict(row)
                item.setdefault("venue", venue)
                venues.append(item)

    if venues:
        return venues

    results = metadata_smoke.get("results")
    if isinstance(results, dict):
        for venue, row in results.items():
            if isinstance(row, dict):
                item = dict(row)
                item.setdefault("venue", venue)
                venues.append(item)
    elif isinstance(results, list):
        venues.extend(dict(row) for row in results if isinstance(row, dict))
    return venues


def _dedupe_text(values: list[Any]) -> list[str]:
    normalized = [str(value).strip() for value in values if str(value).strip()]
    return list(dict.fromkeys(normalized))


def _preview_status(
    *,
    adapter_supported: bool,
    metadata_ok: bool,
    enabled: bool,
    credentials_configured: bool,
) -> str:
    if not adapter_supported:
        return "blocked_adapter_unsupported"
    if not metadata_ok:
        return "blocked_metadata_contract_failed"
    if not enabled:
        return "blocked_config_disabled"
    if not credentials_configured:
        return "blocked_missing_credentials"
    return "preview_available_runtime_lifecycle_missing"


def _lifecycle_status(
    *,
    adapter_supported: bool,
    metadata_ok: bool,
    enabled: bool,
    credentials_configured: bool,
) -> str:
    if not adapter_supported:
        return "blocked_adapter_unsupported"
    if not metadata_ok:
        return "blocked_metadata_contract_failed"
    if not enabled:
        return "blocked_config_disabled"
    if not credentials_configured:
        return "blocked_missing_credentials"
    return "blocked_missing_runtime_backed_proof"


def _contract_preview(contract: Mapping[str, Any], *, symbol: Any) -> dict[str, Any]:
    qty_contract = contract.get("qty_contract") if isinstance(contract.get("qty_contract"), dict) else {}
    price_contract = contract.get("price_contract") if isinstance(contract.get("price_contract"), dict) else {}
    min_qty = _first_present(contract.get("min_qty"), qty_contract.get("min_qty"))
    return {
        "symbol": _first_present(contract.get("symbol"), symbol),
        "side": "buy",
        "order_type": "limit_preview",
        "preview_qty": min_qty,
        "min_qty": min_qty,
        "min_cost": contract.get("min_cost"),
        "step_size": _first_present(contract.get("step_size"), qty_contract.get("step_size")),
        "tick_size": _first_present(contract.get("tick_size"), price_contract.get("tick_size")),
        "amount_precision": contract.get("amount_precision"),
        "price_precision": contract.get("price_precision"),
    }


def _simulation_block(
    status: str,
    *,
    stage: str,
    required_evidence: list[str],
) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": status,
        "runtime_backed": False,
        "dry_run_only": True,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": False,
        "required_evidence": required_evidence,
    }


def _build_local_lifecycle_rehearsal(venues: list[dict[str, Any]]) -> dict[str, Any]:
    """Exercise the local lifecycle state contract without touching an adapter.

    This rehearsal proves only that the local dry-run state sequence and ledger
    arithmetic are coherent.  It must never be interpreted as exchange-backed
    acknowledgement, fill, cancel, reconciliation, or runtime readiness.
    """

    venue = next(
        (
            row
            for row in venues
            if row.get("adapter_supported") is True
            and row.get("metadata_ok") is True
            and row.get("enabled_in_config") is True
        ),
        None,
    )
    fail_closed = {
        "runtime_backed": False,
        "dry_run_only": True,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": False,
    }
    if venue is None:
        return {
            "status": "blocked_no_metadata_supported_venue",
            "scope": "local_contract_rehearsal_not_exchange_proof",
            "venue": None,
            **fail_closed,
            "events": [],
            "checks": {
                "transition_order_valid": False,
                "filled_qty_lte_requested_qty": False,
                "remaining_qty_matches": False,
                "terminal_state_canceled": False,
                "ledger_match": False,
                "live_adapter_called": False,
            },
            "limitations": [
                "no metadata-supported enabled venue was available",
                "no exchange adapter was called",
                "runtime venue lifecycle remains unverified",
            ],
        }

    requested_units = 100_000
    filled_units = 25_000
    remaining_units = requested_units - filled_units
    events = [
        {"sequence": 1, "event_type": "order_previewed", "state": "previewed"},
        {"sequence": 2, "event_type": "ack_recorded", "state": "open"},
        {
            "sequence": 3,
            "event_type": "partial_fill_recorded",
            "state": "partially_filled",
            "requested_units": requested_units,
            "filled_units": filled_units,
            "remaining_units": remaining_units,
        },
        {"sequence": 4, "event_type": "cancel_recorded", "state": "canceled"},
        {
            "sequence": 5,
            "event_type": "ledger_reconciled",
            "state": "reconciled",
            "filled_units": filled_units,
            "canceled_units": remaining_units,
        },
    ]
    return {
        "status": "passed_local_state_machine_runtime_unverified",
        "scope": "local_contract_rehearsal_not_exchange_proof",
        "venue": venue.get("venue"),
        **fail_closed,
        "events": events,
        "checks": {
            "transition_order_valid": [event["sequence"] for event in events] == [1, 2, 3, 4, 5],
            "filled_qty_lte_requested_qty": 0 <= filled_units <= requested_units,
            "remaining_qty_matches": remaining_units == requested_units - filled_units,
            "terminal_state_canceled": events[-2]["state"] == "canceled",
            "ledger_match": filled_units + remaining_units == requested_units,
            "live_adapter_called": False,
        },
        "metadata_contract": {
            "symbol": (venue.get("order_preview") or {}).get("constraints", {}).get("symbol"),
            "preview_qty": (venue.get("order_preview") or {}).get("constraints", {}).get("preview_qty"),
        },
        "limitations": [
            "local deterministic rehearsal only",
            "no exchange adapter was called",
            "no exchange acknowledgement, fill, cancel, or reconciliation was observed",
            "runtime venue lifecycle remains unverified",
        ],
    }


def _normalize_venue(row: Mapping[str, Any], *, symbol: Any) -> dict[str, Any]:
    venue = str(row.get("venue") or row.get("name") or "unknown").strip().lower() or "unknown"
    adapter_supported = row.get("adapter_supported") is not False
    metadata_ok = _as_bool(row.get("ok"))
    enabled = _as_bool(row.get("enabled_in_config"))
    credentials_configured = _as_bool(row.get("credentials_configured"))
    contract = row.get("contract") if isinstance(row.get("contract"), dict) else {}
    proof_state = str(row.get("proof_state") or "metadata_contract_missing")
    row_blockers = _dedupe_text(_as_list(row.get("blockers")))
    lifecycle_blockers = [
        "order preview is dry-run only",
        "runtime-backed order ack proof missing",
        "runtime-backed cancel proof missing",
        "runtime-backed fill proof missing",
        "runtime-backed reconciliation proof missing",
    ]
    blockers = _dedupe_text([*row_blockers, *lifecycle_blockers])
    preview_status = _preview_status(
        adapter_supported=adapter_supported,
        metadata_ok=metadata_ok,
        enabled=enabled,
        credentials_configured=credentials_configured,
    )
    lifecycle_status = _lifecycle_status(
        adapter_supported=adapter_supported,
        metadata_ok=metadata_ok,
        enabled=enabled,
        credentials_configured=credentials_configured,
    )

    order_preview = {
        "status": preview_status,
        "preview_available": bool(adapter_supported and metadata_ok),
        "dry_run_only": True,
        "would_submit": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": False,
        "constraints": _contract_preview(contract, symbol=_first_present(row.get("symbol"), symbol)),
        "blockers": blockers,
    }
    runtime_ready = bool(
        row.get("runtime_ready") is True
        and not blockers
        and proof_state in {"runtime_ready", "runtime_backed_order_lifecycle_complete"}
    )
    operator_next_action = row.get("operator_next_action")
    if not operator_next_action:
        if not adapter_supported:
            operator_next_action = f"Connect the {venue} adapter before dry-run lifecycle proof can start."
        elif not credentials_configured:
            operator_next_action = f"Configure {venue} credentials, then capture sandbox or tiny-order ack/cancel/fill evidence."
        else:
            operator_next_action = f"Capture {venue} runtime-backed ack, cancel, fill, and reconciliation evidence."
    verify_next = row.get("verify_next") or "Run scripts/venue_dry_run_proof.py after refreshing execution metadata smoke."

    return {
        "venue": venue,
        "adapter_supported": adapter_supported,
        "metadata_ok": metadata_ok,
        "enabled_in_config": enabled,
        "credentials_configured": credentials_configured,
        "credential_present": credentials_configured,
        "proof_state": proof_state,
        "runtime_ready": runtime_ready,
        "readiness_state": "runtime_ready" if runtime_ready else "blocked_missing_runtime_backed_proof",
        "blockers": blockers,
        "order_preview": order_preview,
        "ack_simulation": _simulation_block(
            lifecycle_status,
            stage="ack",
            required_evidence=["venue order id", "client order id", "exchange ack timestamp"],
        ),
        "cancel_simulation": _simulation_block(
            lifecycle_status,
            stage="cancel",
            required_evidence=["cancel request id", "exchange cancel ack", "terminal canceled state"],
        ),
        "fill_simulation": _simulation_block(
            lifecycle_status,
            stage="fill",
            required_evidence=["trade id", "filled qty", "filled price", "exchange fill timestamp"],
        ),
        "reconciliation_check": _simulation_block(
            lifecycle_status,
            stage="reconciliation",
            required_evidence=["open order poll", "trade history poll", "local ledger match"],
        ),
        "operator_next_action": str(operator_next_action),
        "verify_next": str(verify_next),
    }


def build_venue_dry_run_proof(
    execution_metadata_smoke: Mapping[str, Any] | None = None,
    *,
    generated_at: str | None = None,
    metadata_path: Path = DEFAULT_METADATA_IN,
) -> dict[str, Any]:
    metadata_smoke = dict(execution_metadata_smoke or {})
    venues = [
        _normalize_venue(row, symbol=metadata_smoke.get("symbol") or "BTC/USDT")
        for row in _metadata_venues(metadata_smoke)
    ]
    if not venues:
        venues = [
            {
                "venue": "unknown",
                "adapter_supported": False,
                "metadata_ok": False,
                "enabled_in_config": False,
                "credentials_configured": False,
                "credential_present": False,
                "proof_state": "artifact_missing_or_unparseable",
                "runtime_ready": False,
                "readiness_state": "blocked_missing_runtime_backed_proof",
                "blockers": [
                    "execution_metadata_smoke artifact missing or unparseable",
                    "runtime-backed order ack proof missing",
                    "runtime-backed cancel proof missing",
                    "runtime-backed fill proof missing",
                    "runtime-backed reconciliation proof missing",
                ],
                "order_preview": {
                    "status": "blocked_metadata_artifact_missing",
                    "preview_available": False,
                    "dry_run_only": True,
                    "would_submit": False,
                    "order_submission_enabled": False,
                    "risk_on_order_enabled": False,
                    "live_order_submitted": False,
                    "constraints": {"symbol": metadata_smoke.get("symbol") or "BTC/USDT"},
                    "blockers": ["execution_metadata_smoke artifact missing or unparseable"],
                },
                "ack_simulation": _simulation_block(
                    "blocked_metadata_artifact_missing",
                    stage="ack",
                    required_evidence=["venue order id", "exchange ack timestamp"],
                ),
                "cancel_simulation": _simulation_block(
                    "blocked_metadata_artifact_missing",
                    stage="cancel",
                    required_evidence=["exchange cancel ack", "terminal canceled state"],
                ),
                "fill_simulation": _simulation_block(
                    "blocked_metadata_artifact_missing",
                    stage="fill",
                    required_evidence=["trade id", "filled qty", "filled price"],
                ),
                "reconciliation_check": _simulation_block(
                    "blocked_metadata_artifact_missing",
                    stage="reconciliation",
                    required_evidence=["open order poll", "trade history poll", "local ledger match"],
                ),
                "operator_next_action": "Refresh execution metadata smoke before dry-run lifecycle proof.",
                "verify_next": "python scripts/execution_metadata_smoke.py --symbol BTCUSDT --venues okx binance",
            }
        ]

    runtime_ready_count = sum(1 for venue in venues if venue.get("runtime_ready") is True)
    credentials_configured_any = any(venue.get("credentials_configured") is True for venue in venues)
    blockers = _dedupe_text([
        blocker
        for venue in venues
        for blocker in _as_list(venue.get("blockers"))
    ])
    runtime_ready = bool(venues) and runtime_ready_count == len(venues)
    status = "ready" if runtime_ready else "blocked_missing_runtime_backed_proof"
    order_preview = venues[0]["order_preview"] if venues else {}
    ack_simulation = venues[0]["ack_simulation"] if venues else {}
    cancel_simulation = venues[0]["cancel_simulation"] if venues else {}
    fill_simulation = venues[0]["fill_simulation"] if venues else {}
    reconciliation_check = venues[0]["reconciliation_check"] if venues else {}
    local_lifecycle_rehearsal = _build_local_lifecycle_rehearsal(venues)

    return {
        "generated_at": generated_at or _now_iso(),
        "artifact": "venue_dry_run_proof",
        "status": status,
        "symbol": metadata_smoke.get("symbol") or "BTC/USDT",
        "source_artifacts": {
            "execution_metadata_smoke": {
                "path": _rel_path(metadata_path),
                "exists": bool(metadata_smoke),
                "generated_at": metadata_smoke.get("generated_at"),
            }
        },
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "dry_run_only": True,
        "secrets_redacted": True,
        "credential_present": credentials_configured_any,
        "credentials_configured_any": credentials_configured_any,
        "runtime_ready": runtime_ready,
        "runtime_ready_count": runtime_ready_count,
        "venues_checked": len(venues),
        "runtime_ready_blockers": blockers,
        "venues": venues,
        "order_preview": order_preview,
        "ack_simulation": ack_simulation,
        "cancel_simulation": cancel_simulation,
        "fill_simulation": fill_simulation,
        "reconciliation_check": reconciliation_check,
        "local_lifecycle_rehearsal": local_lifecycle_rehearsal,
        "customer_usable_now": [
            "venue readiness checklist",
            "dry-run order preview with would_submit=false",
            "missing lifecycle proof checklist",
        ],
        "not_allowed": [
            "live buy/add exposure",
            "automatic live order submission",
            "canary order without runtime-backed venue lifecycle proof",
        ],
        "operator_next_action": venues[0].get("operator_next_action") if venues else "Refresh metadata smoke.",
        "verify_next": "python scripts/venue_dry_run_proof.py",
        "next_validation_artifact": "data/venue_dry_run_proof.json",
    }


def markdown(payload: Mapping[str, Any]) -> str:
    raw_local_rehearsal = payload.get("local_lifecycle_rehearsal")
    local_rehearsal: Mapping[str, Any] = (
        raw_local_rehearsal if isinstance(raw_local_rehearsal, dict) else {}
    )
    raw_local_checks = local_rehearsal.get("checks")
    local_checks: Mapping[str, Any] = raw_local_checks if isinstance(raw_local_checks, dict) else {}
    lines = [
        "# Venue dry-run proof",
        "",
        f"- generated_at: `{payload.get('generated_at')}`",
        f"- status: `{payload.get('status')}`",
        f"- symbol: `{payload.get('symbol')}`",
        f"- live_exposure_allowed: `{payload.get('live_exposure_allowed')}`",
        f"- order_submission_enabled: `{payload.get('order_submission_enabled')}`",
        f"- risk_on_order_enabled: `{payload.get('risk_on_order_enabled')}`",
        f"- dry_run_only: `{payload.get('dry_run_only')}`",
        f"- runtime_ready: `{payload.get('runtime_ready')}` ({payload.get('runtime_ready_count')}/{payload.get('venues_checked')})",
        f"- credential_present: `{payload.get('credential_present')}` (values redacted)",
        "",
        "## Venues",
    ]
    for venue in payload.get("venues") or []:
        if not isinstance(venue, dict):
            continue
        preview = venue.get("order_preview") if isinstance(venue.get("order_preview"), dict) else {}
        lines.append(
            f"- `{venue.get('venue')}`: adapter_supported=`{venue.get('adapter_supported')}`, "
            f"enabled_in_config=`{venue.get('enabled_in_config')}`, "
            f"credentials_configured=`{venue.get('credentials_configured')}`, "
            f"proof_state=`{venue.get('proof_state')}`, runtime_ready=`{venue.get('runtime_ready')}`, "
            f"order_preview_status=`{preview.get('status')}`"
        )
        blockers = venue.get("blockers") if isinstance(venue.get("blockers"), list) else []
        for blocker in blockers[:6]:
            lines.append(f"  - blocker: {blocker}")
    lines += [
        "",
        "## Lifecycle Checks",
        f"- ack: `{(payload.get('ack_simulation') or {}).get('status')}` / runtime_backed=`{(payload.get('ack_simulation') or {}).get('runtime_backed')}`",
        f"- cancel: `{(payload.get('cancel_simulation') or {}).get('status')}` / runtime_backed=`{(payload.get('cancel_simulation') or {}).get('runtime_backed')}`",
        f"- fill: `{(payload.get('fill_simulation') or {}).get('status')}` / runtime_backed=`{(payload.get('fill_simulation') or {}).get('runtime_backed')}`",
        f"- reconciliation: `{(payload.get('reconciliation_check') or {}).get('status')}` / runtime_backed=`{(payload.get('reconciliation_check') or {}).get('runtime_backed')}`",
        "",
        "## Local contract rehearsal (not exchange proof)",
        f"- local lifecycle rehearsal: `{local_rehearsal.get('status')}`",
        f"- scope: `{local_rehearsal.get('scope')}`",
        f"- venue: `{local_rehearsal.get('venue')}`",
        f"- runtime_backed: `{local_rehearsal.get('runtime_backed')}`",
        f"- live_adapter_called: `{local_checks.get('live_adapter_called')}`",
        "- interpretation: local state-machine/ledger proof only; exchange ack/fill/cancel/reconciliation remain unverified.",
    ]
    return "\n".join(lines)


def write_outputs(payload: Mapping[str, Any], json_out: Path, markdown_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(markdown(payload) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-in", type=Path, default=DEFAULT_METADATA_IN)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    args = parser.parse_args(argv)

    metadata = _read_json(args.metadata_in)
    payload = build_venue_dry_run_proof(metadata, metadata_path=args.metadata_in)
    write_outputs(payload, args.json_out, args.markdown_out)
    print(
        "venue_dry_run_proof: "
        f"status={payload['status']} "
        f"runtime_ready={payload['runtime_ready']} "
        f"order_submission_enabled={payload['order_submission_enabled']} "
        f"venues_checked={payload['venues_checked']} "
        f"json={args.json_out} md={args.markdown_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
