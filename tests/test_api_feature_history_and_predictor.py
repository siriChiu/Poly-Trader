import asyncio
from types import SimpleNamespace

from server.routes import api as api_module
from model import predictor as predictor_module


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def query(self, *args, **kwargs):
        return _FakeQuery(self._rows)


def test_api_features_exposes_extended_feature_history_keys(monkeypatch):
    row = SimpleNamespace(
        timestamp=SimpleNamespace(isoformat=lambda: "2026-04-08T12:00:00"),
        feat_eye=0.1,
        feat_ear=0.2,
        feat_nose=0.3,
        feat_tongue=0.4,
        feat_body=0.5,
        feat_pulse=0.6,
        feat_aura=0.7,
        feat_mind=0.8,
        feat_vix=20.0,
        feat_dxy=101.0,
        feat_rsi14=0.55,
        feat_macd_hist=0.01,
        feat_atr_pct=0.02,
        feat_vwap_dev=0.03,
        feat_bb_pct_b=0.7,
        feat_nq_return_1h=0.01,
        feat_nq_return_24h=0.02,
        feat_claw=0.3,
        feat_claw_intensity=0.4,
        feat_fang_pcr=0.5,
        feat_fang_skew=0.6,
        feat_fin_netflow=0.7,
        feat_web_whale=0.8,
        feat_scales_ssr=0.9,
        feat_nest_pred=1.0,
        feat_4h_bias50=-2.0,
        feat_4h_bias20=-1.0,
        feat_4h_bias200=4.0,
        feat_4h_rsi14=45.0,
        feat_4h_macd_hist=100.0,
        feat_4h_bb_pct_b=0.4,
        feat_4h_dist_bb_lower=2.5,
        feat_4h_ma_order=1.0,
        feat_4h_dist_swing_low=3.0,
        feat_4h_vol_ratio=1.8,
    )
    monkeypatch.setattr(api_module, "get_db", lambda: _FakeSession([row]))

    result = asyncio.run(api_module.api_features(days=7))

    assert len(result) == 1
    payload = result[0]
    for key in [
        "claw",
        "claw_intensity",
        "fang_pcr",
        "fang_skew",
        "fin_netflow",
        "web_whale",
        "scales_ssr",
        "nest_pred",
        "nq_return_1h",
        "nq_return_24h",
        "4h_bias50",
        "4h_bias200",
        "4h_dist_bb_lower",
        "4h_dist_sl",
        "4h_vol_ratio",
    ]:
        assert key in payload
        assert payload[key] is not None


def test_api_feature_coverage_flags_low_distinct_series(monkeypatch):
    rows = [
        SimpleNamespace(timestamp=object(), feat_eye=0.1, feat_claw=0.0, feat_claw_intensity=0.3, feat_4h_bias50=-2.0, feat_4h_ma_order=-1.0),
        SimpleNamespace(timestamp=object(), feat_eye=0.2, feat_claw=0.0, feat_claw_intensity=0.3, feat_4h_bias50=-1.5, feat_4h_ma_order=0.0),
        SimpleNamespace(timestamp=object(), feat_eye=0.3, feat_claw=0.0, feat_claw_intensity=0.3, feat_4h_bias50=-1.0, feat_4h_ma_order=1.0),
    ]
    monkeypatch.setattr(api_module, "get_db", lambda: _FakeSession(rows))

    result = asyncio.run(api_module.api_features_coverage(days=90))

    assert result["features"]["claw"]["chart_usable"] is False
    assert result["features"]["claw"]["quality_flag"] == "source_fallback_zero"
    assert "distinct<10" in result["features"]["claw"]["reasons"]
    assert result["features"]["claw"]["backfill_status"] == "blocked"
    assert result["features"]["claw"]["history_class"] == "archive_required"
    assert "CoinGlass" in result["features"]["claw"]["backfill_blocker"]
    assert result["features"]["4h_bias50"]["chart_usable"] is False
    assert result["features"]["4h_bias50"]["quality_flag"] == "low_distinct"
    assert result["features"]["4h_bias50"]["backfill_status"] == "n/a"
    assert result["features"]["4h_ma_order"]["chart_usable"] is True


def test_circuit_breaker_uses_simulated_target_column():
    rows = [(0,), (0,), (0,)] * 20
    result = predictor_module._check_circuit_breaker(_FakeSession(rows))

    assert result is not None
    assert result["signal"] == "CIRCUIT_BREAKER"
    assert "Consecutive loss streak" in result["reason"]
