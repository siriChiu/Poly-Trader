import pandas as pd

from model.train import _align_sparse_4h_features


def test_align_sparse_4h_features_uses_timestamp_snapshot_without_ffill_logic():
    feat_df = pd.DataFrame(
        [
            {"timestamp": "2026-01-01 00:00:00", "symbol": "BTCUSDT", "feat_eye": 0.1, "feat_4h_bias50": -2.0, "feat_4h_rsi14": 40.0, "regime_label": "bear"},
            {"timestamp": "2026-01-01 00:01:00", "symbol": "BTCUSDT", "feat_eye": 0.2, "feat_4h_bias50": None, "feat_4h_rsi14": None, "regime_label": None},
            {"timestamp": "2026-01-01 03:59:00", "symbol": "BTCUSDT", "feat_eye": 0.3, "feat_4h_bias50": None, "feat_4h_rsi14": None, "regime_label": None},
            {"timestamp": "2026-01-01 04:00:00", "symbol": "BTCUSDT", "feat_eye": 0.4, "feat_4h_bias50": 1.5, "feat_4h_rsi14": 65.0, "regime_label": "bull"},
            {"timestamp": "2026-01-01 04:01:00", "symbol": "BTCUSDT", "feat_eye": 0.5, "feat_4h_bias50": None, "feat_4h_rsi14": None, "regime_label": None},
        ]
    )

    aligned = _align_sparse_4h_features(feat_df, tolerance="6h")

    row_0001 = aligned.loc[aligned["timestamp"] == pd.Timestamp("2026-01-01 00:01:00")].iloc[0]
    row_0359 = aligned.loc[aligned["timestamp"] == pd.Timestamp("2026-01-01 03:59:00")].iloc[0]
    row_0401 = aligned.loc[aligned["timestamp"] == pd.Timestamp("2026-01-01 04:01:00")].iloc[0]

    assert row_0001["feat_4h_bias50"] == -2.0
    assert row_0359["feat_4h_bias50"] == -2.0
    assert row_0401["feat_4h_bias50"] == 1.5
    assert row_0001["regime_label"] == "bear"
    assert row_0401["regime_label"] == "bull"


def test_align_sparse_4h_features_respects_tolerance_window():
    feat_df = pd.DataFrame(
        [
            {"timestamp": "2026-01-01 00:00:00", "symbol": "BTCUSDT", "feat_eye": 0.1, "feat_4h_bias50": -2.0, "feat_4h_rsi14": 40.0, "regime_label": "bear"},
            {"timestamp": "2026-01-01 10:30:00", "symbol": "BTCUSDT", "feat_eye": 0.2, "feat_4h_bias50": None, "feat_4h_rsi14": None, "regime_label": None},
        ]
    )

    aligned = _align_sparse_4h_features(feat_df, tolerance="6h")
    late_row = aligned.loc[aligned["timestamp"] == pd.Timestamp("2026-01-01 10:30:00")].iloc[0]

    assert pd.isna(late_row["feat_4h_bias50"])
    assert pd.isna(late_row["regime_label"])
