import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "bull_4h_pocket_ablation.py"
spec = importlib.util.spec_from_file_location("bull_4h_pocket_ablation_test_module", MODULE_PATH)
bull_4h_pocket_ablation = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bull_4h_pocket_ablation)


def test_support_pathology_summary_surfaces_exact_bucket_gap_and_proxy_fallback():
    payload = {
        "live_context": {
            "current_live_structure_bucket": "ALLOW|base_allow|q65",
            "current_live_structure_bucket_rows": 0,
            "supported_neighbor_buckets": ["ALLOW|base_allow|q85"],
            "exact_recent_structure_bucket_counts": {
                "ALLOW|base_allow|q85": 14,
                "ALLOW|base_allow|q65": 0,
            },
            "decision_quality_calibration_scope": "regime_label",
            "decision_quality_label": "D",
            "decision_quality_scope_guardrail_applied": True,
            "decision_quality_scope_guardrail_reason": "dominant recent regime mismatch",
            "decision_quality_narrowed_pathology_scope": "regime_label+entry_quality_label",
            "decision_quality_narrowed_pathology_reason": "same-bucket pathology",
            "pathology_worst_scope": "regime_label+entry_quality_label",
            "pathology_shared_shift_features": [
                "feat_4h_dist_swing_low",
                "feat_4h_dist_bb_lower",
            ],
            "collapse_feature_snapshot": {
                "feat_4h_dist_swing_low": {"mean_delta": -5.9},
            },
        },
        "cohorts": {
            "bull_exact_live_lane_proxy": {"rows": 50},
            "bull_live_exact_lane_bucket_proxy": {"rows": 38},
            "bull_supported_neighbor_buckets_proxy": {"rows": 12},
        },
    }

    summary = bull_4h_pocket_ablation._support_pathology_summary(payload)

    assert summary["blocker_state"] == "exact_lane_proxy_fallback_only"
    assert summary["preferred_support_cohort"] == "bull_exact_live_lane_proxy"
    assert summary["current_live_structure_bucket_gap_to_minimum"] == 50
    assert summary["exact_live_bucket_proxy_gap_to_minimum"] == 12
    assert summary["exact_live_lane_proxy_gap_to_minimum"] == 0
    assert summary["dominant_neighbor_bucket"] == "ALLOW|base_allow|q85"
    assert summary["bucket_gap_vs_dominant_neighbor"] == 14
    assert summary["narrowed_pathology_scope"] == "regime_label+entry_quality_label"
    assert summary["pathology_shared_shift_features"] == [
        "feat_4h_dist_swing_low",
        "feat_4h_dist_bb_lower",
    ]


def test_support_pathology_summary_marks_exact_bucket_supported_when_rows_clear_threshold():
    payload = {
        "live_context": {
            "current_live_structure_bucket": "ALLOW|base_allow|q65",
            "current_live_structure_bucket_rows": 55,
            "supported_neighbor_buckets": [],
            "exact_recent_structure_bucket_counts": {
                "ALLOW|base_allow|q65": 55,
            },
        },
        "cohorts": {
            "bull_exact_live_lane_proxy": {"rows": 80},
            "bull_live_exact_lane_bucket_proxy": {"rows": 55},
            "bull_supported_neighbor_buckets_proxy": {"rows": 0},
        },
    }

    summary = bull_4h_pocket_ablation._support_pathology_summary(payload)

    assert summary["blocker_state"] == "exact_live_bucket_supported"
    assert summary["preferred_support_cohort"] == "exact_live_bucket"
    assert summary["current_live_structure_bucket_gap_to_minimum"] == 0
    assert summary["bucket_gap_vs_dominant_neighbor"] == 0
