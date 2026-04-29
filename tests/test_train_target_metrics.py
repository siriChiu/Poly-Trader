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


class _CaptureXGBClassifier:
    last_params = None

    def __init__(self, **kwargs):
        type(self).last_params = kwargs

    def fit(self, X, y, sample_weight=None):
        self.sample_weight = sample_weight
        return self


def test_train_xgboost_uses_hist_tree_method_for_heartbeat_budget(monkeypatch):
    monkeypatch.setattr(train_module.xgb, "XGBClassifier", _CaptureXGBClassifier)
    X = pd.DataFrame({"feat_a": [0.1, 0.2, 0.3, 0.4], "feat_b": [0.2, 0.3, 0.4, 0.5]})
    y = pd.Series([0, 1, 0, 1])

    train_module.train_xgboost(X, y)

    params = _CaptureXGBClassifier.last_params
    assert params["tree_method"] == "hist"
    assert params["n_jobs"] == train_module.DEFAULT_XGB_N_JOBS
    assert 1 <= params["n_jobs"] <= 4


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

    assert train_module.run_training(session=None, target_col="simulated_pyramid_win", max_cv_folds=2) is True

    metrics = json.loads(Path("model/last_metrics.json").read_text(encoding="utf-8"))
    assert metrics["target_col"] == "simulated_pyramid_win"
    assert metrics["feature_profile"] == "core_plus_macro"
    assert metrics["n_features"] == 2
    assert metrics["cv_folds"] == 2
    assert metrics["cv_max_folds"] == 2



def test_train_main_skip_regime_models_delegates_without_duplicate_preload(monkeypatch):
    class _DummySession:
        closed = False

        def close(self):
            self.closed = True

    session = _DummySession()
    calls = []

    import database.models as database_models

    monkeypatch.setattr(database_models, "init_db", lambda db_url: session)

    def _unexpected_preload(*args, **kwargs):
        raise AssertionError("main() should not call load_training_data before run_training(); run_training owns data loading")

    monkeypatch.setattr(train_module, "load_training_data", _unexpected_preload)
    monkeypatch.setattr(train_module, "run_training", lambda received_session, **kwargs: calls.append((received_session, kwargs)) or True)

    assert train_module.main(["--skip-regime-models", "--max-cv-folds", "2"]) is True
    assert calls == [(session, {"max_cv_folds": 2})]
    assert session.closed is True



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



def test_select_feature_profile_ignores_broad_q35_reference_when_exact_bucket_has_no_support():
    all_columns = train_module.FEATURE_COLS + ["feat_eye_lag12", "feat_vix_x_eye"]
    profile, columns, meta = train_module.select_feature_profile(
        all_columns,
        target_col="simulated_pyramid_win",
        ablation_payload={
            "target_col": "simulated_pyramid_win",
            "generated_at": "2026-04-29 04:03:58",
            "recommended_profile": "core_plus_macro",
            "profiles": {
                "core_plus_macro": {
                    "cv_mean_accuracy": 0.58,
                    "cv_worst_accuracy": 0.54,
                    "cv_std_accuracy": 0.02,
                    "cv_mean_brier": 0.21,
                },
                "core_plus_macro_plus_all_4h": {
                    "cv_mean_accuracy": 0.67,
                    "cv_worst_accuracy": 0.50,
                    "cv_std_accuracy": 0.16,
                    "cv_mean_brier": 0.25,
                },
            },
        },
        bull_pocket_payload={
            "target_col": "simulated_pyramid_win",
            "generated_at": "2026-04-29 04:03:58",
            "live_context": {
                "current_live_structure_bucket_rows": 0,
            },
            "support_pathology_summary": {
                "exact_bucket_root_cause": "same_lane_exists_but_q65_missing",
            },
            "cohorts": {
                "bull_collapse_q35": {
                    "rows": 943,
                    "recommended_profile": "core_plus_macro_plus_all_4h",
                },
            },
        },
    )

    assert profile == "core_plus_macro"
    assert set(columns) == set(train_module.CORE_FEATURES + train_module.MACRO_FEATURES)
    assert meta["source"] == "feature_group_ablation.recommended_profile"



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



def test_select_feature_profile_prefers_exact_supported_bull_profile_when_bucket_support_is_sufficient():
    all_columns = train_module.FEATURE_COLS + [
        "feat_eye_lag12",
        "feat_vix_x_eye",
        "feat_4h_dist_swing_low",
        "feat_4h_dist_bb_lower",
        "feat_4h_bb_pct_b",
    ]
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
                "core_plus_macro_plus_4h_structure_shift": {
                    "cv_mean_accuracy": 0.76,
                    "cv_worst_accuracy": 0.46,
                    "cv_std_accuracy": 0.15,
                    "cv_mean_brier": 0.18,
                },
            },
        },
        bull_pocket_payload={
            "target_col": "simulated_pyramid_win",
            "generated_at": "2026-04-14 10:35:00",
            "live_context": {
                "current_live_structure_bucket_rows": 75,
            },
            "support_pathology_summary": {
                "exact_bucket_root_cause": "exact_bucket_supported",
            },
            "cohorts": {
                "exact_live_bucket": {
                    "rows": 75,
                    "recommended_profile": None,
                },
                "bull_all": {
                    "rows": 759,
                    "recommended_profile": "core_plus_macro_plus_4h_structure_shift",
                },
                "bull_supported_neighbor_buckets_proxy": {
                    "rows": 84,
                    "recommended_profile": "core_plus_macro",
                },
            },
        },
    )

    assert profile == "core_plus_macro_plus_4h_structure_shift"
    assert set(columns) == set(
        train_module.CORE_FEATURES
        + train_module.MACRO_FEATURES
        + ["feat_4h_dist_swing_low", "feat_4h_dist_bb_lower", "feat_4h_bb_pct_b"]
    )
    assert meta["source"] == "bull_4h_pocket_ablation.exact_supported_profile"
    assert meta["support_cohort"] == "bull_all"
    assert meta["support_rows"] == 759
    assert meta["exact_live_bucket_rows"] == 75


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
