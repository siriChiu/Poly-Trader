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
    monkeypatch.setattr(api_module, "_ensure_execution_metadata_smoke_governance", lambda cfg, symbol: {"all_ok": True, "ok_count": 2, "venues_checked": 2, "venues": [{"venue": "binance", "ok": True}], "governance": {"status": "healthy"}})

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
    monkeypatch.setattr(api_module, "_ensure_execution_metadata_smoke_governance", lambda cfg, symbol: None)
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


def test_ensure_execution_metadata_smoke_governance_auto_refreshes_stale_artifact(tmp_path, monkeypatch):
    stale_path = tmp_path / "execution_metadata_smoke_stale.json"
    stale_path.write_text(json.dumps({
        "generated_at": (datetime.now(timezone.utc) - timedelta(minutes=91)).isoformat().replace("+00:00", "Z"),
        "symbol": "BTC/USDT",
        "all_ok": False,
        "ok_count": 0,
        "venues_checked": 1,
        "results": {},
    }), encoding="utf-8")
    monkeypatch.setattr(api_module, "_EXECUTION_METADATA_SMOKE_PATH", stale_path)
    monkeypatch.setattr(api_module, "run_metadata_smoke", lambda cfg, symbol: {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "symbol": symbol,
        "all_ok": True,
        "ok_count": 1,
        "venues_checked": 1,
        "results": {
            "binance": {"ok": True, "enabled_in_config": True, "credentials_configured": False, "contract": {"step_size": "0.001", "tick_size": "0.1"}},
        },
    })
    api_module._EXECUTION_METADATA_SMOKE_REFRESH_STATE.update({
        "attempted_at": None,
        "completed_at": None,
        "status": "idle",
        "reason": "not_attempted",
        "next_retry_at": None,
        "error": None,
    })

    summary = api_module._ensure_execution_metadata_smoke_governance({"trading": {"symbol": "BTCUSDT"}}, "BTCUSDT")

    assert summary is not None
    assert summary["freshness"]["status"] == "fresh"
    assert summary["governance"]["status"] == "healthy"
    assert summary["governance"]["auto_refresh"]["status"] == "succeeded"
    assert summary["governance"]["refresh_command"].endswith("python scripts/execution_metadata_smoke.py --symbol BTCUSDT")


def test_ensure_execution_metadata_smoke_governance_marks_unavailable_refresh_failures(tmp_path, monkeypatch):
    missing_path = tmp_path / "missing_execution_metadata_smoke.json"
    monkeypatch.setattr(api_module, "_EXECUTION_METADATA_SMOKE_PATH", missing_path)
    monkeypatch.setattr(api_module, "run_metadata_smoke", lambda cfg, symbol: (_ for _ in ()).throw(RuntimeError("smoke boom")))
    api_module._EXECUTION_METADATA_SMOKE_REFRESH_STATE.update({
        "attempted_at": None,
        "completed_at": None,
        "status": "idle",
        "reason": "not_attempted",
        "next_retry_at": None,
        "error": None,
    })

    summary = api_module._ensure_execution_metadata_smoke_governance({"trading": {"symbol": "BTCUSDT"}}, "BTCUSDT")

    assert summary is not None
    assert summary["freshness"]["status"] == "unavailable"
    assert summary["governance"]["status"] == "artifact_unavailable"
    assert summary["governance"]["auto_refresh"]["status"] == "failed"
    assert "smoke boom" in summary["governance"]["auto_refresh"]["error"]


def test_run_execution_metadata_smoke_background_governance_records_runtime_state(monkeypatch):
    monkeypatch.setattr(api_module, "_ensure_execution_metadata_smoke_governance", lambda cfg, symbol: {
        "freshness": {"status": "fresh"},
        "governance": {"status": "healthy"},
    })
    captured = {}
    monkeypatch.setattr(api_module, "set_runtime_status", lambda key, payload: captured.__setitem__(key, payload))
    api_module._EXECUTION_METADATA_SMOKE_BACKGROUND_STATE.update({
        "status": "idle",
        "reason": "not_started",
        "checked_at": None,
        "freshness_status": None,
        "governance_status": None,
        "error": None,
        "interval_seconds": 60.0,
    })

    summary = api_module.run_execution_metadata_smoke_background_governance(
        {"trading": {"symbol": "BTCUSDT"}},
        "BTCUSDT",
        reason="test_tick",
        interval_seconds=42.0,
    )

    assert summary is not None
    assert summary["freshness"]["status"] == "fresh"
    assert api_module._EXECUTION_METADATA_SMOKE_BACKGROUND_STATE["status"] == "healthy"
    assert api_module._EXECUTION_METADATA_SMOKE_BACKGROUND_STATE["governance_status"] == "healthy"
    assert api_module._EXECUTION_METADATA_SMOKE_BACKGROUND_STATE["interval_seconds"] == 42.0
    assert captured["execution_metadata_smoke_background"]["status"] == "healthy"


def test_execution_metadata_background_monitor_loop_runs_one_tick(monkeypatch):
    calls = []
    monkeypatch.setattr(
        server_main,
        "run_execution_metadata_smoke_background_governance",
        lambda cfg, symbol, reason, interval_seconds: calls.append({
            "cfg": cfg,
            "symbol": symbol,
            "reason": reason,
            "interval_seconds": interval_seconds,
        }),
    )

    stop_event = SimpleNamespace(is_set=lambda: False, wait=lambda timeout: False)
    server_main._execution_metadata_background_monitor_loop(
        stop_event,
        {"trading": {"symbol": "BTCUSDT"}},
        "BTCUSDT",
        interval_seconds=7.0,
        run_once=True,
    )

    assert calls == [{
        "cfg": {"trading": {"symbol": "BTCUSDT"}},
        "symbol": "BTCUSDT",
        "reason": "server_background_monitor",
        "interval_seconds": 7.0,
    }]


def test_load_execution_metadata_external_monitor_state_reports_freshness(tmp_path, monkeypatch):
    artifact = tmp_path / "execution_metadata_external_monitor.json"
    artifact.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "external_process",
        "status": "healthy",
        "reason": "external_cron_monitor",
        "freshness_status": "fresh",
        "governance_status": "healthy",
        "error": None,
        "interval_seconds": 300,
        "command": "source venv/bin/activate && python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT",
        "install_contract": {
            "preferred_host_lane": "user_crontab",
            "install_status": {
                "status": "installed",
                "installed": True,
                "active_lane": "user_crontab",
                "lanes": {
                    "user_crontab": {"installed": True, "stdout": "*/5 * * * * ... poly-trader-execution-metadata-external-monitor"},
                },
            },
            "user_crontab": {"schedule": "*/5 * * * *", "verify_command": "crontab -l | grep 'poly-trader-execution-metadata-external-monitor'"},
            "fallback": {"reason": "manual fallback", "command": "source venv/bin/activate && python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT"},
        },
    }), encoding="utf-8")
    monkeypatch.setattr(api_module, "_EXECUTION_METADATA_EXTERNAL_MONITOR_PATH", artifact)

    state = api_module._load_execution_metadata_external_monitor_state()

    assert state["available"] is True
    assert state["status"] == "healthy"
    assert state["freshness"]["status"] == "fresh"
    assert state["command"].endswith("python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT")
    assert state["install_contract"]["preferred_host_lane"] == "user_crontab"
    assert state["install_contract"]["install_status"]["status"] == "installed"
    assert state["install_contract"]["install_status"]["active_lane"] == "user_crontab"
    assert state["install_contract"]["user_crontab"]["schedule"] == "*/5 * * * *"



def test_build_execution_metadata_smoke_governance_includes_external_monitor(monkeypatch):
    monkeypatch.setattr(api_module, "_load_execution_metadata_external_monitor_state", lambda symbol="BTCUSDT": {
        "available": True,
        "status": "healthy",
        "reason": "external_cron_monitor",
        "checked_at": "2026-04-16T16:00:00Z",
        "freshness": {"status": "fresh"},
        "command": "source venv/bin/activate && python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT",
        "install_contract": {"preferred_host_lane": "user_crontab"},
    })
    monkeypatch.setattr(api_module, "_build_execution_metadata_smoke_refresh_state", lambda: {"status": "idle"})
    monkeypatch.setattr(api_module, "_build_execution_metadata_smoke_background_state", lambda: {"status": "healthy"})

    governance = api_module._build_execution_metadata_smoke_governance(
        {"freshness": {"status": "fresh"}},
        "BTCUSDT",
    )

    assert governance["status"] == "healthy"
    assert governance["external_monitor"]["status"] == "healthy"
    assert governance["external_monitor"]["freshness"]["status"] == "fresh"
    assert governance["external_monitor"]["install_contract"]["preferred_host_lane"] == "user_crontab"
