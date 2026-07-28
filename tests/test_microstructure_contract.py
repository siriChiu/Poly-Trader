from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from execution.microstructure import MICROSTRUCTURE_FEATURES, build_microstructure_contract
from server.routes import api as api_module


def _ready_artifact(now: datetime) -> dict:
    stamp = now.isoformat().replace("+00:00", "Z")
    return {
        "generated_at": stamp,
        "symbol": "BTC/USDT",
        "venue": "okx",
        "source": {
            "kind": "orderbook_and_trade_flow",
            "name": "test-feed",
            "configured": True,
            "available": True,
            "observed_at": stamp,
        },
        "coverage": {
            "window_minutes": 60,
            "observed_events": 60,
            "covered_events": 60,
            "coverage_ratio": 1.0,
        },
        "features": {
            name: {
                "value": 1.0,
                "available": True,
                "coverage_ratio": 1.0,
                "source": "test-feed",
            }
            for name in MICROSTRUCTURE_FEATURES
        },
        "forecast_edge_bps": 22.0,
        "forecast": {"source": "test-calibrated-edge"},
    }


def test_missing_microstructure_source_is_observation_only():
    now = datetime(2026, 7, 17, 3, 30, tzinfo=timezone.utc)
    contract = build_microstructure_contract({"generated_at": now.isoformat().replace("+00:00", "Z")}, now=now)

    assert contract["status"] == "blocked_missing_source"
    assert contract["source"]["available"] is False
    assert contract["coverage"]["coverage_ratio"] == 0.0
    assert contract["forecast_edge_bps"] is None
    assert contract["decision_contract"] == {
        "status": "observation_only",
        "observation_only": True,
        "paper_shadow_risk_on_allowed": False,
        "live_risk_on_allowed": False,
        "reason": "microstructure source/coverage/forecast is unavailable or stale; remain observation-only",
    }
    assert all(item["available"] is False for item in contract["features"].values())


def test_fresh_source_backed_microstructure_contract_can_supply_paper_forecast_only():
    now = datetime(2026, 7, 17, 3, 30, tzinfo=timezone.utc)
    contract = build_microstructure_contract(_ready_artifact(now), now=now)

    assert contract["status"] == "ready"
    assert contract["forecast_edge_bps"] == 22.0
    assert contract["forecast"]["available"] is True
    assert contract["decision_contract"]["status"] == "candidate_ready"
    assert contract["decision_contract"]["paper_shadow_risk_on_allowed"] is True
    assert contract["decision_contract"]["live_risk_on_allowed"] is False


def test_api_status_wires_microstructure_contract_and_never_uses_stale_model_forecast():
    blocked = build_microstructure_contract(
        {"generated_at": "2026-07-17T03:30:00Z"},
        now=datetime(2026, 7, 17, 3, 30, tzinfo=timezone.utc),
    )

    class StubExecutionService:
        def __init__(self, *args, **kwargs):
            pass

        def execution_summary(self):
            return {}

    class StubAccountSync:
        def __init__(self, *args, **kwargs):
            pass

        def snapshot(self, symbol):
            return {"symbol": symbol}

    with patch.object(api_module, "get_config", return_value={"trading": {"symbol": "BTCUSDT", "dry_run": True}}), \
        patch.object(api_module, "get_db", return_value=SimpleNamespace()), \
        patch.object(api_module, "ExecutionService", StubExecutionService), \
        patch.object(api_module, "AccountSyncService", StubAccountSync), \
        patch.object(api_module, "_build_live_runtime_closure_surface", return_value={"forecast_edge_bps": 999.0}), \
        patch.object(api_module, "load_microstructure_contract", return_value=blocked), \
        patch.object(api_module, "_load_recent_canonical_drift_summary", return_value={}), \
        patch.object(api_module, "_load_high_conviction_topk_summary", return_value={}), \
        patch.object(api_module, "build_range_chop_playbook", return_value={}), \
        patch.object(api_module, "_build_execution_reconciliation_summary", return_value={}), \
        patch.object(api_module, "_ensure_execution_metadata_smoke_governance", return_value={}), \
        patch.object(api_module, "_load_venue_dry_run_proof_summary", return_value={}), \
        patch.object(api_module, "_strategy_data_sync_status", return_value={"freshness": {"overall_status": "fresh"}}):
        payload = asyncio.run(api_module.api_status())

    assert payload["microstructure_contract"]["status"] == "blocked_missing_source"
    assert payload["execution"]["microstructure_contract"]["decision_contract"]["observation_only"] is True
    assert payload["execution"]["live_runtime_truth"]["forecast_edge_bps"] is None
    assert payload["cost_aware_edge"]["forecast_gate_status"] == "observation_only_missing_microstructure_forecast"
    assert payload["cost_aware_edge"]["passed"] is False
