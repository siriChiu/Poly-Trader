from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from backtesting.model_leaderboard import ModelLeaderboard
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
