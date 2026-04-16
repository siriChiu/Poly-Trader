import json
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from server import main as server_main
from server.routes import api as api_module


class DummySession:
    def close(self):
        return None


def test_run_startup_raw_continuity_check_records_clean_status():
    app = SimpleNamespace(state=SimpleNamespace())
    with ExitStack() as stack:
        stack.enter_context(patch.object(server_main, "get_db", return_value=DummySession()))
        repair = stack.enter_context(
            patch.object(
                server_main,
                "repair_recent_raw_continuity",
                return_value={
                    "symbol": "BTCUSDT",
                    "inserted_total": 0,
                    "coarse_inserted": 0,
                    "fine_inserted": 0,
                    "bridge_inserted": 0,
                    "used_bridge": False,
                    "used_fine_grain": False,
                    "skipped_no_klines": False,
                },
            )
        )
        feature_repair = stack.enter_context(
            patch.object(
                server_main,
                "repair_recent_feature_continuity",
                return_value={
                    "symbol": "BTCUSDT",
                    "inserted_total": 0,
                    "missing_before": 0,
                    "remaining_missing": 0,
                    "gap_count_over_expected": 0,
                },
            )
        )

        status = server_main._run_startup_raw_continuity_check(app)

    repair.assert_called_once()
    feature_repair.assert_called_once()
    assert status["status"] == "clean"
    assert status["continuity_repair"]["inserted_total"] == 0
    assert app.state.raw_continuity_status["status"] == "clean"
    assert app.state.feature_continuity_status["status"] == "clean"


def test_run_startup_raw_continuity_check_records_repaired_status():
    app = SimpleNamespace(state=SimpleNamespace())
    with ExitStack() as stack:
        stack.enter_context(patch.object(server_main, "get_db", return_value=DummySession()))
        patcher = stack.enter_context(
            patch.object(
                server_main,
                "repair_recent_raw_continuity",
                return_value={
                    "symbol": "BTCUSDT",
                    "inserted_total": 3,
                    "coarse_inserted": 0,
                    "fine_inserted": 1,
                    "bridge_inserted": 2,
                    "used_bridge": True,
                    "used_fine_grain": True,
                    "skipped_no_klines": False,
                },
            )
        )
        feature_patcher = stack.enter_context(
            patch.object(
                server_main,
                "repair_recent_feature_continuity",
                return_value={
                    "symbol": "BTCUSDT",
                    "inserted_total": 4,
                    "missing_before": 4,
                    "remaining_missing": 0,
                    "gap_count_over_expected": 0,
                },
            )
        )

        status = server_main._run_startup_raw_continuity_check(app)

    patcher.assert_called_once()
    feature_patcher.assert_called_once()
    assert status["status"] == "repaired"
    assert status["continuity_repair"]["bridge_inserted"] == 2
    assert app.state.raw_continuity_status["status"] == "repaired"
    assert app.state.feature_continuity_status["status"] == "repaired"


def test_run_startup_raw_continuity_check_records_failure_status():
    app = SimpleNamespace(state=SimpleNamespace())
    with ExitStack() as stack:
        stack.enter_context(patch.object(server_main, "get_db", return_value=DummySession()))
        stack.enter_context(
            patch.object(server_main, "repair_recent_raw_continuity", side_effect=RuntimeError("boom"))
        )

        status = server_main._run_startup_raw_continuity_check(app)

    assert status["status"] == "error"
    assert "boom" in status["error"]
    assert app.state.raw_continuity_status["status"] == "error"


def test_api_status_includes_runtime_raw_and_feature_continuity(monkeypatch):
    monkeypatch.setattr(api_module, "get_runtime_status", lambda key, default=None: {
        "raw_continuity": {
            "status": "repaired",
            "continuity_repair": {"inserted_total": 2, "bridge_inserted": 1},
        },
        "feature_continuity": {
            "status": "clean",
            "continuity_repair": {"inserted_total": 0, "remaining_missing": 0},
        },
    }.get(key, default))
    monkeypatch.setattr(api_module, "is_automation_enabled", lambda: True)
    monkeypatch.setattr(api_module, "get_config", lambda: {"trading": {"dry_run": False, "symbol": "BTCUSDT", "venue": "binance"}, "execution": {"mode": "paper", "venue": "binance", "venues": {"binance": {"enabled": True}}}})
    monkeypatch.setattr(api_module, "_load_execution_metadata_smoke_summary", lambda: {"all_ok": True, "ok_count": 2, "venues_checked": 2, "venues": [{"venue": "binance", "ok": True}]})

    import asyncio
    payload = asyncio.run(api_module.api_status())

    assert payload["automation"] is True
    assert payload["raw_continuity"]["status"] == "repaired"
    assert payload["raw_continuity"]["continuity_repair"]["bridge_inserted"] == 1
    assert payload["feature_continuity"]["status"] == "clean"
    assert payload["feature_continuity"]["continuity_repair"]["remaining_missing"] == 0
    assert payload["execution"]["guardrails"]["consecutive_failures"] >= 0
    assert payload["execution_metadata_smoke"]["ok_count"] == 2


def test_api_status_passes_db_session_into_execution_service(monkeypatch):
    captured = {}
    db_session = object()

    class DummyExecutionService:
        def __init__(self, cfg, db_session=None):
            captured["cfg"] = cfg
            captured["db_session"] = db_session

        def execution_summary(self):
            return {"guardrails": {"daily_loss_ratio": 0.02, "consecutive_failures": 0}}

    class DummyAccountSyncService:
        def __init__(self, cfg):
            self.cfg = cfg

        def snapshot(self, symbol=None):
            return {"symbol": symbol, "health": {"connected": True}}

    monkeypatch.setattr(api_module, "ExecutionService", DummyExecutionService)
    monkeypatch.setattr(api_module, "AccountSyncService", DummyAccountSyncService)
    monkeypatch.setattr(api_module, "get_db", lambda: db_session)
    monkeypatch.setattr(api_module, "get_runtime_status", lambda key, default=None: default)
    monkeypatch.setattr(api_module, "_load_execution_metadata_smoke_summary", lambda: None)
    monkeypatch.setattr(api_module, "is_automation_enabled", lambda: False)
    monkeypatch.setattr(api_module, "get_config", lambda: {
        "trading": {"dry_run": False, "symbol": "BTCUSDT", "venue": "binance"},
        "execution": {"mode": "paper", "venue": "binance", "venues": {"binance": {"enabled": True}}},
    })

    import asyncio
    payload = asyncio.run(api_module.api_status())

    assert captured["db_session"] is db_session
    assert payload["execution"]["guardrails"]["daily_loss_ratio"] == 0.02


def test_load_execution_metadata_smoke_summary_reports_freshness(tmp_path, monkeypatch):
    fresh_path = tmp_path / "execution_metadata_smoke.json"
    fresh_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "symbol": "BTC/USDT",
        "all_ok": True,
        "ok_count": 2,
        "venues_checked": 2,
        "results": {
            "binance": {"ok": True, "enabled_in_config": True, "credentials_configured": False, "contract": {"step_size": "0.001", "tick_size": "0.1"}},
        },
    }), encoding="utf-8")
    monkeypatch.setattr(api_module, "_EXECUTION_METADATA_SMOKE_PATH", fresh_path)

    summary = api_module._load_execution_metadata_smoke_summary()

    assert summary is not None
    assert summary["freshness"]["status"] == "fresh"
    assert summary["freshness"]["age_minutes"] is not None
    assert summary["freshness"]["age_minutes"] >= 0
    assert summary["freshness"]["stale_after_minutes"] == api_module._EXECUTION_METADATA_SMOKE_STALE_AFTER_MINUTES


def test_load_execution_metadata_smoke_summary_marks_stale_and_invalid_timestamps(tmp_path, monkeypatch):
    stale_path = tmp_path / "execution_metadata_smoke_stale.json"
    stale_path.write_text(json.dumps({
        "generated_at": (datetime.now(timezone.utc) - timedelta(minutes=91)).isoformat().replace("+00:00", "Z"),
        "symbol": "BTC/USDT",
        "all_ok": True,
        "ok_count": 1,
        "venues_checked": 1,
        "results": {},
    }), encoding="utf-8")
    monkeypatch.setattr(api_module, "_EXECUTION_METADATA_SMOKE_PATH", stale_path)
    stale_summary = api_module._load_execution_metadata_smoke_summary()

    assert stale_summary is not None
    assert stale_summary["freshness"]["status"] == "stale"
    assert stale_summary["freshness"]["reason"] == "artifact_older_than_policy"

    invalid_path = tmp_path / "execution_metadata_smoke_invalid.json"
    invalid_path.write_text(json.dumps({
        "generated_at": "not-a-timestamp",
        "symbol": "BTC/USDT",
        "all_ok": False,
        "ok_count": 0,
        "venues_checked": 1,
        "results": {},
    }), encoding="utf-8")
    monkeypatch.setattr(api_module, "_EXECUTION_METADATA_SMOKE_PATH", invalid_path)
    invalid_summary = api_module._load_execution_metadata_smoke_summary()

    assert invalid_summary is not None
    assert invalid_summary["freshness"]["status"] == "unavailable"
    assert invalid_summary["freshness"]["reason"] == "invalid_generated_at"
