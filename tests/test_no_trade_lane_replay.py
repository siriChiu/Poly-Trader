import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "no_trade_lane_replay.py"
spec = importlib.util.spec_from_file_location("no_trade_lane_replay_test_module", MODULE_PATH)
replay = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(replay)


def _recent_drift_payload():
    return {
        "generated_at": "2026-06-03T14:55:49Z",
        "primary_window": {
            "window": 100,
            "summary": {
                "win_rate": 0.27,
                "dominant_regime": "bear",
                "dominant_regime_share": 0.94,
                "alerts": ["regime_concentration", "regime_shift"],
            },
        },
        "canonical_tail_root_cause": {
            "no_new_risk_shadow_replay": {
                "mode": "shadow_only_no_new_risk_falsification",
                "shadow_only": True,
                "risk_on_order_enabled": False,
                "order_submission_enabled": False,
                "live_exposure_allowed": False,
                "deployable": False,
                "deployment_verdict": "not_deployable_shadow_only_runtime_blocked",
                "baseline": {"rows": 100, "wins": 27, "losses": 73, "win_rate": 0.27},
                "best_observable_gate": "dominant_regime_shadow_gate",
                "gates": [
                    {
                        "id": "dominant_regime_shadow_gate",
                        "falsification_verdict": "fails_shadow_metric",
                        "runtime_candidate": True,
                        "uses_future_outcome_fields": False,
                        "blocked_rows": 94,
                        "blocked_losses": 67,
                        "loss_capture_share": 0.918,
                        "win_cost_share": 1.0,
                        "kept_rows": 6,
                        "kept_win_rate": 0.0,
                    }
                ],
            }
        },
    }


def test_no_trade_lane_replay_validates_abstain_reduce_only_without_deployable_support():
    payload = replay.build_no_trade_lane_replay(
        live_predict_probe={
            "generated_at": "2026-06-03T14:56:38Z",
            "signal": "CIRCUIT_BREAKER",
            "should_trade": False,
            "deployment_blocker": "circuit_breaker_active",
            "runtime_closure_state": "circuit_breaker_active",
            "regime_label": "bear",
            "regime_gate": "BLOCK",
            "current_live_structure_bucket": "BLOCK|bias200_below_min|q00",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "support_route_verdict": "exact_bucket_unsupported_block",
            "support_governance_route": "exact_live_lane_proxy_available",
            "allowed_layers_raw": 0,
            "allowed_layers": 0,
            "allowed_layers_reason": "decision_quality_below_trade_floor; circuit_breaker_active",
            "execution_guardrail_reason": "decision_quality_below_trade_floor; circuit_breaker_active",
            "api_trade_guardrail_active": True,
            "api_trade_buy_guardrail": "current_live_deployment_blocker_409",
            "api_trade_allowed_actions": ["wait", "reduce", "sell", "shadow_buy", "paper_buy"],
            "api_trade_allowed_risk_off_sides": ["reduce", "sell"],
            "api_trade_allowed_paper_shadow_sides": ["shadow_buy", "paper_buy"],
            "release_condition": {
                "current_recent_window_wins": 6,
                "recent_window": 50,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 9,
            },
        },
        recent_drift_report=_recent_drift_payload(),
        live_canary_structural_pivot={
            "current_truth": {
                "current_lane_actionability": "no_trade_block_lane",
                "support_evidence_role": "no_trade_decision_validation_not_deployable_support",
                "structure_bucket": "BLOCK|bias200_below_min|q00",
            },
            "structural_decision": {
                "map_signal_next_validation_artifact": "data/no_trade_lane_replay.json",
            },
        },
        generated_at="2026-06-03T15:00:00Z",
    )

    decision = payload["replay_decision"]
    checks = payload["machine_checks"]
    replay_payload = payload["replay"]

    assert decision["verdict"] == "validated_abstain_reduce_only_no_trade_lane"
    assert decision["validated"] is True
    assert decision["deployable"] is False
    assert decision["buy_add_support_closure_allowed"] is False
    assert decision["support_rows_counted_for_buy_add"] is False
    assert decision["risk_on_order_enabled"] is False
    assert decision["order_submission_enabled"] is False
    assert checks["all_passed"] is True
    assert checks["support_evidence_not_deployable"] is True
    assert replay_payload["abstain_path"]["validated"] is True
    assert replay_payload["reduce_only_path"]["validated"] is True
    assert replay_payload["paper_shadow_path"]["validated"] is True
    assert replay_payload["recent_drift_shadow_context"]["best_gate_id"] == "dominant_regime_shadow_gate"


def test_no_trade_lane_replay_does_not_validate_risk_on_lane():
    payload = replay.build_no_trade_lane_replay(
        live_predict_probe={
            "signal": "BUY",
            "should_trade": True,
            "regime_gate": "ALLOW",
            "current_live_structure_bucket": "ALLOW|trend|q65",
            "current_live_structure_bucket_rows": 55,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 0,
            "allowed_layers_raw": 1,
            "allowed_layers": 1,
            "api_trade_allowed_risk_off_sides": ["reduce", "sell"],
            "api_trade_allowed_paper_shadow_sides": ["shadow_buy", "paper_buy"],
        },
        recent_drift_report=_recent_drift_payload(),
        generated_at="2026-06-03T15:00:00Z",
    )

    assert payload["replay_decision"]["verdict"] == "not_applicable_or_incomplete_no_trade_replay"
    assert payload["replay_decision"]["validated"] is False
    assert payload["replay_decision"]["deployable"] is False
    assert payload["machine_checks"]["current_lane_is_no_trade_block_lane"] is False
    assert payload["machine_checks"]["buy_add_support_closure_allowed"] is False
