from __future__ import annotations

from model.personal_release import (
    apply_runtime_release_policy,
    evaluate_candidate_release,
    resolve_personal_release_policy,
)
from model.runtime_closure import build_runtime_closure_state, build_runtime_closure_summary
from scripts.topk_walkforward_precision import build_high_conviction_oos_matrix_rows


APPROVAL_CONFIG = {
    "strategy_release": {
        "mode": "owner_approved_personal_use",
        "owner_approval": {
            "enabled": True,
            "decision_id": "poly-trader-personal-release-2026-07-19",
            "approved_by": "Kazuha",
            "selector": {
                "model": "logistic_regression",
                "feature_profile": "current_full",
                "regime": "all",
                "top_k": "top_1pct",
            },
            "statistical_gate_policy": "advisory_with_uncertainty_sizing",
            "max_layers_until_full_evidence": 1,
            "runtime_binding": {
                "verified": False,
                "model": "logistic_regression",
                "feature_profile": "current_full",
            },
        },
    }
}


def _policy(*, binding_verified: bool = False):
    config = {
        **APPROVAL_CONFIG,
        "strategy_release": {
            **APPROVAL_CONFIG["strategy_release"],
            "owner_approval": {
                **APPROVAL_CONFIG["strategy_release"]["owner_approval"],
                "runtime_binding": {
                    **APPROVAL_CONFIG["strategy_release"]["owner_approval"]["runtime_binding"],
                    "verified": binding_verified,
                },
            },
        },
    }
    return resolve_personal_release_policy(config)


def _candidate():
    return {
        "model": "logistic_regression",
        "feature_profile": "current_full",
        "regime": "all",
        "top_k": "top_1pct",
        "trade_count": 29,
        "wins": 20,
        "losses": 9,
        "win_rate": 0.6897,
        "oos_roi": 0.2465,
        "profit_factor": 4.3797,
        "max_drawdown": 0.0478,
        "worst_fold": 0.0994,
    }


def test_owner_approval_turns_sample_and_exact_support_gates_into_sizing_warnings():
    decision = evaluate_candidate_release(
        _candidate(),
        strict_failures=[
            "min_trades_not_met",
            "support_route_not_deployable",
            "deployment_blocker_active",
        ],
        support_context={
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "current_live_structure_bucket_rows": 34,
            "minimum_support_rows": 50,
        },
        policy=_policy(),
    )

    assert decision["strategy_release_status"] == "owner_approved_personal_use"
    assert decision["owner_approved"] is True
    assert decision["strategy_release_ready"] is True
    assert decision["hard_gate_failures"] == []
    assert set(decision["statistical_warnings"]) == {
        "min_trades_not_met",
        "support_route_not_deployable",
        "deployment_blocker_active",
    }
    assert decision["support_evidence_ratio"] == 0.68
    assert decision["model_evidence_ratio"] == 0.58
    assert decision["evidence_tier"] == "caution"
    assert decision["recommended_max_layers"] == 1
    assert decision["technical_execution_gates_required"] is True


def test_owner_approval_does_not_override_drawdown_or_negative_fold_hard_risk_failures():
    decision = evaluate_candidate_release(
        _candidate(),
        strict_failures=["min_trades_not_met", "max_drawdown_too_high", "worst_fold_negative"],
        support_context={"current_live_structure_bucket_rows": 34, "minimum_support_rows": 50},
        policy=_policy(),
    )

    assert decision["strategy_release_status"] == "owner_approval_blocked_by_hard_risk_gate"
    assert decision["strategy_release_ready"] is False
    assert decision["statistical_warnings"] == ["min_trades_not_met"]
    assert decision["hard_gate_failures"] == ["max_drawdown_too_high", "worst_fold_negative"]


def test_runtime_breaker_blocks_execution_without_revoking_owner_strategy_release():
    decision = evaluate_candidate_release(
        _candidate(),
        strict_failures=["min_trades_not_met", "deployment_blocker_active", "breaker_release_not_ready"],
        support_context={
            "deployment_blocker": "circuit_breaker_active",
            "current_live_structure_bucket_rows": 34,
            "minimum_support_rows": 50,
        },
        policy=_policy(),
    )

    assert decision["strategy_release_status"] == "owner_approved_personal_use"
    assert decision["strategy_release_ready"] is True
    assert decision["statistical_warnings"] == ["min_trades_not_met"]
    assert decision["hard_gate_failures"] == []
    assert decision["technical_execution_blockers"] == [
        "deployment_blocker_active",
        "breaker_release_not_ready",
    ]


def test_owner_approval_is_selector_scoped():
    candidate = _candidate()
    candidate["model"] = "xgboost"

    decision = evaluate_candidate_release(
        candidate,
        strict_failures=["min_trades_not_met"],
        support_context={},
        policy=_policy(),
    )

    assert decision["owner_approved"] is False
    assert decision["strategy_release_status"] == "strict_gates_apply"
    assert decision["hard_gate_failures"] == ["min_trades_not_met"]


def test_unverified_runtime_binding_replaces_waiting_with_actionable_technical_blocker():
    result = apply_runtime_release_policy(
        {
            "allowed_layers": 2,
            "allowed_layers_raw": 2,
            "allowed_layers_reason": "full_three_layers_allowed",
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "under_minimum_exact_live_structure_bucket",
        },
        {
            "type": "under_minimum_exact_live_structure_bucket",
            "reason": "wait for 50 rows",
            "current_live_structure_bucket_rows": 34,
            "minimum_support_rows": 50,
        },
        policy=_policy(binding_verified=False),
        runtime_identity={"model": "xgboost", "feature_profile": "current_full"},
    )

    assert result["strategy_release_status"] == "owner_approved_personal_use"
    assert result["statistical_gate_blocking"] is False
    assert result["deployment_blocker"] == "owner_approved_strategy_binding_required"
    assert result["allowed_layers"] == 0
    assert result["recommended_max_layers"] == 1
    assert result["evidence_tier"] == "caution"
    assert result["support_evidence_ratio"] == 0.68
    assert result["technical_execution_gates_required"] is True
    assert "under_minimum_exact_live_structure_bucket" in result["statistical_warnings"]
    assert "等待" not in result["deployment_blocker_reason"]


def test_verified_runtime_binding_opens_only_first_layer_and_keeps_support_as_warning():
    result = apply_runtime_release_policy(
        {
            "allowed_layers": 3,
            "allowed_layers_raw": 3,
            "allowed_layers_reason": "full_three_layers_allowed",
            "execution_guardrail_applied": True,
            "execution_guardrail_reason": "under_minimum_exact_live_structure_bucket",
        },
        {
            "type": "under_minimum_exact_live_structure_bucket",
            "reason": "wait for 50 rows",
            "current_live_structure_bucket_rows": 34,
            "minimum_support_rows": 50,
        },
        policy=_policy(binding_verified=True),
        runtime_identity={"model": "logistic_regression", "feature_profile": "current_full"},
    )

    assert result["strategy_release_status"] == "owner_approved_personal_use"
    assert result["deployment_blocker"] is None
    assert result["allowed_layers"] == 1
    assert result["allowed_layers_raw"] == 3
    assert result["allowed_layers_reason"] == "owner_approved_uncertainty_caps_first_layer"
    assert result["execution_guardrail_applied"] is False
    assert result["execution_guardrail_reason"] is None
    assert result["statistical_warnings"] == ["under_minimum_exact_live_structure_bucket"]


def test_owner_approval_never_overrides_circuit_breaker():
    result = apply_runtime_release_policy(
        {
            "allowed_layers": 3,
            "allowed_layers_raw": 3,
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
        },
        {"type": "circuit_breaker_active", "reason": "loss streak"},
        policy=_policy(binding_verified=False),
        runtime_identity={"model": "logistic_regression", "feature_profile": "current_full"},
    )

    assert result["deployment_blocker"] == "circuit_breaker_active"
    assert result["allowed_layers"] == 0
    assert result["strategy_release_status"] == "owner_approved_personal_use"
    assert result["technical_execution_gates_required"] is True
    assert result["technical_execution_blockers"] == ["circuit_breaker_active"]
    assert result["statistical_warnings"] == ["unsupported_exact_live_structure_bucket"]
    assert result["runtime_binding_verified"] is False
    assert result["evidence_tier"] == "limited"


def test_runtime_closure_explains_owner_release_without_waiting_copy():
    payload = {
        "strategy_release_status": "owner_approved_personal_use",
        "owner_approved": True,
        "deployment_blocker": None,
        "signal": "BUY",
        "allowed_layers": 1,
        "recommended_max_layers": 1,
        "current_live_structure_bucket_rows": 34,
        "minimum_support_rows": 50,
        "statistical_warnings": ["under_minimum_exact_live_structure_bucket"],
    }

    assert build_runtime_closure_state(payload) == "owner_approved_capacity_opened"
    summary = build_runtime_closure_summary(payload)
    assert summary is not None
    assert "個人使用" in summary
    assert "第一層" in summary
    assert "34/50" in summary
    assert "等待" not in summary


def test_topk_row_marks_owner_approved_release_without_claiming_live_deployability():
    report = {
        "aggregate_top_slices": {
            "top_1pct": {
                "oos_roi": 0.2465,
                "win_rate": 0.6897,
                "profit_factor": 4.3797,
                "max_drawdown": 0.0478,
                "trade_count": 29,
                "wins": 20,
                "losses": 9,
            }
        },
        "folds": [
            {"top_slices": {"top_1pct": {"oos_roi": 0.12}}},
            {"top_slices": {"top_1pct": {"oos_roi": 0.0994}}},
        ],
    }
    rows = build_high_conviction_oos_matrix_rows(
        "logistic_regression",
        report,
        support_context={
            "support_route_verdict": "exact_bucket_present_but_below_minimum",
            "support_route_deployable": False,
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "current_live_structure_bucket_rows": 34,
            "minimum_support_rows": 50,
            "release_ready": True,
        },
        feature_profile="current_full",
        release_policy=_policy(),
    )

    row = rows[0]
    assert row["strategy_release_status"] == "owner_approved_personal_use"
    assert row["strategy_release_ready"] is True
    assert row["deployment_candidate_tier"] == "owner_approved_personal_use"
    assert row["deployable_verdict"] == "not_live_deployable"
    assert row["recommended_max_layers"] == 1
    assert set(row["statistical_warnings"]) == {
        "min_trades_not_met",
        "support_route_not_deployable",
        "deployment_blocker_active",
    }
    assert row["hard_gate_failures"] == []
