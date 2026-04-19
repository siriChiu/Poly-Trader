import json
from pathlib import Path
import sqlite3

import pandas as pd
import pytest

import backtesting.model_leaderboard as model_leaderboard_module
from backtesting.model_leaderboard import ModelLeaderboard
from server.routes import api as api_module
from server.routes.api import load_model_leaderboard_frame


@pytest.fixture
def leaderboard_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "leaderboard.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_eye REAL,
            feat_ear REAL,
            feat_nose REAL,
            feat_tongue REAL,
            feat_body REAL,
            feat_pulse REAL,
            feat_aura REAL,
            feat_mind REAL,
            feat_vix REAL,
            feat_dxy REAL,
            feat_rsi14 REAL,
            feat_macd_hist REAL,
            feat_atr_pct REAL,
            feat_vwap_dev REAL,
            feat_bb_pct_b REAL,
            feat_4h_bias50 REAL,
            feat_4h_bias20 REAL,
            feat_4h_bias200 REAL,
            feat_4h_rsi14 REAL,
            feat_4h_macd_hist REAL,
            feat_4h_bb_pct_b REAL,
            feat_4h_dist_bb_lower REAL,
            feat_4h_ma_order REAL,
            feat_4h_dist_swing_low REAL,
            feat_4h_vol_ratio REAL,
            feat_local_bottom_score REAL,
            feat_local_top_score REAL,
            feat_turning_point_score REAL
        );
        CREATE TABLE raw_market_data (
            timestamp TEXT,
            symbol TEXT,
            close_price REAL
        );
        CREATE TABLE labels (
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            label_spot_long_win INTEGER
        );
        """
    )

    ts = "2026-01-01 00:00:00"
    conn.execute(
        "INSERT INTO features_normalized VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (ts, "BTCUSDT", "bull", 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 11.0, 101.0, 0.55, 0.01, 0.02, 0.03, 0.8, -2.0, -1.0, -3.0, 45.0, 100.0, 0.4, -0.6, 1.0, 3.0, 1.2, 0.61, 0.47, 0.61),
    )
    conn.execute(
        "INSERT INTO raw_market_data VALUES (?,?,?)",
        (ts, "BTCUSDT", 50000.0),
    )
    # Intentionally mismatched symbol to validate timestamp fallback join.
    conn.execute(
        "INSERT INTO labels VALUES (?,?,?,?)",
        (ts, "BTC", 1440, 1),
    )
    conn.commit()
    conn.close()
    return db_path


def test_walk_forward_splits_handles_integer_month_count():
    timestamps = pd.date_range("2025-01-01", periods=500, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "label_spot_long_win": [i % 2 for i in range(len(timestamps))],
            "feat_4h_bias50": [0.0] * len(timestamps),
            "feat_nose": [0.5] * len(timestamps),
            "feat_pulse": [0.5] * len(timestamps),
            "feat_ear": [0.1] * len(timestamps),
        }
    )

    leaderboard = ModelLeaderboard(df)
    splits = leaderboard._get_walk_forward_splits()

    assert splits
    assert all(len(split) == 4 for split in splits)


def test_evaluate_model_prefers_latest_bounded_walk_forward_splits(monkeypatch):
    timestamps = pd.date_range("2024-01-01", periods=900, freq="12h")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "simulated_pyramid_win": [i % 2 for i in range(len(timestamps))],
            "feat_4h_bias50": [0.0] * len(timestamps),
            "feat_nose": [0.5] * len(timestamps),
            "feat_pulse": [0.5] * len(timestamps),
            "feat_ear": [0.1] * len(timestamps),
        }
    )
    leaderboard = ModelLeaderboard(df, target_col="simulated_pyramid_win")
    splits = leaderboard._get_walk_forward_splits()
    expected_indices = list(range(len(splits) - leaderboard.EVALUATION_MAX_FOLDS, len(splits)))

    monkeypatch.setattr(model_leaderboard_module, "MIN_TRAIN_SAMPLES", 1)
    monkeypatch.setattr(leaderboard, "_deployment_profile_candidates_for_model", lambda model_name: ["standard"])
    monkeypatch.setattr(
        leaderboard,
        "_feature_profile_candidates_for_frame",
        lambda feature_cols: [{"name": "core_only", "meta": {"source": "test"}}],
    )

    def fake_run_single_fold(train_df, test_df, model_name):
        fold = model_leaderboard_module.FoldResult(
            fold=0,
            train_start=str(train_df["timestamp"].min().date()),
            train_end=str(train_df["timestamp"].max().date()),
            test_start=str(test_df["timestamp"].min().date()),
            test_end=str(test_df["timestamp"].max().date()),
            train_samples=len(train_df),
            test_samples=len(test_df),
            total_trades=1,
            roi=0.01,
            win_rate=0.5,
            avg_entry_quality=0.56,
            avg_allowed_layers=1.0,
        )
        return fold, None, None, 0.61, 0.57

    monkeypatch.setattr(leaderboard, "_run_single_fold", fake_run_single_fold)

    score = leaderboard.evaluate_model("xgboost")

    assert score is not None
    assert [fold.fold for fold in score.folds] == expected_indices
    status = leaderboard.last_model_statuses["xgboost"]
    assert status["evaluation_fold_window"] == "latest_bounded_walk_forward"
    assert status["evaluation_fold_indices"] == expected_indices
    assert status["evaluation_fold_count"] == leaderboard.EVALUATION_MAX_FOLDS


def test_load_model_leaderboard_frame_falls_back_to_timestamp_join(leaderboard_db: Path):
    df = load_model_leaderboard_frame(str(leaderboard_db))

    assert not df.empty
    assert df.loc[0, "label_spot_long_win"] == 1
    assert df.loc[0, "close_price"] == 50000.0
    assert df.loc[0, "regime_label"] == "bull"
    assert df.loc[0, "feat_local_bottom_score"] == pytest.approx(0.61)
    assert df.loc[0, "feat_local_top_score"] == pytest.approx(0.47)


def test_load_model_leaderboard_frame_prefers_simulated_target_rows(tmp_path: Path):
    db_path = tmp_path / "leaderboard_simulated.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE features_normalized (
            timestamp TEXT,
            symbol TEXT,
            regime_label TEXT,
            feat_eye REAL,
            feat_ear REAL,
            feat_nose REAL,
            feat_tongue REAL,
            feat_body REAL,
            feat_pulse REAL,
            feat_aura REAL,
            feat_mind REAL,
            feat_vix REAL,
            feat_dxy REAL,
            feat_rsi14 REAL,
            feat_macd_hist REAL,
            feat_atr_pct REAL,
            feat_vwap_dev REAL,
            feat_bb_pct_b REAL,
            feat_4h_bias50 REAL,
            feat_4h_bias20 REAL,
            feat_4h_bias200 REAL,
            feat_4h_rsi14 REAL,
            feat_4h_macd_hist REAL,
            feat_4h_bb_pct_b REAL,
            feat_4h_dist_bb_lower REAL,
            feat_4h_ma_order REAL,
            feat_4h_dist_swing_low REAL,
            feat_4h_vol_ratio REAL,
            feat_local_bottom_score REAL,
            feat_local_top_score REAL,
            feat_turning_point_score REAL
        );
        CREATE TABLE raw_market_data (
            timestamp TEXT,
            symbol TEXT,
            close_price REAL
        );
        CREATE TABLE labels (
            timestamp TEXT,
            symbol TEXT,
            horizon_minutes INTEGER,
            label_spot_long_win INTEGER,
            simulated_pyramid_win INTEGER,
            simulated_pyramid_pnl REAL,
            simulated_pyramid_quality REAL,
            simulated_pyramid_drawdown_penalty REAL,
            simulated_pyramid_time_underwater REAL
        );
        """
    )
    ts = "2026-01-02 00:00:00"
    conn.execute(
        "INSERT INTO features_normalized VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (ts, "BTCUSDT", "bull", 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 11.0, 101.0, 0.55, 0.01, 0.02, 0.03, 0.8, -2.0, -1.0, -3.0, 45.0, 100.0, 0.4, -0.6, 1.0, 3.0, 1.2, 0.61, 0.47, 0.61),
    )
    conn.execute("INSERT INTO raw_market_data VALUES (?,?,?)", (ts, "BTCUSDT", 51000.0))
    conn.execute(
        "INSERT INTO labels VALUES (?,?,?,?,?,?,?,?,?)",
        (ts, "BTCUSDT", 1440, None, 1, 0.12, 0.45, 0.18, 0.25),
    )
    conn.commit()
    conn.close()

    df = load_model_leaderboard_frame(str(db_path))

    assert not df.empty
    assert "simulated_pyramid_win" in df.columns
    assert "simulated_pyramid_drawdown_penalty" in df.columns
    assert "simulated_pyramid_time_underwater" in df.columns
    assert "feat_4h_bias200" in df.columns
    assert "feat_4h_dist_bb_lower" in df.columns
    assert "feat_4h_vol_ratio" in df.columns
    assert pd.isna(df.loc[0, "label_spot_long_win"])
    assert df.loc[0, "simulated_pyramid_win"] == 1
    assert df.loc[0, "simulated_pyramid_drawdown_penalty"] == pytest.approx(0.18)
    assert df.loc[0, "simulated_pyramid_time_underwater"] == pytest.approx(0.25)
    assert df.loc[0, "feat_4h_bias200"] == pytest.approx(-3.0)
    assert df.loc[0, "feat_4h_dist_bb_lower"] == pytest.approx(-0.6)
    assert df.loc[0, "feat_4h_vol_ratio"] == pytest.approx(1.2)
    assert df.loc[0, "feat_local_bottom_score"] == pytest.approx(0.61)
    assert df.loc[0, "feat_local_top_score"] == pytest.approx(0.47)
    assert df.loc[0, "close_price"] == 51000.0


def test_supported_models_includes_catboost():
    assert "catboost" in ModelLeaderboard.SUPPORTED_MODELS


def test_build_model_leaderboard_payload_uses_bounded_refresh_shortlist(monkeypatch):
    refresh_calls = {}

    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=3, freq="D"),
            "close_price": [50000.0, 50010.0, 50020.0],
            "simulated_pyramid_win": [1, 0, 1],
            "feat_4h_bias50": [0.0, 0.0, 0.0],
            "feat_nose": [0.4, 0.5, 0.6],
            "feat_pulse": [0.6, 0.5, 0.4],
            "feat_ear": [0.1, 0.1, 0.1],
        }
    )

    monkeypatch.setattr(api_module, "load_model_leaderboard_frame", lambda db_path=None: df)
    monkeypatch.setattr(api_module, "_load_model_leaderboard_history", lambda db_path=None: [])
    monkeypatch.setattr(api_module, "_summarize_target_candidates", lambda *args, **kwargs: [])
    monkeypatch.setattr(api_module, "_serialize_model_scores", lambda scores, leaderboard: [])

    def _fake_run_all_models(self, model_names=None):
        refresh_calls["model_names"] = list(model_names or [])
        self.last_model_statuses = {
            name: {"status": "skipped", "reason": "test_shortlist", "detail": None}
            for name in refresh_calls["model_names"]
        }
        return []

    monkeypatch.setattr(ModelLeaderboard, "run_all_models", _fake_run_all_models)

    payload = api_module._build_model_leaderboard_payload()

    assert refresh_calls["model_names"] == ModelLeaderboard.REFRESH_MODELS
    assert payload["refresh_model_scope"] == "production_refresh_shortlist"
    assert payload["evaluated_models"] == ModelLeaderboard.REFRESH_MODELS
    assert payload["excluded_supported_models"] == ["mlp", "svm", "ensemble"]



def test_score_model_from_folds_marks_zero_trade_rows_as_placeholders():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=4, freq="D"),
            "close_price": [50000.0, 50010.0, 50020.0, 50030.0],
            "simulated_pyramid_win": [1, 0, 1, 0],
            "feat_4h_bias50": [0.0, 0.0, 0.0, 0.0],
            "feat_nose": [0.4, 0.5, 0.6, 0.7],
            "feat_pulse": [0.6, 0.5, 0.4, 0.3],
            "feat_ear": [0.1, 0.1, 0.1, 0.1],
        }
    )
    leaderboard = ModelLeaderboard(df)
    fold = model_leaderboard_module.FoldResult(
        fold=0,
        train_start="2026-01-01",
        train_end="2026-01-02",
        test_start="2026-01-03",
        test_end="2026-01-04",
        train_samples=2,
        test_samples=2,
        total_trades=0,
        roi=0.0,
        win_rate=0.0,
        max_drawdown=0.0,
        profit_factor=0.0,
        trade_quality_score=0.0,
        avg_decision_quality_score=0.0,
        avg_expected_time_underwater=0.0,
    )

    score = leaderboard._score_model_from_folds("xgboost", [fold], [0.62], [0.55])

    assert score.ranking_eligible is False
    assert score.ranking_status == "no_trade_placeholder"
    assert score.placeholder_reason == "no_trades_generated_under_current_deployment_profile"
    assert score.ranking_warning is not None and "未產生任何交易" in score.ranking_warning
    assert score.reliability_score == 0.0
    assert score.return_power_score == 0.0
    assert score.risk_control_score == 0.0
    assert score.capital_efficiency_score == 0.0
    assert score.overall_score == 0.0
    assert score.composite_score == 0.0



def test_build_model_leaderboard_payload_separates_no_trade_placeholders(monkeypatch):
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=3, freq="D"),
            "close_price": [50000.0, 50010.0, 50020.0],
            "simulated_pyramid_win": [1, 0, 1],
            "feat_4h_bias50": [0.0, 0.0, 0.0],
            "feat_nose": [0.4, 0.5, 0.6],
            "feat_pulse": [0.6, 0.5, 0.4],
            "feat_ear": [0.1, 0.1, 0.1],
        }
    )

    monkeypatch.setattr(api_module, "load_model_leaderboard_frame", lambda db_path=None: df)
    monkeypatch.setattr(api_module, "_load_model_leaderboard_history", lambda db_path=None: [])
    monkeypatch.setattr(api_module, "_summarize_target_candidates", lambda *args, **kwargs: [])

    comparable = model_leaderboard_module.ModelScore(
        model_name="xgboost",
        deployment_profile="standard",
        feature_profile="core_only",
        feature_profile_source="feature_group_ablation.recommended_profile",
        avg_roi=0.04,
        avg_win_rate=0.58,
        avg_trades=12.0,
        overall_score=0.71,
        composite_score=0.71,
        reliability_score=0.63,
        return_power_score=0.67,
    )
    placeholder = model_leaderboard_module.ModelScore(
        model_name="rule_baseline",
        deployment_profile="standard",
        feature_profile="core_plus_macro_plus_4h_structure_shift",
        feature_profile_source="bull_4h_pocket_ablation.exact_supported_profile",
        avg_roi=0.0,
        avg_win_rate=0.0,
        avg_trades=0.0,
        overall_score=0.0,
        composite_score=0.0,
        ranking_eligible=False,
        ranking_status="no_trade_placeholder",
        ranking_warning="此模型在當前 deployment profile 下未產生任何交易；僅可視為 no-trade placeholder，不得當成正常排行榜前段結果。",
        placeholder_reason="no_trades_generated_under_current_deployment_profile",
    )

    def _fake_run_all_models(self, model_names=None):
        self.last_model_statuses = {
            "xgboost": {"status": "ok", "selected_feature_profile": "core_only", "selected_feature_profile_source": "feature_group_ablation.recommended_profile"},
            "rule_baseline": {"status": "ok", "selected_feature_profile": "core_plus_macro_plus_4h_structure_shift", "selected_feature_profile_source": "bull_4h_pocket_ablation.exact_supported_profile"},
        }
        return [comparable, placeholder]

    monkeypatch.setattr(ModelLeaderboard, "run_all_models", _fake_run_all_models)

    payload = api_module._build_model_leaderboard_payload()

    assert payload["count"] == 1
    assert payload["comparable_count"] == 1
    assert payload["placeholder_count"] == 1
    assert payload["evaluated_row_count"] == 2
    assert payload["leaderboard"][0]["model_name"] == "xgboost"
    assert payload["leaderboard"][0]["rank"] == 1
    assert payload["placeholder_rows"][0]["model_name"] == "rule_baseline"
    assert payload["placeholder_rows"][0]["rank"] is None
    assert payload["placeholder_rows"][0]["raw_rank"] == 2
    assert payload["quadrant_points"] == [
        {
            "model_name": "xgboost",
            "reliability_score": payload["leaderboard"][0]["reliability_score"],
            "return_power_score": payload["leaderboard"][0]["return_power_score"],
            "overall_score": payload["leaderboard"][0]["overall_score"],
        }
    ]
    assert payload["leaderboard_warning"] is not None and "no-trade placeholder" in payload["leaderboard_warning"]


def test_build_model_leaderboard_payload_includes_strategy_param_scan_when_placeholder_only(monkeypatch):
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=3, freq="D"),
            "close_price": [50000.0, 50010.0, 50020.0],
            "simulated_pyramid_win": [1, 0, 1],
            "feat_4h_bias50": [0.0, 0.0, 0.0],
            "feat_nose": [0.4, 0.5, 0.6],
            "feat_pulse": [0.6, 0.5, 0.4],
            "feat_ear": [0.1, 0.1, 0.1],
        }
    )

    monkeypatch.setattr(api_module, "load_model_leaderboard_frame", lambda db_path=None: df)
    monkeypatch.setattr(api_module, "_load_model_leaderboard_history", lambda db_path=None: [])
    monkeypatch.setattr(api_module, "_summarize_target_candidates", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        api_module,
        "_load_strategy_param_scan_summary",
        lambda: {
            "generated_at": "2026-04-18T11:44:36Z",
            "saved_strategy_count": 6,
            "best_strategy_candidates": [
                {
                    "name": "Auto Leaderboard · 重掃 lightgbm Hybrid #01",
                    "model_name": "lightgbm",
                    "roi": 0.3744,
                    "win_rate": 0.7183,
                    "total_trades": 71,
                }
            ],
            "warning": "canonical model leaderboard 仍是 placeholder-only；請改看策略參數重掃候選。",
        },
    )

    placeholder = model_leaderboard_module.ModelScore(
        model_name="rule_baseline",
        deployment_profile="standard",
        feature_profile="core_plus_macro_plus_4h_structure_shift",
        feature_profile_source="bull_4h_pocket_ablation.exact_supported_profile",
        avg_roi=0.0,
        avg_win_rate=0.0,
        avg_trades=0.0,
        overall_score=0.0,
        composite_score=0.0,
        ranking_eligible=False,
        ranking_status="no_trade_placeholder",
        ranking_warning="此模型在當前 deployment profile 下未產生任何交易；僅可視為 no-trade placeholder，不得當成正常排行榜前段結果。",
        placeholder_reason="no_trades_generated_under_current_deployment_profile",
    )

    def _fake_run_all_models(self, model_names=None):
        self.last_model_statuses = {"rule_baseline": {"status": "ok"}}
        return [placeholder]

    monkeypatch.setattr(ModelLeaderboard, "run_all_models", _fake_run_all_models)

    payload = api_module._build_model_leaderboard_payload()

    assert payload["count"] == 0
    assert payload["placeholder_count"] == 1
    assert payload["strategy_param_scan"]["saved_strategy_count"] == 6
    assert payload["strategy_param_scan"]["best_strategy_candidates"][0]["model_name"] == "lightgbm"
    assert "placeholder-only" in payload["strategy_param_scan"]["warning"]


def test_target_candidate_summary_reuses_refresh_shortlist(monkeypatch):
    calls = []

    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=4, freq="D"),
            "close_price": [50000.0, 50010.0, 50020.0, 50030.0],
            "simulated_pyramid_win": [1, 0, 1, 0],
            "label_spot_long_win": [1, 1, 0, 0],
            "feat_4h_bias50": [0.0, 0.0, 0.0, 0.0],
            "feat_nose": [0.4, 0.5, 0.6, 0.7],
            "feat_pulse": [0.6, 0.5, 0.4, 0.3],
            "feat_ear": [0.1, 0.1, 0.1, 0.1],
        }
    )

    def _fake_run_all_models(self, model_names=None):
        calls.append(list(model_names or []))
        self.last_model_statuses = {}
        return []

    monkeypatch.setattr(ModelLeaderboard, "run_all_models", _fake_run_all_models)
    monkeypatch.setattr(api_module, "_serialize_model_scores", lambda scores, leaderboard: [])

    summaries = api_module._summarize_target_candidates(df)

    assert summaries == [
        {
            "target_col": "simulated_pyramid_win",
            "is_canonical": True,
            "usage_note": "主訓練 / 主排行榜 target",
            "best_model": None,
            "model_count": 0,
        },
        {
            "target_col": "label_spot_long_win",
            "is_canonical": False,
            "usage_note": "僅供 path-aware 比較診斷，不作 canonical 排名主依據",
            "best_model": None,
            "model_count": 0,
        },
    ]
    assert calls == [ModelLeaderboard.REFRESH_MODELS, ModelLeaderboard.REFRESH_MODELS]


def test_serialize_model_scores_makes_fold_results_json_safe():
    score = model_leaderboard_module.ModelScore(
        model_name="xgboost",
        folds=[
            model_leaderboard_module.FoldResult(
                fold=0,
                train_start="2026-01-01",
                train_end="2026-02-01",
                test_start="2026-02-01",
                test_end="2026-03-01",
                train_samples=100,
                test_samples=20,
                deployment_profile="balanced_conviction",
                feature_profile="core_only",
                feature_profile_source="feature_group_ablation.recommended_profile",
            )
        ],
    )

    payload = api_module._serialize_model_scores([score], leaderboard=None)

    assert payload[0]["folds"] == [
        {
            "fold": 0,
            "train_start": "2026-01-01",
            "train_end": "2026-02-01",
            "test_start": "2026-02-01",
            "test_end": "2026-03-01",
            "train_samples": 100,
            "test_samples": 20,
            "roi": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "profit_factor": 0.0,
            "avg_entry_quality": 0.0,
            "avg_allowed_layers": 0.0,
            "trade_quality_score": 0.0,
            "regime_gate_allow_ratio": 0.0,
            "avg_decision_quality_score": 0.0,
            "avg_expected_win_rate": 0.0,
            "avg_expected_pyramid_quality": 0.0,
            "avg_expected_drawdown_penalty": 0.0,
            "avg_expected_time_underwater": 0.0,
            "deployment_profile": "balanced_conviction",
            "feature_profile": "core_only",
            "feature_profile_source": "feature_group_ablation.recommended_profile",
        }
    ]
    json.dumps(payload, ensure_ascii=False)


def test_model_leaderboard_defaults_to_simulated_target():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=2, freq="D"),
            "close_price": [50000, 50010],
            "label_spot_long_win": [0, 1],
            "simulated_pyramid_win": [1, 1],
            "feat_4h_bias50": [0.0, 0.0],
            "feat_4h_bias200": [0.0, 0.0],
            "feat_nose": [0.4, 0.5],
            "feat_pulse": [0.6, 0.6],
            "feat_ear": [0.1, 0.1],
        }
    )

    leaderboard = ModelLeaderboard(df)

    assert leaderboard.target_col == "simulated_pyramid_win"


def test_build_strategy_params_uses_evidence_driven_profile_for_random_forest():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=2, freq="D"),
            "close_price": [50000, 50010],
            "simulated_pyramid_win": [1, 0],
            "feat_4h_bias50": [0.0, 0.0],
            "feat_4h_bias200": [0.0, 0.0],
            "feat_nose": [0.4, 0.5],
            "feat_pulse": [0.6, 0.6],
            "feat_ear": [0.1, 0.1],
        }
    )
    leaderboard = ModelLeaderboard(df)

    params = leaderboard._build_strategy_params("random_forest")

    assert params["deployment_profile"] == "stable_turning_point_all_regimes_relaxed_v1"
    assert params["entry"]["allowed_regimes"] == ["bear", "bull", "chop", "unknown"]
    assert params["entry"]["top_k_percent"] == pytest.approx(0.0)
    assert params["turning_point"]["enabled"] is True
    assert params["turning_point"]["bottom_score_min"] == pytest.approx(0.56)


def test_deployment_profile_candidates_include_scan_backed_best_when_artifact_exists():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=2, freq="D"),
            "close_price": [50000, 50010],
            "simulated_pyramid_win": [1, 0],
            "feat_4h_bias50": [0.0, 0.0],
            "feat_4h_bias200": [0.0, 0.0],
            "feat_nose": [0.4, 0.5],
            "feat_pulse": [0.6, 0.6],
            "feat_ear": [0.1, 0.1],
        }
    )
    leaderboard = ModelLeaderboard(df)
    leaderboard._strategy_param_scan_payload = {
        "scan_results": [
            {
                "model_name": "xgboost",
                "best": {
                    "params": {
                        "model_name": "xgboost",
                        "entry": {"bias50_max": 3.0, "confidence_min": 0.55, "entry_quality_min": 0.5, "allowed_regimes": ["bull", "chop"]},
                        "stop_loss": -0.05,
                        "turning_point": {"enabled": True, "bottom_score_min": 0.56, "top_score_take_profit": 0.8},
                        "editor_modules": ["turning_point"],
                    }
                },
            }
        ]
    }

    candidates = leaderboard._deployment_profile_candidates_for_model("xgboost")

    assert candidates[0] == "scan_backed_best"
    assert "balanced_conviction" in candidates


def test_build_strategy_params_uses_scan_backed_best_params_when_available():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=2, freq="D"),
            "close_price": [50000, 50010],
            "simulated_pyramid_win": [1, 0],
            "feat_4h_bias50": [0.0, 0.0],
            "feat_4h_bias200": [0.0, 0.0],
            "feat_nose": [0.4, 0.5],
            "feat_pulse": [0.6, 0.6],
            "feat_ear": [0.1, 0.1],
        }
    )
    leaderboard = ModelLeaderboard(df)
    leaderboard._strategy_param_scan_payload = {
        "scan_results": [
            {
                "model_name": "xgboost",
                "best": {
                    "params": {
                        "model_name": "xgboost",
                        "entry": {
                            "bias50_max": 3.0,
                            "confidence_min": 0.55,
                            "entry_quality_min": 0.5,
                            "allowed_regimes": ["bull", "chop", "bear", "unknown"],
                            "layer2_bias_max": 2.0,
                            "layer3_bias_max": 0.5,
                        },
                        "layers": [0.25, 0.25, 0.5],
                        "stop_loss": -0.05,
                        "take_profit_bias": 999.0,
                        "take_profit_roi": 999.0,
                        "turning_point": {"enabled": True, "bottom_score_min": 0.56, "top_score_take_profit": 0.8},
                        "editor_modules": ["turning_point"],
                    }
                },
            }
        ]
    }
    leaderboard._deployment_profile_override = "scan_backed_best"

    params = leaderboard._build_strategy_params("xgboost")

    assert params["deployment_profile"] == "scan_backed_best"
    assert params["entry"]["bias50_max"] == pytest.approx(3.0)
    assert params["entry"]["confidence_min"] == pytest.approx(0.55)
    assert params["stop_loss"] == pytest.approx(-0.05)
    assert params["turning_point"]["enabled"] is True
    assert params["turning_point"]["bottom_score_min"] == pytest.approx(0.56)


def test_deployment_profile_candidates_promote_matching_scan_signature_to_code_backed_profile():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=2, freq="D"),
            "close_price": [50000, 50010],
            "simulated_pyramid_win": [1, 0],
            "feat_4h_bias50": [0.0, 0.0],
            "feat_4h_bias200": [0.0, 0.0],
            "feat_nose": [0.4, 0.5],
            "feat_pulse": [0.6, 0.6],
            "feat_ear": [0.1, 0.1],
        }
    )
    leaderboard = ModelLeaderboard(df)
    leaderboard._strategy_param_scan_payload = {
        "scan_results": [
            {
                "model_name": "xgboost",
                "best": {
                    "params": {
                        "model_name": "xgboost",
                        "entry": {
                            "bias50_max": 3.0,
                            "nose_max": 0.4,
                            "pulse_min": 0.0,
                            "confidence_min": 0.55,
                            "entry_quality_min": 0.5,
                            "top_k_percent": 0.0,
                            "allowed_regimes": ["bull", "chop", "bear", "unknown"],
                            "layer2_bias_max": 2.0,
                            "layer3_bias_max": 0.5,
                        },
                        "layers": [0.25, 0.25, 0.5],
                        "stop_loss": -0.03,
                        "take_profit_bias": 999.0,
                        "take_profit_roi": 999.0,
                        "turning_point": {"enabled": True, "bottom_score_min": 0.56, "top_score_take_profit": 0.8, "min_profit_pct": 0.0},
                        "editor_modules": ["turning_point"],
                    }
                },
            }
        ]
    }

    candidates = leaderboard._deployment_profile_candidates_for_model("xgboost")
    leaderboard._deployment_profile_override = candidates[0]
    params = leaderboard._build_strategy_params("xgboost")

    assert candidates[0] == "stable_turning_point_all_regimes_strict_v1"
    assert "scan_backed_best" not in candidates
    assert params["deployment_profile"] == "stable_turning_point_all_regimes_strict_v1"
    assert params["entry"]["allowed_regimes"] == ["bear", "bull", "chop", "unknown"]
    assert params["entry"]["confidence_min"] == pytest.approx(0.55)
    assert params["stop_loss"] == pytest.approx(-0.03)


def test_evaluate_model_auto_selects_best_deployment_profile(monkeypatch):
    timestamps = pd.date_range("2025-01-01", periods=220, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "simulated_pyramid_win": [i % 2 for i in range(len(timestamps))],
            "feat_4h_bias50": [0.0] * len(timestamps),
            "feat_nose": [0.4] * len(timestamps),
            "feat_pulse": [0.6] * len(timestamps),
            "feat_ear": [0.1] * len(timestamps),
        }
    )
    leaderboard = ModelLeaderboard(df)
    monkeypatch.setattr("backtesting.model_leaderboard.MIN_TRAIN_SAMPLES", 50)
    monkeypatch.setattr(
        leaderboard,
        "_get_walk_forward_splits",
        lambda: [("2025-01-01", "2025-05-01", "2025-05-01", "2025-07-15")],
    )

    def fake_run_single_fold(train_df, test_df, model_name):
        profile = leaderboard._deployment_profile_override or leaderboard._default_deployment_profile_name(model_name)
        if profile == "balanced_conviction":
            fold = type("Fold", (), {
                "fold": 0,
                "train_start": "2025-01-01",
                "train_end": "2025-05-01",
                "test_start": "2025-05-01",
                "test_end": "2025-06-01",
                "train_samples": len(train_df),
                "test_samples": len(test_df),
                "roi": 0.14,
                "win_rate": 0.70,
                "total_trades": 10,
                "max_drawdown": 0.07,
                "sharpe_ratio": 0.0,
                "profit_factor": 1.60,
                "avg_entry_quality": 0.78,
                "avg_allowed_layers": 2.1,
                "trade_quality_score": 0.74,
                "regime_gate_allow_ratio": 0.88,
                "avg_decision_quality_score": 0.66,
                "avg_expected_win_rate": 0.81,
                "avg_expected_pyramid_quality": 0.58,
                "avg_expected_drawdown_penalty": 0.12,
                "avg_expected_time_underwater": 0.16,
                "deployment_profile": profile,
            })()
            return fold, None, object(), 0.73, 0.68

        fold = type("Fold", (), {
            "fold": 0,
            "train_start": "2025-01-01",
            "train_end": "2025-05-01",
            "test_start": "2025-05-01",
            "test_end": "2025-06-01",
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "roi": 0.16,
            "win_rate": 0.58,
            "total_trades": 12,
            "max_drawdown": 0.23,
            "sharpe_ratio": 0.0,
            "profit_factor": 1.08,
            "avg_entry_quality": 0.49,
            "avg_allowed_layers": 1.0,
            "trade_quality_score": 0.36,
            "regime_gate_allow_ratio": 0.42,
            "avg_decision_quality_score": 0.18,
            "avg_expected_win_rate": 0.53,
            "avg_expected_pyramid_quality": 0.28,
            "avg_expected_drawdown_penalty": 0.32,
            "avg_expected_time_underwater": 0.52,
            "deployment_profile": profile,
        })()
        return fold, None, object(), 0.79, 0.61

    monkeypatch.setattr(leaderboard, "_run_single_fold", fake_run_single_fold)

    score = leaderboard.evaluate_model("xgboost")

    assert score is not None
    assert score.deployment_profile == "balanced_conviction"
    assert leaderboard.last_model_statuses["xgboost"]["selected_deployment_profile"] == "balanced_conviction"
    assert "standard" in leaderboard.last_model_statuses["xgboost"]["deployment_profiles_evaluated"]



def test_evaluate_model_prefers_code_backed_promoted_profile_when_scores_tie(monkeypatch):
    timestamps = pd.date_range("2025-01-01", periods=220, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "simulated_pyramid_win": [i % 2 for i in range(len(timestamps))],
            "feat_4h_bias50": [0.0] * len(timestamps),
            "feat_nose": [0.4] * len(timestamps),
            "feat_pulse": [0.6] * len(timestamps),
            "feat_ear": [0.1] * len(timestamps),
        }
    )
    leaderboard = ModelLeaderboard(df)
    monkeypatch.setattr("backtesting.model_leaderboard.MIN_TRAIN_SAMPLES", 50)
    monkeypatch.setattr(
        leaderboard,
        "_get_walk_forward_splits",
        lambda: [("2025-01-01", "2025-05-01", "2025-05-01", "2025-07-15")],
    )
    monkeypatch.setattr(
        leaderboard,
        "_deployment_profile_candidates_for_model",
        lambda model_name: ["scan_backed_best", "stable_turning_point_bull_chop_strict_v1"],
    )
    monkeypatch.setattr(
        leaderboard,
        "_feature_profile_candidates_for_frame",
        lambda feature_cols: [{"name": "core_only", "columns": feature_cols, "meta": {"source": "feature_group_ablation.recommended_profile"}}],
    )

    def fake_run_single_fold(train_df, test_df, model_name):
        profile = leaderboard._deployment_profile_override or "scan_backed_best"
        fold = type("Fold", (), {
            "fold": 0,
            "train_start": "2025-01-01",
            "train_end": "2025-05-01",
            "test_start": "2025-05-01",
            "test_end": "2025-06-01",
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "roi": 0.18,
            "win_rate": 0.74,
            "total_trades": 9,
            "max_drawdown": 0.09,
            "sharpe_ratio": 0.0,
            "profit_factor": 1.8,
            "avg_entry_quality": 0.79,
            "avg_allowed_layers": 2.2,
            "trade_quality_score": 0.71,
            "regime_gate_allow_ratio": 0.84,
            "avg_decision_quality_score": 0.67,
            "avg_expected_win_rate": 0.78,
            "avg_expected_pyramid_quality": 0.57,
            "avg_expected_drawdown_penalty": 0.11,
            "avg_expected_time_underwater": 0.18,
            "deployment_profile": profile,
            "feature_profile": "core_only",
            "feature_profile_source": "feature_group_ablation.recommended_profile",
        })()
        return fold, None, object(), 0.77, 0.71

    monkeypatch.setattr(leaderboard, "_run_single_fold", fake_run_single_fold)

    score = leaderboard.evaluate_model("logistic_regression")

    assert score is not None
    assert score.deployment_profile == "stable_turning_point_bull_chop_strict_v1"
    assert score.deployment_profile_source == "code_backed_promoted_from_scan"
    assert leaderboard.last_model_statuses["logistic_regression"]["selected_deployment_profile"] == "stable_turning_point_bull_chop_strict_v1"
    assert leaderboard.last_model_statuses["logistic_regression"]["selected_deployment_profile_source"] == "code_backed_promoted_from_scan"



def test_evaluate_model_auto_selects_best_feature_profile(monkeypatch):
    timestamps = pd.date_range("2025-01-01", periods=220, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "simulated_pyramid_win": [i % 2 for i in range(len(timestamps))],
            "feat_4h_bias50": [0.0] * len(timestamps),
            "feat_nose": [0.4] * len(timestamps),
            "feat_pulse": [0.6] * len(timestamps),
            "feat_ear": [0.1] * len(timestamps),
        }
    )
    leaderboard = ModelLeaderboard(df)
    monkeypatch.setattr("backtesting.model_leaderboard.MIN_TRAIN_SAMPLES", 50)
    monkeypatch.setattr(
        leaderboard,
        "_get_walk_forward_splits",
        lambda: [("2025-01-01", "2025-05-01", "2025-05-01", "2025-07-15")],
    )
    monkeypatch.setattr(
        leaderboard,
        "_feature_profile_candidates_for_frame",
        lambda feature_cols: [
            {"name": "core_only", "columns": feature_cols[:2], "meta": {"source": "feature_group_ablation.recommended_profile"}},
            {
                "name": "core_plus_macro",
                "columns": feature_cols,
                "meta": {
                    "source": "bull_4h_pocket_ablation.support_aware_profile",
                    "support_cohort": "bull_supported_neighbor_buckets_proxy",
                    "support_rows": 84,
                    "exact_live_bucket_rows": 0,
                },
            },
        ],
    )

    def fake_run_single_fold(train_df, test_df, model_name):
        deployment = leaderboard._deployment_profile_override or leaderboard._default_deployment_profile_name(model_name)
        feature_profile = leaderboard._feature_profile_override or "current_full"
        feature_source = (leaderboard._feature_profile_meta_override or {}).get("source", "code_default")
        if feature_profile == "core_only":
            fold = type("Fold", (), {
                "fold": 0,
                "train_start": "2025-01-01",
                "train_end": "2025-05-01",
                "test_start": "2025-05-01",
                "test_end": "2025-06-01",
                "train_samples": len(train_df),
                "test_samples": len(test_df),
                "roi": 0.12,
                "win_rate": 0.67,
                "total_trades": 10,
                "max_drawdown": 0.08,
                "sharpe_ratio": 0.0,
                "profit_factor": 1.35,
                "avg_entry_quality": 0.72,
                "avg_allowed_layers": 2.0,
                "trade_quality_score": 0.66,
                "regime_gate_allow_ratio": 0.84,
                "avg_decision_quality_score": 0.61,
                "avg_expected_win_rate": 0.79,
                "avg_expected_pyramid_quality": 0.52,
                "avg_expected_drawdown_penalty": 0.15,
                "avg_expected_time_underwater": 0.18,
                "deployment_profile": deployment,
                "feature_profile": feature_profile,
                "feature_profile_source": feature_source,
            })()
            return fold, None, object(), 0.72, 0.68

        fold = type("Fold", (), {
            "fold": 0,
            "train_start": "2025-01-01",
            "train_end": "2025-05-01",
            "test_start": "2025-05-01",
            "test_end": "2025-06-01",
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "roi": 0.06,
            "win_rate": 0.54,
            "total_trades": 12,
            "max_drawdown": 0.21,
            "sharpe_ratio": 0.0,
            "profit_factor": 1.05,
            "avg_entry_quality": 0.44,
            "avg_allowed_layers": 1.0,
            "trade_quality_score": 0.31,
            "regime_gate_allow_ratio": 0.40,
            "avg_decision_quality_score": 0.16,
            "avg_expected_win_rate": 0.52,
            "avg_expected_pyramid_quality": 0.21,
            "avg_expected_drawdown_penalty": 0.31,
            "avg_expected_time_underwater": 0.53,
            "deployment_profile": deployment,
            "feature_profile": feature_profile,
            "feature_profile_source": feature_source,
        })()
        return fold, None, object(), 0.75, 0.60

    monkeypatch.setattr(leaderboard, "_run_single_fold", fake_run_single_fold)

    score = leaderboard.evaluate_model("xgboost")

    assert score is not None
    assert score.feature_profile == "core_only"
    assert leaderboard.last_model_statuses["xgboost"]["selected_feature_profile"] == "core_only"
    assert "core_plus_macro" in leaderboard.last_model_statuses["xgboost"]["feature_profiles_evaluated"]


def test_evaluate_model_rejects_zero_exact_support_feature_profile_even_if_score_is_higher(monkeypatch):
    timestamps = pd.date_range("2025-01-01", periods=220, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "simulated_pyramid_win": [i % 2 for i in range(len(timestamps))],
            "feat_4h_bias50": [0.0] * len(timestamps),
            "feat_nose": [0.4] * len(timestamps),
            "feat_pulse": [0.6] * len(timestamps),
            "feat_ear": [0.1] * len(timestamps),
        }
    )
    leaderboard = ModelLeaderboard(df)
    monkeypatch.setattr("backtesting.model_leaderboard.MIN_TRAIN_SAMPLES", 50)
    monkeypatch.setattr(
        leaderboard,
        "_get_walk_forward_splits",
        lambda: [("2025-01-01", "2025-05-01", "2025-05-01", "2025-07-15")],
    )
    monkeypatch.setattr(
        leaderboard,
        "_feature_profile_candidates_for_frame",
        lambda feature_cols: [
            {"name": "core_only", "columns": feature_cols[:2], "meta": {"source": "feature_group_ablation.recommended_profile"}},
            {
                "name": "core_plus_macro",
                "columns": feature_cols,
                "meta": {
                    "source": "bull_4h_pocket_ablation.support_aware_profile",
                    "support_cohort": "bull_supported_neighbor_buckets_proxy",
                    "support_rows": 84,
                    "exact_live_bucket_rows": 0,
                    "minimum_support_rows": 20,
                },
            },
        ],
    )

    def fake_run_single_fold(train_df, test_df, model_name):
        deployment = leaderboard._deployment_profile_override or leaderboard._default_deployment_profile_name(model_name)
        feature_profile = leaderboard._feature_profile_override or "current_full"
        feature_source = (leaderboard._feature_profile_meta_override or {}).get("source", "code_default")
        if feature_profile == "core_plus_macro":
            fold = type("Fold", (), {
                "fold": 0,
                "train_start": "2025-01-01",
                "train_end": "2025-05-01",
                "test_start": "2025-05-01",
                "test_end": "2025-06-01",
                "train_samples": len(train_df),
                "test_samples": len(test_df),
                "roi": 0.24,
                "win_rate": 0.79,
                "total_trades": 18,
                "max_drawdown": 0.05,
                "sharpe_ratio": 0.0,
                "profit_factor": 1.8,
                "avg_entry_quality": 0.83,
                "avg_allowed_layers": 2.8,
                "trade_quality_score": 0.81,
                "regime_gate_allow_ratio": 0.91,
                "avg_decision_quality_score": 0.77,
                "avg_expected_win_rate": 0.88,
                "avg_expected_pyramid_quality": 0.64,
                "avg_expected_drawdown_penalty": 0.10,
                "avg_expected_time_underwater": 0.12,
                "deployment_profile": deployment,
                "feature_profile": feature_profile,
                "feature_profile_source": feature_source,
            })()
            return fold, None, object(), 0.84, 0.75

        fold = type("Fold", (), {
            "fold": 0,
            "train_start": "2025-01-01",
            "train_end": "2025-05-01",
            "test_start": "2025-05-01",
            "test_end": "2025-06-01",
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "roi": 0.10,
            "win_rate": 0.62,
            "total_trades": 10,
            "max_drawdown": 0.08,
            "sharpe_ratio": 0.0,
            "profit_factor": 1.30,
            "avg_entry_quality": 0.66,
            "avg_allowed_layers": 2.0,
            "trade_quality_score": 0.60,
            "regime_gate_allow_ratio": 0.78,
            "avg_decision_quality_score": 0.58,
            "avg_expected_win_rate": 0.73,
            "avg_expected_pyramid_quality": 0.49,
            "avg_expected_drawdown_penalty": 0.16,
            "avg_expected_time_underwater": 0.20,
            "deployment_profile": deployment,
            "feature_profile": feature_profile,
            "feature_profile_source": feature_source,
        })()
        return fold, None, object(), 0.72, 0.64

    monkeypatch.setattr(leaderboard, "_run_single_fold", fake_run_single_fold)

    score = leaderboard.evaluate_model("xgboost")

    assert score is not None
    assert score.feature_profile == "core_only"
    status = leaderboard.last_model_statuses["xgboost"]
    assert status["selected_feature_profile"] == "core_only"
    diagnostics = status["feature_profile_candidate_diagnostics"]
    blocked = next(item for item in diagnostics if item["feature_profile"] == "core_plus_macro")
    assert blocked["blocker_applied"] is True
    assert blocked["blocker_reason"] == "unsupported_exact_live_structure_bucket"
    assert blocked["rank"] > 1


def test_feature_profile_blocker_assessment_flags_under_minimum_exact_bucket():
    timestamps = pd.date_range("2025-01-01", periods=40, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "simulated_pyramid_win": [1 if i % 2 else 0 for i in range(len(timestamps))],
            "feat_a": [float(i) for i in range(len(timestamps))],
            "feat_b": [float(i % 5) for i in range(len(timestamps))],
        }
    )
    leaderboard = ModelLeaderboard(df, target_col="simulated_pyramid_win")

    blocker = leaderboard._feature_profile_blocker_assessment(
        {
            "source": "bull_4h_pocket_ablation.support_aware_profile",
            "support_cohort": "bull_exact_live_lane_proxy",
            "support_rows": 315,
            "exact_live_bucket_rows": 8,
            "minimum_support_rows": 50,
        }
    )

    assert blocker["blocker_applied"] is True
    assert blocker["blocker_reason"] == "under_minimum_exact_live_structure_bucket"


def test_model_leaderboard_can_use_simulated_target(monkeypatch):
    timestamps = pd.date_range("2025-01-01", periods=220, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "label_spot_long_win": [0] * len(timestamps),
            "simulated_pyramid_win": [1 if i % 3 else 0 for i in range(len(timestamps))],
            "feat_4h_bias50": [0.0] * len(timestamps),
            "feat_nose": [0.4] * len(timestamps),
            "feat_pulse": [0.6] * len(timestamps),
            "feat_ear": [0.1] * len(timestamps),
        }
    )
    leaderboard = ModelLeaderboard(df, target_col="simulated_pyramid_win")
    monkeypatch.setattr("backtesting.model_leaderboard.MIN_TRAIN_SAMPLES", 50)
    monkeypatch.setattr(
        leaderboard,
        "_get_walk_forward_splits",
        lambda: [("2025-01-01", "2025-05-01", "2025-05-01", "2025-07-15")],
    )

    captured = {}

    class DummyModel:
        def predict(self, X):
            return [1] * len(X)

        def predict_proba(self, X):
            import numpy as np
            return np.column_stack([1 - np.ones(len(X)) * 0.7, np.ones(len(X)) * 0.7])

    def fake_train_model(X_train, y_train, model_name):
        captured["y_train_mean"] = float(y_train.mean())
        return DummyModel()

    monkeypatch.setattr(leaderboard, "_train_model", fake_train_model)
    monkeypatch.setattr("backtesting.model_leaderboard.run_hybrid_backtest", lambda *args, **kwargs: type("Result", (), {
        "roi": 0.1,
        "win_rate": 0.6,
        "total_trades": 10,
        "max_drawdown": 0.08,
        "profit_factor": 1.2,
    })())

    score = leaderboard.evaluate_model("xgboost")

    assert score is not None
    assert leaderboard.target_col == "simulated_pyramid_win"
    assert captured["y_train_mean"] > 0.6


def test_run_single_fold_uses_true_4h_context_and_deployment_profile(monkeypatch):
    timestamps = pd.date_range("2025-01-01", periods=220, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "simulated_pyramid_win": [i % 2 for i in range(len(timestamps))],
            "feat_4h_bias50": [0.1] * len(timestamps),
            "feat_4h_bias200": [-2.5] * len(timestamps),
            "feat_4h_bb_pct_b": [0.4] * len(timestamps),
            "feat_4h_dist_bb_lower": [-0.8] * len(timestamps),
            "feat_4h_dist_swing_low": [2.2] * len(timestamps),
            "regime_label": ["bear"] * len(timestamps),
            "feat_local_bottom_score": [0.64] * len(timestamps),
            "feat_local_top_score": [0.28] * len(timestamps),
            "feat_nose": [0.4] * len(timestamps),
            "feat_pulse": [0.6] * len(timestamps),
            "feat_ear": [0.1] * len(timestamps),
        }
    )
    leaderboard = ModelLeaderboard(df)

    class DummyModel:
        def predict(self, X):
            import numpy as np
            return np.ones(len(X))

        def predict_proba(self, X):
            import numpy as np
            return np.column_stack([1 - np.ones(len(X)) * 0.7, np.ones(len(X)) * 0.7])

    monkeypatch.setattr(leaderboard, "_train_model", lambda *args, **kwargs: DummyModel())
    captured = {}

    def fake_run_hybrid_backtest(prices, timestamps, bias50, bias200, nose, pulse, ear, confidence, params, **kwargs):
        captured["bias200_first"] = bias200[0]
        captured["deployment_profile"] = params.get("deployment_profile")
        captured["allowed_regimes"] = params.get("entry", {}).get("allowed_regimes")
        captured["top_k_percent"] = params.get("entry", {}).get("top_k_percent")
        captured["regimes"] = kwargs.get("regimes")
        captured["local_bottom_score_first"] = kwargs.get("local_bottom_score")[0]
        captured["local_top_score_first"] = kwargs.get("local_top_score")[0]
        return type("Result", (), {
            "roi": 0.1,
            "win_rate": 0.6,
            "total_trades": 8,
            "max_drawdown": 0.08,
            "profit_factor": 1.3,
            "trades": [],
        })()

    monkeypatch.setattr(model_leaderboard_module, "run_hybrid_backtest", fake_run_hybrid_backtest)

    fold, _, _, _, _ = leaderboard._run_single_fold(df.iloc[:150], df.iloc[150:], "random_forest")

    assert captured["bias200_first"] == pytest.approx(-2.5)
    assert captured["deployment_profile"] == "stable_turning_point_all_regimes_relaxed_v1"
    assert captured["allowed_regimes"] == ["bear", "bull", "chop", "unknown"]
    assert captured["top_k_percent"] == pytest.approx(0.0)
    assert captured["regimes"][0] == "bear"
    assert captured["local_bottom_score_first"] == pytest.approx(0.64)
    assert captured["local_top_score_first"] == pytest.approx(0.28)
    assert fold.deployment_profile == "stable_turning_point_all_regimes_relaxed_v1"


def test_evaluate_model_records_average_profit_factor(monkeypatch):
    timestamps = pd.date_range("2025-01-01", periods=220, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "label_spot_long_win": [i % 2 for i in range(len(timestamps))],
            "feat_4h_bias50": [0.0] * len(timestamps),
            "feat_nose": [0.4] * len(timestamps),
            "feat_pulse": [0.6] * len(timestamps),
            "feat_ear": [0.1] * len(timestamps),
        }
    )
    leaderboard = ModelLeaderboard(df)
    monkeypatch.setattr("backtesting.model_leaderboard.MIN_TRAIN_SAMPLES", 50)

    monkeypatch.setattr(
        leaderboard,
        "_get_walk_forward_splits",
        lambda: [("2025-01-01", "2025-05-01", "2025-05-01", "2025-07-15")],
    )

    class DummyResult:
        roi = 0.12
        win_rate = 0.66
        total_trades = 12
        max_drawdown = 0.08
        profit_factor = 1.42

    def fake_run_single_fold(train_df, test_df, model_name):
        fold = type("Fold", (), {
            "fold": 0,
            "train_start": "2025-01-01",
            "train_end": "2025-05-01",
            "test_start": "2025-05-01",
            "test_end": "2025-06-01",
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "roi": 0.12,
            "win_rate": 0.66,
            "total_trades": 12,
            "max_drawdown": 0.08,
            "sharpe_ratio": 0.0,
            "profit_factor": 1.42,
            "avg_entry_quality": 0.74,
            "avg_allowed_layers": 2.0,
            "trade_quality_score": 0.71,
            "regime_gate_allow_ratio": 0.83,
            "avg_decision_quality_score": 0.58,
            "avg_expected_win_rate": 0.77,
            "avg_expected_pyramid_quality": 0.52,
            "avg_expected_drawdown_penalty": 0.14,
            "avg_expected_time_underwater": 0.18,
        })()
        return fold, None, DummyResult(), 0.72, 0.64

    monkeypatch.setattr(leaderboard, "_run_single_fold", fake_run_single_fold)

    score = leaderboard.evaluate_model("rule_baseline")

    assert score is not None
    assert score.avg_profit_factor == pytest.approx(1.42)
    assert score.avg_trade_quality == pytest.approx(0.71)
    assert score.avg_decision_quality_score == pytest.approx(0.58)
    assert score.avg_expected_drawdown_penalty == pytest.approx(0.14)
    assert score.regime_stability_score == pytest.approx(1.0)
    assert score.reliability_score > 0
    assert score.return_power_score > 0
    assert score.risk_control_score > 0
    assert score.capital_efficiency_score > 0
    assert score.overall_score == pytest.approx(score.composite_score)


def test_summarize_trade_quality_prefers_canonical_decision_quality_when_labels_exist():
    result = type("Result", (), {
        "trades": [{
            "entry_timestamp": "2025-05-01 00:00:00",
            "entry_quality": 0.82,
            "allowed_layers": 2,
            "regime_gate": "ALLOW",
        }],
        "max_drawdown": 0.09,
        "profit_factor": 1.5,
        "win_rate": 0.64,
    })()
    trade_frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2025-05-01 00:00:00"]),
            "simulated_pyramid_win": [0.8],
            "simulated_pyramid_quality": [0.5],
            "simulated_pyramid_drawdown_penalty": [0.12],
            "simulated_pyramid_time_underwater": [0.18],
        }
    )

    summary = model_leaderboard_module._summarize_trade_quality(result, trade_frame)

    assert summary["avg_expected_win_rate"] == pytest.approx(0.8)
    assert summary["avg_expected_pyramid_quality"] == pytest.approx(0.5)
    assert summary["avg_expected_drawdown_penalty"] == pytest.approx(0.12)
    assert summary["avg_expected_time_underwater"] == pytest.approx(0.18)
    assert summary["avg_decision_quality_score"] == pytest.approx(0.443)
    assert summary["trade_quality_score"] == pytest.approx(0.443)


def test_evaluate_model_composite_rewards_low_drawdown_and_trade_quality(monkeypatch):
    timestamps = pd.date_range("2025-01-01", periods=220, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "label_spot_long_win": [i % 2 for i in range(len(timestamps))],
            "feat_4h_bias50": [0.0] * len(timestamps),
            "feat_nose": [0.4] * len(timestamps),
            "feat_pulse": [0.6] * len(timestamps),
            "feat_ear": [0.1] * len(timestamps),
        }
    )
    leaderboard = ModelLeaderboard(df)
    monkeypatch.setattr("backtesting.model_leaderboard.MIN_TRAIN_SAMPLES", 50)
    monkeypatch.setattr(
        leaderboard,
        "_get_walk_forward_splits",
        lambda: [("2025-01-01", "2025-05-01", "2025-05-01", "2025-07-15")],
    )

    def fake_run_single_fold(train_df, test_df, model_name):
        if model_name == "xgboost":
            fold = type("Fold", (), {
                "fold": 0,
                "train_start": "2025-01-01",
                "train_end": "2025-05-01",
                "test_start": "2025-05-01",
                "test_end": "2025-06-01",
                "train_samples": len(train_df),
                "test_samples": len(test_df),
                "roi": 0.18,
                "win_rate": 0.62,
                "total_trades": 10,
                "max_drawdown": 0.26,
                "sharpe_ratio": 0.0,
                "profit_factor": 1.05,
                "avg_entry_quality": 0.52,
                "avg_allowed_layers": 1.0,
                "trade_quality_score": 0.41,
                "regime_gate_allow_ratio": 0.35,
                "avg_decision_quality_score": 0.22,
                "avg_expected_win_rate": 0.54,
                "avg_expected_pyramid_quality": 0.31,
                "avg_expected_drawdown_penalty": 0.33,
                "avg_expected_time_underwater": 0.51,
            })()
            return fold, None, object(), 0.88, 0.60
        fold = type("Fold", (), {
            "fold": 0,
            "train_start": "2025-01-01",
            "train_end": "2025-05-01",
            "test_start": "2025-05-01",
            "test_end": "2025-06-01",
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "roi": 0.11,
            "win_rate": 0.64,
            "total_trades": 14,
            "max_drawdown": 0.07,
            "sharpe_ratio": 0.0,
            "profit_factor": 1.55,
            "avg_entry_quality": 0.78,
            "avg_allowed_layers": 2.3,
            "trade_quality_score": 0.79,
            "regime_gate_allow_ratio": 0.86,
            "avg_decision_quality_score": 0.63,
            "avg_expected_win_rate": 0.81,
            "avg_expected_pyramid_quality": 0.59,
            "avg_expected_drawdown_penalty": 0.12,
            "avg_expected_time_underwater": 0.14,
        })()
        return fold, None, object(), 0.76, 0.67

    monkeypatch.setattr(leaderboard, "_run_single_fold", fake_run_single_fold)

    aggressive = leaderboard.evaluate_model("xgboost")
    quality_first = leaderboard.evaluate_model("rule_baseline")

    assert aggressive is not None and quality_first is not None
    assert aggressive.avg_roi > quality_first.avg_roi
    assert quality_first.composite_score > aggressive.composite_score
    assert quality_first.max_drawdown_score > aggressive.max_drawdown_score
    assert quality_first.avg_trade_quality > aggressive.avg_trade_quality


def test_evaluate_model_tracks_unavailable_dependency_reason(monkeypatch):
    timestamps = pd.date_range("2025-01-01", periods=220, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": [50000 + i for i in range(len(timestamps))],
            "label_spot_long_win": [i % 2 for i in range(len(timestamps))],
            "feat_4h_bias50": [0.0] * len(timestamps),
            "feat_nose": [0.4] * len(timestamps),
            "feat_pulse": [0.6] * len(timestamps),
            "feat_ear": [0.1] * len(timestamps),
        }
    )
    leaderboard = ModelLeaderboard(df, target_col="label_spot_long_win")
    monkeypatch.setattr("backtesting.model_leaderboard.MIN_TRAIN_SAMPLES", 50)
    monkeypatch.setattr(
        leaderboard,
        "_get_walk_forward_splits",
        lambda: [("2025-01-01", "2025-05-01", "2025-05-01", "2025-07-15")],
    )

    def fake_train_model(X_train, y_train, model_name):
        from backtesting.model_leaderboard import ModelUnavailableError
        raise ModelUnavailableError(model_name, "missing_dependency", "No module named 'lightgbm'")

    monkeypatch.setattr(leaderboard, "_train_model", fake_train_model)

    score = leaderboard.evaluate_model("lightgbm")

    assert score is None
    assert leaderboard.last_model_statuses["lightgbm"]["status"] == "unavailable"
    assert leaderboard.last_model_statuses["lightgbm"]["reason"] == "missing_dependency"


def test_build_model_leaderboard_payload_includes_skipped_models(monkeypatch):
    class FakeLeaderboard:
        def __init__(self, data_df, target_col="simulated_pyramid_win"):
            self.target_col = target_col
            self.last_model_statuses = {
                "lightgbm": {"status": "unavailable", "reason": "missing_dependency", "detail": "No module named 'lightgbm'"},
                "xgboost": {
                    "status": "ok",
                    "selected_deployment_profile": "balanced_conviction",
                    "selected_deployment_profile_label": "Balanced Conviction",
                    "selected_deployment_profile_source": "code_backed",
                    "deployment_profiles_evaluated": ["balanced_conviction", "standard"],
                    "selected_feature_profile": "core_only",
                    "selected_feature_profile_source": "feature_group_ablation.recommended_profile",
                    "selected_feature_profile_blocker_applied": False,
                    "selected_feature_profile_blocker_reason": None,
                    "feature_profiles_evaluated": ["core_only", "core_plus_macro"],
                    "feature_profile_candidate_diagnostics": [
                        {
                            "rank": 1,
                            "deployment_profile": "balanced_conviction",
                            "feature_profile": "core_only",
                            "blocker_applied": False,
                            "blocker_reason": None,
                        },
                        {
                            "rank": 2,
                            "deployment_profile": "balanced_conviction",
                            "feature_profile": "core_plus_macro",
                            "blocker_applied": True,
                            "blocker_reason": "unsupported_exact_live_structure_bucket",
                        },
                    ],
                },
            }

        def run_all_models(self, model_names):
            class Score:
                model_name = "xgboost"
                deployment_profile = "balanced_conviction"
                feature_profile = "core_only"
                feature_profile_source = "feature_group_ablation.recommended_profile"
                feature_profile_meta = {}
                avg_roi = 0.12
                avg_win_rate = 0.66
                avg_trades = 11
                avg_max_drawdown = 0.08
                avg_profit_factor = 1.4
                avg_entry_quality = 0.74
                avg_allowed_layers = 2.2
                avg_trade_quality = 0.71
                avg_decision_quality_score = 0.57
                avg_expected_win_rate = 0.79
                avg_expected_pyramid_quality = 0.55
                avg_expected_drawdown_penalty = 0.13
                avg_expected_time_underwater = 0.19
                regime_stability_score = 0.92
                trade_count_score = 0.55
                roi_score = 0.8
                max_drawdown_score = 0.77
                profit_factor_score = 0.27
                time_underwater_score = 0.68
                decision_quality_component = 0.57
                reliability_score = 0.73
                return_power_score = 0.61
                risk_control_score = 0.69
                capital_efficiency_score = 0.58
                overall_score = 0.66
                overfit_penalty = 0.4
                std_roi = 0.03
                train_accuracy = 0.72
                test_accuracy = 0.64
                train_test_gap = 0.08
                composite_score = 0.66
                folds = []

            return [Score()]

    monkeypatch.setattr(api_module, "load_model_leaderboard_frame", lambda db_path: pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=3, freq="D"),
        "close_price": [1.0, 2.0, 3.0],
        "simulated_pyramid_win": [1, 0, 1],
    }))
    monkeypatch.setattr("backtesting.model_leaderboard.ModelLeaderboard", FakeLeaderboard)

    payload = api_module._build_model_leaderboard_payload()

    assert payload["leaderboard"][0]["model_name"] == "xgboost"
    assert payload["leaderboard"][0]["deployment_profile"] == "balanced_conviction"
    assert payload["leaderboard"][0]["deployment_profile_label"] == "Balanced Conviction"
    assert payload["leaderboard"][0]["deployment_profile_source"] == "code_backed"
    assert payload["leaderboard"][0]["selected_deployment_profile"] == "balanced_conviction"
    assert payload["leaderboard"][0]["selected_deployment_profile_label"] == "Balanced Conviction"
    assert payload["leaderboard"][0]["selected_deployment_profile_source"] == "code_backed"
    assert payload["leaderboard"][0]["feature_profile"] == "core_only"
    assert payload["leaderboard"][0]["selected_feature_profile"] == "core_only"
    assert payload["leaderboard"][0]["selected_feature_profile_blocker_applied"] is False
    assert payload["leaderboard"][0]["selected_feature_profile_blocker_reason"] is None
    assert payload["leaderboard"][0]["feature_profile_candidate_diagnostics"][1]["blocker_reason"] == "unsupported_exact_live_structure_bucket"
    assert "core_plus_macro" in payload["leaderboard"][0]["feature_profiles_evaluated"]
    assert payload["leaderboard"][0]["model_tier"] == "core"
    assert payload["leaderboard"][0]["model_tier_label"] == "核心模型"
    assert payload["leaderboard"][0]["avg_trade_quality"] == pytest.approx(0.71)
    assert payload["leaderboard"][0]["avg_decision_quality_score"] == pytest.approx(0.57)
    assert payload["leaderboard"][0]["avg_expected_drawdown_penalty"] == pytest.approx(0.13)
    assert payload["leaderboard"][0]["regime_stability_score"] == pytest.approx(0.92)
    assert payload["leaderboard"][0]["overall_score"] == pytest.approx(0.66)
    assert payload["leaderboard"][0]["reliability_score"] == pytest.approx(0.73)
    assert payload["leaderboard"][0]["return_power_score"] == pytest.approx(0.61)
    assert payload["quadrant_points"][0]["model_name"] == "xgboost"
    assert payload["leaderboard"][0]["rank_delta"] == 0
    assert isinstance(payload["snapshot_history"], list)
    assert payload["storage"]["canonical_store"].startswith("sqlite:")
    assert payload["overfit_gap_threshold"] == pytest.approx(0.12)
    assert payload["leaderboard"][0]["overfit_penalty"] == pytest.approx(0.4)
    assert payload["skipped_models"][0]["model_name"] == "lightgbm"
    assert payload["skipped_models"][0]["reason"] == "missing_dependency"


def test_build_model_leaderboard_payload_moves_zero_trade_rows_to_placeholder_models(monkeypatch):
    class FakeLeaderboard:
        def __init__(self, data_df, target_col="simulated_pyramid_win"):
            self.target_col = target_col
            self.last_model_statuses = {"rule_baseline": {"status": "ok"}}

        def run_all_models(self, model_names):
            class Score:
                model_name = "rule_baseline"
                deployment_profile = "standard"
                feature_profile = "core_only"
                feature_profile_source = "feature_group_ablation.recommended_profile"
                avg_roi = 0.0
                avg_win_rate = 0.0
                avg_trades = 0
                avg_max_drawdown = 0.0
                avg_profit_factor = 0.0
                avg_entry_quality = 0.0
                avg_allowed_layers = 0.0
                avg_trade_quality = 0.0
                avg_decision_quality_score = 0.0
                avg_expected_win_rate = 0.0
                avg_expected_pyramid_quality = 0.0
                avg_expected_drawdown_penalty = 0.0
                avg_expected_time_underwater = 0.0
                regime_stability_score = 0.0
                trade_count_score = 0.0
                roi_score = 0.0
                max_drawdown_score = 0.0
                profit_factor_score = 0.0
                time_underwater_score = 0.0
                decision_quality_component = 0.0
                reliability_score = 0.62
                return_power_score = 0.0
                risk_control_score = 0.0
                capital_efficiency_score = 0.0
                overall_score = 0.62
                overfit_penalty = 0.0
                std_roi = 0.0
                train_accuracy = 0.0
                test_accuracy = 0.0
                train_test_gap = 0.0
                composite_score = 0.62
                folds = []

            return [Score()]

    monkeypatch.setattr(api_module, "load_model_leaderboard_frame", lambda db_path: pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=3, freq="D"),
        "close_price": [1.0, 2.0, 3.0],
        "simulated_pyramid_win": [1, 0, 1],
    }))
    monkeypatch.setattr("backtesting.model_leaderboard.ModelLeaderboard", FakeLeaderboard)

    payload = api_module._build_model_leaderboard_payload()

    assert payload["count"] == 0
    assert payload["leaderboard"] == []
    assert payload["placeholder_count"] == 1
    assert payload["placeholder_models"][0]["model_name"] == "rule_baseline"
    assert payload["placeholder_models"][0]["ranking_status"] == "no_trade_placeholder"
    assert payload["placeholder_models"][0]["avg_total_trades"] == 0.0
    assert payload["data_warning"] is not None


def test_summarize_target_candidates_prefers_non_overfit_best_model(monkeypatch):
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=4, freq="D"),
            "close_price": [1, 2, 3, 4],
            "label_spot_long_win": [0, 1, 0, 1],
            "simulated_pyramid_win": [1, 1, 0, 1],
        }
    )

    class FakeLeaderboard:
        def __init__(self, data_df, target_col="label_spot_long_win"):
            self.target_col = target_col

        def run_all_models(self, model_names):
            class Score:
                def __init__(self, model_name, gap, train_acc, roi, wr):
                    self.model_name = model_name
                    self.avg_roi = roi
                    self.avg_win_rate = wr
                    self.avg_trades = 11
                    self.avg_max_drawdown = 0.1
                    self.avg_profit_factor = 1.1
                    self.std_roi = 0.01
                    self.train_accuracy = train_acc
                    self.test_accuracy = max(0.0, train_acc - gap)
                    self.train_test_gap = gap
                    self.composite_score = roi
                    self.folds = []

            if self.target_col == "simulated_pyramid_win":
                return [Score("xgboost", 0.05, 0.82, 0.22, 0.68)]
            return [Score("xgboost", 0.16, 0.91, 0.30, 0.70), Score("logistic_regression", 0.04, 0.74, 0.12, 0.60)]

    monkeypatch.setattr("backtesting.model_leaderboard.ModelLeaderboard", FakeLeaderboard)
    monkeypatch.setattr(api_module, "_serialize_model_scores", api_module._serialize_model_scores)

    summary = api_module._summarize_target_candidates(df, 0.12, 0.90)

    assert len(summary) == 2
    path_aware = next(item for item in summary if item["target_col"] == "label_spot_long_win")
    simulated = next(item for item in summary if item["target_col"] == "simulated_pyramid_win")
    assert summary[0]["target_col"] == "simulated_pyramid_win"
    assert simulated["is_canonical"] is True
    assert simulated["usage_note"] == "主訓練 / 主排行榜 target"
    assert path_aware["is_canonical"] is False
    assert "僅供 path-aware 比較診斷" in path_aware["usage_note"]
    assert path_aware["best_model"]["model_name"] == "logistic_regression"
    assert simulated["best_model"]["model_name"] == "xgboost"


def test_api_model_leaderboard_returns_cached_payload_without_recompute(monkeypatch):
    monkeypatch.setattr(api_module, "MODEL_LB_CACHE_PATH", Path("/tmp/nonexistent_polytrader_cache.json"))
    monkeypatch.setattr(
        api_module,
        "_MODEL_LB_CACHE",
        {
            "payload": {"leaderboard": [{"model_name": "cached_model"}], "count": 1},
            "updated_at": 4102444800.0,
            "refreshing": False,
            "error": None,
        },
    )
    monkeypatch.setattr(api_module, "_ensure_model_leaderboard_refresh", lambda force=False: None)

    import asyncio
    result = asyncio.run(api_module.api_model_leaderboard())

    assert result["leaderboard"][0]["model_name"] == "cached_model"
    assert result["cached"] is True



def test_api_model_leaderboard_reload_newer_disk_cache_into_runtime(monkeypatch, tmp_path: Path):
    cache_path = tmp_path / "model_leaderboard_cache.json"
    disk_payload = {
        "leaderboard": [
            {
                "rank": 1,
                "model_name": "disk_model",
                "deployment_profile": "stable_turning_point_all_regimes_relaxed_v1",
                "selected_deployment_profile": "stable_turning_point_all_regimes_relaxed_v1",
                "selected_feature_profile": "core_only",
            }
        ],
        "count": 1,
        "comparable_count": 1,
        "placeholder_count": 0,
    }
    cache_path.write_text(
        json.dumps({"payload": disk_payload, "updated_at": 4102444800.0, "error": None}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(api_module, "MODEL_LB_CACHE_PATH", cache_path)
    monkeypatch.setattr(
        api_module,
        "_MODEL_LB_CACHE",
        {
            "payload": {"leaderboard": [{"model_name": "memory_model"}], "count": 1},
            "updated_at": 4102444700.0,
            "refreshing": False,
            "error": None,
        },
    )
    monkeypatch.setattr(api_module, "_ensure_model_leaderboard_refresh", lambda force=False: None)

    import asyncio
    result = asyncio.run(api_module.api_model_leaderboard())

    assert result["leaderboard"][0]["model_name"] == "disk_model"
    assert api_module._MODEL_LB_CACHE["payload"]["leaderboard"][0]["model_name"] == "disk_model"
    assert api_module._MODEL_LB_CACHE["updated_at"] == 4102444800.0



def test_api_model_leaderboard_prefers_newer_snapshot_over_older_disk_cache(monkeypatch, tmp_path: Path):
    cache_path = tmp_path / "model_leaderboard_cache.json"
    db_path = tmp_path / "leaderboard_snapshot.db"
    cache_payload = {
        "leaderboard": [
            {
                "rank": 1,
                "model_name": "cache_model",
                "deployment_profile": "standard",
                "selected_deployment_profile": "standard",
                "selected_feature_profile": "current_full",
            }
        ],
        "count": 1,
        "comparable_count": 1,
        "placeholder_count": 0,
    }
    snapshot_payload = {
        "leaderboard": [
            {
                "rank": 1,
                "model_name": "snapshot_model",
                "deployment_profile": "stable_turning_point_all_regimes_relaxed_v1",
                "selected_deployment_profile": "stable_turning_point_all_regimes_relaxed_v1",
                "selected_feature_profile": "core_only",
            }
        ],
        "count": 1,
        "comparable_count": 1,
        "placeholder_count": 0,
    }
    cache_path.write_text(
        json.dumps({"payload": cache_payload, "updated_at": 4102444700.0, "error": None}, ensure_ascii=False),
        encoding="utf-8",
    )
    conn = sqlite3.connect(db_path)
    try:
        api_module._ensure_model_leaderboard_tables(conn)
        conn.execute(
            "INSERT INTO leaderboard_model_snapshots(created_at, updated_at, target_col, model_count, payload_json) VALUES (?, ?, ?, ?, ?)",
            (
                "2100-01-01T00:00:00Z",
                4102444800.0,
                "simulated_pyramid_win",
                1,
                json.dumps(snapshot_payload, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(api_module, "MODEL_LB_CACHE_PATH", cache_path)
    monkeypatch.setattr(api_module, "DB_PATH", str(db_path))
    monkeypatch.setattr(
        api_module,
        "_MODEL_LB_CACHE",
        {
            "payload": {"leaderboard": [{"model_name": "memory_model"}], "count": 1},
            "updated_at": 4102444600.0,
            "refreshing": False,
            "error": None,
        },
    )
    monkeypatch.setattr(api_module, "_ensure_model_leaderboard_refresh", lambda force=False: None)

    import asyncio
    result = asyncio.run(api_module.api_model_leaderboard())

    assert result["leaderboard"][0]["model_name"] == "snapshot_model"
    assert result["leaderboard"][0]["selected_feature_profile"] == "core_only"
    assert api_module._MODEL_LB_CACHE["payload"]["leaderboard"][0]["model_name"] == "snapshot_model"
    assert api_module._MODEL_LB_CACHE["updated_at"] == 4102444800.0



def test_api_model_leaderboard_history_returns_recent_snapshot_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "lb_history.db"
    conn = sqlite3.connect(db_path)
    try:
        api_module._ensure_model_leaderboard_tables(conn)
        conn.execute(
            "INSERT INTO leaderboard_model_snapshots(created_at, updated_at, target_col, model_count, payload_json) VALUES (?, ?, ?, ?, ?)",
            ("2026-04-13T16:00:00Z", 123.0, "simulated_pyramid_win", 8, "{}"),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(api_module, "DB_PATH", str(db_path))

    import asyncio
    result = asyncio.run(api_module.api_model_leaderboard_history(limit=5))

    assert result["count"] == 1
    assert result["history"][0]["id"] == 1
    assert result["history"][0]["target_col"] == "simulated_pyramid_win"


def test_load_model_leaderboard_history_preserves_snapshot_ids(tmp_path):
    db_path = tmp_path / "lb_history_helper.db"
    conn = sqlite3.connect(db_path)
    try:
        api_module._ensure_model_leaderboard_tables(conn)
        conn.execute(
            "INSERT INTO leaderboard_model_snapshots(created_at, updated_at, target_col, model_count, payload_json) VALUES (?, ?, ?, ?, ?)",
            ("2026-04-18T14:12:52Z", 1776521572.2506027, "simulated_pyramid_win", 0, "{}"),
        )
        conn.execute(
            "INSERT INTO leaderboard_model_snapshots(created_at, updated_at, target_col, model_count, payload_json) VALUES (?, ?, ?, ?, ?)",
            ("2026-04-18T14:08:46Z", 1776521326.2036104, "simulated_pyramid_win", 0, "{}"),
        )
        conn.commit()
    finally:
        conn.close()

    history = api_module._load_model_leaderboard_history(db_path=str(db_path), limit=5)

    assert [row["id"] for row in history] == [2, 1]
    assert history[0]["created_at"] == "2026-04-18T14:08:46Z"
    assert history[1]["created_at"] == "2026-04-18T14:12:52Z"


def test_normalize_model_leaderboard_payload_backfills_snapshot_history_ids(tmp_path, monkeypatch):
    db_path = tmp_path / "lb_history_normalize.db"
    conn = sqlite3.connect(db_path)
    try:
        api_module._ensure_model_leaderboard_tables(conn)
        conn.execute(
            "INSERT INTO leaderboard_model_snapshots(created_at, updated_at, target_col, model_count, payload_json) VALUES (?, ?, ?, ?, ?)",
            ("2026-04-18T14:48:43.521912Z", 1776523723.5219226, "simulated_pyramid_win", 0, "{}"),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(api_module, "DB_PATH", str(db_path))

    normalized = api_module._normalize_model_leaderboard_payload(
        {
            "leaderboard": [],
            "placeholder_rows": [],
            "snapshot_history": [
                {
                    "created_at": "2026-04-18T14:48:43.521912Z",
                    "updated_at": 1776523723.5219226,
                    "target_col": "simulated_pyramid_win",
                    "model_count": 0,
                }
            ],
        }
    )

    assert normalized["snapshot_history"][0]["id"] == 1
