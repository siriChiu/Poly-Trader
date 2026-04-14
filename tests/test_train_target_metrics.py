import json
from pathlib import Path
import sqlite3

import pandas as pd

from model import train as train_module


class _DummyModel:
    import numpy as _np
    feature_importances_ = _np.array([0.6, 0.4])

    def get_params(self):
        return {"n_estimators": 5, "max_depth": 2}

    def predict(self, X):
        return [1 if i % 2 else 0 for i in range(len(X))]


class _DummyFoldModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def fit(self, X, y, sample_weight=None):
        return self

    def predict(self, X):
        return [1 if i % 2 else 0 for i in range(len(X))]


def test_run_training_writes_target_specific_last_metrics(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("model").mkdir()
    conn = sqlite3.connect("poly_trader.db")
    conn.execute("CREATE TABLE model_metrics (timestamp TEXT, train_accuracy REAL, cv_accuracy REAL, cv_std REAL, n_features INTEGER, notes TEXT)")
    conn.commit()
    conn.close()

    X = pd.DataFrame({"feat_a": [0.1] * 80, "feat_b": [0.2] * 80})
    X.attrs["feature_profile"] = "core_plus_macro"
    X.attrs["feature_profile_meta"] = {"source": "test_fixture"}
    y = pd.Series(([0, 1] * 40), name="simulated_pyramid_win")
    y_return = pd.Series([0.01] * 80)

    monkeypatch.setattr(train_module, "load_training_data", lambda *args, **kwargs: (X, y, y_return))
    monkeypatch.setattr(train_module, "train_xgboost", lambda X, y: _DummyModel())
    monkeypatch.setattr(train_module, "fit_probability_calibrator", lambda model, X, y: {"kind": "stub"})
    monkeypatch.setattr(train_module, "save_model", lambda payload: None)
    monkeypatch.setattr(train_module.xgb, "XGBClassifier", _DummyFoldModel)

    assert train_module.run_training(session=None, target_col="simulated_pyramid_win") is True

    metrics = Path("model/last_metrics.json").read_text(encoding="utf-8")
    assert '"target_col": "simulated_pyramid_win"' in metrics
    assert '"feature_profile": "core_plus_macro"' in metrics
    assert '"n_features": 2' in metrics


def test_load_tw_ic_guardrail_reads_dynamic_window_and_recent_drift(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    dw_result = data_dir / "dw_result.json"
    drift_report = data_dir / "recent_drift_report.json"
    dw_result.write_text(
        json.dumps(
            {
                "raw_best_n": 600,
                "recommended_best_n": 5000,
                "guardrail_policy": {"disqualifying_alerts": ["constant_target", "regime_concentration"]},
                "600": {"alerts": ["label_imbalance", "regime_concentration"], "distribution_guardrail": True},
            }
        ),
        encoding="utf-8",
    )
    drift_report.write_text(
        json.dumps(
            {
                "primary_window": {
                    "window": "100",
                    "alerts": ["constant_target", "regime_concentration"],
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(train_module, "DW_RESULT_PATH", dw_result)
    monkeypatch.setattr(train_module, "RECENT_DRIFT_REPORT_PATH", drift_report)

    guardrail = train_module._load_tw_ic_guardrail()

    assert guardrail["recommended_best_n"] == 5000
    assert guardrail["raw_best_n"] == 600
    assert guardrail["raw_best_guardrailed"] is True
    assert guardrail["should_dampen_recent_window"] is True
    assert "recent_window=100" in guardrail["guardrail_reason"]



def test_build_time_decay_weights_damps_guardrailed_recent_window():
    weights, metadata = train_module._build_time_decay_weights(
        10,
        tau=2,
        guardrail={
            "primary_window": 3,
            "recommended_best_n": 5,
            "raw_best_n": 2,
            "should_dampen_recent_window": True,
            "guardrail_reason": "recent_window=3 alerts=['constant_target']",
        },
    )

    assert metadata["applied"] is True
    assert metadata["damped_recent_rows"] == 3
    assert metadata["recommended_best_n"] == 5
    assert weights[-1] == weights[-2] == weights[-3]
    assert weights[-1] < weights[-4]


def test_select_feature_profile_prefers_recommended_ablation_profile():
    all_columns = train_module.FEATURE_COLS + ["feat_eye_lag12", "feat_vix_x_eye"]
    profile, columns, meta = train_module.select_feature_profile(
        all_columns,
        target_col="simulated_pyramid_win",
        ablation_payload={
            "target_col": "simulated_pyramid_win",
            "recommended_profile": "core_plus_macro",
            "generated_at": "2026-04-14 08:05:22",
            "profiles": {
                "core_plus_macro": {
                    "cv_mean_accuracy": 0.73,
                    "cv_worst_accuracy": 0.46,
                    "cv_std_accuracy": 0.17,
                    "cv_mean_brier": 0.19,
                },
                "current_full": {
                    "cv_mean_accuracy": 0.65,
                    "cv_worst_accuracy": 0.45,
                    "cv_std_accuracy": 0.16,
                    "cv_mean_brier": 0.24,
                },
            },
        },
    )

    assert profile == "core_plus_macro"
    assert set(columns) == set(train_module.CORE_FEATURES + train_module.MACRO_FEATURES)
    assert meta["source"] == "feature_group_ablation.recommended_profile"


def test_select_feature_profile_falls_back_when_target_mismatches_ablation():
    all_columns = train_module.FEATURE_COLS + ["feat_eye_lag12", "feat_vix_x_eye"]
    profile, columns, meta = train_module.select_feature_profile(
        all_columns,
        target_col="simulated_pyramid_win",
        ablation_payload={
            "target_col": "label_spot_long_win",
            "recommended_profile": "current_full",
            "profiles": {
                "current_full": {
                    "cv_mean_accuracy": 0.99,
                    "cv_worst_accuracy": 0.99,
                    "cv_std_accuracy": 0.01,
                    "cv_mean_brier": 0.01,
                }
            },
        },
    )

    assert profile == train_module.STRONG_BASELINE_FEATURE_PROFILE
    assert set(columns) == set(train_module.CORE_FEATURES + train_module.MACRO_FEATURES)
    assert meta["source"] == "code_default"


def test_select_feature_profile_prefers_support_aware_bull_profile_when_exact_bucket_has_no_support():
    all_columns = train_module.FEATURE_COLS + ["feat_eye_lag12", "feat_vix_x_eye"]
    profile, columns, meta = train_module.select_feature_profile(
        all_columns,
        target_col="simulated_pyramid_win",
        ablation_payload={
            "target_col": "simulated_pyramid_win",
            "generated_at": "2026-04-14 10:34:00",
            "recommended_profile": "core_only",
            "profiles": {
                "core_only": {
                    "cv_mean_accuracy": 0.72,
                    "cv_worst_accuracy": 0.45,
                    "cv_std_accuracy": 0.18,
                    "cv_mean_brier": 0.20,
                },
                "core_plus_macro": {
                    "cv_mean_accuracy": 0.68,
                    "cv_worst_accuracy": 0.44,
                    "cv_std_accuracy": 0.16,
                    "cv_mean_brier": 0.19,
                },
            },
        },
        bull_pocket_payload={
            "target_col": "simulated_pyramid_win",
            "generated_at": "2026-04-14 10:35:00",
            "live_context": {
                "current_live_structure_bucket_rows": 0,
            },
            "cohorts": {
                "bull_supported_neighbor_buckets_proxy": {
                    "rows": 84,
                    "recommended_profile": "core_plus_macro",
                },
                "bull_collapse_q35": {
                    "rows": 250,
                    "recommended_profile": "core_plus_macro",
                },
            },
        },
    )

    assert profile == "core_plus_macro"
    assert set(columns) == set(train_module.CORE_FEATURES + train_module.MACRO_FEATURES)
    assert meta["source"] == "bull_4h_pocket_ablation.support_aware_profile"
    assert meta["support_cohort"] == "bull_supported_neighbor_buckets_proxy"
    assert meta["support_rows"] == 84



def test_select_support_aware_profile_prefers_exact_live_bucket_proxy_when_available():
    all_columns = train_module.FEATURE_COLS + ["feat_eye_lag12", "feat_vix_x_eye"]
    profile, columns, meta = train_module.select_feature_profile(
        all_columns,
        target_col="simulated_pyramid_win",
        ablation_payload={
            "target_col": "simulated_pyramid_win",
            "generated_at": "2026-04-14 10:34:00",
            "recommended_profile": "core_only",
            "profiles": {
                "core_only": {
                    "cv_mean_accuracy": 0.72,
                    "cv_worst_accuracy": 0.45,
                    "cv_std_accuracy": 0.18,
                    "cv_mean_brier": 0.20,
                },
                "core_plus_macro": {
                    "cv_mean_accuracy": 0.68,
                    "cv_worst_accuracy": 0.44,
                    "cv_std_accuracy": 0.16,
                    "cv_mean_brier": 0.19,
                },
            },
        },
        bull_pocket_payload={
            "target_col": "simulated_pyramid_win",
            "generated_at": "2026-04-14 10:35:00",
            "live_context": {
                "current_live_structure_bucket_rows": 0,
            },
            "cohorts": {
                "bull_live_exact_lane_bucket_proxy": {
                    "rows": 58,
                    "recommended_profile": "core_plus_macro",
                },
                "bull_exact_live_lane_proxy": {
                    "rows": 50,
                    "recommended_profile": "core_plus_macro",
                },
                "bull_supported_neighbor_buckets_proxy": {
                    "rows": 84,
                    "recommended_profile": "core_plus_macro",
                },
                "bull_collapse_q35": {
                    "rows": 250,
                    "recommended_profile": "core_plus_macro",
                },
            },
        },
    )

    assert profile == "core_plus_macro"
    assert set(columns) == set(train_module.CORE_FEATURES + train_module.MACRO_FEATURES)
    assert meta["source"] == "bull_4h_pocket_ablation.support_aware_profile"
    assert meta["support_cohort"] == "bull_live_exact_lane_bucket_proxy"
    assert meta["support_rows"] == 58
    assert meta["exact_live_bucket_rows"] == 0



def test_select_feature_profile_keeps_global_recommendation_when_exact_bucket_support_is_sufficient():
    all_columns = train_module.FEATURE_COLS + ["feat_eye_lag12", "feat_vix_x_eye"]
    profile, _, meta = train_module.select_feature_profile(
        all_columns,
        target_col="simulated_pyramid_win",
        ablation_payload={
            "target_col": "simulated_pyramid_win",
            "generated_at": "2026-04-14 10:34:00",
            "recommended_profile": "core_only",
            "profiles": {
                "core_only": {
                    "cv_mean_accuracy": 0.72,
                    "cv_worst_accuracy": 0.45,
                    "cv_std_accuracy": 0.18,
                    "cv_mean_brier": 0.20,
                },
                "core_plus_macro": {
                    "cv_mean_accuracy": 0.68,
                    "cv_worst_accuracy": 0.44,
                    "cv_std_accuracy": 0.16,
                    "cv_mean_brier": 0.19,
                },
            },
        },
        bull_pocket_payload={
            "target_col": "simulated_pyramid_win",
            "generated_at": "2026-04-14 10:35:00",
            "live_context": {
                "current_live_structure_bucket_rows": 75,
            },
            "cohorts": {
                "bull_supported_neighbor_buckets_proxy": {
                    "rows": 84,
                    "recommended_profile": "core_plus_macro",
                },
            },
        },
    )

    assert profile == "core_only"
    assert meta["source"] == "feature_group_ablation.recommended_profile"


def test_select_feature_profile_accepts_extended_ablation_profiles_from_report():
    all_columns = train_module.FEATURE_COLS + [
        "feat_eye_lag12",
        "feat_4h_bias50_lag12",
        "feat_4h_bias20_lag12",
        "feat_4h_bias200_lag12",
        "feat_4h_rsi14_lag12",
        "feat_4h_macd_hist_lag12",
        "feat_4h_vol_ratio_lag12",
    ]
    profile, columns, meta = train_module.select_feature_profile(
        all_columns,
        target_col="simulated_pyramid_win",
        ablation_payload={
            "target_col": "simulated_pyramid_win",
            "generated_at": "2026-04-14 10:34:00",
            "recommended_profile": "core_macro_plus_stable_4h",
            "profiles": {
                "core_only": {
                    "cv_mean_accuracy": 0.72,
                    "cv_worst_accuracy": 0.45,
                    "cv_std_accuracy": 0.18,
                    "cv_mean_brier": 0.20,
                },
                "core_macro_plus_stable_4h": {
                    "cv_mean_accuracy": 0.73,
                    "cv_worst_accuracy": 0.46,
                    "cv_std_accuracy": 0.17,
                    "cv_mean_brier": 0.19,
                },
                "current_full_no_bull_collapse_4h": {
                    "cv_mean_accuracy": 0.70,
                    "cv_worst_accuracy": 0.44,
                    "cv_std_accuracy": 0.17,
                    "cv_mean_brier": 0.20,
                },
            },
        },
        bull_pocket_payload={},
    )

    assert profile == "core_macro_plus_stable_4h"
    assert "feat_4h_bias50_lag12" in columns
    assert "feat_4h_bb_pct_b" not in columns
    assert meta["source"] == "feature_group_ablation.recommended_profile"
