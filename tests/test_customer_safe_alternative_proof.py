import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "customer_safe_alternative_proof.py"
spec = importlib.util.spec_from_file_location("customer_safe_alternative_proof_test_module", MODULE_PATH)
proof = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(proof)


def test_customer_safe_proof_preserves_fail_closed_live_gate_with_shadow_candidate():
    live_probe = {
        "deployment_blocker": "unsupported_exact_live_structure_bucket",
        "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q35",
        "current_live_structure_bucket_rows": 0,
        "minimum_support_rows": 50,
        "current_live_structure_bucket_gap_to_minimum": 50,
        "support_route_verdict": "exact_bucket_unsupported_block",
        "support_governance_route": "exact_live_lane_proxy_available",
    }
    support_fill = {
        "support_identity": {"current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q35"},
        "verdict": {
            "classification": "semantic_window_gap_not_raw_backfill_gap",
            "current_exact_bucket_rows": 0,
            "minimum_support_rows": 50,
            "gap_to_minimum": 50,
            "alternative_solution_required": True,
            "shadow_or_paper_allowed": True,
            "time_to_evidence_bucket": "semantic_rebaseline_review_required_before_reference_rows_count",
            "missing_capability_class": "Constraint/Review",
        },
    }
    topk = {
        "artifact_freshness_status": "fresh",
        "risk_qualified_rows": 6,
        "runtime_blocked_candidate_rows": 6,
        "deployable_rows": 0,
        "nearest_deployable_rows": [
            {
                "model": "logistic_regression",
                "feature_profile": "current_full",
                "regime": "all",
                "top_k": "top_2pct",
                "win_rate": 0.86,
                "oos_roi": 0.93,
                "profit_factor": 19.88,
                "max_drawdown": 0.022,
                "worst_fold": 0.2068,
                "trade_count": 58,
                "deployment_candidate_tier": "runtime_blocked_oos_pass",
                "oos_gate_passed": True,
                "blocked_only_by_live_guardrails": True,
                "gate_failures": ["support_route_not_deployable", "deployment_blocker_active"],
                "live_gate_failures": ["support_route_not_deployable"],
                "support_route": "exact_bucket_unsupported_block",
                "support_governance_route": "exact_live_lane_proxy_available",
                "support_route_deployable": False,
                "deployment_blocker": "circuit_breaker_active",
                "runtime_closure_state": "circuit_breaker_active",
                "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q35",
                "current_live_structure_bucket_rows": 0,
                "minimum_support_rows": 50,
                "current_live_structure_bucket_gap_to_minimum": 50,
                "release_ready": False,
                "current_recent_window_wins": 0,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 15,
                "deployable_verdict": "not_deployable",
            }
        ],
    }
    execution_smoke = {
        "runtime_ready": False,
        "readiness_state": "blocked_until_runtime_lifecycle_proof",
        "runtime_ready_blockers": ["live exchange credential 尚未驗證"],
        "venues": [
            {
                "venue": "okx",
                "adapter_supported": True,
                "enabled_in_config": True,
                "credentials_configured": False,
                "proof_state": "public_metadata_only",
                "runtime_ready": False,
                "blockers": ["order ack lifecycle 尚未驗證"],
            }
        ],
    }

    payload = proof.build_customer_safe_alternative_proof(
        live_predict_probe=live_probe,
        q15_support_fill_feasibility=support_fill,
        high_conviction_topk_oos_matrix=topk,
        execution_metadata_smoke=execution_smoke,
        recent_drift_report={},
        generated_at="2026-05-20T14:00:00Z",
    )

    gate = payload["live_deployment_gate"]
    assert gate["canary_ready"] is False
    assert gate["live_exposure_allowed"] is False
    assert gate["order_submission_enabled"] is False
    assert gate["risk_on_order_enabled"] is False
    assert gate["blocking_gate"] == "current_live_support_gate"

    support = payload["current_live_support"]
    assert support["current_rows"] == 0
    assert support["minimum_support_rows"] == 50
    assert support["gap_to_minimum"] == 50
    assert support["support_route_deployable"] is False

    nearest = payload["topk_shadow_candidate_context"]["nearest_candidate"]
    assert nearest["model"] == "logistic_regression"
    assert nearest["feature_profile"] == "current_full"
    assert nearest["regime"] == "all"
    assert nearest["profit_factor"] == 19.88
    assert nearest["max_drawdown"] == 0.022
    assert nearest["worst_fold"] == 0.2068
    assert nearest["trade_count"] == 58
    assert nearest["deployment_candidate_tier"] == "runtime_blocked_oos_pass"
    assert nearest["gate_failures"] == ["support_route_not_deployable", "deployment_blocker_active"]
    assert nearest["support_route_deployable"] is False
    assert nearest["release_ready"] is False

    lanes = {lane["id"]: lane for lane in payload["customer_safe_lanes"]}
    assert lanes["paper_shadow_decision_support_sleeve"]["status"] == "available"
    assert lanes["paper_shadow_decision_support_sleeve"]["deployable"] is False
    assert lanes["paper_shadow_decision_support_sleeve"]["live_exposure_allowed"] is False
    assert lanes["paper_shadow_decision_support_sleeve"]["order_submission_enabled"] is False
    assert lanes["venue_dry_run_readiness_proof"]["status"] == "blocked_missing_runtime_backed_proof"
    assert lanes["venue_dry_run_readiness_proof"]["credential_values_redacted"] is True

    portfolio = payload["alternative_solution_portfolio"]
    assert portfolio["pm_challenge_answered"] is True
    assert portfolio["option_count"] >= 3
    assert portfolio["time_to_evidence_bucket"] == "semantic_rebaseline_review_required_before_reference_rows_count"
    assert portfolio["missing_capability_class"] == "Constraint/Review"
    for option in portfolio["options"]:
        assert option["deployable"] is False
        assert option["live_exposure_allowed"] is False
        assert option["order_submission_enabled"] is False
        assert option["risk_on_order_enabled"] is False

    assert any("透過 /api/trade shadow_buy / paper_buy 強制 dry-run" in item for item in payload["allowed_today"])
    assert "真實/live 買入 / 加倉" in payload["not_allowed"]
    assert payload["fail_closed_invariants"]["paper_shadow_is_not_live_deployability"] is True
    assert payload["pm_handoff_carried_forward"]["selected_customer_safe_lane"] == "paper_shadow_decision_support_sleeve"


def test_customer_safe_proof_prioritizes_active_circuit_breaker_before_support_model_venue():
    payload = proof.build_customer_safe_alternative_proof(
        live_predict_probe={
            "deployment_blocker": "circuit_breaker_active",
            "runtime_closure_state": "circuit_breaker_active",
            "current_live_structure_bucket": "BLOCK|bear_bias200_hard_block|q15",
            "current_live_structure_bucket_rows": 50,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 0,
            "support_route_verdict": "exact_bucket_supported",
            "support_governance_route": "exact_live_bucket_supported",
            "deployment_blocker_details": {
                "support_route_deployable": True,
                "release_condition": {
                    "recent_window": 50,
                    "current_recent_window_wins": 4,
                    "required_recent_window_wins": 15,
                    "additional_recent_window_wins_needed": 11,
                    "release_ready": False,
                },
            },
        },
        q15_support_fill_feasibility={"verdict": {"current_exact_bucket_rows": 50, "minimum_support_rows": 50, "gap_to_minimum": 0}},
        high_conviction_topk_oos_matrix={"deployable_rows": 1, "risk_qualified_rows": 2, "runtime_blocked_candidate_rows": 0},
        execution_metadata_smoke={
            "runtime_ready": True,
            "readiness_state": "ready",
            "venues": [{"venue": "okx", "runtime_ready": True, "credentials_configured": True, "proof_state": "runtime_backed_proof_complete"}],
        },
        recent_drift_report={},
        generated_at="2026-05-20T14:00:00Z",
    )

    gate = payload["live_deployment_gate"]
    assert gate["support_ready"] is True
    assert gate["topk_deployable"] is True
    assert gate["venue_runtime_ready"] is True
    assert gate["circuit_breaker_ready"] is False
    assert gate["live_exposure_allowed"] is False
    assert gate["order_submission_enabled"] is False
    assert gate["primary_blocking_gate"] == "circuit_breaker_gate"
    assert gate["blocking_gates"] == ["circuit_breaker_gate"]
    breaker = payload["circuit_breaker_gate"]
    assert breaker["current_recent_window_wins"] == 4
    assert breaker["required_recent_window_wins"] == 15
    assert breaker["additional_recent_window_wins_needed"] == 11
    assert payload["fail_closed_invariants"]["circuit_breaker_blocks_live_until_release_condition_met"] is True
    md = proof.markdown(payload)
    assert "primary_blocking_gate: `circuit_breaker_gate`" in md
    assert "circuit_breaker_release_ready: `False`" in md


def test_customer_safe_proof_falls_back_to_circuit_breaker_audit_release_math():
    payload = proof.build_customer_safe_alternative_proof(
        live_predict_probe={
            "deployment_blocker": "unsupported_exact_live_structure_bucket",
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q35",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "support_route_verdict": "exact_bucket_unsupported_block",
        },
        circuit_breaker_audit={
            "release_condition": {
                "release_ready": True,
                "recent_window": 50,
                "current_recent_window_wins": 50,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 0,
            }
        },
        q15_support_fill_feasibility={"verdict": {"current_exact_bucket_rows": 0, "minimum_support_rows": 50, "gap_to_minimum": 50}},
        high_conviction_topk_oos_matrix={"risk_qualified_rows": 6, "runtime_blocked_candidate_rows": 6, "deployable_rows": 0},
        execution_metadata_smoke={"runtime_ready": False},
        recent_drift_report={},
        generated_at="2026-05-24T10:00:00Z",
    )

    breaker = payload["circuit_breaker_gate"]
    assert breaker["release_ready"] is True
    assert breaker["current_recent_window_wins"] == 50
    assert breaker["required_recent_window_wins"] == 15
    assert breaker["additional_recent_window_wins_needed"] == 0
    assert payload["live_deployment_gate"]["blocking_gate"] == "current_live_support_gate"
    md = proof.markdown(payload)
    assert "circuit_breaker_release_ready: `True` (wins `50/15`, gap `0`)" in md
    assert "wins `None/None`" not in md


def test_customer_safe_proof_reads_nested_recent_shadow_falsification_without_deploying():
    payload = proof.build_customer_safe_alternative_proof(
        live_predict_probe={
            "deployment_blocker": "circuit_breaker_active",
            "current_live_structure_bucket": "BLOCK|bear_bias200_hard_block|q00",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "support_route_verdict": "exact_bucket_unsupported_block",
        },
        q15_support_fill_feasibility={"verdict": {"classification": "no_exact_bucket_history"}},
        high_conviction_topk_oos_matrix={"risk_qualified_rows": 6, "runtime_blocked_candidate_rows": 6, "deployable_rows": 0},
        execution_metadata_smoke={"runtime_ready": False},
        recent_drift_report={
            "primary_window": {"window": "100", "win_rate": 0.24, "dominant_regime": "chop", "alerts": ["regime_shift"]},
            "canonical_tail_root_cause": {
                "no_new_risk_shadow_replay": {
                    "mode": "shadow_only_no_new_risk_falsification",
                    "deployable": False,
                    "order_submission_enabled": False,
                    "baseline": {"rows": 100, "win_rate": 0.24},
                    "best_gate": {
                        "id": "dominant_regime_shadow_gate",
                        "kept_rows": 6,
                        "kept_win_rate": 0.8333,
                        "loss_capture_share": 0.9868,
                        "summary": {"operator_message": "僅限 paper/shadow；不可送單"},
                    },
                }
            },
        },
        generated_at="2026-05-20T14:00:00Z",
    )

    recent = payload["recent_window_context"]
    assert recent["latest_window"] == "100"
    assert recent["win_rate"] == 0.24
    assert recent["dominant_regime"] == "chop"
    assert recent["shadow_falsification_mode"] == "shadow_only_no_new_risk_falsification"
    assert recent["shadow_falsification_best_gate"] == "dominant_regime_shadow_gate"
    assert recent["shadow_falsification_kept_rows"] == 6
    assert recent["shadow_falsification_kept_win_rate"] == 0.8333
    assert recent["shadow_falsification_deployable"] is False
    assert recent["shadow_falsification_order_submission_enabled"] is False

    lanes = {lane["id"]: lane for lane in payload["customer_safe_lanes"]}
    falsification = lanes["recent_window_no_new_risk_falsification"]
    assert falsification["status"] == "shadow_only_no_new_risk_falsification"
    assert falsification["deployable"] is False
    assert falsification["order_submission_enabled"] is False

    portfolio = payload["alternative_solution_portfolio"]
    assert portfolio["evidence_summary"]["recent_shadow_mode"] == "shadow_only_no_new_risk_falsification"
    md = proof.markdown(payload)
    assert "recent_window_no_new_risk_falsification" in md
    assert "只限影子驗證；不可送單" in md
    assert "shadow_only_no_new_risk_falsification" not in md


def test_customer_safe_proof_selects_best_runtime_gate_from_recent_replay_list():
    payload = proof.build_customer_safe_alternative_proof(
        live_predict_probe={
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q35",
            "current_live_structure_bucket_rows": 1,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 49,
            "support_route_verdict": "exact_bucket_present_but_below_minimum",
        },
        q15_support_fill_feasibility={"verdict": {"classification": "semantic_window_gap_not_raw_backfill_gap"}},
        high_conviction_topk_oos_matrix={"risk_qualified_rows": 6, "runtime_blocked_candidate_rows": 6, "deployable_rows": 0},
        execution_metadata_smoke={"runtime_ready": False},
        recent_drift_report={
            "primary_window": {"window": "100", "summary": {"win_rate": 0.79, "dominant_regime": "bear"}, "alerts": ["regime_shift"]},
            "canonical_tail_root_cause": {
                "no_new_risk_shadow_replay": {
                    "mode": "shadow_only_no_new_risk_falsification",
                    "deployable": False,
                    "order_submission_enabled": False,
                    "baseline": {"rows": 100, "win_rate": 0.79},
                    "gates": [
                        {
                            "id": "outcome_tp_miss_high_underwater",
                            "runtime_candidate": False,
                            "uses_future_outcome_fields": True,
                            "falsification_verdict": "passes_shadow_metric_future_only",
                            "kept_rows": 67,
                            "kept_win_rate": 1.0,
                            "loss_capture_share": 1.0,
                        },
                        {
                            "id": "dominant_regime_shadow_gate",
                            "runtime_candidate": True,
                            "uses_future_outcome_fields": False,
                            "falsification_verdict": "inconclusive_all_rows_blocked",
                            "kept_rows": 0,
                            "kept_win_rate": None,
                            "loss_capture_share": 1.0,
                        },
                        {
                            "id": "observable_4h_shift_shadow_gate",
                            "runtime_candidate": True,
                            "uses_future_outcome_fields": False,
                            "falsification_verdict": "passes_shadow_metric",
                            "kept_rows": 71,
                            "kept_win_rate": 1.0,
                            "loss_capture_share": 1.0,
                        },
                    ],
                }
            },
        },
        generated_at="2026-05-24T13:10:00Z",
    )

    recent = payload["recent_window_context"]
    assert recent["shadow_falsification_best_gate"] == "observable_4h_shift_shadow_gate"
    assert recent["shadow_falsification_kept_rows"] == 71
    assert recent["shadow_falsification_kept_win_rate"] == 1.0
    assert recent["shadow_falsification_deployable"] is False
    assert recent["shadow_falsification_order_submission_enabled"] is False

    lanes = {lane["id"]: lane for lane in payload["customer_safe_lanes"]}
    falsification = lanes["recent_window_no_new_risk_falsification"]
    assert falsification["best_gate"] == "observable_4h_shift_shadow_gate"
    assert falsification["kept_rows"] == 71
    assert falsification["deployable"] is False
    assert falsification["order_submission_enabled"] is False
    md = proof.markdown(payload)
    assert "best_gate=4H 可觀測位移影子 gate" in md
    assert "observable_4h_shift_shadow_gate" not in md
    assert "outcome_tp_miss_high_underwater" not in md


def test_customer_safe_proof_reads_nested_primary_window_summary_before_loss_regime_fallback():
    payload = proof.build_customer_safe_alternative_proof(
        live_predict_probe={
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q35",
            "current_live_structure_bucket_rows": 3,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 47,
            "support_route_verdict": "exact_bucket_present_but_below_minimum",
        },
        q15_support_fill_feasibility={"verdict": {"classification": "semantic_rebaseline_under_minimum"}},
        high_conviction_topk_oos_matrix={"risk_qualified_rows": 6, "runtime_blocked_candidate_rows": 6, "deployable_rows": 0},
        execution_metadata_smoke={"runtime_ready": False},
        recent_drift_report={
            "primary_window": {
                "window": "100",
                "alerts": ["regime_shift"],
                "summary": {
                    "rows": 100,
                    "win_rate": 0.24,
                    "dominant_regime": "bear",
                    "dominant_regime_share": 0.58,
                    "quality_metrics": {"avg_simulated_quality": -0.12, "avg_simulated_pnl": -0.003, "avg_drawdown_penalty": 0.19},
                    "compact_summary": {
                        "window": 100,
                        "alerts": ["regime_shift", "constant_target"],
                        "severity": "high",
                        "interpretation": "distribution_pathology",
                        "win_rate": 0.24,
                        "avg_quality": -0.12,
                        "avg_pnl": -0.003,
                        "avg_drawdown_penalty": 0.19,
                        "dominant_regime": "bear",
                        "dominant_regime_share": 0.58,
                        "tail_streak": {"target": 0, "count": 42, "start_timestamp": "t0", "end_timestamp": "t1"},
                        "adverse_streak": {"target": 0, "count": 44, "start_timestamp": "t0", "end_timestamp": "t1"},
                        "top_shift_features": ["feat_rsi14", "feat_mind"],
                        "actionable_summary": "negative distribution pathology requires current-window validation",
                    },
                },
            },
            "canonical_tail_root_cause": {
                "dominant_loss_regime": "chop",
                "no_new_risk_shadow_replay": {
                    "mode": "shadow_only_no_new_risk_falsification",
                    "deployable": False,
                    "order_submission_enabled": False,
                    "baseline": {"rows": 100, "win_rate": 0.21},
                },
            },
        },
        generated_at="2026-05-24T01:10:00Z",
    )

    recent = payload["recent_window_context"]
    assert recent["latest_window"] == "100"
    assert recent["win_rate"] == 0.24
    assert recent["dominant_regime"] == "bear"
    assert recent["dominant_regime_share"] == 0.58
    assert recent["alerts"] == ["regime_shift", "constant_target"]
    assert recent["severity"] == "high"
    assert recent["interpretation"] == "distribution_pathology"
    assert recent["avg_quality"] == -0.12
    assert recent["avg_pnl"] == -0.003
    assert recent["avg_drawdown_penalty"] == 0.19
    assert recent["tail_streak"]["count"] == 42
    assert recent["top_shift_features"] == ["feat_rsi14", "feat_mind"]
    assert recent["actionable_summary"] == "negative distribution pathology requires current-window validation"
    assert recent["shadow_falsification_mode"] == "shadow_only_no_new_risk_falsification"
    md = proof.markdown(payload)
    assert "Recent-tail no-new-risk context" in md
    assert "tail_streak: target=`0` count=`42`" in md
    assert "top_shift_features: RSI14、趨勢偏離感測" in md
    assert "distribution_pathology" not in md
    assert "constant_target" not in md
    assert "feat_rsi14" not in md
    assert "feat_mind" not in md


def test_customer_safe_proof_requires_all_gates_before_canary():
    payload = proof.build_customer_safe_alternative_proof(
        live_predict_probe={
            "current_live_structure_bucket_rows": 50,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 0,
            "deployment_blocker": None,
            "support_route_verdict": "exact_bucket_supported",
            "support_governance_route": "exact_bucket_supported",
            "deployment_blocker_details": {"support_route_deployable": True},
        },
        q15_support_fill_feasibility={"verdict": {"current_exact_bucket_rows": 50, "minimum_support_rows": 50, "gap_to_minimum": 0}},
        high_conviction_topk_oos_matrix={"deployable_rows": 1, "risk_qualified_rows": 2, "runtime_blocked_candidate_rows": 0},
        execution_metadata_smoke={
            "runtime_ready": True,
            "readiness_state": "ready",
            "venues": [{"venue": "okx", "runtime_ready": True, "credentials_configured": True, "proof_state": "runtime_backed_proof_complete"}],
        },
        recent_drift_report={},
        generated_at="2026-05-20T14:00:00Z",
    )

    assert payload["live_deployment_gate"]["canary_ready"] is True
    assert payload["live_deployment_gate"]["live_exposure_allowed"] is True
    assert payload["live_deployment_gate"]["order_submission_enabled"] is True
    assert payload["live_deployment_gate"]["blocking_gate"] == "none"
    assert payload["current_live_support"]["deployment_blocker"] is None
    assert "exact support 達標" in payload["pm_handoff_carried_forward"]["decision"]
    assert "current exact support 已達標" in payload["next_gate"]
    assert "必須補齊" not in payload["next_gate"]
    # Even when all gates pass, the proof still documents that paper/shadow is not live deployability.
    assert payload["fail_closed_invariants"]["paper_shadow_is_not_live_deployability"] is True


def test_customer_safe_proof_does_not_resurrect_stale_support_blocker_after_support_closes():
    payload = proof.build_customer_safe_alternative_proof(
        live_predict_probe={
            "deployment_blocker": None,
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q15",
            "current_live_structure_bucket_rows": 117,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 0,
            "support_route_verdict": "exact_bucket_supported",
            "support_governance_route": "exact_live_bucket_supported",
        },
        q15_support_fill_feasibility={"verdict": {"current_exact_bucket_rows": 117, "minimum_support_rows": 50, "gap_to_minimum": 0}},
        high_conviction_topk_oos_matrix={"deployable_rows": 0, "risk_qualified_rows": 6, "runtime_blocked_candidate_rows": 6},
        execution_metadata_smoke={"runtime_ready": False, "readiness_state": "blocked_until_runtime_lifecycle_proof"},
        recent_drift_report={},
        generated_at="2026-05-20T14:00:00Z",
    )

    assert payload["current_live_support"]["deployment_blocker"] is None
    assert payload["current_live_support"]["support_route_deployable"] is True
    assert payload["live_deployment_gate"]["support_ready"] is True
    assert payload["live_deployment_gate"]["blocking_gate"] == "model_gate"
    assert payload["live_deployment_gate"]["live_exposure_allowed"] is False
    assert "current exact support 已達標" in payload["next_gate"]
    assert "必須補齊" not in payload["next_gate"]


def test_customer_safe_proof_prefers_live_reference_rows_over_stale_topk_context():
    payload = proof.build_customer_safe_alternative_proof(
        live_predict_probe={
            "deployment_blocker": "circuit_breaker_active",
            "current_live_structure_bucket": "BLOCK|bear_bias200_hard_block|q00",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "support_route_verdict": "exact_bucket_unsupported_block",
            "support_governance_route": "exact_live_lane_proxy_available",
            "support_governance_reference_evidence": {
                "support_governance_route": "exact_live_lane_proxy_available",
                "support_route_verdict": "exact_bucket_unsupported_block",
                "current_rows": 0,
                "minimum_support_rows": 50,
                "exact_live_lane_proxy_rows": 10,
                "reference_only": True,
            },
        },
        q15_support_fill_feasibility={"verdict": {"current_exact_bucket_rows": 0, "minimum_support_rows": 50, "gap_to_minimum": 50}},
        high_conviction_topk_oos_matrix={
            "deployable_rows": 0,
            "risk_qualified_rows": 6,
            "runtime_blocked_candidate_rows": 6,
            "support_context": {
                "support_governance_reference_evidence": {
                    "exact_live_lane_proxy_rows": 216,
                    "reference_only": True,
                }
            },
        },
        execution_metadata_smoke={"runtime_ready": False},
        recent_drift_report={},
        generated_at="2026-05-26T19:03:00Z",
    )

    support = payload["current_live_support"]
    assert support["reference_only_rows"] == 10
    assert support["support_governance_reference_evidence"]["exact_live_lane_proxy_rows"] == 10
    assert support["support_route_deployable"] is False


def test_customer_safe_markdown_names_handoff_and_forbidden_actions():
    payload = proof.build_customer_safe_alternative_proof(
        live_predict_probe={"current_live_structure_bucket_rows": 0, "minimum_support_rows": 50, "current_live_structure_bucket_gap_to_minimum": 50},
        q15_support_fill_feasibility={},
        high_conviction_topk_oos_matrix={"risk_qualified_rows": 6, "runtime_blocked_candidate_rows": 6, "deployable_rows": 0},
        execution_metadata_smoke={},
        recent_drift_report={},
        generated_at="2026-05-20T14:00:00Z",
    )
    md = proof.markdown(payload)
    assert "Customer-safe alternative proof" in md
    assert "PM handoff carried forward" in md
    assert "live_exposure_allowed: **False**" in md
    assert "買入 / 加倉" in md
    assert "paper_shadow_decision_support_sleeve" in md
    assert "Alternative solution option portfolio" in md
    assert "selected_next_artifact" in md
    assert "最近研究候選" in md
    assert "最大回撤=—" in md
    assert "runtime_blocked_oos_pass" not in md
    assert "not_deployable" not in md
