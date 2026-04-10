from datetime import datetime

import pandas as pd

from data_ingestion.collector import repair_recent_raw_continuity
from database.models import RawMarketData, init_db


def _klines_df(*timestamps):
    return pd.DataFrame(
        [
            {
                "timestamp": ts,
                "close": 100000.0 + i,
                "volume": 1000.0 + i,
            }
            for i, ts in enumerate(timestamps)
        ]
    )


def test_repair_recent_raw_continuity_inserts_missing_4h_rows(tmp_path):
    db_path = tmp_path / "continuity.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        session.add_all(
            [
                RawMarketData(timestamp=datetime(2026, 4, 9, 0, 0, 0), symbol="BTCUSDT", close_price=100.0),
                RawMarketData(timestamp=datetime(2026, 4, 10, 0, 0, 0), symbol="BTCUSDT", close_price=110.0),
            ]
        )
        session.commit()

        inserted = repair_recent_raw_continuity(
            session,
            "BTCUSDT",
            lookback_days=3650,
            klines_df=_klines_df(
                datetime(2026, 4, 9, 0, 0, 0),
                datetime(2026, 4, 9, 4, 0, 0),
                datetime(2026, 4, 9, 8, 0, 0),
                datetime(2026, 4, 9, 12, 0, 0),
                datetime(2026, 4, 9, 16, 0, 0),
                datetime(2026, 4, 9, 20, 0, 0),
                datetime(2026, 4, 10, 0, 0, 0),
            ),
            fine_grain_klines_df=pd.DataFrame(),
        )
        session.commit()

        rows = (
            session.query(RawMarketData)
            .filter(RawMarketData.symbol == "BTCUSDT")
            .order_by(RawMarketData.timestamp)
            .all()
        )
        timestamps = [row.timestamp for row in rows]

        assert inserted == 5
        assert timestamps == [
            datetime(2026, 4, 9, 0, 0, 0),
            datetime(2026, 4, 9, 4, 0, 0),
            datetime(2026, 4, 9, 8, 0, 0),
            datetime(2026, 4, 9, 12, 0, 0),
            datetime(2026, 4, 9, 16, 0, 0),
            datetime(2026, 4, 9, 20, 0, 0),
            datetime(2026, 4, 10, 0, 0, 0),
        ]
    finally:
        session.close()


def test_repair_recent_raw_continuity_respects_alignment_tolerance(tmp_path):
    db_path = tmp_path / "continuity_tolerance.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        session.add(
            RawMarketData(
                timestamp=datetime(2026, 4, 9, 4, 20, 0),
                symbol="BTCUSDT",
                close_price=100.0,
            )
        )
        session.commit()

        inserted = repair_recent_raw_continuity(
            session,
            "BTCUSDT",
            lookback_days=3650,
            alignment_tolerance_minutes=30,
            klines_df=_klines_df(datetime(2026, 4, 9, 4, 0, 0)),
            fine_grain_klines_df=pd.DataFrame(),
        )
        session.commit()

        rows = session.query(RawMarketData).filter(RawMarketData.symbol == "BTCUSDT").all()
        assert inserted == 0
        assert len(rows) == 1
    finally:
        session.close()


def test_repair_recent_raw_continuity_uses_fine_grain_klines_to_close_240m_gap(tmp_path):
    db_path = tmp_path / "continuity_fine_grain.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        session.add_all(
            [
                RawMarketData(timestamp=datetime(2026, 4, 9, 20, 0, 0), symbol="BTCUSDT", close_price=100.0),
                RawMarketData(timestamp=datetime(2026, 4, 10, 2, 25, 0), symbol="BTCUSDT", close_price=110.0),
            ]
        )
        session.commit()

        inserted = repair_recent_raw_continuity(
            session,
            "BTCUSDT",
            lookback_days=3650,
            klines_df=pd.DataFrame(),
            fine_grain_days=3650,
            fine_grain_klines_df=_klines_df(
                datetime(2026, 4, 9, 21, 0, 0),
                datetime(2026, 4, 9, 22, 0, 0),
                datetime(2026, 4, 9, 23, 0, 0),
                datetime(2026, 4, 10, 0, 0, 0),
                datetime(2026, 4, 10, 1, 0, 0),
                datetime(2026, 4, 10, 2, 0, 0),
            ),
        )
        session.commit()

        rows = (
            session.query(RawMarketData)
            .filter(RawMarketData.symbol == "BTCUSDT")
            .order_by(RawMarketData.timestamp)
            .all()
        )
        timestamps = [row.timestamp for row in rows]

        assert inserted == 5
        assert timestamps == [
            datetime(2026, 4, 9, 20, 0, 0),
            datetime(2026, 4, 9, 21, 0, 0),
            datetime(2026, 4, 9, 22, 0, 0),
            datetime(2026, 4, 9, 23, 0, 0),
            datetime(2026, 4, 10, 0, 0, 0),
            datetime(2026, 4, 10, 1, 0, 0),
            datetime(2026, 4, 10, 2, 25, 0),
        ]
    finally:
        session.close()


def test_repair_recent_raw_continuity_falls_back_to_interpolated_hourly_bridges(tmp_path):
    db_path = tmp_path / "continuity_interpolated.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        session.add_all(
            [
                RawMarketData(timestamp=datetime(2026, 4, 9, 20, 0, 0), symbol="BTCUSDT", close_price=100.0),
                RawMarketData(timestamp=datetime(2026, 4, 10, 2, 25, 0), symbol="BTCUSDT", close_price=112.5),
            ]
        )
        session.commit()

        inserted = repair_recent_raw_continuity(
            session,
            "BTCUSDT",
            lookback_days=3650,
            klines_df=pd.DataFrame(),
            fine_grain_days=3650,
            fine_grain_klines_df=pd.DataFrame(),
        )
        session.commit()

        rows = (
            session.query(RawMarketData)
            .filter(RawMarketData.symbol == "BTCUSDT")
            .order_by(RawMarketData.timestamp)
            .all()
        )
        timestamps = [row.timestamp for row in rows]

        assert inserted == 5
        assert timestamps == [
            datetime(2026, 4, 9, 20, 0, 0),
            datetime(2026, 4, 9, 21, 0, 0),
            datetime(2026, 4, 9, 22, 0, 0),
            datetime(2026, 4, 9, 23, 0, 0),
            datetime(2026, 4, 10, 0, 0, 0),
            datetime(2026, 4, 10, 1, 0, 0),
            datetime(2026, 4, 10, 2, 25, 0),
        ]
        bridge_prices = [round(row.close_price, 4) for row in rows[1:-1]]
        assert bridge_prices[0] > 100.0
        assert bridge_prices[-1] < 112.5
    finally:
        session.close()


def test_repair_recent_raw_continuity_return_details_surfaces_bridge_usage(tmp_path):
    db_path = tmp_path / "continuity_details.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        session.add_all(
            [
                RawMarketData(timestamp=datetime(2026, 4, 9, 20, 0, 0), symbol="BTCUSDT", close_price=100.0),
                RawMarketData(timestamp=datetime(2026, 4, 10, 2, 25, 0), symbol="BTCUSDT", close_price=112.5),
            ]
        )
        session.commit()

        details = repair_recent_raw_continuity(
            session,
            "BTCUSDT",
            lookback_days=3650,
            klines_df=pd.DataFrame(),
            fine_grain_days=3650,
            fine_grain_klines_df=pd.DataFrame(),
            return_details=True,
        )

        assert details["inserted_total"] == 5
        assert details["coarse_inserted"] == 0
        assert details["fine_inserted"] == 0
        assert details["bridge_inserted"] == 5
        assert details["used_bridge"] is True
        assert details["skipped_no_klines"] is True
    finally:
        session.close()
