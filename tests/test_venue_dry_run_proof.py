import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "venue_dry_run_proof.py"
spec = importlib.util.spec_from_file_location("venue_dry_run_proof_test_module", MODULE_PATH)
proof = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(proof)


def test_venue_dry_run_proof_keeps_metadata_only_okx_fail_closed():
    payload = proof.build_venue_dry_run_proof(
        {
            "generated_at": "2026-06-04T03:12:08Z",
            "symbol": "BTC/USDT",
            "venues_checked": 2,
            "venues": [
                {
                    "ok": True,
                    "venue": "okx",
                    "symbol": "BTC/USDT",
                    "adapter_supported": True,
                    "enabled_in_config": True,
                    "credentials_configured": False,
                    "proof_state": "public_metadata_only",
                    "runtime_ready": False,
                    "contract": {
                        "symbol": "BTC/USDT",
                        "min_qty": 0.001,
                        "min_cost": 10.0,
                        "step_size": "0.001",
                        "tick_size": "0.10",
                    },
                    "blockers": [
                        "live exchange credential 尚未驗證",
                        "order ack lifecycle 尚未驗證",
                        "fill lifecycle 尚未驗證",
                    ],
                },
                {
                    "ok": False,
                    "venue": "binance",
                    "adapter_supported": False,
                    "enabled_in_config": False,
                    "credentials_configured": False,
                    "proof_state": "adapter_unsupported",
                    "runtime_ready": False,
                    "blockers": ["場館 adapter 尚未接入"],
                },
            ],
        },
        generated_at="2026-06-04T04:00:00Z",
    )

    assert payload["artifact"] == "venue_dry_run_proof"
    assert payload["status"] == "blocked_missing_runtime_backed_proof"
    assert payload["live_exposure_allowed"] is False
    assert payload["order_submission_enabled"] is False
    assert payload["risk_on_order_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["credential_present"] is False
    assert payload["secrets_redacted"] is True

    okx = {venue["venue"]: venue for venue in payload["venues"]}["okx"]
    assert okx["metadata_ok"] is True
    assert okx["order_preview"]["status"] == "blocked_missing_credentials"
    assert okx["order_preview"]["preview_available"] is True
    assert okx["order_preview"]["would_submit"] is False
    assert okx["order_preview"]["constraints"]["preview_qty"] == 0.001
    assert okx["ack_simulation"]["runtime_backed"] is False
    assert okx["cancel_simulation"]["runtime_backed"] is False
    assert okx["fill_simulation"]["runtime_backed"] is False
    assert okx["reconciliation_check"]["runtime_backed"] is False

    binance = {venue["venue"]: venue for venue in payload["venues"]}["binance"]
    assert binance["adapter_supported"] is False
    assert binance["order_preview"]["status"] == "blocked_adapter_unsupported"
    assert "api_key" not in str(payload).lower()
    assert "password" not in str(payload).lower()
    assert "token" not in str(payload).lower()


def test_venue_dry_run_proof_is_fail_closed_when_metadata_artifact_missing():
    payload = proof.build_venue_dry_run_proof({}, generated_at="2026-06-04T04:00:00Z")

    assert payload["status"] == "blocked_missing_runtime_backed_proof"
    assert payload["runtime_ready"] is False
    assert payload["venues_checked"] == 1
    assert payload["venues"][0]["proof_state"] == "artifact_missing_or_unparseable"
    assert payload["order_preview"]["status"] == "blocked_metadata_artifact_missing"
    assert payload["ack_simulation"]["runtime_backed"] is False
