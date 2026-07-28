from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "venue_lifecycle_hard_no_go.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("venue_lifecycle_hard_no_go_test_module", MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _governor() -> dict:
    return {
        "run_number": 27,
        "selected_forced_branch": "venue_lifecycle_proof",
        "truth": {
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "deployment_blocker": "exact_live_lane_toxic_sub_bucket_current_bucket",
            "support_current_rows": 58,
            "support_delta_vs_previous": 27,
            "signature_payload": {"minimum_rows": 50},
        },
    }


def _venue_proof() -> dict:
    return {
        "generated_at": "2026-07-21T09:00:00Z",
        "runtime_ready": False,
        "runtime_ready_count": 0,
        "venues_checked": 2,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_exposure_allowed": False,
        "venues": [
            {
                "venue": "okx",
                "adapter_supported": True,
                "enabled_in_config": True,
                "credentials_configured": False,
                "proof_state": "public_metadata_only",
                "runtime_ready": False,
                "ack_simulation": {"status": "blocked_missing_credentials"},
                "cancel_simulation": {"status": "blocked_missing_credentials"},
                "fill_simulation": {"status": "blocked_missing_credentials"},
                "reconciliation_check": {"status": "blocked_missing_credentials"},
            },
            {
                "venue": "binance",
                "adapter_supported": False,
                "enabled_in_config": False,
                "credentials_configured": False,
                "proof_state": "adapter_unsupported",
                "runtime_ready": False,
            },
        ],
        "local_lifecycle_rehearsal": {
            "status": "passed_local_state_machine_runtime_unverified",
            "scope": "local_contract_rehearsal_not_exchange_proof",
            "runtime_backed": False,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
            "checks": {"live_adapter_called": False},
        },
    }


def _verification(venue_proof: dict | None = None) -> dict:
    bound_proof = venue_proof or _venue_proof()
    canonical = json.dumps(
        bound_proof,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return {
        "strict_ok": True,
        "api_consistent": True,
        "artifact_consistent": True,
        "artifact_proof_present": True,
        "artifact_generated_at": bound_proof["generated_at"],
        "artifact_payload_sha256": hashlib.sha256(canonical).hexdigest(),
        "fail_closed": True,
        "secret_safe": True,
        "local_lifecycle_rehearsal_valid": True,
        "secret_like_key_paths": [],
    }


def test_build_receipt_names_one_secret_safe_okx_gate() -> None:
    module = _load_module()
    venue_proof = _venue_proof()

    receipt = module.build_receipt(
        _governor(),
        venue_proof,
        _verification(venue_proof),
        generated_at="2026-07-21T09:01:00Z",
    )

    assert receipt["receipt_valid"] is True
    assert receipt["heartbeat_governor_run"] == 27
    assert receipt["selected_forced_branch"] == "venue_lifecycle_proof"
    assert receipt["verdict"] == "hard_no_go_single_failed_gate"
    assert receipt["single_failed_gate"] == "okx_sandbox_credentials_and_runtime_binding_gate"
    assert receipt["current_evidence"]["okx_credentials_configured"] is False
    assert receipt["current_evidence"]["runtime_ready"] is False
    assert receipt["safety"]["credentials_exposed"] is False
    assert receipt["safety"]["live_adapter_called"] is False
    assert receipt["safety"]["live_order_submitted"] is False
    assert receipt["safety"]["order_submission_enabled"] is False
    assert receipt["safety"]["risk_on_order_enabled"] is False
    assert receipt["independent_verifier"]["bound_to_venue_proof"] is True
    assert receipt["next_validation_artifact"] == "data/okx_runtime_lifecycle_proof.json"
    assert "api_key" not in json.dumps(receipt).lower()
    assert "api_secret" not in json.dumps(receipt).lower()


def test_build_receipt_rejects_verifier_receipt_bound_to_an_older_venue_proof() -> None:
    module = _load_module()
    venue_proof = _venue_proof()
    stale_verification = _verification(venue_proof)
    stale_verification["artifact_generated_at"] = "2026-07-21T08:00:00Z"

    receipt = module.build_receipt(
        _governor(),
        venue_proof,
        stale_verification,
        generated_at="2026-07-21T09:01:00Z",
    )

    assert receipt["receipt_valid"] is False
    assert receipt["independent_verifier"]["bound_to_venue_proof"] is False


def test_strict_cli_rejects_a_self_consistent_but_unverified_receipt(tmp_path: Path) -> None:
    governor_path = tmp_path / "governor.json"
    venue_path = tmp_path / "venue.json"
    verification_path = tmp_path / "verification.json"
    output_path = tmp_path / "receipt.json"
    governor_path.write_text(json.dumps(_governor()), encoding="utf-8")
    venue_path.write_text(json.dumps(_venue_proof()), encoding="utf-8")
    verification = _verification(_venue_proof())
    verification["strict_ok"] = False
    verification_path.write_text(json.dumps(verification), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--governor",
            str(governor_path),
            "--venue-proof",
            str(venue_path),
            "--verification",
            str(verification_path),
            "--output",
            str(output_path),
            "--strict",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    receipt = json.loads(output_path.read_text(encoding="utf-8"))
    assert receipt["receipt_valid"] is False
    assert receipt["independent_verifier"]["strict_ok"] is False
    assert receipt["verdict"] == "hard_no_go_single_failed_gate"
