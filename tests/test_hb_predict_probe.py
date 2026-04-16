import json

from scripts import hb_predict_probe


class DummySession:
    def close(self):
        return None


def test_hb_predict_probe_emits_q35_runtime_and_structure_fields(monkeypatch, capsys):
    session = DummySession()

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
            "structure_bucket": "CAUTION|structure_quality_caution|q35",
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
            "decision_quality_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "decision_quality_exact_live_structure_bucket_support_rows": 1,
        },
    )

    hb_predict_probe.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["structure_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert payload["current_live_structure_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert payload["current_live_structure_bucket_rows"] == 1
    assert payload["q35_discriminative_redesign_applied"] is True
    assert payload["q35_discriminative_redesign"]["applied"] is True
    assert payload["allowed_layers_raw"] == 1
    assert payload["allowed_layers_raw_reason"] == "entry_quality_C_single_layer"
    assert payload["allowed_layers_reason"] == "under_minimum_exact_live_structure_bucket"
    assert payload["deployment_blocker"] == "under_minimum_exact_live_structure_bucket"
