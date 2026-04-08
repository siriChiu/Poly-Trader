from pathlib import Path
import sqlite3

import pandas as pd
import pytest

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
            feat_4h_rsi14 REAL,
            feat_4h_macd_hist REAL,
            feat_4h_bb_pct_b REAL,
            feat_4h_ma_order REAL,
            feat_4h_dist_swing_low REAL
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
        "INSERT INTO features_normalized VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (ts, "BTCUSDT", 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 11.0, 101.0, 0.55, 0.01, 0.02, 0.03, 0.8, -2.0, -1.0, 45.0, 100.0, 0.4, 1.0, 3.0),
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


def test_load_model_leaderboard_frame_falls_back_to_timestamp_join(leaderboard_db: Path):
    df = load_model_leaderboard_frame(str(leaderboard_db))

    assert not df.empty
    assert df.loc[0, "label_spot_long_win"] == 1
    assert df.loc[0, "close_price"] == 50000.0


def test_supported_models_includes_catboost():
    assert "catboost" in ModelLeaderboard.SUPPORTED_MODELS


def test_model_leaderboard_defaults_to_simulated_target():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=2, freq="D"),
            "close_price": [50000, 50010],
            "label_spot_long_win": [0, 1],
            "simulated_pyramid_win": [1, 1],
            "feat_4h_bias50": [0.0, 0.0],
            "feat_nose": [0.4, 0.5],
            "feat_pulse": [0.6, 0.6],
            "feat_ear": [0.1, 0.1],
        }
    )

    leaderboard = ModelLeaderboard(df)

    assert leaderboard.target_col == "simulated_pyramid_win"


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
        })()
        return fold, None, DummyResult(), 0.72, 0.64

    monkeypatch.setattr(leaderboard, "_run_single_fold", fake_run_single_fold)

    score = leaderboard.evaluate_model("rule_baseline")

    assert score is not None
    assert score.avg_profit_factor == pytest.approx(1.42)


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
