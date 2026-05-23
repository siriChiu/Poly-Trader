import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "live_canary_structural_pivot.py"
spec = importlib.util.spec_from_file_location("live_canary_structural_pivot_test_module", MODULE_PATH)
pivot = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(pivot)


def _blocked_payload():
    return pivot.build_live_canary_structural_pivot(
        live_predict_probe={
            "deployment_blocker": "circuit_breaker_active",
            "current_live_structure_bucket": "BLOCK|bear_bias200_hard_block|q00",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "support_route_verdict": "exact_bucket_unsupported_block",
            "support_governance_route": "exact_live_lane_proxy_available",
            "support_progress": {
                "delta_vs_previous": None,
                "stagnant_run_count": 0,
                "semantic_signature_delta_vs_previous": 0,
                "semantic_signature_stagnant_run_count": 2,
            },
            "deployment_blocker_details": {
                "release_condition": {
                    "release_ready": False,
                    "current_streak": 54,
                    "recent_window": 50,
                    "current_recent_window_wins": 0,
                    "required_recent_window_wins": 15,
                    "additional_recent_window_wins_needed": 15,
                }
            },
        },
        circuit_breaker_audit={
            "release_condition": {
                "release_ready": False,
                "current_streak": 54,
                "recent_window": 50,
                "current_recent_window_wins": 0,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 15,
            }
        },
        high_conviction_topk_oos_matrix={
            "risk_qualified_rows": 6,
            "runtime_blocked_candidate_rows": 6,
            "deployable_rows": 0,
            "nearest_deployable_rows": [
                {
                    "model": "logistic_regression",
                    "top_k": "top_2pct",
                    "win_rate": 0.8621,
                    "oos_roi": 0.9324,
                    "profit_factor": 19.8864,
                    "max_drawdown": 0.022,
                    "worst_fold": 0.2068,
                    "trade_count": 58,
                    "deployment_candidate_tier": "runtime_blocked_oos_pass",
                    "deployable_verdict": "not_deployable",
                }
            ],
        },
        execution_metadata_smoke={
            "runtime_ready": False,
            "readiness_state": "blocked_until_runtime_lifecycle_proof",
            "venues": [{"venue": "okx", "runtime_ready": False, "credentials_configured": False, "proof_state": "public_metadata_only"}],
        },
        customer_safe_alternative_proof={},
        q15_support_fill_feasibility={
            "verdict": {
                "current_exact_bucket_rows": 0,
                "minimum_support_rows": 50,
                "gap_to_minimum": 50,
                "time_to_evidence_bucket": "unknown_until_bucket_map_or_signal_redesign",
                "missing_capability_class": "Map/Signal",
                "alternative_solution_required": True,
            }
        },
        config_snapshot={
            "config_path": "config.yaml",
            "exists": True,
            "execution_mode": "paper",
            "enable_live_trading": False,
            "live_canary_enabled": False,
            "allowed_symbols_configured": False,
            "max_base_qty_by_symbol_configured": False,
            "policy_ready": False,
            "credential_values_redacted": True,
        },
        generated_at="2026-05-23T04:00:00Z",
    )


def test_live_canary_pivot_refreshes_current_zero_truth_and_names_one_primary_gate():
    payload = _blocked_payload()

    truth = payload["current_truth"]
    assert truth["support_rows"] == 0
    assert truth["minimum_support_rows"] == 50
    assert truth["support_gap"] == 50
    assert truth["recent_window_wins"] == 0
    assert truth["additional_recent_window_wins_needed"] == 15
    assert truth["deployable_rows"] == 0
    assert truth["venue_runtime_ready"] is False
    assert truth["live_canary_policy_ready"] is False
    assert truth["nearest_candidate"]["max_drawdown"] == 0.022
    assert truth["nearest_candidate"]["profit_factor"] == 19.8864
    assert truth["nearest_candidate"]["deployment_candidate_tier"] == "runtime_blocked_oos_pass"
    assert truth["support_delta_vs_previous"] == 0
    assert truth["semantic_signature_delta_vs_previous"] == 0
    assert truth["semantic_signature_stagnant_run_count"] == 2

    gate = payload["micro_canary_gate"]
    assert gate["micro_canary_ready"] is False
    assert gate["live_exposure_allowed"] is False
    assert gate["order_submission_enabled"] is False
    assert gate["single_failed_gate_for_72h_decision"] == "current_live_support_gate"
    assert "circuit_breaker_gate" in gate["supplementary_blockers_not_used_as_single_gate"]
    assert "venue_lifecycle_gate" in gate["supplementary_blockers_not_used_as_single_gate"]

    decision = payload["structural_decision"]
    assert decision["single_failed_gate_for_72h_decision"] == "current_live_support_gate"
    assert "q15_support_fill_feasibility" in decision["next_validation_artifact"]

    lanes = {lane["lane"]: lane for lane in payload["lanes"]}
    assert lanes["B_model_shadow_to_decision"]["can_start_now"] is True
    assert lanes["B_model_shadow_to_decision"]["live_exposure"] == "paper_shadow_only"
    assert lanes["C_strategy_micro_canary"]["can_start_now"] is False
    assert lanes["D_map_signal_redesign_for_current_bucket"]["status"] == "required"
    assert lanes["D_map_signal_redesign_for_current_bucket"]["semantic_signature_delta_vs_previous"] == 0


def test_live_canary_pivot_requires_all_gates_before_order_submission():
    payload = pivot.build_live_canary_structural_pivot(
        live_predict_probe={
            "deployment_blocker": None,
            "current_live_structure_bucket": "ALLOW|trend|q65",
            "current_live_structure_bucket_rows": 55,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 0,
            "support_route_verdict": "exact_bucket_supported",
            "support_governance_route": "exact_bucket_supported",
            "support_route_deployable": True,
        },
        circuit_breaker_audit={"release_condition": {"release_ready": True, "recent_window": 50, "current_recent_window_wins": 18, "required_recent_window_wins": 15, "additional_recent_window_wins_needed": 0}},
        high_conviction_topk_oos_matrix={"risk_qualified_rows": 3, "runtime_blocked_candidate_rows": 0, "deployable_rows": 1},
        execution_metadata_smoke={
            "runtime_ready": True,
            "venues": [{"venue": "okx", "runtime_ready": True, "credentials_configured": True, "proof_state": "runtime_backed_proof_complete"}],
        },
        customer_safe_alternative_proof={},
        q15_support_fill_feasibility={"verdict": {"current_exact_bucket_rows": 55, "minimum_support_rows": 50, "gap_to_minimum": 0}},
        config_snapshot={
            "config_path": "config.yaml",
            "exists": True,
            "execution_mode": "live_canary",
            "enable_live_trading": True,
            "live_canary_enabled": True,
            "allowed_symbols_configured": True,
            "max_base_qty_by_symbol_configured": True,
            "policy_ready": True,
            "credential_values_redacted": True,
        },
        generated_at="2026-05-23T04:00:00Z",
    )

    gate = payload["micro_canary_gate"]
    assert gate["micro_canary_ready"] is True
    assert gate["single_failed_gate_for_72h_decision"] == "none"
    assert gate["order_submission_enabled"] is True
    assert gate["supplementary_blockers_not_used_as_single_gate"] == []
    assert payload["hard_no_go_now"]["order_submission_enabled"] is True


def test_live_canary_markdown_is_operator_safe_and_secret_redacted():
    payload = _blocked_payload()
    md = pivot.markdown(payload)

    assert "Live canary structural pivot" in md
    assert "single_failed_gate_for_72h_decision" in md
    assert "current_live_support_gate" in md
    assert "support: `0/50`" in md
    assert "semantic-signature progress" in md
    assert "recent wins `0/50`" in md
    assert "order_submission_enabled: **False**" in md
    assert "credential_values_redacted: `True`" in md
    assert "[REDACTED]" not in md  # markdown uses secret-safe booleans, not credential placeholders
    assert "api_secret" not in md.lower()
    assert "passphrase" not in md.lower()
