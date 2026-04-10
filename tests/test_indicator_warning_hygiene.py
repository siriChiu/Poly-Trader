import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from feature_engine.ohlcv_4h import compute_4h_indicators
from feature_engine.technical_indicators import bollinger_bands, rsi, vwap


def _runtime_warnings(records):
    return [r for r in records if issubclass(r.category, RuntimeWarning)]


def test_technical_indicators_avoid_runtime_warnings_on_zero_denominators():
    prices = np.zeros(32, dtype=float)
    highs = np.zeros(32, dtype=float)
    lows = np.zeros(32, dtype=float)
    volumes = np.zeros(32, dtype=float)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _, _, _, percent_b = bollinger_bands(prices, period=20)
        rsi_vals = rsi(prices, period=14)
        vwap_vals = vwap(highs, lows, prices, volumes)

    assert _runtime_warnings(caught) == []
    assert percent_b[-1] == 0.5
    assert np.all(np.isfinite(rsi_vals))
    assert np.all(np.isfinite(vwap_vals))
    assert np.allclose(vwap_vals, 0.0)


def test_4h_indicator_pipeline_avoids_runtime_warnings_on_flat_series():
    candles = {
        "closes": np.zeros(240, dtype=float),
        "highs": np.zeros(240, dtype=float),
        "lows": np.zeros(240, dtype=float),
        "volumes": np.zeros(240, dtype=float),
    }

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = compute_4h_indicators(candles)

    assert _runtime_warnings(caught) == []
    assert result["4h_bb_pct_b"][-1] == 0.5
    assert result["4h_vol_ratio"][-1] == 1.0
    assert result["4h_rsi14"][-1] == 99.00990099009901
    assert np.all(np.isfinite(result["4h_dist_bb_lower"]))
    assert np.all(np.isfinite(result["4h_bias20"]))
