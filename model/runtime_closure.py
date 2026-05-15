from __future__ import annotations

import re
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

_STRUCTURE_BUCKET_TOKEN_REPLACEMENTS = [
    ("bull_q15_bias50_overextended_block", "牛市 q15 bias50 過熱阻塞"),
    ("bull_high_bias200_overheat_block", "牛市高 bias200 過熱阻塞"),
    ("structure_quality_caution", "結構品質觀察"),
    ("structure_quality_block", "結構品質阻塞"),
    ("base_caution_regime_or_bias", "基線觀察（市場狀態 / 偏離）"),
    ("base_allow", "基線放行"),
]


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
    bucket = _humanize_runtime_text(
        result.get("current_live_structure_bucket") or result.get("structure_bucket") or "unknown_bucket"
    )
    support_route_verdict = str(_support_route_verdict(result) or "")
    support_governance_route = _support_governance_route(result)
    current_rows, minimum_rows = _support_rows(result)
    recommended_patch = scope_pathology_summary.get("recommended_patch") if isinstance(scope_pathology_summary, Mapping) else None

    if result.get("signal") == "CIRCUIT_BREAKER":
        release_floor_pct = ((release_floor if isinstance(release_floor, (int, float)) else 0.3) * 100)
        streak_cap = breaker_release.get("streak_must_be_below", 50)
        reason_text = _humanize_runtime_text(result.get("reason") or blocker_reason or "風控熔斷條件仍未解除")
        summary = (
            f"風控熔斷啟用中：{reason_text}；解除條件：連續虧損筆數 < {streak_cap} 且最近 {release_window} 筆勝率 >= {release_floor_pct:.0f}%"
            + (
                f"；目前最近 {release_window} 筆只贏 {current_wins}/{release_window}，至少還差 {release_gap} 勝。"
                if release_gap not in (None, 0) and current_wins is not None
                else "。"
            )
        )
        if result.get("decision_quality_recent_pathology_applied") and result.get("decision_quality_recent_pathology_reason"):
            summary += f" 同時近期病態={_humanize_runtime_text(result.get('decision_quality_recent_pathology_reason'))}。"
        return _append_scope_summary(summary, scope_pathology_summary)

    if blocker.startswith("exact_live_lane_toxic_"):
        summary = (
            f"當前即時分桶 {bucket} 已具精準樣本，但執行期仍被 {_humanize_runtime_text(blocker)} 擋住；"
            f"{_humanize_runtime_text(blocker_reason or '精準即時路徑毒性治理仍未解除')}。"
            "目前保持僅觀察，不可把支持樣本閉環誤讀成部署閉環。"
        )
        return _append_scope_summary(summary, scope_pathology_summary)

    if blocker == "decision_quality_below_trade_floor" and support_route_verdict == "exact_bucket_supported" and not patch_name:
        trade_floor = _trade_floor(result)
        component_verdict = result.get("component_experiment_verdict")
        component = _component_experiment(result)
        machine_answer = component.get("machine_read_answer") if isinstance(component.get("machine_read_answer"), Mapping) else {}
        positive_status = (
            result.get("component_experiment_positive_discrimination_status")
            or machine_answer.get("preserves_positive_discrimination_status")
            or component.get("positive_discrimination_status")
        )
        verify_next = result.get("component_experiment_verify_next") or component.get("verify_next")
        entry_quality = _float_or_zero(result.get("entry_quality"))
        entry_label = result.get("entry_quality_label") or "—"
        summary = (
            f"當前即時分桶 {bucket} 已完成精準樣本閉環"
            + (f"（{current_rows}/{minimum_rows}）" if current_rows is not None and minimum_rows is not None else "")
            + f"，但頂層即時基準仍停在進場品質={entry_quality:.4f} ({entry_label})"
            + (f" < 交易門檻 {trade_floor:.2f}" if trade_floor is not None else "")
            + "；目前維持明確不可部署治理。"
        )
        if component_verdict == "exact_supported_component_experiment_blocked_by_discrimination":
            summary += (
                " q15 跨門檻結果只代表可做研究型元件實驗，不是執行放行；"
                "元件實驗目前被正向辨別力阻塞"
                + (f"（{_humanize_runtime_text(positive_status)}）" if positive_status else "")
                + "，不可放寬 allowed_layers / execution guardrail。"
            )
            if verify_next:
                verify_text = _humanize_runtime_text(verify_next).rstrip("。")
                summary += f" 下一步={verify_text}。"
        elif component_verdict:
            summary += (
                f" q15 審核的 {_humanize_runtime_text(component_verdict)} 只代表研究型元件實驗就緒，"
                "不可把支持樣本閉環誤讀成部署閉環。"
            )
        else:
            summary += " 不可把支持樣本閉環誤讀成部署閉環。"
        return _append_scope_summary(summary, scope_pathology_summary)

    if patch_name and result.get("signal") == "HOLD" and (_int_or_zero(result.get("allowed_layers")) > 0):
        return (
            f"{patch_name} 已啟用；執行期已開出 {_int_or_zero(result.get('allowed_layers'))} 層部署容量，"
            "但 signal 仍是 HOLD，不等於自動 BUY。"
        )

    if patch_name and (
        result.get("deployment_blocker")
        or result.get("execution_guardrail_applied")
        or _int_or_zero(result.get("allowed_layers")) <= 0
    ):
        raw_layers = _int_or_zero(result.get("allowed_layers_raw") or result.get("allowed_layers"))
        summary = (
            f"{patch_name} 已啟用並把進場品質拉到 {_float_or_zero(result.get('entry_quality')):.4f}（原始層數={raw_layers}），"
            f"但最終執行仍被 {_humanize_runtime_text(blocker or blocker_reason or 'unknown_guardrail')} 擋住；目前不可把修補方案已啟用誤讀成可部署。"
        )
        return _append_scope_summary(summary, scope_pathology_summary)

    if patch_name:
        return f"{patch_name} 已啟用，但當前執行期狀態不屬於容量已開且訊號觀望。"

    if blocker in _EXACT_SUPPORT_PENDING_BLOCKERS or support_route_verdict in _EXACT_SUPPORT_PENDING_VERDICTS:
        support_text = _format_support_rows(current_rows, minimum_rows)
        summary = (
            f"當前即時分桶 {bucket} 的精準樣本仍未就緒（{support_text}"
            + (f"，路徑={_humanize_runtime_text(support_route_verdict)}" if support_route_verdict else "")
            + (f" / 治理={_humanize_runtime_text(support_governance_route)}" if support_governance_route else "")
            + "）；較寬範圍 / 近似樣本"
        )
        if isinstance(recommended_patch, Mapping) and (recommended_patch.get("recommended_profile") or recommended_patch.get("status")):
            summary += " 與建議修補方案"
        summary += " 目前都只屬僅供治理參考，不可視為部署閉環。"
        if isinstance(recommended_patch, Mapping):
            profile = recommended_patch.get("recommended_profile")
            status = recommended_patch.get("status")
            if profile or status:
                summary += f" 建議修補方案={_humanize_runtime_text(profile or '—')} ({_humanize_runtime_text(status or 'reference_only')})."
        if blocker_reason and blocker_reason not in summary:
            reason_text = _humanize_runtime_text(blocker_reason).rstrip("。")
            summary += f" 阻塞點={reason_text}。"
        return _append_scope_summary(summary, scope_pathology_summary)

    if blocker or blocker_reason:
        summary = (
            f"當前即時執行期仍被 {_humanize_runtime_text(blocker or 'unknown_blocker')} 擋住；"
            f"{_humanize_runtime_text(blocker_reason or '需檢查部署 / 執行保護欄')}。"
        )
        return _append_scope_summary(summary, scope_pathology_summary)

    return None



def _append_scope_summary(summary: str, scope_pathology_summary: Mapping[str, Any] | None) -> str:
    if isinstance(scope_pathology_summary, Mapping) and scope_pathology_summary.get("summary"):
        return f"{summary} 精準路徑與外溢對照：{_humanize_runtime_text(scope_pathology_summary.get('summary'))}"
    return summary


def _humanize_runtime_text(value: Any) -> str:
    text = _humanize_structure_bucket_tokens(str(value or ""))
    replacements = [
        ("Consecutive loss streak:", "連續虧損筆數："),
        ("Consecutive loss streak", "連續虧損筆數"),
        ("Recent 50-sample win rate", "最近 50 筆勝率"),
        ("recent 50 win rate", "最近 50 筆勝率"),
        ("recent 50", "最近 50 筆"),
        ("decision_quality_below_trade_floor", "決策品質低於交易門檻"),
        ("entry_quality_below_trade_floor", "進場品質低於交易門檻"),
        ("unsupported_exact_live_structure_bucket_blocks_trade", "精準樣本尚未建立，阻止交易"),
        ("floor_crossed_but_support_not_ready", "已跨越門檻但精準樣本未就緒"),
        ("runtime_blocker_preempts_floor_analysis", "執行期阻塞優先於跨門檻分析"),
        ("runtime_blocker_preempts_runtime_sizing", "執行期阻塞優先於層數配置"),
        ("regime_gate_block", "市場閘門阻塞"),
        ("circuit_breaker_active", "風控熔斷啟用中"),
        ("runtime gate/support", "執行期 gate/樣本支持"),
        ("scoring floor", "評分門檻"),
        ("score-only", "僅限評分"),
        ("execution-blocked", "執行仍阻塞"),
        ("floor-cross", "跨越門檻"),
        ("decision-quality trade floor", "決策品質交易門檻"),
        ("decision-quality", "決策品質"),
        ("top-level live baseline", "頂層即時基準"),
        ("current live structure bucket", "當前即時結構分桶"),
        ("current live bucket", "當前即時分桶"),
        ("exact support closure", "精準樣本閉環"),
        ("support closure", "支持樣本閉環"),
        ("deployment closure", "部署閉環"),
        ("component-experiment readiness", "元件實驗就緒"),
        ("component experiment readiness", "元件實驗就緒"),
        ("no-deploy governance", "不可部署治理"),
        ("patch_active_but_execution_blocked", "修補方案已套用但執行期仍阻塞"),
        ("patch active", "修補方案已啟用"),
        ("final execution", "最終執行"),
        ("deployment capacity", "部署容量"),
        ("trade floor", "交易門檻"),
        ("entry_quality", "進場品質"),
        ("raw layers", "原始層數"),
        ("raw entry", "原始進場品質"),
        ("release condition =", "解除條件："),
        ("release condition", "解除條件"),
        ("streak", "連續虧損筆數"),
        ("sample win rate", "筆勝率"),
        ("circuit breaker active", "風控熔斷啟用中"),
        ("circuit breaker", "風控熔斷"),
        ("exact live lane", "精準即時路徑"),
        ("missing exact support", "精準樣本缺失"),
        ("exact support", "精準樣本"),
        ("hold-only", "僅觀察"),
        ("broader / proxy rows", "較寬範圍 / 近似樣本"),
        ("reference_only_non_current_live_scope", "非目前即時範圍，僅供治理參考"),
        ("reference_only_until_exact_support_ready", "精準樣本就緒前僅供治理參考"),
        ("exact_supported_component_experiment_blocked_by_discrimination", "精準樣本元件實驗被正向辨別力阻塞，不可部署"),
        ("exact_supported_component_experiment_ready", "精準樣本元件實驗就緒"),
        ("legal_component_experiment_after_support_ready", "精準樣本就緒後可做研究型元件實驗"),
        ("legal_to_relax_runtime_gate", "只允許研究型元件實驗，尚非執行放行"),
        ("math_cross_possible_but_illegal_without_exact_support", "數學上可跨門檻，但精準樣本未達標前不可啟用"),
        ("failed_exact_lane_bucket_dominance", "同路徑鄰近分桶表現不劣於當前分桶"),
        ("preserves_positive_discrimination", "保留正向辨別力"),
        ("positive discrimination", "正向辨別力"),
        ("reference-only", "僅供治理參考"),
        ("reference_only", "僅供治理參考"),
        ("non_current_live_scope", "非目前即時範圍"),
        ("bull_4h_pocket_ablation.bull_collapse_q35", "牛市 4H 口袋消融 / 牛市崩落 q35"),
        ("bull_4h_pocket_ablation", "牛市 4H 口袋消融"),
        ("bull_collapse_q35", "牛市崩落 q35"),
        ("exact_live_bucket_present_but_below_minimum", "目前即時分桶精準樣本未達最小門檻"),
        ("exact_live_bucket_supported", "目前即時分桶精準樣本已就緒"),
        ("unsupported_exact_live_structure_bucket", "精準樣本尚未建立"),
        ("under_minimum_exact_live_structure_bucket", "精準樣本未達最小門檻"),
        ("exact_bucket_supported", "精準樣本已就緒"),
        ("exact_bucket_unsupported_block", "精準樣本尚未建立"),
        ("exact_bucket_present_but_below_minimum", "精準樣本未達最小門檻"),
        ("bull|BLOCK", "牛市|阻塞"),
        ("bull|ALLOW", "牛市|允許"),
        ("bull|CAUTION", "牛市|警戒"),
        ("chop|CAUTION", "盤整|警戒"),
        ("distribution_pathology", "分佈病態"),
        ("label_imbalance", "標籤失衡"),
        ("regime_concentration", "市場狀態過度集中"),
        ("dominant_regime", "主導市場狀態"),
        ("recent drift primary window", "近期漂移主要視窗"),
        ("recent scope slice", "近期範圍切片"),
        ("shows", "顯示"),
        ("alerts=", "警示="),
        ("同 quality 寬 scope", "同品質寬範圍"),
        ("deployment-grade minimum support", "部署級最小精準樣本門檻"),
        ("minimum support", "最小精準樣本門檻"),
        ("support 補滿前", "精準樣本補滿前"),
        ("exact rows", "精準筆數"),
        ("exact 筆", "精準筆數"),
        ("this lane", "這條路徑"),
        ("這條 lane", "這條路徑"),
        (" lane", " 路徑"),
        ("quality", "品質"),
        ("scope", "範圍"),
        ("spillover", "外溢"),
        ("rows", "筆"),
        ("WR", "勝率"),
        ("runtime", "執行期"),
        ("deployment", "部署"),
        ("execution", "執行"),
        ("guardrail", "保護欄"),
        ("blocker", "阻塞點"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    cleanup_pairs = [
        ("支持路徑=精準樣本未達最小門檻（精準樣本未達最小門檻）", "支持路徑=精準樣本未達最小門檻"),
        ("舊 範圍", "舊範圍"),
        ("舊範圍 的", "舊範圍的"),
        ("寬 範圍", "寬範圍"),
        ("寬範圍 出現", "寬範圍出現"),
        ("已有 精準筆數", "已有精準筆數"),
        ("這條路徑 視為", "這條路徑視為"),
        ("執行期 只能", "執行期只能"),
        ("。。", "。"),
    ]
    for old, new in cleanup_pairs:
        text = text.replace(old, new)
    return text


def _humanize_structure_bucket_tokens(text: str) -> str:
    """Render live-structure bucket enums as operator-safe Chinese copy.

    Runtime summaries are user-facing operator copy.  If we first replace the
    generic word ``quality`` we create hybrid strings such as
    ``structure_品質_caution``.  Replace the whole structure-bucket tokens first
    and only then translate gate / regime atoms.
    """

    for token, label in _STRUCTURE_BUCKET_TOKEN_REPLACEMENTS:
        text = text.replace(token, label)
        spaced_token = token.replace("_", " ")
        if spaced_token != token:
            text = text.replace(spaced_token, label)
    gate_replacements = [
        (r"\bBLOCK\b", "阻塞"),
        (r"\bCAUTION\b", "觀察"),
        (r"\bALLOW\b", "放行"),
        (r"\bbull\b", "牛市"),
        (r"\bbear\b", "熊市"),
        (r"\bchop\b", "盤整"),
        (r"\bneutral\b", "中性"),
    ]
    for pattern, label in gate_replacements:
        text = re.sub(pattern, label, text, flags=re.IGNORECASE)
    return text.replace("|", "｜")



def _component_experiment(result: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = result.get("component_experiment")
    if isinstance(direct, Mapping):
        return direct
    details = result.get("deployment_blocker_details") if isinstance(result.get("deployment_blocker_details"), Mapping) else {}
    nested = details.get("component_experiment") if isinstance(details.get("component_experiment"), Mapping) else {}
    return nested


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
