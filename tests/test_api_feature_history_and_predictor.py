import asyncio
import json
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

    assert result["maturity_counts"]["blocked"] >= 1
    assert result["features"]["claw"]["chart_usable"] is False
    assert result["features"]["claw"]["score_usable"] is False
    assert result["features"]["claw"]["maturity_tier"] == "blocked"
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
    assert result["features"]["4h_bias50"]["score_usable"] is False
    assert result["features"]["4h_bias50"]["maturity_tier"] == "blocked"
    assert result["features"]["4h_bias50"]["quality_flag"] == "low_distinct"
    assert result["features"]["4h_bias50"]["backfill_status"] == "n/a"
    assert result["features"]["4h_ma_order"]["chart_usable"] is True
    assert result["features"]["4h_ma_order"]["score_usable"] is True
    assert result["features"]["4h_ma_order"]["maturity_tier"] == "core"


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
        "feat_4h_bb_pct_b": 0.82,
        "feat_4h_dist_bb_lower": 7.2,
        "feat_4h_dist_swing_low": 9.1,
    }

    profile = predictor_module._build_live_decision_profile(features)

    expected_quality = strategy_lab._compute_entry_quality(-1.8, 0.24, 0.81, -0.04, 0.82, 7.2, 9.1)
    expected_gate = strategy_lab._compute_regime_gate(2.2, "bull", -10.0, 0.82, 7.2, 9.1)
    expected_layers = strategy_lab._allowed_layers_for_signal(expected_gate, expected_quality, 3)

    assert profile["entry_quality"] == expected_quality
    assert profile["regime_gate"] == expected_gate
    assert profile["allowed_layers"] == expected_layers
    assert profile["entry_quality_label"] == "A"
    assert profile["decision_profile_version"] == "phase16_baseline_v2"


def test_live_decision_profile_downgrades_allow_gate_when_4h_structure_collapses():
    features = {
        "regime_label": "bull",
        "feat_4h_bias200": 2.4,
        "feat_4h_bias50": -2.0,
        "feat_nose": 0.18,
        "feat_pulse": 0.78,
        "feat_ear": -0.03,
        "feat_4h_bb_pct_b": 0.10,
        "feat_4h_dist_bb_lower": 0.35,
        "feat_4h_dist_swing_low": 1.5,
    }

    profile = predictor_module._build_live_decision_profile(features)

    assert profile["regime_gate"] == "BLOCK"
    assert profile["allowed_layers"] == 0
    assert profile["entry_quality_label"] == "C"


def test_decision_quality_contract_prefers_matching_gate_and_quality_bucket():
    rows = [
        {
            "timestamp": "2026-04-10T00:00:00",
            "regime_gate": "ALLOW",
            "entry_quality_label": "B",
            "simulated_pyramid_win": 0.82,
            "simulated_pyramid_pnl": 0.14,
            "simulated_pyramid_quality": 0.71,
            "simulated_pyramid_drawdown_penalty": 0.09,
            "simulated_pyramid_time_underwater": 0.16,
        }
        for _ in range(35)
    ]
    rows.extend(
        {
            "timestamp": "2026-04-09T00:00:00",
            "regime_gate": "CAUTION",
            "entry_quality_label": "C",
            "simulated_pyramid_win": 0.31,
            "simulated_pyramid_pnl": -0.04,
            "simulated_pyramid_quality": 0.22,
            "simulated_pyramid_drawdown_penalty": 0.34,
            "simulated_pyramid_time_underwater": 0.52,
        }
        for _ in range(80)
    )

    contract = predictor_module._summarize_decision_quality_contract(
        rows,
        {
            "regime_gate": "ALLOW",
            "entry_quality_label": "B",
            "decision_profile_version": "phase16_baseline_v2",
        },
    )

    assert contract["decision_quality_calibration_scope"] == "regime_gate+entry_quality_label"
    assert contract["decision_quality_sample_size"] == 35
    assert contract["expected_win_rate"] == 0.82
    assert contract["expected_pyramid_quality"] == 0.71
    assert contract["expected_drawdown_penalty"] == 0.09
    assert contract["expected_time_underwater"] == 0.16
    assert contract["decision_quality_score"] == predictor_module._compute_decision_quality_score(0.82, 0.71, 0.09, 0.16)
    assert contract["decision_quality_label"] == "B"
    assert contract["decision_quality_calibration_window"] == len(rows)


def test_decision_quality_contract_uses_guardrail_recommended_window(monkeypatch, tmp_path):
    dw_result = tmp_path / "dw_result.json"
    dw_result.write_text(
        json.dumps(
            {
                "raw_best_n": 600,
                "recommended_best_n": 5000,
                "guardrail_policy": {"disqualifying_alerts": ["constant_target", "regime_concentration"]},
                "600": {"alerts": ["label_imbalance", "regime_concentration"], "distribution_guardrail": True},
                "5000": {"alerts": [], "distribution_guardrail": False},
            }
        )
    )
    monkeypatch.setattr(predictor_module, "DW_RESULT_PATH", dw_result)

    guardrail = predictor_module._load_dynamic_window_guardrail()

    assert guardrail["recommended_best_n"] == 5000
    assert guardrail["raw_best_guardrailed"] is True
    assert "raw_best_n=600" in guardrail["guardrail_reason"]


def test_decision_quality_contract_guardrails_imbalanced_bucket_to_broader_scope():
    rows = [
        {
            "timestamp": f"2026-04-10T00:{i:02d}:00",
            "regime_gate": "CAUTION",
            "entry_quality_label": "B",
            "simulated_pyramid_win": 1.0,
            "simulated_pyramid_pnl": 0.15,
            "simulated_pyramid_quality": 0.72,
            "simulated_pyramid_drawdown_penalty": 0.08,
            "simulated_pyramid_time_underwater": 0.15,
        }
        for i in range(40)
    ]
    rows.extend(
        {
            "timestamp": f"2026-04-09T00:{i:02d}:00",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "simulated_pyramid_win": 1.0 if i < 50 else 0.0,
            "simulated_pyramid_pnl": 0.05 if i < 50 else -0.03,
            "simulated_pyramid_quality": 0.44 if i < 50 else 0.28,
            "simulated_pyramid_drawdown_penalty": 0.14 if i < 50 else 0.21,
            "simulated_pyramid_time_underwater": 0.21 if i < 50 else 0.34,
        }
        for i in range(80)
    )

    contract = predictor_module._summarize_decision_quality_contract(
        rows,
        {
            "regime_gate": "CAUTION",
            "entry_quality_label": "B",
            "decision_profile_version": "phase16_baseline_v2",
        },
        enforce_scope_guardrails=True,
    )

    assert contract["decision_quality_calibration_scope"] == "regime_gate"
    assert contract["decision_quality_sample_size"] == 120
    assert contract["decision_quality_scope_guardrail_applied"] is True
    assert contract["decision_quality_scope_guardrail_alerts"] == ["constant_target"]
    assert "scope regime_gate+entry_quality_label rejected" in contract["decision_quality_scope_guardrail_reason"]
    assert contract["expected_win_rate"] == 0.75


def test_decision_quality_contract_penalizes_negative_recent_pathology_in_chosen_scope():
    rows = [
        {
            "timestamp": f"2026-04-10T00:{i:02d}:00",
            "regime_gate": "CAUTION",
            "entry_quality_label": "C",
            "simulated_pyramid_win": 0.82,
            "simulated_pyramid_pnl": 0.12,
            "simulated_pyramid_quality": 0.62,
            "simulated_pyramid_drawdown_penalty": 0.12,
            "simulated_pyramid_time_underwater": 0.18,
        }
        for i in range(200)
    ]
    rows.extend(
        {
            "timestamp": f"2026-04-11T00:{i:02d}:00",
            "regime_gate": "CAUTION",
            "entry_quality_label": "C",
            "simulated_pyramid_win": 0.0,
            "simulated_pyramid_pnl": -0.04,
            "simulated_pyramid_quality": -0.22,
            "simulated_pyramid_drawdown_penalty": 0.31,
            "simulated_pyramid_time_underwater": 0.57,
        }
        for i in range(100)
    )

    contract = predictor_module._summarize_decision_quality_contract(
        rows,
        {
            "regime_gate": "CAUTION",
            "entry_quality_label": "C",
            "decision_profile_version": "phase16_baseline_v2",
        },
    )

    assert contract["decision_quality_calibration_scope"] == "regime_gate+entry_quality_label"
    assert contract["decision_quality_recent_pathology_applied"] is True
    assert contract["decision_quality_recent_pathology_window"] == 100
    assert contract["decision_quality_recent_pathology_alerts"] == ["constant_target"]
    assert contract["expected_win_rate"] == 0.0
    assert contract["expected_pyramid_pnl"] == -0.04
    assert contract["expected_pyramid_quality"] == -0.22
    assert contract["expected_drawdown_penalty"] == 0.31
    assert contract["decision_quality_label"] == "D"
    assert "distribution_pathology" in contract["decision_quality_recent_pathology_reason"]


def test_decision_quality_scope_diagnostics_expose_narrow_and_broad_pathology_lanes():
    rows = []
    for i in range(120):
        rows.append(
            {
                "timestamp": f"2026-04-10T00:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "bull",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "feat_4h_bias200": 2.4,
                "feat_4h_dist_bb_lower": 7.5,
                "feat_4h_dist_swing_low": 8.0,
                "feat_4h_bb_pct_b": 0.92,
                "simulated_pyramid_win": 1.0,
                "simulated_pyramid_pnl": 0.012,
                "simulated_pyramid_quality": 0.42,
                "simulated_pyramid_drawdown_penalty": 0.18,
                "simulated_pyramid_time_underwater": 0.42,
            }
        )
    for i in range(100):
        rows.append(
            {
                "timestamp": f"2026-04-11T00:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "bull",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "feat_4h_bias200": 0.9,
                "feat_4h_dist_bb_lower": 0.4,
                "feat_4h_dist_swing_low": 1.7,
                "feat_4h_bb_pct_b": 0.13,
                "simulated_pyramid_win": 0.0,
                "simulated_pyramid_pnl": -0.011,
                "simulated_pyramid_quality": -0.28,
                "simulated_pyramid_drawdown_penalty": 0.28,
                "simulated_pyramid_time_underwater": 0.88,
            }
        )
    for i in range(380):
        rows.append(
            {
                "timestamp": f"2026-04-12T00:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "chop",
                "regime_gate": "CAUTION",
                "entry_quality_label": "D",
                "feat_4h_bias200": 0.8,
                "feat_4h_dist_bb_lower": 1.3,
                "feat_4h_dist_swing_low": 2.0,
                "feat_4h_bb_pct_b": 0.4,
                "simulated_pyramid_win": 0.0,
                "simulated_pyramid_pnl": -0.008,
                "simulated_pyramid_quality": -0.16,
                "simulated_pyramid_drawdown_penalty": 0.26,
                "simulated_pyramid_time_underwater": 0.75,
            }
        )

    diags = predictor_module._build_decision_quality_scope_diagnostics(
        rows,
        {
            "regime_label": "bull",
            "regime_gate": "ALLOW",
            "entry_quality_label": "D",
        },
    )

    exact_narrow = diags["regime_label+regime_gate+entry_quality_label"]
    narrow = diags["regime_gate+entry_quality_label"]
    regime_narrow = diags["regime_label+entry_quality_label"]
    broad = diags["entry_quality_label"]
    assert exact_narrow["rows"] == 220
    assert exact_narrow["recent500_regime_counts"] == {"bull": 220}
    assert exact_narrow["recent500_dominant_regime"] == {"regime": "bull", "count": 220, "share": 1.0}
    assert exact_narrow["recent500_gate_counts"] == {"ALLOW": 220}
    assert exact_narrow["recent500_dominant_gate"] == {"gate": "ALLOW", "count": 220, "share": 1.0}
    assert exact_narrow["recent500_regime_gate_counts"] == {"bull|ALLOW": 220}
    assert exact_narrow["recent500_dominant_regime_gate"] == {
        "regime_gate": "bull|ALLOW",
        "regime": "bull",
        "gate": "ALLOW",
        "count": 220,
        "share": 1.0,
    }
    assert exact_narrow["avg_drawdown_penalty"] == 0.2255
    assert exact_narrow["avg_time_underwater"] == 0.6291
    assert exact_narrow["spillover_vs_exact_live_lane"] is None
    assert exact_narrow["recent_pathology"]["applied"] is True
    assert exact_narrow["recent_pathology"]["window"] == 100
    assert narrow["rows"] == 220
    assert narrow["recent500_regime_counts"] == {"bull": 220}
    assert narrow["recent500_dominant_regime"] == {"regime": "bull", "count": 220, "share": 1.0}
    assert narrow["recent500_gate_counts"] == {"ALLOW": 220}
    assert narrow["recent500_dominant_gate"] == {"gate": "ALLOW", "count": 220, "share": 1.0}
    assert narrow["recent500_regime_gate_counts"] == {"bull|ALLOW": 220}
    assert narrow["recent500_dominant_regime_gate"] == {
        "regime_gate": "bull|ALLOW",
        "regime": "bull",
        "gate": "ALLOW",
        "count": 220,
        "share": 1.0,
    }
    assert narrow["recent_pathology"]["applied"] is True
    assert narrow["recent_pathology"]["window"] == 100
    assert broad["rows"] == 600
    assert broad["recent500_regime_counts"] == {"chop": 280, "bull": 220}
    assert broad["recent500_dominant_regime"] == {"regime": "chop", "count": 280, "share": 0.56}
    assert broad["recent500_gate_counts"] == {"CAUTION": 280, "ALLOW": 220}
    assert broad["recent500_dominant_gate"] == {"gate": "CAUTION", "count": 280, "share": 0.56}
    assert broad["recent500_regime_gate_counts"] == {"chop|CAUTION": 280, "bull|ALLOW": 220}
    assert broad["recent500_dominant_regime_gate"] == {
        "regime_gate": "chop|CAUTION",
        "regime": "chop",
        "gate": "CAUTION",
        "count": 280,
        "share": 0.56,
    }
    spillover = broad["spillover_vs_exact_live_lane"]
    assert spillover["extra_rows"] == 380
    assert spillover["extra_row_share"] == 0.6333
    assert spillover["extra_gate_counts"] == {"CAUTION": 280}
    assert spillover["extra_dominant_gate"] == {"gate": "CAUTION", "count": 280, "share": 1.0}
    assert spillover["extra_regime_gate_counts"] == {"chop|CAUTION": 280}
    assert spillover["extra_dominant_regime_gate"] == {
        "regime_gate": "chop|CAUTION",
        "regime": "chop",
        "gate": "CAUTION",
        "count": 280,
        "share": 1.0,
    }
    assert spillover["extra_regime_gate_metrics"] == {
        "chop|CAUTION": {
            "rows": 380,
            "win_rate": 0.0,
            "avg_pnl": -0.008,
            "avg_quality": -0.16,
            "avg_drawdown_penalty": 0.26,
            "avg_time_underwater": 0.75,
        }
    }
    assert spillover["worst_extra_regime_gate"] == {
        "regime_gate": "chop|CAUTION",
        "regime": "chop",
        "gate": "CAUTION",
        "rows": 380,
        "win_rate": 0.0,
        "avg_pnl": -0.008,
        "avg_quality": -0.16,
        "avg_drawdown_penalty": 0.26,
        "avg_time_underwater": 0.75,
    }
    assert spillover["worst_extra_regime_gate_feature_contrast"] == {
        "current_quality": {
            "win_rate": 0.0,
            "avg_simulated_pnl": -0.008,
            "avg_simulated_quality": -0.16,
            "avg_drawdown_penalty": 0.26,
            "avg_time_underwater": 0.75,
        },
        "reference_quality": {
            "win_rate": 0.5455,
            "avg_simulated_pnl": 0.0015,
            "avg_simulated_quality": 0.1018,
            "avg_drawdown_penalty": 0.2255,
            "avg_time_underwater": 0.6291,
        },
        "win_rate_delta_vs_reference": -0.5455,
        "avg_simulated_pnl_delta_vs_reference": -0.0095,
        "avg_simulated_quality_delta_vs_reference": -0.2618,
        "avg_drawdown_penalty_delta_vs_reference": 0.0345,
        "avg_time_underwater_delta_vs_reference": 0.1209,
        "top_mean_shift_features": [
            {"feature": "feat_4h_dist_swing_low", "current_mean": 2.0, "reference_mean": 5.1364, "mean_delta": -3.1364},
            {"feature": "feat_4h_dist_bb_lower", "current_mean": 1.3, "reference_mean": 4.2727, "mean_delta": -2.9727},
            {"feature": "feat_4h_bias200", "current_mean": 0.8, "reference_mean": 1.7182, "mean_delta": -0.9182},
        ],
    }
    assert spillover["worst_extra_regime_gate_feature_snapshot"] == {
        "feat_4h_bias200": {"current_mean": 0.8, "reference_mean": 1.7182, "mean_delta": -0.9182},
        "feat_4h_bb_pct_b": {"current_mean": 0.4, "reference_mean": 0.5609, "mean_delta": -0.1609},
        "feat_4h_dist_bb_lower": {"current_mean": 1.3, "reference_mean": 4.2727, "mean_delta": -2.9727},
        "feat_4h_dist_swing_low": {"current_mean": 2.0, "reference_mean": 5.1364, "mean_delta": -3.1364},
    }
    assert spillover["worst_extra_regime_gate_path_summary"] == {
        "rows": 380,
        "final_gate_counts": {"CAUTION": 380},
        "final_reason_counts": {"base_caution_regime_or_bias": 380},
        "base_gate_counts": {"CAUTION": 380},
        "avg_structure_quality": 0.2556,
        "avg_bias200": 0.8,
        "missing_input_rows": 0,
        "missing_input_feature_counts": {},
    }
    assert spillover["exact_live_gate_path_summary"] == {
        "rows": 220,
        "final_gate_counts": {"ALLOW": 120, "BLOCK": 100},
        "final_reason_counts": {"base_allow": 120, "structure_quality_block": 100},
        "base_gate_counts": {"ALLOW": 220},
        "avg_structure_quality": 0.5365,
        "avg_bias200": 1.7182,
        "missing_input_rows": 0,
        "missing_input_feature_counts": {},
    }
    assert spillover["win_rate_delta_vs_exact"] == -0.3455
    assert spillover["avg_pnl_delta_vs_exact"] == -0.006
    assert spillover["avg_quality_delta_vs_exact"] == -0.1658
    assert spillover["avg_drawdown_penalty_delta_vs_exact"] == 0.0218
    assert spillover["avg_time_underwater_delta_vs_exact"] == 0.0766
    assert broad["recent_pathology"]["applied"] is True
    assert broad["recent_pathology"]["window"] == 250

    consensus = diags["pathology_consensus"]
    assert consensus["pathology_scope_count"] == 4
    assert consensus["worst_pathology_scope"]["scope"] == "entry_quality_label"
    assert consensus["worst_pathology_scope"]["recent500_regime_counts"] == broad["recent500_regime_counts"]
    exact_scope = next(row for row in consensus["pathology_scopes"] if row["scope"] == "regime_label+regime_gate+entry_quality_label")
    assert exact_scope["recent500_regime_counts"] == exact_narrow["recent500_regime_counts"]
    assert exact_scope["recent500_dominant_regime"] == {"regime": "bull", "count": 220, "share": 1.0}
    regime_scope = next(row for row in consensus["pathology_scopes"] if row["scope"] == "regime_label+entry_quality_label")
    assert regime_scope["recent500_regime_counts"] == regime_narrow["recent500_regime_counts"]
    assert regime_scope["recent500_dominant_regime"] == {"regime": "bull", "count": 220, "share": 1.0}
    assert regime_scope["recent500_gate_counts"] == regime_narrow["recent500_gate_counts"]
    assert regime_scope["recent500_dominant_gate"] == regime_narrow["recent500_dominant_gate"]
    assert regime_scope["recent500_regime_gate_counts"] == regime_narrow["recent500_regime_gate_counts"]
    assert regime_scope["recent500_dominant_regime_gate"] == regime_narrow["recent500_dominant_regime_gate"]
    shared_features = {row["feature"]: row for row in consensus["shared_top_shift_features"]}
    assert {"feat_4h_dist_bb_lower", "feat_4h_dist_swing_low", "feat_4h_bb_pct_b"}.issuperset(shared_features)
    assert shared_features["feat_4h_dist_swing_low"]["scope_count"] == 4
    assert set(shared_features["feat_4h_dist_swing_low"]["scopes"]) == {
        "regime_label+regime_gate+entry_quality_label",
        "regime_gate+entry_quality_label",
        "regime_label+entry_quality_label",
        "entry_quality_label",
    }


def test_decision_quality_contract_clamps_to_worse_regime_specific_d_lane_when_broader_scope_hides_bull_pathology():
    def _stamp(day: str, idx: int) -> str:
        hour, minute = divmod(idx, 60)
        return f"{day}T{hour:02d}:{minute:02d}:00"

    rows = []
    for i in range(127):
        rows.append(
            {
                "timestamp": _stamp("2026-04-12", i),
                "symbol": "BTCUSDT",
                "regime_label": "neutral" if i < 102 else "bull",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "feat_4h_dist_bb_lower": 6.9,
                "feat_4h_dist_swing_low": 7.2,
                "feat_4h_bb_pct_b": 1.16,
                "simulated_pyramid_win": 1.0 if i < 28 else 0.0,
                "simulated_pyramid_pnl": 0.004 if i < 28 else -0.0048,
                "simulated_pyramid_quality": 0.05 if i < 28 else -0.1156,
                "simulated_pyramid_drawdown_penalty": 0.14 if i < 28 else 0.22,
                "simulated_pyramid_time_underwater": 0.29 if i < 28 else 0.39,
            }
        )
    for i in range(147):
        rows.append(
            {
                "timestamp": _stamp("2026-04-11", i),
                "symbol": "BTCUSDT",
                "regime_label": "bull",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "feat_4h_dist_bb_lower": 6.86,
                "feat_4h_dist_swing_low": 7.18,
                "feat_4h_bb_pct_b": 1.16,
                "simulated_pyramid_win": 1.0 if i < 11 else 0.0,
                "simulated_pyramid_pnl": 0.001 if i < 11 else -0.0158,
                "simulated_pyramid_quality": -0.05 if i < 11 else -0.2218,
                "simulated_pyramid_drawdown_penalty": 0.19 if i < 11 else 0.31,
                "simulated_pyramid_time_underwater": 0.41 if i < 11 else 0.98,
            }
        )
    for i in range(3463):
        rows.append(
            {
                "timestamp": _stamp("2026-04-10", i),
                "symbol": "BTCUSDT",
                "regime_label": "chop",
                "regime_gate": "CAUTION",
                "entry_quality_label": "D",
                "feat_4h_dist_bb_lower": 1.3,
                "feat_4h_dist_swing_low": 2.1,
                "feat_4h_bb_pct_b": 0.4,
                "simulated_pyramid_win": 1.0 if i < 2397 else 0.0,
                "simulated_pyramid_pnl": 0.018 if i < 2397 else -0.0042,
                "simulated_pyramid_quality": 0.43 if i < 2397 else 0.085,
                "simulated_pyramid_drawdown_penalty": 0.08 if i < 2397 else 0.21,
                "simulated_pyramid_time_underwater": 0.24 if i < 2397 else 0.44,
            }
        )

    contract = predictor_module._summarize_decision_quality_contract(
        rows,
        {
            "regime_label": "bull",
            "regime_gate": "ALLOW",
            "entry_quality_label": "D",
            "decision_profile_version": "phase16_baseline_v2",
        },
    )

    assert contract["decision_quality_calibration_scope"] == "regime_label+regime_gate+entry_quality_label"
    assert contract["decision_quality_sample_size"] == 172
    assert contract["decision_quality_recent_pathology_applied"] is True
    assert contract["decision_quality_recent_pathology_window"] == 100
    assert contract["decision_quality_narrowed_pathology_applied"] is False
    assert contract["expected_win_rate"] == 0.0
    assert contract["expected_pyramid_pnl"] == -0.0131
    assert contract["expected_pyramid_quality"] == -0.1954
    assert contract["expected_drawdown_penalty"] == 0.2892
    assert contract["expected_time_underwater"] == 0.8578
    assert contract["decision_quality_guardrail_applied"] is False



def test_recent_scope_pathology_prefers_more_persistent_negative_window_when_scores_tie():
    def _ts(i: int) -> str:
        return f"2026-04-12T{(i // 60):02d}:{(i % 60):02d}:00"

    rows = [
        {
            "timestamp": f"2026-04-11T{(i // 60):02d}:{(i % 60):02d}:00",
            "symbol": "BTCUSDT",
            "regime_gate": "CAUTION",
            "entry_quality_label": "C",
            "feat_4h_dist_bb_lower": 6.0,
            "feat_4h_dist_swing_low": 8.5,
            "feat_4h_bb_pct_b": 0.78,
            "simulated_pyramid_win": 0.82,
            "simulated_pyramid_pnl": 0.08,
            "simulated_pyramid_quality": 0.41,
            "simulated_pyramid_drawdown_penalty": 0.12,
            "simulated_pyramid_time_underwater": 0.18,
        }
        for i in range(250)
    ]
    rows.extend(
        {
            "timestamp": _ts(i),
            "symbol": "BTCUSDT",
            "regime_gate": "CAUTION",
            "entry_quality_label": "C",
            "feat_4h_dist_bb_lower": 0.35,
            "feat_4h_dist_swing_low": 1.4,
            "feat_4h_bb_pct_b": 0.11,
            "simulated_pyramid_win": 0.0,
            "simulated_pyramid_pnl": -0.04,
            "simulated_pyramid_quality": -0.22,
            "simulated_pyramid_drawdown_penalty": 0.31,
            "simulated_pyramid_time_underwater": 0.57,
        }
        for i in range(250)
    )

    summary = predictor_module._recent_scope_pathology_summary(rows)

    assert summary["applied"] is True
    assert summary["window"] == 250
    assert summary["alerts"] == ["constant_target"]
    assert summary["summary"]["win_rate"] == 0.0
    assert summary["summary"]["start_timestamp"] == "2026-04-12T00:00:00"
    assert summary["summary"]["end_timestamp"] == "2026-04-12T04:09:00"
    assert summary["summary"]["adverse_target_streak"]["target"] == 0
    assert summary["summary"]["adverse_target_streak"]["count"] == 250
    comparison = summary["summary"]["reference_window_comparison"]
    assert comparison["reference_quality"]["win_rate"] == 0.82
    assert comparison["win_rate_delta_vs_reference"] == -0.82
    assert comparison["avg_simulated_quality_delta_vs_reference"] == -0.63
    assert comparison["top_mean_shift_features"][0]["feature"] == "feat_4h_dist_swing_low"
    assert "window=2026-04-12T00:00:00->2026-04-12T04:09:00" in summary["reason"]
    assert "adverse_streak=250x0" in summary["reason"]
    assert "vs sibling prev_win_rate=0.82" in summary["reason"]
    assert "feat_4h_dist_swing_low(8.5→1.4)" in summary["reason"]


def test_apply_live_execution_guardrails_caps_layers_for_c_quality_and_guardrailed_window():
    profile = {
        "regime_label": "chop",
        "regime_gate": "CAUTION",
        "entry_quality": 0.91,
        "entry_quality_label": "A",
        "allowed_layers": 2,
        "decision_profile_version": "phase16_baseline_v2",
    }
    contract = {
        **predictor_module._decision_quality_fallback(),
        "decision_quality_guardrail_applied": True,
        "decision_quality_label": "C",
        "decision_quality_score": 0.3759,
    }

    guarded = predictor_module._apply_live_execution_guardrails(profile, contract)

    assert guarded["allowed_layers_raw"] == 2
    assert guarded["allowed_layers"] == 1
    assert guarded["execution_guardrail_applied"] is True
    assert "decision_quality_label_C_caps_layers" in guarded["execution_guardrail_reason"]


def test_apply_live_execution_guardrails_blocks_trade_for_recent_distribution_pathology():
    profile = {
        "regime_label": "chop",
        "regime_gate": "CAUTION",
        "entry_quality": 0.74,
        "entry_quality_label": "B",
        "allowed_layers": 2,
        "decision_profile_version": "phase16_baseline_v2",
    }
    contract = {
        **predictor_module._decision_quality_fallback(),
        "decision_quality_guardrail_applied": True,
        "decision_quality_recent_pathology_applied": True,
        "decision_quality_recent_pathology_reason": "recent scope slice 100 rows shows distribution_pathology",
        "decision_quality_label": "B",
        "decision_quality_score": 0.51,
    }

    guarded = predictor_module._apply_live_execution_guardrails(profile, contract)

    assert guarded["allowed_layers_raw"] == 2
    assert guarded["allowed_layers"] == 0
    assert guarded["execution_guardrail_applied"] is True
    assert "recent_distribution_pathology_blocks_trade" in guarded["execution_guardrail_reason"]


def test_predict_applies_execution_guardrail_to_live_result(monkeypatch):
    monkeypatch.setattr(predictor_module, "_check_circuit_breaker", lambda session: None)
    monkeypatch.setattr(
        predictor_module,
        "load_latest_features",
        lambda session: {
            "regime_label": "chop",
            "feat_body": -0.2,
            "feat_mind": -0.1,
            "feat_4h_bias200": -0.5,
            "feat_4h_bias50": -0.2,
            "feat_nose": 0.1,
            "feat_pulse": 0.8,
            "feat_ear": -0.05,
        },
    )
    monkeypatch.setattr(
        predictor_module,
        "_infer_live_decision_quality_contract",
        lambda session, decision_profile, horizon_minutes=1440, lookback_rows=5000: {
            **predictor_module._decision_quality_fallback(),
            "decision_quality_guardrail_applied": True,
            "decision_quality_guardrail_reason": "raw_best_n=600 guardrailed",
            "decision_quality_label": "C",
            "decision_quality_score": 0.39,
        },
    )

    class _FakePredictor:
        def predict_proba(self, features):
            return 0.78

    result = predictor_module.predict(session=object(), predictor=_FakePredictor(), regime_models={})

    assert result["signal"] == "BUY"
    assert result["allowed_layers_raw"] == 2
    assert result["allowed_layers"] == 1
    assert result["execution_guardrail_applied"] is True
    assert result["should_trade"] is True


def test_predict_routes_regime_model_using_decision_profile_regime(monkeypatch):
    monkeypatch.setattr(predictor_module, "_check_circuit_breaker", lambda session: None)
    monkeypatch.setattr(
        predictor_module,
        "load_latest_features",
        lambda session: {
            "regime_label": "chop",
            "feat_body": -0.9,
            "feat_mind": -0.8,
            "feat_4h_bias200": -0.5,
            "feat_4h_bias50": -0.1,
            "feat_nose": 0.1,
            "feat_pulse": 0.8,
            "feat_ear": -0.05,
        },
    )
    monkeypatch.setattr(
        predictor_module,
        "_infer_live_decision_quality_contract",
        lambda session, decision_profile, horizon_minutes=1440, lookback_rows=5000: {
            **predictor_module._decision_quality_fallback(),
            "decision_quality_calibration_scope": "global",
            "decision_quality_calibration_window": 5000,
        },
    )

    class _FakePredictor:
        def predict_proba(self, features):
            return 0.62

    class _FakeRegimePredictor:
        def __init__(self, model):
            self.model = model

        def predict_proba(self, features):
            return self.model["confidence"]

    monkeypatch.setattr(predictor_module, "XGBoostPredictor", _FakeRegimePredictor)

    result = predictor_module.predict(
        session=object(),
        predictor=_FakePredictor(),
        regime_models={
            "bear": {"confidence": 0.91},
            "chop": {"confidence": 0.48},
        },
    )

    assert result["regime_label"] == "chop"
    assert result["model_route_regime"] == "chop"
    assert result["used_model"] == "regime_chop_abstain"


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
            "decision_quality_horizon_minutes": 1440,
            "decision_quality_calibration_scope": "regime_gate+entry_quality_label",
            "decision_quality_calibration_window": 5000,
            "decision_quality_sample_size": 64,
            "decision_quality_reference_from": "2026-04-10 12:00:00",
            "decision_quality_guardrail_applied": True,
            "decision_quality_guardrail_reason": "raw_best_n=600 guardrailed via alerts=['label_imbalance', 'regime_concentration']",
            "expected_win_rate": 0.68,
            "expected_pyramid_pnl": 0.12,
            "expected_pyramid_quality": 0.61,
            "expected_drawdown_penalty": 0.09,
            "expected_time_underwater": 0.22,
            "decision_quality_score": 0.4405,
            "decision_quality_label": "C",
            "decision_profile_version": "phase16_baseline_v2",
        }

    monkeypatch.setattr(predictor_module, "predict", _fake_predict)

    result = asyncio.run(api_module.get_confidence_prediction())

    assert result["signal"] == "BUY"
    assert result["regime_gate"] == "ALLOW"
    assert result["allowed_layers"] == 3
    assert result["decision_quality_calibration_scope"] == "regime_gate+entry_quality_label"
    assert result["decision_quality_calibration_window"] == 5000
    assert result["decision_quality_guardrail_applied"] is True
    assert result["expected_drawdown_penalty"] == 0.09
    assert result["decision_profile_version"] == "phase16_baseline_v2"
    assert closed["value"] is True


def test_backtest_route_uses_canonical_features_and_returns_decision_quality(monkeypatch):
    class _FakeExchange:
        def fetch_ohlcv(self, symbol, interval, limit=0):
            assert symbol == "BTCUSDT"
            assert interval in {"4h", "1d"}
            return [
                [1712793600000, 100.0, 101.0, 99.0, 100.0, 10.0],
                [1712808000000, 101.0, 102.0, 100.0, 101.0, 11.0],
                [1712822400000, 102.0, 103.0, 101.0, 102.0, 12.0],
                [1712836800000, 103.0, 104.0, 102.0, 103.0, 13.0],
                [1712851200000, 104.0, 105.0, 103.0, 104.0, 14.0],
                [1712865600000, 105.0, 106.0, 104.0, 105.0, 15.0],
                [1712880000000, 106.0, 107.0, 105.0, 106.0, 16.0],
                [1712894400000, 107.0, 108.0, 106.0, 107.0, 17.0],
                [1712908800000, 108.0, 109.0, 107.0, 108.0, 18.0],
                [1712923200000, 109.0, 110.0, 108.0, 109.0, 19.0],
                [1712937600000, 110.0, 111.0, 109.0, 110.0, 20.0],
                [1712952000000, 111.0, 112.0, 110.0, 111.0, 21.0],
                [1712966400000, 112.0, 113.0, 111.0, 112.0, 22.0],
                [1712980800000, 113.0, 114.0, 112.0, 113.0, 23.0],
                [1712995200000, 114.0, 115.0, 113.0, 114.0, 24.0],
                [1713009600000, 115.0, 116.0, 114.0, 115.0, 25.0],
                [1713024000000, 116.0, 117.0, 115.0, 116.0, 26.0],
                [1713038400000, 117.0, 118.0, 116.0, 117.0, 27.0],
                [1713052800000, 118.0, 119.0, 117.0, 118.0, 28.0],
                [1713067200000, 119.0, 120.0, 118.0, 119.0, 29.0],
            ]

    class _FakeQueryBacktest:
        def __init__(self, rows):
            self._rows = rows

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return self._rows

    class _FakeDbBacktest:
        def __init__(self, rows):
            self._rows = rows

        def query(self, *args, **kwargs):
            return _FakeQueryBacktest(self._rows)

    rows = [
        SimpleNamespace(
            timestamp=SimpleNamespace(timestamp=lambda ts=1712793600 + i * 14400: ts),
            feat_eye=3.0,
            feat_ear=0.02,
            feat_nose=0.20,
            feat_tongue=0.0,
            feat_body=0.8,
            feat_pulse=0.95,
            feat_aura=0.01,
            feat_mind=0.02,
            feat_4h_bias50=-5.0,
            feat_4h_bias200=4.0,
            regime_label="bull",
        )
        for i in range(20)
    ]

    monkeypatch.setattr(api_module.ccxt, "binance", lambda: _FakeExchange())
    monkeypatch.setattr(api_module, "get_db", lambda: _FakeDbBacktest(rows))
    monkeypatch.setattr(
        api_module,
        "_compute_strategy_decision_quality_profile",
        lambda trades, db=None, horizon_minutes=1440: {
            **api_module._strategy_decision_contract_meta(horizon_minutes=horizon_minutes),
            "avg_expected_win_rate": 0.71,
            "avg_expected_pyramid_pnl": 0.12,
            "avg_expected_pyramid_quality": 0.63,
            "avg_expected_drawdown_penalty": 0.09,
            "avg_expected_time_underwater": 0.21,
            "avg_decision_quality_score": 0.4315,
            "decision_quality_label": "C",
            "decision_quality_sample_size": 3,
        },
    )

    result = asyncio.run(api_module.api_backtest(days=3, initial_capital=10000.0))

    assert "error" not in result
    assert result["total_trades"] >= 1
    assert result["decision_contract"]["target_col"] == "simulated_pyramid_win"
    assert result["decision_contract"]["decision_quality_horizon_minutes"] == 1440
    assert result["avg_expected_win_rate"] == 0.71
    assert result["avg_decision_quality_score"] == 0.4315
    assert result["decision_quality_label"] == "C"
    assert result["dominant_regime_gate"] == "ALLOW"
    assert result["avg_allowed_layers"] == 3.0
    assert result["avg_entry_quality"] is not None
    assert result["trades"][0]["entry_quality_label"] in {"A", "B", "C", "D"}
    assert result["trades"][0]["entry_timestamp"].endswith("Z")
