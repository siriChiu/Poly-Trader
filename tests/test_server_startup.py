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
    reconciliation_payload = {"status": "warning", "summary": "reconciliation evidence"}
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
    monkeypatch.setattr(api_module, "get_confidence_prediction", lambda: {
        "signal": "HOLD",
        "confidence": 0.346959,
        "entry_quality": 0.5501,
        "entry_quality_label": "C",
        "allowed_layers": 1,
        "allowed_layers_raw": 1,
        "allowed_layers_reason": "entry_quality_C_single_layer",
        "allowed_layers_raw_reason": "entry_quality_C_single_layer",
        "q15_exact_supported_component_patch_applied": True,
        "support_route_verdict": "exact_bucket_supported",
        "support_progress": {"current_rows": 77, "minimum_support_rows": 50},
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "current_live_structure_bucket_rows": 0,
                "alerts": ["no_rows"],
            }
        },
    })
    monkeypatch.setattr(api_module, "_build_execution_reconciliation_summary", lambda db, symbol, account_snapshot, execution_summary: reconciliation_payload)

    import asyncio
    payload = asyncio.run(api_module.api_status())

    assert payload["automation"] is True
    assert payload["raw_continuity"]["status"] == "repaired"
    assert payload["raw_continuity"]["continuity_repair"]["bridge_inserted"] == 1
    assert payload["feature_continuity"]["status"] == "clean"
    assert payload["feature_continuity"]["continuity_repair"]["remaining_missing"] == 0
    assert payload["execution"]["guardrails"]["consecutive_failures"] >= 0
    assert payload["execution_reconciliation"] == reconciliation_payload
    assert payload["execution_metadata_smoke"]["ok_count"] == 2
    assert payload["execution_surface_contract"]["canonical_execution_route"] == "dashboard"
    assert payload["execution_surface_contract"]["canonical_surface_label"] == "Dashboard / Execution 狀態面板"
    assert payload["execution_surface_contract"]["shortcut_surface"]["name"] == "signal_banner"
    assert payload["execution_surface_contract"]["shortcut_surface"]["role"] == "shortcut-only"
    assert payload["execution_surface_contract"]["shortcut_surface"]["status"] == "not-upgraded"
    assert payload["execution_surface_contract"]["shortcut_surface"]["message"] == "SignalBanner 目前只提供快捷下單 / 自動交易切換；完整 Execution 狀態、Guardrail context 與 stale governance 必須回 Dashboard 檢查。"
    assert payload["execution_surface_contract"]["shortcut_surface"]["upgrade_prerequisite"] == "必須先完整消費 /api/status 的 ticking_state、stale governance、guardrail context，才能升級第二 execution route。"
    assert payload["execution_surface_contract"]["readiness_scope"] == "runtime_governance_visibility_only"
    assert payload["execution_surface_contract"]["operator_message"].startswith("目前完成的是 execution governance / visibility closure，不是 live 或 canary readiness。")
    assert payload["execution"]["live_runtime_truth"]["runtime_closure_state"] == "capacity_opened_signal_hold"
    assert payload["execution_surface_contract"]["live_runtime_truth"]["runtime_closure_state"] == "capacity_opened_signal_hold"
    assert payload["execution"]["live_runtime_truth"]["support_alignment_status"] == "runtime_ahead_of_calibration"
    assert payload["execution"]["live_runtime_truth"]["runtime_exact_support_rows"] == 77
    assert payload["execution"]["live_runtime_truth"]["calibration_exact_lane_rows"] == 0
    assert "runtime 已有 77 筆 exact support，但 calibration exact lane 仍是 0 筆" in payload["execution"]["live_runtime_truth"]["support_alignment_summary"]
    assert "1 層 deployment capacity" in payload["execution_surface_contract"]["operator_message"]
    assert payload["execution_surface_contract"]["live_ready"] is False
    assert payload["execution_surface_contract"]["live_ready_blockers"] == [
        "live exchange credential 尚未驗證",
        "order ack lifecycle 尚未驗證",
        "fill lifecycle 尚未驗證",
    ]


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


class _QueryStub:
    def __init__(self, rows):
        if isinstance(rows, list):
            self._rows = rows
        elif rows is None:
            self._rows = []
        else:
            self._rows = [rows]

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class _DbStub:
    def __init__(self, trade_row, lifecycle_rows=None):
        self._trade_row = trade_row
        self._lifecycle_rows = lifecycle_rows or []

    def query(self, model, *_args, **_kwargs):
        if getattr(model, "__name__", "") == "OrderLifecycleEvent":
            return _QueryStub(self._lifecycle_rows)
        return _QueryStub(self._trade_row)


def test_build_execution_reconciliation_summary_marks_healthy_match():
    latest_trade = SimpleNamespace(
        timestamp=datetime.now(timezone.utc),
        symbol="BTC/USDT",
        exchange="binance",
        action="BUY",
        order_id="order-1",
        client_order_id="client-1",
        order_status="closed",
        is_dry_run=1,
    )
    lifecycle_rows = [
        SimpleNamespace(
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=3),
            exchange="binance",
            symbol="BTC/USDT",
            order_id="order-1",
            client_order_id="client-1",
            event_type="validation_passed",
            order_state="validated",
            source="execution_service",
            summary="validated",
            payload_json='{}',
            is_dry_run=1,
        ),
        SimpleNamespace(
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=2),
            exchange="binance",
            symbol="BTC/USDT",
            order_id="order-1",
            client_order_id="client-1",
            event_type="venue_ack",
            order_state="closed",
            source="exchange_adapter",
            summary="ack",
            payload_json='{}',
            is_dry_run=1,
        ),
        SimpleNamespace(
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=1),
            exchange="binance",
            symbol="BTC/USDT",
            order_id="order-1",
            client_order_id="client-1",
            event_type="trade_history_persisted",
            order_state="closed",
            source="trade_history",
            summary="persisted",
            payload_json='{}',
            is_dry_run=1,
        ),
    ]
    payload = api_module._build_execution_reconciliation_summary(
        _DbStub(latest_trade, lifecycle_rows=lifecycle_rows),
        "BTCUSDT",
        {
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "degraded": False,
            "positions": [],
            "open_orders": [],
            "position_count": 0,
            "open_order_count": 0,
        },
        {
            "guardrails": {
                "last_order": {
                    "symbol": "BTC/USDT",
                    "status": "closed",
                    "order_id": "order-1",
                    "client_order_id": "client-1",
                }
            }
        },
    )

    assert payload["status"] == "healthy"
    assert payload["trade_history_alignment"]["status"] == "matched"
    assert payload["open_order_alignment"]["status"] == "not_open"
    assert payload["lifecycle_audit"]["stage"] == "terminal_reconciled"
    assert payload["lifecycle_audit"]["restart_replay_required"] is False
    assert payload["recovery_state"]["status"] == "ready_for_next_audit"
    assert payload["lifecycle_contract"]["baseline_contract_status"] == "complete"
    assert payload["lifecycle_contract"]["replay_readiness"] == "ready"
    assert payload["lifecycle_contract"]["replay_verdict"] == "baseline_replay_ready_missing_path_artifacts"
    assert payload["lifecycle_contract"]["replay_verdict_reason"] == "terminal_observed_without_partial_or_cancel"
    assert payload["lifecycle_contract"]["artifact_coverage"] == "terminal_observed_without_partial_or_cancel"
    assert payload["lifecycle_contract"]["artifact_checklist_summary"] == "baseline 3/3 ready · path artifacts 0/2 observed · restart replay ready"
    assert payload["lifecycle_contract"]["artifact_provenance_summary"] == "venue-backed 0 · dry-run only 4 · internal-only 1 · missing/not-applicable 2"
    assert payload["lifecycle_contract"]["artifact_checklist"][0]["key"] == "validation_passed"
    assert payload["lifecycle_contract"]["artifact_checklist"][0]["status"] == "observed"
    assert payload["lifecycle_contract"]["artifact_checklist"][0]["provenance_level"] == "dry_run_only"
    assert payload["lifecycle_contract"]["artifact_checklist"][0]["evidence"]["event_type"] == "validation_passed"
    assert payload["lifecycle_contract"]["artifact_checklist"][3]["key"] == "partial_fill"
    assert payload["lifecycle_contract"]["artifact_checklist"][3]["status"] == "pending_optional"
    assert payload["lifecycle_contract"]["artifact_checklist"][3]["provenance_level"] == "missing"
    assert payload["lifecycle_contract"]["artifact_checklist"][-1]["key"] == "restart_replay"
    assert payload["lifecycle_contract"]["artifact_checklist"][-1]["status"] == "ready"
    assert payload["lifecycle_contract"]["artifact_checklist"][-1]["provenance_level"] == "internal_only"
    assert payload["lifecycle_contract"]["event_type_counts"]["trade_history_persisted"] == 1
    assert payload["lifecycle_contract"]["venue_lanes_summary"].startswith("Binance: baseline 3/3")
    assert payload["lifecycle_contract"]["venue_lanes"][0]["venue"] == "binance"
    assert payload["lifecycle_contract"]["venue_lanes"][0]["status"] == "baseline_ready_missing_path"
    assert payload["lifecycle_contract"]["venue_lanes"][0]["operator_next_artifact"] == "partial_fill_or_cancel"
    assert payload["lifecycle_contract"]["venue_lanes"][0]["artifact_drilldown_summary"] == "artifacts 5 · observed 5 · required missing 0"
    assert payload["lifecycle_contract"]["venue_lanes"][0]["timeline_count"] == 3
    assert payload["lifecycle_contract"]["venue_lanes"][0]["timeline_summary"] == "timeline 3 events · latest trade_history_persisted"
    assert payload["lifecycle_contract"]["venue_lanes"][0]["timeline_events"][-1]["event_type"] == "trade_history_persisted"
    assert payload["issues"] == []


def test_build_execution_reconciliation_summary_tracks_unscoped_internal_lane_when_exchange_missing():
    latest_trade = SimpleNamespace(
        timestamp=datetime.now(timezone.utc),
        symbol="BTC/USDT",
        exchange=None,
        action="BUY",
        order_id="order-1",
        client_order_id="client-1",
        order_status="open",
        is_dry_run=0,
    )
    lifecycle_rows = [
        SimpleNamespace(
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=3),
            exchange=None,
            symbol="BTC/USDT",
            order_id="order-1",
            client_order_id="client-1",
            event_type="validation_passed",
            order_state="validated",
            source="execution_service",
            summary="validated",
            payload_json='{}',
            is_dry_run=0,
        ),
        SimpleNamespace(
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=2),
            exchange=None,
            symbol="BTC/USDT",
            order_id="order-1",
            client_order_id="client-1",
            event_type="trade_history_persisted",
            order_state="open",
            source="trade_history",
            summary="persisted",
            payload_json='{}',
            is_dry_run=0,
        ),
    ]
    payload = api_module._build_execution_reconciliation_summary(
        _DbStub(latest_trade, lifecycle_rows=lifecycle_rows),
        "BTCUSDT",
        {
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "degraded": False,
            "positions": [],
            "open_orders": [],
            "position_count": 0,
            "open_order_count": 0,
        },
        {
            "guardrails": {
                "last_order": {
                    "symbol": "BTC/USDT",
                    "status": "open",
                    "order_id": "order-1",
                    "client_order_id": "client-1",
                }
            }
        },
    )

    lanes = {lane["venue"]: lane for lane in payload["lifecycle_contract"]["venue_lanes"]}
    assert lanes["unscoped_internal"]["baseline_observed"] == 2
    assert lanes["unscoped_internal"]["baseline_required"] == 3
    assert lanes["unscoped_internal"]["status"] == "baseline_incomplete"
    assert lanes["unscoped_internal"]["operator_next_artifact"] == "venue_ack"
    assert lanes["unscoped_internal"]["artifact_drilldown_summary"] == "artifacts 7 · observed 2 · required missing 2"
    assert lanes["unscoped_internal"]["timeline_count"] == 2
    assert lanes["unscoped_internal"]["timeline_events"][0]["exchange"] is None
    assert "Unscoped internal: baseline 2/3" in payload["lifecycle_contract"]["venue_lanes_summary"]


def test_build_live_runtime_closure_surface_marks_circuit_breaker_as_runtime_blocker():
    payload = api_module._build_live_runtime_closure_surface(
        {
            "signal": "CIRCUIT_BREAKER",
            "reason": "Recent 50-sample win rate: 10.00% < 30%",
            "allowed_layers": 0,
            "allowed_layers_raw": None,
            "allowed_layers_raw_reason": "circuit_breaker_preempts_runtime_sizing",
            "allowed_layers_reason": "circuit_breaker_blocks_trade",
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "circuit_breaker_blocks_trade",
            "deployment_blocker": "circuit_breaker_active",
            "deployment_blocker_reason": "Recent 50-sample win rate: 10.00% < 30%",
            "deployment_blocker_source": "circuit_breaker",
            "deployment_blocker_details": {"release_condition": {"recent_window": 50}},
        }
    )

    assert payload["runtime_closure_state"] == "circuit_breaker_active"
    assert payload["allowed_layers_reason"] == "circuit_breaker_blocks_trade"
    assert payload["execution_guardrail_reason"] == "circuit_breaker_blocks_trade"
    assert payload["deployment_blocker"] == "circuit_breaker_active"
    assert "release condition = streak < 50 且 recent 50 win rate >= 30%" in payload["runtime_closure_summary"]


def test_build_execution_reconciliation_summary_flags_missing_open_order_when_snapshot_fresh():
    payload = api_module._build_execution_reconciliation_summary(
        _DbStub(None),
        "BTCUSDT",
        {
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "degraded": False,
            "positions": [],
            "open_orders": [],
            "position_count": 0,
            "open_order_count": 0,
        },
        {
            "guardrails": {
                "last_order": {
                    "symbol": "BTC/USDT",
                    "status": "open",
                    "order_id": "order-open",
                    "client_order_id": "client-open",
                }
            }
        },
    )

    assert payload["status"] == "warning"
    assert payload["open_order_alignment"]["status"] == "missing_from_account_snapshot"
    assert payload["lifecycle_audit"]["stage"] == "open_missing_from_snapshot"
    assert payload["lifecycle_audit"]["restart_replay_required"] is True
    assert payload["recovery_state"]["status"] == "needs_open_order_replay"
    assert payload["lifecycle_contract"]["replay_verdict"] == "baseline_events_missing"
    assert "open_order_missing_from_snapshot" in payload["issues"]


def test_build_execution_reconciliation_summary_without_runtime_order_is_idle():
    payload = api_module._build_execution_reconciliation_summary(
        _DbStub(None),
        "BTCUSDT",
        {
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "degraded": False,
            "positions": [],
            "open_orders": [],
        },
        {"guardrails": {"last_order": None}},
    )

    assert payload["lifecycle_audit"]["stage"] == "no_runtime_order"
    assert payload["recovery_state"]["status"] == "idle"
    assert payload["recovery_state"]["restart_replay_required"] is False
    assert payload["lifecycle_contract"]["status"] == "absent"
    assert payload["lifecycle_contract"]["replay_readiness"] == "not_applicable"
    assert payload["lifecycle_contract"]["replay_verdict"] == "no_runtime_order"
    assert payload["lifecycle_contract"]["artifact_checklist_summary"] == "尚未建立任何 runtime order artifact；先捕捉第一筆 order lifecycle。"
    assert payload["lifecycle_contract"]["artifact_provenance_summary"] == "venue-backed 0 · dry-run only 0 · internal-only 0 · missing/not-applicable 2"
    assert payload["lifecycle_contract"]["artifact_checklist"][0]["key"] == "capture_first_runtime_order"
    assert payload["lifecycle_contract"]["artifact_checklist"][0]["status"] == "not_applicable"
    assert payload["lifecycle_contract"]["artifact_checklist"][0]["provenance_level"] == "missing"


def test_build_execution_reconciliation_summary_marks_lifecycle_contract_incomplete_without_baseline_events():
    latest_trade = SimpleNamespace(
        timestamp=datetime.now(timezone.utc),
        symbol="BTC/USDT",
        exchange="binance",
        action="BUY",
        order_id="order-gap",
        client_order_id="client-gap",
        order_status="closed",
        is_dry_run=1,
    )
    lifecycle_rows = [
        SimpleNamespace(
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=1),
            exchange="binance",
            symbol="BTC/USDT",
            order_id="order-gap",
            client_order_id="client-gap",
            event_type="venue_ack",
            order_state="closed",
            source="exchange_adapter",
            summary="ack",
            payload_json='{}',
            is_dry_run=1,
        ),
    ]
    payload = api_module._build_execution_reconciliation_summary(
        _DbStub(latest_trade, lifecycle_rows=lifecycle_rows),
        "BTCUSDT",
        {
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "degraded": False,
            "positions": [],
            "open_orders": [],
        },
        {
            "guardrails": {
                "last_order": {
                    "symbol": "BTC/USDT",
                    "status": "closed",
                    "order_id": "order-gap",
                    "client_order_id": "client-gap",
                }
            }
        },
    )

    assert payload["lifecycle_contract"]["status"] == "incomplete"
    assert payload["lifecycle_contract"]["baseline_contract_status"] == "incomplete"
    assert payload["lifecycle_contract"]["replay_readiness"] == "blocked"
    assert payload["lifecycle_contract"]["replay_verdict"] == "baseline_events_missing"
    assert payload["lifecycle_contract"]["replay_verdict_reason"] == "missing_required_lifecycle_events"
    assert payload["lifecycle_contract"]["missing_event_types"] == ["validation_passed", "trade_history_persisted"]
    assert payload["lifecycle_contract"]["operator_next_artifact"] == "backfill_required_lifecycle_events"
    assert payload["lifecycle_contract"]["artifact_checklist_summary"] == "baseline 1/3 ready · path artifacts 0/2 observed · restart replay blocked"
    assert payload["lifecycle_contract"]["artifact_checklist"][0]["status"] == "missing"
    assert payload["lifecycle_contract"]["artifact_checklist"][1]["status"] == "observed"
    assert payload["lifecycle_contract"]["artifact_checklist"][2]["status"] == "missing"
    assert payload["lifecycle_contract"]["artifact_checklist"][-1]["status"] == "blocked"


def test_build_execution_reconciliation_summary_normalizes_epoch_runtime_timestamp():
    latest_trade = SimpleNamespace(
        timestamp=datetime.now(timezone.utc),
        symbol="BTC/USDT",
        exchange="binance",
        action="BUY",
        order_id="order-epoch",
        client_order_id="client-epoch",
        order_status="closed",
        is_dry_run=0,
    )
    payload = api_module._build_execution_reconciliation_summary(
        _DbStub(latest_trade),
        "BTCUSDT",
        {
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "degraded": False,
            "positions": [],
            "open_orders": [],
        },
        {
            "guardrails": {
                "last_order": {
                    "symbol": "BTC/USDT",
                    "status": "closed",
                    "order_id": "order-epoch",
                    "client_order_id": "client-epoch",
                    "timestamp": 1_712_345_678_901,
                }
            }
        },
    )

    assert payload["lifecycle_audit"]["evidence"]["runtime_order_timestamp"].endswith("Z")
    assert payload["lifecycle_audit"]["evidence"]["trade_history_timestamp"].endswith("Z")


def test_build_execution_reconciliation_summary_includes_lifecycle_timeline():
    latest_trade = SimpleNamespace(
        timestamp=datetime.now(timezone.utc),
        symbol="BTC/USDT",
        exchange="binance",
        action="BUY",
        order_id="order-timeline",
        client_order_id="client-timeline",
        order_status="closed",
        is_dry_run=1,
    )
    lifecycle_rows = [
        SimpleNamespace(
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=2),
            exchange="binance",
            symbol="BTC/USDT",
            order_id="order-timeline",
            client_order_id="client-timeline",
            event_type="validation_passed",
            order_state="validated",
            source="execution_service",
            summary="validated",
            payload_json='{"normalization": {"normalized": {"qty": 0.01}}}',
            is_dry_run=1,
        ),
        SimpleNamespace(
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=1),
            exchange="binance",
            symbol="BTC/USDT",
            order_id="order-timeline",
            client_order_id="client-timeline",
            event_type="venue_ack",
            order_state="closed",
            source="exchange_adapter",
            summary="ack",
            payload_json='{"timestamp": 1712345678901}',
            is_dry_run=1,
        ),
    ]
    payload = api_module._build_execution_reconciliation_summary(
        _DbStub(latest_trade, lifecycle_rows=lifecycle_rows),
        "BTCUSDT",
        {
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "degraded": False,
            "positions": [],
            "open_orders": [],
        },
        {
            "guardrails": {
                "last_order": {
                    "symbol": "BTC/USDT",
                    "status": "closed",
                    "order_id": "order-timeline",
                    "client_order_id": "client-timeline",
                }
            }
        },
    )

    assert payload["lifecycle_timeline"]["status"] == "available"
    assert payload["lifecycle_timeline"]["total_events"] == 2
    assert payload["lifecycle_timeline"]["latest_event"]["event_type"] == "venue_ack"
    assert payload["lifecycle_timeline"]["events"][0]["payload"]["normalization"]["normalized"]["qty"] == 0.01


def test_build_execution_reconciliation_summary_marks_venue_backed_artifact_provenance():
    latest_trade = SimpleNamespace(
        timestamp=datetime.now(timezone.utc),
        symbol="BTC/USDT",
        exchange="binance",
        action="BUY",
        order_id="order-venue-proof",
        client_order_id="client-venue-proof",
        order_status="closed",
        is_dry_run=0,
    )
    lifecycle_rows = [
        SimpleNamespace(
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=2),
            exchange="binance",
            symbol="BTC/USDT",
            order_id="order-venue-proof",
            client_order_id="client-venue-proof",
            event_type="validation_passed",
            order_state="validated",
            source="execution_service",
            summary="validated",
            payload_json='{}',
            is_dry_run=0,
        ),
        SimpleNamespace(
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=1),
            exchange="binance",
            symbol="BTC/USDT",
            order_id="order-venue-proof",
            client_order_id="client-venue-proof",
            event_type="venue_ack",
            order_state="closed",
            source="exchange_adapter",
            summary="ack",
            payload_json='{}',
            is_dry_run=0,
        ),
    ]
    payload = api_module._build_execution_reconciliation_summary(
        _DbStub(latest_trade, lifecycle_rows=lifecycle_rows),
        "BTCUSDT",
        {
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "degraded": False,
            "positions": [],
            "open_orders": [],
        },
        {
            "guardrails": {
                "last_order": {
                    "symbol": "BTC/USDT",
                    "status": "closed",
                    "order_id": "order-venue-proof",
                    "client_order_id": "client-venue-proof",
                }
            }
        },
    )

    assert payload["lifecycle_contract"]["artifact_checklist"][0]["provenance_level"] == "internal_only"
    assert payload["lifecycle_contract"]["artifact_checklist"][0]["proof_chain_summary"] == "1 timeline events · venue-backed 0 · dry-run 0 · internal 1"
    assert payload["lifecycle_contract"]["artifact_checklist"][0]["proof_chain"][0]["event_type"] == "validation_passed"
    assert payload["lifecycle_contract"]["artifact_checklist"][1]["provenance_level"] == "venue_backed"
    assert payload["lifecycle_contract"]["artifact_checklist"][1]["venue_backed"] is True
    assert payload["lifecycle_contract"]["artifact_checklist"][1]["proof_chain_summary"] == "1 timeline events · venue-backed 1 · dry-run 0 · internal 0"
    assert payload["lifecycle_contract"]["artifact_checklist"][1]["proof_chain"][0]["source"] == "exchange_adapter"
    assert payload["lifecycle_contract"]["artifact_checklist"][-1]["proof_chain_summary"] == "2 timeline events · venue-backed 1 · dry-run 0 · internal 1"
    assert len(payload["lifecycle_contract"]["artifact_checklist"][-1]["proof_chain"]) == 2
    assert payload["lifecycle_contract"]["artifact_provenance_counts"]["venue_backed"] >= 1


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
        "command": "cd /home/kazuha/Poly-Trader && /home/kazuha/Poly-Trader/venv/bin/python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT",
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
            "fallback": {"reason": "manual fallback", "command": "cd /home/kazuha/Poly-Trader && /home/kazuha/Poly-Trader/venv/bin/python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT"},
        },
    }), encoding="utf-8")
    monkeypatch.setattr(api_module, "_EXECUTION_METADATA_EXTERNAL_MONITOR_PATH", artifact)
    monkeypatch.setattr(api_module, "_EXECUTION_METADATA_EXTERNAL_MONITOR_INSTALL_CONTRACT_PATH", tmp_path / "missing-install-contract.json")

    state = api_module._load_execution_metadata_external_monitor_state()

    assert state["available"] is True
    assert state["status"] == "healthy"
    assert state["freshness"]["status"] == "fresh"
    assert state["command"].endswith("scripts/execution_metadata_external_monitor.py --symbol BTCUSDT")
    assert state["install_contract"]["preferred_host_lane"] == "user_crontab"
    assert state["install_contract"]["install_status"]["status"] == "installed"
    assert state["install_contract"]["install_status"]["active_lane"] == "user_crontab"
    assert state["install_contract"]["user_crontab"]["schedule"] == "*/5 * * * *"
    assert state["ticking_state"]["status"] == "observed-ticking"
    assert state["ticking_state"]["active_lane"] == "user_crontab"



def test_load_execution_metadata_external_monitor_state_distinguishes_installed_without_tick(tmp_path, monkeypatch):
    install_contract = tmp_path / "execution_metadata_external_monitor_install_contract.json"
    install_contract.write_text(json.dumps({
        "preferred_host_lane": "user_crontab",
        "install_status": {
            "status": "installed",
            "installed": True,
            "active_lane": "user_crontab",
        },
    }), encoding="utf-8")
    monkeypatch.setattr(api_module, "_EXECUTION_METADATA_EXTERNAL_MONITOR_PATH", tmp_path / "missing-external-monitor.json")
    monkeypatch.setattr(api_module, "_EXECUTION_METADATA_EXTERNAL_MONITOR_INSTALL_CONTRACT_PATH", install_contract)

    state = api_module._load_execution_metadata_external_monitor_state()

    assert state["available"] is False
    assert state["install_contract"]["install_status"]["status"] == "installed"
    assert state["ticking_state"]["status"] == "installed"
    assert state["ticking_state"]["active_lane"] == "user_crontab"



def test_build_execution_metadata_smoke_governance_includes_external_monitor(monkeypatch):
    monkeypatch.setattr(api_module, "_load_execution_metadata_external_monitor_state", lambda symbol="BTCUSDT": {
        "available": True,
        "status": "healthy",
        "reason": "external_cron_monitor",
        "checked_at": "2026-04-16T16:00:00Z",
        "freshness": {"status": "fresh"},
        "command": "cd /home/kazuha/Poly-Trader && /home/kazuha/Poly-Trader/venv/bin/python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT",
        "install_contract": {"preferred_host_lane": "user_crontab"},
        "ticking_state": {"status": "observed-ticking", "active_lane": "user_crontab"},
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
    assert governance["external_monitor"]["ticking_state"]["status"] == "observed-ticking"
