import asyncio

from backtesting import strategy_lab
from database.models import init_db
from execution.console_overview import build_execution_overview
from server.routes import api as api_module


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
            "venue": "okx",
            "live_runtime_truth": {
                "confidence": 0.60,
                "regime_label": "bull",
                "regime_gate": "ALLOW",
                "structure_bucket": "ALLOW|trend|q65",
                "allowed_layers": 2,
                "allowed_layers_reason": "entry_quality_B_two_layers",
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
            }
        },
        "account": {
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "balance": {"total": 1000.0, "free": 820.0, "currency": "USDT"},
            "positions": [{"symbol": "BTC/USDT", "size": 0.1}],
            "open_orders": [{"symbol": "BTCUSDT", "qty": 0.01}],
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


def test_build_execution_overview_exposes_stateful_run_control_beta_contract():
    payload = build_execution_overview(
        _status_payload(),
        config={"trading": {"max_position_ratio": 0.10}},
    )

    assert payload["controls_mode"] == "stateful_run_control_beta"
    assert payload["summary"]["total_profiles"] == 4
    assert payload["summary"]["active_profiles"] == 3
    assert payload["summary"]["monitoring_profiles"] == 3
    assert payload["summary"]["running_runs"] == 0
    assert payload["summary"]["allocation_rule"] == "equal_split_active_sleeves"
    assert payload["operator_message"] == "Bot 營運現在已具備可持久化的運行控制；啟動 / 暫停 / 停止都會保留事件紀錄，且每條運行已可鏡像同商品的執行期 / 對帳摘要，但每個 Bot 的資金 / 持倉 / 委託帳本仍未完全接上。"
    assert payload["upgrade_prerequisite"] == "下一步必須把每個 Bot 的資金 / 持倉 / 委託歸因綁到各自運行，否則這仍只是可持久化的運行控制測試版，不是完整的 Bot 執行期。"
    assert payload["summary"]["operator_message"] == payload["operator_message"]
    assert payload["capital_plan"]["allocation_rule"] == "equal_split_active_sleeves"
    assert payload["capital_plan"]["operator_message"] == "可部署資金目前仍先依風險控管頭寸公式估算，再由啟用倉位腿均分；運行控制雖已可持久化，但每個 Bot 的資金帳本仍未落地。"
    assert payload["capital_plan"]["symbol_scoped_position_count"] == 1
    assert payload["capital_plan"]["symbol_scoped_open_order_count"] == 1
    assert round(payload["capital_plan"]["deployable_capital"], 4) == 60.4
    assert round(payload["capital_plan"]["per_active_profile_budget"], 4) == round(60.4 / 3.0, 4)

    cards = {card["key"]: card for card in payload["profile_cards"]}
    assert cards["trend"]["profile_id"] == "trend"
    assert cards["trend"]["activation_status"] == "active"
    assert cards["trend"]["lifecycle_status"] == "monitoring_shared_symbol"
    assert cards["trend"]["control_contract"]["start_status"] == "ready_control_plane"
    assert cards["trend"]["control_contract"]["mode"] == "stateful_run_control_beta"
    assert cards["trend"]["current_run"] is None
    assert round(cards["trend"]["planned_budget_amount"], 4) == round(60.4 / 3.0, 4)
    assert cards["rebound"]["activation_status"] == "inactive"
    assert cards["rebound"]["lifecycle_status"] == "standby"
    assert cards["rebound"]["planned_budget_amount"] == 0.0



def test_build_execution_overview_exposes_strategy_snapshot_summary(monkeypatch, tmp_path):
    _seed_execution_strategy_catalog(tmp_path, monkeypatch)

    payload = build_execution_overview(
        _status_payload(),
        config={"trading": {"max_position_ratio": 0.10}},
    )

    cards = {card["key"]: card for card in payload["profile_cards"]}
    trend_binding = cards["trend"]["strategy_binding"]
    pullback_binding = cards["pullback"]["strategy_binding"]

    assert payload["strategy_source_summary"]["strategy_count"] == 1
    assert payload["strategy_source_summary"]["covered_sleeves"] == 1
    assert payload["strategy_source_summary"]["total_sleeves"] == 4
    assert payload["strategy_source_summary"]["missing_sleeves"] == ["pullback", "rebound", "selective"]
    assert payload["strategy_source_summary"]["route"] == "/api/execution/strategies/source"
    assert trend_binding["status"] == "saved_strategy_bound"
    assert trend_binding["strategy_name"] == "Trend QA Strategy"
    assert trend_binding["strategy_source"] == "strategy_lab_saved"
    assert trend_binding["primary_sleeve_key"] == "trend"
    assert trend_binding["strategy_hash"]
    assert pullback_binding["status"] == "missing_saved_strategy"
    assert "尚未找到對應 sleeve 的已儲存策略快照" in pullback_binding["summary"]



def test_api_execution_overview_wraps_status_payload_and_registers_execution_control_routes(monkeypatch, tmp_path):
    async def _fake_status():
        return _status_payload()

    _seed_execution_strategy_catalog(tmp_path, monkeypatch)
    session = init_db(f"sqlite:///{tmp_path / 'execution_console.db'}")
    monkeypatch.setattr(api_module, "get_config", lambda: {"trading": {"max_position_ratio": 0.10}})
    monkeypatch.setattr(api_module, "get_db", lambda: session)
    monkeypatch.setattr(api_module, "api_status", _fake_status)

    payload = asyncio.run(api_module.api_execution_overview())
    strategy_payload = asyncio.run(api_module.api_execution_strategy_source())
    runs_payload = asyncio.run(api_module.api_execution_runs())

    assert payload["symbol"] == "BTCUSDT"
    assert payload["controls_mode"] == "stateful_run_control_beta"
    assert payload["summary"]["active_profiles"] == 3
    assert payload["profile_cards"][0]["controls_mode"] == "stateful_run_control_beta"
    assert payload["profile_cards"][0]["strategy_binding"]["status"] == "saved_strategy_bound"
    assert payload["strategy_source_summary"]["route"] == "/api/execution/strategies/source"
    assert strategy_payload["summary"]["strategy_count"] == 1
    assert strategy_payload["sleeve_bindings"]["trend"]["recommended"]["strategy_name"] == "Trend QA Strategy"
    assert runs_payload["controls_mode"] == "stateful_run_control_beta"
    assert runs_payload["summary"]["total_profiles"] == 4
    assert runs_payload["summary"]["total_runs"] == 0
    route_paths = {getattr(route, "path", None) for route in api_module.router.routes}
    assert "/execution/overview" in route_paths
    assert "/execution/strategies/source" in route_paths
    assert "/execution/profiles" in route_paths
    assert "/execution/runs" in route_paths
    assert "/execution/runs/{profile_id}/start" in route_paths
    assert "/execution/runs/{run_id}/pause" in route_paths
    assert "/execution/runs/{run_id}/stop" in route_paths
    assert "/execution/runs/{run_id}" in route_paths
