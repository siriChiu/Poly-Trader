from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "venue_dry_run_api_consistency_probe.py"


def _proof(fill_status: str = "blocked_missing_credentials") -> dict:
    return {
        "artifact": "venue_dry_run_proof",
        "artifact_path": "data/venue_dry_run_proof.json",
        "generated_at": "2026-06-04T04:00:00Z",
        "status": "blocked_missing_runtime_backed_proof",
        "symbol": "BTC/USDT",
        "credential_present": False,
        "credentials_configured_any": False,
        "runtime_ready": False,
        "runtime_ready_count": 0,
        "venues_checked": 2,
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "dry_run_only": True,
        "secrets_redacted": True,
        "runtime_ready_blockers": ["runtime-backed fill proof missing"],
        "venues": [
            {
                "venue": "okx",
                "adapter_supported": True,
                "enabled_in_config": True,
                "credentials_configured": False,
                "credential_present": False,
                "proof_state": "public_metadata_only",
                "readiness_state": "blocked_missing_runtime_backed_proof",
                "runtime_ready": False,
                "order_preview": {"status": "blocked_missing_credentials", "order_submission_enabled": False},
                "ack_simulation": {"status": "blocked_missing_credentials", "runtime_backed": False},
                "cancel_simulation": {"status": "blocked_missing_credentials", "runtime_backed": False},
                "fill_simulation": {"status": fill_status, "runtime_backed": False},
                "reconciliation_check": {"status": "blocked_missing_credentials", "runtime_backed": False},
            }
        ],
        "order_preview": {
            "status": "blocked_missing_credentials",
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
        },
        "ack_simulation": {
            "status": "blocked_missing_credentials",
            "runtime_backed": False,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
        },
        "cancel_simulation": {
            "status": "blocked_missing_credentials",
            "runtime_backed": False,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
        },
        "fill_simulation": {
            "status": fill_status,
            "runtime_backed": False,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
        },
        "reconciliation_check": {
            "status": "blocked_missing_credentials",
            "runtime_backed": False,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
        },
        "local_lifecycle_rehearsal": {
            "status": "passed_local_state_machine_runtime_unverified",
            "scope": "local_contract_rehearsal_not_exchange_proof",
            "venue": "okx",
            "runtime_backed": False,
            "dry_run_only": True,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
            "events": [
                {"sequence": 1, "event_type": "order_previewed", "state": "previewed"},
                {"sequence": 2, "event_type": "ack_recorded", "state": "open"},
                {
                    "sequence": 3,
                    "event_type": "partial_fill_recorded",
                    "state": "partially_filled",
                    "requested_units": 100_000,
                    "filled_units": 25_000,
                    "remaining_units": 75_000,
                },
                {"sequence": 4, "event_type": "cancel_recorded", "state": "canceled"},
                {
                    "sequence": 5,
                    "event_type": "ledger_reconciled",
                    "state": "reconciled",
                    "filled_units": 25_000,
                    "canceled_units": 75_000,
                },
            ],
            "checks": {
                "transition_order_valid": True,
                "filled_qty_lte_requested_qty": True,
                "remaining_qty_matches": True,
                "terminal_state_canceled": True,
                "ledger_match": True,
                "live_adapter_called": False,
            },
        },
    }


def _status_payload(proof: dict) -> dict:
    return {
        "symbol": "BTCUSDT",
        "venue_dry_run_proof": proof,
        "execution": {"venue_dry_run_proof": proof},
        "execution_surface_contract": {"venue_dry_run_proof": proof},
    }


def _overview_payload(proof: dict) -> dict:
    return {
        "symbol": "BTCUSDT",
        "venue_dry_run_proof": proof,
        "execution_readiness": {"order_submission_enabled": False, "risk_on_order_enabled": False},
    }


def _artifact_payload(proof: dict) -> dict:
    artifact = dict(proof)
    artifact.pop("artifact_path", None)
    return artifact


def _run(args: list[str], *, input_payload: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=json.dumps(input_payload) if input_payload is not None else None,
        text=True,
        capture_output=True,
        cwd=PROJECT_ROOT,
    )


def test_probe_passes_when_status_overview_and_artifact_match(tmp_path: Path) -> None:
    proof = _proof()
    status_file = tmp_path / "status.json"
    overview_file = tmp_path / "overview.json"
    artifact_file = tmp_path / "venue_dry_run_proof.json"
    status_file.write_text(json.dumps(_status_payload(proof)), encoding="utf-8")
    overview_file.write_text(json.dumps(_overview_payload(proof)), encoding="utf-8")
    artifact_file.write_text(json.dumps(_artifact_payload(proof)), encoding="utf-8")

    result = _run(
        [
            "--status-file",
            str(status_file),
            "--overview-file",
            str(overview_file),
            "--artifact-file",
            str(artifact_file),
            "--strict",
        ]
    )

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is True
    assert summary["api_consistent"] is True
    assert summary["artifact_consistent"] is True
    assert summary["fail_closed"] is True
    assert summary["secret_safe"] is True
    assert summary["local_lifecycle_rehearsal_valid"] is True
    assert summary["artifact_generated_at"] == proof["generated_at"]
    assert len(summary["artifact_payload_sha256"]) == 64
    assert summary["lifecycle_statuses"]["fill_simulation"]["status"] == "blocked_missing_credentials"


def test_probe_fails_strict_when_overview_lifecycle_status_diverges() -> None:
    proof = _proof()
    overview_proof = _proof(fill_status="ready_unexpected")

    result = _run(
        ["--strict"],
        input_payload={
            "status": _status_payload(proof),
            "execution_overview": _overview_payload(overview_proof),
            "artifact": _artifact_payload(proof),
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["api_consistent"] is False
    assert any(
        item["field"] == "fill_simulation.status"
        for item in summary["status_overview_mismatches"]
    )


def test_probe_fails_strict_when_api_payload_contains_secret_like_key() -> None:
    proof = _proof()
    overview_proof = _proof()
    overview_proof["order_preview"] = dict(overview_proof["order_preview"], api_key="should_not_leak")

    result = _run(
        ["--strict"],
        input_payload={
            "status": _status_payload(proof),
            "execution_overview": _overview_payload(overview_proof),
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["secret_safe"] is False
    assert "overview.order_preview.api_key" in summary["secret_like_key_paths"]
    assert "should_not_leak" not in result.stdout


def test_probe_fails_strict_when_local_lifecycle_rehearsal_invariants_fail() -> None:
    proof = _proof()
    proof["local_lifecycle_rehearsal"]["checks"]["ledger_match"] = False

    result = _run(
        ["--strict"],
        input_payload={
            "status": _status_payload(proof),
            "execution_overview": _overview_payload(proof),
            "artifact": _artifact_payload(proof),
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["local_lifecycle_rehearsal_valid"] is False
    assert "ledger_match" in summary["local_lifecycle_rehearsal_failures"]


def test_probe_accepts_stdin_bundle_without_artifact_for_api_only_check() -> None:
    proof = _proof()

    result = _run(
        ["--strict", "--compact"],
        input_payload={
            "api_status": _status_payload(proof),
            "overview": _overview_payload(proof),
        },
    )

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads(result.stdout)
    assert summary["artifact_proof_present"] is False
    assert summary["artifact_generated_at"] is None
    assert summary["artifact_payload_sha256"] is None
    assert summary["artifact_consistent"] is True
    assert summary["api_consistent"] is True


def test_probe_independently_rejects_impossible_local_lifecycle_quantities() -> None:
    proof = _proof()
    partial_fill = proof["local_lifecycle_rehearsal"]["events"][2]
    partial_fill.update(
        {
            "requested_units": 100_000,
            "filled_units": 125_000,
            "remaining_units": -25_000,
        }
    )
    reconciliation = proof["local_lifecycle_rehearsal"]["events"][4]
    reconciliation.update({"filled_units": 125_000, "canceled_units": -25_000})

    result = _run(
        ["--strict"],
        input_payload={
            "status": _status_payload(proof),
            "execution_overview": _overview_payload(proof),
            "artifact": _artifact_payload(proof),
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["local_lifecycle_rehearsal_valid"] is False
    assert "filled_qty_lte_requested_qty_recomputed" in summary["local_lifecycle_rehearsal_failures"]
    assert "remaining_qty_matches_recomputed" in summary["local_lifecycle_rehearsal_failures"]


def test_probe_independently_rejects_missing_and_nonfinite_lifecycle_quantities() -> None:
    variants = []

    missing = _proof()
    missing["local_lifecycle_rehearsal"]["events"][4].pop("canceled_units")
    variants.append(missing)

    nonfinite = _proof()
    nonfinite["local_lifecycle_rehearsal"]["events"][2]["filled_units"] = float("nan")
    variants.append(nonfinite)

    for proof in variants:
        result = _run(
            ["--strict"],
            input_payload={
                "status": _status_payload(proof),
                "execution_overview": _overview_payload(proof),
                "artifact": _artifact_payload(proof),
            },
        )

        assert result.returncode == 1
        summary = json.loads(result.stdout)
        assert summary["strict_ok"] is False
        assert summary["local_lifecycle_rehearsal_valid"] is False
        assert "quantity_fields_missing_or_invalid" in summary["local_lifecycle_rehearsal_failures"]
