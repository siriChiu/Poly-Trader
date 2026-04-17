import asyncio
import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from backtesting import strategy_lab
from server.routes import api as api_module
from model import predictor as predictor_module
from model import q35_bias50_calibration as q35_calibration_module


class _FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *args, **kwargs):
        filtered = list(self._rows)
        for arg in args:
            expr = str(arg)
            if "horizon_minutes" in expr:
                filtered = [row for row in filtered if getattr(row, "horizon_minutes", 1440) == 1440]
        self._rows = filtered
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


class _FakeLabelRow:
    def __init__(self, target, horizon_minutes=1440):
        self.target = target
        self.horizon_minutes = horizon_minutes

    def __getitem__(self, idx):
        if idx == 0:
            return self.target
        raise IndexError(idx)


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def query(self, *args, **kwargs):
        return _FakeQuery(self._rows)


def test_api_features_exposes_extended_feature_history_keys(monkeypatch):
    row = SimpleNamespace(
        timestamp=datetime(2026, 4, 8, 12, 0, 0),
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
        assert f"raw_{key}" in payload
    assert payload["timestamp"] == "2026-04-08T12:00:00Z"
    assert payload["raw_fang_pcr"] == pytest.approx(0.5)
    assert payload["raw_claw"] == pytest.approx(0.3)


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
    rows = [_FakeLabelRow(0, 1440) for _ in range(60)]
    result = predictor_module._check_circuit_breaker(_FakeSession(rows))

    assert result is not None
    assert result["signal"] == "CIRCUIT_BREAKER"
    assert "Consecutive loss streak" in result["reason"]
    assert result["horizon_minutes"] == 1440
    assert result["triggered_by"] == ["streak", "recent_win_rate"]
    assert result["recent_window_win_rate"] == 0.0
    release = result["deployment_blocker_details"]["release_condition"]
    assert release["current_streak"] == 60
    assert release["current_recent_window_wins"] == 0
    assert release["required_recent_window_wins"] == 15
    assert release["additional_recent_window_wins_needed"] == 15
    assert release["blocked_by"] == ["streak", "recent_win_rate"]


def test_circuit_breaker_ignores_noncanonical_240m_tail_when_1440m_is_healthy():
    rows = [_FakeLabelRow(0, 240) for _ in range(60)] + [_FakeLabelRow(1, 1440) for _ in range(60)]

    result = predictor_module._check_circuit_breaker(_FakeSession(rows))

    assert result is None


def test_circuit_breaker_surfaces_recent_pathology_from_drift_report(tmp_path, monkeypatch):
    drift_path = tmp_path / "recent_drift_report.json"
    drift_path.write_text(
        json.dumps(
            {
                "primary_window": {
                    "window": "500",
                    "alerts": ["label_imbalance", "regime_concentration"],
                    "summary": {
                        "rows": 500,
                        "wins": 402,
                        "losses": 98,
                        "win_rate": 0.804,
                        "drift_interpretation": "distribution_pathology",
                        "dominant_regime": "bull",
                        "dominant_regime_share": 1.0,
                        "quality_metrics": {
                            "avg_simulated_pnl": 0.0046,
                            "avg_simulated_quality": 0.3388,
                            "avg_drawdown_penalty": 0.1538,
                            "avg_time_underwater": 0.4919,
                        },
                        "feature_diagnostics": {
                            "unexpected_frozen_count": 0,
                            "unexpected_compressed_count": 8,
                        },
                        "reference_window_comparison": {
                            "top_mean_shift_features": ["feat_4h_bias20", "feat_vix"],
                        },
                        "target_path_diagnostics": {
                            "longest_target_streak": 259,
                            "longest_one_target_streak": 259,
                        },
                    },
                }
            }
        )
    )
    monkeypatch.setattr(predictor_module, "RECENT_DRIFT_REPORT_PATH", drift_path)

    rows = [_FakeLabelRow(0, 1440) for _ in range(60)]
    result = predictor_module._check_circuit_breaker(_FakeSession(rows))

    assert result is not None
    assert result["decision_quality_recent_pathology_applied"] is True
    assert result["decision_quality_recent_pathology_window"] == 500
    assert result["decision_quality_recent_pathology_alerts"] == ["label_imbalance", "regime_concentration"]
    assert "distribution_pathology" in result["decision_quality_recent_pathology_reason"]
    assert result["decision_quality_recent_pathology_summary"]["dominant_regime"] == "bull"
    assert result["decision_quality_recent_pathology_summary"]["top_mean_shift_features"] == ["feat_4h_bias20", "feat_vix"]
    assert result["decision_quality_recent_pathology_summary"]["longest_one_target_streak"] == 259


def test_infer_deployment_blocker_flags_bull_q35_no_deploy_governance(tmp_path, monkeypatch):
    q35_path = tmp_path / "q35_scaling_audit.json"
    q15_path = tmp_path / "q15_support_audit.json"
    q35_path.write_text(
        json.dumps(
            {
                "scope_applicability": {"status": "current_live_q35_lane_active"},
                "current_live": {
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                },
                "base_stack_redesign_experiment": {
                    "verdict": "base_stack_redesign_floor_cross_requires_non_discriminative_reweight",
                    "machine_read_answer": {
                        "entry_quality_ge_0_55": False,
                        "allowed_layers_gt_zero": False,
                    },
                    "best_discriminative_candidate": {
                        "entry_quality_after": 0.3767,
                    },
                    "best_floor_candidate": {
                        "entry_quality_after": 0.8375,
                    },
                    "unsafe_floor_cross_candidate": {
                        "weights": {"feat_ear": 1.0},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    q15_path.write_text(
        json.dumps(
            {
                "support_route": {"verdict": "exact_bucket_supported"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(predictor_module, "Q35_AUDIT_PATH", q35_path)
    monkeypatch.setattr(predictor_module, "Q15_SUPPORT_AUDIT_PATH", q15_path)

    blocker = predictor_module._infer_deployment_blocker(
        {
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q35",
        },
        {
            "decision_quality_structure_bucket_support_rows": 7,
            "decision_quality_exact_live_structure_bucket_support_rows": 7,
            "decision_quality_structure_bucket_support_mode": "exact_bucket_supported",
        },
    )
    guarded = predictor_module._apply_deployment_blocker_to_execution_profile(
        {
            "allowed_layers": 1,
            "allowed_layers_raw": 1,
            "execution_guardrail_applied": False,
            "execution_guardrail_reason": None,
        },
        blocker,
    )

    assert blocker is not None
    assert blocker["type"] == "bull_q35_no_deploy_governance"
    assert blocker["support_route_verdict"] == "exact_bucket_supported"
    assert blocker["unsafe_floor_cross_candidate"]["weights"] == {"feat_ear": 1.0}
    assert guarded["allowed_layers"] == 0
    assert guarded["deployment_blocker"] == "bull_q35_no_deploy_governance"
    assert "bull_q35_no_deploy_governance" in guarded["execution_guardrail_reason"]


def test_infer_deployment_blocker_flags_under_minimum_exact_live_structure_bucket():
    blocker = predictor_module._infer_deployment_blocker(
        {
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q15",
        },
        {
            "decision_quality_structure_bucket_support_rows": 2,
            "decision_quality_exact_live_structure_bucket_support_rows": 2,
            "decision_quality_structure_bucket_support_mode": "exact_bucket_supported",
            "decision_quality_structure_bucket_guardrail_reason": "chosen scope support is still too small",
        },
    )
    guarded = predictor_module._apply_deployment_blocker_to_execution_profile(
        {
            "allowed_layers": 0,
            "allowed_layers_raw": 0,
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
        },
        blocker,
    )

    assert blocker is not None
    assert blocker["type"] == "under_minimum_exact_live_structure_bucket"
    assert blocker["source"] == "decision_quality_contract"
    assert blocker["current_live_structure_bucket_rows"] == 2
    assert blocker["exact_live_structure_bucket_rows"] == 2
    assert guarded["deployment_blocker"] == "under_minimum_exact_live_structure_bucket"
    assert guarded["allowed_layers"] == 0
    assert guarded["allowed_layers_reason"] == (
        "unsupported_exact_live_structure_bucket_blocks_trade; under_minimum_exact_live_structure_bucket"
    )
    assert "under_minimum_exact_live_structure_bucket" in guarded["execution_guardrail_reason"]


def test_infer_deployment_blocker_uses_scope_diagnostics_fallback_for_exact_rows():
    blocker = predictor_module._infer_deployment_blocker(
        {
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q35",
        },
        {
            "decision_quality_calibration_scope": "regime_label",
            "decision_quality_scope_diagnostics": {
                "regime_label+regime_gate+entry_quality_label": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 4,
                },
                "regime_label": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 142,
                },
            },
        },
    )

    assert blocker is not None
    assert blocker["type"] == "under_minimum_exact_live_structure_bucket"
    assert blocker["current_live_structure_bucket_rows"] == 4
    assert blocker["exact_live_structure_bucket_rows"] == 4
    assert blocker["support_mode"] == "exact_bucket_present_but_below_minimum"


def test_live_decision_profile_applies_q35_discriminative_redesign_when_current_row_matches_audit(tmp_path, monkeypatch):
    q35_path = tmp_path / "q35_scaling_audit.json"
    q35_path.write_text(
        json.dumps(
            {
                "scope_applicability": {"status": "current_live_q35_lane_active"},
                "current_live": {
                    "timestamp": "2026-04-15 16:21:27.341550",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "raw_features": {
                        "feat_4h_bias50": 2.5104,
                        "feat_nose": 0.6998,
                        "feat_pulse": 0.0,
                        "feat_ear": 0.0014,
                    },
                },
                "base_stack_redesign_experiment": {
                    "verdict": "base_stack_redesign_discriminative_reweight_crosses_trade_floor",
                    "machine_read_answer": {
                        "entry_quality_ge_0_55": True,
                        "allowed_layers_gt_0": True,
                        "positive_discriminative_gap": True,
                    },
                    "best_discriminative_candidate": {
                        "weights": {
                            "feat_4h_bias50": 0.0,
                            "feat_nose": 0.0,
                            "feat_pulse": 0.0,
                            "feat_ear": 1.0,
                        },
                        "current_entry_quality_after": 0.8444,
                        "allowed_layers_after": 1,
                        "entry_quality_ge_trade_floor": True,
                        "allowed_layers_gt_0": True,
                        "positive_discriminative_gap": True,
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(predictor_module, "Q35_AUDIT_PATH", q35_path)

    features = {
        "timestamp": "2026-04-15 16:21:27.341550",
        "regime_label": "bull",
        "feat_4h_bias200": 5.7456,
        "feat_4h_bias50": 2.5104,
        "feat_nose": 0.6998,
        "feat_pulse": 0.0,
        "feat_ear": 0.0014,
        "feat_4h_bb_pct_b": 0.5041,
        "feat_4h_dist_bb_lower": 1.5948,
        "feat_4h_dist_swing_low": 4.892,
    }

    profile = predictor_module._build_live_decision_profile(features)

    assert profile["q35_discriminative_redesign_applied"] is True
    assert profile["q35_discriminative_redesign"]["weights"] == {
        "feat_4h_bias50": 0.0,
        "feat_nose": 0.0,
        "feat_pulse": 0.0,
        "feat_ear": 1.0,
    }
    assert profile["entry_quality"] == pytest.approx(0.8444)
    assert profile["allowed_layers"] == 2
    assert profile["allowed_layers_reason"] == "caution_gate_caps_two_layers"
    assert profile["entry_quality_components"]["q35_discriminative_redesign"]["applied"] is True
    assert [
        component["weight"] for component in profile["entry_quality_components"]["base_components"]
    ] == [0.0, 0.0, 0.0, 1.0]


def test_live_decision_profile_skips_q35_discriminative_redesign_when_audit_row_is_stale(tmp_path, monkeypatch):
    q35_path = tmp_path / "q35_scaling_audit.json"
    q35_path.write_text(
        json.dumps(
            {
                "scope_applicability": {"status": "current_live_q35_lane_active"},
                "current_live": {
                    "timestamp": "2026-04-15 12:00:00",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "raw_features": {
                        "feat_4h_bias50": 2.5104,
                        "feat_nose": 0.6998,
                        "feat_pulse": 0.0,
                        "feat_ear": 0.0014,
                    },
                },
                "base_stack_redesign_experiment": {
                    "verdict": "base_stack_redesign_discriminative_reweight_crosses_trade_floor",
                    "machine_read_answer": {
                        "entry_quality_ge_0_55": True,
                        "allowed_layers_gt_0": True,
                        "positive_discriminative_gap": True,
                    },
                    "best_discriminative_candidate": {
                        "weights": {
                            "feat_4h_bias50": 0.0,
                            "feat_nose": 0.0,
                            "feat_pulse": 0.0,
                            "feat_ear": 1.0,
                        },
                        "current_entry_quality_after": 0.8444,
                        "allowed_layers_after": 1,
                        "entry_quality_ge_trade_floor": True,
                        "allowed_layers_gt_0": True,
                        "positive_discriminative_gap": True,
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(predictor_module, "Q35_AUDIT_PATH", q35_path)

    features = {
        "timestamp": "2026-04-15 16:21:27.341550",
        "regime_label": "bull",
        "feat_4h_bias200": 1.8,
        "feat_4h_bias50": 0.9,
        "feat_nose": 0.22,
        "feat_pulse": 0.35,
        "feat_ear": 0.01,
        "feat_4h_bb_pct_b": 0.45,
        "feat_4h_dist_bb_lower": 5.0,
        "feat_4h_dist_swing_low": 6.0,
    }

    profile = predictor_module._build_live_decision_profile(features)

    assert profile["q35_discriminative_redesign_applied"] is False
    assert profile["q35_discriminative_redesign"] is None
    assert profile["allowed_layers"] == 0
    assert profile["allowed_layers_reason"] == "entry_quality_below_trade_floor"


def test_live_decision_profile_applies_q15_exact_supported_bias50_patch(tmp_path, monkeypatch):
    q15_path = tmp_path / "q15_support_audit.json"
    q15_path.write_text(
        json.dumps(
            {
                "scope_applicability": {
                    "status": "current_live_q15_lane_active",
                    "active_for_current_live_row": True,
                    "current_structure_bucket": "CAUTION|structure_quality_caution|q15",
                },
                "current_live": {
                    "feature_timestamp": "2026-04-16 23:00:23.100224",
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                    "raw_features": {
                        "feat_4h_bias50": 2.6461,
                        "feat_nose": 0.6107,
                        "feat_pulse": 0.4451,
                        "feat_ear": 0.0112,
                    },
                },
                "support_route": {
                    "verdict": "exact_bucket_supported",
                    "deployable": True,
                },
                "floor_cross_legality": {
                    "verdict": "legal_component_experiment_after_support_ready",
                    "legal_to_relax_runtime_gate": True,
                    "best_single_component": "feat_4h_bias50",
                    "best_single_component_required_score_delta": 0.754,
                },
                "component_experiment": {
                    "verdict": "exact_supported_component_experiment_ready",
                    "feature": "feat_4h_bias50",
                    "mode": "bias50_floor_counterfactual",
                    "machine_read_answer": {
                        "support_ready": True,
                        "entry_quality_ge_0_55": True,
                        "allowed_layers_gt_0": True,
                        "preserves_positive_discrimination": True,
                        "preserves_positive_discrimination_status": "verified_exact_lane_bucket_dominance",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(predictor_module, "Q15_SUPPORT_AUDIT_PATH", q15_path)

    features = {
        "timestamp": "2026-04-16 23:00:23.100224",
        "regime_label": "bull",
        "feat_4h_bias200": 2.2202,
        "feat_4h_bias50": 2.6461,
        "feat_nose": 0.6107,
        "feat_pulse": 0.4451,
        "feat_ear": 0.0112,
        "feat_4h_bb_pct_b": 0.5099,
        "feat_4h_dist_bb_lower": 1.6483,
        "feat_4h_dist_swing_low": 1.773,
    }

    profile = predictor_module._build_live_decision_profile(features)

    assert profile["q15_exact_supported_component_patch_applied"] is True
    assert profile["q15_exact_supported_component_patch"]["feature"] == "feat_4h_bias50"
    assert profile["q15_exact_supported_component_patch"]["required_score_delta"] == pytest.approx(0.754)
    assert profile["entry_quality"] == pytest.approx(0.5501)
    assert profile["entry_quality"] > 0.55
    assert profile["entry_quality_label"] == "C"
    assert profile["allowed_layers"] == 1
    assert profile["allowed_layers_reason"] == "entry_quality_C_single_layer"
    assert profile["entry_quality_components"]["base_components"][0]["normalized_score"] == pytest.approx(0.754)


def test_structure_bucket_support_guardrail_replays_q35_runtime_redesign_support(tmp_path, monkeypatch):
    q35_path = tmp_path / "q35_scaling_audit.json"
    q35_path.write_text(
        json.dumps(
            {
                "scope_applicability": {"status": "current_live_q35_lane_active"},
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "entry_quality_label": "B",
                    "q35_discriminative_redesign_applied": True,
                    "q35_discriminative_redesign": {
                        "weights": {
                            "feat_4h_bias50": 0.0,
                            "feat_nose": 0.0,
                            "feat_pulse": 1.0,
                            "feat_ear": 0.0,
                        }
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(predictor_module, "Q35_AUDIT_PATH", q35_path)

    decision_profile = {
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "structure_bucket": "CAUTION|structure_quality_caution|q35",
        "entry_quality_label": "B",
        "q35_discriminative_redesign_applied": True,
        "q35_discriminative_redesign": {
            "weights": {
                "feat_4h_bias50": 0.0,
                "feat_nose": 0.0,
                "feat_pulse": 1.0,
                "feat_ear": 0.0,
            }
        },
    }
    scope_diagnostics = {
        "regime_label+regime_gate+entry_quality_label": {
            "current_live_structure_bucket_rows": 0,
            "current_live_structure_bucket_share": None,
            "current_live_structure_bucket_metrics": None,
            "recent500_structure_bucket_counts": {},
        },
        "regime_gate": {
            "current_live_structure_bucket_rows": 187,
            "current_live_structure_bucket_share": 0.9791,
            "current_live_structure_bucket_metrics": {
                "win_rate": 0.9091,
                "avg_pnl": 0.0072,
                "avg_quality": 0.3974,
                "avg_drawdown_penalty": 0.1695,
                "avg_time_underwater": 0.6795,
            },
            "recent500_structure_bucket_counts": {
                "CAUTION|structure_quality_caution|q15": 4,
                "CAUTION|structure_quality_caution|q35": 187,
            },
        },
    }

    guarded = predictor_module._structure_bucket_support_guardrail(
        decision_profile,
        "regime_gate",
        scope_diagnostics,
        expected_win_rate=0.95,
        expected_pnl=0.01,
        expected_quality=0.5,
        expected_drawdown_penalty=0.15,
        expected_time_underwater=0.6,
    )

    assert guarded["applied"] is True
    assert guarded["support_mode"] == "exact_bucket_supported_via_q35_runtime_redesign"
    assert guarded["support_rows"] == 187
    assert guarded["exact_support_rows"] == 187
    assert guarded["supported_neighbor_buckets"] == ["CAUTION|structure_quality_caution|q15"]
    assert guarded["expected_win_rate"] == pytest.approx(0.9091)
    assert guarded["expected_pnl"] == pytest.approx(0.0072)
    assert guarded["expected_quality"] == pytest.approx(0.3974)
    assert guarded["expected_drawdown_penalty"] == pytest.approx(0.1695)
    assert guarded["expected_time_underwater"] == pytest.approx(0.6795)


def test_structure_bucket_support_guardrail_replays_q15_exact_supported_runtime(tmp_path, monkeypatch):
    q15_path = tmp_path / "q15_support_audit.json"
    q15_path.write_text(
        json.dumps(
            {
                "scope_applicability": {
                    "status": "current_live_q15_lane_active",
                    "active_for_current_live_row": True,
                    "current_structure_bucket": "CAUTION|structure_quality_caution|q15",
                },
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                    "current_live_structure_bucket_rows": 79,
                },
                "support_route": {
                    "verdict": "exact_bucket_supported",
                    "deployable": True,
                    "support_progress": {
                        "current_rows": 79,
                        "minimum_support_rows": 50,
                    },
                },
                "component_experiment": {
                    "verdict": "exact_supported_component_experiment_ready",
                    "feature": "feat_4h_bias50",
                    "machine_read_answer": {
                        "support_ready": True,
                        "entry_quality_ge_0_55": True,
                        "allowed_layers_gt_0": True,
                        "preserves_positive_discrimination": True,
                    },
                    "positive_discrimination_evidence": {
                        "current_bucket_metrics": {
                            "win_rate": 1.0,
                            "avg_pnl": 0.0058,
                            "avg_quality": 0.4966,
                            "avg_drawdown_penalty": 0.0674,
                            "avg_time_underwater": 0.1272,
                        }
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(predictor_module, "Q15_SUPPORT_AUDIT_PATH", q15_path)

    decision_profile = {
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "structure_bucket": "CAUTION|structure_quality_caution|q15",
        "entry_quality_label": "C",
        "q15_exact_supported_component_patch_applied": True,
    }
    scope_diagnostics = {
        "regime_label+regime_gate+entry_quality_label": {
            "current_live_structure_bucket_rows": 0,
            "current_live_structure_bucket_share": None,
            "current_live_structure_bucket_metrics": None,
            "recent500_structure_bucket_counts": {},
        },
        "regime_label": {
            "rows": 200,
            "current_live_structure_bucket_rows": 79,
            "current_live_structure_bucket_share": 0.395,
            "current_live_structure_bucket_metrics": {
                "win_rate": 1.0,
                "avg_pnl": 0.0058,
                "avg_quality": 0.4966,
                "avg_drawdown_penalty": 0.0674,
                "avg_time_underwater": 0.1272,
            },
            "recent500_structure_bucket_counts": {
                "CAUTION|structure_quality_caution|q15": 79,
                "CAUTION|structure_quality_caution|q35": 121,
            },
        },
    }

    guarded = predictor_module._structure_bucket_support_guardrail(
        decision_profile,
        "regime_label",
        scope_diagnostics,
        expected_win_rate=0.91,
        expected_pnl=0.0041,
        expected_quality=0.4146,
        expected_drawdown_penalty=0.1096,
        expected_time_underwater=0.2429,
    )

    assert guarded["applied"] is True
    assert guarded["support_mode"] == "exact_bucket_supported_via_q15_audit"
    assert guarded["support_rows"] == 79
    assert guarded["exact_support_rows"] == 79
    assert guarded["supported_neighbor_buckets"] == []
    assert guarded["expected_win_rate"] == pytest.approx(0.91)
    assert guarded["expected_pnl"] == pytest.approx(0.0041)
    assert guarded["expected_quality"] == pytest.approx(0.4146)
    assert guarded["expected_drawdown_penalty"] == pytest.approx(0.1096)
    assert guarded["expected_time_underwater"] == pytest.approx(0.2429)


def test_predictor_applies_legacy_isotonic_calibration_payload_keys():
    predictor = predictor_module.XGBoostPredictor({
        "clf": None,
        "feature_names": [],
        "calibration": {
            "kind": "isotonic",
            "x": [0.2, 0.8],
            "y": [0.1, 0.9],
        },
    })

    calibrated = predictor._apply_calibration(0.5)

    assert calibrated == pytest.approx(0.5)


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

    debug = predictor_module._compute_live_regime_gate_debug(2.2, "bull", bb_pct_b_value=0.82, dist_bb_lower_value=7.2, dist_swing_low_value=9.1)

    assert profile["entry_quality"] == expected_quality
    assert profile["regime_gate"] == expected_gate
    assert profile["regime_gate_reason"] == debug["final_reason"]
    assert profile["structure_quality"] == debug["structure_quality"]
    assert profile["structure_bucket"] == predictor_module._live_structure_bucket_from_debug(debug)
    assert profile["allowed_layers"] == expected_layers
    assert profile["allowed_layers_reason"] == "full_three_layers_allowed"
    assert profile["entry_quality_label"] == "A"
    assert profile["entry_quality_components"]["entry_quality"] == expected_quality
    assert profile["entry_quality_components"]["trade_floor"] == 0.55
    assert profile["entry_quality_components"]["trade_floor_gap"] == round(expected_quality - 0.55, 4)
    assert profile["entry_quality_components"]["base_components"][0]["feature"] == "feat_4h_bias50"
    assert profile["entry_quality_components"]["structure_components"][0]["feature"] == "feat_4h_bb_pct_b"
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


def test_live_decision_profile_blocks_overextended_allow_lane_even_when_bias200_is_positive():
    features = {
        "regime_label": "bull",
        "feat_4h_bias200": 3.4,
        "feat_4h_bias50": 4.1,
        "feat_nose": 0.45,
        "feat_pulse": 0.5,
        "feat_ear": 0.02,
        "feat_4h_bb_pct_b": 1.08,
        "feat_4h_dist_bb_lower": 10.8,
        "feat_4h_dist_swing_low": 11.6,
    }

    profile = predictor_module._build_live_decision_profile(features)
    debug = predictor_module._compute_live_regime_gate_debug(
        3.4,
        "bull",
        bb_pct_b_value=1.08,
        dist_bb_lower_value=10.8,
        dist_swing_low_value=11.6,
    )
    expected_gate = strategy_lab._compute_regime_gate(3.4, "bull", -10.0, 1.08, 10.8, 11.6)

    assert debug["final_reason"] == "structure_overextended_block"
    assert profile["regime_gate"] == "BLOCK"
    assert profile["allowed_layers"] == 0
    assert expected_gate == "BLOCK"


def test_live_decision_profile_downgrades_borderline_allow_q35_to_caution():
    features = {
        "regime_label": "bull",
        "feat_4h_bias200": 1.8,
        "feat_4h_bias50": 0.9,
        "feat_nose": 0.22,
        "feat_pulse": 0.35,
        "feat_ear": 0.01,
        "feat_4h_bb_pct_b": 0.45,
        "feat_4h_dist_bb_lower": 5.0,
        "feat_4h_dist_swing_low": 6.0,
    }

    profile = predictor_module._build_live_decision_profile(features)
    debug = predictor_module._compute_live_regime_gate_debug(
        1.8,
        "bull",
        bb_pct_b_value=0.45,
        dist_bb_lower_value=5.0,
        dist_swing_low_value=6.0,
    )
    expected_gate = strategy_lab._compute_regime_gate(1.8, "bull", -10.0, 0.45, 5.0, 6.0)

    assert round(debug["structure_quality"], 4) == 0.5573
    assert debug["final_reason"] == "structure_quality_caution"
    assert debug["final_gate"] == "CAUTION"
    assert profile["regime_gate"] == "CAUTION"
    assert profile["structure_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert profile["allowed_layers"] == 0
    assert profile["allowed_layers_reason"] == "entry_quality_below_trade_floor"
    assert profile["entry_quality_components"]["trade_floor_gap"] < 0
    assert profile["entry_quality_components"]["structure_quality"] == debug["structure_quality"]
    assert expected_gate == "CAUTION"


def test_piecewise_q35_bias50_calibration_ignores_non_q35_structure_bucket(tmp_path, monkeypatch):
    audit_path = tmp_path / "q35_scaling_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "overall_verdict": "broader_bull_cohort_recalibration_candidate",
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                },
                "segmented_calibration": {
                    "status": "segmented_calibration_required",
                    "recommended_mode": "piecewise_quantile_calibration",
                    "exact_lane": {
                        "bias50_distribution": {"p90": 3.1054},
                    },
                    "reference_cohort": {
                        "cohort": "bull_all",
                        "bias50_distribution": {"p90": 4.4607},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(q35_calibration_module, "DEFAULT_Q35_AUDIT_PATH", audit_path)
    q35_calibration_module._AUDIT_CACHE.update({"path": None, "mtime": None, "data": None})

    result = q35_calibration_module.compute_piecewise_bias50_score(
        3.7867,
        regime_label="bull",
        regime_gate="CAUTION",
        structure_bucket="CAUTION|structure_quality_caution|q15",
    )

    assert result["applied"] is False
    assert result["mode"] == "legacy_linear"
    assert result["score"] == 0.0



def test_piecewise_q35_bias50_calibration_uses_bull_reference_extension(tmp_path, monkeypatch):
    audit_path = tmp_path / "q35_scaling_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "overall_verdict": "broader_bull_cohort_recalibration_candidate",
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                },
                "segmented_calibration": {
                    "status": "segmented_calibration_required",
                    "recommended_mode": "piecewise_quantile_calibration",
                    "exact_lane": {
                        "bias50_distribution": {"p90": 3.1054},
                    },
                    "reference_cohort": {
                        "cohort": "bull_all",
                        "bias50_distribution": {"p90": 4.4607},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(q35_calibration_module, "DEFAULT_Q35_AUDIT_PATH", audit_path)
    q35_calibration_module._AUDIT_CACHE.update({"path": None, "mtime": None, "data": None})

    result = q35_calibration_module.compute_piecewise_bias50_score(
        3.7867,
        regime_label="bull",
        regime_gate="CAUTION",
        structure_bucket="CAUTION|structure_quality_caution|q35",
    )

    assert result["applied"] is True
    assert result["mode"] == "piecewise_quantile_calibration"
    assert result["reference_cohort"] == "bull_all"
    assert result["segment"] == "bull_reference_extension"
    assert result["legacy_score"] == 0.0
    assert 0.05 < result["score"] < 0.35
    assert result["score_delta_vs_legacy"] > 0



def test_piecewise_q35_bias50_calibration_supports_exact_lane_formula_review(tmp_path, monkeypatch):
    audit_path = tmp_path / "q35_scaling_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "overall_verdict": "bias50_formula_may_be_too_harsh",
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                },
                "segmented_calibration": {
                    "status": "formula_review_required",
                    "recommended_mode": "exact_lane_formula_review",
                    "exact_lane": {
                        "bias50_distribution": {"p75": 3.0207, "p90": 3.4106},
                    },
                    "reference_cohort": {
                        "cohort": "same_gate_same_quality",
                        "bias50_distribution": {"p90": 3.3233},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(q35_calibration_module, "DEFAULT_Q35_AUDIT_PATH", audit_path)
    q35_calibration_module._AUDIT_CACHE.update({"path": None, "mtime": None, "data": None})

    result = q35_calibration_module.compute_piecewise_bias50_score(
        3.2357,
        regime_label="bull",
        regime_gate="CAUTION",
        structure_bucket="CAUTION|structure_quality_caution|q35",
    )

    assert result["applied"] is True
    assert result["mode"] == "exact_lane_formula_review"
    assert result["segment"] == "exact_lane_elevated_within_p90"
    assert result["score"] > result["legacy_score"]
    assert result["score"] < 0.18
    assert result["reference_cohort"] == "same_gate_same_quality"



def test_piecewise_q35_bias50_calibration_supports_exact_lane_core_band_formula_review(tmp_path, monkeypatch):
    audit_path = tmp_path / "q35_scaling_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "overall_verdict": "bias50_formula_may_be_too_harsh",
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                },
                "segmented_calibration": {
                    "status": "formula_review_required",
                    "recommended_mode": "exact_lane_formula_review",
                    "exact_lane": {
                        "bias50_distribution": {"p25": 2.7164, "p75": 3.4106, "p90": 4.2204},
                    },
                    "reference_cohort": {
                        "cohort": "same_bucket",
                        "bias50_distribution": {"p90": 4.2197},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(q35_calibration_module, "DEFAULT_Q35_AUDIT_PATH", audit_path)
    q35_calibration_module._AUDIT_CACHE.update({"path": None, "mtime": None, "data": None})

    result = q35_calibration_module.compute_piecewise_bias50_score(
        2.7468,
        regime_label="bull",
        regime_gate="CAUTION",
        structure_bucket="CAUTION|structure_quality_caution|q35",
    )

    assert result["applied"] is True
    assert result["mode"] == "exact_lane_formula_review"
    assert result["segment"] == "exact_lane_supported_within_p75"
    assert result["score"] > result["legacy_score"]
    assert 0.18 <= result["score"] <= 0.24
    assert result["reference_cohort"] == "same_bucket"



def test_piecewise_q35_bias50_calibration_supports_exact_lane_core_normal_below_p25_formula_review(tmp_path, monkeypatch):
    audit_path = tmp_path / "q35_scaling_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "overall_verdict": "bias50_formula_may_be_too_harsh",
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                },
                "segmented_calibration": {
                    "status": "formula_review_required",
                    "recommended_mode": "exact_lane_formula_review",
                    "exact_lane": {
                        "bias50_distribution": {"min": 1.6545, "p25": 2.7464, "p75": 4.0464, "p90": 4.2197},
                    },
                    "reference_cohort": {
                        "cohort": "same_gate_same_quality",
                        "bias50_distribution": {"p90": 4.2124},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(q35_calibration_module, "DEFAULT_Q35_AUDIT_PATH", audit_path)
    q35_calibration_module._AUDIT_CACHE.update({"path": None, "mtime": None, "data": None})

    result = q35_calibration_module.compute_piecewise_bias50_score(
        2.6826,
        regime_label="bull",
        regime_gate="CAUTION",
        structure_bucket="CAUTION|structure_quality_caution|q35",
    )

    assert result["applied"] is True
    assert result["mode"] == "exact_lane_formula_review"
    assert result["segment"] == "exact_lane_core_band_below_p25"
    assert result["score"] > result["legacy_score"]
    assert 0.22 <= result["score"] <= 0.28
    assert result["reference_cohort"] == "same_gate_same_quality"



def test_live_decision_profile_exposes_bias50_piecewise_calibration_diagnostics(tmp_path, monkeypatch):
    audit_path = tmp_path / "q35_scaling_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "overall_verdict": "broader_bull_cohort_recalibration_candidate",
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                },
                "segmented_calibration": {
                    "status": "segmented_calibration_required",
                    "recommended_mode": "piecewise_quantile_calibration",
                    "exact_lane": {
                        "bias50_distribution": {"p90": 3.1054},
                    },
                    "reference_cohort": {
                        "cohort": "bull_all",
                        "bias50_distribution": {"p90": 4.4607},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(q35_calibration_module, "DEFAULT_Q35_AUDIT_PATH", audit_path)
    q35_calibration_module._AUDIT_CACHE.update({"path": None, "mtime": None, "data": None})

    features = {
        "regime_label": "bull",
        "feat_4h_bias200": 1.8,
        "feat_4h_bias50": 3.7867,
        "feat_nose": 0.5839,
        "feat_pulse": 0.6049,
        "feat_ear": -0.0084,
        "feat_4h_bb_pct_b": 0.6002,
        "feat_4h_dist_bb_lower": 1.8799,
        "feat_4h_dist_swing_low": 5.512,
    }

    profile = predictor_module._build_live_decision_profile(features)
    strategy_quality = strategy_lab._compute_entry_quality(
        3.7867,
        0.5839,
        0.6049,
        -0.0084,
        0.6002,
        1.8799,
        5.512,
        regime_label="bull",
        regime_gate="CAUTION",
        structure_bucket="CAUTION|structure_quality_caution|q35",
    )

    calibration = profile["entry_quality_components"]["bias50_calibration"]
    assert profile["regime_gate"] == "CAUTION"
    assert profile["structure_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert calibration["applied"] is True
    assert calibration["mode"] == "piecewise_quantile_calibration"
    assert calibration["segment"] == "bull_reference_extension"
    assert calibration["score"] > calibration["legacy_score"]
    assert profile["entry_quality"] == strategy_quality
    assert profile["allowed_layers"] == 0
    assert profile["allowed_layers_reason"] == "entry_quality_below_trade_floor"
    assert profile["entry_quality_components"]["trade_floor_gap"] < 0



def test_exact_live_lane_bucket_diagnostics_treats_single_bucket_as_no_split():
    rows = [
        {
            "structure_bucket": "CAUTION|structure_quality_caution|q35",
            "simulated_pyramid_win": 1.0,
            "simulated_pyramid_pnl": 0.02,
            "simulated_pyramid_quality": 0.70,
            "simulated_pyramid_drawdown_penalty": 0.03,
            "simulated_pyramid_time_underwater": 0.18,
        }
        for _ in range(12)
    ]

    diag = predictor_module._exact_live_lane_bucket_diagnostics(
        rows,
        "CAUTION|structure_quality_caution|q35",
    )

    assert diag["bucket_count"] == 1
    assert diag["verdict"] == "no_exact_lane_sub_bucket_split"
    assert diag["reason"] == "exact live lane 沒有可比較的非 current bucket 子 bucket。"
    assert diag["toxic_bucket"] is None


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
        "structure_quality_distribution": {
            "min": 0.2556,
            "p25": 0.2556,
            "p50": 0.2556,
            "p75": 0.2556,
            "max": 0.2556,
        },
        "structure_quality_gate_bands": {
            "block_lt_0.15": 0,
            "caution_0.15_to_0.35": 380,
            "allow_ge_0.35": 0,
        },
        "avg_bias200": 0.8,
        "target_counts": {"loss": 380},
        "pnl_sign_counts": {"positive": 0, "zero": 0, "negative": 380},
        "quality_sign_counts": {"positive": 0, "zero": 0, "negative": 380},
        "canonical_true_negative_rows": 380,
        "canonical_true_negative_share": 1.0,
        "missing_input_rows": 0,
        "missing_input_feature_counts": {},
    }
    assert spillover["exact_live_gate_path_summary"] == {
        "rows": 220,
        "final_gate_counts": {"ALLOW": 120, "BLOCK": 100},
        "final_reason_counts": {"base_allow": 120, "structure_quality_block": 100},
        "base_gate_counts": {"ALLOW": 220},
        "avg_structure_quality": 0.5365,
        "structure_quality_distribution": {
            "min": 0.1168,
            "p25": 0.1168,
            "p50": 0.8862,
            "p75": 0.8862,
            "max": 0.8862,
        },
        "structure_quality_gate_bands": {
            "block_lt_0.15": 100,
            "caution_0.15_to_0.35": 0,
            "allow_ge_0.35": 120,
        },
        "avg_bias200": 1.7182,
        "target_counts": {"win": 120, "loss": 100},
        "pnl_sign_counts": {"positive": 120, "zero": 0, "negative": 100},
        "quality_sign_counts": {"positive": 120, "zero": 0, "negative": 100},
        "canonical_true_negative_rows": 100,
        "canonical_true_negative_share": 0.4545,
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



def test_decision_quality_contract_surfaces_toxic_exact_allow_lane_when_broader_scope_is_selected():
    def _stamp(day: str, idx: int) -> str:
        hour, minute = divmod(idx, 60)
        return f"{day}T{hour:02d}:{minute:02d}:00"

    rows = []
    for i in range(24):
        rows.append(
            {
                "timestamp": _stamp("2026-04-13", i),
                "symbol": "BTCUSDT",
                "regime_label": "bull",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "feat_4h_bias200": 2.1,
                "feat_4h_dist_bb_lower": 6.8,
                "feat_4h_dist_swing_low": 7.2,
                "feat_4h_bb_pct_b": 1.16,
                "simulated_pyramid_win": 1.0 if i < 7 else 0.0,
                "simulated_pyramid_pnl": 0.0012 if i < 7 else -0.0022,
                "simulated_pyramid_quality": 0.02 if i < 7 else -0.0153,
                "simulated_pyramid_drawdown_penalty": 0.22 if i < 7 else 0.331,
                "simulated_pyramid_time_underwater": 0.39 if i < 7 else 0.707,
            }
        )
    for i in range(103):
        rows.append(
            {
                "timestamp": _stamp("2026-04-12", i),
                "symbol": "BTCUSDT",
                "regime_label": "neutral",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "feat_4h_bias200": 1.5,
                "feat_4h_dist_bb_lower": 4.6,
                "feat_4h_dist_swing_low": 5.9,
                "feat_4h_bb_pct_b": 0.81,
                "simulated_pyramid_win": 1.0 if i < 60 else 0.0,
                "simulated_pyramid_pnl": 0.006 if i < 60 else -0.001,
                "simulated_pyramid_quality": 0.18 if i < 60 else 0.04,
                "simulated_pyramid_drawdown_penalty": 0.14 if i < 60 else 0.22,
                "simulated_pyramid_time_underwater": 0.33 if i < 60 else 0.49,
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

    assert contract["decision_quality_calibration_scope"] == "regime_gate+entry_quality_label"
    assert contract["decision_quality_sample_size"] == 127
    assert contract["decision_quality_exact_live_lane_toxicity_applied"] is True
    assert contract["decision_quality_exact_live_lane_status"] == "toxic_allow_lane"
    assert "stays ALLOW but is toxic" in contract["decision_quality_exact_live_lane_reason"]
    assert contract["decision_quality_exact_live_lane_summary"] == {
        "scope": "regime_label+regime_gate+entry_quality_label",
        "rows": 24,
        "regime_label": "bull",
        "regime_gate": "ALLOW",
        "entry_quality_label": "D",
        "win_rate": 0.2917,
        "avg_pnl": -0.0012,
        "avg_quality": -0.005,
        "avg_drawdown_penalty": 0.2986,
        "avg_time_underwater": 0.6145,
        "allow_rows": 24,
        "allow_share": 1.0,
        "canonical_true_negative_share": 0.7083,
        "final_gate_counts": {"ALLOW": 24},
    }
    assert contract["expected_win_rate"] == 0.2917
    assert contract["expected_pyramid_pnl"] == -0.0012
    assert contract["expected_pyramid_quality"] == -0.005
    assert contract["expected_drawdown_penalty"] == 0.2986
    assert contract["expected_time_underwater"] == 0.6145



def test_decision_quality_contract_flags_unsupported_live_structure_bucket_when_scope_is_misaligned():
    rows = []
    for i in range(14):
        rows.append(
            {
                "timestamp": f"2026-04-13T00:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "bull",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "structure_bucket": "ALLOW|base_allow|q85",
                "feat_4h_dist_bb_lower": 10.2,
                "feat_4h_dist_swing_low": 13.0,
                "feat_4h_bb_pct_b": 1.22,
                "simulated_pyramid_win": 1.0 if i < 7 else 0.0,
                "simulated_pyramid_pnl": 0.008 if i < 7 else -0.004,
                "simulated_pyramid_quality": 0.28 if i < 7 else 0.02,
                "simulated_pyramid_drawdown_penalty": 0.19 if i < 7 else 0.22,
                "simulated_pyramid_time_underwater": 0.41 if i < 7 else 0.5,
            }
        )
    for i in range(66):
        rows.append(
            {
                "timestamp": f"2026-04-12T01:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "neutral",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "structure_bucket": "ALLOW|base_allow|q65",
                "feat_4h_dist_bb_lower": 8.1,
                "feat_4h_dist_swing_low": 10.8,
                "feat_4h_bb_pct_b": 1.04,
                "simulated_pyramid_win": 0.0,
                "simulated_pyramid_pnl": -0.002,
                "simulated_pyramid_quality": -0.04,
                "simulated_pyramid_drawdown_penalty": 0.31,
                "simulated_pyramid_time_underwater": 0.73,
            }
        )
    for i in range(35):
        rows.append(
            {
                "timestamp": f"2026-04-11T02:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "neutral",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "structure_bucket": "ALLOW|base_allow|q85",
                "feat_4h_dist_bb_lower": 9.9,
                "feat_4h_dist_swing_low": 11.9,
                "feat_4h_bb_pct_b": 1.19,
                "simulated_pyramid_win": 0.0,
                "simulated_pyramid_pnl": -0.01,
                "simulated_pyramid_quality": -0.22,
                "simulated_pyramid_drawdown_penalty": 0.29,
                "simulated_pyramid_time_underwater": 0.84,
            }
        )
    for i in range(2):
        rows.append(
            {
                "timestamp": f"2026-04-10T03:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "neutral",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "structure_bucket": "ALLOW|base_allow|q35",
                "feat_4h_dist_bb_lower": 6.8,
                "feat_4h_dist_swing_low": 7.1,
                "feat_4h_bb_pct_b": 0.64,
                "simulated_pyramid_win": 1.0 if i == 0 else 0.0,
                "simulated_pyramid_pnl": 0.001 if i == 0 else -0.0048,
                "simulated_pyramid_quality": 0.24 if i == 0 else -0.0408,
                "simulated_pyramid_drawdown_penalty": 0.2 if i == 0 else 0.24,
                "simulated_pyramid_time_underwater": 0.46 if i == 0 else 0.55,
            }
        )

    contract = predictor_module._summarize_decision_quality_contract(
        rows,
        {
            "regime_label": "bull",
            "regime_gate": "ALLOW",
            "entry_quality_label": "D",
            "structure_bucket": "ALLOW|base_allow|q35",
            "decision_profile_version": "phase16_baseline_v2",
        },
    )

    scope_diag = contract["decision_quality_scope_diagnostics"]["regime_gate+entry_quality_label"]
    assert contract["decision_quality_calibration_scope"] == "regime_gate+entry_quality_label"
    assert scope_diag["current_live_structure_bucket"] == "ALLOW|base_allow|q35"
    assert scope_diag["current_live_structure_bucket_rows"] == 2
    assert scope_diag["current_live_structure_bucket_share"] == 0.0171
    assert scope_diag["recent500_dominant_structure_bucket"] == {
        "structure_bucket": "ALLOW|base_allow|q65",
        "count": 66,
        "share": 0.5641,
    }
    assert contract["decision_quality_live_structure_bucket"] == "ALLOW|base_allow|q35"
    assert contract["decision_quality_structure_bucket_guardrail_applied"] is True
    assert contract["decision_quality_structure_bucket_support_mode"] == "exact_bucket_unsupported_block"
    assert contract["decision_quality_structure_bucket_support_rows"] == 2
    assert contract["decision_quality_structure_bucket_support_share"] == 0.0171
    assert contract["decision_quality_exact_live_structure_bucket_support_rows"] == 0
    assert contract["decision_quality_structure_bucket_supported_neighbor_buckets"] == ["ALLOW|base_allow|q85"]
    assert "zero support for live structure bucket ALLOW|base_allow|q35" in contract["decision_quality_structure_bucket_guardrail_reason"]
    assert "broader same-bucket scopes are informational only" in contract["decision_quality_structure_bucket_guardrail_reason"]



def test_decision_quality_contract_keeps_positive_same_regime_lane_and_clamps_to_bucket_support():
    rows = []
    for i in range(46):
        rows.append(
            {
                "timestamp": f"2026-04-14T00:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "neutral",
                "regime_gate": "ALLOW",
                "entry_quality_label": "C",
                "structure_bucket": "ALLOW|base_allow|q85",
                "feat_4h_dist_bb_lower": 8.6,
                "feat_4h_dist_swing_low": 9.1,
                "feat_4h_bb_pct_b": 1.07,
                "simulated_pyramid_win": 0.0,
                "simulated_pyramid_pnl": -0.0035,
                "simulated_pyramid_quality": -0.1906,
                "simulated_pyramid_drawdown_penalty": 0.3414,
                "simulated_pyramid_time_underwater": 0.78,
            }
        )
    for i in range(46):
        rows.append(
            {
                "timestamp": f"2026-04-13T01:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "bull",
                "regime_gate": "CAUTION",
                "entry_quality_label": "C",
                "structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
                "feat_4h_dist_bb_lower": 1.76,
                "feat_4h_dist_swing_low": 1.86,
                "feat_4h_bb_pct_b": 0.35,
                "simulated_pyramid_win": 1.0 if i < 39 else 0.0,
                "simulated_pyramid_pnl": 0.0015 if i < 39 else -0.001,
                "simulated_pyramid_quality": 0.3618 if i < 39 else 0.02,
                "simulated_pyramid_drawdown_penalty": 0.0709 if i < 39 else 0.11,
                "simulated_pyramid_time_underwater": 0.2434 if i < 39 else 0.31,
            }
        )
    for i in range(2):
        rows.append(
            {
                "timestamp": f"2026-04-12T02:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "neutral",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "structure_bucket": "ALLOW|base_allow|q35",
                "feat_4h_dist_bb_lower": 6.8,
                "feat_4h_dist_swing_low": 7.1,
                "feat_4h_bb_pct_b": 0.64,
                "simulated_pyramid_win": 1.0 if i == 0 else 0.0,
                "simulated_pyramid_pnl": 0.001 if i == 0 else -0.0048,
                "simulated_pyramid_quality": 0.24 if i == 0 else -0.0408,
                "simulated_pyramid_drawdown_penalty": 0.2 if i == 0 else 0.24,
                "simulated_pyramid_time_underwater": 0.46 if i == 0 else 0.55,
            }
        )

    contract = predictor_module._summarize_decision_quality_contract(
        rows,
        {
            "regime_label": "bull",
            "regime_gate": "ALLOW",
            "entry_quality_label": "C",
            "structure_bucket": "ALLOW|base_allow|q35",
            "decision_profile_version": "phase16_baseline_v2",
        },
        enforce_scope_guardrails=True,
    )

    assert contract["decision_quality_scope_guardrail_applied"] is True
    assert "scope regime_gate+entry_quality_label rejected" in contract["decision_quality_scope_guardrail_reason"]
    assert contract["decision_quality_calibration_scope"] == "regime_label+entry_quality_label"
    assert contract["decision_quality_sample_size"] == 46
    assert contract["decision_quality_structure_bucket_guardrail_applied"] is True
    assert contract["decision_quality_structure_bucket_support_mode"] == "exact_bucket_unsupported_block"
    assert contract["decision_quality_structure_bucket_support_rows"] == 0
    assert contract["decision_quality_exact_live_structure_bucket_support_rows"] == 0
    assert contract["decision_quality_structure_bucket_supported_neighbor_buckets"] == []
    assert "zero support for live structure bucket ALLOW|base_allow|q35" in contract["decision_quality_structure_bucket_guardrail_reason"]
    assert "broader same-bucket scopes are informational only" in contract["decision_quality_structure_bucket_guardrail_reason"]



def test_decision_quality_contract_rejects_broader_lane_when_recent_regime_mismatches_live_regime():
    rows = []
    for i in range(14):
        rows.append(
            {
                "timestamp": f"2026-04-14T00:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "bull",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "structure_bucket": "ALLOW|base_allow|q85",
                "feat_4h_dist_bb_lower": 10.2,
                "feat_4h_dist_swing_low": 12.9,
                "feat_4h_bb_pct_b": 1.23,
                "simulated_pyramid_win": 1.0 if i < 7 else 0.0,
                "simulated_pyramid_pnl": 0.0082 if i < 7 else -0.0048,
                "simulated_pyramid_quality": 0.2412 if i < 7 else -0.0408,
                "simulated_pyramid_drawdown_penalty": 0.2041,
                "simulated_pyramid_time_underwater": 0.4575,
            }
        )
    for i in range(101):
        rows.append(
            {
                "timestamp": f"2026-04-13T01:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "neutral",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "structure_bucket": "ALLOW|base_allow|q65",
                "feat_4h_dist_bb_lower": 6.69,
                "feat_4h_dist_swing_low": 7.04,
                "feat_4h_bb_pct_b": 1.23,
                "simulated_pyramid_win": 1.0 if i < 20 else 0.0,
                "simulated_pyramid_pnl": 0.001 if i < 20 else -0.0032,
                "simulated_pyramid_quality": 0.18 if i < 20 else -0.0989,
                "simulated_pyramid_drawdown_penalty": 0.3471,
                "simulated_pyramid_time_underwater": 0.7864,
            }
        )
    for i in range(147):
        rows.append(
            {
                "timestamp": f"2026-04-12T02:{i:02d}:00",
                "symbol": "BTCUSDT",
                "regime_label": "bull",
                "regime_gate": "BLOCK" if i < 116 else "CAUTION",
                "entry_quality_label": "D",
                "structure_bucket": "BLOCK|structure_quality_block|q00" if i < 116 else "CAUTION|structure_quality_caution|q15",
                "feat_4h_dist_bb_lower": 1.46 if i < 116 else 6.9,
                "feat_4h_dist_swing_low": 2.96 if i < 116 else 12.8,
                "feat_4h_bb_pct_b": 0.23 if i < 116 else 1.2,
                "simulated_pyramid_win": 1.0 if i >= 136 else 0.0,
                "simulated_pyramid_pnl": 0.008 if i >= 136 else -0.0111,
                "simulated_pyramid_quality": 0.24 if i >= 136 else -0.2098,
                "simulated_pyramid_drawdown_penalty": 0.2833,
                "simulated_pyramid_time_underwater": 0.804,
            }
        )

    contract = predictor_module._summarize_decision_quality_contract(
        rows,
        {
            "regime_label": "bull",
            "regime_gate": "ALLOW",
            "entry_quality_label": "D",
            "structure_bucket": "ALLOW|base_allow|q85",
            "decision_profile_version": "phase16_baseline_v2",
        },
        enforce_scope_guardrails=True,
    )

    assert contract["decision_quality_scope_guardrail_applied"] is True
    assert "scope regime_gate+entry_quality_label rejected via dominant recent regime mismatch" in contract["decision_quality_scope_guardrail_reason"]
    assert "scope entry_quality_label rejected via alerts=['label_imbalance']" in contract["decision_quality_scope_guardrail_reason"]
    assert contract["decision_quality_calibration_scope"] == "regime_label+entry_quality_label"
    assert contract["decision_quality_sample_size"] == 161


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
    assert guarded["allowed_layers_raw_reason"] == "caution_gate_caps_two_layers"
    assert guarded["allowed_layers"] == 1
    assert guarded["allowed_layers_reason"] == "decision_quality_label_C_caps_layers"
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


def test_apply_live_execution_guardrails_blocks_trade_for_unsupported_exact_live_structure_bucket():
    profile = {
        "regime_label": "bull",
        "regime_gate": "ALLOW",
        "entry_quality": 0.71,
        "entry_quality_label": "B",
        "allowed_layers": 2,
        "decision_profile_version": "phase16_baseline_v2",
    }
    contract = {
        **predictor_module._decision_quality_fallback(),
        "decision_quality_guardrail_applied": True,
        "decision_quality_structure_bucket_guardrail_applied": True,
        "decision_quality_structure_bucket_support_mode": "exact_bucket_unsupported_block",
        "decision_quality_structure_bucket_support_rows": 2,
        "decision_quality_exact_live_structure_bucket_support_rows": 0,
        "decision_quality_structure_bucket_supported_neighbor_buckets": ["ALLOW|base_allow|q15"],
        "decision_quality_structure_bucket_guardrail_reason": "exact live scope has zero support for live structure bucket ALLOW|base_allow|q35",
        "decision_quality_label": "B",
        "decision_quality_score": 0.58,
    }

    guarded = predictor_module._apply_live_execution_guardrails(profile, contract)

    assert guarded["allowed_layers_raw"] == 2
    assert guarded["allowed_layers"] == 0
    assert guarded["execution_guardrail_applied"] is True
    assert "unsupported_exact_live_structure_bucket_blocks_trade" in guarded["execution_guardrail_reason"]



def test_apply_live_execution_guardrails_reports_exact_live_lane_toxicity():
    profile = {
        "regime_label": "bull",
        "regime_gate": "ALLOW",
        "entry_quality": 0.41,
        "entry_quality_label": "D",
        "allowed_layers": 2,
        "decision_profile_version": "phase16_baseline_v2",
    }
    contract = {
        **predictor_module._decision_quality_fallback(),
        "decision_quality_guardrail_applied": True,
        "decision_quality_exact_live_lane_toxicity_applied": True,
        "decision_quality_exact_live_lane_status": "toxic_allow_lane",
        "decision_quality_label": "D",
        "decision_quality_score": 0.24,
    }

    guarded = predictor_module._apply_live_execution_guardrails(profile, contract)

    assert guarded["allowed_layers_raw"] == 2
    assert guarded["allowed_layers"] == 0
    assert guarded["execution_guardrail_applied"] is True
    assert "decision_quality_below_trade_floor" in guarded["execution_guardrail_reason"]
    assert "exact_live_lane_toxic_allow_lane_blocks_trade" in guarded["execution_guardrail_reason"]



def test_decision_quality_contract_surfaces_exact_lane_toxic_sub_bucket_without_penalizing_current_q35_bucket():
    rows = [
        {
            "timestamp": f"2026-04-14T00:{i:02d}:00",
            "symbol": "BTCUSDT",
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "structure_bucket": "CAUTION|structure_quality_caution|q35",
            "simulated_pyramid_win": 1.0,
            "simulated_pyramid_pnl": 0.022,
            "simulated_pyramid_quality": 0.71,
            "simulated_pyramid_drawdown_penalty": 0.07,
            "simulated_pyramid_time_underwater": 0.09,
        }
        for i in range(13)
    ]
    rows.extend(
        {
            "timestamp": f"2026-04-13T01:{i:02d}:00",
            "symbol": "BTCUSDT",
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "structure_bucket": "CAUTION|structure_quality_caution|q15",
            "simulated_pyramid_win": 0.0,
            "simulated_pyramid_pnl": -0.02,
            "simulated_pyramid_quality": -0.3,
            "simulated_pyramid_drawdown_penalty": 0.31,
            "simulated_pyramid_time_underwater": 0.61,
        }
        for i in range(4)
    )
    rows.extend(
        {
            "timestamp": f"2026-04-12T02:{i:02d}:00",
            "symbol": "BTCUSDT",
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
            "simulated_pyramid_win": 1.0 if i < 4 else 0.0,
            "simulated_pyramid_pnl": 0.01 if i < 4 else -0.005,
            "simulated_pyramid_quality": 0.22 if i < 4 else 0.05,
            "simulated_pyramid_drawdown_penalty": 0.11,
            "simulated_pyramid_time_underwater": 0.22,
        }
        for i in range(7)
    )
    rows.extend(
        {
            "timestamp": f"2026-04-11T03:{i:02d}:00",
            "symbol": "BTCUSDT",
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "structure_bucket": "CAUTION|base_caution_regime_or_bias|q85",
            "simulated_pyramid_win": 1.0 if i < 5 else 0.0,
            "simulated_pyramid_pnl": 0.012 if i < 5 else -0.003,
            "simulated_pyramid_quality": 0.33 if i < 5 else 0.08,
            "simulated_pyramid_drawdown_penalty": 0.12,
            "simulated_pyramid_time_underwater": 0.19,
        }
        for i in range(6)
    )

    contract = predictor_module._summarize_decision_quality_contract(
        rows,
        {
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "structure_bucket": "CAUTION|structure_quality_caution|q35",
            "decision_profile_version": "phase16_baseline_v2",
        },
    )

    assert contract["decision_quality_calibration_scope"] == "regime_label+regime_gate+entry_quality_label"
    assert contract["decision_quality_exact_live_lane_bucket_verdict"] == "toxic_sub_bucket_identified"
    assert contract["decision_quality_exact_live_lane_toxicity_applied"] is False
    assert contract["decision_quality_exact_live_lane_toxic_bucket"]["bucket"] == "CAUTION|structure_quality_caution|q15"
    assert contract["decision_quality_exact_live_lane_toxic_bucket"]["win_rate"] == 0.0
    assert contract["decision_quality_exact_live_lane_toxic_bucket"]["vs_current_bucket"]["win_rate_delta"] == -1.0
    assert contract["decision_quality_exact_live_lane_bucket_diagnostics"]["buckets"]["CAUTION|structure_quality_caution|q35"]["rows"] == 13



def test_decision_quality_contract_blocks_when_current_bucket_is_exact_lane_toxic_sub_bucket():
    rows = [
        {
            "timestamp": f"2026-04-14T00:{i:02d}:00",
            "symbol": "BTCUSDT",
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "structure_bucket": "CAUTION|structure_quality_caution|q15",
            "simulated_pyramid_win": 0.0,
            "simulated_pyramid_pnl": -0.02,
            "simulated_pyramid_quality": -0.3,
            "simulated_pyramid_drawdown_penalty": 0.31,
            "simulated_pyramid_time_underwater": 0.61,
        }
        for i in range(4)
    ]
    rows.extend(
        {
            "timestamp": f"2026-04-13T01:{i:02d}:00",
            "symbol": "BTCUSDT",
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "structure_bucket": "CAUTION|structure_quality_caution|q35",
            "simulated_pyramid_win": 1.0,
            "simulated_pyramid_pnl": 0.022,
            "simulated_pyramid_quality": 0.71,
            "simulated_pyramid_drawdown_penalty": 0.07,
            "simulated_pyramid_time_underwater": 0.09,
        }
        for i in range(13)
    )
    rows.extend(
        {
            "timestamp": f"2026-04-12T02:{i:02d}:00",
            "symbol": "BTCUSDT",
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "structure_bucket": "CAUTION|base_caution_regime_or_bias|q85",
            "simulated_pyramid_win": 1.0 if i < 5 else 0.0,
            "simulated_pyramid_pnl": 0.012 if i < 5 else -0.003,
            "simulated_pyramid_quality": 0.33 if i < 5 else 0.08,
            "simulated_pyramid_drawdown_penalty": 0.12,
            "simulated_pyramid_time_underwater": 0.19,
        }
        for i in range(6)
    )
    rows.extend(
        {
            "timestamp": f"2026-04-11T03:{i:02d}:00",
            "symbol": "BTCUSDT",
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
            "simulated_pyramid_win": 1.0 if i < 4 else 0.0,
            "simulated_pyramid_pnl": 0.01 if i < 4 else -0.005,
            "simulated_pyramid_quality": 0.22 if i < 4 else 0.05,
            "simulated_pyramid_drawdown_penalty": 0.11,
            "simulated_pyramid_time_underwater": 0.22,
        }
        for i in range(7)
    )

    contract = predictor_module._summarize_decision_quality_contract(
        rows,
        {
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality_label": "D",
            "structure_bucket": "CAUTION|structure_quality_caution|q15",
            "decision_profile_version": "phase16_baseline_v2",
        },
    )

    assert contract["decision_quality_exact_live_lane_toxicity_applied"] is True
    assert contract["decision_quality_exact_live_lane_status"] == "toxic_sub_bucket_current_bucket"
    assert contract["decision_quality_exact_live_lane_toxic_bucket"]["bucket"] == "CAUTION|structure_quality_caution|q15"
    assert "toxic sub-bucket" in contract["decision_quality_exact_live_lane_reason"]

    guarded = predictor_module._apply_live_execution_guardrails(
        {
            "regime_label": "bull",
            "regime_gate": "CAUTION",
            "entry_quality": 0.42,
            "entry_quality_label": "D",
            "allowed_layers": 2,
            "decision_profile_version": "phase16_baseline_v2",
        },
        contract,
    )

    assert guarded["allowed_layers_raw"] == 2
    assert guarded["allowed_layers"] == 0
    assert "exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade" in guarded["execution_guardrail_reason"]



def test_structure_bucket_support_guardrail_blocks_unsupported_exact_bucket_without_broader_fallback():
    decision_profile = {
        "structure_bucket": "CAUTION|structure_quality_caution|q35",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality_label": "D",
    }
    scope_diagnostics = {
        "regime_label": {
            "current_live_structure_bucket_rows": 2,
            "current_live_structure_bucket_share": 0.01,
            "current_live_structure_bucket_metrics": {
                "win_rate": 0.5,
                "avg_pnl": -0.001,
                "avg_quality": 0.1,
                "avg_drawdown_penalty": 0.2,
                "avg_time_underwater": 0.4,
            },
            "recent500_dominant_structure_bucket": {
                "structure_bucket": "CAUTION|base_caution_regime_or_bias|q15"
            },
        },
        "regime_label+regime_gate+entry_quality_label": {
            "current_live_structure_bucket_rows": 0,
            "current_live_structure_bucket_share": 0.0,
            "recent500_structure_bucket_counts": {
                "CAUTION|structure_quality_caution|q15": 4,
                "CAUTION|base_caution_regime_or_bias|q15": 7,
            },
        },
        "regime_gate+entry_quality_label": {
            "current_live_structure_bucket_rows": 9,
            "current_live_structure_bucket_share": 0.2,
            "current_live_structure_bucket_metrics": {
                "win_rate": 0.9,
                "avg_pnl": 0.03,
                "avg_quality": 0.7,
                "avg_drawdown_penalty": 0.05,
                "avg_time_underwater": 0.1,
            },
        },
    }

    guarded = predictor_module._structure_bucket_support_guardrail(
        decision_profile,
        chosen_scope="regime_label",
        scope_diagnostics=scope_diagnostics,
        expected_win_rate=0.8,
        expected_pnl=0.02,
        expected_quality=0.5,
        expected_drawdown_penalty=0.1,
        expected_time_underwater=0.2,
    )

    assert guarded["applied"] is True
    assert guarded["support_mode"] == "exact_bucket_unsupported_block"
    assert guarded["exact_support_rows"] == 0
    assert guarded["support_rows"] == 2
    assert guarded["supported_neighbor_buckets"] == [
        "CAUTION|structure_quality_caution|q15",
        "CAUTION|base_caution_regime_or_bias|q15",
    ]
    assert guarded["expected_win_rate"] == 0.8
    assert "broader same-bucket scopes are informational only" in guarded["reason"]


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
    monkeypatch.setattr(api_module, "_load_q15_support_audit_summary", lambda _bucket=None: None)

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


def test_get_confidence_prediction_enriches_q15_support_blocker_from_audit(monkeypatch):
    import asyncio
    import config as config_module
    from database import models as models_module
    from model import predictor as predictor_module

    class _FakeDb:
        def close(self):
            return None

    monkeypatch.setattr(config_module, "load_config", lambda: {"database": {"url": "sqlite:///fake.db"}})
    monkeypatch.setattr(models_module, "init_db", lambda _url: _FakeDb())
    monkeypatch.setattr(predictor_module, "load_predictor", lambda: ("global-predictor", {"bull": object()}))
    monkeypatch.setattr(
        predictor_module,
        "predict",
        lambda _session, _predictor, _regime_models: {
            "confidence": 0.24,
            "signal": "HOLD",
            "confidence_level": "LOW",
            "should_trade": False,
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q15",
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "deployment_blocker_reason": "support not enough",
            "deployment_blocker_details": {"current_live_structure_bucket_rows": 4},
            "decision_profile_version": "phase16_baseline_v2",
        },
    )
    monkeypatch.setattr(
        api_module,
        "_load_q15_support_audit_summary",
        lambda _bucket=None: {
            "support_route_verdict": "exact_bucket_present_but_below_minimum",
            "support_route_deployable": False,
            "support_governance_route": "exact_live_bucket_present_but_below_minimum",
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 46,
            "support_progress": {
                "status": "accumulating",
                "current_rows": 4,
                "minimum_support_rows": 50,
                "gap_to_minimum": 46,
                "delta_vs_previous": 4,
            },
            "floor_cross_legality": {
                "verdict": "math_cross_possible_but_illegal_without_exact_support",
                "legal_to_relax_runtime_gate": False,
                "remaining_gap_to_floor": 0.233,
                "best_single_component": "feat_4h_bias50",
                "best_single_component_required_score_delta": 0.7767,
            },
            "component_experiment": {"verdict": "reference_only_until_exact_support_ready"},
        },
    )

    result = asyncio.run(api_module.get_confidence_prediction())

    assert result["support_route_verdict"] == "exact_bucket_present_but_below_minimum"
    assert result["minimum_support_rows"] == 50
    assert result["support_progress"]["status"] == "accumulating"
    assert result["deployment_blocker_details"]["support_progress"]["gap_to_minimum"] == 46
    assert result["floor_cross_verdict"] == "math_cross_possible_but_illegal_without_exact_support"
    assert result["best_single_component"] == "feat_4h_bias50"
    assert result["component_experiment_verdict"] == "reference_only_until_exact_support_ready"


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
