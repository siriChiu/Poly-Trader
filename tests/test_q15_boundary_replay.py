import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_q15_boundary_replay.py"
spec = importlib.util.spec_from_file_location("hb_q15_boundary_replay_test_module", MODULE_PATH)
q15_boundary_replay = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(q15_boundary_replay)


def test_build_report_marks_boundary_as_relabel_when_support_is_preexisting_q35():
    probe = {
        "feature_timestamp": "2026-04-15 08:22:43",
        "target_col": "simulated_pyramid_win",
        "signal": "HOLD",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality": 0.4352,
        "entry_quality_label": "D",
        "decision_quality_calibration_scope": "regime_label+regime_gate+entry_quality_label",
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "recent500_structure_bucket_counts": {
                    "CAUTION|structure_quality_caution|q35": 76,
                }
            }
        },
        "entry_quality_components": {
            "base_quality": 0.4675,
            "structure_quality": 0.3384,
            "trade_floor_gap": -0.1148,
            "structure_components": [
                {"feature": "feat_4h_bb_pct_b", "raw_value": 0.3943},
            ],
        },
    }
    support_audit = {
        "target_col": "simulated_pyramid_win",
        "current_live": {
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "current_live_structure_bucket_rows": 0,
        },
        "support_route": {"verdict": "exact_bucket_missing_proxy_reference_only"},
        "floor_cross_legality": {"verdict": "math_cross_possible_but_illegal_without_exact_support"},
    }
    root_cause = {
        "target_col": "simulated_pyramid_win",
        "current_live": {
            "structure_bucket": "CAUTION|structure_quality_caution|q15",
            "structure_quality": 0.3384,
            "q35_threshold": 0.35,
        },
        "exact_live_lane": {
            "dominant_neighbor_bucket": "CAUTION|structure_quality_caution|q35",
            "dominant_neighbor_rows": 158,
            "near_boundary_rows": 2,
        },
        "verdict": "boundary_sensitivity_candidate",
        "candidate_patch": {
            "needed_raw_delta_to_cross_q35": 0.0341,
        },
    }

    report = q15_boundary_replay.build_report(probe, support_audit, root_cause)

    assert report["verdict"] == "boundary_relabels_into_existing_q35_support"
    assert report["boundary_replay"]["replay_scope_bucket_rows"] == 76
    assert report["boundary_replay"]["generated_rows_via_boundary_only"] == 2
    assert report["boundary_replay"]["preexisting_rows_in_replay_bucket"] == 74
    assert report["component_counterfactual"]["verdict"] == "bucket_proxy_only_not_trade_floor_fix"
    assert report["component_counterfactual"]["allowed_layers_after"] == 0


def test_build_report_handles_missing_inputs():
    report = q15_boundary_replay.build_report({}, {}, {})

    assert report["verdict"] == "missing_inputs"
    assert "缺少" in report["reason"]
