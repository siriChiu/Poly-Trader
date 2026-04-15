import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_q15_support_audit.py"
spec = importlib.util.spec_from_file_location("hb_q15_support_audit_test_module", MODULE_PATH)
q15_support_audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(q15_support_audit)


def test_support_route_decision_marks_proxy_reference_only_when_exact_bucket_missing():
    result = q15_support_audit._support_route_decision(
        current_bucket_rows=0,
        minimum_support_rows=50,
        exact_bucket_proxy_rows=4,
        exact_lane_proxy_rows=418,
        supported_neighbor_rows=155,
        exact_bucket_root_cause="same_lane_shifted_to_neighbor_bucket",
        preferred_support_cohort="bull_exact_live_lane_proxy",
        support_governance_route="exact_live_bucket_proxy_available",
    )

    assert result["verdict"] == "exact_bucket_missing_proxy_reference_only"
    assert result["deployable"] is False
    assert result["governance_reference_only"] is True
    assert result["preferred_support_cohort"] == "bull_live_exact_bucket_proxy"


def test_floor_cross_legality_blocks_component_release_when_support_missing():
    support_route = {
        "deployable": False,
    }
    best_single_component = {
        "feature": "feat_4h_bias50",
        "can_single_component_cross_floor": True,
        "required_score_delta_to_cross_floor": 0.066,
    }

    result = q15_support_audit._floor_cross_legality(
        support_route=support_route,
        runtime_blocker=None,
        remaining_gap_to_floor=0.0198,
        best_single_component=best_single_component,
    )

    assert result["verdict"] == "math_cross_possible_but_illegal_without_exact_support"
    assert result["legal_to_relax_runtime_gate"] is False
    assert "feat_4h_bias50" in result["reason"]


def test_build_report_combines_support_route_and_floor_cross_legality():
    probe = {
        "feature_timestamp": "2026-04-15 07:03:58",
        "target_col": "simulated_pyramid_win",
        "signal": "HOLD",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality": 0.5302,
        "entry_quality_label": "D",
        "decision_quality_label": "B",
        "allowed_layers": 0,
        "allowed_layers_reason": "entry_quality_below_trade_floor",
        "execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
    }
    drilldown = {
        "component_gap_attribution": {
            "remaining_gap_to_floor": 0.0198,
            "best_single_component": {
                "feature": "feat_4h_bias50",
                "required_score_delta_to_cross_floor": 0.066,
                "can_single_component_cross_floor": True,
            }
        }
    }
    bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "live_context": {
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "current_live_structure_bucket_rows": 0,
        },
        "support_pathology_summary": {
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "exact_bucket_root_cause": "same_lane_shifted_to_neighbor_bucket",
            "preferred_support_cohort": "bull_exact_live_lane_proxy",
            "recommended_action": "維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。",
        },
    }
    leaderboard_probe = {
        "alignment": {
            "support_governance_route": "exact_live_bucket_proxy_available",
            "bull_exact_live_bucket_proxy_rows": 4,
            "bull_exact_live_lane_proxy_rows": 418,
            "bull_support_neighbor_rows": 155,
        }
    }

    report = q15_support_audit.build_report(probe, drilldown, bull_pocket, leaderboard_probe)

    assert report["support_route"]["verdict"] == "exact_bucket_missing_proxy_reference_only"
    assert report["support_route"]["deployable"] is False
    assert report["support_route"]["preferred_support_cohort"] == "bull_live_exact_bucket_proxy"
    assert report["floor_cross_legality"]["verdict"] == "math_cross_possible_but_illegal_without_exact_support"
    assert report["floor_cross_legality"]["best_single_component"] == "feat_4h_bias50"
