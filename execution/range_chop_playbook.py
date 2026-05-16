from __future__ import annotations

from typing import Any, Mapping


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _text(*values: Any) -> str:
    parts = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in value)
            continue
        parts.append(str(value))
    return " ".join(parts).lower()


def _support_context(live_runtime_truth: Mapping[str, Any] | None, high_conviction_topk: Mapping[str, Any] | None) -> dict[str, Any]:
    live_runtime_truth = _as_dict(live_runtime_truth)
    topk = _as_dict(high_conviction_topk)
    topk_support = _as_dict(topk.get("support_context"))
    progress = _as_dict(live_runtime_truth.get("support_progress"))

    current_rows = _to_int(
        topk_support.get("current_live_structure_bucket_rows")
        or topk_support.get("current_rows")
        or live_runtime_truth.get("runtime_exact_support_rows")
        or live_runtime_truth.get("current_live_structure_bucket_rows")
        or progress.get("current_rows")
    )
    minimum_rows = _to_int(
        topk_support.get("minimum_support_rows")
        or progress.get("minimum_support_rows")
        or live_runtime_truth.get("minimum_support_rows")
    )
    gap_to_minimum = _to_int(
        topk_support.get("support_rows_needed")
        or topk_support.get("current_live_structure_bucket_gap_to_minimum")
        or progress.get("gap_to_minimum")
        or live_runtime_truth.get("current_live_structure_bucket_gap_to_minimum")
    )
    if gap_to_minimum is None and current_rows is not None and minimum_rows is not None:
        gap_to_minimum = max(minimum_rows - current_rows, 0)

    return {
        "current_bucket": (
            topk_support.get("current_live_structure_bucket")
            or live_runtime_truth.get("current_live_structure_bucket")
            or live_runtime_truth.get("structure_bucket")
        ),
        "current_rows": current_rows,
        "minimum_rows": minimum_rows,
        "gap_to_minimum": gap_to_minimum,
        "support_progress_status": (
            topk_support.get("support_progress_status")
            or progress.get("status")
            or live_runtime_truth.get("support_progress_status")
        ),
        "stalled_support_accumulation": bool(
            topk_support.get("stalled_support_accumulation")
            or progress.get("stalled_support_accumulation")
            or live_runtime_truth.get("stalled_support_accumulation")
        ),
        "stagnant_run_count": _to_int(
            topk_support.get("stagnant_run_count")
            or progress.get("stagnant_run_count")
            or live_runtime_truth.get("stagnant_run_count")
        ),
    }


def build_range_chop_playbook(
    live_runtime_truth: Mapping[str, Any] | None,
    high_conviction_topk: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an operator playbook for choppy/range markets without unlocking risk-on trades.

    The playbook is intentionally not a deployment proof.  It gives operators a
    positive path while current-live support is unstable: run paper-shadow
    observations, collect support evidence, and allow de-risking actions.  Buy / add
    exposure remains fail-closed until the canonical current-live gate and venue
    proof chain pass.
    """
    live_runtime_truth = _as_dict(live_runtime_truth)
    routing = _as_dict(live_runtime_truth.get("sleeve_routing"))
    support = _support_context(live_runtime_truth, high_conviction_topk)

    regime_label = live_runtime_truth.get("regime_label") or routing.get("current_regime")
    regime_gate = live_runtime_truth.get("regime_gate") or routing.get("current_regime_gate")
    structure_bucket = live_runtime_truth.get("structure_bucket") or routing.get("current_structure_bucket")
    runtime_state = live_runtime_truth.get("runtime_closure_state")
    deployment_blocker = live_runtime_truth.get("deployment_blocker")
    guardrail_reason = live_runtime_truth.get("execution_guardrail_reason")

    combined_text = _text(
        regime_label,
        regime_gate,
        structure_bucket,
        runtime_state,
        deployment_blocker,
        guardrail_reason,
        live_runtime_truth.get("deployment_blocker_reason"),
        support.get("current_bucket"),
    )
    chop_like = any(token in combined_text for token in ("chop", "range", "sideway", "neutral", "盤整", "震盪", "擁塞", "高低"))
    runtime_blocked = bool(
        deployment_blocker
        or guardrail_reason
        or "blocked" in combined_text
        or "block" in combined_text
        or str(regime_gate or "").upper() == "BLOCK"
    )
    support_gap = (support.get("gap_to_minimum") or 0) > 0
    shadow_available = bool(runtime_blocked and (chop_like or support_gap or deployment_blocker))
    status = "shadow_reduce_only" if shadow_available else "standby"

    support_summary_parts: list[str] = []
    if support.get("current_rows") is not None and support.get("minimum_rows") is not None:
        support_summary_parts.append(f"精準支持 {support['current_rows']}/{support['minimum_rows']}")
    if support.get("gap_to_minimum") is not None:
        support_summary_parts.append(f"缺 {support['gap_to_minimum']}")
    if support.get("stalled_support_accumulation") and support.get("stagnant_run_count") is not None:
        support_summary_parts.append(f"停滯 {support['stagnant_run_count']} 輪")

    if shadow_available:
        operator_message = (
            "不是永遠不能實戰；高低震盪先拆成「影子觀察 / 減風險先行」："
            "區間候選只進影子觀察，先累積決策、支撐樣本與場館預演；"
            "若已有倉位，減風險 / 取消掛單允許；買入 / 加倉仍等即時部署門檻與場館證據鏈通過。"
        )
        next_operator_action = (
            "先啟動區間震盪影子觀察與減風險檢查；不要把反彈或回調候選直接升級為買入 / 加倉。"
        )
    else:
        operator_message = (
            "目前不是需要高低震盪拆解的阻塞狀態；仍保留減風險通道，買入 / 加倉需遵守即時部署門檻。"
        )
        next_operator_action = "維持一般路由；若市場轉為高低震盪或即時支持失穩，再切到影子觀察 / 減風險劇本。"

    return {
        "key": "range_chop_playbook",
        "status": status,
        "summary": "影子觀察 / 減風險先行" if shadow_available else "一般路由待命",
        "market_problem": "高低震盪 / 盤整分桶尚未穩定" if shadow_available else "尚未觸發高低震盪 playbook",
        "shadow_available": shadow_available,
        "shadow_mode": "paper_shadow",
        "shadow_scope": "range_chop_rehearsal",
        "risk_reduction_allowed": True,
        "buy_add_requires_current_live_gate": True,
        "risk_on_order_enabled": False,
        "order_submission_enabled": False,
        "allowed_operator_actions": [
            "range_shadow_observe",
            "reduce_position",
            "cancel_stale_orders",
            "collect_support_evidence",
        ],
        "blocked_operator_actions": ["buy", "add_exposure", "enable_automation"],
        "reduce_risk_sides": ["sell", "reduce", "cancel"],
        "release_prerequisites": [
            "即時部署精準支持達標",
            "場館憑證 / 委託 ack / 成交 lifecycle 證據鏈完成",
            "影子觀察事件紀錄連續通過",
        ],
        "operator_message": operator_message,
        "next_operator_action": next_operator_action,
        "support_summary": " · ".join(support_summary_parts) if support_summary_parts else None,
        "support_context": support,
        "source": "live_runtime_truth+high_conviction_topk",
    }
