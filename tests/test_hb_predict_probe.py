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
    assert payload["runtime_closure_state"] == "patch_inactive_or_blocked"
    assert json.loads(out_path.read_text()) == payload


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
    assert "patch 已啟用並把 entry_quality 拉到 0.5500" in payload["runtime_closure_summary"]
    assert "不可把 patch active 誤讀成可部署" in payload["runtime_closure_summary"]
