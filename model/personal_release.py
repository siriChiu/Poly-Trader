from __future__ import annotations

"""Personal-use strategy release policy.

This module deliberately separates three concerns that were previously collapsed
into one binary deployment gate:

1. strict research statistics (kept for comparison and audit),
2. owner-approved personal-use release (warnings + bounded sizing), and
3. technical execution safety (breaker, model binding, venue, canary, permits).

Owner approval never authorizes a live adapter call by itself.
"""

from copy import deepcopy
from typing import Any, Mapping, Sequence

OWNER_APPROVED_MODE = "owner_approved_personal_use"
OWNER_APPROVED_STATUS = "owner_approved_personal_use"

_SUPPORT_ONLY_BLOCKERS = {
    "unsupported_exact_live_structure_bucket",
    "under_minimum_exact_live_structure_bucket",
}

_ADVISORY_FAILURES = {
    "min_trades_not_met",
    "support_route_not_deployable",
}

_TECHNICAL_EXECUTION_FAILURES = {
    "deployment_blocker_active",
    "breaker_release_not_ready",
    "runtime_binding_required",
}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _to_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _ratio(value: Any, minimum: Any) -> float:
    numerator = _to_int(value)
    denominator = _to_int(minimum)
    if numerator is None or denominator is None or denominator <= 0:
        return 0.0
    return round(min(max(numerator / denominator, 0.0), 1.0), 4)


def _unique(values: Sequence[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def resolve_personal_release_policy(config: Mapping[str, Any] | None) -> dict[str, Any]:
    root = _mapping(config)
    release = _mapping(root.get("strategy_release"))
    approval = _mapping(release.get("owner_approval"))
    selector = {_norm(key): _norm(value) for key, value in _mapping(approval.get("selector")).items() if _norm(value)}
    binding = _mapping(approval.get("runtime_binding"))
    mode = _norm(release.get("mode"))
    enabled = bool(approval.get("enabled")) and mode == OWNER_APPROVED_MODE

    max_layers = _to_int(approval.get("max_layers_until_full_evidence"))
    if max_layers is None:
        max_layers = 1
    max_layers = min(max(max_layers, 1), 3)

    min_trades = _to_int(approval.get("minimum_full_evidence_trades"))
    if min_trades is None or min_trades <= 0:
        min_trades = 50

    return {
        "enabled": enabled,
        "mode": mode or "strict",
        "decision_id": str(approval.get("decision_id") or "").strip() or None,
        "approved_by": str(approval.get("approved_by") or "").strip() or None,
        "selector": selector,
        "statistical_gate_policy": _norm(approval.get("statistical_gate_policy")) or "strict",
        "max_layers_until_full_evidence": max_layers,
        "minimum_full_evidence_trades": min_trades,
        "runtime_binding": {
            "verified": bool(binding.get("verified")),
            "model": _norm(binding.get("model") or selector.get("model")),
            "feature_profile": _norm(binding.get("feature_profile") or selector.get("feature_profile")),
            "artifact_path": str(binding.get("artifact_path") or "").strip() or None,
            "artifact_sha256": str(binding.get("artifact_sha256") or "").strip() or None,
        },
        "technical_execution_gates_required": True,
    }


def _selector_matches(candidate: Mapping[str, Any], policy: Mapping[str, Any]) -> bool:
    selector = _mapping(policy.get("selector"))
    if not selector:
        return False
    for key, expected in selector.items():
        if _norm(candidate.get(key)) != _norm(expected):
            return False
    return True


def _support_blocker(support_context: Mapping[str, Any]) -> str | None:
    blocker = _norm(support_context.get("deployment_blocker"))
    if blocker in _SUPPORT_ONLY_BLOCKERS:
        return blocker
    return None


def _failure_is_advisory(failure: str, support_context: Mapping[str, Any]) -> bool:
    if failure in _ADVISORY_FAILURES:
        if failure == "support_route_not_deployable":
            blocker = _norm(support_context.get("deployment_blocker"))
            route = _norm(support_context.get("support_route_verdict") or support_context.get("support_route"))
            return blocker in _SUPPORT_ONLY_BLOCKERS or route in {
                "exact_bucket_present_but_below_minimum",
                "exact_bucket_unsupported_block",
            }
        return True
    if failure == "deployment_blocker_active":
        return _support_blocker(support_context) is not None
    return False


def _failure_is_technical_execution(failure: str, support_context: Mapping[str, Any]) -> bool:
    if failure not in _TECHNICAL_EXECUTION_FAILURES:
        return False
    if failure == "deployment_blocker_active":
        return _support_blocker(support_context) is None
    return True


def _evidence_tier(support_ratio: float, model_ratio: float) -> str:
    evidence_score = (0.5 * support_ratio) + (0.5 * model_ratio)
    if support_ratio >= 1.0 and model_ratio >= 1.0:
        return "full"
    if evidence_score >= 0.5:
        return "caution"
    return "limited"


def evaluate_candidate_release(
    candidate: Mapping[str, Any],
    *,
    strict_failures: Sequence[Any],
    support_context: Mapping[str, Any] | None,
    policy: Mapping[str, Any] | None,
) -> dict[str, Any]:
    candidate = _mapping(candidate)
    support_context = _mapping(support_context)
    policy = _mapping(policy)
    failures = _unique(strict_failures)
    approved = bool(policy.get("enabled")) and _selector_matches(candidate, policy)

    support_ratio = _ratio(
        support_context.get("current_live_structure_bucket_rows"),
        support_context.get("minimum_support_rows"),
    )
    model_ratio = _ratio(candidate.get("trade_count"), policy.get("minimum_full_evidence_trades") or 50)
    evidence_score = round((0.5 * support_ratio) + (0.5 * model_ratio), 4)
    evidence_tier = _evidence_tier(support_ratio, model_ratio)

    if not approved:
        return {
            "owner_approved": False,
            "strategy_release_ready": not failures,
            "strategy_release_status": "strict_gates_passed" if not failures else "strict_gates_apply",
            "statistical_warnings": [],
            "technical_execution_blockers": [],
            "hard_gate_failures": failures,
            "strict_gate_failures": failures,
            "support_evidence_ratio": support_ratio,
            "model_evidence_ratio": model_ratio,
            "evidence_score": evidence_score,
            "evidence_tier": evidence_tier,
            "recommended_max_layers": 3 if not failures else 0,
            "technical_execution_gates_required": True,
        }

    statistical_warnings = [failure for failure in failures if _failure_is_advisory(failure, support_context)]
    technical_execution_blockers = [
        failure
        for failure in failures
        if failure not in statistical_warnings and _failure_is_technical_execution(failure, support_context)
    ]
    hard_failures = [
        failure
        for failure in failures
        if failure not in statistical_warnings and failure not in technical_execution_blockers
    ]
    release_ready = not hard_failures
    return {
        "owner_approved": True,
        "owner_approval_decision_id": policy.get("decision_id"),
        "owner_approved_by": policy.get("approved_by"),
        "strategy_release_ready": release_ready,
        "strategy_release_status": OWNER_APPROVED_STATUS if release_ready else "owner_approval_blocked_by_hard_risk_gate",
        "statistical_gate_policy": policy.get("statistical_gate_policy"),
        "statistical_gate_blocking": False,
        "statistical_warnings": statistical_warnings,
        "technical_execution_blockers": technical_execution_blockers,
        "hard_gate_failures": hard_failures,
        "strict_gate_failures": failures,
        "support_evidence_ratio": support_ratio,
        "model_evidence_ratio": model_ratio,
        "evidence_score": evidence_score,
        "evidence_tier": evidence_tier,
        "recommended_max_layers": (
            3
            if release_ready and evidence_tier == "full"
            else int(policy.get("max_layers_until_full_evidence") or 1)
            if release_ready
            else 0
        ),
        "technical_execution_gates_required": True,
    }


def _binding_matches(runtime_identity: Mapping[str, Any], policy: Mapping[str, Any]) -> bool:
    binding = _mapping(policy.get("runtime_binding"))
    if not binding.get("verified"):
        return False
    runtime_identity = _mapping(runtime_identity)
    for key in ("model", "feature_profile"):
        expected = _norm(binding.get(key))
        if expected and _norm(runtime_identity.get(key)) != expected:
            return False
    return True


def _strip_support_reason(value: Any) -> str | None:
    reasons = [part.strip() for part in str(value or "").split(";") if part.strip()]
    kept = [reason for reason in reasons if reason not in _SUPPORT_ONLY_BLOCKERS and not any(token in reason for token in _SUPPORT_ONLY_BLOCKERS)]
    return "; ".join(kept) or None


def apply_runtime_release_policy(
    execution_profile: Mapping[str, Any] | None,
    deployment_blocker: Mapping[str, Any] | None,
    *,
    policy: Mapping[str, Any] | None,
    runtime_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply owner release after strict predictor guardrails.

    Statistical support blockers become warnings only when the exact approved
    runtime model binding is verified. Otherwise they are replaced by a concrete
    model-binding task, never by another passive wait state.
    """

    guarded = deepcopy(_mapping(execution_profile))
    blocker = _mapping(deployment_blocker)
    policy = _mapping(policy)
    if not policy.get("enabled"):
        return guarded

    blocker_type = _norm(blocker.get("type") or guarded.get("deployment_blocker"))
    support_warning = blocker_type if blocker_type in _SUPPORT_ONLY_BLOCKERS else None
    raw_layers = _to_int(guarded.get("allowed_layers_raw"))
    if raw_layers is None:
        raw_layers = max(_to_int(guarded.get("allowed_layers")) or 0, 0)
    raw_layers = max(raw_layers, 0)
    max_layers = int(policy.get("max_layers_until_full_evidence") or 1)
    support_progress = _mapping(blocker.get("support_progress"))
    support_rows = _to_int(
        blocker.get("current_live_structure_bucket_rows")
        if blocker.get("current_live_structure_bucket_rows") is not None
        else support_progress.get("current_rows")
    )
    if support_rows is None:
        support_rows = _to_int(guarded.get("current_live_structure_bucket_rows"))
    minimum_support_rows = _to_int(
        blocker.get("minimum_support_rows")
        if blocker.get("minimum_support_rows") is not None
        else support_progress.get("minimum_support_rows")
    )
    if minimum_support_rows is None:
        minimum_support_rows = _to_int(guarded.get("minimum_support_rows"))
    support_ratio = _ratio(support_rows, minimum_support_rows or 50)
    runtime_evidence_tier = _evidence_tier(support_ratio, support_ratio)
    inferred_support_warning = None
    if minimum_support_rows and (support_rows or 0) < minimum_support_rows:
        inferred_support_warning = (
            "unsupported_exact_live_structure_bucket"
            if (support_rows or 0) <= 0
            else "under_minimum_exact_live_structure_bucket"
        )
    warnings = _unique(
        [
            *guarded.get("statistical_warnings", []),
            *([support_warning] if support_warning else []),
            *([inferred_support_warning] if inferred_support_warning else []),
        ]
    )
    binding_verified = _binding_matches(_mapping(runtime_identity), policy)
    technical_execution_blockers = _unique(
        [
            *guarded.get("technical_execution_blockers", []),
            *([blocker_type] if blocker_type and blocker_type not in _SUPPORT_ONLY_BLOCKERS else []),
        ]
    )

    guarded.update(
        {
            "owner_approved": True,
            "owner_approval_decision_id": policy.get("decision_id"),
            "owner_approved_by": policy.get("approved_by"),
            "strategy_release_ready": True,
            "strategy_release_status": OWNER_APPROVED_STATUS,
            "statistical_gate_policy": policy.get("statistical_gate_policy"),
            "statistical_gate_blocking": False,
            "statistical_warnings": warnings,
            "technical_execution_blockers": technical_execution_blockers,
            "support_evidence_ratio": support_ratio,
            "model_evidence_ratio": None,
            "evidence_score": support_ratio,
            "evidence_tier": runtime_evidence_tier,
            "recommended_max_layers": max_layers,
            "technical_execution_gates_required": True,
            "runtime_binding_verified": binding_verified,
            "allowed_layers_raw": raw_layers,
        }
    )

    if blocker_type and blocker_type not in _SUPPORT_ONLY_BLOCKERS:
        guarded["deployment_blocker"] = blocker_type
        guarded["deployment_blocker_reason"] = blocker.get("reason") or guarded.get("deployment_blocker_reason")
        guarded["deployment_blocker_source"] = blocker.get("source") or guarded.get("deployment_blocker_source")
        guarded["deployment_blocker_details"] = blocker or guarded.get("deployment_blocker_details")
        guarded["allowed_layers"] = 0
        return guarded

    if not binding_verified:
        binding = _mapping(policy.get("runtime_binding"))
        required_model = binding.get("model") or "approved model"
        required_profile = binding.get("feature_profile") or "approved feature profile"
        technical_blocker = {
            "type": "owner_approved_strategy_binding_required",
            "reason": (
                f"策略已由擁有者放行供個人使用；目前需把 runtime 明確綁定到 {required_model}/{required_profile} "
                "的同一份 fitted model、feature schema 與 checksum，完成後才可交由技術執行 gate 評估。"
            ),
            "source": "strategy_release.owner_approval.runtime_binding",
            "required_model": required_model,
            "required_feature_profile": required_profile,
            "binding_verified": False,
        }
        guarded.update(
            {
                "deployment_blocker": technical_blocker["type"],
                "deployment_blocker_reason": technical_blocker["reason"],
                "deployment_blocker_source": technical_blocker["source"],
                "deployment_blocker_details": technical_blocker,
                "allowed_layers": 0,
                "allowed_layers_reason": technical_blocker["type"],
                "execution_guardrail_applied": True,
                "execution_guardrail_reason": technical_blocker["type"],
                "runtime_binding_verified": False,
                "technical_execution_blockers": _unique(
                    [*technical_execution_blockers, technical_blocker["type"]]
                ),
            }
        )
        return guarded

    guarded.update(
        {
            "deployment_blocker": None,
            "deployment_blocker_reason": None,
            "deployment_blocker_source": None,
            "deployment_blocker_details": None,
            "allowed_layers": min(raw_layers, max_layers),
            "allowed_layers_reason": "owner_approved_uncertainty_caps_first_layer" if raw_layers > max_layers else guarded.get("allowed_layers_raw_reason") or guarded.get("allowed_layers_reason"),
            "execution_guardrail_reason": _strip_support_reason(guarded.get("execution_guardrail_reason")),
            "runtime_binding_verified": True,
        }
    )
    guarded["execution_guardrail_applied"] = bool(guarded.get("execution_guardrail_reason"))
    return guarded
