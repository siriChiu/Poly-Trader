import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "bull_4h_pocket_ablation.py"
spec = importlib.util.spec_from_file_location("bull_4h_pocket_ablation_test_module", MODULE_PATH)
bull_4h_pocket_ablation = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bull_4h_pocket_ablation)


def test_load_frame_accepts_feature_group_source_meta(monkeypatch):
    x = bull_4h_pocket_ablation.pd.DataFrame(
        {
            "feat_eye": [0.1, 0.2],
            "feat_4h_bias50": [0.3, 0.4],
        }
    )
    y = bull_4h_pocket_ablation.pd.Series([1, 0])
    regimes = bull_4h_pocket_ablation.pd.Series(["bull", "bear"])
    source_meta = {"target_col": "simulated_pyramid_win"}

    monkeypatch.setattr(
        bull_4h_pocket_ablation.feature_group_module,
        "_load_training_frame",
        lambda: (x.copy(), y.copy(), regimes.copy(), source_meta.copy()),
    )

    frame, got_y, got_regimes = bull_4h_pocket_ablation._load_frame()

    assert list(frame["regime_label"]) == ["bull", "bear"]
    assert got_y.tolist() == [1, 0]
    assert got_regimes.tolist() == ["bull", "bear"]


def test_load_frame_with_source_meta_returns_source_meta(monkeypatch):
    x = bull_4h_pocket_ablation.pd.DataFrame({"feat_eye": [0.1]})
    y = bull_4h_pocket_ablation.pd.Series([1])
    regimes = bull_4h_pocket_ablation.pd.Series(["bull"])
    source_meta = {
        "label_rows": 21913,
        "latest_label_timestamp": "2026-04-17 04:05:06",
        "horizon_minutes": 1440,
        "target_col": "simulated_pyramid_win",
    }

    monkeypatch.setattr(
        bull_4h_pocket_ablation.feature_group_module,
        "_load_training_frame",
        lambda: (x.copy(), y.copy(), regimes.copy(), source_meta.copy()),
    )

    frame, got_y, got_regimes, got_source_meta = bull_4h_pocket_ablation._load_frame_with_source_meta()

    assert list(frame["regime_label"]) == ["bull"]
    assert got_y.tolist() == [1]
    assert got_regimes.tolist() == ["bull"]
    assert got_source_meta == source_meta


def test_live_context_reuses_runtime_support_when_exact_lane_rows_are_zero(tmp_path, monkeypatch):
    live_probe = tmp_path / "live_predict_probe.json"
    live_probe.write_text(
        bull_4h_pocket_ablation.json.dumps(
            {
                "feature_timestamp": "2026-04-18 08:18:48.555339",
                "regime_label": "bull",
                "regime_gate": "CAUTION",
                "entry_quality_label": "B",
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                "current_live_structure_bucket_rows": 100,
                "support_route_verdict": "exact_bucket_supported",
                "support_route_deployable": True,
                "support_progress": {
                    "status": "exact_supported",
                    "current_rows": 100,
                    "minimum_support_rows": 50,
                },
                "decision_quality_scope_diagnostics": {
                    "regime_label+regime_gate+entry_quality_label": {
                        "rows": 0,
                        "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                        "current_live_structure_bucket_rows": 0,
                        "current_live_structure_bucket_metrics": None,
                        "recent500_structure_bucket_counts": {},
                    },
                    "regime_gate": {
                        "rows": 200,
                        "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                        "current_live_structure_bucket_rows": 100,
                        "current_live_structure_bucket_metrics": {
                            "rows": 100,
                            "win_rate": 0.46,
                            "avg_pnl": 0.0014,
                            "avg_quality": 0.1281,
                            "avg_drawdown_penalty": 0.2018,
                            "avg_time_underwater": 0.5549,
                        },
                        "recent500_structure_bucket_counts": {
                            "CAUTION|structure_quality_caution|q35": 100,
                            "CAUTION|structure_quality_caution|q15": 96,
                        },
                        "recent500_regime_counts": {
                            "bull": 196,
                            "chop": 4,
                        },
                        "recent500_dominant_regime": {
                            "regime": "bull",
                            "count": 196,
                            "share": 0.98,
                        },
                        "recent_pathology": {
                            "applied": False,
                            "window": 100,
                            "alerts": [],
                            "reason": None,
                            "summary": None,
                        },
                        "spillover_vs_exact_live_lane": {
                            "worst_extra_regime_gate_feature_snapshot": {
                                "feat_4h_bias200": {
                                    "current_mean": 6.3681,
                                    "reference_mean": None,
                                    "mean_delta": None,
                                }
                            }
                        },
                    },
                    "regime_gate+entry_quality_label": {
                        "rows": 0,
                        "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                        "current_live_structure_bucket_rows": 0,
                        "current_live_structure_bucket_metrics": None,
                        "recent500_structure_bucket_counts": {},
                        "recent500_regime_counts": {},
                        "recent500_dominant_regime": None,
                        "recent_pathology": {
                            "applied": False,
                            "window": 0,
                            "alerts": [],
                            "reason": None,
                            "summary": None,
                        },
                    },
                    "regime_label+entry_quality_label": {
                        "rows": 0,
                        "current_live_structure_bucket_rows": 0,
                        "current_live_structure_bucket_metrics": None,
                        "recent500_structure_bucket_counts": {},
                    },
                    "pathology_consensus": {
                        "worst_pathology_scope": None,
                        "shared_top_shift_features": [],
                    },
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(bull_4h_pocket_ablation, "LIVE_PROBE_PATH", live_probe)

    context = bull_4h_pocket_ablation._live_context()

    assert context["support_route_verdict"] == "exact_bucket_supported"
    assert context["current_live_structure_bucket_rows"] == 100
    assert context["broad_scope_source"] == "regime_gate"
    assert context["broad_scope_rows"] == 200
    assert context["broad_current_live_structure_bucket_rows"] == 100
    assert context["supported_neighbor_buckets"] == ["CAUTION|structure_quality_caution|q15"]
    assert context["broad_recent500_regime_counts"] == {"bull": 196, "chop": 4}
    assert context["collapse_feature_snapshot"]["feat_4h_bias200"]["current_mean"] == 6.3681


def test_main_refresh_live_context_reuses_reference_profiles_but_clears_live_specific_profiles(tmp_path, monkeypatch):
    out_json = tmp_path / "bull_4h_pocket_ablation.json"
    out_md = tmp_path / "bull_4h_pocket_ablation.md"
    monkeypatch.setattr(bull_4h_pocket_ablation, "OUT_JSON", out_json)
    monkeypatch.setattr(bull_4h_pocket_ablation, "OUT_MD", out_md)
    monkeypatch.setattr(bull_4h_pocket_ablation, "_write_markdown", lambda payload: None)
    monkeypatch.setattr(
        bull_4h_pocket_ablation,
        "_live_context",
        lambda: {
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "current_live_structure_bucket_rows": 2,
            "supported_neighbor_buckets": ["CAUTION|structure_quality_caution|q15"],
            "exact_scope_rows": 3,
            "broad_scope_rows": 5,
            "broad_current_live_structure_bucket_rows": 2,
        },
    )
    monkeypatch.setattr(bull_4h_pocket_ablation, "_build_proxy_boundary_diagnostics", lambda *args, **kwargs: {"verdict": "ok"})
    monkeypatch.setattr(bull_4h_pocket_ablation, "_build_exact_lane_bucket_diagnostics", lambda *args, **kwargs: {"verdict": "ok"})
    monkeypatch.setattr(
        bull_4h_pocket_ablation,
        "_support_pathology_summary",
        lambda payload: {
            "blocker_state": "exact_bucket_present_but_below_minimum",
            "preferred_support_cohort": "bull_live_exact_lane_bucket_proxy",
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 48,
            "recommended_action": "refresh current bucket only",
        },
    )

    frame = bull_4h_pocket_ablation.pd.DataFrame(
        {
            "feat_eye": [0.1, 0.2, 0.3, 0.4],
            "feat_nose": [0.5, 0.6, 0.7, 0.8],
            "feat_pulse": [0.2, 0.3, 0.4, 0.5],
            "feat_ear": [0.1, 0.1, 0.2, 0.2],
            "feat_4h_bias50": [1.0, 1.1, 1.2, 1.3],
            "feat_4h_bias200": [2.0, 2.1, 2.2, 2.3],
            "feat_4h_dist_swing_low": [0.2, 0.3, 0.4, 0.8],
            "feat_4h_dist_bb_lower": [0.2, 0.3, 0.5, 0.9],
            "feat_4h_bb_pct_b": [0.2, 0.4, 0.6, 0.8],
            "regime_label": ["bull", "bull", "bull", "bear"],
            "regime_gate": ["CAUTION", "CAUTION", "CAUTION", "ALLOW"],
            "regime_gate_reason": ["r1", "r2", "r3", "r4"],
            "structure_quality": [0.3, 0.4, 0.2, 0.8],
            "structure_bucket": [
                "CAUTION|structure_quality_caution|q35",
                "CAUTION|structure_quality_caution|q35",
                "CAUTION|structure_quality_caution|q15",
                "ALLOW|base_allow|q65",
            ],
            "entry_quality": [0.4, 0.45, 0.3, 0.7],
            "entry_quality_label": ["D", "D", "D", "B"],
        }
    )
    y = bull_4h_pocket_ablation.pd.Series([1, 0, 1, 0])
    regimes = bull_4h_pocket_ablation.pd.Series(frame["regime_label"])
    source_meta = {"target_col": "simulated_pyramid_win"}
    monkeypatch.setattr(
        bull_4h_pocket_ablation,
        "_load_frame_with_source_meta",
        lambda: (frame.copy(), y.copy(), regimes.copy(), source_meta.copy()),
    )
    monkeypatch.setattr(bull_4h_pocket_ablation, "_derive_live_bucket_columns", lambda df: df)

    out_json.write_text(
        bull_4h_pocket_ablation.json.dumps(
            {
                "cohorts": {
                    "bull_all": {
                        "rows": 99,
                        "base_win_rate": 0.6,
                        "recommended_profile": "core_plus_macro_plus_all_4h",
                        "profiles": {"core_plus_macro_plus_all_4h": {"cv_mean_accuracy": 0.61, "feature_count": 12}},
                    },
                    "bull_collapse_q35": {
                        "rows": 50,
                        "base_win_rate": 0.55,
                        "recommended_profile": "core_plus_macro",
                        "profiles": {"core_plus_macro": {"cv_mean_accuracy": 0.58, "feature_count": 8}},
                    },
                    "bull_exact_live_lane_proxy": {
                        "rows": 80,
                        "base_win_rate": 0.52,
                        "recommended_profile": "stale_profile",
                        "profiles": {"stale_profile": {"cv_mean_accuracy": 0.57}},
                    },
                    "bull_live_exact_lane_bucket_proxy": {
                        "rows": 40,
                        "base_win_rate": 0.5,
                        "recommended_profile": "stale_profile",
                        "profiles": {"stale_profile": {"cv_mean_accuracy": 0.56}},
                    },
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    bull_4h_pocket_ablation.main(["--refresh-live-context"])

    payload = bull_4h_pocket_ablation.json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["refresh_mode"] == "live_context_only"
    assert payload["live_specific_profiles_fresh"] is False
    assert payload["cohorts"]["bull_all"]["recommended_profile"] == "core_plus_macro_plus_all_4h"
    assert payload["cohorts"]["bull_collapse_q35"]["recommended_profile"] == "core_plus_macro"
    assert payload["cohorts"]["bull_exact_live_lane_proxy"]["recommended_profile"] is None
    assert payload["cohorts"]["bull_live_exact_lane_bucket_proxy"]["recommended_profile"] is None
    assert payload["cohorts"]["bull_exact_live_lane_proxy"]["rows"] == 3
    assert payload["cohorts"]["bull_live_exact_lane_bucket_proxy"]["rows"] == 2
    assert payload["cohorts"]["bull_supported_neighbor_buckets_proxy"]["rows"] == 1
