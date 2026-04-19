import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.live_pathology_summary import build_live_pathology_scope_surface


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


def test_build_live_pathology_scope_surface_keeps_reference_patch_visible_for_non_bull_live_rows(tmp_path):
    artifact_path = tmp_path / "bull_4h_pocket_ablation.json"
    _write_bull_patch_artifact(artifact_path)

    confidence_payload = {
        "regime_label": "chop",
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
    assert patch["status"] == "reference_only_until_exact_support_ready"
    assert patch["recommended_profile"] == "core_plus_macro"
    assert patch["spillover_regime_gate"] == "bull|BLOCK"
    assert patch["reference_patch_scope"] == "bull|CAUTION"
    assert patch["reference_source"] == "bull_4h_pocket_ablation.bull_collapse_q35"
    assert patch["current_live_structure_bucket"] == "CAUTION|base_caution_regime_or_bias|q15"
    assert patch["current_live_structure_bucket_rows"] == 0
    assert patch["gap_to_minimum"] == 50
