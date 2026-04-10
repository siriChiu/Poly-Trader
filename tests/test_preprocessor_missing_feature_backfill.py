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
