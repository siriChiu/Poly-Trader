from pathlib import Path

import pytest

from backtesting import strategy_lab


@pytest.fixture
def isolated_strategies_dir(tmp_path: Path, monkeypatch):
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    monkeypatch.setattr(strategy_lab, "STRATEGIES_DIR", strategies_dir)
    return strategies_dir


def test_build_auto_strategy_candidates_exposes_multi_sleeve_metadata():
    candidates = strategy_lab.build_auto_strategy_candidates(["random_forest", "xgboost"])

    primary_sleeves = {candidate.get("metadata", {}).get("primary_sleeve_key") for candidate in candidates}

    assert {"trend", "pullback", "rebound", "selective"}.issubset(primary_sleeves)
    assert all(candidate.get("metadata", {}).get("primary_sleeve_label") for candidate in candidates)
    assert all(isinstance(candidate.get("metadata", {}).get("sleeve_labels"), list) for candidate in candidates)
    assert any("capital_defense" in (candidate.get("metadata", {}).get("sleeve_keys") or []) for candidate in candidates)
    assert any("turning_point_exit" in (candidate.get("metadata", {}).get("sleeve_keys") or []) for candidate in candidates)


def test_save_strategy_metadata_infers_primary_and_auxiliary_sleeves(isolated_strategies_dir: Path):
    strategy_lab.save_strategy(
        "Sleeve Demo",
        {
            "type": "hybrid",
            "params": {
                "entry": {
                    "bias50_max": -1.2,
                    "layer2_bias_max": -2.8,
                    "layer3_bias_max": -5.0,
                    "confidence_min": 0.75,
                    "entry_quality_min": 0.68,
                    "top_k_percent": 5,
                    "allowed_regimes": ["bear"],
                },
                "capital_management": {"mode": "reserve_90", "base_entry_fraction": 0.10, "reserve_trigger_drawdown": 0.08},
                "editor_modules": ["reserve_90", "turning_point"],
                "turning_point": {"enabled": True, "bottom_score_min": 0.62, "top_score_take_profit": 0.68},
            },
        },
        {"roi": 0.09, "win_rate": 0.61},
    )

    loaded = strategy_lab.load_strategy("Sleeve Demo")

    assert loaded is not None
    assert loaded["metadata"]["primary_sleeve_key"] == "selective"
    assert loaded["metadata"]["primary_sleeve_label"] == "高信念精選"
    assert "capital_defense" in loaded["metadata"]["sleeve_keys"]
    assert "turning_point_exit" in loaded["metadata"]["sleeve_keys"]
    assert "高信念精選" in (loaded["metadata"].get("sleeve_summary") or "")


def test_build_regime_aware_sleeve_routing_activates_bull_trend_pullback_and_selective_lanes():
    routing = strategy_lab.build_regime_aware_sleeve_routing(
        regime_label="bull",
        regime_gate="ALLOW",
        structure_bucket="A",
        allowed_layers=2,
        entry_quality=0.74,
    )

    active_keys = {item["key"] for item in routing["active_sleeves"]}
    inactive_keys = {item["key"] for item in routing["inactive_sleeves"]}

    assert routing["current_regime"] == "bull"
    assert routing["current_regime_gate"] == "ALLOW"
    assert routing["active_ratio_text"] == f"{routing['active_count']}/{routing['total_count']}"
    assert {"trend", "pullback", "selective"}.issubset(active_keys)
    assert "rebound" in inactive_keys
    assert any("bull" in (item["why"] or "") for item in routing["active_sleeves"])


def test_build_regime_aware_sleeve_routing_turns_all_sleeves_inactive_under_runtime_blocker():
    routing = strategy_lab.build_regime_aware_sleeve_routing(
        regime_label="bull",
        regime_gate="ALLOW",
        structure_bucket="A",
        allowed_layers=1,
        entry_quality=0.62,
        deployment_blocker="circuit_breaker_active",
        execution_guardrail_reason="circuit_breaker_blocks_trade",
    )

    assert routing["active_count"] == 0
    assert len(routing["inactive_sleeves"]) == routing["total_count"]
    assert all("circuit breaker" in (item["why"] or "") for item in routing["inactive_sleeves"])
    assert "0/" in routing["summary"]
