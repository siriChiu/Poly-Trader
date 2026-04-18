import asyncio
from types import SimpleNamespace

from backtesting import strategy_lab
from database.models import init_db
from server.routes import api as api_module


def _local_request():
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


def _status_payload():
    return {
        "symbol": "BTCUSDT",
        "timestamp": "2026-04-18T12:00:00Z",
        "execution_surface_contract": {
            "live_ready": False,
            "live_ready_blockers": ["order ack lifecycle 尚未驗證"],
        },
        "execution": {
            "mode": "paper",
            "venue": "binance",
            "guardrails": {
                "kill_switch": False,
                "daily_loss_halt": False,
                "failure_halt": False,
                "last_order": {
                    "venue": "binance",
                    "symbol": "BTCUSDT",
                    "side": "buy",
                    "qty": 0.05,
                    "status": "open",
                    "order_id": "ord-123",
                },
            },
            "live_runtime_truth": {
                "confidence": 0.61,
                "regime_label": "bull",
                "regime_gate": "ALLOW",
                "structure_bucket": "ALLOW|trend|q65",
                "allowed_layers": 2,
                "allowed_layers_reason": "entry_quality_B_two_layers",
                "runtime_closure_state": "runtime_visible_preview",
                "runtime_closure_summary": "目前 runtime truth 與 reconciliation 已可見，但 per-bot ledger 尚未綁定。",
                "sleeve_routing": {
                    "current_regime": "bull",
                    "current_regime_gate": "ALLOW",
                    "current_structure_bucket": "ALLOW|trend|q65",
                    "active_sleeves": [
                        {"key": "trend", "label": "趨勢承接", "summary": "trend", "why": "bull allow"},
                        {"key": "pullback", "label": "回調承接", "summary": "pullback", "why": "bull/chop lane"},
                        {"key": "selective", "label": "高信念精選", "summary": "selective", "why": "quality lane"},
                    ],
                    "inactive_sleeves": [
                        {"key": "rebound", "label": "深跌回補", "summary": "rebound", "why": "not stress lane"},
                    ],
                },
            },
        },
        "account": {
            "captured_at": "2026-04-18T12:00:05Z",
            "degraded": False,
            "operator_message": "account snapshot fresh",
            "recovery_hint": "none",
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "balance": {"total": 1000.0, "free": 820.0, "currency": "USDT"},
            "positions": [{
                "symbol": "BTC/USDT",
                "side": "long",
                "size": 0.1,
                "entryPrice": 67250.0,
                "markPrice": 68000.0,
                "unrealizedPnl": 125.0,
            }],
            "open_orders": [{"symbol": "BTCUSDT", "side": "buy", "qty": 0.01, "price": 69000.0}],
        },
        "execution_reconciliation": {
            "status": "attention",
            "summary": "shared symbol reconciliation available",
            "checked_at": "2026-04-18T12:00:06Z",
            "recovery_state": {
                "status": "operator_review",
                "operator_action": "確認 shared symbol 倉位與 run ownership 邊界。",
            },
            "lifecycle_audit": {
                "stage": "reconciliation_visible",
                "runtime_state": "open_order_detected",
                "trade_history_state": "awaiting_match",
                "restart_replay_required": False,
                "operator_action": "先確認 run 是否只鏡像 shared symbol 狀態。",
            },
        },
    }



def _seed_execution_strategy_catalog(tmp_path, monkeypatch):
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    monkeypatch.setattr(strategy_lab, "STRATEGIES_DIR", strategies_dir)
    strategy_lab.save_strategy(
        "Trend QA Strategy",
        {
            "type": "hybrid",
            "params": {
                "model_name": "random_forest",
                "entry": {
                    "bias50_max": 0.1,
                },
            },
        },
        {
            "roi": 0.083,
            "profit_factor": 1.21,
            "avg_decision_quality_score": 0.61,
            "avg_expected_win_rate": 0.57,
            "total_trades": 14,
        },
    )


def test_execution_run_lifecycle_start_pause_stop_and_detail(monkeypatch, tmp_path):
    async def _fake_status():
        return _status_payload()

    _seed_execution_strategy_catalog(tmp_path, monkeypatch)
    session = init_db(f"sqlite:///{tmp_path / 'execution_runs.db'}")
    monkeypatch.setattr(api_module, "get_config", lambda: {"trading": {"max_position_ratio": 0.10}})
    monkeypatch.setattr(api_module, "get_db", lambda: session)
    monkeypatch.setattr(api_module, "api_status", _fake_status)

    start_payload = asyncio.run(api_module.api_execution_start_run("trend", request=_local_request()))
    run_id = start_payload["run"]["run_id"]
    assert start_payload["action"] == "start"
    assert start_payload["action_result"] == "started"
    assert start_payload["run"]["state"] == "running"
    assert start_payload["run"]["runtime_binding_status"] == "control_plane_only"
    assert start_payload["run"]["runtime_binding_contract"]["status"] == "symbol_scope_runtime_mirror"
    assert start_payload["run"]["runtime_binding_contract"]["operator_action"] == "確認 shared symbol 倉位與 run ownership 邊界。"
    assert start_payload["run"]["runtime_binding_contract"]["ownership_boundary"]["pnl_attribution"] == "symbol_scoped_preview_only"
    assert start_payload["run"]["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["budget_alignment_status"] == "warning_over_planned_preview"
    assert start_payload["run"]["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["gross_position_notional"] == 6800.0
    assert start_payload["run"]["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["open_order_notional"] == 690.0
    assert start_payload["run"]["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["unrealized_pnl"] == 125.0
    assert start_payload["run"]["strategy_binding"]["strategy_name"] == "Trend QA Strategy"
    assert start_payload["run"]["strategy_binding"]["strategy_source"] == "strategy_lab_saved"
    assert start_payload["run"]["strategy_binding"]["strategy_hash"]
    assert start_payload["run"]["runtime_binding_snapshot"]["reconciliation"]["status"] == "attention"
    assert start_payload["run"]["runtime_binding_snapshot"]["guardrails"]["last_order"]["order_id"] == "ord-123"
    assert start_payload["snapshot"]["summary"]["running_runs"] == 1

    overview_payload = asyncio.run(api_module.api_execution_overview())
    trend_card = next(card for card in overview_payload["profile_cards"] if card["key"] == "trend")
    assert trend_card["current_run_state"] == "running"
    assert trend_card["control_contract"]["start_status"] == "already_running"
    assert trend_card["current_run"]["runtime_binding_contract"]["status"] == "symbol_scope_runtime_mirror"

    pause_payload = asyncio.run(api_module.api_execution_pause_run(run_id, request=_local_request()))
    assert pause_payload["action"] == "pause"
    assert pause_payload["action_result"] == "paused"
    assert pause_payload["run"]["state"] == "paused"
    assert pause_payload["run"]["action_contract"]["can_resume"] is True

    resume_payload = asyncio.run(api_module.api_execution_start_run("trend", request=_local_request()))
    assert resume_payload["action_result"] == "resumed"
    assert resume_payload["run"]["state"] == "running"

    stop_payload = asyncio.run(api_module.api_execution_stop_run(run_id, request=_local_request()))
    assert stop_payload["action"] == "stop"
    assert stop_payload["action_result"] == "stopped"
    assert stop_payload["run"]["state"] == "stopped"
    assert stop_payload["run"]["stop_reason"] == "operator_stop"

    detail_payload = asyncio.run(api_module.api_execution_run_detail(run_id))
    event_types = [event["event_type"] for event in detail_payload["recent_events"]]
    assert detail_payload["state"] == "stopped"
    assert detail_payload["runtime_binding_contract"]["status"] == "symbol_scope_runtime_mirror"
    assert detail_payload["runtime_binding_contract"]["ownership_boundary"]["ledger_scope"] == "shared_symbol_preview_only"
    assert detail_payload["runtime_binding_contract"]["ownership_boundary"]["pnl_attribution"] == "symbol_scoped_preview_only"
    assert detail_payload["strategy_binding"]["strategy_name"] == "Trend QA Strategy"
    assert detail_payload["strategy_binding"]["strategy_hash"] == start_payload["run"]["strategy_binding"]["strategy_hash"]
    assert detail_payload["runtime_binding_snapshot"]["account_snapshot"]["position_count"] == 1
    assert detail_payload["runtime_binding_snapshot"]["capital_preview"]["allocation_scope"] == "run_budget_vs_shared_balance_preview"
    assert detail_payload["runtime_binding_snapshot"]["capital_preview"]["balance_total"] == 1000.0
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_preview"]["positions_total_count"] == 1
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_preview"]["open_orders_total_count"] == 1
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_preview"]["positions"][0]["symbol"] == "BTC/USDT"
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_preview"]["open_orders"][0]["symbol"] == "BTCUSDT"
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["total_known_commitment"] == 7490.0
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["budget_alignment_status"] == "warning_over_planned_preview"
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["position_priced_count"] == 1
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["open_order_priced_count"] == 1
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["unrealized_pnl"] == 125.0
    assert "started" in event_types
    assert "paused" in event_types
    assert "resumed" in event_types
    assert "stopped" in event_types

    runs_payload = asyncio.run(api_module.api_execution_runs())
    assert runs_payload["summary"]["running_runs"] == 0
    assert runs_payload["summary"]["paused_runs"] == 0
    assert runs_payload["summary"]["stopped_runs"] == 1
    assert runs_payload["runs"][0]["run_id"] == run_id



def test_execution_run_start_rejects_inactive_profile(monkeypatch, tmp_path):
    async def _fake_status():
        return _status_payload()

    session = init_db(f"sqlite:///{tmp_path / 'execution_runs_blocked.db'}")
    monkeypatch.setattr(api_module, "get_config", lambda: {"trading": {"max_position_ratio": 0.10}})
    monkeypatch.setattr(api_module, "get_db", lambda: session)
    monkeypatch.setattr(api_module, "api_status", _fake_status)

    try:
        asyncio.run(api_module.api_execution_start_run("rebound", request=_local_request()))
    except Exception as exc:
        detail = getattr(exc, "detail", {})
        assert detail["code"] == "profile_not_startable"
        assert detail["context"]["start_status"] == "inactive_preview"
    else:
        raise AssertionError("inactive profile should not start")
