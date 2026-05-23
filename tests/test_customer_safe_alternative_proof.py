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

    assert "買入 / 加倉" in payload["not_allowed"]
    assert payload["fail_closed_invariants"]["paper_shadow_is_not_live_deployability"] is True
    assert payload["pm_handoff_carried_forward"]["selected_customer_safe_lane"] == "paper_shadow_decision_support_sleeve"


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
