import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_parallel_runner.py"
spec = importlib.util.spec_from_file_location("hb_parallel_runner_test_module", MODULE_PATH)
hb_parallel_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(hb_parallel_runner)


def test_parse_args_allows_fast_without_hb():
    args = hb_parallel_runner.parse_args(["--fast"])

    assert args.fast is True
    assert args.no_collect is False
    assert hb_parallel_runner.resolve_run_label(args) == "fast"


def test_parse_args_requires_hb_for_full_mode():
    try:
        hb_parallel_runner.parse_args([])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("Expected parser error when --hb missing in full mode")


def test_parse_collect_metadata_extracts_continuity_repair_json():
    payload = '{"inserted_total": 3, "bridge_inserted": 1, "used_bridge": true}'
    stdout = f"hello\nCONTINUITY_REPAIR_META: {payload}\nworld"

    parsed = hb_parallel_runner.parse_collect_metadata(stdout)

    assert parsed["inserted_total"] == 3
    assert parsed["bridge_inserted"] == 1
    assert parsed["used_bridge"] is True


def test_save_summary_uses_run_label_and_persists_source_blockers(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))

    counts = {"raw_market_data": 1, "features_normalized": 2, "labels": 3, "simulated_pyramid_win_rate": 0.5}
    collect_result = {
        "attempted": True,
        "success": True,
        "returncode": 0,
        "stdout": 'CONTINUITY_REPAIR_META: {"inserted_total": 2, "bridge_inserted": 1, "used_bridge": true}',
        "stderr": "",
    }
    blockers = {
        "blocked_count": 1,
        "counts_by_history_class": {"snapshot_only": 1},
        "blocked_features": [{"key": "nest_pred", "history_class": "snapshot_only"}],
    }
    results = {"full_ic": {"success": True, "stdout": "ok", "stderr": ""}}

    summary, summary_path = hb_parallel_runner.save_summary(
        "fast",
        counts,
        blockers,
        collect_result,
        results,
        elapsed=1.2,
        fast_mode=True,
        ic_diagnostics={"global_pass": 13, "tw_pass": 10, "total_features": 30},
        drift_diagnostics={"primary_window": "100", "primary_alerts": ["regime_concentration"]},
        live_predictor_diagnostics={"decision_quality_label": "D", "allowed_layers": 0},
        feature_ablation={"recommended_profile": "core_plus_macro"},
        bull_4h_pocket_ablation={"bull_collapse_q35": {"recommended_profile": "core_plus_macro"}},
        leaderboard_candidate_diagnostics={"selected_feature_profile": "core_only", "dual_profile_state": "leaderboard_global_winner_vs_train_support_fallback"},
        auto_propose_result={"attempted": True, "success": True, "returncode": 0, "stdout": "ok", "stderr": ""},
    )

    assert summary["heartbeat"] == "fast"
    assert summary["mode"] == "fast"
    assert summary["collect_result"]["success"] is True
    assert summary["collect_result"]["continuity_repair"]["bridge_inserted"] == 1
    assert summary["collect_result"]["continuity_repair"]["bridge_fallback_streak"] == 1
    assert summary["source_blockers"]["blocked_count"] == 1
    assert summary["ic_diagnostics"]["tw_pass"] == 10
    assert summary["drift_diagnostics"]["primary_window"] == "100"
    assert summary["live_predictor_diagnostics"]["decision_quality_label"] == "D"
    assert summary["feature_ablation"]["recommended_profile"] == "core_plus_macro"
    assert summary["bull_4h_pocket_ablation"]["bull_collapse_q35"]["recommended_profile"] == "core_plus_macro"
    assert summary["leaderboard_candidate_diagnostics"]["selected_feature_profile"] == "core_only"
    assert summary["auto_propose"]["success"] is True
    assert summary_path.endswith("heartbeat_fast_summary.json")

    saved = json.loads(Path(summary_path).read_text())
    assert saved["collect_result"]["attempted"] is True
    assert saved["collect_result"]["continuity_repair"]["used_bridge"] is True
    assert saved["source_blockers"]["blocked_features"][0]["key"] == "nest_pred"
    assert saved["ic_diagnostics"]["global_pass"] == 13
    assert saved["drift_diagnostics"]["primary_alerts"] == ["regime_concentration"]
    assert saved["live_predictor_diagnostics"]["allowed_layers"] == 0
    assert saved["feature_ablation"]["recommended_profile"] == "core_plus_macro"
    assert saved["bull_4h_pocket_ablation"]["bull_collapse_q35"]["recommended_profile"] == "core_plus_macro"
    assert saved["leaderboard_candidate_diagnostics"]["dual_profile_state"] == "leaderboard_global_winner_vs_train_support_fallback"
    assert saved["auto_propose"]["stdout_preview"] == "ok"


def test_collect_recent_drift_diagnostics_reads_primary_window(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "recent_drift_report.json").write_text(
        json.dumps(
            {
                "target_col": "simulated_pyramid_win",
                "horizon_minutes": 1440,
                "full_sample": {"rows": 11134, "win_rate": 0.6459},
                "primary_window": {
                    "window": "100",
                    "alerts": ["regime_concentration"],
                    "summary": {
                        "rows": 100,
                        "win_rate": 0.93,
                        "win_rate_delta_vs_full": 0.2841,
                        "dominant_regime": "chop",
                        "dominant_regime_share": 0.97,
                        "drift_interpretation": "supported_extreme_trend",
                        "feature_diagnostics": {
                            "feature_count": 30,
                            "low_variance_count": 4,
                            "low_distinct_count": 2,
                            "null_heavy_count": 1,
                        },
                        "target_path_diagnostics": {
                            "window_start_timestamp": "2026-04-12 00:00:00",
                            "window_end_timestamp": "2026-04-13 03:00:00",
                            "latest_target": 1,
                            "tail_target_streak": {
                                "target": 1,
                                "count": 14,
                                "start_timestamp": "2026-04-12 14:00:00",
                                "end_timestamp": "2026-04-13 03:00:00",
                                "regime_counts": {"chop": 14},
                            },
                            "target_regime_breakdown": {"chop:1": 93, "bear:0": 7},
                            "recent_examples": [{"timestamp": "2026-04-13 03:00:00", "target": 1, "regime": "chop"}],
                        },
                    },
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_recent_drift_diagnostics()

    assert diag["target_col"] == "simulated_pyramid_win"
    assert diag["primary_window"] == "100"
    assert diag["primary_summary"]["dominant_regime"] == "chop"
    assert diag["primary_summary"]["drift_interpretation"] == "supported_extreme_trend"
    assert diag["primary_summary"]["feature_diagnostics"]["low_variance_count"] == 4
    assert diag["primary_summary"]["target_path_diagnostics"]["tail_target_streak"]["count"] == 14
    assert diag["primary_summary"]["target_path_diagnostics"]["recent_examples"][0]["timestamp"] == "2026-04-13 03:00:00"


def test_collect_live_predictor_diagnostics_reads_probe_json(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "live_predict_probe.json").write_text(
        json.dumps(
            {
                "target_col": "simulated_pyramid_win",
                "used_model": "regime_bull_ensemble",
                "signal": "HOLD",
                "confidence": 0.21,
                "should_trade": False,
                "regime_label": "bull",
                "model_route_regime": "bull",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "allowed_layers_raw": 0,
                "allowed_layers": 0,
                "execution_guardrail_applied": True,
                "decision_quality_calibration_scope": "entry_quality_label",
                "decision_quality_scope_diagnostics": {
                    "regime_gate+entry_quality_label": {"rows": 315},
                    "entry_quality_label": {"rows": 3186},
                },
                "decision_quality_recent_pathology_applied": True,
                "decision_quality_recent_pathology_window": 500,
                "decision_quality_recent_pathology_alerts": ["label_imbalance"],
                "decision_quality_exact_live_lane_bucket_verdict": "toxic_sub_bucket_identified",
                "decision_quality_exact_live_lane_bucket_reason": "q15 子 bucket 比 q35 差，應升級成 veto 候選",
                "decision_quality_exact_live_lane_toxic_bucket": {
                    "bucket": "CAUTION|structure_quality_caution|q15",
                    "rows": 4,
                    "win_rate": 0.0,
                },
                "decision_quality_exact_live_lane_bucket_diagnostics": {
                    "verdict": "toxic_sub_bucket_identified"
                },
                "decision_quality_label": "D",
                "expected_win_rate": 0.154,
                "expected_pyramid_quality": -0.1536,
                "non_null_4h_feature_count": 10,
                "non_null_4h_lag_count": 30,
                "decision_quality_recent_pathology_summary": {
                    "rows": 500,
                    "reference_window_comparison": {
                        "top_mean_shift_features": [{"feature": "feat_4h_dist_swing_low"}]
                    },
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_live_predictor_diagnostics()

    assert diag["used_model"] == "regime_bull_ensemble"
    assert diag["decision_quality_recent_pathology_applied"] is True
    assert diag["decision_quality_recent_pathology_window"] == 500
    assert diag["decision_quality_exact_live_lane_bucket_verdict"] == "toxic_sub_bucket_identified"
    assert diag["decision_quality_exact_live_lane_toxic_bucket"]["bucket"] == "CAUTION|structure_quality_caution|q15"
    assert diag["decision_quality_label"] == "D"
    assert diag["non_null_4h_lag_count"] == 30
    assert diag["decision_quality_scope_diagnostics"]["entry_quality_label"]["rows"] == 3186


def test_collect_feature_ablation_diagnostics_reads_recommended_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "feature_group_ablation.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14 10:00:00",
                "target_col": "simulated_pyramid_win",
                "recent_rows": 5000,
                "recommended_profile": "core_plus_macro",
                "bull_collapse_4h_features": ["feat_4h_dist_bb_lower"],
                "stable_4h_features": ["feat_4h_bias200"],
                "profiles": {
                    "core_plus_macro": {"cv_mean_accuracy": 0.73, "cv_worst_accuracy": 0.45},
                    "current_full": {"cv_mean_accuracy": 0.65, "cv_worst_accuracy": 0.44},
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_feature_ablation_diagnostics()

    assert diag["recommended_profile"] == "core_plus_macro"
    assert diag["recommended_metrics"]["cv_mean_accuracy"] == 0.73
    assert diag["current_full_metrics"]["cv_mean_accuracy"] == 0.65
    assert diag["bull_collapse_4h_features"] == ["feat_4h_dist_bb_lower"]


def test_collect_bull_4h_pocket_diagnostics_reads_live_bucket_support(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "bull_4h_pocket_ablation.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14 10:05:00",
                "target_col": "simulated_pyramid_win",
                "collapse_features": ["feat_4h_dist_bb_lower"],
                "collapse_thresholds": {"feat_4h_dist_bb_lower": 0.43},
                "live_context": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "entry_quality_label": "D",
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 0,
                    "supported_neighbor_buckets": ["CAUTION|base_caution_regime_or_bias|q15"],
                },
                "support_pathology_summary": {
                    "blocker_state": "exact_lane_proxy_fallback_only",
                    "preferred_support_cohort": "bull_exact_live_lane_proxy",
                    "minimum_support_rows": 50,
                    "current_live_structure_bucket_gap_to_minimum": 50,
                    "exact_bucket_root_cause": "same_lane_exists_but_q35_missing",
                    "bucket_comparison_takeaway": "neighbor_bucket_outperforms_broader_same_bucket",
                    "proxy_boundary_verdict": "proxy_too_wide_vs_exact_bucket",
                    "proxy_boundary_reason": "proxy 與 recent exact bucket 差距過大",
                    "proxy_boundary_diagnostics": {
                        "recent_exact_current_bucket": {"rows": 5, "win_rate": 0.4},
                        "historical_exact_bucket_proxy": {"rows": 8, "win_rate": 0.8},
                    },
                    "bucket_evidence_comparison": {
                        "current_live_bucket": "CAUTION|structure_quality_caution|q35",
                        "exact_live_lane": {"bucket": "CAUTION|base_caution_regime_or_bias|q15", "rows": 25},
                        "exact_bucket_proxy": {"bucket": "CAUTION|structure_quality_caution|q35", "rows": 8},
                        "broader_same_bucket": {"bucket": "CAUTION|structure_quality_caution|q35", "rows": 61},
                    },
                    "exact_lane_bucket_verdict": "toxic_sub_bucket_identified",
                    "exact_lane_bucket_reason": "q15 子 bucket 明顯拖累 exact lane",
                    "exact_lane_toxic_bucket": {
                        "bucket": "CAUTION|base_caution_regime_or_bias|q15",
                        "rows": 7,
                        "win_rate": 0.1429,
                        "vs_current_bucket": {"win_rate_delta": -0.6571},
                    },
                    "exact_lane_bucket_diagnostics": {
                        "verdict": "toxic_sub_bucket_identified",
                        "buckets": {
                            "CAUTION|structure_quality_caution|q35": {"rows": 5, "win_rate": 0.8},
                            "CAUTION|base_caution_regime_or_bias|q15": {"rows": 7, "win_rate": 0.1429},
                        },
                    },
                    "recommended_action": "維持 blocker",
                },
                "cohorts": {
                    "bull_all": {"rows": 100, "base_win_rate": 0.67, "recommended_profile": "core_plus_macro_plus_all_4h", "profiles": {"core_plus_macro_plus_all_4h": {"cv_mean_accuracy": 0.64}}},
                    "bull_collapse_q35": {"rows": 40, "base_win_rate": 0.51, "recommended_profile": "core_plus_macro", "profiles": {"core_plus_macro": {"cv_mean_accuracy": 0.70}}},
                    "bull_exact_live_lane_proxy": {"rows": 25, "base_win_rate": 0.79, "recommended_profile": "core_plus_macro", "profiles": {"core_plus_macro": {"cv_mean_accuracy": 0.81}}},
                    "bull_live_exact_lane_bucket_proxy": {"rows": 8, "base_win_rate": 0.50, "recommended_profile": "core_plus_macro", "profiles": {"core_plus_macro": {"cv_mean_accuracy": 0.62}}},
                    "bull_supported_neighbor_buckets_proxy": {"rows": 20, "base_win_rate": 0.69, "recommended_profile": "core_plus_macro", "profiles": {"core_plus_macro": {"cv_mean_accuracy": 0.73}}},
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_bull_4h_pocket_diagnostics()

    assert diag["live_context"]["current_live_structure_bucket_rows"] == 0
    assert diag["live_context"]["supported_neighbor_buckets"] == ["CAUTION|base_caution_regime_or_bias|q15"]
    assert diag["support_pathology_summary"]["exact_bucket_root_cause"] == "same_lane_exists_but_q35_missing"
    assert diag["support_pathology_summary"]["bucket_comparison_takeaway"] == "neighbor_bucket_outperforms_broader_same_bucket"
    assert diag["support_pathology_summary"]["proxy_boundary_verdict"] == "proxy_too_wide_vs_exact_bucket"
    assert diag["support_pathology_summary"]["proxy_boundary_diagnostics"]["recent_exact_current_bucket"]["rows"] == 5
    assert diag["support_pathology_summary"]["bucket_evidence_comparison"]["broader_same_bucket"]["rows"] == 61
    assert diag["support_pathology_summary"]["exact_lane_bucket_verdict"] == "toxic_sub_bucket_identified"
    assert diag["support_pathology_summary"]["exact_lane_toxic_bucket"]["bucket"] == "CAUTION|base_caution_regime_or_bias|q15"
    assert diag["support_pathology_summary"]["exact_lane_bucket_diagnostics"]["buckets"]["CAUTION|base_caution_regime_or_bias|q15"]["rows"] == 7
    assert diag["bull_all"]["recommended_profile"] == "core_plus_macro_plus_all_4h"
    assert diag["bull_collapse_q35"]["recommended_profile"] == "core_plus_macro"
    assert diag["bull_live_exact_lane_bucket_proxy"]["rows"] == 8


def test_collect_leaderboard_candidate_diagnostics_reads_dual_profile_state(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "leaderboard_feature_profile_probe.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14T12:40:00Z",
                "target_col": "simulated_pyramid_win",
                "leaderboard_count": 8,
                "top_model": {
                    "selected_feature_profile": "core_only",
                    "selected_feature_profile_source": "feature_group_ablation.recommended_profile",
                    "selected_feature_profile_blocker_applied": False,
                    "selected_feature_profile_blocker_reason": None,
                },
                "alignment": {
                    "dual_profile_state": "leaderboard_global_winner_vs_train_support_fallback",
                    "global_recommended_profile": "core_only",
                    "train_selected_profile": "core_plus_macro",
                    "train_selected_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
                    "train_support_cohort": "bull_supported_neighbor_buckets_proxy",
                    "train_support_rows": 84,
                    "train_exact_live_bucket_rows": 0,
                    "live_regime_gate": "CAUTION",
                    "live_entry_quality_label": "D",
                    "live_execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
                    "live_current_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "live_current_structure_bucket_rows": 0,
                    "supported_neighbor_buckets": ["CAUTION|base_caution_regime_or_bias|q15"],
                    "bull_support_aware_profile": "core_plus_macro",
                    "bull_support_neighbor_rows": 84,
                    "bull_exact_live_bucket_proxy_rows": 43,
                    "blocked_candidate_profiles": [
                        {
                            "feature_profile": "core_plus_macro",
                            "blocker_reason": "unsupported_exact_live_structure_bucket",
                            "exact_live_bucket_rows": 0,
                        }
                    ],
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_leaderboard_candidate_diagnostics()

    assert diag["selected_feature_profile"] == "core_only"
    assert diag["dual_profile_state"] == "leaderboard_global_winner_vs_train_support_fallback"
    assert diag["train_selected_profile"] == "core_plus_macro"
    assert diag["live_current_structure_bucket_rows"] == 0
    assert diag["blocked_candidate_profiles"][0]["blocker_reason"] == "unsupported_exact_live_structure_bucket"
