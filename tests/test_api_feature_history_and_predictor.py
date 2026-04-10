import asyncio
from types import SimpleNamespace

from backtesting import strategy_lab
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
        SimpleNamespace(timestamp="2026-04-09T01:00:00+00:00", feat_eye=0.1, feat_claw=0.0, feat_claw_intensity=0.3, feat_4h_bias50=-2.0, feat_4h_ma_order=-1.0),
        SimpleNamespace(timestamp="2026-04-09T02:00:00+00:00", feat_eye=0.2, feat_claw=0.0, feat_claw_intensity=0.3, feat_4h_bias50=-1.5, feat_4h_ma_order=0.0),
        SimpleNamespace(timestamp="2026-04-09T03:00:00+00:00", feat_eye=0.3, feat_claw=0.0, feat_claw_intensity=0.3, feat_4h_bias50=-1.0, feat_4h_ma_order=1.0),
    ]
    monkeypatch.setattr(api_module, "get_db", lambda: _FakeSession(rows))
    monkeypatch.setattr(api_module, "_compute_raw_snapshot_stats", lambda db: {
        "claw_snapshot": {
            "count": 3,
            "latest_ts": "2026-04-09T03:00:00+00:00",
            "oldest_ts": "2026-04-09T01:00:00+00:00",
            "span_hours": 2.0,
            "latest_age_minutes": 120.0,
            "latest_status": "auth_missing",
            "latest_message": "COINGLASS_API_KEY missing",
        }
    })

    result = asyncio.run(api_module.api_features_coverage(days=90))

    assert result["features"]["claw"]["chart_usable"] is False
    assert result["features"]["claw"]["quality_flag"] == "source_auth_blocked"
    assert result["features"]["claw"]["quality_label"] == "source auth missing; latest snapshots are failing"
    assert result["features"]["claw"]["reasons"][0] == "source_auth_blocked"
    assert "distinct<10" in result["features"]["claw"]["reasons"]
    assert result["features"]["claw"]["backfill_status"] == "blocked"
    assert result["features"]["claw"]["history_class"] == "archive_required"
    assert result["features"]["claw"]["raw_snapshot_events"] == 3
    assert result["features"]["claw"]["forward_archive_started"] is True
    assert result["features"]["claw"]["forward_archive_ready"] is False
    assert result["features"]["claw"]["forward_archive_stale"] is True
    assert result["features"]["claw"]["forward_archive_status"] == "stale"
    assert result["features"]["claw"]["forward_archive_ready_min_events"] == 10
    assert "CoinGlass" in result["features"]["claw"]["backfill_blocker"]
    assert result["features"]["claw"]["raw_snapshot_latest_age_min"] == 120.0
    assert result["features"]["claw"]["raw_snapshot_span_hours"] == 2.0
    assert result["features"]["claw"]["archive_window_started"] is True
    assert result["features"]["claw"]["archive_window_rows"] == 3
    assert result["features"]["claw"]["archive_window_non_null"] == 3
    assert result["features"]["claw"]["archive_window_coverage_pct"] == 100.0
    assert "Forward raw snapshot archive is stale (3/10 stored event(s)" in result["features"]["claw"]["backfill_blocker"]
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


def test_live_decision_profile_matches_strategy_lab_baseline():
    features = {
        "regime_label": "bull",
        "feat_4h_bias200": 2.2,
        "feat_4h_bias50": -1.8,
        "feat_nose": 0.24,
        "feat_pulse": 0.81,
        "feat_ear": -0.04,
    }

    profile = predictor_module._build_live_decision_profile(features)

    expected_quality = strategy_lab._compute_entry_quality(-1.8, 0.24, 0.81, -0.04)
    expected_gate = strategy_lab._compute_regime_gate(2.2, "bull", -10.0)
    expected_layers = strategy_lab._allowed_layers_for_signal(expected_gate, expected_quality, 3)

    assert profile["entry_quality"] == expected_quality
    assert profile["regime_gate"] == expected_gate
    assert profile["allowed_layers"] == expected_layers
    assert profile["entry_quality_label"] == "B"
    assert profile["decision_profile_version"] == "phase16_baseline_v1"


def test_predict_confidence_route_unpacks_load_predictor_tuple(monkeypatch):
    import config as config_module
    from database import models as models_module

    closed = {"value": False}

    class _FakeDb:
        def close(self):
            closed["value"] = True

    monkeypatch.setattr(config_module, "load_config", lambda: {"database": {"url": "sqlite:///fake.db"}})
    monkeypatch.setattr(models_module, "init_db", lambda _url: _FakeDb())
    monkeypatch.setattr(predictor_module, "load_predictor", lambda: ("global-predictor", {"bull": object()}))

    def _fake_predict(session, predictor, regime_models):
        assert predictor == "global-predictor"
        assert "bull" in regime_models
        return {
            "confidence": 0.73,
            "signal": "BUY",
            "confidence_level": "HIGH",
            "should_trade": True,
            "regime_gate": "ALLOW",
            "entry_quality": 0.74,
            "entry_quality_label": "B",
            "allowed_layers": 3,
            "decision_profile_version": "phase16_baseline_v1",
        }

    monkeypatch.setattr(predictor_module, "predict", _fake_predict)

    result = asyncio.run(api_module.get_confidence_prediction())

    assert result["signal"] == "BUY"
    assert result["regime_gate"] == "ALLOW"
    assert result["allowed_layers"] == 3
    assert closed["value"] is True
