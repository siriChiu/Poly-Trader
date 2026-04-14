import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pandas as pd
from sqlalchemy import text

from data_ingestion.labeling import save_labels_to_db
from database.models import FeaturesNormalized, Labels, RawMarketData, init_db
from scripts.hb_collect import summarize_label_horizons


def test_summarize_label_horizons_marks_expected_vs_stale(tmp_path):
    db_path = tmp_path / "hb_collect.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        latest_raw = datetime(2026, 4, 10, 12, 0, 0)
        session.add(RawMarketData(timestamp=latest_raw, symbol="BTCUSDT", close_price=1.0))
        session.add_all(
            [
                Labels(
                    timestamp=latest_raw - timedelta(hours=4),
                    symbol="BTCUSDT",
                    horizon_minutes=240,
                    simulated_pyramid_win=1,
                ),
                Labels(
                    timestamp=latest_raw - timedelta(hours=24),
                    symbol="BTCUSDT",
                    horizon_minutes=1440,
                    simulated_pyramid_win=0,
                ),
                Labels(
                    timestamp=latest_raw - timedelta(hours=50),
                    symbol="BTCUSDT",
                    horizon_minutes=720,
                    simulated_pyramid_win=1,
                ),
            ]
        )
        session.commit()

        summary = summarize_label_horizons(session, "BTCUSDT")
        by_horizon = {row["horizon_minutes"]: row for row in summary}

        assert by_horizon[240]["freshness"] == "expected_horizon_lag"
        assert by_horizon[1440]["freshness"] == "expected_horizon_lag"
        assert by_horizon[720]["freshness"] == "inactive_horizon"
        assert by_horizon[720]["is_active"] is False
        assert by_horizon[1440]["lag_hours_vs_raw"] == 24.0
    finally:
        session.close()


def test_summarize_label_horizons_marks_active_horizon_blocked_by_raw_gap(tmp_path):
    db_path = tmp_path / "hb_collect_gap.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        session.add_all(
            [
                RawMarketData(timestamp=datetime(2026, 4, 9, 0, 0, 0), symbol="BTCUSDT", close_price=1.0),
                RawMarketData(timestamp=datetime(2026, 4, 10, 0, 0, 0), symbol="BTCUSDT", close_price=1.1),
                Labels(
                    timestamp=datetime(2026, 4, 9, 10, 0, 0),
                    symbol="BTCUSDT",
                    horizon_minutes=240,
                    simulated_pyramid_win=1,
                ),
            ]
        )
        session.commit()

        summary = summarize_label_horizons(session, "BTCUSDT")
        by_horizon = {row["horizon_minutes"]: row for row in summary}
        assert by_horizon[240]["freshness"] == "raw_gap_blocked"
        assert by_horizon[240]["latest_raw_gap_hours"] == 14.0
    finally:
        session.close()


def test_save_labels_to_db_backfills_canonical_columns_for_existing_rows(tmp_path):
    db_path = tmp_path / "hb_collect_backfill.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        ts = datetime(2026, 4, 9, 0, 0, 0)
        session.add_all(
            [
                RawMarketData(timestamp=ts, symbol="BTCUSDT", close_price=100.0),
                FeaturesNormalized(timestamp=ts, symbol="BTCUSDT", regime_label="bull"),
                Labels(
                    timestamp=ts,
                    symbol="BTCUSDT",
                    horizon_minutes=240,
                    future_return_pct=0.03,
                    label_sell_win=0,
                    simulated_pyramid_win=None,
                    label_spot_long_win=None,
                    label_up=None,
                ),
            ]
        )
        session.commit()

        labels_df = pd.DataFrame(
            [
                {
                    "timestamp": ts,
                    "future_return_pct": 0.03,
                    "future_max_drawdown": -0.01,
                    "future_max_runup": 0.05,
                    "label_spot_long_win": 1,
                    "label_spot_long_tp_hit": 1,
                    "label_spot_long_quality": 1.2,
                    "simulated_pyramid_win": 1,
                    "simulated_pyramid_pnl": 0.021,
                    "simulated_pyramid_quality": 0.42,
                    "simulated_pyramid_drawdown_penalty": 0.18,
                    "simulated_pyramid_time_underwater": 0.25,
                    "label_sell_win": 0,
                    "label_up": 1,
                }
            ]
        )

        save_labels_to_db(session, labels_df, symbol="BTCUSDT", horizon_hours=4)

        row = session.query(Labels).filter_by(symbol="BTCUSDT", horizon_minutes=240).one()
        assert row.simulated_pyramid_win == 1
        assert row.simulated_pyramid_pnl == 0.021
        assert row.simulated_pyramid_drawdown_penalty == 0.18
        assert row.simulated_pyramid_time_underwater == 0.25
        assert row.label_spot_long_win == 1
        assert row.label_up == 1
        assert row.regime_label == "bull"
    finally:
        session.close()


def test_init_db_sets_sqlite_busy_timeout_and_wal(tmp_path):
    db_path = tmp_path / "hb_collect_pragmas.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        journal_mode = session.execute(text("PRAGMA journal_mode")).scalar()
        busy_timeout = session.execute(text("PRAGMA busy_timeout")).scalar()
        assert str(journal_mode).lower() == "wal"
        assert int(busy_timeout) >= 30000
    finally:
        session.close()
