from __future__ import annotations

from datetime import datetime, timezone

from database.models import RawMarketData, init_db


def test_raw_market_debug_fields_round_trip_in_isolated_database(tmp_path) -> None:
    session = init_db(f"sqlite:///{tmp_path / 'raw_market_debug.db'}")
    try:
        row = RawMarketData(
            timestamp=datetime(2026, 7, 16, tzinfo=timezone.utc),
            symbol="BTC-USDT-SWAP",
            eye_dist=0.25,
            ear_prob=0.75,
            stablecoin_mcap=123_456.0,
        )
        session.add(row)
        session.commit()
        session.expire_all()

        stored = session.query(RawMarketData).one()
        assert getattr(stored, "eye_dist") == 0.25
        assert getattr(stored, "ear_prob") == 0.75
        assert getattr(stored, "stablecoin_mcap") == 123_456.0
    finally:
        session.close()
