import importlib.util
import json
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
    assert result["reconstructed_from_q15_patch"] is False


def test_component_gap_attribution_reconstructs_baseline_when_q15_patch_is_active():
    eq_components = {
        "entry_quality": 0.55,
        "trade_floor": 0.55,
        "base_quality_weight": 0.75,
        "structure_quality_weight": 0.25,
        "base_components": [
            {
                "feature": "feat_4h_bias50",
                "weight": 0.40,
                "raw_value": 3.8273,
                "normalized_score": 0.4397,
                "weighted_contribution": 0.1759,
            },
            {
                "feature": "feat_nose",
                "weight": 0.18,
                "raw_value": 0.0911,
                "normalized_score": 0.9089,
                "weighted_contribution": 0.1636,
            },
            {
                "feature": "feat_pulse",
                "weight": 0.27,
                "raw_value": 0.4974,
                "normalized_score": 0.4974,
                "weighted_contribution": 0.1343,
            },
            {
                "feature": "feat_ear",
                "weight": 0.15,
                "raw_value": -0.009,
                "normalized_score": 0.9549,
                "weighted_contribution": 0.1432,
            },
        ],
        "structure_quality": 0.349,
        "structure_components": [
            {
                "feature": "feat_4h_bb_pct_b",
                "weight": 0.34,
                "raw_value": 0.4405,
                "normalized_score": 0.4405,
                "weighted_contribution": 0.1498,
            },
            {
                "feature": "feat_4h_dist_bb_lower",
                "weight": 0.33,
                "raw_value": 1.3549,
                "normalized_score": 0.1694,
                "weighted_contribution": 0.0559,
            },
            {
                "feature": "feat_4h_dist_swing_low",
                "weight": 0.33,
                "raw_value": 4.3429,
                "normalized_score": 0.4343,
                "weighted_contribution": 0.1433,
            },
        ],
        "q15_exact_supported_component_patch": {
            "applied": True,
            "feature": "feat_4h_bias50",
            "original_normalized_score": 0.0,
            "patched_normalized_score": 0.4397,
            "required_score_delta": 0.4397,
        },
    }

    result = live_drilldown._component_gap_attribution(eq_components, {})

    assert result["reconstructed_from_q15_patch"] is True
    assert result["runtime_entry_quality_after_patch"] == 0.55
    assert result["entry_quality"] == 0.4181
    assert result["remaining_gap_to_floor"] == 0.1319
    assert result["best_single_component"]["feature"] == "feat_4h_bias50"
    assert result["best_single_component"]["required_score_delta_to_cross_floor"] == 0.4397
    assert result["single_component_floor_crossers"][0]["feature"] == "feat_4h_bias50"


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


def test_live_decision_quality_drilldown_surfaces_recommended_patch_summary(tmp_path, monkeypatch):
    probe_path = tmp_path / "live_predict_probe.json"
    out_json = tmp_path / "live_decision_quality_drilldown.json"
    out_md = tmp_path / "live_decision_quality_drilldown.md"
    q35_path = tmp_path / "q35_scaling_audit.json"
    q35_path.write_text("{}", encoding="utf-8")

    probe_payload = {
        "feature_timestamp": "2026-04-19 07:15:00",
        "target_col": "simulated_pyramid_win",
        "signal": "CIRCUIT_BREAKER",
        "confidence": 0.5,
        "should_trade": False,
        "regime_label": "bull",
        "regime_gate": "BLOCK",
        "entry_quality": 0.3467,
        "entry_quality_label": "D",
        "entry_quality_components": {
            "entry_quality": 0.3467,
            "trade_floor": 0.55,
            "base_quality": 0.3791,
            "base_quality_weight": 0.75,
            "structure_quality": 0.2494,
            "structure_quality_weight": 0.25,
            "base_components": [],
            "structure_components": [],
        },
        "deployment_blocker": "circuit_breaker_active",
        "deployment_blocker_reason": "Consecutive loss streak: 237 >= 50; Recent 50-sample win rate: 0.00% < 30%",
        "deployment_blocker_source": "circuit_breaker",
        "deployment_blocker_details": {
            "recent_window": {"window_size": 50, "wins": 0, "win_rate": 0.0, "floor": 0.3},
            "release_condition": {"required_recent_window_wins": 15, "additional_recent_window_wins_needed": 15},
        },
        "allowed_layers_raw": 0,
        "allowed_layers_raw_reason": "regime_gate_block",
        "allowed_layers": 0,
        "allowed_layers_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active",
        "execution_guardrail_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active",
        "runtime_closure_state": "circuit_breaker_active",
        "runtime_closure_summary": "circuit breaker active",
        "support_route_verdict": "exact_bucket_missing_exact_lane_proxy_only",
        "floor_cross_verdict": "runtime_blocker_preempts_floor_analysis",
        "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
        "q15_exact_supported_component_patch_applied": False,
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "rows": 0,
                "win_rate": None,
                "avg_pnl": None,
                "avg_quality": None,
                "avg_drawdown_penalty": None,
                "avg_time_underwater": None,
                "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                "current_live_structure_bucket_rows": 0,
            },
            "regime_label+entry_quality_label": {
                "rows": 200,
                "win_rate": 0.0,
                "avg_pnl": -0.01,
                "avg_quality": -0.2868,
                "avg_drawdown_penalty": 0.3869,
                "avg_time_underwater": 0.9055,
                "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                "current_live_structure_bucket_rows": 0,
                "spillover_vs_exact_live_lane": {
                    "extra_rows": 200,
                    "extra_row_share": 1.0,
                    "worst_extra_regime_gate": {
                        "regime_gate": "bull|CAUTION",
                        "rows": 113,
                        "win_rate": 0.0,
                        "avg_pnl": -0.0109,
                        "avg_quality": -0.2947,
                        "avg_drawdown_penalty": 0.3817,
                        "avg_time_underwater": 0.818,
                    },
                    "worst_extra_regime_gate_feature_contrast": {
                        "top_mean_shift_features": [
                            {"feature": "feat_4h_bias200", "reference_mean": 7.52, "current_mean": 9.86, "mean_delta": 2.34}
                        ]
                    },
                },
            },
            "pathology_consensus": {
                "shared_top_shift_features": [
                    {"feature": "feat_4h_dist_bb_lower", "scope_count": 2}
                ],
                "worst_pathology_scope": {
                    "scope": "regime_label+entry_quality_label",
                    "rows": 200,
                    "win_rate": 0.0,
                    "avg_quality": -0.2868,
                },
            },
        },
        "decision_quality_scope_pathology_summary": {
            "focus_scope": "regime_label+entry_quality_label",
            "focus_scope_label": "同 regime + quality 寬 scope",
            "focus_scope_rows": 200,
            "summary": "同 regime + quality 寬 scope 出現 bull|CAUTION spillover。",
            "exact_live_lane": {
                "scope": "regime_label+regime_gate+entry_quality_label",
                "rows": 0,
                "win_rate": None,
                "avg_pnl": None,
                "avg_quality": None,
                "avg_drawdown_penalty": None,
                "avg_time_underwater": None,
                "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                "current_live_structure_bucket_rows": 0,
            },
            "spillover": {
                "extra_rows": 200,
                "extra_row_share": 1.0,
                "worst_extra_regime_gate": {
                    "regime_gate": "bull|CAUTION",
                    "rows": 113,
                    "win_rate": 0.0,
                    "avg_pnl": -0.0109,
                    "avg_quality": -0.2947,
                    "avg_drawdown_penalty": 0.3817,
                    "avg_time_underwater": 0.818,
                },
                "top_mean_shift_features": [
                    {"feature": "feat_4h_dist_bb_lower", "reference_mean": 0.81, "current_mean": 3.07, "mean_delta": 2.26}
                ],
            },
            "recommended_patch": {
                "status": "reference_only_until_exact_support_ready",
                "reason": "bull|CAUTION spillover 已有正式 patch 建議（core_plus_macro），目前只能作治理 / 訓練參考，不可直接放行 runtime。",
                "recommended_profile": "core_plus_macro",
                "support_route_verdict": "exact_bucket_missing_exact_lane_proxy_only",
                "gap_to_minimum": 50,
                "collapse_features": [
                    "feat_4h_dist_swing_low",
                    "feat_4h_dist_bb_lower",
                    "feat_4h_bb_pct_b",
                ],
                "recommended_action": "維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。",
            },
        },
    }
    probe_path.write_text(json.dumps(probe_payload, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(live_drilldown, "PROBE_PATH", probe_path)
    monkeypatch.setattr(live_drilldown, "OUT_JSON", out_json)
    monkeypatch.setattr(live_drilldown, "OUT_MD", out_md)
    monkeypatch.setattr(live_drilldown, "Q35_AUDIT_PATH", q35_path)

    live_drilldown.main()

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    markdown = out_md.read_text(encoding="utf-8")

    assert payload["recommended_patch"]["recommended_profile"] == "core_plus_macro"
    assert payload["recommended_patch"]["status"] == "reference_only_until_exact_support_ready"
    assert "recommended_patch: **core_plus_macro**" in markdown
    assert "recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b" in markdown
