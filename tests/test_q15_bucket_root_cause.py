import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_q15_bucket_root_cause.py"
spec = importlib.util.spec_from_file_location("hb_q15_bucket_root_cause_test_module", MODULE_PATH)
q15_bucket_root_cause = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(q15_bucket_root_cause)


def test_build_report_marks_structure_scoring_gap_when_no_exact_lane_boundary_rows(monkeypatch):
    exact_lane_frame = q15_bucket_root_cause.pd.DataFrame(
        {
            "regime_label": ["bull", "bull", "bull"],
            "regime_gate": ["CAUTION", "CAUTION", "CAUTION"],
            "entry_quality_label": ["D", "D", "D"],
            "structure_bucket": [
                "CAUTION|structure_quality_caution|q35",
                "CAUTION|structure_quality_caution|q35",
                "CAUTION|structure_quality_caution|q35",
            ],
            "structure_quality": [0.42, 0.48, 0.51],
            "feat_4h_bb_pct_b": [0.72, 0.84, 0.91],
            "feat_4h_dist_bb_lower": [3.2, 3.9, 4.4],
            "feat_4h_dist_swing_low": [4.3, 4.8, 5.4],
        }
    )

    monkeypatch.setattr(
        q15_bucket_root_cause.feature_group_module,
        "_load_training_frame",
        lambda: (exact_lane_frame[[
            "feat_4h_bb_pct_b",
            "feat_4h_dist_bb_lower",
            "feat_4h_dist_swing_low",
        ]].copy(), q15_bucket_root_cause.pd.Series([1, 1, 1]), exact_lane_frame["regime_label"].copy()),
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.bull_pocket_module,
        "_derive_live_bucket_columns",
        lambda frame: exact_lane_frame.copy(),
    )

    probe = {
        "feature_timestamp": "2026-04-15 08:00:00",
        "target_col": "simulated_pyramid_win",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality_label": "D",
        "non_null_4h_feature_count": 7,
        "execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
        "entry_quality_components": {
            "structure_quality": 0.2813,
            "structure_components": [
                {"feature": "feat_4h_bb_pct_b", "raw_value": 0.2882, "normalized_score": 0.2882, "weighted_contribution": 0.0980},
                {"feature": "feat_4h_dist_bb_lower", "raw_value": 0.9181, "normalized_score": 0.1148, "weighted_contribution": 0.0379},
                {"feature": "feat_4h_dist_swing_low", "raw_value": 4.4066, "normalized_score": 0.4407, "weighted_contribution": 0.1454},
            ],
        },
    }
    bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "live_context": {
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
        },
    }

    report = q15_bucket_root_cause.build_report(probe, {}, bull_pocket)

    assert report["verdict"] == "structure_scoring_gap_not_boundary"
    assert report["candidate_patch_type"] == "structure_component_scoring"
    assert report["exact_live_lane"]["dominant_neighbor_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert report["exact_live_lane"]["near_boundary_rows"] == 0
    assert report["candidate_patch_feature"] in {
        "feat_4h_bb_pct_b",
        "feat_4h_dist_bb_lower",
        "feat_4h_dist_swing_low",
    }
    assert "boundary" in report["reason"]


def test_build_report_marks_projection_issue_when_4h_inputs_missing(monkeypatch):
    empty_frame = q15_bucket_root_cause.pd.DataFrame(
        {
            "regime_label": [],
            "regime_gate": [],
            "entry_quality_label": [],
            "structure_bucket": [],
            "structure_quality": [],
            "feat_4h_bb_pct_b": [],
            "feat_4h_dist_bb_lower": [],
            "feat_4h_dist_swing_low": [],
        }
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.feature_group_module,
        "_load_training_frame",
        lambda: (empty_frame[["feat_4h_bb_pct_b", "feat_4h_dist_bb_lower", "feat_4h_dist_swing_low"]].copy(), q15_bucket_root_cause.pd.Series(dtype=float), q15_bucket_root_cause.pd.Series(dtype=object)),
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.bull_pocket_module,
        "_derive_live_bucket_columns",
        lambda frame: empty_frame.copy(),
    )

    probe = {
        "feature_timestamp": "2026-04-15 08:00:00",
        "target_col": "simulated_pyramid_win",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality_label": "D",
        "non_null_4h_feature_count": 2,
        "entry_quality_components": {
            "structure_quality": None,
            "structure_components": [],
        },
    }
    report = q15_bucket_root_cause.build_report(probe, {}, {"live_context": {"current_live_structure_bucket": "CAUTION|structure_quality_caution|q15"}})

    assert report["verdict"] == "live_row_projection_missing_4h_inputs"
    assert report["candidate_patch_type"] == "live_row_projection"
    assert "投影" in report["reason"]


def test_build_report_marks_stale_when_probe_bucket_differs_from_bull_pocket(monkeypatch):
    exact_lane_frame = q15_bucket_root_cause.pd.DataFrame(
        {
            "regime_label": ["bull", "bull"],
            "regime_gate": ["CAUTION", "CAUTION"],
            "entry_quality_label": ["D", "D"],
            "structure_bucket": [
                "CAUTION|structure_quality_caution|q35",
                "CAUTION|structure_quality_caution|q35",
            ],
            "structure_quality": [0.42, 0.48],
            "feat_4h_bb_pct_b": [0.72, 0.84],
            "feat_4h_dist_bb_lower": [3.2, 3.9],
            "feat_4h_dist_swing_low": [4.3, 4.8],
        }
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.feature_group_module,
        "_load_training_frame",
        lambda: (exact_lane_frame[[
            "feat_4h_bb_pct_b",
            "feat_4h_dist_bb_lower",
            "feat_4h_dist_swing_low",
        ]].copy(), q15_bucket_root_cause.pd.Series([1, 1]), exact_lane_frame["regime_label"].copy()),
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.bull_pocket_module,
        "_derive_live_bucket_columns",
        lambda frame: exact_lane_frame.copy(),
    )

    probe = {
        "feature_timestamp": "2026-04-15 15:48:14",
        "target_col": "simulated_pyramid_win",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality_label": "D",
        "non_null_4h_feature_count": 7,
        "execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            }
        },
        "entry_quality_components": {
            "structure_quality": 0.2813,
            "structure_components": [
                {"feature": "feat_4h_bb_pct_b", "raw_value": 0.2882, "normalized_score": 0.2882, "weighted_contribution": 0.0980},
                {"feature": "feat_4h_dist_bb_lower", "raw_value": 0.9181, "normalized_score": 0.1148, "weighted_contribution": 0.0379},
                {"feature": "feat_4h_dist_swing_low", "raw_value": 4.4066, "normalized_score": 0.4407, "weighted_contribution": 0.1454},
            ],
        },
    }
    bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "live_context": {
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
        },
    }

    report = q15_bucket_root_cause.build_report(probe, {}, bull_pocket)

    assert report["verdict"] == "stale_or_non_current_context"
    assert report["artifact_context_freshness"]["verdict"] == "stale_or_non_current_context"
    assert "current_live_structure_bucket" in report["artifact_context_freshness"]["mismatched_fields"]
    assert report["current_live"]["structure_bucket"] == "CAUTION|structure_quality_caution|q15"
    assert report["exact_live_lane"]["bucket_counts"]["CAUTION|structure_quality_caution|q35"] == 2


def test_build_report_accepts_feature_group_source_meta(monkeypatch):
    exact_lane_frame = q15_bucket_root_cause.pd.DataFrame(
        {
            "regime_label": ["bull", "bull"],
            "regime_gate": ["CAUTION", "CAUTION"],
            "entry_quality_label": ["D", "D"],
            "structure_bucket": [
                "CAUTION|structure_quality_caution|q35",
                "CAUTION|structure_quality_caution|q35",
            ],
            "structure_quality": [0.42, 0.48],
            "feat_4h_bb_pct_b": [0.72, 0.84],
            "feat_4h_dist_bb_lower": [3.2, 3.9],
            "feat_4h_dist_swing_low": [4.3, 4.8],
        }
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.feature_group_module,
        "_load_training_frame",
        lambda: (
            exact_lane_frame[[
                "feat_4h_bb_pct_b",
                "feat_4h_dist_bb_lower",
                "feat_4h_dist_swing_low",
            ]].copy(),
            q15_bucket_root_cause.pd.Series([1, 1]),
            exact_lane_frame["regime_label"].copy(),
            {"target_col": "simulated_pyramid_win"},
        ),
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.bull_pocket_module,
        "_derive_live_bucket_columns",
        lambda frame: exact_lane_frame.copy(),
    )

    probe = {
        "feature_timestamp": "2026-04-17 11:34:13",
        "target_col": "simulated_pyramid_win",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality_label": "D",
        "non_null_4h_feature_count": 7,
        "execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
        "entry_quality_components": {
            "structure_quality": 0.2813,
            "structure_components": [
                {"feature": "feat_4h_bb_pct_b", "raw_value": 0.2882, "normalized_score": 0.2882, "weighted_contribution": 0.0980},
                {"feature": "feat_4h_dist_bb_lower", "raw_value": 0.9181, "normalized_score": 0.1148, "weighted_contribution": 0.0379},
                {"feature": "feat_4h_dist_swing_low", "raw_value": 4.4066, "normalized_score": 0.4407, "weighted_contribution": 0.1454},
            ],
        },
        "decision_quality_scope_diagnostics": {
            "regime_label+regime_gate+entry_quality_label": {
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            }
        },
    }

    report = q15_bucket_root_cause.build_report(probe, {}, {"live_context": {"current_live_structure_bucket": "CAUTION|structure_quality_caution|q15"}})

    assert report["current_live"]["structure_bucket"] == "CAUTION|structure_quality_caution|q15"
    assert report["exact_live_lane"]["rows"] == 2


def test_build_report_reports_current_exact_support_under_minimum_instead_of_boundary_review(monkeypatch):
    buckets = (
        ["BLOCK|bull_q15_bias50_overextended_block|q15"] * 10
        + ["BLOCK|bull_q15_bias50_overextended_block|q35"] * 40
    )
    exact_lane_frame = q15_bucket_root_cause.pd.DataFrame(
        {
            "regime_label": ["bull"] * 50,
            "regime_gate": ["BLOCK"] * 50,
            "entry_quality_label": ["D"] * 50,
            "structure_bucket": buckets,
            "structure_quality": [0.22] * 10 + [0.41] * 40,
            "feat_4h_bb_pct_b": [0.31] * 50,
            "feat_4h_dist_bb_lower": [1.4] * 50,
            "feat_4h_dist_swing_low": [2.8] * 50,
        }
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.feature_group_module,
        "_load_training_frame",
        lambda: (exact_lane_frame[[
            "feat_4h_bb_pct_b",
            "feat_4h_dist_bb_lower",
            "feat_4h_dist_swing_low",
        ]].copy(), q15_bucket_root_cause.pd.Series([1] * 50), exact_lane_frame["regime_label"].copy()),
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.bull_pocket_module,
        "_derive_live_bucket_columns",
        lambda frame: exact_lane_frame.copy(),
    )

    probe = {
        "feature_timestamp": "2026-04-24 08:02:34",
        "target_col": "simulated_pyramid_win",
        "regime_label": "bull",
        "regime_gate": "BLOCK",
        "entry_quality_label": "D",
        "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
        "support_route_verdict": "exact_bucket_present_but_below_minimum",
        "support_progress": {
            "status": "semantic_rebaseline_under_minimum",
            "current_rows": 10,
            "minimum_support_rows": 50,
            "gap_to_minimum": 40,
            "regression_basis": "legacy_or_different_semantic_signature",
        },
        "non_null_4h_feature_count": 7,
        "entry_quality_components": {
            "structure_quality": 0.22,
            "structure_components": [
                {"feature": "feat_4h_bb_pct_b", "raw_value": 0.31, "weighted_contribution": 0.1054},
                {"feature": "feat_4h_dist_bb_lower", "raw_value": 1.4, "weighted_contribution": 0.0578},
                {"feature": "feat_4h_dist_swing_low", "raw_value": 2.8, "weighted_contribution": 0.0924},
            ],
        },
    }
    drilldown = {
        "component_gap_attribution": {
            "remaining_gap_to_floor": 0.044,
            "best_single_component": {"feature": "feat_4h_bias50"},
        }
    }
    bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "live_context": {
            "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
            "regime_label": "bull",
            "regime_gate": "BLOCK",
            "entry_quality_label": "D",
        },
    }

    report = q15_bucket_root_cause.build_report(probe, drilldown, bull_pocket)

    assert report["verdict"] == "current_exact_support_under_minimum"
    assert report["candidate_patch_type"] == "support_accumulation_or_semantic_rebaseline"
    assert report["candidate_patch_feature"] is None
    assert report["current_live"]["support_current_rows"] == 10
    assert report["current_live"]["support_gap_to_minimum"] == 40
    assert report["exact_live_lane"]["bucket_counts"]["BLOCK|bull_q15_bias50_overextended_block|q15"] == 10
    assert report["floor_gap_attribution"]["remaining_gap_to_floor"] == 0.044
    assert "不是 boundary candidate" in report["reason"]


def test_build_report_does_not_let_stale_reference_bull_context_hide_current_support_truth(monkeypatch):
    exact_lane_frame = q15_bucket_root_cause.pd.DataFrame(
        {
            "regime_label": ["bull"] * 4,
            "regime_gate": ["CAUTION"] * 4,
            "entry_quality_label": ["D"] * 4,
            "structure_bucket": [
                "CAUTION|structure_quality_caution|q15",
                "CAUTION|structure_quality_caution|q15",
                "CAUTION|structure_quality_caution|q35",
                "CAUTION|structure_quality_caution|q35",
            ],
            "structure_quality": [0.31, 0.32, 0.41, 0.44],
            "feat_4h_bb_pct_b": [0.41, 0.42, 0.62, 0.65],
            "feat_4h_dist_bb_lower": [1.3, 1.4, 3.1, 3.3],
            "feat_4h_dist_swing_low": [3.6, 3.7, 4.8, 4.9],
        }
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.feature_group_module,
        "_load_training_frame",
        lambda: (
            exact_lane_frame[[
                "feat_4h_bb_pct_b",
                "feat_4h_dist_bb_lower",
                "feat_4h_dist_swing_low",
            ]].copy(),
            q15_bucket_root_cause.pd.Series([1] * 4),
            exact_lane_frame["regime_label"].copy(),
        ),
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.bull_pocket_module,
        "_derive_live_bucket_columns",
        lambda frame: exact_lane_frame.copy(),
    )

    probe = {
        "feature_timestamp": "2026-04-24 10:33:44.629444",
        "target_col": "simulated_pyramid_win",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality_label": "D",
        "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
        "current_live_structure_bucket_rows": 2,
        "minimum_support_rows": 50,
        "support_route_verdict": "exact_bucket_present_but_below_minimum",
        "support_progress": {
            "status": "semantic_rebaseline_under_minimum",
            "current_rows": 2,
            "minimum_support_rows": 50,
            "gap_to_minimum": 48,
        },
        "non_null_4h_feature_count": 10,
        "entry_quality_components": {
            "structure_quality": 0.3167,
            "structure_components": [
                {"feature": "feat_4h_bb_pct_b", "raw_value": 0.4171, "weighted_contribution": 0.1418},
                {"feature": "feat_4h_dist_bb_lower", "raw_value": 1.3163, "weighted_contribution": 0.0543},
                {"feature": "feat_4h_dist_swing_low", "raw_value": 3.6548, "weighted_contribution": 0.1206},
            ],
        },
    }
    drilldown = {"generated_at": "2026-04-24 10:33:44.629444"}
    stale_bull_pocket = {
        "target_col": "simulated_pyramid_win",
        "live_context": {
            "current_live_structure_bucket": "BLOCK|bull_high_bias200_overheat_block|q35",
            "regime_label": "bull",
            "regime_gate": "BLOCK",
            "entry_quality_label": "D",
        },
    }

    report = q15_bucket_root_cause.build_report(probe, drilldown, stale_bull_pocket)

    assert report["artifact_context_freshness"]["verdict"] == "current_context"
    assert report["artifact_context_freshness"]["mismatched_fields"] == []
    assert "current_live_structure_bucket" in report["artifact_context_freshness"]["reference_mismatched_fields"]
    assert "regime_gate" in report["artifact_context_freshness"]["reference_mismatched_fields"]
    assert report["verdict"] == "current_exact_support_under_minimum"
    assert report["current_live"]["support_current_rows"] == 2
    assert report["current_live"]["support_gap_to_minimum"] == 48


def test_build_report_marks_runtime_blocker_preempt_when_circuit_breaker_active(monkeypatch):
    empty_frame = q15_bucket_root_cause.pd.DataFrame(
        {
            "regime_label": [],
            "regime_gate": [],
            "entry_quality_label": [],
            "structure_bucket": [],
            "structure_quality": [],
            "feat_4h_bb_pct_b": [],
            "feat_4h_dist_bb_lower": [],
            "feat_4h_dist_swing_low": [],
        }
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.feature_group_module,
        "_load_training_frame",
        lambda: (empty_frame[["feat_4h_bb_pct_b", "feat_4h_dist_bb_lower", "feat_4h_dist_swing_low"]].copy(), q15_bucket_root_cause.pd.Series(dtype=float), q15_bucket_root_cause.pd.Series(dtype=object)),
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.bull_pocket_module,
        "_derive_live_bucket_columns",
        lambda frame: empty_frame.copy(),
    )

    probe = {
        "feature_timestamp": "2026-04-17 11:34:13",
        "target_col": "simulated_pyramid_win",
        "signal": "CIRCUIT_BREAKER",
        "deployment_blocker": "circuit_breaker_active",
        "deployment_blocker_source": "circuit_breaker",
        "execution_guardrail_reason": "circuit_breaker_blocks_trade",
        "regime_label": "bull",
        "regime_gate": None,
        "entry_quality_label": None,
        "non_null_4h_feature_count": 7,
        "entry_quality_components": {
            "structure_quality": None,
            "structure_components": [],
        },
    }

    report = q15_bucket_root_cause.build_report(probe, {}, {"live_context": {"current_live_structure_bucket": "CAUTION|structure_quality_caution|q15"}})

    assert report["verdict"] == "runtime_blocker_preempts_bucket_root_cause"
    assert report["candidate_patch_type"] is None
    assert "circuit breaker" in report["reason"]
    assert "canonical breaker" in report["verify_next"]


def test_build_report_stops_support_accumulation_copy_after_exact_support_closure(monkeypatch):
    empty_frame = q15_bucket_root_cause.pd.DataFrame(
        {
            "regime_label": [],
            "regime_gate": [],
            "entry_quality_label": [],
            "structure_bucket": [],
            "structure_quality": [],
            "feat_4h_bb_pct_b": [],
            "feat_4h_dist_bb_lower": [],
            "feat_4h_dist_swing_low": [],
        }
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.feature_group_module,
        "_load_training_frame",
        lambda: (
            empty_frame[["feat_4h_bb_pct_b", "feat_4h_dist_bb_lower", "feat_4h_dist_swing_low"]].copy(),
            q15_bucket_root_cause.pd.Series(dtype=float),
            q15_bucket_root_cause.pd.Series(dtype=object),
        ),
    )
    monkeypatch.setattr(
        q15_bucket_root_cause.bull_pocket_module,
        "_derive_live_bucket_columns",
        lambda frame: empty_frame.copy(),
    )

    probe = {
        "feature_timestamp": "2026-04-22 02:34:04",
        "target_col": "simulated_pyramid_win",
        "signal": "HOLD",
        "deployment_blocker": "decision_quality_below_trade_floor",
        "execution_guardrail_reason": "decision_quality_below_trade_floor",
        "support_route_verdict": "exact_bucket_supported",
        "support_progress": {
            "status": "exact_supported",
            "current_rows": 69,
            "minimum_support_rows": 50,
            "gap_to_minimum": 0,
        },
        "current_live_structure_bucket_rows": 69,
        "minimum_support_rows": 50,
        "current_live_structure_bucket_gap_to_minimum": 0,
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality_label": "C",
        "non_null_4h_feature_count": 7,
        "entry_quality_components": {
            "structure_quality": 0.5716,
            "structure_components": [
                {"feature": "feat_4h_bb_pct_b", "raw_value": 0.9160, "normalized_score": 0.9160, "weighted_contribution": 0.3114},
                {"feature": "feat_4h_dist_bb_lower", "raw_value": 2.8195, "normalized_score": 0.3524, "weighted_contribution": 0.1163},
                {"feature": "feat_4h_dist_swing_low", "raw_value": 4.3585, "normalized_score": 0.4358, "weighted_contribution": 0.1438},
            ],
        },
    }

    report = q15_bucket_root_cause.build_report(
        probe,
        {},
        {"live_context": {"current_live_structure_bucket": "CAUTION|structure_quality_caution|q35"}},
    )

    assert report["verdict"] == "current_bucket_exact_support_already_closed"
    assert report["candidate_patch_type"] == "deployment_blocker_verification"
    assert report["candidate_patch_feature"] is None
    assert report["candidate_patch"] is None
    assert "69/50" in report["reason"]
    assert "decision_quality_below_trade_floor" in report["verify_next"]
    assert "minimum_support_rows" in report["verify_next"]
