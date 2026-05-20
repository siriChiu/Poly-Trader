from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from execution.control_plane import (
    CONTROL_MODE,
    CONTROL_PLANE_OPERATOR_MESSAGE,
    CONTROL_PLANE_UPGRADE_PREREQUISITE,
    PRIMARY_SLEEVE_META,
    PRIMARY_SLEEVE_ORDER,
    build_execution_strategy_source_snapshot,
)
from execution.range_chop_playbook import build_range_chop_playbook
from execution.risk_control import check_position_size


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}



def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []



def _to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None



def _to_int(value: Any) -> Optional[int]:
    number = _to_float(value)
    if number is None:
        return None
    return int(number)



def _load_high_conviction_topk(status_payload: Dict[str, Any]) -> Dict[str, Any]:
    execution_surface_contract = _as_dict(status_payload.get("execution_surface_contract"))
    execution = _as_dict(status_payload.get("execution"))
    return _as_dict(
        execution_surface_contract.get("high_conviction_topk")
        or execution.get("high_conviction_topk")
        or status_payload.get("high_conviction_topk")
    )



def _build_high_conviction_shadow_contract(status_payload: Dict[str, Any]) -> Dict[str, Any]:
    topk = _load_high_conviction_topk(status_payload)
    if not topk:
        return {"shadow_available": False}

    risk_qualified_count = _to_int(topk.get("risk_qualified_count")) or 0
    runtime_blocked_candidate_count = _to_int(topk.get("runtime_blocked_candidate_count")) or 0
    deployable_count = _to_int(topk.get("deployable_count")) or 0
    readiness_status = str(topk.get("deployment_readiness_status") or "").strip()
    support_context = _as_dict(topk.get("support_context"))
    nearest_rows = [row for row in _as_list(topk.get("nearest_deployable_rows")) if isinstance(row, dict)]
    nearest = nearest_rows[0] if nearest_rows else {}

    shadow_available = bool(
        risk_qualified_count > 0
        and runtime_blocked_candidate_count > 0
        and deployable_count == 0
        and readiness_status in {"paper_shadow_only", "stale_artifact_shadow_only", "freshness_unknown_shadow_only"}
    )
    support_rows = _to_int(support_context.get("current_live_structure_bucket_rows"))
    minimum_rows = _to_int(support_context.get("minimum_support_rows"))
    gap_rows = _to_int(
        support_context.get("support_rows_needed")
        or support_context.get("current_live_structure_bucket_gap_to_minimum")
    )
    stalled_runs = _to_int(support_context.get("stagnant_run_count"))
    start_reason = (
        f"高信心 OOS 已通過離線 / 風控門檻 {risk_qualified_count} 筆，但可部署仍為 0；"
        f"目前精準支持 {support_rows if support_rows is not None else '—'} / {minimum_rows if minimum_rows is not None else '—'}"
        f"（缺 {gap_rows if gap_rows is not None else '—'}），可先啟動影子觀察運行，只記錄決策與共享帳戶預覽，不送單、不加倉。"
    )
    next_action = (
        "啟動高信念精選的影子觀察運行：只納入即時監控、事件紀錄與同商品共享預覽，"
        "等精準樣本與場館證據鏈通過後再升級小流量。"
    )
    support_summary_parts = []
    if support_rows is not None and minimum_rows is not None:
        support_summary_parts.append(f"支持 {support_rows}/{minimum_rows}")
    if gap_rows is not None:
        support_summary_parts.append(f"缺 {gap_rows}")
    if stalled_runs is not None and support_context.get("stalled_support_accumulation") is True:
        support_summary_parts.append(f"連續停滯 {stalled_runs} 輪")

    return {
        "shadow_available": shadow_available,
        "shadow_only": True,
        "risk_on_order_enabled": False,
        "shadow_mode": "paper_shadow",
        "readiness_status": readiness_status,
        "risk_qualified_count": risk_qualified_count,
        "runtime_blocked_candidate_count": runtime_blocked_candidate_count,
        "deployable_count": deployable_count,
        "operator_message": topk.get("operator_message") or start_reason,
        "start_reason": start_reason,
        "next_operator_action": next_action,
        "support_summary": " · ".join(support_summary_parts) if support_summary_parts else None,
        "support_context": support_context,
        "nearest_candidate": {
            "model_name": nearest.get("model_name"),
            "threshold_name": nearest.get("threshold_name"),
            "deployment_candidate_tier": nearest.get("deployment_candidate_tier"),
            "blocked_only_by_live_guardrails": nearest.get("blocked_only_by_live_guardrails"),
            "deployable": nearest.get("deployable"),
            "signal": nearest.get("signal"),
            "allowed_layers": nearest.get("allowed_layers"),
        } if nearest else None,
    }



def _record_text(record: Any, keys: Iterable[str]) -> Optional[str]:
    if not isinstance(record, dict):
        return None
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None



def _symbol_key(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.replace("/", "").replace("-", "").replace("_", "").upper()



def _symbol_keys(*values: Optional[str]) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for value in values:
        normalized = _symbol_key(value)
        if normalized and normalized not in seen:
            ordered.append(normalized)
            seen.add(normalized)
    return ordered



def _filter_records_for_symbol(records: Iterable[Any], symbol_keys: List[str]) -> List[Dict[str, Any]]:
    symbol_key_set = set(symbol_keys)
    matched: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        record_symbol = _record_text(record, ["symbol", "instId", "market", "pair"])
        record_key = _symbol_key(record_symbol)
        if symbol_key_set and record_key and record_key in symbol_key_set:
            matched.append(record)
    return matched



def _planned_budget(
    *,
    active: bool,
    total_balance: Optional[float],
    deployable_capital: Optional[float],
    active_count: int,
) -> Dict[str, Optional[float]]:
    if not active or active_count <= 0 or deployable_capital is None:
        return {
            "planned_budget_amount": 0.0 if active_count > 0 else None,
            "planned_budget_ratio_of_balance": 0.0 if total_balance not in (None, 0) else None,
        }
    amount = float(deployable_capital) / float(active_count)
    ratio = None
    if total_balance not in (None, 0):
        ratio = float(amount) / float(total_balance)
    return {
        "planned_budget_amount": amount,
        "planned_budget_ratio_of_balance": ratio,
    }



def _first_text(*values: Any) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None



def _first_int(*values: Any) -> Optional[int]:
    for value in values:
        number = _to_int(value)
        if number is not None:
            return number
    return None



def _first_float(*values: Any) -> Optional[float]:
    for value in values:
        number = _to_float(value)
        if number is not None:
            return number
    return None



def _nearest_high_conviction_candidate(topk: Dict[str, Any]) -> Dict[str, Any]:
    nearest_rows = [row for row in _as_list(topk.get("nearest_deployable_rows")) if isinstance(row, dict)]
    if nearest_rows:
        return nearest_rows[0]
    rows = [row for row in _as_list(topk.get("rows")) if isinstance(row, dict)]
    return rows[0] if rows else {}



def _venue_record_for_payload(status_payload: Dict[str, Any]) -> Dict[str, Any]:
    execution = _as_dict(status_payload.get("execution"))
    metadata_smoke = _as_dict(status_payload.get("execution_metadata_smoke"))
    venues = [item for item in _as_list(metadata_smoke.get("venues")) if isinstance(item, dict)]
    target_venue = str(execution.get("venue") or "").strip().lower()
    if target_venue:
        for venue in venues:
            if str(venue.get("venue") or "").strip().lower() == target_venue:
                return venue
    return venues[0] if venues else {}



def build_execution_readiness_bundle(
    status_payload: Optional[Dict[str, Any]],
    *,
    range_chop_playbook: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build M5 operator-safe execution readiness, shadow ledger, and venue proof payloads.

    This is intentionally fail-closed: OOS/model quality can open only a shadow
    observation lane.  Buy/add exposure and live order submission stay disabled
    until exact support, breaker/release math, venue proof chain, and surface
    contract all pass.
    """

    payload = _as_dict(status_payload)
    execution_surface_contract = _as_dict(payload.get("execution_surface_contract"))
    execution = _as_dict(payload.get("execution"))
    live_runtime_truth = _as_dict(execution.get("live_runtime_truth") or execution_surface_contract.get("live_runtime_truth"))
    account = _as_dict(payload.get("account"))
    execution_reconciliation = _as_dict(payload.get("execution_reconciliation"))
    topk = _load_high_conviction_topk(payload)
    high_conviction_shadow = _build_high_conviction_shadow_contract(payload)
    range_chop = _as_dict(range_chop_playbook or execution.get("range_chop_playbook") or execution_surface_contract.get("range_chop_playbook") or payload.get("range_chop_playbook"))
    venue_record = _venue_record_for_payload(payload)

    support_progress = _as_dict(live_runtime_truth.get("support_progress"))
    topk_support_context = _as_dict(topk.get("support_context"))
    blocker_details = _as_dict(live_runtime_truth.get("deployment_blocker_details"))
    release_condition = _as_dict(blocker_details.get("release_condition"))
    recent_window_details = _as_dict(blocker_details.get("recent_window"))

    support_rows = _first_int(
        support_progress.get("current_rows"),
        live_runtime_truth.get("current_live_structure_bucket_rows"),
        topk_support_context.get("current_live_structure_bucket_rows"),
    )
    support_minimum = _first_int(
        support_progress.get("minimum_support_rows"),
        live_runtime_truth.get("minimum_support_rows"),
        topk_support_context.get("minimum_support_rows"),
    )
    support_gap = _first_int(
        support_progress.get("gap_to_minimum"),
        live_runtime_truth.get("current_live_structure_bucket_gap_to_minimum"),
        topk_support_context.get("support_rows_needed"),
        topk_support_context.get("current_live_structure_bucket_gap_to_minimum"),
    )
    if support_gap is None and support_rows is not None and support_minimum is not None:
        support_gap = max(int(support_minimum) - int(support_rows), 0)
    support_passed = bool(
        support_rows is not None
        and support_minimum is not None
        and int(support_rows) >= int(support_minimum)
        and str(live_runtime_truth.get("support_route_verdict") or "").strip() in {"exact_bucket_supported", "exact_live_bucket_supported"}
    )

    support_delta = _first_int(
        support_progress.get("delta_vs_previous"),
        support_progress.get("support_delta_vs_previous"),
        topk_support_context.get("support_delta_vs_previous"),
        topk_support_context.get("delta_vs_previous"),
    )
    support_previous_rows = _first_int(
        support_progress.get("previous_rows"),
        topk_support_context.get("support_previous_rows"),
    )
    stagnant_run_count = _first_int(
        support_progress.get("stagnant_run_count"),
        topk_support_context.get("support_progress_stagnant_run_count"),
        topk_support_context.get("stagnant_run_count"),
    ) or 0
    stalled_support = bool(
        support_progress.get("stalled_support_accumulation")
        or topk_support_context.get("support_progress_stalled_support_accumulation")
        or topk_support_context.get("stalled_support_accumulation")
        or (stagnant_run_count > 0 and (support_delta is None or int(support_delta) <= 0))
    )
    estimated_heartbeats_to_support = None
    estimated_hours_at_hourly_heartbeat = None
    estimated_days_at_hourly_heartbeat = None
    if support_gap is not None and int(support_gap) <= 0:
        time_to_evidence_status = "support_already_met"
        time_to_evidence_summary = "即時精準支持已達最低樣本；仍需檢查熔斷與場館證據鏈。"
        estimated_heartbeats_to_support = 0
        estimated_hours_at_hourly_heartbeat = 0
        estimated_days_at_hourly_heartbeat = 0.0
        alternative_solution_required = False
    elif support_gap is not None and support_delta is not None and int(support_delta) > 0:
        estimated_heartbeats_to_support = max((int(support_gap) + int(support_delta) - 1) // int(support_delta), 1)
        estimated_hours_at_hourly_heartbeat = estimated_heartbeats_to_support
        estimated_days_at_hourly_heartbeat = round(estimated_hours_at_hourly_heartbeat / 24.0, 2)
        time_to_evidence_status = "estimable_from_recent_delta"
        time_to_evidence_summary = (
            f"即時精準支持最近增加 {int(support_delta)} 筆（{support_previous_rows if support_previous_rows is not None else '—'}→"
            f"{support_rows if support_rows is not None else '—'}），以每輪同速估算還需 {estimated_heartbeats_to_support} 輪；"
            f"若工程心跳維持約每小時一次，約 {estimated_days_at_hourly_heartbeat} 天。"
        )
        alternative_solution_required = bool(estimated_days_at_hourly_heartbeat > 7.0)
    elif support_gap is not None:
        time_to_evidence_status = "indeterminate_stalled_support" if stalled_support else "indeterminate_no_positive_delta"
        time_to_evidence_summary = (
            f"即時精準支持仍缺 {int(support_gap)} 筆，但最近沒有正向增量；無法給出可靠完成時間，"
            "本輪必須啟動替代解法評審而不是只等待。"
        )
        alternative_solution_required = True
    else:
        time_to_evidence_status = "unknown_support_gap"
        time_to_evidence_summary = "即時精準支持缺口未知；先修復 support artifact，再評估完成時間與替代解法。"
        alternative_solution_required = True

    time_to_evidence = {
        "status": time_to_evidence_status,
        "summary": time_to_evidence_summary,
        "current_rows": support_rows,
        "minimum_support_rows": support_minimum,
        "gap_to_minimum": support_gap,
        "delta_vs_previous": support_delta,
        "previous_rows": support_previous_rows,
        "stagnant_run_count": stagnant_run_count,
        "stalled_support_accumulation": stalled_support,
        "estimated_heartbeats_to_support": estimated_heartbeats_to_support,
        "heartbeat_interval_assumption_hours": 1,
        "estimated_hours_at_hourly_heartbeat": estimated_hours_at_hourly_heartbeat,
        "estimated_days_at_hourly_heartbeat": estimated_days_at_hourly_heartbeat,
        "alternative_solution_required": alternative_solution_required,
        "operator_message": time_to_evidence_summary,
    }
    alternative_solution_review = {
        "status": "required" if alternative_solution_required else "watch_only",
        "trigger": "time_to_evidence_over_7_days_or_indeterminate" if alternative_solution_required else "support_eta_within_7_days_under_recent_delta",
        "primary_alternative": "paper_shadow_reduce_only_with_range_chop_playbook" if alternative_solution_required else "continue_exact_support_accumulation",
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "allowed_today": [
            "啟動 paper-shadow 訊號帳本並追 24h pyramid outcome",
            "保留減碼 / 取消掛單 / 賣出風險降低路徑",
            "補 venue dry-run preview、ack、cancel、reconciliation 證據鏈",
        ],
        "not_allowed": ["買入 / 加倉", "把寬範圍或舊語義支持包裝成部署閉環"],
        "next_review_trigger": "每輪 heartbeat 重新計算 support_delta；若 estimated_days_at_hourly_heartbeat > 7 或無正增量，PM/工程需重排替代路線。",
        "operator_message": "即時支持若無法在可預期時間內補齊，先交付影子觀察、減風險與場館證據鏈，不開買入 / 加倉。",
    }

    release_window = _first_int(release_condition.get("recent_window"), recent_window_details.get("window_size"), 50) or 50
    release_wins = _first_int(release_condition.get("current_recent_window_wins"), recent_window_details.get("wins"))
    release_required_wins = _first_int(release_condition.get("required_recent_window_wins"))
    release_gap = _first_int(release_condition.get("additional_recent_window_wins_needed"))
    release_ready = bool(release_condition.get("release_ready"))
    if release_required_wins is None and release_window:
        release_required_wins = 15 if int(release_window) == 50 else None
    if release_gap is None and release_wins is not None and release_required_wins is not None:
        release_gap = max(int(release_required_wins) - int(release_wins), 0)
    if release_ready is False and release_gap == 0 and release_wins is not None and release_required_wins is not None:
        release_ready = int(release_wins) >= int(release_required_wins)
    release_known = bool(release_condition or recent_window_details or release_wins is not None)
    release_passed = bool(release_ready or (release_known and release_gap == 0 and release_wins is not None))

    live_ready = bool(execution_surface_contract.get("live_ready"))
    risk_qualified_count = _to_int(topk.get("risk_qualified_count")) or _to_int(high_conviction_shadow.get("risk_qualified_count")) or 0
    runtime_blocked_candidate_count = _to_int(topk.get("runtime_blocked_candidate_count")) or _to_int(high_conviction_shadow.get("runtime_blocked_candidate_count")) or 0
    deployable_count = _to_int(topk.get("deployable_count")) or _to_int(high_conviction_shadow.get("deployable_count")) or 0
    nearest_candidate = _nearest_high_conviction_candidate(topk)
    candidate_model = _first_text(
        nearest_candidate.get("model_name"),
        nearest_candidate.get("model"),
        _as_dict(high_conviction_shadow.get("nearest_candidate")).get("model_name"),
        "no_model_candidate",
    ) or "no_model_candidate"
    candidate_threshold = _first_text(nearest_candidate.get("threshold_name"), nearest_candidate.get("top_k"), nearest_candidate.get("threshold"))
    model_shadow_ready = bool(
        (risk_qualified_count > 0 and runtime_blocked_candidate_count > 0 and deployable_count == 0)
        or high_conviction_shadow.get("shadow_available")
    )
    model_gate_passed = bool(deployable_count > 0)
    model_gate_status = "passed" if model_gate_passed else ("shadow_ready" if model_shadow_ready else "blocked")

    credential_present = bool(
        venue_record.get("credentials_configured")
        or _as_dict(account.get("health")).get("credentials_configured")
        or _as_dict(execution.get("health")).get("credentials_configured")
    )
    venue_blockers = [str(item) for item in _as_list(venue_record.get("blockers")) if str(item).strip()]
    live_ready_blockers = [str(item) for item in _as_list(execution_surface_contract.get("live_ready_blockers")) if str(item).strip()]
    proof_state = _first_text(venue_record.get("proof_state"), "missing_runtime_backed_order_lifecycle")
    venue_passed = bool(credential_present and not venue_blockers and live_ready and proof_state in {"runtime_backed_proof_complete", "ready"})
    venue_status = "passed" if venue_passed else "blocked"

    shadow_ready = bool(model_shadow_ready or range_chop.get("shadow_available") or range_chop.get("risk_reduction_allowed"))
    canary_ready = bool(live_ready and model_gate_passed and support_passed and release_passed and venue_passed)
    risk_on_order_enabled = False
    order_submission_enabled = False
    readiness_status = "canary_ready" if canary_ready else ("shadow_reduce_only" if shadow_ready or range_chop.get("risk_reduction_allowed") else "blocked")

    model_detail_parts = []
    if risk_qualified_count:
        model_detail_parts.append(f"離線 / 風控已過 {risk_qualified_count} 筆")
    if runtime_blocked_candidate_count:
        model_detail_parts.append(f"執行期阻塞候選 {runtime_blocked_candidate_count} 筆")
    model_detail_parts.append(f"可部署樣本 {deployable_count} 筆")

    support_summary = (
        f"即時部署精準支持 {support_rows if support_rows is not None else '—'}/{support_minimum if support_minimum is not None else '—'}"
        f"，還差 {support_gap if support_gap is not None else '—'}"
    )
    release_summary = (
        f"最近 {release_window} 筆目前 {release_wins if release_wins is not None else '—'}/{release_window} 勝"
        f"，解除門檻 {release_required_wins if release_required_wins is not None else '—'} 勝"
        f"，還差 {release_gap if release_gap is not None else '—'} 勝"
    )

    gates = [
        {
            "key": "model_gate",
            "label": "模型 gate",
            "status": model_gate_status,
            "passed": model_gate_passed,
            "shadow_ready": model_shadow_ready,
            "current": deployable_count,
            "required": 1,
            "gap": 0 if model_gate_passed else 1,
            "summary": "；".join(model_detail_parts),
            "next_action": "研究勝出模型可進影子觀察；不可標成可部署，直到即時 gate 與場館證據鏈通過。",
        },
        {
            "key": "current_live_support_gate",
            "label": "即時支持 gate",
            "status": "passed" if support_passed else "blocked",
            "passed": support_passed,
            "current": support_rows,
            "required": support_minimum,
            "gap": support_gap,
            "summary": support_summary,
            "next_action": "等待精準分桶累積到最低支持樣本；寬範圍 / 離線 / 參考支持不可替代。",
        },
        {
            "key": "circuit_breaker_gate",
            "label": "熔斷 gate",
            "status": "passed" if release_passed else "blocked",
            "passed": release_passed,
            "current": release_wins,
            "required": release_required_wins,
            "gap": release_gap,
            "summary": release_summary,
            "next_action": "最近窗勝場未達門檻前，只做 shadow / reduce-only，不升級 canary。",
        },
        {
            "key": "venue_gate",
            "label": "場館 gate",
            "status": venue_status,
            "passed": venue_passed,
            "current": 1 if credential_present else 0,
            "required": 1,
            "gap": 0 if credential_present else 1,
            "summary": "credential present 已確認" if credential_present else "credential present 尚未有 runtime-backed proof",
            "blockers": venue_blockers or live_ready_blockers,
            "next_action": _first_text(venue_record.get("operator_next_action"), "補齊 credential presence、order ack、cancel、fill lifecycle 與 reconciliation proof。"),
        },
        {
            "key": "shadow_observation_gate",
            "label": "影子觀察 gate",
            "status": "ready" if shadow_ready else "blocked",
            "passed": shadow_ready,
            "current": 1 if shadow_ready else 0,
            "required": 1,
            "gap": 0 if shadow_ready else 1,
            "summary": "影子觀察可記錄訊號 / 假想 entry / 24h 結果；不送單。" if shadow_ready else "尚未形成可記錄的影子觀察候選。",
            "next_action": "今天可啟動影子觀察、dry-run preview、ack / cancel simulation 與減風險演練。",
        },
    ]
    blocking_gate = next((gate for gate in gates if not gate.get("passed") and gate["key"] != "model_gate"), None)
    if blocking_gate is None and not model_gate_passed:
        blocking_gate = gates[0]

    what_can_do_now = [
        "啟動影子觀察並寫入 Shadow Trade Ledger",
        "做 venue dry-run proof：order preview、ack simulation、cancel simulation、reconciliation check",
        "減碼 / 取消掛單 / 賣出風險降低路徑仍可用",
        "持續收集即時部署精準支持與 24h pyramid outcome",
    ]
    what_cannot_do_now = [
        "買入 / 加倉仍鎖住，直到即時支持 gate、熔斷 gate、場館 gate 全過",
        "不能把 OOS 勝出模型、寬範圍分桶或參考支持標成可部署",
        "不能啟用風險進攻自動下單或完整實單自動化",
    ]

    execution_readiness = {
        "status": readiness_status,
        "stage_label": "Shadow / Reduce-only" if not canary_ready else "Canary-ready",
        "canary_ready": canary_ready,
        "live_ready": live_ready,
        "risk_on_order_enabled": risk_on_order_enabled,
        "order_submission_enabled": order_submission_enabled,
        "blocking_gate_key": blocking_gate.get("key") if blocking_gate else None,
        "blocking_gate_label": blocking_gate.get("label") if blocking_gate else None,
        "operator_message": "實戰準備度目前停在 Shadow / Reduce-only：可以演練與記錄，不可買入 / 加倉。" if not canary_ready else "所有 gate 已通過；只能進入最小 canary，不是 full deploy。",
        "gates": gates,
        "what_can_do_now": what_can_do_now,
        "what_cannot_do_now": what_cannot_do_now,
        "time_to_evidence": time_to_evidence,
        "alternative_solution_review": alternative_solution_review,
        "next_release_condition": "exact support ≥ 50/50、recent 50 ≥ 15 勝、venue proof chain 完整，且 live_ready=true。",
    }

    symbol = str(payload.get("symbol") or "BTCUSDT")
    timestamp = str(payload.get("timestamp") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    structure_bucket = _first_text(live_runtime_truth.get("structure_bucket"), live_runtime_truth.get("current_live_structure_bucket"), "—") or "—"
    regime = f"{_first_text(live_runtime_truth.get('regime_label'), '—')} / {_first_text(live_runtime_truth.get('regime_gate'), '—')} / {structure_bucket}"
    confidence = _first_float(live_runtime_truth.get("confidence"))
    entry_id_timestamp = timestamp.replace(":", "").replace("-", "").replace(".", "")
    shadow_entry = {
        "id": f"shadow-{symbol}-{entry_id_timestamp}",
        "signal_time": timestamp,
        "candidate_model": candidate_model,
        "candidate_threshold": candidate_threshold,
        "confidence": confidence,
        "regime": regime,
        "hypothetical_entry": {
            "symbol": symbol,
            "side": "shadow_long_observation",
            "entry_source": "next_runtime_signal_close_or_preview_price",
            "order_submission_enabled": False,
            "operator_copy": "假想 entry 只記錄，不送單、不加倉。",
        },
        "outcome_24h": {
            "status": "pending_observation_window",
            "window_hours": 24,
            "pnl_pct": None,
            "pyramid_win": None,
        },
        "pyramid_win": None,
        "operator_note": "此列是影子訊號帳本 entry；用來回答 24h 後是否符合 pyramid win，不是委託紀錄。",
    }
    shadow_trade_ledger = {
        "status": "recording_ready" if shadow_ready else "waiting_for_shadow_candidate",
        "mode": "paper_shadow_no_order",
        "order_submission_enabled": False,
        "schema": ["signal_time", "candidate_model", "confidence", "regime", "hypothetical_entry", "outcome_24h", "pyramid_win"],
        "entries": [shadow_entry] if shadow_ready else [],
        "operator_message": "Shadow Trade Ledger 會記錄每個影子訊號、假想 entry 與 24h outcome；它不是下單帳本。",
    }

    venue_label = _first_text(venue_record.get("venue"), execution.get("venue"), "unknown") or "unknown"
    venue_dry_run_proof = {
        "status": "ready" if venue_passed else "blocked_missing_runtime_backed_proof",
        "venue": venue_label,
        "credential_present": credential_present,
        "secrets_redacted": True,
        "proof_state": proof_state,
        "blockers": venue_blockers or live_ready_blockers or ["credential / order ack / fill lifecycle proof 尚未完成"],
        "operator_next_action": _first_text(venue_record.get("operator_next_action"), "先跑 dry-run preview，再補 ack / cancel / reconciliation proof。"),
        "verify_next": _first_text(venue_record.get("verify_next"), "python scripts/execution_metadata_smoke.py --symbol BTCUSDT --venues okx"),
        "order_preview": {
            "status": "preview_available",
            "symbol": symbol,
            "side": "buy_preview_only",
            "qty": 0.001,
            "order_submission_enabled": False,
            "runtime_backed": False,
        },
        "ack_simulation": {
            "status": "simulation_only_waiting_runtime_ack",
            "runtime_backed": False,
        },
        "cancel_simulation": {
            "status": "simulation_only_waiting_runtime_cancel_ack",
            "runtime_backed": False,
        },
        "reconciliation_check": {
            "status": _first_text(execution_reconciliation.get("status"), "limited_evidence_no_runtime_order"),
            "runtime_backed": False,
            "summary": _first_text(execution_reconciliation.get("summary"), "尚未有 runtime-backed order / fill lifecycle 可對帳。"),
        },
    }

    distance_to_canary = [
        f"即時支持 gate：{support_summary}",
        f"time-to-evidence：{time_to_evidence_summary}",
        f"熔斷 gate：{release_summary}",
        "場館 gate：credential present、order preview、ack simulation、cancel simulation、reconciliation check 都必須 runtime-backed。",
    ]
    canary_gap_answers = {
        "canary_ready": canary_ready,
        "distance_to_canary": distance_to_canary,
        "drills_available_today": what_can_do_now,
        "blocked_gate_key": blocking_gate.get("key") if blocking_gate else None,
        "blocking_gate": blocking_gate.get("label") if blocking_gate else "無",
        "blocked_gate_summary": blocking_gate.get("summary") if blocking_gate else "所有 gate 已通過，只允許最小 canary。",
        "time_to_evidence": time_to_evidence,
        "alternative_solution_review": alternative_solution_review,
        "first_canary_plan_if_all_gates_pass": {
            "exposure_pct_max": 0.01,
            "pyramid_layer": "20% first layer only",
            "symbol": symbol,
            "mode": "canary_only_after_all_gates_pass",
            "order_type": "post-only/limit preview first, then tiny canary after operator review",
            "add_exposure_enabled": False,
            "stop_conditions": ["gate regression", "venue proof stale", "24h pyramid outcome fails", "unexpected reconciliation issue"],
        },
    }

    return {
        "execution_readiness": execution_readiness,
        "shadow_trade_ledger": shadow_trade_ledger,
        "venue_dry_run_proof": venue_dry_run_proof,
        "canary_gap_answers": canary_gap_answers,
    }



def build_execution_overview(
    status_payload: Optional[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
    control_plane: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = _as_dict(status_payload)
    config = _as_dict(config)
    control_plane = _as_dict(control_plane)

    symbol = str(payload.get("symbol") or "BTCUSDT")
    timestamp = payload.get("timestamp") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    execution_surface_contract = _as_dict(payload.get("execution_surface_contract"))
    live_runtime_truth = _as_dict(_as_dict(payload.get("execution")).get("live_runtime_truth") or execution_surface_contract.get("live_runtime_truth"))
    sleeve_routing = _as_dict(live_runtime_truth.get("sleeve_routing"))
    account = _as_dict(payload.get("account"))
    runs_by_profile = _as_dict(control_plane.get("runs_by_profile"))
    strategy_source_snapshot = build_execution_strategy_source_snapshot()
    strategy_bindings = _as_dict(strategy_source_snapshot.get("sleeve_bindings"))
    high_conviction_shadow_contract = _build_high_conviction_shadow_contract(payload)
    high_conviction_topk = _load_high_conviction_topk(payload)
    range_chop_playbook = build_range_chop_playbook(live_runtime_truth, high_conviction_topk)
    range_chop_shadow_available = bool(range_chop_playbook.get("shadow_available"))

    positions = [item for item in _as_list(account.get("positions")) if isinstance(item, dict)]
    open_orders = [item for item in _as_list(account.get("open_orders")) if isinstance(item, dict)]
    requested_symbol = account.get("requested_symbol")
    normalized_symbol = account.get("normalized_symbol")
    symbol_scope_keys = _symbol_keys(symbol, requested_symbol if isinstance(requested_symbol, str) else None, normalized_symbol if isinstance(normalized_symbol, str) else None)
    symbol_positions = _filter_records_for_symbol(positions, symbol_scope_keys)
    symbol_open_orders = _filter_records_for_symbol(open_orders, symbol_scope_keys)

    balance = _as_dict(account.get("balance"))
    balance_total = _to_float(balance.get("total"))
    balance_free = _to_float(balance.get("free"))
    allocated_capital = None
    if balance_total is not None and balance_free is not None:
        allocated_capital = max(float(balance_total) - float(balance_free), 0.0)

    trading_cfg = _as_dict(config.get("trading"))
    max_position_ratio = _to_float(trading_cfg.get("max_position_ratio"))
    if max_position_ratio is None:
        max_position_ratio = 0.05
    confidence = _to_float(live_runtime_truth.get("confidence"))
    deployable_capital = None
    if balance_total is not None and confidence is not None:
        deployable_capital = check_position_size(balance_total, confidence, max_position_ratio=max_position_ratio)

    active_items = {
        str(item.get("key") or "").strip(): item
        for item in _as_list(sleeve_routing.get("active_sleeves"))
        if isinstance(item, dict)
    }
    inactive_items = {
        str(item.get("key") or "").strip(): item
        for item in _as_list(sleeve_routing.get("inactive_sleeves"))
        if isinstance(item, dict)
    }
    active_count = len(active_items)
    global_blocker = str(
        live_runtime_truth.get("deployment_blocker")
        or live_runtime_truth.get("execution_guardrail_reason")
        or sleeve_routing.get("global_blocker_reason")
        or ""
    ).strip()

    cards: List[Dict[str, Any]] = []
    blocked_count = 0
    standby_count = 0
    monitoring_count = 0

    for key in PRIMARY_SLEEVE_ORDER:
        active_item = active_items.get(key)
        inactive_item = inactive_items.get(key)
        routing_item = active_item or inactive_item or {}
        fallback = PRIMARY_SLEEVE_META.get(key, {"label": key, "summary": ""})
        label = str(routing_item.get("label") or fallback.get("label") or key)
        summary = str(routing_item.get("summary") or fallback.get("summary") or "")
        active = active_item is not None
        routing_reason = str(routing_item.get("why") or "尚未取得 routing reason。")
        shadow_candidate = bool(
            key == "selective"
            and global_blocker
            and high_conviction_shadow_contract.get("shadow_available")
        )

        if active and (symbol_positions or symbol_open_orders):
            lifecycle_status = "monitoring_shared_symbol"
            next_action = "目前 symbol scope 已有持倉或掛單；先對帳 shared position / open orders，再決定是否擴充成獨立 bot runtime。"
            monitoring_count += 1
        elif active:
            lifecycle_status = "ready_preview"
            next_action = "目前 routing 允許此 sleeve；可用這張卡做 preview-level bot/profile 規劃，但 start/pause/stop mutation API 尚未落地。"
        elif shadow_candidate:
            lifecycle_status = "shadow_monitoring"
            next_action = str(high_conviction_shadow_contract.get("next_operator_action") or "啟動影子觀察運行；只記錄決策，不送單、不加倉。")
            monitoring_count += 1
        elif range_chop_shadow_available and key in {"pullback", "rebound", "selective"}:
            lifecycle_status = "range_shadow_candidate"
            next_action = str(
                range_chop_playbook.get("next_operator_action")
                or "高低震盪不是永遠不能實戰；先做影子觀察與減風險檢查，買入 / 加倉仍等即時部署門檻。"
            )
            monitoring_count += 1
        elif global_blocker:
            lifecycle_status = "blocked_preview"
            next_action = f"先解除全域 blocker：{global_blocker}。解除前不要把這個 sleeve 包裝成可啟動 bot。"
            blocked_count += 1
        else:
            lifecycle_status = "standby"
            next_action = "目前 routing 未啟用此 sleeve；先觀察 regime/gate 變化，不要預先啟動。"
            standby_count += 1

        budget = _planned_budget(
            active=active,
            total_balance=balance_total,
            deployable_capital=deployable_capital,
            active_count=active_count,
        )

        current_run = _as_dict(runs_by_profile.get(key))
        current_run_state = str(current_run.get("state") or "").strip()
        current_run_event = _as_dict(current_run.get("latest_event"))

        if current_run_state == "running":
            start_status = "already_running"
            start_reason = "此 sleeve 已有 stateful running run；可直接 pause/stop，或讓它維持目前 control-plane 狀態。"
            pause_status = "available"
            stop_status = "available"
            next_action = "目前已有 stateful running run；下一步應確認 per-bot capital / position attribution 是否已接上，而不是再重複 start。"
        elif current_run_state == "paused":
            start_status = "resume_available"
            start_reason = "此 sleeve 先前已建立 paused run；可直接 resume，不必重新建立新 run。"
            pause_status = "already_paused"
            stop_status = "available"
            next_action = "此 sleeve 目前在 paused；若要繼續，請 resume 並對齊 per-bot runtime binding。"
        elif shadow_candidate:
            start_status = "shadow_start_available"
            start_reason = str(high_conviction_shadow_contract.get("start_reason") or "可啟動影子觀察運行；只記錄決策，不送單、不加倉。")
            pause_status = "available_when_running"
            stop_status = "available_when_running"
        elif active and not global_blocker:
            start_status = "ready_control_plane"
            start_reason = "routing active，且目前沒有全域 execution blocker；可建立 stateful run control beta。"
            pause_status = "available_when_running"
            stop_status = "available_when_running"
        elif active:
            start_status = "blocked_preview"
            start_reason = f"routing 雖 active，但目前仍被 blocker 擋下：{global_blocker}。"
            pause_status = "blocked_until_started"
            stop_status = "blocked_until_started"
        else:
            start_status = "inactive_preview"
            start_reason = routing_reason
            pause_status = "blocked_until_started"
            stop_status = "blocked_until_started"

        strategy_binding = _as_dict(_as_dict(strategy_bindings.get(key)).get("recommended")) or None
        control_contract = {
            "mode": control_plane.get("controls_mode") or CONTROL_MODE,
            "start_status": start_status,
            "start_reason": start_reason,
            "pause_status": pause_status,
            "stop_status": stop_status,
            "latest_event_type": current_run.get("last_event_type"),
            "latest_event_message": current_run.get("last_event_message") or current_run_event.get("message"),
            "upgrade_required": True,
            "upgrade_prerequisite": CONTROL_PLANE_UPGRADE_PREREQUISITE,
        }
        if range_chop_shadow_available:
            control_contract.update(
                {
                    "range_chop_playbook": range_chop_playbook,
                    "risk_reduction_allowed": True,
                    "buy_add_requires_current_live_gate": True,
                    "risk_on_order_enabled": False,
                    "order_submission_enabled": False,
                }
            )
        if shadow_candidate:
            control_contract.update(
                {
                    "shadow_only": True,
                    "risk_on_order_enabled": False,
                    "shadow_mode": high_conviction_shadow_contract.get("shadow_mode") or "paper_shadow",
                    "high_conviction_topk": high_conviction_shadow_contract,
                    "upgrade_prerequisite": (
                        "先以影子觀察運行收集即時決策與事件紀錄；只有當即時精準樣本、"
                        "場館憑證 / 委託 / 成交證據鏈與單一 Bot 帳本都通過後，才能升級小流量。"
                    ),
                }
            )

        cards.append(
            {
                "key": key,
                "profile_id": key,
                "label": label,
                "summary": summary,
                "activation_status": "active" if active else ("shadow_candidate" if shadow_candidate else "inactive"),
                "lifecycle_status": lifecycle_status,
                "routing_reason": routing_reason,
                "current_regime": sleeve_routing.get("current_regime") or live_runtime_truth.get("regime_label"),
                "current_regime_gate": sleeve_routing.get("current_regime_gate") or live_runtime_truth.get("regime_gate"),
                "current_structure_bucket": sleeve_routing.get("current_structure_bucket") or live_runtime_truth.get("structure_bucket"),
                "allowed_layers": live_runtime_truth.get("allowed_layers"),
                "allowed_layers_reason": live_runtime_truth.get("allowed_layers_reason"),
                "deployment_blocker": live_runtime_truth.get("deployment_blocker"),
                "execution_guardrail_reason": live_runtime_truth.get("execution_guardrail_reason"),
                "strategy_binding": strategy_binding,
                "controls_mode": control_plane.get("controls_mode") or CONTROL_MODE,
                "current_run": current_run or None,
                "current_run_state": current_run_state or None,
                "control_contract": control_contract,
                "symbol_scoped_position_count": len(symbol_positions),
                "symbol_scoped_open_order_count": len(symbol_open_orders),
                "next_operator_action": next_action,
                **budget,
            }
        )

    controls_mode = control_plane.get("controls_mode") or CONTROL_MODE
    control_plane_summary = _as_dict(control_plane.get("summary"))
    summary = {
        "total_profiles": len(cards),
        "active_profiles": active_count,
        "standby_profiles": standby_count,
        "blocked_profiles": blocked_count,
        "monitoring_profiles": monitoring_count,
        "running_runs": control_plane_summary.get("running_runs", 0),
        "paused_runs": control_plane_summary.get("paused_runs", 0),
        "stopped_runs": control_plane_summary.get("stopped_runs", 0),
        "total_runs": control_plane_summary.get("total_runs", 0),
        "controls_mode": controls_mode,
        "allocation_rule": "equal_split_active_sleeves",
        "operator_message": control_plane.get("operator_message") or CONTROL_PLANE_OPERATOR_MESSAGE,
    }

    capital_plan = {
        "currency": balance.get("currency") or "USDT",
        "total_balance": balance_total,
        "free_balance": balance_free,
        "allocated_capital": allocated_capital,
        "deployable_capital": deployable_capital,
        "max_position_ratio": max_position_ratio,
        "confidence": confidence,
        "active_profile_count": active_count,
        "per_active_profile_budget": (float(deployable_capital) / float(active_count)) if deployable_capital is not None and active_count > 0 else None,
        "allocation_rule": "equal_split_active_sleeves",
        "symbol_scoped_position_count": len(symbol_positions),
        "symbol_scoped_open_order_count": len(symbol_open_orders),
        "operator_message": "可部署資金目前仍先依風險控管頭寸公式估算，再由啟用倉位腿均分；運行控制雖已可持久化，但每個 Bot 的資金帳本仍未落地。",
    }

    readiness_bundle = build_execution_readiness_bundle(payload, range_chop_playbook=range_chop_playbook)

    return {
        "symbol": symbol,
        "timestamp": timestamp,
        "controls_mode": controls_mode,
        "source_route": "/api/status",
        "operator_message": summary["operator_message"],
        "upgrade_prerequisite": control_plane.get("upgrade_prerequisite") or CONTROL_PLANE_UPGRADE_PREREQUISITE,
        "summary": summary,
        "capital_plan": capital_plan,
        "strategy_source_summary": _as_dict(strategy_source_snapshot.get("summary")),
        "profile_cards": cards,
        "range_chop_playbook": range_chop_playbook,
        **readiness_bundle,
        "live_ready": bool(execution_surface_contract.get("live_ready", False)),
        "live_ready_blockers": _as_list(execution_surface_contract.get("live_ready_blockers")),
    }
