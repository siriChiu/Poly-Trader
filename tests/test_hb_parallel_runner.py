import importlib.util
import json
from pathlib import Path

from model import q35_bias50_calibration as q35_calibration_module

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_parallel_runner.py"
spec = importlib.util.spec_from_file_location("hb_parallel_runner_test_module", MODULE_PATH)
hb_parallel_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(hb_parallel_runner)

Q35_AUDIT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_q35_scaling_audit.py"
q35_spec = importlib.util.spec_from_file_location("hb_q35_scaling_audit_test_module", Q35_AUDIT_PATH)
hb_q35_scaling_audit = importlib.util.module_from_spec(q35_spec)
assert q35_spec.loader is not None
q35_spec.loader.exec_module(hb_q35_scaling_audit)


class _DictRow(dict):
    def keys(self):
        return super().keys()


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


def test_q35_audit_current_row_context_uses_piecewise_bias50_calibration(tmp_path, monkeypatch):
    audit_path = tmp_path / "q35_scaling_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "overall_verdict": "broader_bull_cohort_recalibration_candidate",
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                },
                "segmented_calibration": {
                    "status": "segmented_calibration_required",
                    "recommended_mode": "piecewise_quantile_calibration",
                    "exact_lane": {
                        "bias50_distribution": {"p90": 3.1054},
                    },
                    "reference_cohort": {
                        "cohort": "bull_all",
                        "bias50_distribution": {"p90": 4.4607},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(q35_calibration_module, "DEFAULT_Q35_AUDIT_PATH", audit_path)
    q35_calibration_module._AUDIT_CACHE.update({"path": None, "mtime": None, "data": None})
    monkeypatch.setattr(hb_q35_scaling_audit.live_predictor, "_compute_live_regime_gate_debug", lambda *args, **kwargs: {
        "final_gate": "CAUTION",
        "base_gate": "ALLOW",
        "final_reason": "structure_quality_caution",
        "structure_quality": 0.3804,
    })
    monkeypatch.setattr(
        hb_q35_scaling_audit.live_predictor,
        "_live_structure_bucket_from_debug",
        lambda debug: "CAUTION|structure_quality_caution|q35",
    )
    row = _DictRow(
        timestamp="2026-04-15 02:39:05.273899",
        symbol="BTCUSDT",
        regime_label="bull",
        feat_4h_bias50=3.23,
        feat_4h_bias200=5.934,
        feat_nose=0.417,
        feat_pulse=0.7533,
        feat_ear=-0.0026,
        feat_4h_bb_pct_b=0.4575,
        feat_4h_dist_bb_lower=1.4566,
        feat_4h_dist_swing_low=4.9917,
    )

    current = hb_q35_scaling_audit._build_row_context(row)
    preview = hb_q35_scaling_audit.compute_piecewise_bias50_score(
        row["feat_4h_bias50"],
        regime_label="bull",
        regime_gate="CAUTION",
        structure_bucket="CAUTION|structure_quality_caution|q35",
        audit=json.loads(audit_path.read_text(encoding="utf-8")),
    )

    calibration = current["entry_quality_components"]["bias50_calibration"]
    assert current["regime_gate"] == "CAUTION"
    assert current["structure_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert calibration["applied"] is True
    assert calibration["segment"] == "bull_reference_extension"
    assert calibration["score"] == preview["score"]
    assert calibration["reference_cohort"] == "bull_all"
    assert current["entry_quality"] > 0.5

    segmented = {
        "status": "segmented_calibration_required",
        "recommended_mode": "piecewise_quantile_calibration",
        "exact_lane": {"bias50_distribution": {"p90": 3.1054}},
        "reference_cohort": {"cohort": "bull_all", "bias50_distribution": {"p90": 4.4607}},
    }
    preview_with_context = hb_q35_scaling_audit.compute_piecewise_bias50_score(
        row["feat_4h_bias50"],
        regime_label="bull",
        regime_gate="CAUTION",
        structure_bucket="CAUTION|structure_quality_caution|q35",
        audit={
            "overall_verdict": "broader_bull_cohort_recalibration_candidate",
            "segmented_calibration": segmented,
            "current_live": {
                "regime_label": "bull",
                "regime_gate": "CAUTION",
                "structure_bucket": "CAUTION|structure_quality_caution|q35",
            },
        },
    )
    runtime_status, runtime_reason = hb_q35_scaling_audit._runtime_contract_state(
        {
            **segmented,
            "status": "segmented_calibration_required",
            "exact_lane": {"percentile_band": "overheat", "bias50_distribution": {"p90": 3.1054}},
        },
        preview_with_context,
    )
    assert runtime_status == "piecewise_runtime_active"
    assert "實際套用" in runtime_reason


def test_q35_runtime_contract_state_marks_runtime_ready_when_current_row_is_back_inside_exact_lane():
    runtime_status, runtime_reason = hb_q35_scaling_audit._runtime_contract_state(
        {
            "status": "segmented_calibration_required",
            "exact_lane": {"percentile_band": "elevated_but_within_p90"},
        },
        {
            "applied": False,
            "mode": "legacy_linear",
            "segment": None,
        },
    )

    assert runtime_status == "piecewise_runtime_ready_current_row_outside_extension"
    assert "已經實作" in runtime_reason
    assert "不需要套用" in runtime_reason



def test_q35_runtime_contract_state_marks_formula_review_active_when_exact_lane_score_is_applied():
    runtime_status, runtime_reason = hb_q35_scaling_audit._runtime_contract_state(
        {
            "status": "formula_review_required",
            "exact_lane": {"percentile_band": "elevated_but_within_p90"},
        },
        {
            "applied": True,
            "mode": "exact_lane_formula_review",
            "segment": "exact_lane_elevated_within_p90",
        },
    )

    assert runtime_status == "piecewise_runtime_active"
    assert "實際套用" in runtime_reason


def test_q35_runtime_contract_state_marks_hold_only_when_reference_band_is_still_overheat():
    runtime_status, runtime_reason = hb_q35_scaling_audit._runtime_contract_state(
        {
            "status": "segmented_calibration_required",
            "exact_lane": {"percentile_band": "overheat"},
        },
        {
            "applied": False,
            "mode": "piecewise_quantile_calibration",
            "segment": "reference_overheat",
        },
    )

    assert runtime_status == "piecewise_runtime_ready_hold_only_current_row"
    assert "hold-only" in runtime_reason


def test_collect_live_predictor_diagnostics_preserves_circuit_breaker_reason():
    payload = {
        "target_col": "simulated_pyramid_win",
        "used_model": "circuit_breaker",
        "model_type": "circuit_breaker",
        "signal": "CIRCUIT_BREAKER",
        "confidence": 0.5,
        "should_trade": False,
        "reason": "Consecutive loss streak: 50 >= 50; Recent 50-sample win rate: 0.00% < 30%",
        "streak": 50,
        "win_rate": 0.0,
        "recent_window_win_rate": 0.0,
        "recent_window_wins": 0,
        "window_size": 50,
        "triggered_by": ["streak", "recent_win_rate"],
        "horizon_minutes": 1440,
        "regime_label": "bull",
        "allowed_layers": 0,
    }

    result = hb_parallel_runner.collect_live_predictor_diagnostics({"stdout": json.dumps(payload)})

    assert result["model_type"] == "circuit_breaker"
    assert result["signal"] == "CIRCUIT_BREAKER"
    assert result["runtime_blocker"] == "circuit_breaker"
    assert result["reason"] == "Consecutive loss streak: 50 >= 50; Recent 50-sample win rate: 0.00% < 30%"
    assert result["streak"] == 50
    assert result["recent_window_win_rate"] == 0.0
    assert result["triggered_by"] == ["streak", "recent_win_rate"]
    assert result["horizon_minutes"] == 1440
    assert result["allowed_layers"] == 0


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
        live_decision_drilldown={
            "json": "data/live_decision_quality_drilldown.json",
            "chosen_scope": "regime_label+entry_quality_label",
            "remaining_gap_to_floor": 0.051,
            "best_single_component": "feat_4h_bias50",
            "best_single_component_required_score_delta": 0.17,
        },
        q35_scaling_audit={
            "overall_verdict": "hold_only_bias50_overheat_confirmed",
            "structure_scaling_verdict": "q35_structure_caution_not_root_cause",
            "broader_bull_cohorts": {"bull_all": {"current_bias50_percentile": 0.99}},
            "segmented_calibration": {
                "status": "hold_only_confirmed",
                "recommended_mode": "keep_hold_only",
                "reference_cohort": {},
            },
        },
        circuit_breaker_audit={
            "root_cause": {"verdict": "mixed_horizon_false_positive"},
            "mixed_scope": {"triggered_by": ["streak", "recent_win_rate"], "streak": {"count": 59}},
            "aligned_scope": {"triggered_by": [], "release_ready": True},
        },
        feature_ablation={"recommended_profile": "core_plus_macro", "profile_role": {"role": "global_shrinkage_winner"}},
        bull_4h_pocket_ablation={"bull_collapse_q35": {"recommended_profile": "core_plus_macro"}, "production_profile_role": {"role": "support_aware_production_profile"}},
        leaderboard_candidate_diagnostics={"selected_feature_profile": "core_only", "dual_profile_state": "leaderboard_global_winner_vs_train_support_fallback", "profile_split": {"verdict": "dual_role_required"}},
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
    assert summary["live_decision_drilldown"]["best_single_component"] == "feat_4h_bias50"
    assert summary["q35_scaling_audit"]["overall_verdict"] == "hold_only_bias50_overheat_confirmed"
    assert summary["q35_scaling_audit"]["segmented_calibration"]["status"] == "hold_only_confirmed"
    assert summary["circuit_breaker_audit"]["root_cause"]["verdict"] == "mixed_horizon_false_positive"
    assert summary["circuit_breaker_audit"]["aligned_scope"]["release_ready"] is True
    assert summary["feature_ablation"]["recommended_profile"] == "core_plus_macro"
    assert summary["feature_ablation"]["profile_role"]["role"] == "global_shrinkage_winner"
    assert summary["bull_4h_pocket_ablation"]["bull_collapse_q35"]["recommended_profile"] == "core_plus_macro"
    assert summary["bull_4h_pocket_ablation"]["production_profile_role"]["role"] == "support_aware_production_profile"
    assert summary["leaderboard_candidate_diagnostics"]["selected_feature_profile"] == "core_only"
    assert summary["leaderboard_candidate_diagnostics"]["profile_split"]["verdict"] == "dual_role_required"
    assert summary["auto_propose"]["success"] is True
    assert summary_path.endswith("heartbeat_fast_summary.json")

    saved = json.loads(Path(summary_path).read_text())
    assert saved["collect_result"]["attempted"] is True
    assert saved["collect_result"]["continuity_repair"]["used_bridge"] is True
    assert saved["source_blockers"]["blocked_features"][0]["key"] == "nest_pred"
    assert saved["ic_diagnostics"]["global_pass"] == 13
    assert saved["drift_diagnostics"]["primary_alerts"] == ["regime_concentration"]
    assert saved["live_predictor_diagnostics"]["allowed_layers"] == 0
    assert saved["live_decision_drilldown"]["remaining_gap_to_floor"] == 0.051
    assert saved["q35_scaling_audit"]["structure_scaling_verdict"] == "q35_structure_caution_not_root_cause"
    assert saved["q35_scaling_audit"]["broader_bull_cohorts"]["bull_all"]["current_bias50_percentile"] == 0.99
    assert saved["q35_scaling_audit"]["segmented_calibration"]["recommended_mode"] == "keep_hold_only"
    assert saved["circuit_breaker_audit"]["mixed_scope"]["streak"]["count"] == 59
    assert saved["circuit_breaker_audit"]["aligned_scope"]["release_ready"] is True
    assert saved["feature_ablation"]["recommended_profile"] == "core_plus_macro"
    assert saved["feature_ablation"]["profile_role"]["role"] == "global_shrinkage_winner"
    assert saved["bull_4h_pocket_ablation"]["bull_collapse_q35"]["recommended_profile"] == "core_plus_macro"
    assert saved["bull_4h_pocket_ablation"]["production_profile_role"]["role"] == "support_aware_production_profile"
    assert saved["leaderboard_candidate_diagnostics"]["dual_profile_state"] == "leaderboard_global_winner_vs_train_support_fallback"
    assert saved["leaderboard_candidate_diagnostics"]["profile_split"]["verdict"] == "dual_role_required"
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
                "entry_quality_components": {
                    "entry_quality": 0.3861,
                    "trade_floor": 0.55,
                    "trade_floor_gap": -0.1639,
                    "base_components": [{"feature": "feat_4h_bias50"}],
                    "structure_components": [{"feature": "feat_4h_bb_pct_b"}],
                },
                "allowed_layers_raw": 0,
                "allowed_layers": 0,
                "allowed_layers_reason": "entry_quality_below_trade_floor",
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
    assert diag["allowed_layers_reason"] == "entry_quality_below_trade_floor"
    assert diag["entry_quality_components"]["trade_floor_gap"] == -0.1639
    assert diag["entry_quality_components"]["base_components"][0]["feature"] == "feat_4h_bias50"
    assert diag["decision_quality_label"] == "D"
    assert diag["non_null_4h_lag_count"] == 30
    assert diag["decision_quality_scope_diagnostics"]["entry_quality_label"]["rows"] == 3186


def test_collect_q35_scaling_audit_diagnostics_reads_hold_only_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "q35_scaling_audit.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-15 00:31:10",
                "target_col": "simulated_pyramid_win",
                "overall_verdict": "hold_only_bias50_overheat_confirmed",
                "structure_scaling_verdict": "q35_structure_caution_not_root_cause",
                "verdict_reason": "gate alone does not change layers",
                "recommended_action": "keep hold-only",
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "base_gate": "ALLOW",
                    "gate_reason": "structure_quality_caution",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "structure_quality": 0.4553,
                    "entry_quality": 0.5341,
                    "entry_quality_label": "D",
                    "allowed_layers_raw": 0,
                    "allowed_layers_reason": "entry_quality_below_trade_floor",
                    "entry_quality_components": {
                        "bias50_calibration": {
                            "applied": True,
                            "score": 0.3224,
                            "legacy_score": 0.0,
                            "score_delta_vs_legacy": 0.3224,
                            "mode": "piecewise_quantile_calibration",
                            "segment": "bull_reference_extension",
                            "reference_cohort": "bull_all"
                        }
                    },
                    "raw_features": {
                        "feat_4h_bias50": 3.7318,
                        "feat_4h_bias200": 6.4571
                    }
                },
                "exact_lane_summary": {
                    "rows": 90,
                    "win_rate": 1.0,
                    "current_bias50_percentile": 1.0,
                    "bias50_distribution": {"p90": 3.1054},
                    "structure_quality_distribution": {"p50": 0.5996},
                    "entry_quality_distribution": {"p90": 0.4944}
                },
                "broader_bull_cohorts": {
                    "same_gate_same_quality": {
                        "rows": 105,
                        "win_rate": 0.9714,
                        "current_bias50_percentile": 0.98,
                        "bias50_distribution": {"p90": 3.55}
                    },
                    "same_bucket": {
                        "rows": 90,
                        "win_rate": 1.0,
                        "current_bias50_percentile": 1.0,
                        "bias50_distribution": {"p90": 3.11}
                    },
                    "bull_all": {
                        "rows": 768,
                        "win_rate": 0.7057,
                        "current_bias50_percentile": 0.99,
                        "bias50_distribution": {"p90": 3.4}
                    }
                },
                "segmented_calibration": {
                    "status": "hold_only_confirmed",
                    "recommended_mode": "keep_hold_only",
                    "reason": "current bias50 高於所有候選 cohorts 的 p90",
                    "runtime_contract_status": "piecewise_runtime_active",
                    "runtime_contract_reason": "piecewise bias50 calibration 已由 predictor / q35 audit 實際套用到 current bull q35 lane；後續 heartbeat 不得再把這題描述成 runtime 尚未吃到新公式。",
                    "exact_lane": {
                        "current_bias50_percentile": 1.0,
                        "percentile_band": "overheat",
                        "delta_vs_p90": 0.6264
                    },
                    "reference_cohort": {},
                    "broader_bull_cohorts": {
                        "bull_all": {
                            "current_bias50_percentile": 0.99,
                            "percentile_band": "overheat"
                        }
                    }
                },
                "piecewise_runtime_preview": {
                    "applied": True,
                    "score": 0.3224,
                    "legacy_score": 0.0,
                    "score_delta_vs_legacy": 0.3224,
                    "mode": "piecewise_quantile_calibration",
                    "segment": "bull_reference_extension",
                    "reference_cohort": "bull_all",
                    "reason": "bias50 is above the exact-lane p90 but still inside the broader bull reference p90; use a decaying extension score instead of forcing a zero score.",
                    "exact_p90": 3.1054,
                    "reference_p90": 4.4607
                },
                "counterfactuals": {
                    "entry_if_gate_allow_only": 0.3726,
                    "layers_if_gate_allow_only": 0,
                    "gate_allow_only_changes_layers": False,
                    "entry_if_bias50_fully_relaxed": 0.6726,
                    "layers_if_bias50_fully_relaxed": 1,
                    "required_bias50_cap_for_floor": -0.5565,
                    "current_bias50_value": 3.7318
                }
            }
        )
    )

    diag = hb_parallel_runner.collect_q35_scaling_audit_diagnostics()

    assert diag["overall_verdict"] == "hold_only_bias50_overheat_confirmed"
    assert diag["structure_scaling_verdict"] == "q35_structure_caution_not_root_cause"
    assert diag["segmented_calibration"]["status"] == "hold_only_confirmed"
    assert diag["segmented_calibration"]["runtime_contract_status"] == "piecewise_runtime_active"
    assert "實際套用" in diag["segmented_calibration"]["runtime_contract_reason"]
    assert diag["segmented_calibration"]["exact_lane"]["percentile_band"] == "overheat"
    assert diag["current_live"]["feat_4h_bias50"] == 3.7318
    assert diag["current_live"]["bias50_calibration"]["applied"] is True
    assert diag["current_live"]["bias50_calibration"]["segment"] == "bull_reference_extension"
    assert diag["exact_lane_summary"]["current_bias50_percentile"] == 1.0
    assert diag["broader_bull_cohorts"]["same_gate_same_quality"]["rows"] == 105
    assert diag["broader_bull_cohorts"]["bull_all"]["current_bias50_percentile"] == 0.99
    assert diag["piecewise_runtime_preview"]["applied"] is True
    assert diag["piecewise_runtime_preview"]["reference_cohort"] == "bull_all"
    assert diag["counterfactuals"]["gate_allow_only_changes_layers"] is False
    assert diag["counterfactuals"]["layers_if_bias50_fully_relaxed"] == 1


def test_collect_circuit_breaker_audit_diagnostics_reads_mixed_horizon_false_positive(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "circuit_breaker_audit.json").write_text(
        json.dumps(
            {
                "target_col": "simulated_pyramid_win",
                "trigger_thresholds": {
                    "horizon_minutes": 1440,
                    "streak": 50,
                    "recent_window": 50,
                    "recent_win_rate_floor": 0.30,
                },
                "root_cause": {
                    "verdict": "mixed_horizon_false_positive",
                    "summary": "240m tail triggers the mixed breaker while 1440m is healthy.",
                    "recommended_patch": "align circuit breaker to 1440m",
                },
                "mixed_scope": {
                    "triggered": True,
                    "triggered_by": ["streak", "recent_win_rate"],
                    "rows_available": 100,
                    "latest_timestamp": "2026-04-15 03:04:33",
                    "streak": {"count": 59, "threshold": 50, "horizons": {"240": 59}},
                    "recent_window": {"window_size": 50, "win_rate": 0.0, "losses": 50},
                },
                "aligned_scope": {
                    "triggered": False,
                    "triggered_by": [],
                    "release_ready": True,
                    "rows_available": 100,
                    "latest_timestamp": "2026-04-14 06:49:03",
                    "streak": {"count": 0, "threshold": 50, "horizons": {"1440": 0}},
                    "recent_window": {"window_size": 50, "win_rate": 1.0, "losses": 0},
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_circuit_breaker_audit_diagnostics()

    assert diag["root_cause"]["verdict"] == "mixed_horizon_false_positive"
    assert diag["mixed_scope"]["triggered_by"] == ["streak", "recent_win_rate"]
    assert diag["mixed_scope"]["streak"]["count"] == 59
    assert diag["aligned_scope"]["release_ready"] is True
    assert diag["aligned_scope"]["recent_window"]["win_rate"] == 1.0


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
    assert diag["profile_role"]["role"] == "global_shrinkage_winner"
    assert diag["bull_collapse_4h_features"] == ["feat_4h_dist_bb_lower"]


def test_collect_q15_support_audit_diagnostics_reads_support_and_floor_verdicts(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "q15_support_audit.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-15T07:12:00Z",
                "target_col": "simulated_pyramid_win",
                "current_live": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                    "current_live_structure_bucket_rows": 0,
                },
                "support_route": {
                    "verdict": "exact_bucket_missing_proxy_reference_only",
                    "deployable": False,
                    "preferred_support_cohort": "bull_live_exact_bucket_proxy",
                },
                "floor_cross_legality": {
                    "verdict": "math_cross_possible_but_illegal_without_exact_support",
                    "legal_to_relax_runtime_gate": False,
                    "best_single_component": "feat_4h_bias50",
                    "remaining_gap_to_floor": 0.0198,
                },
                "next_action": "先補 exact bucket 真樣本。",
            }
        )
    )

    diag = hb_parallel_runner.collect_q15_support_audit_diagnostics()

    assert diag["support_route"]["verdict"] == "exact_bucket_missing_proxy_reference_only"
    assert diag["support_route"]["deployable"] is False
    assert diag["floor_cross_legality"]["verdict"] == "math_cross_possible_but_illegal_without_exact_support"
    assert diag["floor_cross_legality"]["best_single_component"] == "feat_4h_bias50"
    assert diag["next_action"] == "先補 exact bucket 真樣本。"


def test_main_runs_q15_support_audit_after_leaderboard_probe(monkeypatch):
    order = []

    class Args:
        fast = True
        hb = "test"
        no_collect = True
        no_train = True
        no_dw = True

    class FakeExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, task):
            raise AssertionError("submit() should not be called when TASKS is empty in this test")

    def _ok(stdout: str = ""):
        return {"success": True, "returncode": 0, "stdout": stdout, "stderr": ""}

    monkeypatch.setattr(hb_parallel_runner, "TASKS", [])
    monkeypatch.setattr(hb_parallel_runner, "parse_args", lambda argv=None: Args())
    monkeypatch.setattr(hb_parallel_runner, "resolve_run_label", lambda args: "test")
    monkeypatch.setattr(hb_parallel_runner, "run_collect_step", lambda skip=False: {"attempted": False, "success": True, "returncode": 0, "stdout": "", "stderr": ""})
    monkeypatch.setattr(
        hb_parallel_runner,
        "quick_counts",
        lambda: {
            "raw_market_data": 1,
            "features_normalized": 1,
            "labels": 1,
            "simulated_pyramid_win_rate": 0.5,
            "latest_raw_timestamp": "2026-04-15 00:00:00",
            "label_horizons": [],
        },
    )
    monkeypatch.setattr(hb_parallel_runner, "collect_source_blockers", lambda: {"blocked_count": 0, "counts_by_history_class": {}, "blocked_features": []})
    monkeypatch.setattr(hb_parallel_runner, "print_source_blockers", lambda payload: None)
    monkeypatch.setattr(hb_parallel_runner, "refresh_train_prerequisites", lambda needs_train: {})
    monkeypatch.setattr(hb_parallel_runner.concurrent.futures, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(hb_parallel_runner.concurrent.futures, "as_completed", lambda future_to_name: [])
    monkeypatch.setattr(hb_parallel_runner, "collect_ic_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_recent_drift_report", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_recent_drift_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_predict_probe", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "_persist_live_predictor_probe", lambda stdout: None)
    monkeypatch.setattr(hb_parallel_runner, "collect_live_predictor_diagnostics", lambda result: {})
    monkeypatch.setattr(hb_parallel_runner, "run_live_decision_quality_drilldown", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "run_q35_scaling_audit", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q35_scaling_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_circuit_breaker_audit", lambda run_label: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_circuit_breaker_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_feature_group_ablation", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_feature_ablation_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_bull_4h_pocket_ablation", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_bull_4h_pocket_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_leaderboard_candidate_probe", lambda: order.append("leaderboard") or _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_leaderboard_candidate_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_support_audit", lambda: order.append("q15") or _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_support_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_auto_propose", lambda run_label=None: _ok())
    monkeypatch.setattr(hb_parallel_runner, "save_summary", lambda *args, **kwargs: ({}, "/tmp/heartbeat_test_summary.json"))

    hb_parallel_runner.main(["--fast", "--hb", "test"])

    assert order == ["leaderboard", "q15"]


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
    assert diag["production_profile_role"]["role"] == "support_aware_production_profile"
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
                    "profile_split": {
                        "global_profile": "core_only",
                        "production_profile": "core_plus_macro",
                        "verdict": "dual_role_required",
                    },
                    "leaderboard_snapshot_created_at": "2026-04-14T06:51:24Z",
                    "alignment_evaluated_at": "2026-04-14T12:40:00Z",
                    "current_alignment_inputs_stale": False,
                    "current_alignment_recency": {"inputs_current": True},
                    "artifact_recency": {"alignment_snapshot_stale": True},
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
    assert diag["profile_split"]["verdict"] == "dual_role_required"
    assert diag["train_selected_profile"] == "core_plus_macro"
    assert diag["current_alignment_inputs_stale"] is False
    assert diag["current_alignment_recency"]["inputs_current"] is True
    assert diag["artifact_recency"]["alignment_snapshot_stale"] is True
    assert diag["live_current_structure_bucket_rows"] == 0
    assert diag["blocked_candidate_profiles"][0]["blocker_reason"] == "unsupported_exact_live_structure_bucket"


def test_refresh_train_prerequisites_runs_both_artifacts_when_train_is_needed(monkeypatch):
    calls = []

    def _feature_result():
        calls.append("feature_result")
        return {"success": True, "returncode": 0}

    def _feature_summary():
        calls.append("feature_summary")
        return {"recommended_profile": "core_plus_macro_plus_4h_structure_shift"}

    def _bull_result():
        calls.append("bull_result")
        return {"success": True, "returncode": 0}

    def _bull_summary():
        calls.append("bull_summary")
        return {"live_context": {"current_live_structure_bucket_rows": 90}}

    monkeypatch.setattr(hb_parallel_runner, "run_feature_group_ablation", _feature_result)
    monkeypatch.setattr(hb_parallel_runner, "collect_feature_ablation_diagnostics", _feature_summary)
    monkeypatch.setattr(hb_parallel_runner, "run_bull_4h_pocket_ablation", _bull_result)
    monkeypatch.setattr(hb_parallel_runner, "collect_bull_4h_pocket_diagnostics", _bull_summary)

    result = hb_parallel_runner.refresh_train_prerequisites(needs_train=True)

    assert calls == ["feature_result", "feature_summary", "bull_result", "bull_summary"]
    assert result["feature_ablation_summary"]["recommended_profile"] == "core_plus_macro_plus_4h_structure_shift"
    assert result["bull_pocket_summary"]["live_context"]["current_live_structure_bucket_rows"] == 90


def test_refresh_train_prerequisites_skips_artifacts_when_train_not_needed():
    assert hb_parallel_runner.refresh_train_prerequisites(needs_train=False) == {}
