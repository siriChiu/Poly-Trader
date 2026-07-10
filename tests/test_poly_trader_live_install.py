from __future__ import annotations

import json
from pathlib import Path

from scripts import poly_trader_live_install as install


def test_live_runner_install_contract_is_dry_run_and_secret_safe(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        install,
        "_run_verify_command",
        lambda command: {
            "installed": False,
            "returncode": 4,
            "stdout": "",
            "stderr": "Unit not found",
            "checked_at": "2026-01-01T00:00:00Z",
        },
    )

    config_path = tmp_path / "config.yaml"
    contract = install.build_install_contract(
        config_path=config_path,
        service_name="poly-trader-live-test",
        dry_run=True,
        no_submit=True,
        shadow_candidate=True,
    )
    blob = json.dumps(contract, ensure_ascii=False, sort_keys=True)

    assert contract["preferred_host_lane"] == "systemd_user"
    assert contract["install_status"]["status"] == "install_ready"
    assert contract["dry_run"] is True
    assert contract["no_submit"] is True
    assert contract["shadow_candidate"] is True
    assert contract["shadow_evidence_mode"] is True
    assert "--dry-run" in contract["manual_run_command"]
    assert "--no-submit" in contract["manual_run_command"]
    assert "--shadow-candidate" in contract["manual_run_command"]
    assert "--dry-run" in contract["systemd_user"]["service_unit"]
    assert "--no-submit" in contract["systemd_user"]["service_unit"]
    assert "--shadow-candidate" in contract["systemd_user"]["service_unit"]
    assert str(config_path) in contract["manual_run_command"]
    assert contract["audit_outputs"]["decision_tables"] == ["live_runner_runs", "live_runner_decisions"]
    assert "api_key" not in blob.lower()
    assert "api_secret" not in blob.lower()
    assert "passphrase" not in blob.lower()
