import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.live_pathology_summary import (
    build_live_pathology_patch_summary,
    build_live_pathology_scope_summary,
    build_live_pathology_scope_surface,
)


def _write_bull_patch_artifact(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-19T00:32:00Z",
                "collapse_features": [
                    "feat_4h_dist_swing_low",
                    "feat_4h_dist_bb_lower",
                    "feat_4h_bb_pct_b",
                ],
                "support_pathology_summary": {
                    "preferred_support_cohort": "bull_exact_live_lane_proxy",
                    "minimum_support_rows": 50,
                    "current_live_structure_bucket_rows": 0,
                    "current_live_structure_bucket_gap_to_minimum": 50,
                    "recommended_action": "維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。",
                },
                "cohorts": {
                    "bull_collapse_q35": {
                        "rows": 473,
                        "base_win_rate": 0.7463,
                        "recommended_profile": "core_plus_macro",
                        "profiles": {
                            "core_plus_macro": {
                                "cv_mean_accuracy": 0.0385,
                            }
                        },
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_build_live_pathology_scope_surface_preserves_artifact_patch_when_live_spillover_turns_block_only(tmp_path):
    artifact_path = tmp_path / "bull_4h_pocket_ablation.json"
    _write_bull_patch_artifact(artifact_path)

    confidence_payload = {
        "regime_label": "bull",
        "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
        "support_route_verdict": "exact_bucket_missing_exact_lane_proxy_only",
        "support_route_deployable": False,
        "support_progress": {
            "current_rows": 0,
            "minimum_support_rows": 50,
            "gap_to_minimum": 50,
        },
    }
    scope_diagnostics = {
        "regime_label+regime_gate+entry_quality_label": {
            "rows": 199,
            "win_rate": 0.0,
            "avg_pnl": -0.01,
            "avg_quality": -0.285,
            "avg_drawdown_penalty": 0.3788,
            "avg_time_underwater": 0.8455,
            "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
            "current_live_structure_bucket_rows": 0,
        },
        "regime_label": {
            "rows": 200,
            "win_rate": 0.0,
            "avg_pnl": -0.01,
            "avg_quality": -0.2852,
            "avg_drawdown_penalty": 0.3786,
            "avg_time_underwater": 0.8432,
            "spillover_vs_exact_live_lane": {
                "extra_rows": 1,
                "extra_row_share": 0.005,
                "win_rate_delta_vs_exact": 0.0,
                "avg_pnl_delta_vs_exact": 0.0,
                "avg_quality_delta_vs_exact": -0.0002,
                "avg_drawdown_penalty_delta_vs_exact": -0.0002,
                "avg_time_underwater_delta_vs_exact": -0.0023,
                "worst_extra_regime_gate": {
                    "regime_gate": "bull|BLOCK",
                    "regime": "bull",
                    "gate": "BLOCK",
                    "rows": 1,
                    "win_rate": 0.0,
                    "avg_pnl": -0.0164,
                    "avg_quality": -0.3135,
                    "avg_drawdown_penalty": 0.3432,
                    "avg_time_underwater": 0.3957,
                },
                "worst_extra_regime_gate_feature_contrast": {
                    "top_mean_shift_features": [
                        {
                            "feature": "feat_4h_bias200",
                            "reference_mean": 10.0304,
                            "current_mean": 9.632,
                            "mean_delta": -0.3984,
                        }
                    ]
                },
            },
        },
    }

    summary = build_live_pathology_scope_surface(
        confidence_payload,
        scope_diagnostics,
        artifact_path=artifact_path,
    )

    assert summary["spillover"]["worst_extra_regime_gate"]["regime_gate"] == "bull|BLOCK"
    patch = summary["recommended_patch"]
    assert patch["recommended_profile"] == "core_plus_macro"
    assert patch["status"] == "reference_only_until_exact_support_ready"
    assert patch["support_route_verdict"] == "exact_bucket_missing_exact_lane_proxy_only"
    assert patch["gap_to_minimum"] == 50
    assert patch["collapse_features"] == [
        "feat_4h_dist_swing_low",
        "feat_4h_dist_bb_lower",
        "feat_4h_bb_pct_b",
    ]
    assert patch["spillover_regime_gate"] == "bull|BLOCK"
    assert patch["reference_patch_scope"] == "bull|CAUTION"
    assert patch["reference_source"] == "bull_4h_pocket_ablation.bull_collapse_q35"


def test_build_live_pathology_patch_summary_treats_string_false_support_route_as_not_deployable(tmp_path):
    artifact_path = tmp_path / "bull_4h_pocket_ablation.json"
    _write_bull_patch_artifact(artifact_path)

    confidence_payload = {
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
        "support_route_verdict": "exact_bucket_supported",
        "support_route_deployable": "false",
        "support_progress": {
            "current_rows": 70,
            "minimum_support_rows": 50,
            "gap_to_minimum": 0,
        },
    }
    scope_summary = {
        "focus_scope": "regime_label",
        "focus_scope_label": "同 regime 寬 scope",
        "spillover": {
            "extra_rows": 70,
            "worst_extra_regime_gate": {
                "regime_gate": "bull|CAUTION",
                "rows": 70,
                "win_rate": 0.42,
                "avg_pnl": -0.001,
                "avg_quality": 0.03,
            },
        },
        "exact_live_lane": {
            "rows": 70,
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "current_live_structure_bucket_rows": 70,
        },
    }

    patch = build_live_pathology_patch_summary(
        confidence_payload,
        scope_summary,
        artifact_path=artifact_path,
    )

    assert patch is not None
    assert patch["support_route_deployable"] is False
    assert patch["status"] == "reference_only_until_exact_support_ready"
    assert patch["reference_only_cause"] == "exact_support_not_ready"


def test_build_live_pathology_scope_surface_marks_patch_reference_only_when_live_scope_differs_even_if_support_is_missing(tmp_path):
    artifact_path = tmp_path / "bull_4h_pocket_ablation.json"
    _write_bull_patch_artifact(artifact_path)

    confidence_payload = {
        "regime_label": "chop",
        "regime_gate": "CAUTION",
        "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
        "support_route_verdict": "exact_bucket_missing_exact_lane_proxy_only",
        "support_route_deployable": False,
        "support_progress": {
            "current_rows": 0,
            "minimum_support_rows": 50,
            "gap_to_minimum": 50,
        },
    }
    scope_diagnostics = {
        "regime_label+regime_gate+entry_quality_label": {
            "rows": 0,
            "win_rate": None,
            "avg_pnl": None,
            "avg_quality": None,
            "avg_drawdown_penalty": None,
            "avg_time_underwater": None,
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
            "current_live_structure_bucket_rows": 0,
        },
        "entry_quality_label": {
            "rows": 199,
            "win_rate": 0.0,
            "avg_pnl": -0.0099,
            "avg_quality": -0.2854,
            "avg_drawdown_penalty": 0.381,
            "avg_time_underwater": 0.8503,
            "spillover_vs_exact_live_lane": {
                "extra_rows": 199,
                "extra_row_share": 1.0,
                "win_rate_delta_vs_exact": None,
                "avg_pnl_delta_vs_exact": None,
                "avg_quality_delta_vs_exact": None,
                "avg_drawdown_penalty_delta_vs_exact": None,
                "avg_time_underwater_delta_vs_exact": None,
                "worst_extra_regime_gate": {
                    "regime_gate": "bull|BLOCK",
                    "regime": "bull",
                    "gate": "BLOCK",
                    "rows": 199,
                    "win_rate": 0.0,
                    "avg_pnl": -0.0099,
                    "avg_quality": -0.2854,
                    "avg_drawdown_penalty": 0.381,
                    "avg_time_underwater": 0.8503,
                },
                "worst_extra_regime_gate_feature_contrast": {
                    "top_mean_shift_features": [
                        {
                            "feature": "feat_4h_bias200",
                            "reference_mean": 7.2021,
                            "current_mean": 9.9266,
                            "mean_delta": 2.7245,
                        }
                    ]
                },
            },
        },
    }

    summary = build_live_pathology_scope_surface(
        confidence_payload,
        scope_diagnostics,
        artifact_path=artifact_path,
    )

    patch = summary["recommended_patch"]
    assert summary["focus_scope"] == "entry_quality_label"
    assert summary["spillover"]["worst_extra_regime_gate"]["regime_gate"] == "bull|BLOCK"
    assert patch["status"] == "reference_only_non_current_live_scope"
    assert patch["reference_only_cause"] == "non_current_live_scope"
    assert patch["patch_scope_matches_live"] is False
    assert patch["current_live_regime_gate"] == "chop|CAUTION"
    assert patch["recommended_profile"] == "core_plus_macro"
    assert patch["spillover_regime_gate"] == "bull|BLOCK"
    assert patch["reference_patch_scope"] == "bull|CAUTION"
    assert patch["reference_source"] == "bull_4h_pocket_ablation.bull_collapse_q35"
    assert patch["current_live_structure_bucket"] == "CAUTION|base_caution_regime_or_bias|q15"
    assert patch["current_live_structure_bucket_rows"] == 0
    assert patch["gap_to_minimum"] == 50
    assert "current live scope 是 chop|CAUTION" in patch["reason"]
    assert "只可作治理 / 訓練參考" in patch["recommended_action"]


def test_build_live_pathology_patch_summary_keeps_spillover_patch_reference_only_when_live_scope_differs(tmp_path):
    artifact_path = tmp_path / "bull_4h_pocket_ablation.json"
    _write_bull_patch_artifact(artifact_path)

    confidence_payload = {
        "regime_label": "chop",
        "regime_gate": "CAUTION",
        "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
        "support_route_verdict": "exact_bucket_supported",
        "support_route_deployable": True,
        "support_progress": {
            "current_rows": 94,
            "minimum_support_rows": 50,
            "gap_to_minimum": 0,
        },
        "deployment_blocker": "circuit_breaker_active",
    }
    scope_summary = {
        "focus_scope": "regime_gate",
        "focus_scope_label": "同 gate 寬 scope",
        "spillover": {
            "extra_rows": 56,
            "worst_extra_regime_gate": {
                "regime_gate": "bull|CAUTION",
                "rows": 53,
                "win_rate": 0.2264,
                "avg_pnl": -0.004,
                "avg_quality": -0.0812,
            },
        },
        "exact_live_lane": {
            "rows": 144,
            "win_rate": 0.9514,
            "avg_pnl": 0.0153,
            "avg_quality": 0.5661,
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
            "current_live_structure_bucket_rows": 94,
        },
    }

    patch = build_live_pathology_patch_summary(
        confidence_payload,
        scope_summary,
        artifact_path=artifact_path,
    )

    assert patch["recommended_profile"] == "core_plus_macro"
    assert patch["status"] == "reference_only_non_current_live_scope"
    assert patch["current_live_regime_gate"] == "chop|CAUTION"
    assert patch["reference_patch_scope"] == "bull|CAUTION"
    assert patch["patch_scope_matches_live"] is False
    assert patch["reference_only_cause"] == "non_current_live_scope"
    assert "current live scope 是 chop|CAUTION" in patch["reason"]
    assert "只可作治理 / 訓練參考" in patch["recommended_action"]


def test_build_live_pathology_patch_summary_keeps_same_scope_patch_reference_only_while_blocker_active(tmp_path):
    artifact_path = tmp_path / "bull_4h_pocket_ablation.json"
    _write_bull_patch_artifact(artifact_path)

    confidence_payload = {
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
        "support_route_verdict": "exact_bucket_supported",
        "support_route_deployable": True,
        "support_progress": {
            "current_rows": 70,
            "minimum_support_rows": 50,
            "gap_to_minimum": 0,
        },
        "deployment_blocker": "decision_quality_below_trade_floor",
        "runtime_closure_state": "patch_active_but_execution_blocked",
    }
    scope_summary = {
        "focus_scope": "regime_label",
        "focus_scope_label": "同 GATE 寬 scope",
        "spillover": {
            "extra_rows": 200,
            "extra_row_share": 1.0,
            "worst_extra_regime_gate": {
                "regime_gate": "bull|CAUTION",
                "rows": 200,
                "win_rate": 0.4,
                "avg_pnl": -0.0023,
                "avg_quality": 0.0321,
            },
        },
        "exact_live_lane": {
            "rows": 0,
            "win_rate": None,
            "avg_pnl": None,
            "avg_quality": None,
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "current_live_structure_bucket_rows": 70,
        },
    }

    patch = build_live_pathology_patch_summary(
        confidence_payload,
        scope_summary,
        artifact_path=artifact_path,
    )

    assert patch is not None
    assert patch["status"] == "reference_only_while_deployment_blocked"
    assert patch["reference_only_cause"] == "deployment_blocker_active"
    assert patch["patch_scope_matches_live"] is True
    assert patch["reference_patch_scope"] == "bull|CAUTION"
    assert "decision_quality_below_trade_floor" in patch["reason"]
    assert "直到 blocker 清除後" in patch["reason"]
    assert "先處理 current-live deployment blocker" in patch["recommended_action"]


def test_build_live_pathology_scope_summary_exposes_exact_lane_bucket_context():
    summary = build_live_pathology_scope_summary(
        {
            "regime_label+regime_gate+entry_quality_label": {
                "rows": 12,
                "win_rate": 1.0,
                "avg_pnl": 0.0095,
                "avg_quality": 0.4193,
                "avg_drawdown_penalty": 0.3774,
                "avg_time_underwater": 0.734,
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                "current_live_structure_bucket_rows": 0,
                "recent500_dominant_structure_bucket": {
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "count": 12,
                    "share": 1.0,
                },
            },
            "entry_quality_label": {
                "rows": 197,
                "spillover_vs_exact_live_lane": {
                    "extra_rows": 185,
                    "extra_row_share": 0.9391,
                    "win_rate_delta_vs_exact": -0.2741,
                    "avg_pnl_delta_vs_exact": 0.0008,
                    "avg_quality_delta_vs_exact": -0.0501,
                    "avg_drawdown_penalty_delta_vs_exact": -0.1618,
                    "avg_time_underwater_delta_vs_exact": -0.3045,
                    "worst_extra_regime_gate": {
                        "regime_gate": "bull|BLOCK",
                        "rows": 24,
                        "win_rate": 0.0,
                        "avg_pnl": -0.0069,
                        "avg_quality": -0.2367,
                        "avg_drawdown_penalty": 0.329,
                        "avg_time_underwater": 0.847,
                    },
                    "worst_extra_regime_gate_feature_contrast": {
                        "top_mean_shift_features": [
                            {
                                "feature": "feat_4h_dist_bb_lower",
                                "reference_mean": 1.6764,
                                "current_mean": 0.929,
                                "mean_delta": -0.7474,
                            }
                        ]
                    },
                },
            },
        }
    )

    assert summary is not None
    assert summary["exact_live_lane"]["dominant_structure_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert summary["exact_live_lane"]["current_live_structure_bucket"] == "CAUTION|structure_quality_caution|q15"
    assert summary["exact_live_lane"]["current_live_structure_bucket_rows"] == 0
    assert summary["exact_live_lane"]["rows"] == 12
