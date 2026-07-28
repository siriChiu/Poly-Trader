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
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q35",
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
    assert gate["single_failed_gate_for_72h_decision"] == "circuit_breaker_gate"
    assert "current_live_support_gate" in gate["supplementary_blockers_not_used_as_single_gate"]
    assert "venue_lifecycle_gate" in gate["supplementary_blockers_not_used_as_single_gate"]
    assert payload["quick_read"]["micro_canary_ready"] is False
    assert payload["quick_read"]["single_failed_gate_for_72h_decision"] == "circuit_breaker_gate"
    assert payload["quick_read"]["next_validation_artifact"] == payload["structural_decision"]["next_validation_artifact"]
    assert payload["micro_canary_ready"] is False
    assert payload["single_failed_gate"] == "circuit_breaker_gate"
    assert payload["single_failed_gate_for_72h_decision"] == "circuit_breaker_gate"
    assert payload["order_submission_enabled"] is False
    assert payload["current_live_structure_bucket"] == "CAUTION|base_caution_regime_or_bias|q35"
    assert payload["support_rows"] == 0
    assert payload["minimum_support_rows"] == 50
    assert payload["support_gap"] == 50

    decision = payload["structural_decision"]
    assert decision["single_failed_gate_for_72h_decision"] == "circuit_breaker_gate"
    assert "circuit_breaker_audit" in decision["next_validation_artifact"]
    assert "Scanned q15 support identity" not in decision["next_validation_artifact"]

    lanes = {lane["lane"]: lane for lane in payload["lanes"]}
    assert lanes["B_model_shadow_to_decision"]["can_start_now"] is True
    assert lanes["B_model_shadow_to_decision"]["live_exposure"] == "paper_shadow_only"
    assert lanes["C_strategy_micro_canary"]["can_start_now"] is False
    assert lanes["D_map_signal_redesign_for_current_bucket"]["status"] == "required"
    assert "q15_support_fill_feasibility" in lanes["D_map_signal_redesign_for_current_bucket"]["next_artifact"]
    assert "CAUTION|base_caution_regime_or_bias|q35" in lanes["D_map_signal_redesign_for_current_bucket"]["next_artifact"]
    assert lanes["D_map_signal_redesign_for_current_bucket"]["semantic_signature_delta_vs_previous"] == 0


def test_live_canary_map_signal_lane_is_required_for_under_minimum_nonzero_support():
    payload = pivot.build_live_canary_structural_pivot(
        live_predict_probe={
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
            "current_live_structure_bucket_rows": 7,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 43,
            "support_route_verdict": "exact_bucket_present_but_below_minimum",
            "support_governance_route": "exact_live_bucket_present_but_below_minimum",
            "support_progress": {
                "delta_vs_previous": 0,
                "stagnant_run_count": 5,
                "semantic_signature_delta_vs_previous": 0,
                "semantic_signature_stagnant_run_count": 6,
            },
        },
        circuit_breaker_audit={"release_condition": {"release_ready": True, "recent_window": 50, "current_recent_window_wins": 49, "required_recent_window_wins": 15, "additional_recent_window_wins_needed": 0}},
        high_conviction_topk_oos_matrix={"risk_qualified_rows": 6, "runtime_blocked_candidate_rows": 6, "deployable_rows": 0},
        execution_metadata_smoke={"runtime_ready": False, "venues": [{"venue": "okx", "runtime_ready": False, "credentials_configured": False}]},
        customer_safe_alternative_proof={},
        q15_support_fill_feasibility={"verdict": {"current_exact_bucket_rows": 7, "minimum_support_rows": 50, "gap_to_minimum": 43}},
        q15_support_audit={
            "equilibrium_deadlock": {
                "verdict": "equilibrium_deadlock_confirmed",
                "confirmed": True,
                "forced_research_action_artifact": {
                    "required": True,
                    "output_path": "data/equilibrium_deadlock_research_action.json",
                },
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

    lane = {item["lane"]: item for item in payload["lanes"]}["D_map_signal_redesign_for_current_bucket"]
    assert payload["current_truth"]["support_rows"] == 7
    assert payload["current_truth"]["support_gap"] == 43
    assert lane["can_start_now"] is True
    assert lane["status"] == "equilibrium_deadlock_required"
    assert lane["equilibrium_deadlock_confirmed"] is True
    assert lane["forced_research_action_required"] is True
    assert lane["forced_research_action_output_path"] == "data/equilibrium_deadlock_research_action.json"
    assert payload["current_truth"]["equilibrium_deadlock_confirmed"] is True
    assert payload["structural_decision"]["forced_research_action_required"] is True
    assert "below minimum" in lane["goal"]
    assert "0/50" not in lane["goal"]


def test_live_canary_map_signal_lane_names_forced_research_action_without_confirmed_deadlock():
    payload = pivot.build_live_canary_structural_pivot(
        live_predict_probe={
            "deployment_blocker": "circuit_breaker_active",
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
            "current_live_structure_bucket_rows": 6,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 44,
            "support_route_verdict": "exact_bucket_present_but_below_minimum",
            "support_governance_route": "exact_live_bucket_present_but_below_minimum",
            "support_progress": {
                "delta_vs_previous": -18,
                "stagnant_run_count": 0,
                "semantic_signature_delta_vs_previous": -1,
                "semantic_signature_stagnant_run_count": 0,
            },
        },
        circuit_breaker_audit={"release_condition": {"release_ready": False, "recent_window": 50, "current_recent_window_wins": 0, "required_recent_window_wins": 15, "additional_recent_window_wins_needed": 15}},
        high_conviction_topk_oos_matrix={"risk_qualified_rows": 6, "runtime_blocked_candidate_rows": 6, "deployable_rows": 0},
        execution_metadata_smoke={"runtime_ready": False, "venues": [{"venue": "okx", "runtime_ready": False, "credentials_configured": False}]},
        customer_safe_alternative_proof={},
        q15_support_fill_feasibility={"verdict": {"current_exact_bucket_rows": 6, "minimum_support_rows": 50, "gap_to_minimum": 44}},
        q15_support_audit={
            "equilibrium_deadlock": {
                "verdict": "equilibrium_deadlock_watch",
                "confirmed": False,
                "forced_research_action_artifact": {
                    "required": True,
                    "output_path": "data/equilibrium_deadlock_research_action.json",
                },
            }
        },
        config_snapshot={
            "config_path": "config.yaml",
            "exists": True,
            "execution_mode": "paper",
            "enable_live_trading": False,
            "live_canary_enabled": False,
            "allowed_symbols_configured": True,
            "max_base_qty_by_symbol_configured": True,
            "policy_ready": False,
            "credential_values_redacted": True,
        },
        generated_at="2026-06-03T04:00:00Z",
    )

    lane = {item["lane"]: item for item in payload["lanes"]}["D_map_signal_redesign_for_current_bucket"]

    assert lane["can_start_now"] is True
    assert lane["status"] == "forced_research_action_required"
    assert lane["forced_research_action_required"] is True
    assert lane["equilibrium_deadlock_confirmed"] is False


def test_live_canary_pivot_marks_block_bucket_as_no_trade_lane_audit():
    payload = pivot.build_live_canary_structural_pivot(
        live_predict_probe={
            "deployment_blocker": "circuit_breaker_active",
            "signal": "CIRCUIT_BREAKER",
            "should_trade": False,
            "regime_gate": "BLOCK",
            "allowed_layers_raw": 0,
            "allowed_layers": 0,
            "current_live_structure_bucket": "BLOCK|bias200_below_min|q00",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "support_route_verdict": "exact_bucket_unsupported_block",
            "support_governance_route": "exact_live_lane_proxy_available",
            "support_progress": {
                "delta_vs_previous": 0,
                "stagnant_run_count": 2,
                "semantic_signature_delta_vs_previous": 0,
                "semantic_signature_stagnant_run_count": 2,
            },
        },
        circuit_breaker_audit={"release_condition": {"release_ready": False, "recent_window": 50, "current_recent_window_wins": 6, "required_recent_window_wins": 15, "additional_recent_window_wins_needed": 9}},
        high_conviction_topk_oos_matrix={"risk_qualified_rows": 6, "runtime_blocked_candidate_rows": 6, "deployable_rows": 0},
        execution_metadata_smoke={"runtime_ready": False, "venues": [{"venue": "okx", "runtime_ready": False, "credentials_configured": False}]},
        customer_safe_alternative_proof={},
        q15_support_fill_feasibility={"verdict": {"current_exact_bucket_rows": 0, "minimum_support_rows": 50, "gap_to_minimum": 50}},
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
        generated_at="2026-06-03T04:00:00Z",
    )

    truth = payload["current_truth"]
    decision = payload["structural_decision"]
    lane = {item["lane"]: item for item in payload["lanes"]}["D_map_signal_redesign_for_current_bucket"]

    assert truth["current_lane_actionability"] == "no_trade_block_lane"
    assert truth["support_evidence_role"] == "no_trade_decision_validation_not_deployable_support"
    assert decision["map_signal_forced_lane"] == "no_trade_lane_audit"
    assert "data/no_trade_lane_replay.json" in decision["map_signal_next_validation_artifact"]
    assert lane["can_start_now"] is True
    assert lane["status"] == "no_trade_lane_audit_required"
    assert lane["support_evidence_role"] == "no_trade_decision_validation_not_deployable_support"
    assert "buy/add deployment support" in lane["goal"] or "買入 / 加倉部署" in lane["goal"]
    assert payload["micro_canary_gate"]["single_failed_gate_for_72h_decision"] == "circuit_breaker_gate"


def test_live_canary_no_trade_lane_interpretation_uses_current_nonzero_support_rows():
    payload = pivot.build_live_canary_structural_pivot(
        live_predict_probe={
            "deployment_blocker": "circuit_breaker_active",
            "signal": "CIRCUIT_BREAKER",
            "should_trade": False,
            "regime_gate": "CAUTION",
            "allowed_layers_raw": 0,
            "allowed_layers": 0,
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
            "current_live_structure_bucket_rows": 26,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 24,
            "support_route_verdict": "exact_bucket_present_but_below_minimum",
            "support_governance_route": "exact_live_bucket_present_but_below_minimum",
        },
        circuit_breaker_audit={
            "release_condition": {
                "release_ready": False,
                "recent_window": 50,
                "current_recent_window_wins": 0,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 15,
            }
        },
        high_conviction_topk_oos_matrix={
            "risk_qualified_rows": 0,
            "runtime_blocked_candidate_rows": 0,
            "deployable_rows": 0,
        },
        execution_metadata_smoke={
            "runtime_ready": False,
            "venues": [
                {
                    "venue": "okx",
                    "runtime_ready": False,
                    "credentials_configured": False,
                }
            ],
        },
        customer_safe_alternative_proof={},
        q15_support_fill_feasibility={
            "verdict": {
                "current_exact_bucket_rows": 26,
                "minimum_support_rows": 50,
                "gap_to_minimum": 24,
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
        generated_at="2026-07-23T22:57:00Z",
    )

    interpretation = payload["current_truth"]["operator_interpretation"]
    assert "26/50" in interpretation
    assert "0/50 exact support" not in interpretation
    assert "不可視為買入 / 加倉部署 closure" in interpretation


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
    assert payload["quick_read"]["micro_canary_ready"] is True
    assert payload["quick_read"]["single_failed_gate"] == "none"
    assert payload["quick_read"]["order_submission_enabled"] is True
    assert payload["single_failed_gate_for_72h_decision"] == "none"
    assert payload["live_exposure_allowed"] is True
    assert payload["risk_on_order_enabled"] is True


def test_live_canary_markdown_is_operator_safe_and_secret_redacted():
    payload = _blocked_payload()
    md = pivot.markdown(payload)

    assert "Live canary structural pivot" in md
    assert "single_failed_gate_for_72h_decision" in md
    assert "circuit_breaker_gate" in md
    assert "current_live_support_gate" in md
    assert "support: `0/50`" in md
    assert "semantic-signature progress" in md
    assert "recent wins `0/50`" in md
    assert "order_submission_enabled: **False**" in md
    assert "credential_values_redacted: `True`" in md
    assert "[REDACTED]" not in md  # markdown uses secret-safe booleans, not credential placeholders
    assert "api_secret" not in md.lower()
    assert "passphrase" not in md.lower()
