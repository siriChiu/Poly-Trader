import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "live_decision_quality_drilldown.py"
spec = importlib.util.spec_from_file_location("live_decision_quality_drilldown_test_module", MODULE_PATH)
live_drilldown = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(live_drilldown)


def test_component_gap_attribution_identifies_best_single_component_and_bias50_counterfactual():
    eq_components = {
        "entry_quality": 0.499,
        "trade_floor": 0.55,
        "base_quality_weight": 0.75,
        "structure_quality_weight": 0.25,
        "base_components": [
            {
                "feature": "feat_4h_bias50",
                "weight": 0.40,
                "raw_value": 3.2128,
                "normalized_score": 0.1416,
                "weighted_contribution": 0.0566,
            },
            {
                "feature": "feat_nose",
                "weight": 0.18,
                "raw_value": 0.4280,
                "normalized_score": 0.5720,
                "weighted_contribution": 0.1030,
            },
            {
                "feature": "feat_pulse",
                "weight": 0.27,
                "raw_value": 0.8314,
                "normalized_score": 0.8314,
                "weighted_contribution": 0.2245,
            },
            {
                "feature": "feat_ear",
                "weight": 0.15,
                "raw_value": -0.0016,
                "normalized_score": 0.9922,
                "weighted_contribution": 0.1488,
            },
        ],
        "structure_components": [
            {
                "feature": "feat_4h_bb_pct_b",
                "weight": 0.34,
                "raw_value": 0.4827,
                "normalized_score": 0.4827,
                "weighted_contribution": 0.1641,
            },
            {
                "feature": "feat_4h_dist_bb_lower",
                "weight": 0.33,
                "raw_value": 1.5502,
                "normalized_score": 0.1938,
                "weighted_contribution": 0.0639,
            },
            {
                "feature": "feat_4h_dist_swing_low",
                "weight": 0.33,
                "raw_value": 5.1235,
                "normalized_score": 0.5124,
                "weighted_contribution": 0.1691,
            },
        ],
    }
    q35_counterfactuals = {
        "entry_if_bias50_fully_relaxed": 0.7565,
        "layers_if_bias50_fully_relaxed": 2,
        "required_bias50_cap_for_floor": 2.3628,
        "current_bias50_value": 3.2128,
    }

    result = live_drilldown._component_gap_attribution(eq_components, q35_counterfactuals)

    assert result["remaining_gap_to_floor"] == 0.051
    assert result["best_single_component"]["feature"] == "feat_4h_bias50"
    assert result["best_single_component"]["can_single_component_cross_floor"] is True
    assert result["best_single_component"]["required_score_delta_to_cross_floor"] == 0.17
    assert result["single_component_floor_crossers"][0]["feature"] == "feat_4h_bias50"
    assert result["bias50_floor_counterfactual"]["required_bias50_cap_for_floor"] == 2.3628
    assert result["base_group_max_entry_gain"] > result["structure_group_max_entry_gain"]


def test_component_gap_attribution_handles_zero_gap_without_required_delta():
    eq_components = {
        "entry_quality": 0.61,
        "trade_floor": 0.55,
        "base_quality_weight": 0.75,
        "base_components": [
            {"feature": "feat_4h_bias50", "weight": 0.40, "normalized_score": 0.6, "weighted_contribution": 0.24},
        ],
        "structure_quality_weight": 0.25,
        "structure_components": [],
    }

    result = live_drilldown._component_gap_attribution(eq_components, {})

    assert result["remaining_gap_to_floor"] == 0.0
    assert result["best_single_component"] is None
    assert result["single_component_floor_crossers"] == []


def test_runtime_blocker_summary_and_unavailable_gap_attribution_for_circuit_breaker():
    payload = {
        "signal": "CIRCUIT_BREAKER",
        "model_type": "circuit_breaker",
        "reason": "Consecutive loss streak: 50 >= 50",
        "streak": 50,
        "allowed_layers": 0,
        "deployment_blocker_details": {
            "recent_window": {"window_size": 50, "wins": 3, "win_rate": 0.06, "floor": 0.3},
            "release_condition": {"required_recent_window_wins": 15, "additional_recent_window_wins_needed": 12},
        },
    }

    blocker = live_drilldown._runtime_blocker_summary(payload)
    result = live_drilldown._unavailable_component_gap_attribution(payload["reason"], blocker=blocker)

    assert blocker == {
        "type": "circuit_breaker",
        "signal": "CIRCUIT_BREAKER",
        "model_type": "circuit_breaker",
        "reason": "Consecutive loss streak: 50 >= 50",
        "streak": 50,
        "win_rate": None,
        "recent_window_win_rate": None,
        "recent_window_wins": None,
        "window_size": None,
        "triggered_by": [],
        "horizon_minutes": None,
        "allowed_layers": 0,
        "release_condition": {"required_recent_window_wins": 15, "additional_recent_window_wins_needed": 12},
        "recent_window": {"window_size": 50, "wins": 3, "win_rate": 0.06, "floor": 0.3},
    }
    assert result["remaining_gap_to_floor"] is None
    assert result["best_single_component"] is None
    assert result["runtime_blocker"]["type"] == "circuit_breaker"
    assert result["unavailable_reason"] == "Consecutive loss streak: 50 >= 50"


def test_deployment_blocker_summary_extracts_q35_no_deploy_governance():
    payload = {
        "deployment_blocker": "bull_q35_no_deploy_governance",
        "deployment_blocker_reason": "safe redesign 失敗，只剩 unsafe floor cross",
        "deployment_blocker_source": "q35_scaling_audit+q15_support_audit",
        "deployment_blocker_details": {
            "support_route_verdict": "exact_bucket_supported",
            "unsafe_floor_cross_candidate": {"weights": {"feat_ear": 1.0}},
        },
    }

    blocker = live_drilldown._deployment_blocker_summary(payload)

    assert blocker == {
        "type": "bull_q35_no_deploy_governance",
        "reason": "safe redesign 失敗，只剩 unsafe floor cross",
        "source": "q35_scaling_audit+q15_support_audit",
        "details": {
            "support_route_verdict": "exact_bucket_supported",
            "unsafe_floor_cross_candidate": {"weights": {"feat_ear": 1.0}},
        },
    }


def test_drilldown_markdown_mentions_runtime_closure_summaries():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "capacity opened but signal still HOLD" in source
    assert "patch active but execution still blocked" in source
    assert "runtime closure summary" in source
