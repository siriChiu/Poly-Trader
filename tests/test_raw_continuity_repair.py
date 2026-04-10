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
        )
        session.commit()

        rows = session.query(RawMarketData).filter(RawMarketData.symbol == "BTCUSDT").all()
        assert inserted == 0
        assert len(rows) == 1
    finally:
        session.close()
