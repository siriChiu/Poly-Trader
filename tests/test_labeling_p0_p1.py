from datetime import datetime
from pathlib import Path

from database.models import FeaturesNormalized, RawMarketData, init_db
from data_ingestion.labeling import generate_future_return_labels
from feature_engine.preprocessor import save_features_to_db


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def test_save_features_to_db_persists_symbol_and_upgrades_legacy_null_symbol(tmp_path: Path):
    session = init_db(_sqlite_url(tmp_path / "p0_features.db"))
    try:
        legacy = FeaturesNormalized(timestamp=datetime(2026, 1, 1, 0, 0, 0), symbol=None)
        session.add(legacy)
        session.commit()

        save_features_to_db(
            session,
            {
                "timestamp": legacy.timestamp,
                "symbol": "BTCUSDT",
                "feat_eye": 0.1,
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
        assert len(rows) == 1
        assert rows[0].symbol == "BTCUSDT"
    finally:
        session.close()


def test_save_features_to_db_derives_regime_label_for_new_rows(tmp_path: Path):
    session = init_db(_sqlite_url(tmp_path / "p0_regime.db"))
    try:
        ts = datetime(2026, 1, 2, 0, 0, 0)
        save_features_to_db(
            session,
            {
                "timestamp": ts,
                "symbol": "BTCUSDT",
                "feat_eye": 0.1,
                "feat_ear": 0.2,
                "feat_nose": 0.3,
                "feat_tongue": 0.4,
                "feat_body": 0.5,
                "feat_pulse": 0.6,
                "feat_aura": 0.7,
                "feat_mind": 0.8,
                "feat_4h_bias50": 3.0,
            },
        )

        row = session.query(FeaturesNormalized).filter_by(timestamp=ts, symbol="BTCUSDT").one()
        assert row.regime_label == "bull"
    finally:
        session.close()


def test_generate_future_return_labels_uses_path_aware_long_win(tmp_path: Path):
    session = init_db(_sqlite_url(tmp_path / "p1_labels.db"))
    try:
        ts0 = datetime(2026, 1, 1, 0, 0, 0)
        session.add(FeaturesNormalized(timestamp=ts0, symbol="BTCUSDT"))
        session.add_all(
            [
                RawMarketData(timestamp=ts0, symbol="BTCUSDT", close_price=100.0),
                RawMarketData(timestamp=ts0.replace(hour=12), symbol="BTCUSDT", close_price=103.0),
                RawMarketData(timestamp=ts0.replace(hour=23, minute=55), symbol="BTCUSDT", close_price=101.0),
                RawMarketData(timestamp=ts0.replace(day=2), symbol="BTCUSDT", close_price=101.0),
            ]
        )
        session.commit()

        labels_df = generate_future_return_labels(
            session,
            symbol="BTCUSDT",
            horizon_hours=24,
            threshold_pct=0.02,
            neutral_band=0.05,
        )

        assert not labels_df.empty
        row = labels_df.iloc[0]
        assert row["future_return_pct"] == 0.01
        assert row["future_max_runup"] >= 0.03
        assert row["label_spot_long_tp_hit"] == 1
        assert row["label_spot_long_quality"] > 0
        assert row["simulated_pyramid_win"] == 1
        assert row["simulated_pyramid_pnl"] > 0
        assert row["simulated_pyramid_quality"] > 0
        assert row["label_spot_long_win"] == 1
    finally:
        session.close()
