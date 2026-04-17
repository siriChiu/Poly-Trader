from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from fastapi import HTTPException
from sqlalchemy import text

CONTROL_MODE = "stateful_run_control_beta"
RUNTIME_BINDING_STATUS = "control_plane_only"
CONTROL_PLANE_OPERATOR_MESSAGE = (
    "Execution Console 現在已具備 stateful /api/execution/runs control plane；"
    "start/pause/stop 與 per-run event log 會持久化，且 run 已可鏡像 symbol-scoped runtime / reconciliation 摘要，"
    "但 per-bot capital / position / order ledger 仍未接上。"
)
CONTROL_PLANE_UPGRADE_PREREQUISITE = (
    "下一步必須把 per-bot capital / position attribution 與 ExecutionService 綁到 run，"
    "否則這仍是 stateful control plane beta，不是完整 bot runtime。"
)

PRIMARY_SLEEVE_ORDER = ("trend", "pullback", "rebound", "selective")
PRIMARY_SLEEVE_META: Dict[str, Dict[str, str]] = {
    "trend": {
        "label": "趨勢承接",
        "summary": "順著既有 4H 結構承接 pullback，維持中頻主線節奏。",
    },
    "pullback": {
        "label": "回調承接",
        "summary": "等待較深 pullback 再進場，優先服務 bull / chop 的再部署窗口。",
    },
    "rebound": {
        "label": "深跌回補",
        "summary": "只在極端 oversold / crash pocket 嘗試反身回補，屬於反轉型 sleeve。",
    },
    "selective": {
        "label": "高信念精選",
        "summary": "提高品質門檻與 top-k 篩選，只保留最強交易候選。",
    },
}

_STATE_LABELS = {
    "running": "運行中",
    "paused": "已暫停",
    "stopped": "已停止",
}

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS execution_profiles (
        id TEXT PRIMARY KEY,
        profile_type TEXT NOT NULL,
        label TEXT,
        summary TEXT,
        symbol TEXT,
        venue TEXT,
        mode TEXT,
        activation_status TEXT,
        lifecycle_status TEXT,
        planned_budget_amount REAL,
        planned_budget_ratio REAL,
        routing_reason TEXT,
        control_mode TEXT,
        current_regime TEXT,
        current_regime_gate TEXT,
        current_structure_bucket TEXT,
        source_route TEXT,
        snapshot_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS execution_runs (
        id TEXT PRIMARY KEY,
        profile_id TEXT NOT NULL,
        label TEXT,
        symbol TEXT,
        venue TEXT,
        mode TEXT,
        state TEXT NOT NULL,
        control_mode TEXT,
        runtime_binding_status TEXT,
        budget_amount REAL,
        budget_ratio REAL,
        capital_currency TEXT,
        activation_status TEXT,
        lifecycle_status TEXT,
        start_time TEXT NOT NULL,
        stop_time TEXT,
        stop_reason TEXT,
        operator_note TEXT,
        last_event_type TEXT,
        last_event_message TEXT,
        last_event_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS execution_run_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT,
        payload_json TEXT,
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_execution_runs_profile_state_updated ON execution_runs (profile_id, state, updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_execution_run_events_run_created ON execution_run_events (run_id, created_at)",
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")



def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)



def _json_loads(value: Optional[str]) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return None



def _rows(db, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    result = db.execute(text(query), params or {})
    return [dict(row) for row in result.mappings().all()]



def _one(db, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    result = db.execute(text(query), params or {})
    row = result.mappings().first()
    return dict(row) if row else None



def _run_priority(state: Optional[str]) -> int:
    normalized = str(state or "").lower()
    if normalized == "running":
        return 0
    if normalized == "paused":
        return 1
    return 2



def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}



def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []



def _normalize_symbol_key(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.replace("/", "").replace("-", "").replace("_", "").upper()



def _record_symbol_key(record: Any) -> Optional[str]:
    if not isinstance(record, dict):
        return None
    for key in ("symbol", "instId", "market", "pair"):
        value = record.get(key)
        normalized = _normalize_symbol_key(value)
        if normalized:
            return normalized
    return None



def _compact_preview_record(record: Dict[str, Any], *, kind: str) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    if kind == "position":
        preferred_keys = (
            "symbol",
            "instId",
            "market",
            "pair",
            "side",
            "positionSide",
            "size",
            "qty",
            "amount",
            "contracts",
            "positionAmt",
            "entryPrice",
            "avgPrice",
            "markPrice",
            "unrealizedPnl",
            "pnl",
            "status",
            "state",
        )
    else:
        preferred_keys = (
            "symbol",
            "instId",
            "market",
            "pair",
            "side",
            "qty",
            "amount",
            "size",
            "price",
            "avgPrice",
            "type",
            "status",
            "state",
            "order_id",
            "id",
            "clientOrderId",
            "client_order_id",
            "reduceOnly",
        )
    compact: Dict[str, Any] = {}
    for key in preferred_keys:
        value = record.get(key)
        if value is None:
            continue
        compact[key] = value
    return compact



def _compact_preview_records(records: Iterable[Dict[str, Any]], *, kind: str, limit: int = 3) -> List[Dict[str, Any]]:
    preview: List[Dict[str, Any]] = []
    for record in records:
        if len(preview) >= limit:
            break
        compact = _compact_preview_record(record, kind=kind)
        if compact:
            preview.append(compact)
    return preview



def _runtime_binding_artifacts(row: Dict[str, Any], status_payload: Optional[Dict[str, Any]]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    status_payload = _as_dict(status_payload)
    execution = _as_dict(status_payload.get("execution"))
    account = _as_dict(status_payload.get("account"))
    reconciliation = _as_dict(status_payload.get("execution_reconciliation"))
    live_runtime_truth = _as_dict(
        execution.get("live_runtime_truth")
        or _as_dict(status_payload.get("execution_surface_contract")).get("live_runtime_truth")
    )
    guardrails = _as_dict(execution.get("guardrails"))

    run_symbol = row.get("symbol")
    run_venue = str(row.get("venue") or "").lower()
    run_symbol_key = _normalize_symbol_key(run_symbol)
    status_symbol_keys = {
        key
        for key in (
            _normalize_symbol_key(status_payload.get("symbol")),
            _normalize_symbol_key(account.get("requested_symbol")),
            _normalize_symbol_key(account.get("normalized_symbol")),
        )
        if key
    }
    status_venue = str(execution.get("venue") or row.get("venue") or "").lower()
    symbol_match = bool(run_symbol_key and run_symbol_key in status_symbol_keys)
    venue_match = not run_venue or not status_venue or run_venue == status_venue

    positions = [item for item in _as_list(account.get("positions")) if isinstance(item, dict)]
    open_orders = [item for item in _as_list(account.get("open_orders")) if isinstance(item, dict)]
    symbol_positions = [item for item in positions if _record_symbol_key(item) == run_symbol_key]
    symbol_open_orders = [item for item in open_orders if _record_symbol_key(item) == run_symbol_key]
    balance = _as_dict(account.get("balance"))

    last_order = _as_dict(guardrails.get("last_order"))
    last_order_symbol_match = not last_order or _record_symbol_key(last_order) == run_symbol_key
    matched_runtime = bool(status_payload) and symbol_match and venue_match
    mirrored_components = [
        "live_runtime_truth",
        "account_snapshot",
        "execution_reconciliation",
        "execution_guardrails",
        "shared_symbol_preview",
    ] if matched_runtime else []
    operator_action = (
        _as_dict(reconciliation.get("recovery_state")).get("operator_action")
        or _as_dict(reconciliation.get("lifecycle_audit")).get("operator_action")
        or CONTROL_PLANE_UPGRADE_PREREQUISITE
    )
    summary = (
        "此 run 已鏡像到目前 /api/status 的 symbol-scoped runtime / account / reconciliation 視圖；"
        "但資金、倉位、掛單仍是 shared-symbol preview，不是 per-bot ledger。"
        if matched_runtime
        else "此 run 目前只有 stateful control-plane event log；尚未對齊到當前 runtime symbol/venue snapshot。"
    )
    ownership_boundary = {
        "ledger_scope": "shared_symbol_preview_only" if matched_runtime else "control_plane_only",
        "capital_attribution": "planned_budget_vs_shared_account_balance" if matched_runtime else "not_bound",
        "position_attribution": "symbol_scoped_preview_only" if matched_runtime else "not_bound",
        "open_order_attribution": "symbol_scoped_preview_only" if matched_runtime else "not_bound",
        "summary": (
            "run 目前只擁有 planned budget 與 lifecycle/event log；實際 balance / positions / open orders 仍是 shared-symbol preview。"
            if matched_runtime
            else "run 尚未綁到 runtime symbol/venue snapshot，因此連 shared-symbol preview 都還沒對齊。"
        ),
    }
    contract = {
        "status": "symbol_scope_runtime_mirror" if matched_runtime else "control_plane_only",
        "scope": "symbol_scoped_runtime_preview" if matched_runtime else "control_plane_event_log_only",
        "summary": summary,
        "mirrored_components": mirrored_components,
        "missing_components": [
            "per_bot_capital_ledger",
            "per_bot_position_attribution",
            "per_bot_open_order_attribution",
            "venue_fill_ownership",
            "restart_replay_ownership",
        ],
        "ownership_boundary": ownership_boundary,
        "operator_action": operator_action,
        "match": {
            "run_symbol": run_symbol,
            "status_symbol": status_payload.get("symbol"),
            "symbol_match": symbol_match,
            "run_venue": row.get("venue"),
            "status_venue": execution.get("venue"),
            "venue_match": venue_match,
        },
    }
    snapshot = {
        "symbol": run_symbol,
        "venue": row.get("venue"),
        "mode": execution.get("mode") or row.get("mode"),
        "live_runtime_truth": {
            "runtime_closure_state": live_runtime_truth.get("runtime_closure_state"),
            "runtime_closure_summary": live_runtime_truth.get("runtime_closure_summary"),
            "regime_label": live_runtime_truth.get("regime_label"),
            "regime_gate": live_runtime_truth.get("regime_gate"),
            "structure_bucket": live_runtime_truth.get("structure_bucket"),
            "allowed_layers": live_runtime_truth.get("allowed_layers"),
            "allowed_layers_reason": live_runtime_truth.get("allowed_layers_reason"),
            "deployment_blocker": live_runtime_truth.get("deployment_blocker"),
            "execution_guardrail_reason": live_runtime_truth.get("execution_guardrail_reason"),
        } if matched_runtime else None,
        "account_snapshot": {
            "captured_at": account.get("captured_at"),
            "degraded": account.get("degraded"),
            "operator_message": account.get("operator_message"),
            "recovery_hint": account.get("recovery_hint"),
            "requested_symbol": account.get("requested_symbol"),
            "normalized_symbol": account.get("normalized_symbol"),
            "position_count": len(symbol_positions),
            "open_order_count": len(symbol_open_orders),
        } if matched_runtime else None,
        "capital_preview": {
            "allocation_scope": "run_budget_vs_shared_balance_preview",
            "ownership_status": "shared_symbol_preview_only",
            "budget_amount": row.get("budget_amount"),
            "budget_ratio": row.get("budget_ratio"),
            "balance_total": balance.get("total"),
            "balance_free": balance.get("free"),
            "currency": row.get("capital_currency") or balance.get("currency") or "USDT",
            "summary": "run budget 是 control-plane 規劃值；實際可用資金仍來自 account snapshot 的 shared balance。",
        } if matched_runtime else None,
        "shared_symbol_preview": {
            "scope": "symbol_scoped_account_preview",
            "ownership_status": "shared_symbol_preview_only",
            "ownership_summary": "這裡顯示的是 run 對應 symbol 的 shared account preview，不代表倉位/掛單已完成 per-bot attribution。",
            "captured_at": account.get("captured_at"),
            "positions_total_count": len(symbol_positions),
            "open_orders_total_count": len(symbol_open_orders),
            "balance": {
                "total": balance.get("total"),
                "free": balance.get("free"),
                "currency": balance.get("currency") or row.get("capital_currency") or "USDT",
            },
            "positions": _compact_preview_records(symbol_positions, kind="position"),
            "open_orders": _compact_preview_records(symbol_open_orders, kind="order"),
        } if matched_runtime else None,
        "reconciliation": {
            "status": reconciliation.get("status"),
            "summary": reconciliation.get("summary"),
            "checked_at": reconciliation.get("checked_at"),
            "recovery_state": _as_dict(reconciliation.get("recovery_state")) or None,
            "lifecycle_audit": _as_dict(reconciliation.get("lifecycle_audit")) or None,
        } if matched_runtime else None,
        "guardrails": {
            "kill_switch": guardrails.get("kill_switch"),
            "daily_loss_halt": guardrails.get("daily_loss_halt"),
            "failure_halt": guardrails.get("failure_halt"),
            "last_reject": _as_dict(guardrails.get("last_reject")) or None,
            "last_failure": _as_dict(guardrails.get("last_failure")) or None,
            "last_order": last_order if last_order and last_order_symbol_match else None,
        } if matched_runtime else None,
    }
    return contract, snapshot



def _serialize_event(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": row.get("id"),
        "run_id": row.get("run_id"),
        "profile_id": row.get("profile_id"),
        "event_type": row.get("event_type"),
        "level": row.get("level"),
        "message": row.get("message"),
        "payload": _json_loads(row.get("payload_json")),
        "created_at": row.get("created_at"),
    }



def _serialize_run(
    row: Dict[str, Any],
    events: Optional[List[Dict[str, Any]]] = None,
    status_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    current_state = str(row.get("state") or "stopped")
    recent_events = events or []
    latest_event = recent_events[0] if recent_events else None
    runtime_binding_contract, runtime_binding_snapshot = _runtime_binding_artifacts(row, status_payload)
    return {
        "run_id": row.get("id"),
        "profile_id": row.get("profile_id"),
        "label": row.get("label"),
        "symbol": row.get("symbol"),
        "venue": row.get("venue"),
        "mode": row.get("mode"),
        "state": current_state,
        "state_label": _STATE_LABELS.get(current_state, current_state or "unknown"),
        "control_mode": row.get("control_mode") or CONTROL_MODE,
        "runtime_binding_status": row.get("runtime_binding_status") or RUNTIME_BINDING_STATUS,
        "budget_amount": row.get("budget_amount"),
        "budget_ratio": row.get("budget_ratio"),
        "capital_currency": row.get("capital_currency") or "USDT",
        "activation_status": row.get("activation_status"),
        "lifecycle_status": row.get("lifecycle_status"),
        "start_time": row.get("start_time"),
        "stop_time": row.get("stop_time"),
        "stop_reason": row.get("stop_reason"),
        "operator_note": row.get("operator_note"),
        "last_event_type": row.get("last_event_type"),
        "last_event_message": row.get("last_event_message"),
        "last_event_at": row.get("last_event_at"),
        "runtime_binding_contract": runtime_binding_contract,
        "runtime_binding_snapshot": runtime_binding_snapshot,
        "action_contract": {
            "can_pause": current_state == "running",
            "can_resume": current_state == "paused",
            "can_stop": current_state in {"running", "paused"},
            "upgrade_prerequisite": CONTROL_PLANE_UPGRADE_PREREQUISITE,
        },
        "latest_event": latest_event,
        "recent_events": recent_events,
    }



def _serialize_profile(row: Dict[str, Any], current_run: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    snapshot = _json_loads(row.get("snapshot_json")) or {}
    return {
        "profile_id": row.get("id"),
        "profile_type": row.get("profile_type") or "primary_sleeve",
        "label": row.get("label"),
        "summary": row.get("summary"),
        "symbol": row.get("symbol"),
        "venue": row.get("venue"),
        "mode": row.get("mode"),
        "activation_status": row.get("activation_status"),
        "lifecycle_status": row.get("lifecycle_status"),
        "planned_budget_amount": row.get("planned_budget_amount"),
        "planned_budget_ratio": row.get("planned_budget_ratio"),
        "routing_reason": row.get("routing_reason"),
        "control_mode": row.get("control_mode") or CONTROL_MODE,
        "current_regime": row.get("current_regime"),
        "current_regime_gate": row.get("current_regime_gate"),
        "current_structure_bucket": row.get("current_structure_bucket"),
        "source_route": row.get("source_route") or "/api/execution/overview",
        "current_run": current_run,
        "snapshot": snapshot,
    }



def ensure_execution_control_plane_schema(db) -> None:
    for statement in _SCHEMA_STATEMENTS:
        db.execute(text(statement))
    db.commit()



def _insert_event(
    db,
    *,
    run_id: str,
    profile_id: str,
    event_type: str,
    level: str,
    message: str,
    payload: Optional[Dict[str, Any]] = None,
    created_at: Optional[str] = None,
) -> None:
    created_at = created_at or _utcnow_iso()
    db.execute(
        text(
            """
            INSERT INTO execution_run_events (
                run_id, profile_id, event_type, level, message, payload_json, created_at
            ) VALUES (
                :run_id, :profile_id, :event_type, :level, :message, :payload_json, :created_at
            )
            """
        ),
        {
            "run_id": run_id,
            "profile_id": profile_id,
            "event_type": event_type,
            "level": level,
            "message": message,
            "payload_json": _json_dumps(payload or {}),
            "created_at": created_at,
        },
    )



def _active_or_latest_run_by_profile(runs: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    selected: Dict[str, Dict[str, Any]] = {}
    for row in runs:
        profile_id = str(row.get("profile_id") or "").strip()
        if not profile_id:
            continue
        existing = selected.get(profile_id)
        if existing is None:
            selected[profile_id] = row
            continue
        current_priority = _run_priority(row.get("state"))
        existing_priority = _run_priority(existing.get("state"))
        if current_priority < existing_priority:
            selected[profile_id] = row
            continue
        if current_priority == existing_priority and str(row.get("updated_at") or "") > str(existing.get("updated_at") or ""):
            selected[profile_id] = row
    return selected



def _build_profile_rows(status_payload: Dict[str, Any], overview_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    execution_payload = status_payload.get("execution") if isinstance(status_payload, dict) else {}
    execution_payload = execution_payload if isinstance(execution_payload, dict) else {}
    live_runtime_truth = execution_payload.get("live_runtime_truth") if isinstance(execution_payload, dict) else {}
    live_runtime_truth = live_runtime_truth if isinstance(live_runtime_truth, dict) else {}
    profile_cards = overview_payload.get("profile_cards") if isinstance(overview_payload, dict) else []
    profile_cards = profile_cards if isinstance(profile_cards, list) else []
    base_order = {item.get("key"): item for item in profile_cards if isinstance(item, dict)}

    rows: List[Dict[str, Any]] = []
    for key in PRIMARY_SLEEVE_ORDER:
        card = base_order.get(key) or {
            "key": key,
            "label": PRIMARY_SLEEVE_META.get(key, {}).get("label", key),
            "summary": PRIMARY_SLEEVE_META.get(key, {}).get("summary", ""),
            "activation_status": "inactive",
            "lifecycle_status": "standby",
            "routing_reason": "尚未建立 execution overview profile card。",
        }
        rows.append(
            {
                "id": key,
                "profile_type": "primary_sleeve",
                "label": card.get("label") or key,
                "summary": card.get("summary") or PRIMARY_SLEEVE_META.get(key, {}).get("summary", ""),
                "symbol": overview_payload.get("symbol") or status_payload.get("symbol") or "BTCUSDT",
                "venue": execution_payload.get("venue") or "binance",
                "mode": execution_payload.get("mode") or "paper",
                "activation_status": card.get("activation_status") or "inactive",
                "lifecycle_status": card.get("lifecycle_status") or "standby",
                "planned_budget_amount": card.get("planned_budget_amount"),
                "planned_budget_ratio": card.get("planned_budget_ratio_of_balance"),
                "routing_reason": card.get("routing_reason") or "—",
                "control_mode": CONTROL_MODE,
                "current_regime": card.get("current_regime") or live_runtime_truth.get("regime_label"),
                "current_regime_gate": card.get("current_regime_gate") or live_runtime_truth.get("regime_gate"),
                "current_structure_bucket": card.get("current_structure_bucket") or live_runtime_truth.get("structure_bucket"),
                "source_route": "/api/execution/overview",
                "snapshot_json": _json_dumps(card),
            }
        )
    return rows



def sync_execution_profiles(db, status_payload: Dict[str, Any], overview_payload: Dict[str, Any]) -> None:
    ensure_execution_control_plane_schema(db)
    now = _utcnow_iso()
    for row in _build_profile_rows(status_payload, overview_payload):
        db.execute(
            text(
                """
                INSERT INTO execution_profiles (
                    id, profile_type, label, summary, symbol, venue, mode,
                    activation_status, lifecycle_status, planned_budget_amount,
                    planned_budget_ratio, routing_reason, control_mode,
                    current_regime, current_regime_gate, current_structure_bucket,
                    source_route, snapshot_json, created_at, updated_at
                ) VALUES (
                    :id, :profile_type, :label, :summary, :symbol, :venue, :mode,
                    :activation_status, :lifecycle_status, :planned_budget_amount,
                    :planned_budget_ratio, :routing_reason, :control_mode,
                    :current_regime, :current_regime_gate, :current_structure_bucket,
                    :source_route, :snapshot_json, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    profile_type=excluded.profile_type,
                    label=excluded.label,
                    summary=excluded.summary,
                    symbol=excluded.symbol,
                    venue=excluded.venue,
                    mode=excluded.mode,
                    activation_status=excluded.activation_status,
                    lifecycle_status=excluded.lifecycle_status,
                    planned_budget_amount=excluded.planned_budget_amount,
                    planned_budget_ratio=excluded.planned_budget_ratio,
                    routing_reason=excluded.routing_reason,
                    control_mode=excluded.control_mode,
                    current_regime=excluded.current_regime,
                    current_regime_gate=excluded.current_regime_gate,
                    current_structure_bucket=excluded.current_structure_bucket,
                    source_route=excluded.source_route,
                    snapshot_json=excluded.snapshot_json,
                    updated_at=excluded.updated_at
                """
            ),
            {
                **row,
                "created_at": now,
                "updated_at": now,
            },
        )
    db.commit()



def _load_run_events(db, run_ids: Iterable[str], limit_per_run: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    run_ids = [run_id for run_id in run_ids if run_id]
    if not run_ids:
        return {}
    placeholders = ", ".join([f":run_id_{idx}" for idx, _ in enumerate(run_ids)])
    params = {f"run_id_{idx}": run_id for idx, run_id in enumerate(run_ids)}
    rows = _rows(
        db,
        f"""
        SELECT id, run_id, profile_id, event_type, level, message, payload_json, created_at
        FROM execution_run_events
        WHERE run_id IN ({placeholders})
        ORDER BY created_at DESC, id DESC
        """,
        params,
    )
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        run_id = str(row.get("run_id") or "")
        bucket = grouped.setdefault(run_id, [])
        if len(bucket) >= limit_per_run:
            continue
        bucket.append(_serialize_event(row))
    return grouped



def build_execution_control_plane_snapshot(db, status_payload: Dict[str, Any], overview_payload: Dict[str, Any]) -> Dict[str, Any]:
    sync_execution_profiles(db, status_payload, overview_payload)

    profile_rows = _rows(
        db,
        """
        SELECT *
        FROM execution_profiles
        ORDER BY CASE id
            WHEN 'trend' THEN 0
            WHEN 'pullback' THEN 1
            WHEN 'rebound' THEN 2
            WHEN 'selective' THEN 3
            ELSE 99
        END, updated_at DESC
        """,
    )
    run_rows = _rows(db, "SELECT * FROM execution_runs ORDER BY updated_at DESC, created_at DESC")
    events_by_run = _load_run_events(db, [str(row.get("id") or "") for row in run_rows])
    selected_runs_raw = _active_or_latest_run_by_profile(run_rows)
    selected_runs = {
        profile_id: _serialize_run(row, events_by_run.get(str(row.get("id") or ""), []), status_payload=status_payload)
        for profile_id, row in selected_runs_raw.items()
    }
    profiles = [_serialize_profile(row, selected_runs.get(str(row.get("id") or ""))) for row in profile_rows]
    runs = [_serialize_run(row, events_by_run.get(str(row.get("id") or ""), []), status_payload=status_payload) for row in run_rows]

    summary = {
        "total_profiles": len(profiles),
        "active_profiles": sum(1 for row in profile_rows if str(row.get("activation_status") or "") == "active"),
        "blocked_profiles": sum(1 for row in profile_rows if "blocked" in str(row.get("lifecycle_status") or "")),
        "standby_profiles": sum(1 for row in profile_rows if str(row.get("lifecycle_status") or "") == "standby"),
        "running_runs": sum(1 for row in run_rows if str(row.get("state") or "") == "running"),
        "paused_runs": sum(1 for row in run_rows if str(row.get("state") or "") == "paused"),
        "stopped_runs": sum(1 for row in run_rows if str(row.get("state") or "") == "stopped"),
        "total_runs": len(run_rows),
    }
    return {
        "controls_mode": CONTROL_MODE,
        "operator_message": CONTROL_PLANE_OPERATOR_MESSAGE,
        "upgrade_prerequisite": CONTROL_PLANE_UPGRADE_PREREQUISITE,
        "summary": summary,
        "profiles": profiles,
        "runs": runs,
        "runs_by_profile": selected_runs,
    }



def _require_profile_row(db, profile_id: str) -> Dict[str, Any]:
    row = _one(db, "SELECT * FROM execution_profiles WHERE id = :profile_id", {"profile_id": profile_id})
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "profile_not_found", "message": f"Execution profile '{profile_id}' 不存在"})
    return row



def _require_run_row(db, run_id: str) -> Dict[str, Any]:
    row = _one(db, "SELECT * FROM execution_runs WHERE id = :run_id", {"run_id": run_id})
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "run_not_found", "message": f"Execution run '{run_id}' 不存在"})
    return row



def _current_run_for_profile(db, profile_id: str) -> Optional[Dict[str, Any]]:
    rows = _rows(
        db,
        "SELECT * FROM execution_runs WHERE profile_id = :profile_id ORDER BY updated_at DESC, created_at DESC",
        {"profile_id": profile_id},
    )
    selected = _active_or_latest_run_by_profile(rows).get(profile_id)
    return selected



def start_execution_profile_run(db, profile_id: str, status_payload: Dict[str, Any], overview_payload: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = build_execution_control_plane_snapshot(db, status_payload, overview_payload)
    profile_row = _require_profile_row(db, profile_id)
    profile_snapshot = _json_loads(profile_row.get("snapshot_json")) or {}
    control_contract = profile_snapshot.get("control_contract") if isinstance(profile_snapshot, dict) else {}
    control_contract = control_contract if isinstance(control_contract, dict) else {}
    start_status = str(control_contract.get("start_status") or "")
    if start_status.startswith("blocked") or start_status.startswith("inactive"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "profile_not_startable",
                "message": "目前 routing / blocker 不允許啟動這個 sleeve run。",
                "context": {
                    "profile_id": profile_id,
                    "start_status": start_status,
                    "start_reason": control_contract.get("start_reason") or profile_row.get("routing_reason"),
                },
            },
        )

    existing = _current_run_for_profile(db, profile_id)
    now = _utcnow_iso()
    if existing and str(existing.get("state") or "") == "running":
        _insert_event(
            db,
            run_id=str(existing.get("id")),
            profile_id=profile_id,
            event_type="start_requested_while_running",
            level="info",
            message="此 run 已在運行中；忽略重複 start。",
            payload={"action_result": "noop_already_running"},
            created_at=now,
        )
        db.execute(
            text(
                """
                UPDATE execution_runs
                SET last_event_type = :last_event_type,
                    last_event_message = :last_event_message,
                    last_event_at = :last_event_at,
                    updated_at = :updated_at
                WHERE id = :run_id
                """
            ),
            {
                "run_id": existing.get("id"),
                "last_event_type": "start_requested_while_running",
                "last_event_message": "此 run 已在運行中；忽略重複 start。",
                "last_event_at": now,
                "updated_at": now,
            },
        )
        db.commit()
        return {
            "action": "start",
            "action_result": "noop_already_running",
            "operator_message": "此 bot run 已在運行中；保留原狀。",
            "snapshot": build_execution_control_plane_snapshot(db, status_payload, overview_payload),
            "run": get_execution_run_detail(db, str(existing.get("id")), status_payload=status_payload),
        }

    if existing and str(existing.get("state") or "") == "paused":
        db.execute(
            text(
                """
                UPDATE execution_runs
                SET state = 'running',
                    stop_time = NULL,
                    stop_reason = NULL,
                    last_event_type = :last_event_type,
                    last_event_message = :last_event_message,
                    last_event_at = :last_event_at,
                    updated_at = :updated_at
                WHERE id = :run_id
                """
            ),
            {
                "run_id": existing.get("id"),
                "last_event_type": "resumed",
                "last_event_message": "Execution run 已恢復為 running。",
                "last_event_at": now,
                "updated_at": now,
            },
        )
        _insert_event(
            db,
            run_id=str(existing.get("id")),
            profile_id=profile_id,
            event_type="resumed",
            level="info",
            message="Execution run 已恢復為 running。",
            payload={"state": "running", "runtime_binding_status": RUNTIME_BINDING_STATUS},
            created_at=now,
        )
        db.commit()
        return {
            "action": "start",
            "action_result": "resumed",
            "operator_message": "已恢復既有 paused run。",
            "snapshot": build_execution_control_plane_snapshot(db, status_payload, overview_payload),
            "run": get_execution_run_detail(db, str(existing.get("id")), status_payload=status_payload),
        }

    run_id = str(uuid.uuid4())
    currency = (
        (overview_payload.get("capital_plan") or {}).get("currency")
        if isinstance(overview_payload, dict)
        else None
    ) or "USDT"
    message = "Execution run 已建立；目前是 stateful control-plane beta，尚未綁定真實 per-bot capital / order ledger。"
    db.execute(
        text(
            """
            INSERT INTO execution_runs (
                id, profile_id, label, symbol, venue, mode, state, control_mode,
                runtime_binding_status, budget_amount, budget_ratio, capital_currency,
                activation_status, lifecycle_status, start_time, stop_time, stop_reason,
                operator_note, last_event_type, last_event_message, last_event_at,
                created_at, updated_at
            ) VALUES (
                :id, :profile_id, :label, :symbol, :venue, :mode, :state, :control_mode,
                :runtime_binding_status, :budget_amount, :budget_ratio, :capital_currency,
                :activation_status, :lifecycle_status, :start_time, :stop_time, :stop_reason,
                :operator_note, :last_event_type, :last_event_message, :last_event_at,
                :created_at, :updated_at
            )
            """
        ),
        {
            "id": run_id,
            "profile_id": profile_id,
            "label": profile_row.get("label"),
            "symbol": profile_row.get("symbol"),
            "venue": profile_row.get("venue"),
            "mode": profile_row.get("mode"),
            "state": "running",
            "control_mode": CONTROL_MODE,
            "runtime_binding_status": RUNTIME_BINDING_STATUS,
            "budget_amount": profile_row.get("planned_budget_amount"),
            "budget_ratio": profile_row.get("planned_budget_ratio"),
            "capital_currency": currency,
            "activation_status": profile_row.get("activation_status"),
            "lifecycle_status": profile_row.get("lifecycle_status"),
            "start_time": now,
            "stop_time": None,
            "stop_reason": None,
            "operator_note": CONTROL_PLANE_UPGRADE_PREREQUISITE,
            "last_event_type": "started",
            "last_event_message": message,
            "last_event_at": now,
            "created_at": now,
            "updated_at": now,
        },
    )
    _insert_event(
        db,
        run_id=run_id,
        profile_id=profile_id,
        event_type="started",
        level="info",
        message=message,
        payload={
            "state": "running",
            "runtime_binding_status": RUNTIME_BINDING_STATUS,
            "budget_amount": profile_row.get("planned_budget_amount"),
            "budget_ratio": profile_row.get("planned_budget_ratio"),
        },
        created_at=now,
    )
    db.commit()
    return {
        "action": "start",
        "action_result": "started",
        "operator_message": "已建立新的 execution run。",
        "snapshot": build_execution_control_plane_snapshot(db, status_payload, overview_payload),
        "run": get_execution_run_detail(db, run_id, status_payload=status_payload),
    }



def _transition_run_state(
    db,
    *,
    run_id: str,
    target_state: str,
    event_type: str,
    message: str,
    stop_reason: Optional[str] = None,
    noop_when: Optional[str] = None,
    status_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    run_row = _require_run_row(db, run_id)
    now = _utcnow_iso()
    current_state = str(run_row.get("state") or "stopped")
    if noop_when and current_state == noop_when:
        _insert_event(
            db,
            run_id=run_id,
            profile_id=str(run_row.get("profile_id") or ""),
            event_type=f"{event_type}_noop",
            level="info",
            message=f"Run 已經是 {current_state}；忽略重複操作。",
            payload={"action_result": f"noop_already_{current_state}"},
            created_at=now,
        )
        db.execute(
            text(
                """
                UPDATE execution_runs
                SET last_event_type = :last_event_type,
                    last_event_message = :last_event_message,
                    last_event_at = :last_event_at,
                    updated_at = :updated_at
                WHERE id = :run_id
                """
            ),
            {
                "run_id": run_id,
                "last_event_type": f"{event_type}_noop",
                "last_event_message": f"Run 已經是 {current_state}；忽略重複操作。",
                "last_event_at": now,
                "updated_at": now,
            },
        )
        db.commit()
        return {
            "action_result": f"noop_already_{current_state}",
            "run": get_execution_run_detail(db, run_id, status_payload=status_payload),
        }

    db.execute(
        text(
            """
            UPDATE execution_runs
            SET state = :state,
                stop_time = :stop_time,
                stop_reason = :stop_reason,
                last_event_type = :last_event_type,
                last_event_message = :last_event_message,
                last_event_at = :last_event_at,
                updated_at = :updated_at
            WHERE id = :run_id
            """
        ),
        {
            "run_id": run_id,
            "state": target_state,
            "stop_time": now if target_state == "stopped" else None,
            "stop_reason": stop_reason,
            "last_event_type": event_type,
            "last_event_message": message,
            "last_event_at": now,
            "updated_at": now,
        },
    )
    _insert_event(
        db,
        run_id=run_id,
        profile_id=str(run_row.get("profile_id") or ""),
        event_type=event_type,
        level="info",
        message=message,
        payload={"state": target_state, "stop_reason": stop_reason},
        created_at=now,
    )
    db.commit()
    return {
        "action_result": event_type,
        "run": get_execution_run_detail(db, run_id, status_payload=status_payload),
    }



def pause_execution_run(db, run_id: str, status_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _transition_run_state(
        db,
        run_id=run_id,
        target_state="paused",
        event_type="paused",
        message="Execution run 已暫停；目前保留 run/event 狀態，但尚未綁定真實 order-level pause。",
        noop_when="paused",
        status_payload=status_payload,
    )



def stop_execution_run(db, run_id: str, status_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _transition_run_state(
        db,
        run_id=run_id,
        target_state="stopped",
        event_type="stopped",
        message="Execution run 已停止；此動作目前結束 control-plane run，不代表 venue order 已自動撤銷。",
        stop_reason="operator_stop",
        noop_when="stopped",
        status_payload=status_payload,
    )



def get_execution_run_detail(db, run_id: str, status_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ensure_execution_control_plane_schema(db)
    run_row = _require_run_row(db, run_id)
    events = _load_run_events(db, [run_id], limit_per_run=20).get(run_id, [])
    return _serialize_run(run_row, events, status_payload=status_payload)
