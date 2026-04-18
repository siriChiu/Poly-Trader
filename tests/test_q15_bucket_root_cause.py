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


def test_build_report_prefers_probe_bucket_over_stale_bull_pocket_bucket(monkeypatch):
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

    report = q15_bucket_root_cause.build_report(probe, {}, {"live_context": {"current_live_structure_bucket": "CAUTION|structure_quality_caution|q35"}})

    assert report["current_live"]["structure_bucket"] == "CAUTION|structure_quality_caution|q15"
    assert report["exact_live_lane"]["rows"] == 2


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
