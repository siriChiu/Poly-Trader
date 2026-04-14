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
            "exact_scope_metrics": {
                "rows": 14,
                "win_rate": 0.5,
                "avg_pnl": 0.0082,
                "avg_quality": 0.2412,
                "avg_drawdown_penalty": 0.2041,
                "avg_time_underwater": 0.4575,
            },
            "exact_dominant_structure_bucket": {
                "structure_bucket": "ALLOW|base_allow|q85",
                "count": 14,
                "share": 1.0,
            },
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
            "broad_current_live_structure_bucket_rows": 66,
            "broad_recent500_dominant_regime": {"regime": "neutral", "share": 0.8783},
            "broad_current_live_structure_bucket_metrics": {"rows": 66, "win_rate": 0.303},
            "broad_recent_pathology": {
                "summary": {
                    "reference_window_comparison": {
                        "top_mean_shift_features": [
                            {"feature": "feat_4h_dist_swing_low"},
                            {"feature": "feat_4h_dist_bb_lower"},
                        ]
                    }
                }
            },
            "collapse_feature_snapshot": {
                "feat_4h_dist_swing_low": {"mean_delta": -5.9},
            },
        },
        "cohorts": {
            "bull_exact_live_lane_proxy": {"rows": 50},
            "bull_live_exact_lane_bucket_proxy": {
                "rows": 38,
                "base_win_rate": 0.8421,
                "recommended_profile": "core_plus_macro",
                "profiles": {"core_plus_macro": {"cv_mean_accuracy": 0.8333}},
            },
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
    assert summary["exact_bucket_root_cause"] == "cross_regime_spillover_dominates_q65"
    assert summary["bucket_comparison_takeaway"] == "prefer_same_bucket_proxy_over_cross_regime_spillover"
    assert summary["broad_current_live_structure_bucket_rows"] == 66
    assert summary["broad_dominant_regime"] == "neutral"
    assert summary["broader_bucket_pathology_shift_features"] == [
        "feat_4h_dist_swing_low",
        "feat_4h_dist_bb_lower",
    ]
    assert summary["narrowed_pathology_scope"] == "regime_label+entry_quality_label"
    assert summary["pathology_shared_shift_features"] == [
        "feat_4h_dist_swing_low",
        "feat_4h_dist_bb_lower",
    ]
    bucket_cmp = summary["bucket_evidence_comparison"]
    assert bucket_cmp["exact_live_lane"]["bucket"] == "ALLOW|base_allow|q85"
    assert bucket_cmp["exact_live_lane"]["rows"] == 14
    assert bucket_cmp["exact_bucket_proxy"]["rows"] == 38
    assert bucket_cmp["broader_same_bucket"]["rows"] == 66
    assert bucket_cmp["proxy_vs_broader_same_bucket"]["win_rate_delta"] == 0.5391


def test_build_proxy_boundary_diagnostics_prefers_same_bucket_proxy_over_cross_regime_broader_scope():
    frame = bull_4h_pocket_ablation.pd.DataFrame(
        [
            {"regime_label": "bull", "regime_gate": "CAUTION", "entry_quality_label": "D", "structure_bucket": "CAUTION|structure_quality_caution|q35", "feat_4h_bias200": -1.0, "feat_4h_dist_swing_low": 1.0, "feat_4h_dist_bb_lower": 0.2, "feat_4h_bb_pct_b": 0.1},
            {"regime_label": "bull", "regime_gate": "CAUTION", "entry_quality_label": "D", "structure_bucket": "CAUTION|structure_quality_caution|q35", "feat_4h_bias200": -1.1, "feat_4h_dist_swing_low": 1.1, "feat_4h_dist_bb_lower": 0.2, "feat_4h_bb_pct_b": 0.1},
            {"regime_label": "bull", "regime_gate": "CAUTION", "entry_quality_label": "D", "structure_bucket": "CAUTION|structure_quality_caution|q35", "feat_4h_bias200": -1.2, "feat_4h_dist_swing_low": 1.2, "feat_4h_dist_bb_lower": 0.3, "feat_4h_bb_pct_b": 0.1},
            {"regime_label": "bull", "regime_gate": "CAUTION", "entry_quality_label": "D", "structure_bucket": "CAUTION|base_caution_regime_or_bias|q15", "feat_4h_bias200": -0.8, "feat_4h_dist_swing_low": 1.5, "feat_4h_dist_bb_lower": 0.4, "feat_4h_bb_pct_b": 0.2},
            {"regime_label": "chop", "regime_gate": "CAUTION", "entry_quality_label": "D", "structure_bucket": "CAUTION|structure_quality_caution|q35", "feat_4h_bias200": -0.3, "feat_4h_dist_swing_low": 2.0, "feat_4h_dist_bb_lower": 0.8, "feat_4h_bb_pct_b": 0.5},
            {"regime_label": "chop", "regime_gate": "CAUTION", "entry_quality_label": "D", "structure_bucket": "CAUTION|structure_quality_caution|q35", "feat_4h_bias200": -0.2, "feat_4h_dist_swing_low": 2.1, "feat_4h_dist_bb_lower": 0.9, "feat_4h_bb_pct_b": 0.6},
            {"regime_label": "chop", "regime_gate": "CAUTION", "entry_quality_label": "D", "structure_bucket": "CAUTION|structure_quality_caution|q35", "feat_4h_bias200": -0.1, "feat_4h_dist_swing_low": 2.2, "feat_4h_dist_bb_lower": 1.0, "feat_4h_bb_pct_b": 0.7},
        ]
    )
    y = bull_4h_pocket_ablation.pd.Series([1, 1, 1, 0, 0, 0, 0], dtype=float)
    exact_live_lane_mask = (frame["regime_label"] == "bull") & (frame["regime_gate"] == "CAUTION") & (frame["entry_quality_label"] == "D")
    live_bucket_mask = exact_live_lane_mask & (frame["structure_bucket"] == "CAUTION|structure_quality_caution|q35")
    broad_same_bucket_mask = (frame["regime_gate"] == "CAUTION") & (frame["entry_quality_label"] == "D") & (frame["structure_bucket"] == "CAUTION|structure_quality_caution|q35")

    diagnostics = bull_4h_pocket_ablation._build_proxy_boundary_diagnostics(
        frame,
        y,
        live_context={
            "regime_label": "bull",
            "current_live_structure_bucket_rows": 2,
            "exact_scope_rows": 3,
            "broad_current_live_structure_bucket_rows": 4,
            "exact_scope_metrics": {"avg_quality": 0.30},
            "exact_current_live_structure_bucket_metrics": {"avg_quality": 0.70},
            "broad_current_live_structure_bucket_metrics": {"avg_quality": 0.20},
        },
        exact_live_lane_mask=exact_live_lane_mask,
        live_bucket_mask=live_bucket_mask,
        broad_same_bucket_mask=broad_same_bucket_mask,
    )

    assert diagnostics["recent_exact_current_bucket"]["rows"] == 2
    assert diagnostics["historical_exact_bucket_proxy"]["rows"] == 3
    assert diagnostics["recent_broader_same_bucket"]["rows"] == 4
    assert diagnostics["recent_broader_same_bucket"]["dominant_regime"]["regime"] == "chop"
    assert diagnostics["proxy_vs_current_live_bucket"]["win_rate_delta"] == 0.0
    assert diagnostics["proxy_boundary_verdict"] == "proxy_matches_exact_bucket_better_than_cross_regime_broader_scope"


def test_build_exact_lane_bucket_diagnostics_identifies_toxic_sub_bucket():
    frame = bull_4h_pocket_ablation.pd.DataFrame(
        [
            {"structure_bucket": "CAUTION|structure_quality_caution|q35", "feat_4h_bias200": -0.2, "feat_4h_dist_swing_low": 1.0, "feat_4h_dist_bb_lower": 0.2, "feat_4h_bb_pct_b": 0.10},
            {"structure_bucket": "CAUTION|structure_quality_caution|q35", "feat_4h_bias200": -0.3, "feat_4h_dist_swing_low": 1.1, "feat_4h_dist_bb_lower": 0.2, "feat_4h_bb_pct_b": 0.11},
            {"structure_bucket": "CAUTION|structure_quality_caution|q35", "feat_4h_bias200": -0.4, "feat_4h_dist_swing_low": 1.2, "feat_4h_dist_bb_lower": 0.3, "feat_4h_bb_pct_b": 0.12},
            {"structure_bucket": "CAUTION|base_caution_regime_or_bias|q15", "feat_4h_bias200": -1.1, "feat_4h_dist_swing_low": 4.5, "feat_4h_dist_bb_lower": 1.1, "feat_4h_bb_pct_b": 0.55},
            {"structure_bucket": "CAUTION|base_caution_regime_or_bias|q15", "feat_4h_bias200": -1.0, "feat_4h_dist_swing_low": 4.2, "feat_4h_dist_bb_lower": 1.0, "feat_4h_bb_pct_b": 0.50},
            {"structure_bucket": "CAUTION|base_caution_regime_or_bias|q85", "feat_4h_bias200": -0.6, "feat_4h_dist_swing_low": 2.0, "feat_4h_dist_bb_lower": 0.5, "feat_4h_bb_pct_b": 0.20},
        ]
    )
    y = bull_4h_pocket_ablation.pd.Series([1, 1, 1, 0, 0, 1], dtype=float)
    mask = bull_4h_pocket_ablation.pd.Series([True] * len(frame))

    diagnostics = bull_4h_pocket_ablation._build_exact_lane_bucket_diagnostics(
        frame,
        y,
        live_context={
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "exact_recent_structure_bucket_counts": {
                "CAUTION|structure_quality_caution|q35": 3,
                "CAUTION|base_caution_regime_or_bias|q15": 2,
                "CAUTION|base_caution_regime_or_bias|q85": 1,
            },
            "exact_current_live_structure_bucket_metrics": {
                "win_rate": 1.0,
                "avg_pnl": 0.02,
                "avg_quality": 0.65,
                "avg_drawdown_penalty": 0.08,
                "avg_time_underwater": 0.10,
            },
        },
        exact_live_lane_mask=mask,
    )

    assert diagnostics["verdict"] == "toxic_sub_bucket_identified"
    assert diagnostics["toxic_bucket"]["bucket"] == "CAUTION|base_caution_regime_or_bias|q15"
    assert diagnostics["toxic_bucket"]["win_rate"] == 0.0
    assert diagnostics["toxic_bucket"]["vs_current_bucket"]["win_rate_delta"] == -1.0
    assert diagnostics["buckets"]["CAUTION|structure_quality_caution|q35"]["avg_quality"] == 0.65


def test_support_pathology_summary_marks_exact_bucket_supported_when_rows_clear_threshold():
    payload = {
        "live_context": {
            "regime_label": "bull",
            "current_live_structure_bucket": "ALLOW|base_allow|q65",
            "current_live_structure_bucket_rows": 55,
            "broad_current_live_structure_bucket_rows": 55,
            "broad_recent500_dominant_regime": {"regime": "bull", "share": 1.0},
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
    assert summary["exact_bucket_root_cause"] == "exact_bucket_supported"


def test_support_pathology_summary_marks_present_but_under_supported_bucket_gap():
    payload = {
        "live_context": {
            "regime_label": "bull",
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "current_live_structure_bucket_rows": 5,
            "broad_current_live_structure_bucket_rows": 7,
            "broad_recent500_dominant_regime": {"regime": "chop", "share": 0.982},
            "supported_neighbor_buckets": ["CAUTION|base_caution_regime_or_bias|q15"],
            "exact_recent_structure_bucket_counts": {
                "CAUTION|structure_quality_caution|q35": 5,
                "CAUTION|base_caution_regime_or_bias|q15": 7,
            },
        },
        "cohorts": {
            "bull_exact_live_lane_proxy": {"rows": 311},
            "bull_live_exact_lane_bucket_proxy": {"rows": 48},
            "bull_supported_neighbor_buckets_proxy": {"rows": 84},
        },
    }

    summary = bull_4h_pocket_ablation._support_pathology_summary(payload)

    assert summary["blocker_state"] == "exact_lane_proxy_fallback_only"
    assert summary["preferred_support_cohort"] == "bull_exact_live_lane_proxy"
    assert summary["current_live_structure_bucket_gap_to_minimum"] == 45
    assert summary["exact_bucket_root_cause"] == "exact_bucket_present_but_below_minimum"


def test_support_pathology_summary_keeps_under_minimum_blocker_even_if_exact_bucket_proxy_is_ready():
    payload = {
        "live_context": {
            "regime_label": "bull",
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "current_live_structure_bucket_rows": 9,
            "broad_current_live_structure_bucket_rows": 11,
            "broad_recent500_dominant_regime": {"regime": "chop", "share": 0.974},
            "supported_neighbor_buckets": [
                "CAUTION|structure_quality_caution|q15",
                "CAUTION|base_caution_regime_or_bias|q15",
            ],
            "exact_recent_structure_bucket_counts": {
                "CAUTION|structure_quality_caution|q35": 9,
                "CAUTION|structure_quality_caution|q15": 4,
                "CAUTION|base_caution_regime_or_bias|q15": 7,
            },
        },
        "cohorts": {
            "bull_exact_live_lane_proxy": {"rows": 315},
            "bull_live_exact_lane_bucket_proxy": {"rows": 52},
            "bull_supported_neighbor_buckets_proxy": {"rows": 84},
        },
    }

    summary = bull_4h_pocket_ablation._support_pathology_summary(payload)

    assert summary["blocker_state"] == "exact_lane_proxy_fallback_only"
    assert summary["preferred_support_cohort"] == "bull_live_exact_lane_bucket_proxy"
    assert summary["current_live_structure_bucket_gap_to_minimum"] == 41
    assert summary["exact_live_bucket_proxy_gap_to_minimum"] == 0
    assert summary["exact_bucket_root_cause"] == "exact_bucket_present_but_below_minimum"
