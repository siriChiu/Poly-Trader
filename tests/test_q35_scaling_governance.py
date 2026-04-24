from scripts import hb_parallel_runner
from scripts import hb_q35_scaling_audit


def _base_component(feature: str, score: float) -> dict:
    return {"feature": feature, "normalized_score": score}


def _lane_row(label: int, *, bias50: float, nose: float, pulse: float, ear: float) -> dict:
    return {
        "simulated_pyramid_win": label,
        "entry_quality_components": {
            "base_components": [
                _base_component("feat_4h_bias50", bias50),
                _base_component("feat_nose", nose),
                _base_component("feat_pulse", pulse),
                _base_component("feat_ear", ear),
            ]
        },
    }


def test_q35_base_stack_redesign_separates_score_floor_cross_from_execution_closure():
    runtime_current = {
        "regime_gate": "BLOCK",
        "allowed_layers_raw": 0,
        "entry_quality": 0.4269,
        "entry_quality_components": {
            "trade_floor": 0.55,
            "structure_quality": 0.4252,
            "base_components": [
                _base_component("feat_4h_bias50", 0.0),
                _base_component("feat_nose", 0.4686),
                _base_component("feat_pulse", 0.7221),
                _base_component("feat_ear", 0.988),
            ],
        },
    }
    runtime_exact_lane = [
        _lane_row(1, bias50=0.0, nose=0.64, pulse=0.40, ear=0.94),
        _lane_row(1, bias50=0.0, nose=0.62, pulse=0.43, ear=0.95),
        _lane_row(0, bias50=0.0, nose=0.58, pulse=0.42, ear=0.93),
        _lane_row(0, bias50=0.0, nose=0.57, pulse=0.44, ear=0.94),
    ]

    result = hb_q35_scaling_audit._build_base_stack_redesign_experiment(
        runtime_current,
        runtime_exact_lane,
    )

    assert result["verdict"] == "base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked"
    assert result["best_discriminative_candidate"]["entry_quality_ge_trade_floor"] is True
    assert result["best_discriminative_candidate"]["allowed_layers_gt_0"] is False
    assert result["machine_read_answer"] == {
        "entry_quality_ge_0_55": True,
        "allowed_layers_gt_0": False,
        "positive_discriminative_gap": True,
        "execution_blocked_after_floor_cross": True,
    }
    assert "runtime gate/support" in result["reason"]


def test_q35_doc_line_shows_score_floor_cross_is_not_deployment_closure():
    issue = {
        "summary": {
            "overall_verdict": "bias50_formula_may_be_too_harsh",
            "redesign_verdict": "base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked",
            "runtime_remaining_gap_to_floor": 0.1231,
            "redesign_entry_quality": 0.5551,
            "redesign_allowed_layers_after": 0,
            "redesign_positive_discriminative_gap": True,
            "redesign_execution_blocked_after_floor_cross": True,
        }
    }

    line = hb_parallel_runner._q35_scaling_doc_line(issue)

    assert "runtime_gap_to_floor=0.1231" in line
    assert "redesign_entry_quality=0.5551" in line
    assert "redesign_allowed_layers=0" in line
    assert "positive_discriminative_gap=True" in line
    assert "execution_blocked_after_floor_cross=True" in line
    assert "： /" not in line
