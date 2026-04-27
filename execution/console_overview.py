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

        if active and (symbol_positions or symbol_open_orders):
            lifecycle_status = "monitoring_shared_symbol"
            next_action = "目前 symbol scope 已有持倉或掛單；先對帳 shared position / open orders，再決定是否擴充成獨立 bot runtime。"
            monitoring_count += 1
        elif active:
            lifecycle_status = "ready_preview"
            next_action = "目前 routing 允許此 sleeve；可用這張卡做 preview-level bot/profile 規劃，但 start/pause/stop mutation API 尚未落地。"
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

        cards.append(
            {
                "key": key,
                "profile_id": key,
                "label": label,
                "summary": summary,
                "activation_status": "active" if active else "inactive",
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
                "control_contract": {
                    "mode": control_plane.get("controls_mode") or CONTROL_MODE,
                    "start_status": start_status,
                    "start_reason": start_reason,
                    "pause_status": pause_status,
                    "stop_status": stop_status,
                    "latest_event_type": current_run.get("last_event_type"),
                    "latest_event_message": current_run.get("last_event_message") or current_run_event.get("message"),
                    "upgrade_required": True,
                    "upgrade_prerequisite": CONTROL_PLANE_UPGRADE_PREREQUISITE,
                },
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
        "live_ready": bool(execution_surface_contract.get("live_ready", False)),
        "live_ready_blockers": _as_list(execution_surface_contract.get("live_ready_blockers")),
    }
