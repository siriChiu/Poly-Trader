from __future__ import annotations

from typing import Any, Mapping


_EXACT_SUPPORT_PENDING_VERDICTS = {
    "exact_bucket_unsupported_block",
    "exact_bucket_present_but_below_minimum",
    "exact_bucket_missing_proxy_reference_only",
    "exact_bucket_missing_exact_lane_proxy_only",
}

_EXACT_SUPPORT_PENDING_BLOCKERS = {
    "unsupported_exact_live_structure_bucket",
    "under_minimum_exact_live_structure_bucket",
}


def runtime_patch_name(result: Mapping[str, Any] | None) -> str | None:
    result = result or {}
    if result.get("q15_exact_supported_component_patch_applied"):
        return "q15 patch"
    if result.get("q35_discriminative_redesign_applied"):
        return "q35 discriminative redesign"
    return None



def build_runtime_closure_state(result: Mapping[str, Any] | None) -> str:
    result = result or {}
    patch_name = runtime_patch_name(result)
    blocker = str(result.get("deployment_blocker") or "")
    support_route_verdict = str(_support_route_verdict(result) or "")
    if result.get("signal") == "CIRCUIT_BREAKER":
        return "circuit_breaker_active"
    if blocker.startswith("exact_live_lane_toxic_"):
        return "deployment_guardrail_blocks_trade"
    if blocker == "decision_quality_below_trade_floor" and support_route_verdict == "exact_bucket_supported" and not patch_name:
        return "support_closed_but_trade_floor_blocked"
    if patch_name and result.get("signal") == "HOLD" and (_int_or_zero(result.get("allowed_layers")) > 0):
        return "capacity_opened_signal_hold"
    if patch_name and (
        result.get("deployment_blocker")
        or result.get("execution_guardrail_applied")
        or _int_or_zero(result.get("allowed_layers")) <= 0
    ):
        return "patch_active_but_execution_blocked"
    if patch_name:
        return "patch_active"
    return "patch_inactive_or_blocked"



def build_runtime_closure_summary(
    result: Mapping[str, Any] | None,
    *,
    release_window: int = 50,
    release_floor: Any = None,
    release_gap: Any = None,
    current_wins: Any = None,
    breaker_release: Mapping[str, Any] | None = None,
    scope_pathology_summary: Mapping[str, Any] | None = None,
) -> str | None:
    result = result or {}
    breaker_release = breaker_release or {}
    patch_name = runtime_patch_name(result)
    blocker = str(result.get("deployment_blocker") or "")
    blocker_reason = (
        result.get("deployment_blocker_reason")
        or result.get("execution_guardrail_reason")
        or result.get("allowed_layers_reason")
    )
    bucket = str(result.get("current_live_structure_bucket") or result.get("structure_bucket") or "unknown_bucket")
    support_route_verdict = str(_support_route_verdict(result) or "")
    support_governance_route = _support_governance_route(result)
    current_rows, minimum_rows = _support_rows(result)
    recommended_patch = scope_pathology_summary.get("recommended_patch") if isinstance(scope_pathology_summary, Mapping) else None

    if result.get("signal") == "CIRCUIT_BREAKER":
        release_floor_pct = ((release_floor if isinstance(release_floor, (int, float)) else 0.3) * 100)
        streak_cap = breaker_release.get("streak_must_be_below", 50)
        summary = (
            f"circuit breaker active：{result.get('reason')}; release condition = streak < {streak_cap} 且 recent {release_window} win rate >= {release_floor_pct:.0f}%"
            + (
                f"；目前 recent {release_window} 只贏 {current_wins}/{release_window}，至少還差 {release_gap} 勝。"
                if release_gap not in (None, 0) and current_wins is not None
                else "。"
            )
        )
        if result.get("decision_quality_recent_pathology_applied") and result.get("decision_quality_recent_pathology_reason"):
            summary += f" 同時 recent pathology={result.get('decision_quality_recent_pathology_reason')}。"
        return _append_scope_summary(summary, scope_pathology_summary)

    if blocker.startswith("exact_live_lane_toxic_"):
        summary = (
            f"current live bucket {bucket} 已具 exact support，但 runtime 仍被 {blocker} 擋住；"
            f"{blocker_reason or 'exact live lane 毒性治理仍未解除'}。"
            "目前保持 hold-only，不可把 support closure 誤讀成 deployment closure。"
        )
        return _append_scope_summary(summary, scope_pathology_summary)

    if blocker == "decision_quality_below_trade_floor" and support_route_verdict == "exact_bucket_supported" and not patch_name:
        trade_floor = _trade_floor(result)
        component_verdict = result.get("component_experiment_verdict")
        entry_quality = _float_or_zero(result.get("entry_quality"))
        entry_label = result.get("entry_quality_label") or "—"
        summary = (
            f"current live bucket {bucket} 已完成 exact support closure"
            + (f"（{current_rows}/{minimum_rows}）" if current_rows is not None and minimum_rows is not None else "")
            + f"，但 top-level live baseline 仍停在 entry_quality={entry_quality:.4f} ({entry_label})"
            + (f" < trade floor {trade_floor:.2f}" if trade_floor is not None else "")
            + "；目前維持明確 no-deploy governance。"
            + (f" q15 audit 的 {component_verdict} 只代表研究型 component experiment readiness，" if component_verdict else " ")
            + "不可把 support closure 誤讀成 deployment closure。"
        )
        return _append_scope_summary(summary, scope_pathology_summary)

    if patch_name and result.get("signal") == "HOLD" and (_int_or_zero(result.get("allowed_layers")) > 0):
        return (
            f"{patch_name} 已啟用；runtime 已開出 {_int_or_zero(result.get('allowed_layers'))} 層 deployment capacity，"
            "但 signal 仍是 HOLD，不等於自動 BUY。"
        )

    if patch_name and (
        result.get("deployment_blocker")
        or result.get("execution_guardrail_applied")
        or _int_or_zero(result.get("allowed_layers")) <= 0
    ):
        raw_layers = _int_or_zero(result.get("allowed_layers_raw") or result.get("allowed_layers"))
        summary = (
            f"{patch_name} 已啟用並把 entry_quality 拉到 {_float_or_zero(result.get('entry_quality')):.4f}（raw layers={raw_layers}），"
            f"但最終 execution 仍被 {blocker or blocker_reason or 'unknown_guardrail'} 擋住；目前不可把 patch active 誤讀成可部署。"
        )
        return _append_scope_summary(summary, scope_pathology_summary)

    if patch_name:
        return f"{patch_name} active，但當前 runtime 狀態不屬於 capacity_opened_signal_hold。"

    if blocker in _EXACT_SUPPORT_PENDING_BLOCKERS or support_route_verdict in _EXACT_SUPPORT_PENDING_VERDICTS:
        support_text = _format_support_rows(current_rows, minimum_rows)
        summary = (
            f"current live bucket {bucket} 的 exact support 仍未就緒（{support_text}"
            + (f"，route={support_route_verdict}" if support_route_verdict else "")
            + (f" / governance={support_governance_route}" if support_governance_route else "")
            + "）；broader / proxy rows"
        )
        if isinstance(recommended_patch, Mapping) and (recommended_patch.get("recommended_profile") or recommended_patch.get("status")):
            summary += " 與 recommended patch"
        summary += " 目前都只屬 reference-only 治理，不可視為 deployment closure。"
        if isinstance(recommended_patch, Mapping):
            profile = recommended_patch.get("recommended_profile")
            status = recommended_patch.get("status")
            if profile or status:
                summary += f" recommended_patch={profile or '—'} ({status or 'reference_only'})."
        if blocker_reason and blocker_reason not in summary:
            summary += f" blocker={blocker_reason}."
        return _append_scope_summary(summary, scope_pathology_summary)

    if blocker or blocker_reason:
        summary = (
            f"current live runtime 仍被 {blocker or 'unknown_blocker'} 擋住；"
            f"{blocker_reason or '需檢查 deployment / execution guardrails'}。"
        )
        return _append_scope_summary(summary, scope_pathology_summary)

    return None



def _append_scope_summary(summary: str, scope_pathology_summary: Mapping[str, Any] | None) -> str:
    if isinstance(scope_pathology_summary, Mapping) and scope_pathology_summary.get("summary"):
        return f"{summary} exact-vs-spillover={scope_pathology_summary.get('summary')}"
    return summary



def _support_route_verdict(result: Mapping[str, Any]) -> Any:
    details = result.get("deployment_blocker_details") if isinstance(result.get("deployment_blocker_details"), Mapping) else {}
    return result.get("support_route_verdict") or details.get("support_route_verdict")



def _support_governance_route(result: Mapping[str, Any]) -> Any:
    details = result.get("deployment_blocker_details") if isinstance(result.get("deployment_blocker_details"), Mapping) else {}
    return result.get("support_governance_route") or details.get("support_governance_route")



def _support_rows(result: Mapping[str, Any]) -> tuple[int | None, int | None]:
    progress = result.get("support_progress") if isinstance(result.get("support_progress"), Mapping) else {}
    details = result.get("deployment_blocker_details") if isinstance(result.get("deployment_blocker_details"), Mapping) else {}
    current_rows = progress.get("current_rows")
    if current_rows is None:
        current_rows = result.get("current_live_structure_bucket_rows")
    if current_rows is None:
        current_rows = details.get("current_live_structure_bucket_rows")
    if current_rows is None:
        current_rows = details.get("exact_live_structure_bucket_rows")
    minimum_rows = progress.get("minimum_support_rows")
    if minimum_rows is None:
        minimum_rows = result.get("minimum_support_rows")
    if minimum_rows is None:
        minimum_rows = details.get("minimum_support_rows")
    return _int_or_none(current_rows), _int_or_none(minimum_rows)



def _format_support_rows(current_rows: int | None, minimum_rows: int | None) -> str:
    if current_rows is None and minimum_rows is None:
        return "unknown/unknown"
    if current_rows is None:
        return f"?/{minimum_rows}"
    if minimum_rows is None:
        return f"{current_rows}/?"
    return f"{current_rows}/{minimum_rows}"



def _trade_floor(result: Mapping[str, Any]) -> float | None:
    entry_quality_components = result.get("entry_quality_components")
    if not isinstance(entry_quality_components, Mapping):
        return None
    trade_floor = entry_quality_components.get("trade_floor")
    try:
        return float(trade_floor) if trade_floor is not None else None
    except (TypeError, ValueError):
        return None



def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None



def _int_or_zero(value: Any) -> int:
    return _int_or_none(value) or 0



def _float_or_zero(value: Any) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0
