from datetime import datetime, timedelta

from database.models import FeaturesNormalized, RawMarketData, init_db
from feature_engine import preprocessor


def test_backfill_missing_feature_rows_only_inserts_missing_timestamps(monkeypatch, tmp_path):
    db_path = tmp_path / "missing_features.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        base = datetime(2026, 4, 1, 0, 0, 0)
        raw_rows = [
            RawMarketData(
                timestamp=base + timedelta(hours=i),
                symbol="BTCUSDT",
                close_price=100 + i,
                volume=1000 + i,
            )
            for i in range(12)
        ]
        session.add_all(raw_rows)
        session.add(FeaturesNormalized(timestamp=base + timedelta(hours=9), symbol="BTCUSDT", feat_eye=0.1))
        session.commit()

        def fake_compute(window):
            ts = window.iloc[-1]["timestamp"]
            return {
                "timestamp": ts,
                "symbol": "BTCUSDT",
                "feat_eye_dist": 0.11,
                "feat_ear_zscore": 0.22,
                "feat_nose_sigmoid": 0.33,
                "feat_tongue_pct": 0.44,
                "feat_body_roc": 0.55,
                "feat_pulse": 0.66,
                "feat_aura": 0.77,
                "feat_mind": 0.88,
            }

        monkeypatch.setattr(preprocessor, "compute_features_from_raw", fake_compute)

        inserted = preprocessor.backfill_missing_feature_rows(session, "BTCUSDT")

        feature_rows = (
            session.query(FeaturesNormalized)
            .filter(FeaturesNormalized.symbol == "BTCUSDT")
            .order_by(FeaturesNormalized.timestamp)
            .all()
        )
        timestamps = [row.timestamp for row in feature_rows]

        assert inserted == 2
        assert timestamps == [
            base + timedelta(hours=9),
            base + timedelta(hours=10),
            base + timedelta(hours=11),
        ]
    finally:
        session.close()



def test_repair_recent_feature_continuity_reports_and_repairs_missing_recent_rows(monkeypatch, tmp_path):
    db_path = tmp_path / "recent_feature_continuity.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        base = datetime.utcnow() - timedelta(hours=11)
        raw_rows = [
            RawMarketData(
                timestamp=base + timedelta(hours=i),
                symbol="BTCUSDT",
                close_price=200 + i,
                volume=500 + i,
            )
            for i in range(12)
        ]
        session.add_all(raw_rows)
        session.add(FeaturesNormalized(timestamp=base + timedelta(hours=9), symbol="BTCUSDT", feat_eye=0.1))
        session.commit()

        def fake_compute(window):
            ts = window.iloc[-1]["timestamp"]
            return {
                "timestamp": ts,
                "symbol": "BTCUSDT",
                "feat_eye_dist": 0.21,
                "feat_ear_zscore": 0.32,
                "feat_nose_sigmoid": 0.43,
                "feat_tongue_pct": 0.54,
                "feat_body_roc": 0.65,
                "feat_pulse": 0.76,
                "feat_aura": 0.87,
                "feat_mind": 0.98,
            }

        monkeypatch.setattr(preprocessor, "compute_features_from_raw", fake_compute)

        details = preprocessor.repair_recent_feature_continuity(
            session,
            "BTCUSDT",
            lookback_days=3,
            return_details=True,
        )

        assert details["missing_before"] == 2
        assert details["inserted_total"] == 2
        assert details["remaining_missing"] == 0
        assert details["gap_count_over_expected"] == 0
    finally:
        session.close()


def test_repair_recent_feature_continuity_can_defer_startup_backfill(monkeypatch, tmp_path):
    db_path = tmp_path / "recent_feature_continuity_deferred.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        base = datetime.utcnow() - timedelta(hours=11)
        raw_rows = [
            RawMarketData(
                timestamp=base + timedelta(hours=i),
                symbol="BTCUSDT",
                close_price=300 + i,
                volume=800 + i,
            )
            for i in range(12)
        ]
        session.add_all(raw_rows)
        session.add(FeaturesNormalized(timestamp=base + timedelta(hours=9), symbol="BTCUSDT", feat_eye=0.1))
        session.commit()

        def fail_if_called(window):
            raise AssertionError("startup continuity check must not compute heavy feature windows when deferred")

        monkeypatch.setattr(preprocessor, "compute_features_from_raw", fail_if_called)

        details = preprocessor.repair_recent_feature_continuity(
            session,
            "BTCUSDT",
            lookback_days=3,
            max_backfill_rows=0,
            return_details=True,
        )

        assert details["missing_before"] == 2
        assert details["inserted_total"] == 0
        assert details["remaining_missing"] == 2
        assert details["repair_deferred"] is True
        assert details["max_backfill_rows"] == 0
    finally:
        session.close()



def test_repair_recent_feature_continuity_treats_slash_and_compact_symbols_as_same_market(
    monkeypatch,
    tmp_path,
):
    db_path = tmp_path / "recent_feature_continuity_symbol_alias.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        base = datetime.utcnow() - timedelta(hours=11)
        raw_rows = [
            RawMarketData(
                timestamp=base + timedelta(hours=i),
                symbol="BTCUSDT",
                close_price=400 + i,
                volume=900 + i,
            )
            for i in range(12)
        ]
        feature_rows = [
            FeaturesNormalized(
                timestamp=base + timedelta(hours=i),
                symbol="BTC/USDT",
                feat_eye=0.1,
            )
            for i in range(9, 12)
        ]
        session.add_all(raw_rows + feature_rows)
        session.commit()

        def fail_if_called(window):
            raise AssertionError("symbol alias rows should satisfy feature continuity without recomputing")

        monkeypatch.setattr(preprocessor, "compute_features_from_raw", fail_if_called)

        details = preprocessor.repair_recent_feature_continuity(
            session,
            "BTCUSDT",
            lookback_days=3,
            max_backfill_rows=25,
            return_details=True,
        )

        assert details["missing_before"] == 0
        assert details["inserted_total"] == 0
        assert details["remaining_missing"] == 0
        assert details["repair_deferred"] is False
    finally:
        session.close()



def test_save_features_to_db_updates_existing_slash_symbol_row_instead_of_duplicating(tmp_path):
    db_path = tmp_path / "feature_symbol_alias_save.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        ts = datetime.utcnow().replace(microsecond=0)
        session.add(FeaturesNormalized(timestamp=ts, symbol="BTC/USDT", feat_eye=0.1))
        session.commit()

        saved = preprocessor.save_features_to_db(
            session,
            {
                "timestamp": ts,
                "symbol": "BTCUSDT",
                "feat_eye": 0.42,
                "feat_ear": 0.2,
                "feat_nose": 0.3,
                "feat_tongue": 0.4,
                "feat_body": 0.5,
                "feat_pulse": 0.6,
                "feat_aura": 0.7,
                "feat_mind": 0.8,
            },
        )

        rows = session.query(FeaturesNormalized).all()
        assert saved is not None
        assert len(rows) == 1
        assert rows[0].symbol == "BTCUSDT"
        assert rows[0].feat_eye == 0.42
    finally:
        session.close()
