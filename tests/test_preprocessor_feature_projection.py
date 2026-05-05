from datetime import datetime, timedelta

import pandas as pd

from database.models import FeaturesNormalized, RawMarketData, init_db
from feature_engine import preprocessor


def _build_df(rows=80):
    timestamps = pd.date_range("2026-04-10", periods=rows, freq="h")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": ["BTCUSDT"] * rows,
            "close_price": [50000 + i * 10 for i in range(rows)],
            "volume": [1000 + i for i in range(rows)],
            "funding_rate": [0.0001] * rows,
            "fear_greed_index": [50] * rows,
            "stablecoin_mcap": [1_000_000] * rows,
            "polymarket_prob": [0.5] * rows,
            "eye_dist": [0.1] * rows,
            "ear_prob": [0.2] * rows,
            "tongue_sentiment": [0.0] * rows,
            "volatility": [0.01] * rows,
            "oi_roc": [0.02] * rows,
            "vix_value": [20.0] * rows,
            "dxy_value": [103.0] * rows,
            "nq_value": [18000.0 + i for i in range(rows)],
        }
    )


def test_compute_features_from_raw_projects_4h_outputs(monkeypatch):
    df = _build_df()

    def fake_ti(_df):
        return {
            "feat_rsi14": 0.61,
            "feat_macd_hist": 0.02,
            "feat_atr_pct": 0.03,
            "feat_vwap_dev": 0.04,
            "feat_bb_pct_b": 0.55,
            "feat_nw_width": 0.12,
            "feat_nw_slope": 0.07,
            "feat_adx": 0.31,
            "feat_choppiness": 0.42,
            "feat_donchian_pos": 0.63,
            "feat_4h_bias50": -2.5,
            "feat_4h_bias20": -1.2,
            "feat_4h_bias200": 3.1,
            "feat_4h_rsi14": 44.0,
            "feat_4h_macd_hist": -0.15,
            "feat_4h_bb_pct_b": 0.21,
            "feat_4h_dist_bb_lower": 1.8,
            "feat_4h_ma_order": -1.0,
            "feat_4h_dist_swing_low": 0.9,
            "feat_4h_vol_ratio": 1.4,
        }

    monkeypatch.setattr(preprocessor, "_compute_technical_indicators_from_df", fake_ti)

    features = preprocessor.compute_features_from_raw(df)

    assert features["feat_4h_bias50"] == -2.5
    assert features["feat_4h_rsi14"] == 44.0
    assert features["feat_4h_vol_ratio"] == 1.4
    assert features["feat_nw_width"] == 0.12
    assert features["feat_adx"] == 0.31


class _FakeExchange:
    def __init__(self, *args, **kwargs):
        pass

    def fetch_ohlcv(self, symbol, timeframe, limit=300):
        assert symbol == "BTC/USDT"
        assert timeframe == "4h"
        return [
            [i * 14_400_000, 100 + i, 101 + i, 99 + i, 100 + i, 1000 + i]
            for i in range(limit)
        ]


def test_compute_technical_indicators_from_df_includes_extended_technical_and_4h(monkeypatch):
    df = _build_df()

    monkeypatch.setattr("ccxt.okx", lambda *args, **kwargs: _FakeExchange())
    monkeypatch.setattr(
        "feature_engine.ohlcv_4h.compute_4h_indicators",
        lambda candles_4h: {
            "4h_bias50": [1.25] * len(candles_4h["closes"]),
            "4h_bias20": [0.75] * len(candles_4h["closes"]),
            "4h_bias200": [2.5] * len(candles_4h["closes"]),
            "4h_rsi14": [48.0] * len(candles_4h["closes"]),
            "4h_macd_hist": [-0.12] * len(candles_4h["closes"]),
            "4h_bb_pct_b": [0.33] * len(candles_4h["closes"]),
            "4h_dist_bb_lower": [1.1] * len(candles_4h["closes"]),
            "4h_ma_order": [1.0] * len(candles_4h["closes"]),
            "4h_dist_swing_low": [0.8] * len(candles_4h["closes"]),
            "4h_vol_ratio": [1.7] * len(candles_4h["closes"]),
        },
    )
    monkeypatch.setattr(
        "feature_engine.technical_indicators.compute_technical_features",
        lambda closes, highs, lows, volumes: {
            "feat_rsi14": 0.57,
            "feat_macd_hist": 0.011,
            "feat_bb_pct_b": 0.49,
            "feat_atr_pct": 0.022,
            "feat_vwap_dev": -0.015,
            "feat_nw_width": 0.18,
            "feat_nw_slope": 0.09,
            "feat_adx": 0.44,
            "feat_choppiness": 0.36,
            "feat_donchian_pos": 0.62,
        },
    )

    result = preprocessor._compute_technical_indicators_from_df(df)

    assert result["feat_nw_width"] == 0.18
    assert result["feat_nw_slope"] == 0.09
    assert result["feat_adx"] == 0.44
    assert result["feat_choppiness"] == 0.36
    assert result["feat_donchian_pos"] == 0.62
    assert result["feat_4h_bias50"] == 1.25
    assert result["feat_4h_vol_ratio"] == 1.7


def test_compute_features_from_raw_leaves_nq_returns_null_without_history(monkeypatch):
    df = _build_df(rows=80)
    df["nq_value"] = [18000.0] + [None] * 79

    monkeypatch.setattr(preprocessor, "_compute_technical_indicators_from_df", lambda _df: {})

    features = preprocessor.compute_features_from_raw(df)

    assert features["feat_nq_return_1h"] is None
    assert features["feat_nq_return_24h"] is None


def test_recompute_all_features_projects_4h_fields_for_existing_and_new_rows(monkeypatch, tmp_path):
    db_path = tmp_path / "recompute_feature_projection.sqlite"
    session = init_db(f"sqlite:///{db_path}")
    try:
        base = datetime(2026, 4, 10, 0, 0, 0)
        raw_rows = [
            RawMarketData(
                timestamp=base + timedelta(hours=i),
                symbol="BTCUSDT",
                close_price=50000 + i,
                volume=1000 + i,
            )
            for i in range(80)
        ]
        session.add_all(raw_rows)
        session.add(
            FeaturesNormalized(
                timestamp=base + timedelta(hours=63),
                symbol="BTCUSDT",
                feat_eye=0.1,
                regime_label=None,
                feat_4h_bias50=None,
            )
        )
        session.commit()

        def fake_compute(window):
            ts = window.iloc[-1]["timestamp"]
            hour_offset = int((ts - base).total_seconds() // 3600)
            return {
                "feat_eye": 0.1 + hour_offset,
                "feat_ear": 0.2,
                "feat_nose": 0.3,
                "feat_tongue": 0.4,
                "feat_body": 0.5,
                "feat_pulse": 0.6,
                "feat_aura": 0.7,
                "feat_mind": 0.8,
                "feat_4h_bias50": 1.5 + hour_offset,
                "feat_4h_bias20": 2.5,
                "feat_4h_bias200": 3.5,
                "feat_4h_rsi14": 44.0,
                "feat_4h_macd_hist": -0.2,
                "feat_4h_bb_pct_b": 0.22,
                "feat_4h_dist_bb_lower": 1.1,
                "feat_4h_ma_order": 1.0,
                "feat_4h_dist_swing_low": 0.9,
                "feat_4h_vol_ratio": 1.7,
                "regime_label": "bull",
            }

        monkeypatch.setattr(preprocessor, "compute_features_from_raw", fake_compute)

        updated = preprocessor.recompute_all_features(session, "BTCUSDT")

        assert updated >= 17

        existing = session.query(FeaturesNormalized).filter_by(timestamp=base + timedelta(hours=63), symbol="BTCUSDT").one()
        inserted = session.query(FeaturesNormalized).filter_by(timestamp=base + timedelta(hours=79), symbol="BTCUSDT").one()

        assert existing.feat_4h_bias50 == 64.5
        assert existing.feat_4h_dist_bb_lower == 1.1
        assert existing.feat_4h_vol_ratio == 1.7
        assert existing.regime_label == "bull"
        assert existing.feature_version == "v4_4h_integration"

        assert inserted.feat_4h_bias50 == 80.5
        assert inserted.feat_4h_dist_swing_low == 0.9
        assert inserted.regime_label == "bull"
        assert inserted.feature_version == "v4_4h_integration"
    finally:
        session.close()
