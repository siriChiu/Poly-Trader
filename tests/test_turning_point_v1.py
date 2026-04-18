from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from data_ingestion.labeling import generate_future_return_labels
from database.models import FeaturesNormalized, RawMarketData, init_db
from feature_engine import preprocessor


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def test_generate_future_return_labels_emits_local_bottom_and_top_signals(tmp_path: Path):
    session = init_db(_sqlite_url(tmp_path / "turning_point_labels.sqlite"))
    try:
        base = datetime(2026, 4, 1, 0, 0, 0)
        feature_times = [base + timedelta(hours=i) for i in range(2)]
        session.add_all(
            [
                FeaturesNormalized(timestamp=feature_times[0], symbol="BTCUSDT", feat_eye=0.1),
                FeaturesNormalized(timestamp=feature_times[1], symbol="BTCUSDT", feat_eye=0.2),
            ]
        )

        raw_rows = []
        closes = {
            feature_times[0]: 100.0,
            feature_times[0] + timedelta(hours=1): 98.0,
            feature_times[0] + timedelta(hours=2): 97.0,
            feature_times[0] + timedelta(hours=3): 99.0,
            feature_times[0] + timedelta(hours=4): 104.0,
            feature_times[1]: 104.0,
            feature_times[1] + timedelta(hours=1): 105.0,
            feature_times[1] + timedelta(hours=2): 103.0,
            feature_times[1] + timedelta(hours=3): 100.0,
            feature_times[1] + timedelta(hours=4): 98.0,
        }
        for ts, price in sorted(closes.items()):
            raw_rows.append(RawMarketData(timestamp=ts, symbol="BTCUSDT", close_price=price, volume=1000.0))
        session.add_all(raw_rows)
        session.commit()

        labels_df = generate_future_return_labels(
            session,
            symbol="BTCUSDT",
            horizon_hours=4,
            threshold_pct=0.02,
            neutral_band=0.05,
        ).sort_values("timestamp").reset_index(drop=True)

        assert "label_local_bottom" in labels_df.columns
        assert "label_local_top" in labels_df.columns
        assert "turning_point_score" in labels_df.columns
        assert int(labels_df.loc[0, "label_local_bottom"]) == 1
        assert int(labels_df.loc[0, "label_local_top"]) == 0
        assert int(labels_df.loc[1, "label_local_bottom"]) == 0
        assert int(labels_df.loc[1, "label_local_top"]) == 1
        assert float(labels_df.loc[0, "turning_point_score"]) > 0.5
        assert float(labels_df.loc[1, "turning_point_score"]) > 0.5
    finally:
        session.close()


def test_compute_features_from_raw_projects_turning_point_family(monkeypatch):
    rows = 180
    base = datetime(2026, 4, 1, 0, 0, 0)
    timestamps = [base + timedelta(minutes=i) for i in range(rows)]
    close = [100 + i * 0.05 for i in range(rows - 6)] + [104.0, 102.0, 99.0, 97.0, 98.5, 101.0]
    volume = [1000.0] * (rows - 3) + [1100.0, 1800.0, 2400.0]
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close_price": close,
            "volume": volume,
            "symbol": ["BTCUSDT"] * rows,
        }
    )

    monkeypatch.setattr(preprocessor, "_compute_technical_indicators_from_df", lambda _df: {})

    features = preprocessor.compute_features_from_raw(df)

    assert "feat_local_bottom_score" in features
    assert "feat_local_top_score" in features
    assert "feat_turning_point_score" in features
    assert "feat_wick_rejection" in features
    assert "feat_volume_exhaustion" in features
    assert "feat_tunnel_distance" in features
    assert 0.0 <= float(features["feat_local_bottom_score"]) <= 1.0
    assert 0.0 <= float(features["feat_turning_point_score"]) <= 1.0
    assert float(features["feat_local_bottom_score"]) > float(features["feat_local_top_score"])
    assert float(features["feat_turning_point_score"]) == max(
        float(features["feat_local_bottom_score"]),
        float(features["feat_local_top_score"]),
    )
