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


def test_venue_dry_run_proof_records_local_lifecycle_rehearsal_without_runtime_promotion():
    payload = proof.build_venue_dry_run_proof(
        {
            "symbol": "BTC/USDT",
            "venues": [
                {
                    "ok": True,
                    "venue": "okx",
                    "adapter_supported": True,
                    "enabled_in_config": True,
                    "credentials_configured": False,
                    "proof_state": "public_metadata_only",
                    "runtime_ready": False,
                    "contract": {"symbol": "BTC/USDT", "min_qty": 0.001},
                }
            ],
        },
        generated_at="2026-07-19T07:15:00Z",
    )

    rehearsal = payload["local_lifecycle_rehearsal"]
    assert rehearsal["status"] == "passed_local_state_machine_runtime_unverified"
    assert rehearsal["scope"] == "local_contract_rehearsal_not_exchange_proof"
    assert rehearsal["venue"] == "okx"
    assert rehearsal["runtime_backed"] is False
    assert rehearsal["dry_run_only"] is True
    assert rehearsal["order_submission_enabled"] is False
    assert rehearsal["risk_on_order_enabled"] is False
    assert rehearsal["live_order_submitted"] is False
    assert [event["state"] for event in rehearsal["events"]] == [
        "previewed",
        "open",
        "partially_filled",
        "canceled",
        "reconciled",
    ]
    assert rehearsal["checks"] == {
        "transition_order_valid": True,
        "filled_qty_lte_requested_qty": True,
        "remaining_qty_matches": True,
        "terminal_state_canceled": True,
        "ledger_match": True,
        "live_adapter_called": False,
    }
    assert payload["runtime_ready"] is False
    assert payload["order_submission_enabled"] is False
    rendered = proof.markdown(payload)
    assert "local lifecycle rehearsal" in rendered
    assert "passed_local_state_machine_runtime_unverified" in rendered
    assert "local_contract_rehearsal_not_exchange_proof" in rendered


def test_venue_dry_run_proof_is_fail_closed_when_metadata_artifact_missing():
    payload = proof.build_venue_dry_run_proof({}, generated_at="2026-06-04T04:00:00Z")

    assert payload["status"] == "blocked_missing_runtime_backed_proof"
    assert payload["runtime_ready"] is False
    assert payload["venues_checked"] == 1
    assert payload["venues"][0]["proof_state"] == "artifact_missing_or_unparseable"
    assert payload["order_preview"]["status"] == "blocked_metadata_artifact_missing"
    assert payload["ack_simulation"]["runtime_backed"] is False


def test_venue_dry_run_markdown_ends_with_one_newline(tmp_path):
    payload = proof.build_venue_dry_run_proof({}, generated_at="2026-06-04T04:00:00Z")
    json_out = tmp_path / "venue_dry_run_proof.json"
    markdown_out = tmp_path / "venue_dry_run_proof.md"

    proof.write_outputs(payload, json_out, markdown_out)

    markdown = markdown_out.read_text(encoding="utf-8")
    assert markdown.endswith("\n")
    assert not markdown.endswith("\n\n")
