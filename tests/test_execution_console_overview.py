import asyncio

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



def test_build_execution_overview_creates_equal_split_preview_cards():
    payload = build_execution_overview(
        _status_payload(),
        config={"trading": {"max_position_ratio": 0.10}},
    )

    assert payload["controls_mode"] == "preview_only"
    assert payload["summary"]["total_profiles"] == 4
    assert payload["summary"]["active_profiles"] == 3
    assert payload["summary"]["monitoring_profiles"] == 3
    assert payload["summary"]["allocation_rule"] == "equal_split_active_sleeves"
    assert payload["capital_plan"]["allocation_rule"] == "equal_split_active_sleeves"
    assert payload["capital_plan"]["symbol_scoped_position_count"] == 1
    assert payload["capital_plan"]["symbol_scoped_open_order_count"] == 1
    assert round(payload["capital_plan"]["deployable_capital"], 4) == 60.4
    assert round(payload["capital_plan"]["per_active_profile_budget"], 4) == round(60.4 / 3.0, 4)

    cards = {card["key"]: card for card in payload["profile_cards"]}
    assert cards["trend"]["activation_status"] == "active"
    assert cards["trend"]["lifecycle_status"] == "monitoring_shared_symbol"
    assert cards["trend"]["control_contract"]["start_status"] == "ready_preview"
    assert round(cards["trend"]["planned_budget_amount"], 4) == round(60.4 / 3.0, 4)
    assert cards["rebound"]["activation_status"] == "inactive"
    assert cards["rebound"]["lifecycle_status"] == "standby"
    assert cards["rebound"]["planned_budget_amount"] == 0.0



def test_api_execution_overview_wraps_status_payload_and_route_is_registered(monkeypatch):
    async def _fake_status():
        return _status_payload()

    monkeypatch.setattr(api_module, "get_config", lambda: {"trading": {"max_position_ratio": 0.10}})
    monkeypatch.setattr(api_module, "api_status", _fake_status)

    payload = asyncio.run(api_module.api_execution_overview())

    assert payload["symbol"] == "BTCUSDT"
    assert payload["summary"]["active_profiles"] == 3
    assert payload["profile_cards"][0]["controls_mode"] == "preview_only"
    assert any(getattr(route, "path", None) == "/execution/overview" for route in api_module.router.routes)
