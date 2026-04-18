import json

from scripts import hb_predict_probe


class DummySession:
    def close(self):
        return None


def test_hb_predict_probe_emits_q35_runtime_and_structure_fields(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    q15_audit_path.write_text(
        json.dumps(
            {
                "scope_applicability": {
                    "active_for_current_live_row": True,
                    "current_structure_bucket": "CAUTION|structure_quality_caution|q15",
                },
                "support_route": {
                    "verdict": "exact_bucket_present_but_below_minimum",
                    "deployable": False,
                    "support_progress": {
                        "status": "accumulating",
                        "current_rows": 1,
                        "minimum_support_rows": 50,
                        "gap_to_minimum": 49,
                    },
                },
                "floor_cross_legality": {
                    "verdict": "math_cross_possible_but_illegal_without_exact_support",
                    "best_single_component": "feat_4h_bias50",
                },
                "component_experiment": {"verdict": "reference_only_until_exact_support_ready"},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)

    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(
        hb_predict_probe,
        "load_latest_features",
        lambda _session: {
            "timestamp": "2026-04-16 03:44:54.846308",
            "regime_label": "bull",
            "feat_4h_bias50": 3.2779,
        },
    )
    monkeypatch.setattr(
        hb_predict_probe,
        "predict",
        lambda _session, _predictor, _regime_models: {
            "target_col": "simulated_pyramid_win",
            "used_model": "regime_bull_ensemble",
            "model_type": "RegimeAwarePredictor",
            "signal": "HOLD",
            "confidence": 0.537135,
            "regime_label": "bull",
            "model_route_regime": "bull",
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q15",
            "entry_quality": 0.5621,
            "entry_quality_label": "C",
            "entry_quality_components": {
                "trade_floor": 0.55,
                "q35_discriminative_redesign": {
                    "applied": True,
                    "weights": {"feat_pulse": 0.9, "feat_ear": 0.1},
                },
            },
            "q35_discriminative_redesign_applied": True,
            "q35_discriminative_redesign": {
                "applied": True,
                "weights": {"feat_pulse": 0.9, "feat_ear": 0.1},
            },
            "allowed_layers_raw": 1,
            "allowed_layers_raw_reason": "entry_quality_C_single_layer",
            "allowed_layers": 0,
            "allowed_layers_reason": "under_minimum_exact_live_structure_bucket",
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "under_minimum_exact_live_structure_bucket",
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "deployment_blocker_reason": "support not enough",
            "deployment_blocker_source": "decision_quality_contract",
            "deployment_blocker_details": {"current_live_structure_bucket_rows": 1},
            "decision_quality_horizon_minutes": 1440,
            "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "decision_quality_exact_live_structure_bucket_support_rows": 1,
        },
    )

    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["structure_bucket"] == "CAUTION|structure_quality_caution|q15"
    assert payload["current_live_structure_bucket"] == "CAUTION|structure_quality_caution|q15"
    assert payload["current_live_structure_bucket_rows"] == 1
    assert payload["q35_discriminative_redesign_applied"] is True
    assert payload["q35_discriminative_redesign"]["applied"] is True
    assert payload["allowed_layers_raw"] == 1
    assert payload["allowed_layers_raw_reason"] == "entry_quality_C_single_layer"
    assert payload["allowed_layers_reason"] == "under_minimum_exact_live_structure_bucket"
    assert payload["deployment_blocker"] == "under_minimum_exact_live_structure_bucket"
    assert payload["support_route_verdict"] == "exact_bucket_present_but_below_minimum"
    assert payload["support_progress"]["status"] == "accumulating"
    assert payload["best_single_component"] == "feat_4h_bias50"
    assert payload["component_experiment_verdict"] == "reference_only_until_exact_support_ready"
    assert payload["runtime_closure_state"] == "patch_active_but_execution_blocked"
    assert "q35 discriminative redesign 已啟用並把 entry_quality 拉到 0.5621" in payload["runtime_closure_summary"]
    assert json.loads(out_path.read_text()) == payload


def test_hb_predict_probe_falls_back_to_generic_support_progress_for_q35_blocker(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    q15_audit_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(
        hb_predict_probe,
        "load_latest_features",
        lambda _session: {
            "timestamp": "2026-04-18 10:00:00",
            "regime_label": "bull",
            "feat_4h_bias50": 5.0,
        },
    )
    monkeypatch.setattr(
        hb_predict_probe,
        "predict",
        lambda _session, _predictor, _regime_models: {
            "target_col": "simulated_pyramid_win",
            "used_model": "regime_bull_ensemble",
            "model_type": "RegimeAwarePredictor",
            "signal": "HOLD",
            "confidence": 0.59051,
            "regime_label": "bull",
            "model_route_regime": "bull",
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q35",
            "entry_quality": 0.5508,
            "entry_quality_label": "C",
            "entry_quality_components": {"trade_floor": 0.55},
            "allowed_layers_raw": 1,
            "allowed_layers_raw_reason": "entry_quality_C_single_layer",
            "allowed_layers": 0,
            "allowed_layers_reason": "decision_quality_below_trade_floor; under_minimum_exact_live_structure_bucket",
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "decision_quality_below_trade_floor; under_minimum_exact_live_structure_bucket",
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "deployment_blocker_reason": "support not enough",
            "deployment_blocker_source": "decision_quality_contract",
            "deployment_blocker_details": {
                "structure_bucket": "CAUTION|structure_quality_caution|q35",
                "support_mode": "exact_bucket_present_but_below_minimum",
                "current_live_structure_bucket_rows": 9,
                "exact_live_structure_bucket_rows": 9,
                "minimum_support_rows": 50,
                "current_live_structure_bucket_gap_to_minimum": 41,
                "support_progress": {
                    "status": "accumulating",
                    "current_rows": 9,
                    "minimum_support_rows": 50,
                    "gap_to_minimum": 41,
                },
            },
            "decision_quality_horizon_minutes": 1440,
            "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "decision_quality_exact_live_structure_bucket_support_rows": 9,
        },
    )

    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["current_live_structure_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert payload["current_live_structure_bucket_rows"] == 9
    assert payload["support_route_verdict"] == "exact_bucket_present_but_below_minimum"
    assert payload["support_progress"]["status"] == "accumulating"
    assert payload["minimum_support_rows"] == 50
    assert payload["current_live_structure_bucket_gap_to_minimum"] == 41
    assert payload["floor_cross_verdict"] is None
    assert payload["component_experiment_verdict"] is None


def test_hb_predict_probe_uses_result_support_route_when_q35_override_is_exact_supported(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    q15_audit_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(
        hb_predict_probe,
        "load_latest_features",
        lambda _session: {
            "timestamp": "2026-04-18 12:00:00",
            "regime_label": "bull",
            "feat_4h_bias50": 4.4,
        },
    )
    monkeypatch.setattr(
        hb_predict_probe,
        "predict",
        lambda _session, _predictor, _regime_models: {
            "target_col": "simulated_pyramid_win",
            "used_model": "regime_bull_ensemble",
            "model_type": "RegimeAwarePredictor",
            "signal": "BUY",
            "confidence": 0.71,
            "regime_label": "bull",
            "model_route_regime": "bull",
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q35",
            "entry_quality": 0.7127,
            "entry_quality_label": "B",
            "entry_quality_components": {"trade_floor": 0.55},
            "allowed_layers_raw": 2,
            "allowed_layers_raw_reason": "caution_gate_caps_two_layers",
            "allowed_layers": 0,
            "allowed_layers_reason": "decision_quality_below_trade_floor",
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "decision_quality_below_trade_floor",
            "deployment_blocker": None,
            "deployment_blocker_reason": None,
            "deployment_blocker_source": None,
            "deployment_blocker_details": None,
            "decision_quality_horizon_minutes": 1440,
            "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "decision_quality_structure_bucket_support_mode": "exact_bucket_supported_via_q35_runtime_redesign",
            "decision_quality_exact_live_structure_bucket_support_rows": 100,
            "support_route_verdict": "exact_bucket_supported",
            "support_route_deployable": True,
            "support_progress": {
                "status": "exact_supported",
                "current_rows": 100,
                "minimum_support_rows": 50,
                "gap_to_minimum": 0,
            },
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 0,
        },
    )

    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["deployment_blocker"] is None
    assert payload["current_live_structure_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert payload["current_live_structure_bucket_rows"] == 100
    assert payload["support_route_verdict"] == "exact_bucket_supported"
    assert payload["support_route_deployable"] is True
    assert payload["support_progress"]["status"] == "exact_supported"
    assert payload["minimum_support_rows"] == 50
    assert payload["current_live_structure_bucket_gap_to_minimum"] == 0
    assert json.loads(out_path.read_text()) == payload


def test_hb_predict_probe_emits_explicit_no_deploy_governance_for_exact_supported_q15(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    q15_audit_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-18T09:02:43.662805+00:00",
                "scope_applicability": {
                    "active_for_current_live_row": True,
                    "current_structure_bucket": "CAUTION|structure_quality_caution|q15",
                },
                "support_route": {
                    "verdict": "exact_bucket_supported",
                    "deployable": True,
                    "support_progress": {
                        "status": "exact_supported",
                        "current_rows": 96,
                        "minimum_support_rows": 50,
                        "gap_to_minimum": 0,
                    },
                },
                "floor_cross_legality": {
                    "verdict": "legal_component_experiment_after_support_ready",
                    "legal_to_relax_runtime_gate": True,
                    "remaining_gap_to_floor": 0.1319,
                    "best_single_component": "feat_4h_bias50",
                    "best_single_component_required_score_delta": 0.4397,
                },
                "component_experiment": {
                    "verdict": "exact_supported_component_experiment_ready",
                    "feature": "feat_4h_bias50",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(
        hb_predict_probe,
        "load_latest_features",
        lambda _session: {
            "timestamp": "2026-04-18T09:02:43.662805+00:00",
            "regime_label": "bull",
            "feat_4h_bias50": 3.8273,
        },
    )
    monkeypatch.setattr(
        hb_predict_probe,
        "predict",
        lambda _session, _predictor, regime_models=None: {
            "target_col": "simulated_pyramid_win",
            "used_model": "regime_bull_ensemble",
            "model_type": "RegimeAwarePredictor",
            "signal": "BUY",
            "confidence": 0.83224,
            "regime_label": "bull",
            "model_route_regime": "bull",
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q15",
            "entry_quality": 0.4181,
            "entry_quality_label": "D",
            "entry_quality_components": {"trade_floor": 0.55},
            "allowed_layers_raw": 0,
            "allowed_layers_raw_reason": "entry_quality_below_trade_floor",
            "allowed_layers": 0,
            "allowed_layers_reason": "decision_quality_below_trade_floor",
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "decision_quality_below_trade_floor",
            "deployment_blocker": "decision_quality_below_trade_floor",
            "deployment_blocker_reason": "support 已 closure，但 live baseline 仍低於 trade floor",
            "deployment_blocker_source": "decision_quality_contract+q15_support_audit",
            "deployment_blocker_details": {
                "support_route_verdict": "exact_bucket_supported",
                "current_live_structure_bucket_rows": 96,
                "minimum_support_rows": 50,
            },
            "decision_quality_horizon_minutes": 1440,
            "support_route_verdict": "exact_bucket_supported",
            "support_route_deployable": True,
            "support_progress": {
                "status": "exact_supported",
                "current_rows": 96,
                "minimum_support_rows": 50,
                "gap_to_minimum": 0,
            },
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 0,
        },
    )

    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["deployment_blocker"] == "decision_quality_below_trade_floor"
    assert payload["runtime_closure_state"] == "support_closed_but_trade_floor_blocked"
    assert payload["support_route_verdict"] == "exact_bucket_supported"
    assert payload["component_experiment_verdict"] == "exact_supported_component_experiment_ready"
    assert "已完成 exact support closure" in payload["runtime_closure_summary"]
    assert "不可把 support closure 誤讀成 deployment closure" in payload["runtime_closure_summary"]
    assert json.loads(out_path.read_text()) == payload


def test_hb_predict_probe_backfills_support_route_into_runtime_closure_from_q15_audit(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    q15_audit_path.write_text(
        json.dumps(
            {
                "scope_applicability": {
                    "active_for_current_live_row": True,
                    "current_structure_bucket": "CAUTION|structure_quality_caution|q15",
                },
                "support_route": {
                    "verdict": "exact_bucket_supported",
                    "deployable": True,
                    "support_progress": {
                        "status": "exact_supported",
                        "current_rows": 96,
                        "minimum_support_rows": 50,
                        "gap_to_minimum": 0,
                    },
                },
                "floor_cross_legality": {
                    "verdict": "legal_component_experiment_after_support_ready",
                    "best_single_component": "feat_4h_bias50",
                    "best_single_component_required_score_delta": 0.705,
                },
                "component_experiment": {"verdict": "exact_supported_component_experiment_ready"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(
        hb_predict_probe,
        "load_latest_features",
        lambda _session: {"timestamp": "2026-04-18T12:08:40.638156", "regime_label": "bull", "feat_4h_bias50": 3.097},
    )
    monkeypatch.setattr(
        hb_predict_probe,
        "predict",
        lambda *_args, **_kwargs: {
            "target_col": "simulated_pyramid_win",
            "used_model": "regime_bull_ensemble",
            "model_type": "RegimeAwarePredictor",
            "signal": "BUY",
            "confidence": 0.764611,
            "regime_label": "bull",
            "model_route_regime": "bull",
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q15",
            "entry_quality": 0.3385,
            "entry_quality_label": "D",
            "entry_quality_components": {"trade_floor": 0.55},
            "allowed_layers_raw": 0,
            "allowed_layers_raw_reason": "entry_quality_below_trade_floor",
            "allowed_layers": 0,
            "allowed_layers_reason": "decision_quality_below_trade_floor",
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "decision_quality_below_trade_floor",
            "deployment_blocker": "decision_quality_below_trade_floor",
            "deployment_blocker_reason": "support 已 closure，但 live baseline 仍低於 trade floor",
            "deployment_blocker_source": "decision_quality_contract+q15_support_audit",
            "deployment_blocker_details": {},
            "decision_quality_horizon_minutes": 1440,
            "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "decision_quality_exact_live_structure_bucket_support_rows": 96,
        },
    )

    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["support_route_verdict"] == "exact_bucket_supported"
    assert payload["runtime_closure_state"] == "support_closed_but_trade_floor_blocked"
    assert "已完成 exact support closure" in payload["runtime_closure_summary"]
    assert payload["support_progress"]["current_rows"] == 96



def test_hb_predict_probe_refreshes_q15_audit_before_emitting(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    stale_payload = {
        "generated_at": "2026-04-16T23:00:23.100224+00:00",
        "scope_applicability": {
            "active_for_current_live_row": True,
            "current_structure_bucket": "CAUTION|structure_quality_caution|q15",
        },
        "support_route": {
            "verdict": "exact_bucket_present_but_below_minimum",
            "deployable": False,
            "support_progress": {
                "status": "accumulating",
                "current_rows": 1,
                "minimum_support_rows": 50,
                "gap_to_minimum": 49,
            },
        },
        "floor_cross_legality": {
            "verdict": "math_cross_possible_but_illegal_without_exact_support",
            "best_single_component": "feat_4h_bias50",
            "best_single_component_required_score_delta": 0.111,
        },
        "component_experiment": {"verdict": "reference_only_until_exact_support_ready"},
    }
    refreshed_payload = {
        "generated_at": "2026-04-16T23:44:54.846308+00:00",
        "scope_applicability": {
            "active_for_current_live_row": True,
            "current_structure_bucket": "CAUTION|structure_quality_caution|q15",
        },
        "support_route": {
            "verdict": "exact_bucket_supported",
            "deployable": True,
            "support_progress": {
                "status": "exact_supported",
                "current_rows": 77,
                "minimum_support_rows": 50,
                "gap_to_minimum": 0,
            },
        },
        "floor_cross_legality": {
            "verdict": "legal_component_experiment_after_support_ready",
            "legal_to_relax_runtime_gate": True,
            "best_single_component": "feat_4h_bias50",
            "best_single_component_required_score_delta": 0.754,
            "remaining_gap_to_floor": 0.2262,
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
        },
    }
    q15_audit_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(
        hb_predict_probe,
        "load_latest_features",
        lambda _session: {
            "timestamp": "2026-04-16T23:44:54.846308+00:00",
            "regime_label": "bull",
            "feat_4h_bias50": 3.2779,
        },
    )
    predict_results = [
        {
            "target_col": "simulated_pyramid_win",
            "used_model": "regime_bull_ensemble",
            "model_type": "RegimeAwarePredictor",
            "signal": "HOLD",
            "confidence": 0.537135,
            "regime_label": "bull",
            "model_route_regime": "bull",
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q15",
            "entry_quality": 0.3238,
            "entry_quality_label": "D",
            "entry_quality_components": {"trade_floor": 0.55},
            "allowed_layers_raw": 0,
            "allowed_layers_raw_reason": "entry_quality_below_trade_floor",
            "allowed_layers": 0,
            "allowed_layers_reason": "entry_quality_below_trade_floor",
            "execution_guardrail_applied": False,
            "execution_guardrail_reason": None,
            "deployment_blocker": None,
            "deployment_blocker_reason": None,
            "deployment_blocker_source": None,
            "deployment_blocker_details": None,
            "decision_quality_horizon_minutes": 1440,
            "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "decision_quality_exact_live_structure_bucket_support_rows": 77,
        },
        {
            "target_col": "simulated_pyramid_win",
            "used_model": "regime_bull_ensemble",
            "model_type": "RegimeAwarePredictor",
            "signal": "HOLD",
            "confidence": 0.537135,
            "regime_label": "bull",
            "model_route_regime": "bull",
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q15",
            "entry_quality": 0.5501,
            "entry_quality_label": "C",
            "entry_quality_components": {"trade_floor": 0.55},
            "q15_exact_supported_component_patch_applied": True,
            "allowed_layers_raw": 1,
            "allowed_layers_raw_reason": "entry_quality_C_single_layer",
            "allowed_layers": 1,
            "allowed_layers_reason": "entry_quality_C_single_layer",
            "execution_guardrail_applied": False,
            "execution_guardrail_reason": None,
            "deployment_blocker": None,
            "deployment_blocker_reason": None,
            "deployment_blocker_source": None,
            "deployment_blocker_details": None,
            "decision_quality_horizon_minutes": 1440,
            "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "decision_quality_exact_live_structure_bucket_support_rows": 77,
        },
    ]
    predict_calls = []

    def _fake_predict(_session, _predictor, _regime_models):
        predict_calls.append(True)
        return predict_results[len(predict_calls) - 1]

    monkeypatch.setattr(hb_predict_probe, "predict", _fake_predict)

    refresh_calls = []
    refresh_payloads = []

    def _fake_refresh(current_live_structure_bucket, feature_timestamp, force=False):
        refresh_calls.append((current_live_structure_bucket, feature_timestamp, force))
        if force:
            payload = dict(refreshed_payload)
            payload["current_live"] = {
                "feature_timestamp": feature_timestamp,
                "entry_quality": 0.5501,
                "entry_quality_label": "C",
                "allowed_layers": 1,
                "allowed_layers_reason": "entry_quality_C_single_layer",
            }
        else:
            payload = dict(refreshed_payload)
            payload["current_live"] = {
                "feature_timestamp": feature_timestamp,
                "entry_quality": 0.3238,
                "entry_quality_label": "D",
                "allowed_layers": 0,
                "allowed_layers_reason": "entry_quality_below_trade_floor",
            }
        refresh_payloads.append(payload)
        q15_audit_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    monkeypatch.setattr(hb_predict_probe, "_refresh_q15_support_audit", _fake_refresh)

    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)

    assert refresh_calls == [
        ("CAUTION|structure_quality_caution|q15", "2026-04-16T23:44:54.846308+00:00", False),
        ("CAUTION|structure_quality_caution|q15", "2026-04-16T23:44:54.846308+00:00", True),
    ]
    assert len(predict_calls) == 2
    assert payload["support_route_verdict"] == "exact_bucket_supported"
    assert payload["support_route_deployable"] is True
    assert payload["component_experiment_verdict"] == "exact_supported_component_experiment_ready"
    assert payload["q15_exact_supported_component_patch_applied"] is True
    assert payload["allowed_layers_raw"] == 1
    assert payload["allowed_layers"] == 1
    assert payload["q15_support_audit"]["current_live"]["entry_quality"] == 0.5501
    assert payload["q15_support_audit"]["current_live"]["allowed_layers"] == 1
    assert json.loads(out_path.read_text()) == payload


def test_q15_audit_matches_probe_rejects_incomplete_exact_supported_component_ready_payload():
    payload = {
        "generated_at": "2026-04-17T00:54:21.709888+00:00",
        "current_live": {
            "feature_timestamp": "2026-04-17T00:54:21.709888+00:00",
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
        },
        "scope_applicability": {
            "active_for_current_live_row": True,
            "current_structure_bucket": "CAUTION|structure_quality_caution|q15",
        },
        "component_experiment": {
            "verdict": "exact_supported_component_experiment_ready",
            "machine_read_answer": {
                "support_ready": True,
                "entry_quality_ge_0_55": True,
                "allowed_layers_gt_0": True,
                "preserves_positive_discrimination": None,
                "preserves_positive_discrimination_status": "not_measured_missing_current_bucket_metrics",
            },
            "positive_discrimination_evidence": {
                "preserves_positive_discrimination": None,
                "status": "not_measured_missing_current_bucket_metrics",
            },
        },
    }

    assert hb_predict_probe._q15_audit_matches_probe(
        payload,
        current_live_structure_bucket="CAUTION|structure_quality_caution|q15",
        feature_timestamp="2026-04-17T00:54:21.709888+00:00",
    ) is False


def test_hb_predict_probe_replays_when_refreshed_q15_audit_invalidates_patch(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    q15_audit_path.write_text(json.dumps({
        "generated_at": "2026-04-17T00:00:00+00:00",
        "scope_applicability": {"active_for_current_live_row": True, "current_structure_bucket": "CAUTION|structure_quality_caution|q15"},
        "support_route": {"verdict": "exact_bucket_supported", "deployable": True, "support_progress": {"status": "exact_supported", "current_rows": 77, "minimum_support_rows": 50, "gap_to_minimum": 0}},
        "floor_cross_legality": {"verdict": "legal_component_experiment_after_support_ready", "legal_to_relax_runtime_gate": True},
        "component_experiment": {"verdict": "exact_supported_component_experiment_ready", "feature": "feat_4h_bias50", "machine_read_answer": {"support_ready": True, "entry_quality_ge_0_55": True, "allowed_layers_gt_0": True, "preserves_positive_discrimination": True}}
    }), encoding="utf-8")
    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(hb_predict_probe, "load_latest_features", lambda _session: {"timestamp": "2026-04-17T00:00:00+00:00", "regime_label": "bull"})

    results = [
        {
            "target_col": "simulated_pyramid_win", "used_model": "regime_bull_ensemble", "model_type": "RegimeAwarePredictor",
            "signal": "HOLD", "confidence": 0.34, "regime_label": "bull", "model_route_regime": "bull", "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q15", "entry_quality": 0.5501, "entry_quality_label": "C",
            "allowed_layers_raw": 1, "allowed_layers_raw_reason": "entry_quality_C_single_layer", "allowed_layers": 0, "allowed_layers_reason": "unsupported_exact_live_structure_bucket",
            "q15_exact_supported_component_patch_applied": True, "execution_guardrail_applied": True, "execution_guardrail_reason": "unsupported_exact_live_structure_bucket",
            "deployment_blocker": "unsupported_exact_live_structure_bucket", "deployment_blocker_reason": "support not enough", "deployment_blocker_source": "decision_quality_contract", "deployment_blocker_details": {"exact_live_structure_bucket_rows": 0},
            "decision_quality_horizon_minutes": 1440, "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q15", "decision_quality_exact_live_structure_bucket_support_rows": 0,
        },
        {
            "target_col": "simulated_pyramid_win", "used_model": "regime_bull_ensemble", "model_type": "RegimeAwarePredictor",
            "signal": "HOLD", "confidence": 0.31, "regime_label": "bull", "model_route_regime": "bull", "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q15", "entry_quality": 0.3027, "entry_quality_label": "D",
            "allowed_layers_raw": 0, "allowed_layers_raw_reason": "entry_quality_below_trade_floor", "allowed_layers": 0, "allowed_layers_reason": "entry_quality_below_trade_floor",
            "q15_exact_supported_component_patch_applied": False, "execution_guardrail_applied": False, "execution_guardrail_reason": None,
            "deployment_blocker": None, "deployment_blocker_reason": None, "deployment_blocker_source": None, "deployment_blocker_details": None,
            "decision_quality_horizon_minutes": 1440, "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q15", "decision_quality_exact_live_structure_bucket_support_rows": 0,
        },
    ]
    predict_calls = []

    def _fake_predict(*_args, **_kwargs):
        predict_calls.append(True)
        return results[len(predict_calls) - 1]

    monkeypatch.setattr(hb_predict_probe, "predict", _fake_predict)

    refreshed_payload = {
        "generated_at": "2026-04-17T00:00:00+00:00",
        "scope_applicability": {"active_for_current_live_row": True, "current_structure_bucket": "CAUTION|structure_quality_caution|q15"},
        "support_route": {"verdict": "exact_bucket_missing_proxy_reference_only", "deployable": False, "support_progress": {"status": "stalled_under_minimum", "current_rows": 0, "minimum_support_rows": 50, "gap_to_minimum": 50}},
        "floor_cross_legality": {"verdict": "floor_crossed_but_support_not_ready", "legal_to_relax_runtime_gate": False, "remaining_gap_to_floor": 0.0},
        "component_experiment": {"verdict": "reference_only_until_exact_support_ready", "feature": None, "machine_read_answer": {"support_ready": False, "entry_quality_ge_0_55": False, "allowed_layers_gt_0": False, "preserves_positive_discrimination": None}},
    }

    def _fake_refresh(current_live_structure_bucket, feature_timestamp, force=False):
        assert current_live_structure_bucket == "CAUTION|structure_quality_caution|q15"
        assert feature_timestamp == "2026-04-17T00:00:00+00:00"
        q15_audit_path.write_text(json.dumps(refreshed_payload), encoding="utf-8")
        return refreshed_payload

    monkeypatch.setattr(hb_predict_probe, "_refresh_q15_support_audit", _fake_refresh)

    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)

    assert len(predict_calls) == 2
    assert payload["q15_exact_supported_component_patch_applied"] is False
    assert payload["entry_quality"] == 0.3027
    assert payload["runtime_closure_state"] == "patch_inactive_or_blocked"
    assert payload["support_route_verdict"] == "exact_bucket_missing_proxy_reference_only"
    assert payload["component_experiment_verdict"] == "reference_only_until_exact_support_ready"
    assert json.loads(out_path.read_text()) == payload


def test_hb_predict_probe_emits_toxic_exact_lane_runtime_blocker_summary(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", tmp_path / "missing_q15_support_audit.json")
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(
        hb_predict_probe,
        "load_latest_features",
        lambda _session: {"timestamp": "2026-04-17T00:00:00+00:00", "regime_label": "bull"},
    )
    monkeypatch.setattr(
        hb_predict_probe,
        "predict",
        lambda *_args, **_kwargs: {
            "target_col": "simulated_pyramid_win",
            "used_model": "regime_bull_ensemble",
            "model_type": "RegimeAwarePredictor",
            "signal": "BUY",
            "confidence": 0.86,
            "regime_label": "bull",
            "model_route_regime": "bull",
            "regime_gate": "CAUTION",
            "structure_bucket": "CAUTION|structure_quality_caution|q35",
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "entry_quality": 0.4556,
            "entry_quality_label": "D",
            "allowed_layers_raw": 0,
            "allowed_layers_raw_reason": "entry_quality_below_trade_floor",
            "allowed_layers": 0,
            "allowed_layers_reason": "decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade",
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "decision_quality_below_trade_floor; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade",
            "deployment_blocker": "exact_live_lane_toxic_sub_bucket_current_bucket",
            "deployment_blocker_reason": "current q35 bucket is the exact-lane toxic sub-bucket",
            "deployment_blocker_source": "decision_quality_contract",
            "deployment_blocker_details": {
                "current_live_structure_bucket_rows": 137,
                "toxic_bucket": {
                    "bucket": "CAUTION|structure_quality_caution|q35",
                    "rows": 137,
                    "win_rate": 0.5474,
                    "avg_quality": 0.1729,
                },
            },
            "decision_quality_horizon_minutes": 1440,
            "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "decision_quality_exact_live_structure_bucket_support_rows": 137,
        },
    )

    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["deployment_blocker"] == "exact_live_lane_toxic_sub_bucket_current_bucket"
    assert payload["runtime_closure_state"] == "deployment_guardrail_blocks_trade"
    assert "已具 exact support" in payload["runtime_closure_summary"]
    assert "不可把 support closure 誤讀成 deployment closure" in payload["runtime_closure_summary"]
    assert json.loads(out_path.read_text()) == payload


def test_hb_predict_probe_emits_capacity_opened_hold_summary(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    q15_audit_path.write_text(json.dumps({
        "scope_applicability": {"active_for_current_live_row": True, "current_structure_bucket": "CAUTION|structure_quality_caution|q15"},
        "support_route": {"verdict": "exact_bucket_supported", "deployable": True, "support_progress": {"status": "exact_supported", "current_rows": 77, "minimum_support_rows": 50, "gap_to_minimum": 0}},
        "floor_cross_legality": {"verdict": "legal_component_experiment_after_support_ready"},
        "component_experiment": {"verdict": "exact_supported_component_experiment_ready"}
    }), encoding="utf-8")
    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(hb_predict_probe, "load_latest_features", lambda _session: {"timestamp": "2026-04-17T00:00:00+00:00", "regime_label": "bull"})
    monkeypatch.setattr(hb_predict_probe, "predict", lambda *_args, **_kwargs: {
        "target_col": "simulated_pyramid_win", "used_model": "regime_bull_ensemble", "model_type": "RegimeAwarePredictor",
        "signal": "HOLD", "confidence": 0.34, "regime_label": "bull", "model_route_regime": "bull", "regime_gate": "CAUTION",
        "structure_bucket": "CAUTION|structure_quality_caution|q15", "entry_quality": 0.5501, "entry_quality_label": "C",
        "allowed_layers_raw": 1, "allowed_layers_raw_reason": "entry_quality_C_single_layer", "allowed_layers": 1, "allowed_layers_reason": "entry_quality_C_single_layer",
        "q15_exact_supported_component_patch_applied": True, "execution_guardrail_applied": False, "execution_guardrail_reason": None,
        "deployment_blocker": None, "deployment_blocker_reason": None, "deployment_blocker_source": None, "deployment_blocker_details": None,
        "decision_quality_horizon_minutes": 1440, "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q15", "decision_quality_exact_live_structure_bucket_support_rows": 77
    })
    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["q15_exact_supported_component_patch_applied"] is True
    assert payload["runtime_closure_state"] == "capacity_opened_signal_hold"
    assert "1 層 deployment capacity" in payload["runtime_closure_summary"]


def test_hb_predict_probe_emits_patch_active_when_q15_capacity_is_live_and_signal_is_buy(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    q15_audit_path.write_text(json.dumps({
        "scope_applicability": {"active_for_current_live_row": True, "current_structure_bucket": "CAUTION|structure_quality_caution|q15"},
        "support_route": {"verdict": "exact_bucket_supported", "deployable": True, "support_progress": {"status": "exact_supported", "current_rows": 95, "minimum_support_rows": 50, "gap_to_minimum": 0}},
        "floor_cross_legality": {"verdict": "legal_component_experiment_after_support_ready", "legal_to_relax_runtime_gate": True},
        "component_experiment": {"verdict": "exact_supported_component_experiment_ready", "feature": "feat_4h_bias50", "machine_read_answer": {"support_ready": True, "entry_quality_ge_0_55": True, "allowed_layers_gt_0": True, "preserves_positive_discrimination": True}}
    }), encoding="utf-8")
    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(hb_predict_probe, "load_latest_features", lambda _session: {"timestamp": "2026-04-18T12:29:28.706281", "regime_label": "bull"})
    monkeypatch.setattr(hb_predict_probe, "predict", lambda *_args, **_kwargs: {
        "target_col": "simulated_pyramid_win", "used_model": "regime_bull_ensemble", "model_type": "RegimeAwarePredictor",
        "signal": "BUY", "confidence": 0.749339, "regime_label": "bull", "model_route_regime": "bull", "regime_gate": "CAUTION",
        "structure_bucket": "CAUTION|structure_quality_caution|q15", "entry_quality": 0.55, "entry_quality_label": "C",
        "allowed_layers_raw": 1, "allowed_layers_raw_reason": "entry_quality_C_single_layer", "allowed_layers": 1, "allowed_layers_reason": "entry_quality_C_single_layer",
        "q15_exact_supported_component_patch_applied": True, "execution_guardrail_applied": False, "execution_guardrail_reason": None,
        "deployment_blocker": None, "deployment_blocker_reason": None, "deployment_blocker_source": None, "deployment_blocker_details": None,
        "decision_quality_horizon_minutes": 1440, "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q15", "decision_quality_exact_live_structure_bucket_support_rows": 95,
        "support_route_verdict": "exact_bucket_supported", "support_route_deployable": True, "support_progress": {"status": "exact_supported", "current_rows": 95, "minimum_support_rows": 50, "gap_to_minimum": 0},
        "minimum_support_rows": 50, "current_live_structure_bucket_gap_to_minimum": 0,
    })
    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["q15_exact_supported_component_patch_applied"] is True
    assert payload["runtime_closure_state"] == "patch_active"
    assert "q15 patch active" in payload["runtime_closure_summary"]


def test_hb_predict_probe_emits_patch_active_but_execution_blocked_summary(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", tmp_path / "missing_q15_support_audit.json")
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(hb_predict_probe, "load_latest_features", lambda _session: {"timestamp": "2026-04-17T00:00:00+00:00", "regime_label": "bull"})
    monkeypatch.setattr(hb_predict_probe, "predict", lambda *_args, **_kwargs: {
        "target_col": "simulated_pyramid_win", "used_model": "regime_bull_ensemble", "model_type": "RegimeAwarePredictor",
        "signal": "HOLD", "confidence": 0.32, "regime_label": "bull", "model_route_regime": "bull", "regime_gate": "CAUTION",
        "structure_bucket": "CAUTION|structure_quality_caution|q15", "entry_quality": 0.55, "entry_quality_label": "C",
        "allowed_layers_raw": 1, "allowed_layers_raw_reason": "entry_quality_C_single_layer", "allowed_layers": 0, "allowed_layers_reason": "unsupported_exact_live_structure_bucket",
        "q15_exact_supported_component_patch_applied": True, "execution_guardrail_applied": True, "execution_guardrail_reason": "unsupported_exact_live_structure_bucket",
        "deployment_blocker": "unsupported_exact_live_structure_bucket", "deployment_blocker_reason": "exact bucket rows still zero", "deployment_blocker_source": "decision_quality_contract", "deployment_blocker_details": None,
        "decision_quality_horizon_minutes": 1440, "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q15", "decision_quality_exact_live_structure_bucket_support_rows": 0
    })
    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["q15_exact_supported_component_patch_applied"] is True
    assert payload["runtime_closure_state"] == "patch_active_but_execution_blocked"
    assert "q15 patch 已啟用並把 entry_quality 拉到 0.5500" in payload["runtime_closure_summary"]
    assert "不可把 patch active 誤讀成可部署" in payload["runtime_closure_summary"]


def test_hb_predict_probe_emits_q15_patch_active_trade_floor_blocker_summary(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    q15_audit_path.write_text(json.dumps({
        "scope_applicability": {"active_for_current_live_row": True, "current_structure_bucket": "CAUTION|structure_quality_caution|q15"},
        "support_route": {"verdict": "exact_bucket_supported", "deployable": True, "support_progress": {"status": "exact_supported", "current_rows": 96, "minimum_support_rows": 50, "gap_to_minimum": 0}},
        "floor_cross_legality": {"verdict": "legal_component_experiment_after_support_ready", "remaining_gap_to_floor": 0.2115, "best_single_component": "feat_4h_bias50", "best_single_component_required_score_delta": 0.705},
        "component_experiment": {"verdict": "exact_supported_component_experiment_ready"}
    }), encoding="utf-8")
    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(hb_predict_probe, "load_latest_features", lambda _session: {"timestamp": "2026-04-18T12:08:40.638156", "regime_label": "bull"})
    monkeypatch.setattr(hb_predict_probe, "predict", lambda *_args, **_kwargs: {
        "target_col": "simulated_pyramid_win", "used_model": "regime_bull_ensemble", "model_type": "RegimeAwarePredictor",
        "signal": "BUY", "confidence": 0.764611, "regime_label": "bull", "model_route_regime": "bull", "regime_gate": "CAUTION",
        "structure_bucket": "CAUTION|structure_quality_caution|q15", "entry_quality": 0.55, "entry_quality_label": "C",
        "entry_quality_components": {"trade_floor": 0.55},
        "allowed_layers_raw": 1, "allowed_layers_raw_reason": "entry_quality_C_single_layer", "allowed_layers": 0, "allowed_layers_reason": "decision_quality_below_trade_floor",
        "q15_exact_supported_component_patch_applied": True, "execution_guardrail_applied": True, "execution_guardrail_reason": "decision_quality_below_trade_floor",
        "deployment_blocker": "decision_quality_below_trade_floor", "deployment_blocker_reason": "q15 patch 已啟用但 final execution 仍被 trade floor 擋住", "deployment_blocker_source": "decision_quality_contract+q15_support_audit",
        "deployment_blocker_details": {"support_route_verdict": "exact_bucket_supported", "current_live_structure_bucket_rows": 96, "minimum_support_rows": 50, "allowed_layers_raw": 1, "q15_exact_supported_component_patch_applied": True},
        "decision_quality_horizon_minutes": 1440, "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q15", "decision_quality_exact_live_structure_bucket_support_rows": 96,
        "support_route_verdict": "exact_bucket_supported", "support_route_deployable": True, "support_progress": {"status": "exact_supported", "current_rows": 96, "minimum_support_rows": 50, "gap_to_minimum": 0},
        "minimum_support_rows": 50, "current_live_structure_bucket_gap_to_minimum": 0,
    })
    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["deployment_blocker"] == "decision_quality_below_trade_floor"
    assert payload["q15_exact_supported_component_patch_applied"] is True
    assert payload["runtime_closure_state"] == "patch_active_but_execution_blocked"
    assert "q15 patch 已啟用並把 entry_quality 拉到 0.5500（raw layers=1）" in payload["runtime_closure_summary"]
    assert "decision_quality_below_trade_floor" in payload["runtime_closure_summary"]


def test_hb_predict_probe_emits_q35_patch_active_but_execution_blocked_summary(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", tmp_path / "missing_q15_support_audit.json")
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(hb_predict_probe, "load_latest_features", lambda _session: {"timestamp": "2026-04-17T20:15:27.519273", "regime_label": "bull"})
    monkeypatch.setattr(hb_predict_probe, "predict", lambda *_args, **_kwargs: {
        "target_col": "simulated_pyramid_win", "used_model": "regime_bull_ensemble", "model_type": "RegimeAwarePredictor",
        "signal": "HOLD", "confidence": 0.339355, "regime_label": "bull", "model_route_regime": "bull", "regime_gate": "CAUTION",
        "structure_bucket": "CAUTION|structure_quality_caution|q35", "entry_quality": 0.5514, "entry_quality_label": "C",
        "q35_discriminative_redesign_applied": True,
        "q35_discriminative_redesign": {"applied": True, "weights": {"feat_nose": 0.8, "feat_ear": 0.2}},
        "allowed_layers_raw": 1, "allowed_layers_raw_reason": "entry_quality_C_single_layer", "allowed_layers": 0, "allowed_layers_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket",
        "execution_guardrail_applied": True, "execution_guardrail_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket",
        "deployment_blocker": "unsupported_exact_live_structure_bucket", "deployment_blocker_reason": "exact bucket rows still zero", "deployment_blocker_source": "decision_quality_contract", "deployment_blocker_details": {"current_live_structure_bucket_rows": 0, "exact_live_structure_bucket_rows": 0},
        "decision_quality_horizon_minutes": 1440, "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q35", "decision_quality_exact_live_structure_bucket_support_rows": 0
    })
    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["q35_discriminative_redesign_applied"] is True
    assert payload["runtime_closure_state"] == "patch_active_but_execution_blocked"
    assert payload["deployment_blocker"] == "unsupported_exact_live_structure_bucket"
    assert "q35 discriminative redesign 已啟用並把 entry_quality 拉到 0.5514" in payload["runtime_closure_summary"]
    assert "unsupported_exact_live_structure_bucket" in payload["runtime_closure_summary"]


def test_hb_predict_probe_emits_circuit_breaker_runtime_closure(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", tmp_path / "missing_q15_support_audit.json")
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(hb_predict_probe, "load_latest_features", lambda _session: {"timestamp": "2026-04-17T00:00:00+00:00", "regime_label": "bull"})
    monkeypatch.setattr(hb_predict_probe, "predict", lambda *_args, **_kwargs: {
        "target_col": "simulated_pyramid_win", "used_model": "circuit_breaker", "model_type": "circuit_breaker",
        "signal": "CIRCUIT_BREAKER", "confidence": 0.5, "reason": "Recent 50-sample win rate: 10.00% < 30%",
        "streak": 45, "recent_window_win_rate": 0.1, "recent_window_wins": 5, "window_size": 50,
        "triggered_by": ["recent_win_rate"], "horizon_minutes": 1440,
        "allowed_layers_raw": None, "allowed_layers_raw_reason": "circuit_breaker_preempts_runtime_sizing",
        "allowed_layers": 0, "allowed_layers_reason": "circuit_breaker_blocks_trade",
        "execution_guardrail_applied": True, "execution_guardrail_reason": "circuit_breaker_blocks_trade",
        "deployment_blocker": "circuit_breaker_active", "deployment_blocker_reason": "Recent 50-sample win rate: 10.00% < 30%",
        "deployment_blocker_source": "circuit_breaker", "deployment_blocker_details": {
            "recent_window": {"window_size": 50, "wins": 5, "win_rate": 0.1, "floor": 0.3},
            "release_condition": {
                "streak_must_be_below": 50,
                "current_streak": 45,
                "recent_window": 50,
                "recent_win_rate_must_be_at_least": 0.3,
                "current_recent_window_wins": 5,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 10,
            },
        },
        "decision_quality_recent_pathology_applied": True,
        "decision_quality_recent_pathology_reason": "recent drift primary window 500 rows shows distribution_pathology; dominant_regime=bull (100%); alerts=['label_imbalance', 'regime_concentration']",
        "decision_quality_recent_pathology_window": 500,
        "decision_quality_recent_pathology_alerts": ["label_imbalance", "regime_concentration"],
        "decision_quality_recent_pathology_summary": {"win_rate": 0.804, "dominant_regime": "bull"},
        "decision_quality_horizon_minutes": 1440,
    })
    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["runtime_closure_state"] == "circuit_breaker_active"
    assert payload["allowed_layers_reason"] == "circuit_breaker_blocks_trade"
    assert payload["execution_guardrail_reason"] == "circuit_breaker_blocks_trade"
    assert payload["deployment_blocker"] == "circuit_breaker_active"
    assert "release condition = streak < 50 且 recent 50 win rate >= 30%" in payload["runtime_closure_summary"]
    assert "目前 recent 50 只贏 5/50，至少還差 10 勝" in payload["runtime_closure_summary"]
    assert "recent pathology=recent drift primary window 500 rows shows distribution_pathology" in payload["runtime_closure_summary"]


def test_hb_predict_probe_prefers_q15_audit_support_progress_even_under_circuit_breaker(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    q15_audit_path.write_text(
        json.dumps(
            {
                "scope_applicability": {
                    "active_for_current_live_row": True,
                    "current_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                },
                "support_route": {
                    "verdict": "exact_bucket_missing_exact_lane_proxy_only",
                    "deployable": False,
                    "support_progress": {
                        "status": "regressed_under_minimum",
                        "current_rows": 0,
                        "minimum_support_rows": 50,
                        "gap_to_minimum": 50,
                        "delta_vs_previous": -41,
                        "previous_rows": 41,
                    },
                },
                "floor_cross_legality": {
                    "verdict": "runtime_blocker_preempts_floor_analysis",
                    "best_single_component": "feat_4h_bias50",
                    "best_single_component_required_score_delta": 0.885,
                },
                "component_experiment": {"verdict": "runtime_blocker_preempts_component_experiment"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(
        hb_predict_probe,
        "load_latest_features",
        lambda _session: {
            "timestamp": "2026-04-18 20:43:06.555618",
            "regime_label": "bull",
            "feat_4h_bias50": 2.3655,
        },
    )
    monkeypatch.setattr(
        hb_predict_probe,
        "predict",
        lambda *_args, **_kwargs: {
            "target_col": "simulated_pyramid_win",
            "used_model": "circuit_breaker",
            "model_type": "circuit_breaker",
            "signal": "CIRCUIT_BREAKER",
            "confidence": 0.5,
            "reason": "Consecutive loss streak: 235 >= 50; Recent 50-sample win rate: 0.00% < 30%",
            "streak": 235,
            "recent_window_win_rate": 0.0,
            "recent_window_wins": 0,
            "window_size": 50,
            "triggered_by": ["streak", "recent_win_rate"],
            "horizon_minutes": 1440,
            "regime_gate": "BLOCK",
            "structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
            "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
            "current_live_structure_bucket_rows": 0,
            "entry_quality": 0.2845,
            "entry_quality_label": "D",
            "support_route_verdict": "exact_bucket_missing_exact_lane_proxy_only",
            "support_route_deployable": False,
            "support_progress": {
                "status": "stalled_under_minimum",
                "current_rows": 0,
                "minimum_support_rows": 50,
                "gap_to_minimum": 50,
            },
            "deployment_blocker": "circuit_breaker_active",
            "deployment_blocker_reason": "Consecutive loss streak: 235 >= 50; Recent 50-sample win rate: 0.00% < 30%",
            "deployment_blocker_source": "circuit_breaker",
            "deployment_blocker_details": {
                "recent_window": {"window_size": 50, "wins": 0, "win_rate": 0.0, "floor": 0.3},
                "release_condition": {
                    "streak_must_be_below": 50,
                    "current_streak": 235,
                    "recent_window": 50,
                    "recent_win_rate_must_be_at_least": 0.3,
                    "current_recent_window_wins": 0,
                    "required_recent_window_wins": 15,
                    "additional_recent_window_wins_needed": 15,
                },
            },
            "allowed_layers": 0,
            "allowed_layers_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active",
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active",
            "decision_quality_horizon_minutes": 1440,
        },
    )

    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["support_route_verdict"] == "exact_bucket_missing_exact_lane_proxy_only"
    assert payload["support_progress"]["status"] == "regressed_under_minimum"
    assert payload["support_progress"]["delta_vs_previous"] == -41
    assert payload["support_progress"]["previous_rows"] == 41
    assert payload["deployment_blocker_details"]["support_progress"]["delta_vs_previous"] == -41


def test_hb_predict_probe_surfaces_recommended_patch_summary_for_bull_caution_spillover(monkeypatch, capsys, tmp_path):
    session = DummySession()
    out_path = tmp_path / "live_predict_probe.json"
    q15_audit_path = tmp_path / "q15_support_audit.json"
    q15_audit_path.write_text("{}", encoding="utf-8")
    bull_patch_path = tmp_path / "bull_4h_pocket_ablation.json"
    bull_patch_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-19 07:10:00",
                "collapse_features": [
                    "feat_4h_dist_swing_low",
                    "feat_4h_dist_bb_lower",
                    "feat_4h_bb_pct_b",
                ],
                "min_collapse_flags": 2,
                "cohorts": {
                    "bull_collapse_q35": {
                        "rows": 472,
                        "base_win_rate": 0.7458,
                        "recommended_profile": "core_plus_macro",
                        "profiles": {
                            "core_plus_macro": {
                                "cv_mean_accuracy": 0.6123,
                            }
                        },
                    }
                },
                "support_pathology_summary": {
                    "preferred_support_cohort": "bull_exact_live_lane_proxy",
                    "minimum_support_rows": 50,
                    "current_live_structure_bucket_rows": 0,
                    "current_live_structure_bucket_gap_to_minimum": 50,
                    "recommended_action": "維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。",
                },
                "live_context": {
                    "support_route_verdict": "exact_bucket_missing_exact_lane_proxy_only",
                    "support_route_deployable": False,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(hb_predict_probe, "OUT_PATH", out_path)
    monkeypatch.setattr(hb_predict_probe, "Q15_SUPPORT_AUDIT_PATH", q15_audit_path)
    monkeypatch.setattr(hb_predict_probe, "BULL_4H_POCKET_ABLATION_PATH", bull_patch_path)
    monkeypatch.setattr(hb_predict_probe, "init_db", lambda _db_url: session)
    monkeypatch.setattr(hb_predict_probe, "load_predictor", lambda: (object(), {"bull": object()}))
    monkeypatch.setattr(
        hb_predict_probe,
        "load_latest_features",
        lambda _session: {
            "timestamp": "2026-04-19 07:15:00",
            "regime_label": "bull",
            "feat_4h_bias50": 2.44,
        },
    )
    monkeypatch.setattr(
        hb_predict_probe,
        "predict",
        lambda _session, _predictor, _regime_models: {
            "target_col": "simulated_pyramid_win",
            "used_model": "circuit_breaker",
            "model_type": "circuit_breaker",
            "signal": "CIRCUIT_BREAKER",
            "confidence": 0.5,
            "should_trade": False,
            "reason": "Consecutive loss streak: 237 >= 50; Recent 50-sample win rate: 0.00% < 30%",
            "streak": 237,
            "recent_window_wins": 0,
            "window_size": 50,
            "triggered_by": ["streak", "recent_win_rate"],
            "horizon_minutes": 1440,
            "regime_label": "bull",
            "model_route_regime": "bull",
            "regime_gate": "BLOCK",
            "structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
            "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
            "current_live_structure_bucket_rows": 0,
            "entry_quality": 0.3467,
            "entry_quality_label": "D",
            "entry_quality_components": {"trade_floor": 0.55},
            "allowed_layers_raw": 0,
            "allowed_layers_raw_reason": "regime_gate_block",
            "allowed_layers": 0,
            "allowed_layers_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active",
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active",
            "deployment_blocker": "circuit_breaker_active",
            "deployment_blocker_reason": "Consecutive loss streak: 237 >= 50; Recent 50-sample win rate: 0.00% < 30%",
            "deployment_blocker_source": "circuit_breaker",
            "deployment_blocker_details": {
                "recent_window": {"window_size": 50, "wins": 0, "win_rate": 0.0, "floor": 0.3},
                "release_condition": {
                    "streak_must_be_below": 50,
                    "current_streak": 237,
                    "recent_window": 50,
                    "recent_win_rate_must_be_at_least": 0.3,
                    "current_recent_window_wins": 0,
                    "required_recent_window_wins": 15,
                    "additional_recent_window_wins_needed": 15,
                },
            },
            "support_route_verdict": "exact_bucket_missing_exact_lane_proxy_only",
            "support_route_deployable": False,
            "support_progress": {
                "status": "stalled_under_minimum",
                "current_rows": 0,
                "minimum_support_rows": 50,
                "gap_to_minimum": 50,
            },
            "decision_quality_scope_diagnostics": {
                "regime_label+regime_gate+entry_quality_label": {
                    "rows": 0,
                    "win_rate": None,
                    "avg_pnl": None,
                    "avg_quality": None,
                    "avg_drawdown_penalty": None,
                    "avg_time_underwater": None,
                    "current_live_structure_bucket": "BLOCK|bull_q15_bias50_overextended_block|q15",
                    "current_live_structure_bucket_rows": 0,
                    "alerts": ["no_rows"],
                },
                "regime_label+entry_quality_label": {
                    "rows": 200,
                    "win_rate": 0.0,
                    "avg_pnl": -0.01,
                    "avg_quality": -0.2868,
                    "avg_drawdown_penalty": 0.3869,
                    "avg_time_underwater": 0.9055,
                    "spillover_vs_exact_live_lane": {
                        "extra_rows": 200,
                        "extra_row_share": 1.0,
                        "worst_extra_regime_gate": {
                            "regime_gate": "bull|CAUTION",
                            "rows": 113,
                            "win_rate": 0.0,
                            "avg_pnl": -0.0109,
                            "avg_quality": -0.2947,
                            "avg_drawdown_penalty": 0.3817,
                            "avg_time_underwater": 0.818,
                        },
                        "worst_extra_regime_gate_feature_contrast": {
                            "top_mean_shift_features": [
                                {"feature": "feat_4h_bias200", "reference_mean": 7.52, "current_mean": 9.86, "mean_delta": 2.34},
                                {"feature": "feat_4h_dist_bb_lower", "reference_mean": 0.81, "current_mean": 3.07, "mean_delta": 2.26},
                            ]
                        },
                    },
                },
            },
        },
    )

    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)

    summary = payload["decision_quality_scope_pathology_summary"]
    patch = summary["recommended_patch"]
    assert summary["spillover"]["worst_extra_regime_gate"]["regime_gate"] == "bull|CAUTION"
    assert patch["recommended_profile"] == "core_plus_macro"
    assert patch["status"] == "reference_only_until_exact_support_ready"
    assert patch["support_route_verdict"] == "exact_bucket_missing_exact_lane_proxy_only"
    assert patch["gap_to_minimum"] == 50
    assert patch["collapse_features"] == [
        "feat_4h_dist_swing_low",
        "feat_4h_dist_bb_lower",
        "feat_4h_bb_pct_b",
    ]
