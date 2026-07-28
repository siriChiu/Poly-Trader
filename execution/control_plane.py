from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from fastapi import HTTPException
from sqlalchemy import text

from execution.strategy_bundle import build_strategy_bundle, bundle_summary, persist_strategy_bundle

CONTROL_MODE = "stateful_run_control_beta"
RUNTIME_BINDING_STATUS = "control_plane_only"
SHADOW_RUNTIME_BINDING_STATUS = "paper_shadow_runtime_blocked"
CONTROL_PLANE_OPERATOR_MESSAGE = (
    "Bot 營運現在已具備可持久化的運行控制；"
    "啟動 / 暫停 / 停止都會保留事件紀錄，且每條運行已可鏡像同商品的執行期 / 對帳摘要，"
    "但每個 Bot 的資金 / 持倉 / 委託帳本仍未完全接上。"
)
CONTROL_PLANE_UPGRADE_PREREQUISITE = (
    "下一步必須把每個 Bot 的資金 / 持倉 / 委託歸因綁到各自運行，"
    "否則這仍只是可持久化的運行控制測試版，不是完整的 Bot 執行期。"
)
WORKER_POLL_EVENT_TYPE = "paper_shadow_worker_poll"
WORKER_PARITY_BLOCKED_EVENT_TYPE = "worker_bundle_parity_blocked"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAPER_SHADOW_OUTCOME_ARTIFACT_PATH = PROJECT_ROOT / "data" / "paper_shadow_outcome_reconciliation.json"
LIVE_TRADING_ROOT = PROJECT_ROOT / "data" / "live_trading"
PAPER_SHADOW_OUTCOME_WINDOW_HOURS = 24
PAPER_SHADOW_LABEL_MATCH_TOLERANCE_HOURS = 6

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
        strategy_name TEXT,
        strategy_source TEXT,
        strategy_hash TEXT,
        strategy_snapshot_json TEXT,
        strategy_bundle_hash TEXT,
        strategy_bundle_path TEXT,
        strategy_bundle_status TEXT,
        worker_status TEXT,
        worker_control_json TEXT,
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



def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif value is None:
        return None
    else:
        text_value = str(value).strip()
        if not text_value:
            return None
        try:
            parsed = datetime.fromisoformat(text_value.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = datetime.strptime(text_value.split(".")[0], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)



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



def _table_exists(db, table_name: str) -> bool:
    try:
        row = _one(
            db,
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = :table_name LIMIT 1",
            {"table_name": table_name},
        )
    except Exception:
        return False
    return bool(row)



def _run_priority(state: Optional[str]) -> int:
    normalized = str(state or "").lower()
    if normalized == "running":
        return 0
    if normalized == "paused":
        return 1
    return 2



def _to_float_maybe(value: Any) -> Optional[float]:
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



def _to_int_maybe(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(float(text))
        except ValueError:
            return None
    return None



def _strategy_sort_tuple(entry: Dict[str, Any]) -> tuple:
    last_results = entry.get("last_results") if isinstance(entry.get("last_results"), dict) else {}
    return (
        _to_float_maybe(last_results.get("avg_decision_quality_score")) or -999.0,
        _to_float_maybe(last_results.get("avg_expected_win_rate")) or -999.0,
        _to_float_maybe(last_results.get("roi")) or -999.0,
        _to_float_maybe(last_results.get("profit_factor")) or -999.0,
        -(_to_float_maybe(last_results.get("max_drawdown")) or 999.0),
        str(entry.get("updated_at") or entry.get("created_at") or ""),
        str(entry.get("name") or ""),
    )



def _strategy_metadata(entry: Dict[str, Any]) -> Dict[str, Any]:
    from backtesting import strategy_lab

    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    metadata = dict(metadata)
    if not metadata.get("primary_sleeve_key") or not metadata.get("primary_sleeve_label"):
        fallback = strategy_lab._build_strategy_metadata(
            str(entry.get("name") or ""),
            entry.get("definition") if isinstance(entry.get("definition"), dict) else {},
        )
        fallback = fallback if isinstance(fallback, dict) else {}
        merged = dict(fallback)
        merged.update({key: value for key, value in metadata.items() if value not in (None, "", [], {})})
        metadata = merged
    return metadata



def _compact_strategy_binding(entry: Dict[str, Any], sleeve_key: str) -> Dict[str, Any]:
    metadata = _strategy_metadata(entry)
    last_results = entry.get("last_results") if isinstance(entry.get("last_results"), dict) else {}
    primary_label = str(
        metadata.get("primary_sleeve_label")
        or PRIMARY_SLEEVE_META.get(sleeve_key, {}).get("label")
        or sleeve_key
    )
    compact = {
        "status": "saved_strategy_bound",
        "strategy_name": entry.get("name"),
        "strategy_slug": entry.get("slug"),
        "strategy_source": "strategy_lab_saved",
        "strategy_hash": hashlib.sha1(
            _json_dumps(
                {
                    "schema_version": entry.get("schema_version"),
                    "name": entry.get("name"),
                    "updated_at": entry.get("updated_at"),
                    "definition": entry.get("definition"),
                    "metadata": metadata,
                }
            ).encode("utf-8")
        ).hexdigest()[:12],
        "schema_version": entry.get("schema_version"),
        "updated_at": entry.get("updated_at"),
        "created_at": entry.get("created_at"),
        "run_count": entry.get("run_count"),
        "primary_sleeve_key": metadata.get("primary_sleeve_key") or sleeve_key,
        "primary_sleeve_label": primary_label,
        "strategy_type": metadata.get("strategy_type"),
        "model_name": metadata.get("model_name"),
        "title": metadata.get("title") or entry.get("name"),
        "description": metadata.get("description"),
        "sleeve_summary": metadata.get("sleeve_summary"),
        "decision_quality_label": last_results.get("decision_quality_label"),
        "avg_decision_quality_score": _to_float_maybe(last_results.get("avg_decision_quality_score")),
        "avg_expected_win_rate": _to_float_maybe(last_results.get("avg_expected_win_rate")),
        "roi": _to_float_maybe(last_results.get("roi")),
        "profit_factor": _to_float_maybe(last_results.get("profit_factor")),
        "total_trades": _to_int_maybe(last_results.get("total_trades")),
    }
    compact["summary"] = (
        f"{compact.get('strategy_name') or primary_label} · {primary_label} · "
        f"source saved_strategy · hash {compact.get('strategy_hash')}"
    )
    compact["operator_action"] = "可直接沿用這份已儲存策略快照；若要改參數，請先回 Strategy Lab 另存新版本。"
    return compact



def _strategy_entry_for_binding(strategy_binding: Optional[Dict[str, Any]], sleeve_key: str) -> Optional[Dict[str, Any]]:
    if not isinstance(strategy_binding, dict):
        return None
    if str(strategy_binding.get("strategy_source") or "") == "high_conviction_topk_shadow":
        return _synthetic_shadow_strategy_entry(strategy_binding, sleeve_key)
    target_hash = str(strategy_binding.get("strategy_hash") or "").strip()
    target_slug = str(strategy_binding.get("strategy_slug") or "").strip()
    target_name = str(strategy_binding.get("strategy_name") or "").strip()
    if not any([target_hash, target_slug, target_name]):
        return None
    try:
        from backtesting.strategy_lab import load_all_strategies

        strategies = load_all_strategies(include_internal=False)
    except Exception:
        return None

    fallback: Optional[Dict[str, Any]] = None
    for entry in strategies:
        if not isinstance(entry, dict):
            continue
        metadata = _strategy_metadata(entry)
        entry_sleeve = str(metadata.get("primary_sleeve_key") or sleeve_key or "").strip() or sleeve_key
        compact = _compact_strategy_binding(entry, entry_sleeve)
        if target_hash and compact.get("strategy_hash") == target_hash:
            return entry
        if target_slug and str(entry.get("slug") or "") == target_slug:
            fallback = entry
        elif target_name and str(entry.get("name") or "") == target_name and fallback is None:
            fallback = entry
    return fallback



def _shadow_strategy_binding_from_control_contract(profile_id: str, control_contract: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if profile_id != "selective":
        return None
    high_conviction_topk = _as_dict(control_contract.get("high_conviction_topk"))
    if not high_conviction_topk:
        return None
    candidate_rows = high_conviction_topk.get("nearest_deployable_rows")
    candidate = candidate_rows[0] if isinstance(candidate_rows, list) and candidate_rows and isinstance(candidate_rows[0], dict) else {}
    support_context = _as_dict(high_conviction_topk.get("support_context"))
    model_name = (
        candidate.get("model_name")
        or candidate.get("model")
        or candidate.get("candidate_model")
        or "high_conviction_topk"
    )
    threshold_name = (
        candidate.get("threshold_name")
        or candidate.get("top_k")
        or candidate.get("candidate_threshold")
        or "shadow_threshold"
    )
    strategy_name = f"Paper Shadow Top-K · {model_name} · {threshold_name}"
    source_payload = {
        "profile_id": profile_id,
        "strategy_name": strategy_name,
        "candidate": candidate,
        "support_context": support_context,
        "deployment_readiness_status": high_conviction_topk.get("deployment_readiness_status"),
        "risk_qualified_count": high_conviction_topk.get("risk_qualified_count"),
        "runtime_blocked_candidate_count": high_conviction_topk.get("runtime_blocked_candidate_count"),
    }
    strategy_hash = hashlib.sha1(_json_dumps(source_payload).encode("utf-8")).hexdigest()[:12]
    return {
        "status": "synthetic_paper_shadow_bound",
        "strategy_name": strategy_name,
        "strategy_slug": f"paper-shadow-topk-{strategy_hash}",
        "strategy_source": "high_conviction_topk_shadow",
        "strategy_hash": strategy_hash,
        "schema_version": 1,
        "updated_at": _utcnow_iso(),
        "created_at": None,
        "run_count": None,
        "primary_sleeve_key": profile_id,
        "primary_sleeve_label": PRIMARY_SLEEVE_META.get(profile_id, {}).get("label") or profile_id,
        "strategy_type": "shadow_topk_rehearsal",
        "model_name": str(model_name),
        "title": strategy_name,
        "description": "由 high-conviction Top-K runtime-blocked candidate 生成的 paper/shadow rehearsal binding；只用於 worker parity 與 outcome reconciliation。",
        "sleeve_summary": "高信念精選 · paper/shadow only · live buy/add fail-closed",
        "decision_quality_label": candidate.get("deployment_candidate_tier") or high_conviction_topk.get("deployment_readiness_status"),
        "avg_decision_quality_score": _to_float_maybe(candidate.get("avg_decision_quality_score")),
        "avg_expected_win_rate": _to_float_maybe(candidate.get("win_rate") or candidate.get("oos_win_rate")),
        "roi": _to_float_maybe(candidate.get("oos_roi") or candidate.get("roi")),
        "profit_factor": _to_float_maybe(candidate.get("profit_factor")),
        "total_trades": _to_int_maybe(candidate.get("trade_count") or candidate.get("total_trades")),
        "max_drawdown": _to_float_maybe(candidate.get("max_drawdown")),
        "worst_fold": _to_float_maybe(candidate.get("worst_fold")),
        "high_conviction_candidate": candidate,
        "high_conviction_support_context": support_context,
        "summary": f"{strategy_name} · shadow-only · hash {strategy_hash}",
        "operator_action": "這是 Top-K 影子演練 binding：可產生 worker parity / outcome proof，但不允許 live buy/add。",
    }


def _synthetic_shadow_strategy_entry(strategy_binding: Dict[str, Any], sleeve_key: str) -> Dict[str, Any]:
    candidate = _as_dict(strategy_binding.get("high_conviction_candidate"))
    support_context = _as_dict(strategy_binding.get("high_conviction_support_context"))
    model_name = str(strategy_binding.get("model_name") or candidate.get("model_name") or "high_conviction_topk")
    threshold_name = str(candidate.get("threshold_name") or candidate.get("top_k") or "shadow_threshold")
    definition = {
        "type": "shadow_topk_rehearsal",
        "params": {
            "model_name": model_name,
            "threshold_name": threshold_name,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
        },
    }
    metadata = {
        "primary_sleeve_key": sleeve_key,
        "primary_sleeve_label": strategy_binding.get("primary_sleeve_label") or PRIMARY_SLEEVE_META.get(sleeve_key, {}).get("label") or sleeve_key,
        "strategy_type": "shadow_topk_rehearsal",
        "model_name": model_name,
        "title": strategy_binding.get("title") or strategy_binding.get("strategy_name"),
        "description": strategy_binding.get("description"),
        "sleeve_summary": strategy_binding.get("sleeve_summary"),
        "strategy_source": "high_conviction_topk_shadow",
        "support_context": support_context,
        "paper_shadow_only": True,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
    }
    last_results = {
        "roi": _to_float_maybe(strategy_binding.get("roi") or candidate.get("oos_roi") or candidate.get("roi")),
        "win_rate": _to_float_maybe(strategy_binding.get("avg_expected_win_rate") or candidate.get("win_rate")),
        "max_drawdown": _to_float_maybe(strategy_binding.get("max_drawdown") or candidate.get("max_drawdown")),
        "profit_factor": _to_float_maybe(strategy_binding.get("profit_factor") or candidate.get("profit_factor")),
        "total_trades": _to_int_maybe(strategy_binding.get("total_trades") or candidate.get("trade_count") or candidate.get("total_trades")),
        "backtest_range": candidate.get("backtest_range") if isinstance(candidate.get("backtest_range"), dict) else None,
    }
    return {
        "schema_version": strategy_binding.get("schema_version") or 1,
        "name": strategy_binding.get("strategy_name"),
        "slug": strategy_binding.get("strategy_slug"),
        "created_at": strategy_binding.get("created_at"),
        "updated_at": strategy_binding.get("updated_at"),
        "strategy_source": "high_conviction_topk_shadow",
        "definition": definition,
        "metadata": metadata,
        "last_results": last_results,
    }


def _freeze_strategy_bundle_for_run(
    strategy_binding: Optional[Dict[str, Any]],
    profile_id: str,
    run_id: str,
    *,
    config: Optional[Dict[str, Any]],
    status_payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    entry = _strategy_entry_for_binding(strategy_binding, profile_id)
    if entry is None:
        return {
            "status": "missing_saved_strategy_entry",
            "strategy_bundle_summary": None,
            "strategy_bundle_hash": None,
            "strategy_bundle_path": None,
            "strategy_bundle_json": None,
        }
    bundle = build_strategy_bundle(entry, profile_id, config=config, status_payload=status_payload)
    persisted = persist_strategy_bundle(bundle, run_id=run_id, profile_id=profile_id)
    summary = bundle_summary(bundle)
    return {
        **persisted,
        "status": persisted.get("status") or "persisted",
        "strategy_bundle_summary": summary,
    }



def _missing_strategy_binding(sleeve_key: str) -> Dict[str, Any]:
    primary_label = str(PRIMARY_SLEEVE_META.get(sleeve_key, {}).get("label") or sleeve_key)
    return {
        "status": "missing_saved_strategy",
        "strategy_name": None,
        "strategy_slug": None,
        "strategy_source": None,
        "strategy_hash": None,
        "schema_version": None,
        "updated_at": None,
        "created_at": None,
        "run_count": 0,
        "primary_sleeve_key": sleeve_key,
        "primary_sleeve_label": primary_label,
        "strategy_type": None,
        "model_name": None,
        "title": None,
        "description": None,
        "sleeve_summary": None,
        "decision_quality_label": None,
        "avg_decision_quality_score": None,
        "avg_expected_win_rate": None,
        "roi": None,
        "profit_factor": None,
        "total_trades": None,
        "summary": f"尚未找到對應 sleeve 的已儲存策略快照：{primary_label}。",
        "operator_action": "前往 Strategy Lab 儲存對應 sleeve 的策略，才能讓 Execution Console 顯示明確 strategy snapshot / version。",
    }



def build_execution_strategy_source_snapshot() -> Dict[str, Any]:
    from backtesting.strategy_lab import load_all_strategies

    strategies = load_all_strategies(include_internal=False)
    normalized_entries: List[Dict[str, Any]] = []
    sleeve_candidates: Dict[str, List[Dict[str, Any]]] = {key: [] for key in PRIMARY_SLEEVE_ORDER}
    for entry in sorted(strategies, key=_strategy_sort_tuple, reverse=True):
        metadata = _strategy_metadata(entry)
        primary_key = str(metadata.get("primary_sleeve_key") or "").strip()
        if primary_key in sleeve_candidates:
            sleeve_candidates[primary_key].append(entry)
        compact = _compact_strategy_binding(entry, primary_key or "uncategorized")
        compact["status"] = "saved_strategy_catalog"
        normalized_entries.append(compact)

    sleeve_bindings: Dict[str, Dict[str, Any]] = {}
    covered_sleeves = []
    missing_sleeves = []
    for key in PRIMARY_SLEEVE_ORDER:
        candidates = sleeve_candidates.get(key) or []
        recommended = _compact_strategy_binding(candidates[0], key) if candidates else _missing_strategy_binding(key)
        if candidates:
            covered_sleeves.append(key)
        else:
            missing_sleeves.append(key)
        sleeve_bindings[key] = {
            "primary_sleeve_key": key,
            "primary_sleeve_label": PRIMARY_SLEEVE_META.get(key, {}).get("label") or key,
            "coverage_status": recommended.get("status"),
            "recommended": recommended,
            "alternatives": [_compact_strategy_binding(entry, key) for entry in candidates[1:3]],
        }

    return {
        "generated_at": _utcnow_iso(),
        "summary": {
            "route": "/api/execution/strategies/source",
            "strategy_count": len(normalized_entries),
            "covered_sleeves": len(covered_sleeves),
            "total_sleeves": len(PRIMARY_SLEEVE_ORDER),
            "missing_sleeves": missing_sleeves,
            "operator_message": (
                f"目前已有 {len(normalized_entries)} 份已儲存策略快照，可覆蓋 {len(covered_sleeves)}/{len(PRIMARY_SLEEVE_ORDER)} 個 primary sleeves；"
                "尚未覆蓋的 sleeves 仍需回 Strategy Lab 補 strategy snapshot/version。"
            ),
        },
        "sleeve_bindings": sleeve_bindings,
        "strategies": normalized_entries,
    }


def execution_strategy_binding_for_name(strategy_name: str) -> Dict[str, Any]:
    """Resolve one exact user-saved Strategy Lab record for a paper/shadow run.

    Automatic routing normally recommends the highest-ranked strategy per sleeve.
    This resolver preserves the exact Strategy Lab selection and its frozen hash,
    without changing any live execution gate.
    """

    wanted = str(strategy_name or "").strip()
    if not wanted:
        raise HTTPException(
            status_code=400,
            detail={"code": "strategy_name_required", "message": "請先選擇一個已儲存策略。"},
        )
    snapshot = build_execution_strategy_source_snapshot()
    for binding in _as_list(snapshot.get("strategies")):
        if isinstance(binding, dict) and str(binding.get("strategy_name") or "").strip() == wanted:
            sleeve_key = str(binding.get("primary_sleeve_key") or "").strip()
            if sleeve_key not in PRIMARY_SLEEVE_ORDER:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "strategy_sleeve_not_routable",
                        "message": "這個策略尚未對應到可執行 sleeve；請先在 Strategy Lab 儲存完整策略設定。",
                        "context": {"strategy_name": wanted, "primary_sleeve_key": sleeve_key or None},
                    },
                )
            return dict(binding)
    raise HTTPException(
        status_code=404,
        detail={
            "code": "strategy_not_found",
            "message": f"找不到已儲存策略「{wanted}」；請先完成回測並儲存結果。",
        },
    )


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}



def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []



def _high_conviction_topk_from_status(status_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = _as_dict(status_payload)
    execution_surface_contract = _as_dict(payload.get("execution_surface_contract"))
    execution = _as_dict(payload.get("execution"))
    return _as_dict(
        execution_surface_contract.get("high_conviction_topk")
        or execution.get("high_conviction_topk")
        or payload.get("high_conviction_topk")
    )



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



def _record_text(record: Dict[str, Any], keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None



def _first_numeric_value(record: Dict[str, Any], keys: Iterable[str]) -> Optional[float]:
    for key in keys:
        value = _to_float_maybe(record.get(key))
        if value is not None:
            return value
    return None



def _side_sign(record: Dict[str, Any]) -> Optional[float]:
    side = (_record_text(record, ("side", "positionSide")) or "").strip().lower()
    if side in {"buy", "long", "bid"}:
        return 1.0
    if side in {"sell", "short", "ask"}:
        return -1.0
    return None



def _position_signed_quantity(record: Dict[str, Any]) -> Optional[float]:
    explicit_position_amt = _to_float_maybe(record.get("positionAmt"))
    if explicit_position_amt is not None:
        return explicit_position_amt
    quantity = _first_numeric_value(record, ("contracts", "size", "qty", "amount"))
    if quantity is None:
        return None
    side_sign = _side_sign(record)
    if side_sign is None:
        return quantity
    return abs(quantity) * side_sign



def _position_mark_price(record: Dict[str, Any]) -> Optional[float]:
    return _first_numeric_value(record, ("markPrice", "price", "avgPrice", "entryPrice"))



def _order_signed_quantity(record: Dict[str, Any]) -> Optional[float]:
    quantity = _first_numeric_value(record, ("qty", "amount", "size"))
    if quantity is None:
        return None
    side_sign = _side_sign(record)
    if side_sign is None:
        return quantity
    return abs(quantity) * side_sign



def _order_price(record: Dict[str, Any]) -> Optional[float]:
    return _first_numeric_value(record, ("price", "avgPrice"))



def _format_preview_amount(value: Optional[float], currency: str) -> str:
    if value is None:
        return f"— {currency}"
    return f"{float(value):.2f} {currency}"



def _build_shared_symbol_ledger_preview(
    *,
    positions: List[Dict[str, Any]],
    open_orders: List[Dict[str, Any]],
    balance: Dict[str, Any],
    budget_amount: Optional[float],
    currency: str,
) -> Dict[str, Any]:
    gross_position_notional_total = 0.0
    net_position_notional_total = 0.0
    position_priced_count = 0
    unrealized_pnl_total = 0.0
    unrealized_pnl_count = 0

    for record in positions:
        signed_qty = _position_signed_quantity(record)
        mark_price = _position_mark_price(record)
        if signed_qty is not None and mark_price is not None:
            gross_position_notional_total += abs(float(signed_qty)) * float(mark_price)
            net_position_notional_total += float(signed_qty) * float(mark_price)
            position_priced_count += 1
        unrealized_pnl = _first_numeric_value(record, ("unrealizedPnl", "pnl"))
        if unrealized_pnl is not None:
            unrealized_pnl_total += float(unrealized_pnl)
            unrealized_pnl_count += 1

    open_order_notional_total = 0.0
    open_order_priced_count = 0
    for record in open_orders:
        signed_qty = _order_signed_quantity(record)
        price = _order_price(record)
        if signed_qty is None or price is None:
            continue
        open_order_notional_total += abs(float(signed_qty)) * float(price)
        open_order_priced_count += 1

    priced_positions_total = 0.0 if not positions else (gross_position_notional_total if position_priced_count == len(positions) else None)
    priced_net_position_total = 0.0 if not positions else (net_position_notional_total if position_priced_count == len(positions) else None)
    priced_open_orders_total = 0.0 if not open_orders else (open_order_notional_total if open_order_priced_count == len(open_orders) else None)
    total_known_commitment = None
    if priced_positions_total is not None and priced_open_orders_total is not None:
        total_known_commitment = float(priced_positions_total) + float(priced_open_orders_total)

    total_balance = _to_float_maybe(balance.get("total"))
    free_balance = _to_float_maybe(balance.get("free"))
    capital_in_use = None
    if total_balance is not None and free_balance is not None:
        capital_in_use = max(float(total_balance) - float(free_balance), 0.0)

    budget_gap = None
    commitment_vs_budget_ratio = None
    if budget_amount not in (None, 0.0) and total_known_commitment is not None:
        budget_gap = float(budget_amount) - float(total_known_commitment)
        commitment_vs_budget_ratio = float(total_known_commitment) / float(budget_amount)

    if not positions and not open_orders:
        budget_alignment_status = "healthy_no_symbol_commitment"
        budget_alignment_summary = "目前 shared symbol 沒有持倉或掛單；run budget 尚未形成實際 commitment。"
    elif total_known_commitment is None:
        budget_alignment_status = "warning_commitment_unpriced"
        budget_alignment_summary = (
            "已偵測 shared symbol 持倉或掛單，但缺少 mark/price 欄位；"
            "目前只能做 count-level preview，不能判斷 budget alignment。"
        )
    elif budget_amount in (None, 0.0):
        budget_alignment_status = "warning_budget_unavailable"
        budget_alignment_summary = (
            f"shared symbol 已有 {_format_preview_amount(total_known_commitment, currency)} 的 known commitment，"
            "但 run budget 不可用；暫時無法比較 budget alignment。"
        )
    elif float(total_known_commitment) <= float(budget_amount) * 1.05:
        budget_alignment_status = "healthy_within_planned_preview"
        budget_alignment_summary = (
            f"shared symbol known commitment {_format_preview_amount(total_known_commitment, currency)} "
            f"仍在 planned budget {_format_preview_amount(budget_amount, currency)} 的 preview 容許範圍內；"
            "但尚未完成 per-run attribution。"
        )
    else:
        budget_alignment_status = "warning_over_planned_preview"
        budget_alignment_summary = (
            f"shared symbol known commitment {_format_preview_amount(total_known_commitment, currency)} "
            f"已高於 planned budget {_format_preview_amount(budget_amount, currency)}；"
            "先對齊 ownership / attribution，再擴張 exposure。"
        )

    unrealized_pnl_value = 0.0 if not positions else (unrealized_pnl_total if unrealized_pnl_count == len(positions) else None)

    return {
        "scope": "symbol_scoped_shared_ledger_preview",
        "ownership_status": "shared_symbol_preview_only",
        "summary": (
            f"shared symbol ledger preview：{budget_alignment_summary}"
            " 這仍是 symbol-scoped shared preview，不是 per-run realized / unrealized PnL ledger。"
        ),
        "budget_alignment_status": budget_alignment_status,
        "budget_alignment_summary": budget_alignment_summary,
        "pricing_complete": total_known_commitment is not None,
        "position_count": len(positions),
        "open_order_count": len(open_orders),
        "position_priced_count": position_priced_count,
        "open_order_priced_count": open_order_priced_count,
        "gross_position_notional": priced_positions_total,
        "net_position_notional": priced_net_position_total,
        "open_order_notional": priced_open_orders_total,
        "total_known_commitment": total_known_commitment,
        "unrealized_pnl": unrealized_pnl_value,
        "capital_in_use": capital_in_use,
        "budget_amount": budget_amount,
        "budget_gap": budget_gap,
        "commitment_vs_budget_ratio": commitment_vs_budget_ratio,
        "currency": currency,
    }



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
    high_conviction_topk = _high_conviction_topk_from_status(status_payload)
    shadow_only = bool(
        str(row.get("mode") or "") == "paper_shadow"
        or str(row.get("runtime_binding_status") or "") == SHADOW_RUNTIME_BINDING_STATUS
    )

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
    budget_amount = _to_float_maybe(row.get("budget_amount"))
    budget_ratio = _to_float_maybe(row.get("budget_ratio"))
    capital_currency = str(row.get("capital_currency") or balance.get("currency") or "USDT")
    shared_symbol_ledger_preview = _build_shared_symbol_ledger_preview(
        positions=symbol_positions,
        open_orders=symbol_open_orders,
        balance=balance,
        budget_amount=budget_amount,
        currency=capital_currency,
    )

    last_order = _as_dict(guardrails.get("last_order"))
    last_order_symbol_match = not last_order or _record_symbol_key(last_order) == run_symbol_key
    matched_runtime = bool(status_payload) and symbol_match and venue_match
    mirrored_components = [
        "live_runtime_truth",
        "account_snapshot",
        "execution_reconciliation",
        "execution_guardrails",
        "shared_symbol_preview",
        "shared_symbol_ledger_preview",
    ] if matched_runtime else []
    operator_action = (
        _as_dict(reconciliation.get("recovery_state")).get("operator_action")
        or _as_dict(reconciliation.get("lifecycle_audit")).get("operator_action")
        or CONTROL_PLANE_UPGRADE_PREREQUISITE
    )
    summary = (
        "此 run 已鏡像到目前 /api/status 的 symbol-scoped runtime / account / reconciliation 視圖；"
        "shared-symbol budget / exposure / PnL preview 也已 machine-read 化，但仍不是 per-bot ledger。"
        if matched_runtime
        else "此 run 目前只有 stateful control-plane event log；尚未對齊到當前 runtime symbol/venue snapshot。"
    )
    ownership_boundary = {
        "ledger_scope": "shared_symbol_preview_only" if matched_runtime else "control_plane_only",
        "capital_attribution": "planned_budget_vs_shared_account_balance" if matched_runtime else "not_bound",
        "position_attribution": "symbol_scoped_preview_only" if matched_runtime else "not_bound",
        "open_order_attribution": "symbol_scoped_preview_only" if matched_runtime else "not_bound",
        "pnl_attribution": "symbol_scoped_preview_only" if matched_runtime else "not_bound",
        "summary": (
            "run 目前只擁有 planned budget、shared-symbol exposure/PnL preview 與 lifecycle/event log；"
            "實際 balance / positions / open orders / PnL 仍是 shared-symbol preview。"
            if matched_runtime
            else "run 尚未綁到 runtime symbol/venue snapshot，因此連 shared-symbol preview 都還沒對齊。"
        ),
    }
    contract = {
        "status": "symbol_scope_runtime_mirror" if matched_runtime else "control_plane_only",
        "scope": "symbol_scoped_runtime_preview" if matched_runtime else "control_plane_event_log_only",
        "summary": (
            "此運行是高信念精選影子觀察：只鏡像即時決策、帳戶與對帳摘要，不送單、不加倉；"
            "等即時支持、場館證據鏈與單一 Bot 帳本全部通過後才能升級小流量。"
            if shadow_only and matched_runtime
            else summary
        ),
        "shadow_only": shadow_only,
        "risk_on_order_enabled": False,
        "order_submission_enabled": False,
        "high_conviction_topk": high_conviction_topk if shadow_only else None,
        "mirrored_components": mirrored_components,
        "missing_components": [
            "per_bot_capital_ledger",
            "per_bot_position_attribution",
            "per_bot_open_order_attribution",
            "per_bot_pnl_attribution",
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
    snapshot_mode = row.get("mode") if shadow_only else (execution.get("mode") or row.get("mode"))
    snapshot = {
        "symbol": run_symbol,
        "venue": row.get("venue"),
        "mode": snapshot_mode,
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
            "budget_amount": budget_amount,
            "budget_ratio": budget_ratio,
            "balance_total": balance.get("total"),
            "balance_free": balance.get("free"),
            "currency": capital_currency,
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
                "currency": capital_currency,
            },
            "positions": _compact_preview_records(symbol_positions, kind="position"),
            "open_orders": _compact_preview_records(symbol_open_orders, kind="order"),
        } if matched_runtime else None,
        "shared_symbol_ledger_preview": shared_symbol_ledger_preview if matched_runtime else None,
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



def _process_is_alive(value: Any) -> tuple[Optional[int], Optional[bool]]:
    if isinstance(value, bool):
        return None, False
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None, False
    if pid <= 0:
        return None, False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return pid, False
    except PermissionError:
        return pid, True
    except OSError:
        return pid, False
    return pid, True


def _worker_control_contract(row: Dict[str, Any], current_state: str) -> Dict[str, Any]:
    stored = _json_loads(row.get("worker_control_json"))
    stored = stored if isinstance(stored, dict) else {}
    status = str(row.get("worker_status") or stored.get("status") or "backend_worker_not_bound").strip() or "backend_worker_not_bound"
    legacy_backend_worker_bound = bool(stored.get("backend_worker_bound", False))
    continuous_worker = stored.get("continuous_worker") is True
    backend_worker_pid, pid_alive = _process_is_alive(stored.get("backend_worker_pid")) if continuous_worker else (None, None)

    now = datetime.now(timezone.utc)
    lease_owner = str(stored.get("lease_owner") or "").strip()
    lease_epoch = str(stored.get("lease_epoch") or "").strip()
    lease_expires_at = _parse_datetime(stored.get("lease_expires_at"))
    if not continuous_worker:
        lease_status = "not_implemented"
    elif not lease_owner or not lease_epoch or lease_expires_at is None:
        lease_status = "missing"
    elif lease_expires_at <= now:
        lease_status = "expired"
    else:
        lease_status = "active"

    heartbeat_at = _parse_datetime(stored.get("heartbeat_at"))
    if not continuous_worker:
        heartbeat_status = "not_implemented"
    elif heartbeat_at is None:
        heartbeat_status = "missing"
    else:
        heartbeat_age_seconds = (now - heartbeat_at).total_seconds()
        heartbeat_status = "fresh" if -30.0 <= heartbeat_age_seconds <= 120.0 else "stale"

    worker_healthy = bool(
        current_state == "running"
        and continuous_worker
        and backend_worker_pid is not None
        and pid_alive is True
        and lease_status == "active"
        and heartbeat_status == "fresh"
    )
    poll_handler_available = stored.get("poll_handler_available") is True
    runtime_liveness = {
        "status": "healthy" if worker_healthy else "unhealthy" if continuous_worker else "not_continuously_running",
        "healthy": worker_healthy,
        "pid": backend_worker_pid,
        "pid_alive": pid_alive,
        "lease_status": lease_status,
        "heartbeat_status": heartbeat_status,
        "last_poll_at": stored.get("last_poll_at"),
    }
    return {
        "status": status,
        "state": current_state,
        "backend_worker_bound": bool(legacy_backend_worker_bound and worker_healthy),
        "legacy_backend_worker_bound": legacy_backend_worker_bound,
        "poll_handler_available": poll_handler_available,
        "continuous_worker": continuous_worker,
        "runtime_liveness": runtime_liveness,
        "worker_kind": stored.get("worker_kind"),
        "backend_worker_pid": backend_worker_pid,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "bundle_hash_match": stored.get("bundle_hash_match"),
        "last_poll_at": stored.get("last_poll_at"),
        "poll_count": stored.get("poll_count") or 0,
        "latest_order_proposal": stored.get("latest_order_proposal"),
        "last_blocker": stored.get("last_blocker"),
        "last_error": stored.get("last_error"),
        "pause_effect": stored.get("pause_effect") or "pause 會先寫入 run state 並讓未來 worker poll/submit fail-closed；目前尚未綁定長駐 strategy worker。",
        "stop_effect": stored.get("stop_effect") or "stop 會寫入 stopped state 並阻斷後續下單；目前 open orders 仍需透過 shared account reconciliation / 人工場館確認。",
        "cancel_open_orders_status": stored.get("cancel_open_orders_status") or "not_bound_to_exchange_adapter",
        "latest_command": stored.get("latest_command"),
        "latest_command_at": stored.get("latest_command_at"),
        "next_min_gap": (
            stored.get("next_min_gap")
            or "按「同步 worker」可產生 paper/shadow parity event；下一步是把 proposal 接到 24h outcome reconciliation。"
        ),
        "operator_action": stored.get("operator_action") or "目前控制面安全 fail-closed：UI 可啟停狀態與 freeze bundle，但不會直接呼叫 OKX 下單。",
    }



def _initial_worker_control(run_id: str, profile_id: str, *, shadow_only: bool) -> Dict[str, Any]:
    return {
        "status": "shadow_worker_not_started" if shadow_only else "backend_worker_pending",
        "run_id": run_id,
        "profile_id": profile_id,
        "backend_worker_bound": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "latest_command": "start",
        "latest_command_at": _utcnow_iso(),
        "cancel_open_orders_status": "not_requested",
        "operator_action": (
            "影子觀察只收集決策事件；不送單、不加倉。"
            if shadow_only
            else "strategy bundle 已 freeze；可用「同步 worker」產生 paper/shadow parity event，送單前仍 fail-closed。"
        ),
        "next_min_gap": "把 paper/shadow proposal 接到 24h outcome reconciliation；live buy/add 仍等 current-live / venue / bounded canary gate。",
    }



def _load_strategy_bundle_gate(row: Dict[str, Any]) -> Dict[str, Any]:
    expected_hash = str(row.get("strategy_bundle_hash") or "").strip()
    path_text = str(row.get("strategy_bundle_path") or "").strip()
    gate: Dict[str, Any] = {
        "status": "unknown",
        "expected_bundle_hash": expected_hash or None,
        "strategy_bundle_path": path_text or None,
        "bundle_hash_match": False,
    }
    if not expected_hash:
        gate["status"] = "missing_strategy_bundle_hash"
        return gate
    if not path_text:
        gate["status"] = "missing_strategy_bundle_path"
        return gate
    path = Path(path_text).expanduser()
    if not path.exists():
        gate["status"] = "missing_strategy_bundle_file"
        return gate
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        gate.update({"status": "strategy_bundle_json_error", "error": str(exc)[:160]})
        return gate
    if not isinstance(artifact, dict):
        gate["status"] = "strategy_bundle_json_not_object"
        return gate
    artifact_hash = str(artifact.get("bundle_hash") or "").strip()
    gate["artifact_bundle_hash"] = artifact_hash or None
    gate["bundle_id"] = artifact.get("bundle_id")
    gate["deployability_status"] = artifact.get("deployability_status")
    gate["binding_status"] = _as_dict(artifact.get("execution_binding")).get("binding_status")
    if artifact_hash != expected_hash:
        gate["status"] = "strategy_bundle_hash_mismatch"
        return gate
    gate["status"] = "strategy_bundle_hash_match"
    gate["bundle_hash_match"] = True
    return gate



def _build_worker_order_proposal(row: Dict[str, Any], status_payload: Optional[Dict[str, Any]], now: str) -> Dict[str, Any]:
    status_payload = _as_dict(status_payload)
    execution = _as_dict(status_payload.get("execution"))
    surface = _as_dict(status_payload.get("execution_surface_contract"))
    live_runtime_truth = _as_dict(execution.get("live_runtime_truth") or surface.get("live_runtime_truth"))
    signal = str(live_runtime_truth.get("signal") or "HOLD").strip() or "HOLD"
    deployment_blocker = live_runtime_truth.get("deployment_blocker") or live_runtime_truth.get("execution_guardrail_reason")
    return {
        "proposal_schema_version": 1,
        "generated_at": now,
        "run_id": row.get("id"),
        "profile_id": row.get("profile_id"),
        "symbol": row.get("symbol") or status_payload.get("symbol"),
        "venue": row.get("venue"),
        "mode": "paper_shadow" if str(row.get("runtime_binding_status") or "") == SHADOW_RUNTIME_BINDING_STATUS else "paper",
        "signal": signal,
        "allowed_layers": live_runtime_truth.get("allowed_layers"),
        "runtime_closure_state": live_runtime_truth.get("runtime_closure_state"),
        "deployment_blocker": deployment_blocker,
        "side": "paper_shadow_decision",
        "qty": None,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": False,
        "operator_action": (
            "已記錄 paper/shadow worker proposal；這是演練事件，不送 OKX、不加倉。"
            if not deployment_blocker
            else "已記錄 paper/shadow worker proposal；current-live guardrail 仍阻塞真實買入 / 加倉。"
        ),
    }



def _build_exact_worker_order_proposal(row: Dict[str, Any], runtime_cycle: Dict[str, Any], now: str) -> Dict[str, Any]:
    decision = _as_dict(runtime_cycle.get("decision"))
    return {
        "proposal_schema_version": 2,
        "proposal_source": "exact_strategy_runtime",
        "generated_at": now,
        "run_id": row.get("id"),
        "managed_run_id": runtime_cycle.get("managed_run_id"),
        "profile_id": row.get("profile_id"),
        "strategy_name": runtime_cycle.get("strategy_name") or row.get("strategy_name"),
        "strategy_hash": runtime_cycle.get("strategy_hash"),
        "model_name": runtime_cycle.get("model_name"),
        "model_sha256": runtime_cycle.get("model_sha256"),
        "training_data_sha256": runtime_cycle.get("training_data_sha256"),
        "feature_schema_sha256": runtime_cycle.get("feature_schema_sha256"),
        "symbol": decision.get("symbol") or row.get("symbol"),
        "venue": decision.get("venue") or row.get("venue"),
        "mode": "paper_shadow",
        "feature_timestamp": decision.get("feature_timestamp"),
        "price": decision.get("price"),
        "signal": decision.get("signal") or "HOLD",
        "action": decision.get("action") or "HOLD",
        "side": decision.get("side"),
        "qty": decision.get("qty"),
        "model_confidence": decision.get("model_confidence"),
        "entry_quality": decision.get("entry_quality"),
        "allowed_layers": decision.get("allowed_layers"),
        "runtime_reason": decision.get("reason"),
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": False,
        "operator_action": "已用回測時 exact fitted model 完成一次受控 Paper/Shadow cycle；只記錄決策與 outcome lineage，不送實單。",
    }


def _pending_worker_proposal_gate(db, run_id: str, *, now: datetime) -> Optional[Dict[str, Any]]:
    row = _one(
        db,
        """
        SELECT id, payload_json, created_at
        FROM execution_run_events
        WHERE run_id = :run_id
          AND event_type = :event_type
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        {"run_id": run_id, "event_type": WORKER_POLL_EVENT_TYPE},
    )
    if not row:
        return None
    payload = _json_loads(row.get("payload_json"))
    payload = payload if isinstance(payload, dict) else {}
    proposal = payload.get("order_proposal") if isinstance(payload.get("order_proposal"), dict) else None
    if proposal is None:
        return None
    proposal_time = _parse_datetime(proposal.get("generated_at"))
    if proposal_time is None:
        return None
    window_end = proposal_time + timedelta(hours=PAPER_SHADOW_OUTCOME_WINDOW_HOURS)
    if now >= window_end:
        return None
    seconds_remaining = max(0.0, (window_end - now).total_seconds())
    return {
        "status": "pending_observation_window",
        "run_id": run_id,
        "event_id": row.get("id"),
        "event_created_at": row.get("created_at"),
        "proposal_generated_at": proposal_time.isoformat().replace("+00:00", "Z"),
        "window_end": window_end.isoformat().replace("+00:00", "Z"),
        "hours_remaining": round(seconds_remaining / 3600.0, 3),
        "window_hours": PAPER_SHADOW_OUTCOME_WINDOW_HOURS,
        "operator_action": "這條 run 已有未到期的 paper/shadow proposal；等待 24h window 結束並 reconcile，不重複寫入 poll event。",
    }


def poll_execution_paper_shadow_workers(
    db,
    status_payload: Optional[Dict[str, Any]] = None,
    *,
    limit: int = 20,
    exact_runtime_cycles: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    ensure_execution_control_plane_schema(db)
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat().replace("+00:00", "Z")
    run_rows = _rows(
        db,
        """
        SELECT *
        FROM execution_runs
        WHERE state = 'running'
        ORDER BY updated_at ASC, created_at ASC
        LIMIT :limit
        """,
        {"limit": max(1, min(int(limit or 20), 100))},
    )
    processed_run_ids: List[str] = []
    parity_blocked_run_ids: List[str] = []
    pending_outcome_blocked_run_ids: List[str] = []
    pending_outcome_gates: List[Dict[str, Any]] = []
    poll_event_count = 0
    exact_runtime_cycles = exact_runtime_cycles if isinstance(exact_runtime_cycles, dict) else {}

    for row in run_rows:
        run_id = str(row.get("id") or "")
        profile_id = str(row.get("profile_id") or "")
        if not run_id or not profile_id:
            continue
        worker_control = _worker_control_contract(row, "running")
        pending_gate = _pending_worker_proposal_gate(db, run_id, now=now_dt)
        if pending_gate is not None:
            pending_outcome_blocked_run_ids.append(run_id)
            pending_outcome_gates.append(pending_gate)
            continue
        bundle_gate = _load_strategy_bundle_gate(row)
        bundle_hash_match = bool(bundle_gate.get("bundle_hash_match"))
        exact_cycle = _as_dict(exact_runtime_cycles.get(run_id))
        exact_cycle_used = bool(bundle_hash_match and exact_cycle.get("status") == "exact_strategy_cycle_completed")
        proposal = (
            _build_exact_worker_order_proposal(row, exact_cycle, now)
            if exact_cycle_used
            else _build_worker_order_proposal(row, status_payload, now)
            if bundle_hash_match
            else None
        )
        poll_count = int(worker_control.get("poll_count") or 0) + 1
        event_type = WORKER_POLL_EVENT_TYPE if bundle_hash_match else WORKER_PARITY_BLOCKED_EVENT_TYPE
        level = "info" if bundle_hash_match else "warning"
        message = (
            "exact fitted-model Paper/Shadow cycle 已完成並寫入可追溯 proposal；不送單、不加倉。"
            if exact_cycle_used
            else "backend paper/shadow worker 已完成 state poll；bundle hash match，已寫入演練 proposal；不送單、不加倉。"
            if bundle_hash_match
            else "backend paper/shadow worker 已拒絕產生 proposal：strategy bundle parity gate 未通過。"
        )
        worker_control.update(
            {
                "status": "exact_strategy_cycle_recorded" if exact_cycle_used else "paper_shadow_worker_polled" if bundle_hash_match else "worker_bundle_parity_blocked",
                "state": "running",
                "backend_worker_bound": False,
                "poll_handler_available": bundle_hash_match,
                "continuous_worker": False,
                "runtime_cycle_recorded": exact_cycle_used,
                "worker_kind": "exact_strategy_runtime_cycle" if exact_cycle_used else "backend_managed_state_poller",
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "bundle_hash_match": bundle_hash_match,
                "last_poll_at": now,
                "poll_count": poll_count,
                "latest_command": "worker_poll",
                "latest_command_at": now,
                "latest_order_proposal": proposal,
                "last_blocker": None if bundle_hash_match else bundle_gate.get("status"),
                "last_error": bundle_gate.get("error"),
                "operator_action": (
                    "exact fitted model 已完成受控 cycle；接下來只累積 24h outcome 與 replay parity，Live gate 不變。"
                    if exact_cycle_used
                    else "backend state poller 已記錄 paper/shadow proposal；run 暫停 / 停止後下一輪 poll 不會再產生事件。"
                    if bundle_hash_match
                    else "請先修復 strategy bundle hash/path parity；worker 在 parity gate 通過前不產生演練 proposal。"
                ),
                "next_min_gap": (
                    "接 24h paper/shadow outcome reconciliation；live buy/add 仍需 current-live、venue lifecycle 與 bounded canary gate 全過。"
                    if bundle_hash_match
                    else "重建或重新 freeze Strategy Lab bundle，確保 DB run hash 與 bundle artifact hash 一致。"
                ),
            }
        )
        event_payload = {
            "worker_control": worker_control,
            "bundle_gate": bundle_gate,
            "order_proposal": proposal,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
        }
        db.execute(
            text(
                """
                UPDATE execution_runs
                SET worker_status = :worker_status,
                    worker_control_json = :worker_control_json,
                    last_event_type = :last_event_type,
                    last_event_message = :last_event_message,
                    last_event_at = :last_event_at,
                    updated_at = :updated_at
                WHERE id = :run_id
                """
            ),
            {
                "run_id": run_id,
                "worker_status": worker_control.get("status"),
                "worker_control_json": _json_dumps(worker_control),
                "last_event_type": event_type,
                "last_event_message": message,
                "last_event_at": now,
                "updated_at": now,
            },
        )
        _insert_event(
            db,
            run_id=run_id,
            profile_id=profile_id,
            event_type=event_type,
            level=level,
            message=message,
            payload=event_payload,
            created_at=now,
        )
        processed_run_ids.append(run_id)
        poll_event_count += 1 if bundle_hash_match else 0
        if not bundle_hash_match:
            parity_blocked_run_ids.append(run_id)

    db.commit()
    updated_rows = []
    returned_run_ids = processed_run_ids + [run_id for run_id in pending_outcome_blocked_run_ids if run_id not in processed_run_ids]
    if returned_run_ids:
        placeholders = ", ".join([f":run_id_{idx}" for idx, _ in enumerate(returned_run_ids)])
        params = {f"run_id_{idx}": run_id for idx, run_id in enumerate(returned_run_ids)}
        updated_rows = _rows(db, f"SELECT * FROM execution_runs WHERE id IN ({placeholders})", params)
    events_by_run = _load_run_events(db, [str(row.get("id") or "") for row in updated_rows])
    status = "ok" if processed_run_ids else ("pending_outcome_blocked" if pending_outcome_blocked_run_ids else "no_running_runs")
    return {
        "status": status,
        "operator_message": (
            "backend paper/shadow worker poll 已完成；只產生演練事件，不送單、不加倉。"
            if processed_run_ids
            else (
                "已有 running run 的 24h paper/shadow outcome 尚未到期；本次不重複寫入 worker poll event。"
                if pending_outcome_blocked_run_ids
                else "目前沒有 running run 可供 backend paper/shadow worker poll。"
            )
        ),
        "summary": {
            "running_runs_checked": len(run_rows),
            "processed_runs": len(processed_run_ids),
            "poll_events_recorded": poll_event_count,
            "parity_blocked_runs": len(parity_blocked_run_ids),
            "pending_outcome_blocked_runs": len(pending_outcome_blocked_run_ids),
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
        },
        "processed_run_ids": processed_run_ids,
        "parity_blocked_run_ids": parity_blocked_run_ids,
        "pending_outcome_blocked_run_ids": pending_outcome_blocked_run_ids,
        "pending_outcome_gates": pending_outcome_gates,
        "runs": [
            _serialize_run(row, events_by_run.get(str(row.get("id") or ""), []), status_payload=status_payload)
            for row in updated_rows
        ],
    }



def _label_outcome_for_proposal(
    db,
    *,
    symbol: Any,
    proposal_time: datetime,
) -> Optional[Dict[str, Any]]:
    symbol_key = _normalize_symbol_key(symbol) or ""
    tolerance = timedelta(hours=PAPER_SHADOW_LABEL_MATCH_TOLERANCE_HOURS)
    # Use date-prefix bounds so both canonical SQLite DateTime strings
    # (``YYYY-MM-DD HH:MM:SS``) and legacy ISO strings containing ``T``/``Z``
    # remain comparable while the composite horizon/timestamp index can still
    # bound the scan. The exact ± tolerance is enforced below in Python.
    window_start_date = (proposal_time - tolerance).date().isoformat()
    window_end_exclusive = ((proposal_time + tolerance).date() + timedelta(days=1)).isoformat()
    rows = _rows(
        db,
        """
        SELECT timestamp, symbol, simulated_pyramid_win, simulated_pyramid_pnl, simulated_pyramid_quality
        FROM labels
        WHERE horizon_minutes = 1440
          AND simulated_pyramid_win IS NOT NULL
          AND timestamp >= :window_start_date
          AND timestamp < :window_end_exclusive
          AND (
              :symbol_key = ''
              OR UPPER(
                  REPLACE(REPLACE(REPLACE(COALESCE(symbol, ''), '/', ''), '-', ''), '_', '')
              ) = :symbol_key
          )
        ORDER BY timestamp DESC
        """,
        {
            "window_start_date": window_start_date,
            "window_end_exclusive": window_end_exclusive,
            "symbol_key": symbol_key,
        },
    )
    nearest: Optional[Dict[str, Any]] = None
    nearest_delta: Optional[float] = None
    for row in rows:
        if symbol_key and _normalize_symbol_key(row.get("symbol")) != symbol_key:
            continue
        label_time = _parse_datetime(row.get("timestamp"))
        if label_time is None:
            continue
        delta_seconds = abs((label_time - proposal_time).total_seconds())
        if nearest_delta is None or delta_seconds < nearest_delta:
            nearest = row
            nearest_delta = delta_seconds
    if nearest is None or nearest_delta is None:
        return None
    tolerance_seconds = PAPER_SHADOW_LABEL_MATCH_TOLERANCE_HOURS * 3600
    if nearest_delta > tolerance_seconds:
        return None
    return {
        "status": "resolved_from_1440m_label",
        "label_timestamp": _parse_datetime(nearest.get("timestamp")).isoformat().replace("+00:00", "Z") if _parse_datetime(nearest.get("timestamp")) else nearest.get("timestamp"),
        "match_delta_minutes": round(nearest_delta / 60.0, 3),
        "pyramid_win": bool(int(nearest.get("simulated_pyramid_win") or 0)),
        "simulated_pyramid_win": int(nearest.get("simulated_pyramid_win") or 0),
        "pnl_pct": _to_float_maybe(nearest.get("simulated_pyramid_pnl")),
        "quality": _to_float_maybe(nearest.get("simulated_pyramid_quality")),
        "source": "labels.simulated_pyramid_1440m",
    }



def _outcome_for_worker_proposal(db, proposal: Dict[str, Any], *, now: datetime) -> Dict[str, Any]:
    proposal_time = _parse_datetime(proposal.get("generated_at"))
    if proposal_time is None:
        return {
            "status": "proposal_time_unparseable",
            "window_hours": PAPER_SHADOW_OUTCOME_WINDOW_HOURS,
            "pyramid_win": None,
            "pnl_pct": None,
            "quality": None,
            "operator_action": "proposal generated_at 無法解析；需重新產生 paper/shadow worker event。",
        }
    window_end = proposal_time + timedelta(hours=PAPER_SHADOW_OUTCOME_WINDOW_HOURS)
    base = {
        "window_hours": PAPER_SHADOW_OUTCOME_WINDOW_HOURS,
        "proposal_time": proposal_time.isoformat().replace("+00:00", "Z"),
        "window_end": window_end.isoformat().replace("+00:00", "Z"),
    }
    if now < window_end:
        seconds_remaining = max(0.0, (window_end - now).total_seconds())
        return {
            **base,
            "status": "pending_observation_window",
            "hours_remaining": round(seconds_remaining / 3600.0, 3),
            "pyramid_win": None,
            "pnl_pct": None,
            "quality": None,
            "operator_action": "24h observation window 尚未結束；只保留 paper/shadow 記錄，不送單。",
        }

    label_outcome = _label_outcome_for_proposal(db, symbol=proposal.get("symbol"), proposal_time=proposal_time)
    if label_outcome is None:
        return {
            **base,
            "status": "awaiting_label_replay",
            "pyramid_win": None,
            "pnl_pct": None,
            "quality": None,
            "operator_action": "24h window 已結束，但尚未找到匹配的 1440m simulated_pyramid label；需重跑 labels/backfill。",
        }
    return {
        **base,
        **label_outcome,
        "operator_action": "24h shadow outcome 已由 canonical 1440m label resolved；仍只是演練證據，不代表 live-ready。",
    }


def _bool_from_sql(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))
    text_value = str(value).strip().lower()
    if text_value in {"1", "true", "yes", "y"}:
        return True
    if text_value in {"0", "false", "no", "n"}:
        return False
    return None



def _live_runner_jsonl_summary(run_id: str, *, jsonl_root: Optional[Path] = None) -> Dict[str, Any]:
    if not run_id:
        return {"exists": False, "path": None, "line_count": 0, "latest_record": None}
    path = Path(jsonl_root or LIVE_TRADING_ROOT) / f"{run_id}.jsonl"
    if not path.exists():
        return {"exists": False, "path": str(path), "line_count": 0, "latest_record": None}
    line_count = 0
    latest_record: Optional[Dict[str, Any]] = None
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text_value = line.strip()
                if not text_value:
                    continue
                line_count += 1
                try:
                    parsed = json.loads(text_value)
                except Exception:
                    continue
                if isinstance(parsed, dict):
                    latest_record = parsed
    except Exception as exc:
        return {
            "exists": True,
            "path": str(path),
            "line_count": line_count,
            "latest_record": None,
            "error": str(exc),
        }
    compact_latest = None
    if isinstance(latest_record, dict):
        compact_latest = {
            "run_id": latest_record.get("run_id"),
            "created_at": latest_record.get("created_at"),
            "feature_timestamp": latest_record.get("feature_timestamp"),
            "action": latest_record.get("action"),
            "reason": latest_record.get("reason"),
            "order_submitted": bool(latest_record.get("order_submitted")),
            "dry_run": latest_record.get("dry_run"),
            "model_confidence": _to_float_maybe(latest_record.get("model_confidence")),
            "entry_quality": _to_float_maybe(latest_record.get("entry_quality")),
        }
    return {"exists": True, "path": str(path), "line_count": line_count, "latest_record": compact_latest}



def _serialize_live_runner_decision(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    payload = _json_loads(row.get("payload_json"))
    payload = payload if isinstance(payload, dict) else {}
    order_submitted = bool(_bool_from_sql(row.get("order_submitted")))
    dry_run = _bool_from_sql(row.get("dry_run"))
    return {
        "decision_id": row.get("id"),
        "run_id": row.get("run_id"),
        "strategy_name": row.get("strategy_name"),
        "strategy_hash": row.get("strategy_hash"),
        "symbol": row.get("symbol"),
        "venue": row.get("venue"),
        "feature_timestamp": row.get("feature_timestamp"),
        "created_at": row.get("created_at"),
        "price": _to_float_maybe(row.get("price")),
        "signal": row.get("signal"),
        "action": row.get("action"),
        "side": row.get("side"),
        "qty": _to_float_maybe(row.get("qty")),
        "quote_amount": _to_float_maybe(row.get("quote_amount")),
        "order_id": row.get("order_id"),
        "client_order_id": row.get("client_order_id"),
        "order_submitted": order_submitted,
        "dry_run": dry_run,
        "live_order_submitted": bool(order_submitted and dry_run is False),
        "model_confidence": _to_float_maybe(row.get("model_confidence")),
        "entry_quality": _to_float_maybe(row.get("entry_quality")),
        "allowed_layers": _to_int_maybe(row.get("allowed_layers")),
        "regime_gate": row.get("regime_gate"),
        "structure_bucket": row.get("structure_bucket"),
        "reason": row.get("reason"),
        "payload_summary": {
            "has_execution_result": isinstance(payload.get("execution_result"), dict),
            "has_execution_reject": isinstance(payload.get("execution_reject"), dict),
            "has_execution_error": bool(payload.get("execution_error")),
            "has_layer": isinstance(payload.get("layer"), dict),
            "open_layers": len(payload.get("open_layers") or []) if isinstance(payload.get("open_layers"), list) else None,
        },
    }



def _serialize_live_runner_run(row: Optional[Dict[str, Any]], *, jsonl_root: Path) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    config_payload = _json_loads(row.get("config_json"))
    config_payload = config_payload if isinstance(config_payload, dict) else {}
    execution_cfg = _as_dict(config_payload.get("execution"))
    trading_cfg = _as_dict(config_payload.get("trading"))
    return {
        "run_id": row.get("id"),
        "strategy_name": row.get("strategy_name"),
        "strategy_hash": row.get("strategy_hash"),
        "symbol": row.get("symbol"),
        "venue": row.get("venue"),
        "mode": row.get("mode"),
        "status": row.get("status"),
        "model_artifact_path": row.get("model_artifact_path"),
        "started_at": row.get("started_at"),
        "stopped_at": row.get("stopped_at"),
        "last_heartbeat_at": row.get("last_heartbeat_at"),
        "jsonl": _live_runner_jsonl_summary(str(row.get("id") or ""), jsonl_root=jsonl_root),
        "config_contract": {
            "redacted_config_present": bool(config_payload),
            "execution_mode": execution_cfg.get("mode"),
            "dry_run": trading_cfg.get("dry_run"),
            "live_canary_enabled": bool(_as_dict(execution_cfg.get("live_canary")).get("enabled")),
        },
    }



def _live_runner_decision_to_proposal(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    action = str(row.get("action") or "").upper()
    side = str(row.get("side") or "").lower()
    if action not in {"BUY_LAYER", "SELL_ALL"} and side not in {"buy", "sell", "reduce"}:
        return None
    generated_at = row.get("feature_timestamp") or row.get("created_at")
    if _parse_datetime(generated_at) is None:
        return None
    order_submitted = bool(_bool_from_sql(row.get("order_submitted")))
    dry_run = _bool_from_sql(row.get("dry_run"))
    return {
        "source": "live_runner_decisions",
        "source_decision_id": row.get("id"),
        "run_id": row.get("run_id"),
        "symbol": row.get("symbol"),
        "venue": row.get("venue"),
        "generated_at": generated_at,
        "feature_timestamp": row.get("feature_timestamp"),
        "action": row.get("action"),
        "side": row.get("side"),
        "qty": _to_float_maybe(row.get("qty")),
        "price": _to_float_maybe(row.get("price")),
        "model_confidence": _to_float_maybe(row.get("model_confidence")),
        "entry_quality": _to_float_maybe(row.get("entry_quality")),
        "allowed_layers": _to_int_maybe(row.get("allowed_layers")),
        "regime_gate": row.get("regime_gate"),
        "structure_bucket": row.get("structure_bucket"),
        "reason": row.get("reason"),
        "order_submitted": order_submitted,
        "dry_run": dry_run,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": bool(order_submitted and dry_run is False),
    }



def build_live_runner_overview(
    db,
    status_payload: Optional[Dict[str, Any]] = None,
    *,
    now: Optional[datetime] = None,
    jsonl_root: Optional[Path] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Summarize standalone live_runner audit DB/JSONL rows for operator surfaces."""

    now = now or datetime.now(timezone.utc)
    jsonl_root = Path(jsonl_root or LIVE_TRADING_ROOT)
    limit = max(1, min(int(limit or 100), 500))
    if not _table_exists(db, "live_runner_runs") or not _table_exists(db, "live_runner_decisions"):
        gate = {
            "status": "no_live_runner_tables",
            "window_hours": PAPER_SHADOW_OUTCOME_WINDOW_HOURS,
            "candidate_decisions": 0,
            "pending_outcomes": 0,
            "resolved_outcomes": 0,
            "awaiting_label_replay": 0,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
            "operator_message": "standalone live runner 尚未建立 audit tables；先啟動 paper/shadow runner smoke。",
        }
        return {
            "status": "no_live_runner_tables",
            "source": "live_runner_runs/live_runner_decisions",
            "jsonl_root": str(jsonl_root),
            "summary": {
                "total_runs": 0,
                "running_runs": 0,
                "stopped_runs": 0,
                "failed_runs": 0,
                "total_decisions": 0,
                "candidate_decisions": 0,
                "jsonl_backed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "live_order_submitted": False,
            },
            "latest_run": None,
            "latest_decision": None,
            "shadow_evidence_gate": gate,
            "operator_message": gate["operator_message"],
        }

    status_rows = _rows(
        db,
        """
        SELECT status, COUNT(*) AS count
        FROM live_runner_runs
        GROUP BY status
        """,
    )
    status_counts = {str(row.get("status") or "unknown"): int(row.get("count") or 0) for row in status_rows}
    total_runs = sum(status_counts.values())
    total_decisions_row = _one(db, "SELECT COUNT(*) AS count FROM live_runner_decisions") or {}
    total_decisions = int(total_decisions_row.get("count") or 0)
    latest_run_row = _one(
        db,
        """
        SELECT *
        FROM live_runner_runs
        ORDER BY COALESCE(last_heartbeat_at, stopped_at, started_at) DESC, started_at DESC
        LIMIT 1
        """,
    )
    latest_decision_row = _one(
        db,
        """
        SELECT *
        FROM live_runner_decisions
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
    )
    candidate_rows = _rows(
        db,
        """
        SELECT *
        FROM live_runner_decisions
        WHERE action IN ('BUY_LAYER', 'SELL_ALL')
           OR side IN ('buy', 'sell', 'reduce')
           OR order_submitted = 1
        ORDER BY created_at DESC, id DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )

    entries: List[Dict[str, Any]] = []
    pending_count = 0
    resolved_count = 0
    awaiting_label_count = 0
    live_order_submitted = False
    for row in candidate_rows:
        proposal = _live_runner_decision_to_proposal(row)
        if proposal is None:
            continue
        outcome = _outcome_for_worker_proposal(db, proposal, now=now)
        outcome_status = str(outcome.get("status") or "")
        if outcome_status == "pending_observation_window":
            pending_count += 1
        elif outcome_status == "resolved_from_1440m_label":
            resolved_count += 1
        elif outcome_status == "awaiting_label_replay":
            awaiting_label_count += 1
        live_order_submitted = live_order_submitted or bool(proposal.get("live_order_submitted"))
        entries.append(
            {
                "source": "live_runner_decisions",
                "decision_id": row.get("id"),
                "run_id": row.get("run_id"),
                "created_at": row.get("created_at"),
                "feature_timestamp": row.get("feature_timestamp"),
                "action": row.get("action"),
                "side": row.get("side"),
                "reason": row.get("reason"),
                "proposal": proposal,
                "outcome_24h": outcome,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "live_order_submitted": bool(proposal.get("live_order_submitted")),
            }
        )

    pending_window_ends = [
        _parse_datetime(_as_dict(entry.get("outcome_24h")).get("window_end"))
        for entry in entries
        if str(_as_dict(entry.get("outcome_24h")).get("status") or "") == "pending_observation_window"
    ]
    pending_window_ends = [value for value in pending_window_ends if value is not None]
    pending_hours_remaining_values = [
        _to_float_maybe(_as_dict(entry.get("outcome_24h")).get("hours_remaining"))
        for entry in entries
        if str(_as_dict(entry.get("outcome_24h")).get("status") or "") == "pending_observation_window"
    ]
    pending_hours_remaining_values = [value for value in pending_hours_remaining_values if value is not None]
    if live_order_submitted:
        gate_status = "safety_violation_live_order"
        operator_message = "live runner evidence 發現 live_order_submitted=true；立即停止並檢查 fail-closed guardrail。"
    elif resolved_count > 0:
        gate_status = "runner_24h_resolved_evidence_ready"
        operator_message = "standalone live runner 已有 24h shadow outcome resolved；只作 paper/shadow 證據，不代表可真實買入。"
    elif pending_count > 0:
        gate_status = "runner_24h_pending_observation"
        operator_message = "standalone live runner 已有候選決策，等待 24h observation window 結束後再對齊 labels。"
    elif awaiting_label_count > 0:
        gate_status = "runner_24h_label_replay_required"
        operator_message = "standalone live runner 決策已超過 24h，但尚缺 1440m label；需補 labels/backfill。"
    elif entries:
        gate_status = "runner_24h_evidence_recording"
        operator_message = "standalone live runner 已記錄候選決策；仍只做 paper/shadow evidence，不送單。"
    elif total_decisions > 0:
        gate_status = "runner_observing_no_trade_candidates"
        operator_message = "standalone live runner 正在記錄 HOLD / 非交易決策；尚無需 24h outcome 的買賣候選。"
    elif total_runs > 0:
        gate_status = "runner_started_no_decisions"
        operator_message = "standalone live runner run 已建立，但尚無決策列；先確認 runner 是否持續 heartbeat。"
    else:
        gate_status = "needs_live_runner_shadow_run"
        operator_message = "尚未建立 standalone live runner run；先以 --dry-run / --no-submit 啟動 shadow smoke。"

    latest_run = _serialize_live_runner_run(latest_run_row, jsonl_root=jsonl_root)
    latest_decision = _serialize_live_runner_decision(latest_decision_row)
    latest_run_dict = _as_dict(latest_run)
    jsonl_backed = bool(_as_dict(latest_run_dict.get("jsonl")).get("exists")) if latest_run else False
    latest_entry = entries[0] if entries else None
    gate = {
        "status": gate_status,
        "source": "live_runner_decisions",
        "window_hours": PAPER_SHADOW_OUTCOME_WINDOW_HOURS,
        "candidate_decisions": len(entries),
        "pending_outcomes": pending_count,
        "resolved_outcomes": resolved_count,
        "awaiting_label_replay": awaiting_label_count,
        "next_reconcile_at": min(pending_window_ends).isoformat().replace("+00:00", "Z") if pending_window_ends else None,
        "pending_hours_remaining_min": round(min(pending_hours_remaining_values), 3) if pending_hours_remaining_values else None,
        "latest_entry": {
            "decision_id": latest_entry.get("decision_id"),
            "run_id": latest_entry.get("run_id"),
            "created_at": latest_entry.get("created_at"),
            "feature_timestamp": latest_entry.get("feature_timestamp"),
            "action": latest_entry.get("action"),
            "outcome_status": _as_dict(latest_entry.get("outcome_24h")).get("status"),
        } if latest_entry else None,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": live_order_submitted,
        "blocked_live_actions": ["live_buy", "live_add", "automation_enable"],
        "operator_message": operator_message,
    }
    return {
        "status": gate_status,
        "source": "live_runner_runs/live_runner_decisions+jsonl",
        "jsonl_root": str(jsonl_root),
        "summary": {
            "total_runs": total_runs,
            "running_runs": status_counts.get("running", 0),
            "stopped_runs": status_counts.get("stopped", 0),
            "failed_runs": status_counts.get("failed", 0),
            "status_counts": status_counts,
            "total_decisions": total_decisions,
            "candidate_decisions": len(entries),
            "jsonl_backed": jsonl_backed,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": live_order_submitted,
        },
        "latest_run": latest_run,
        "latest_decision": latest_decision,
        "shadow_evidence_gate": gate,
        "recent_entries": entries[:10],
        "operator_message": operator_message,
    }



def _build_paper_shadow_rehearsal_proof(
    db,
    *,
    artifact_status: str,
    summary: Dict[str, Any],
    entry_count: int,
    entries: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    run_rows = _rows(
        db,
        """
        SELECT state, COUNT(*) AS count
        FROM execution_runs
        GROUP BY state
        """,
    )
    run_counts = {str(row.get("state") or "unknown"): int(row.get("count") or 0) for row in run_rows}
    total_runs = sum(run_counts.values())
    running_runs = run_counts.get("running", 0)
    paused_runs = run_counts.get("paused", 0)
    stopped_runs = run_counts.get("stopped", 0)
    latest_running = _one(
        db,
        """
        SELECT id, profile_id, state, worker_status, last_event_type, last_event_at, strategy_bundle_hash
        FROM execution_runs
        WHERE state = 'running'
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
        """,
    )
    latest_run = latest_running or _one(
        db,
        """
        SELECT id, profile_id, state, worker_status, last_event_type, last_event_at, strategy_bundle_hash
        FROM execution_runs
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
        """,
    )

    resolved = int(summary.get("resolved_outcomes") or 0)
    pending = int(summary.get("pending_outcomes") or 0)
    awaiting_label = int(summary.get("awaiting_label_replay") or 0)
    parity_blocked = int(summary.get("parity_blocked_events") or 0)
    worker_events = int(summary.get("worker_poll_events") or 0)
    live_order_submitted = bool(summary.get("live_order_submitted"))
    entries = entries or []
    pending_windows: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        outcome = entry.get("outcome_24h") if isinstance(entry.get("outcome_24h"), dict) else {}
        if str(outcome.get("status") or "") != "pending_observation_window":
            continue
        window_end = _parse_datetime(outcome.get("window_end"))
        hours_remaining = _to_float_maybe(outcome.get("hours_remaining"))
        pending_windows.append(
            {
                "event_id": entry.get("event_id"),
                "run_id": entry.get("run_id"),
                "window_end": window_end,
                "hours_remaining": hours_remaining,
            }
        )
    pending_window_ends = [item["window_end"] for item in pending_windows if item.get("window_end") is not None]
    next_reconcile_at = min(pending_window_ends).isoformat().replace("+00:00", "Z") if pending_window_ends else None
    pending_hours_remaining_values = [
        float(item["hours_remaining"])
        for item in pending_windows
        if isinstance(item.get("hours_remaining"), (int, float))
    ]
    pending_hours_remaining_min = min(pending_hours_remaining_values) if pending_hours_remaining_values else None
    resolution_due_count = sum(1 for value in pending_hours_remaining_values if value <= 0) + awaiting_label

    if live_order_submitted:
        status = "safety_violation_live_order"
        next_operator_action = "立即停止 rehearsal 並檢查 worker event；paper/shadow outcome 不應出現 live_order_submitted=true。"
    elif resolved > 0:
        status = "resolved_evidence_ready"
        next_operator_action = "檢視 resolved 24h outcome，將勝負 / pnl / quality 用於 paper/shadow 決策證據；live buy/add 仍保持 fail-closed。"
    elif awaiting_label > 0:
        status = "label_replay_required"
        next_operator_action = "重跑 1440m labels/backfill 後再執行 worker outcome reconcile。"
    elif pending > 0:
        status = "pending_observation_window"
        next_operator_action = "等待 24h observation window 結束，或在 label 完成後重新 reconcile。"
    elif parity_blocked > 0:
        status = "bundle_parity_blocked"
        next_operator_action = "重新 freeze strategy bundle，確認 DB run hash 與 bundle artifact hash 一致後再 poll worker。"
    elif running_runs > 0:
        status = "needs_worker_poll"
        next_operator_action = "已有 running run；按「同步 worker」產生 paper/shadow proposal event，再進入 24h outcome reconciliation。"
    elif total_runs > 0:
        status = "needs_running_run"
        next_operator_action = "先 resume 或重新 start 一條 paper/shadow run；非 running run 不會產生 worker proposal。"
    else:
        status = "needs_paper_shadow_run"
        next_operator_action = "先在 Execution Console 啟動可用的 paper/shadow sleeve，然後同步 worker 產生 rehearsal event。"

    chain = [
        {
            "key": "start_run",
            "label": "Start paper/shadow run",
            "status": "complete" if total_runs > 0 else "required",
            "count": total_runs,
        },
        {
            "key": "worker_poll",
            "label": "Worker poll proposal",
            "status": "complete" if worker_events > 0 else ("ready" if running_runs > 0 else "blocked"),
            "count": worker_events,
        },
        {
            "key": "outcome_reconciliation",
            "label": "24h outcome reconciliation",
            "status": "complete" if entry_count > 0 else "waiting_for_worker_event",
            "count": entry_count,
        },
        {
            "key": "label_resolution",
            "label": "1440m label resolution",
            "status": "complete" if resolved > 0 else ("pending" if pending > 0 else ("required" if awaiting_label > 0 else "not_started")),
            "count": resolved,
        },
    ]

    return {
        "status": status,
        "artifact_status": artifact_status,
        "can_poll_workers": running_runs > 0 and pending == 0,
        "can_reconcile_outcomes": entry_count > 0,
        "poll_blocked_by_pending_outcome": pending > 0,
        "next_reconcile_at": next_reconcile_at,
        "pending_hours_remaining_min": round(pending_hours_remaining_min, 3) if pending_hours_remaining_min is not None else None,
        "resolution_due_count": resolution_due_count,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": live_order_submitted,
        "run_counts": {
            "running": running_runs,
            "paused": paused_runs,
            "stopped": stopped_runs,
            "total": total_runs,
        },
        "latest_run": {
            "run_id": latest_run.get("id") if latest_run else None,
            "profile_id": latest_run.get("profile_id") if latest_run else None,
            "state": latest_run.get("state") if latest_run else None,
            "worker_status": latest_run.get("worker_status") if latest_run else None,
            "last_event_type": latest_run.get("last_event_type") if latest_run else None,
            "last_event_at": latest_run.get("last_event_at") if latest_run else None,
            "strategy_bundle_hash": latest_run.get("strategy_bundle_hash") if latest_run else None,
        },
        "chain": chain,
        "next_operator_action": next_operator_action,
        "blocked_live_actions": ["live_buy", "live_add", "automation_enable"],
        "operator_message": "這是 paper/shadow rehearsal proof，只證明演練鏈路狀態；不代表可真實下單。",
    }



def build_paper_shadow_outcome_reconciliation(
    db,
    status_payload: Optional[Dict[str, Any]] = None,
    *,
    persist: bool = False,
    artifact_path: Optional[Path] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    limit = max(1, min(int(limit or 100), 500))
    rows = _rows(
        db,
        """
        SELECT
            events.id AS event_id,
            events.run_id AS run_id,
            events.profile_id AS profile_id,
            events.event_type AS event_type,
            events.level AS level,
            events.message AS message,
            events.payload_json AS payload_json,
            events.created_at AS created_at,
            runs.state AS run_state,
            runs.label AS run_label,
            runs.symbol AS run_symbol,
            runs.venue AS run_venue,
            runs.mode AS run_mode,
            runs.strategy_bundle_hash AS strategy_bundle_hash,
            runs.worker_status AS worker_status
        FROM execution_run_events AS events
        LEFT JOIN execution_runs AS runs ON runs.id = events.run_id
        WHERE events.event_type IN (:poll_event_type, :blocked_event_type)
        ORDER BY events.created_at DESC, events.id DESC
        LIMIT :limit
        """,
        {
            "poll_event_type": WORKER_POLL_EVENT_TYPE,
            "blocked_event_type": WORKER_PARITY_BLOCKED_EVENT_TYPE,
            "limit": limit,
        },
    )

    entries: List[Dict[str, Any]] = []
    parity_blocked_count = 0
    pending_count = 0
    resolved_count = 0
    awaiting_label_count = 0
    proposal_count = 0

    for row in rows:
        payload = _json_loads(row.get("payload_json"))
        payload = payload if isinstance(payload, dict) else {}
        proposal = payload.get("order_proposal") if isinstance(payload.get("order_proposal"), dict) else None
        bundle_gate = payload.get("bundle_gate") if isinstance(payload.get("bundle_gate"), dict) else {}
        if str(row.get("event_type") or "") == WORKER_PARITY_BLOCKED_EVENT_TYPE:
            parity_blocked_count += 1
            entries.append(
                {
                    "event_id": row.get("event_id"),
                    "run_id": row.get("run_id"),
                    "profile_id": row.get("profile_id"),
                    "event_type": row.get("event_type"),
                    "created_at": row.get("created_at"),
                    "run_state": row.get("run_state"),
                    "worker_status": row.get("worker_status"),
                    "strategy_bundle_hash": row.get("strategy_bundle_hash"),
                    "bundle_gate": bundle_gate,
                    "outcome_24h": {
                        "status": "blocked_before_proposal",
                        "window_hours": PAPER_SHADOW_OUTCOME_WINDOW_HOURS,
                        "pyramid_win": None,
                        "pnl_pct": None,
                        "operator_action": "bundle parity gate 未過，沒有產生 paper/shadow proposal。",
                    },
                    "order_submission_enabled": False,
                    "risk_on_order_enabled": False,
                    "live_order_submitted": False,
                }
            )
            continue
        if proposal is None:
            continue
        proposal_count += 1
        outcome = _outcome_for_worker_proposal(db, proposal, now=now)
        status = str(outcome.get("status") or "")
        if status == "pending_observation_window":
            pending_count += 1
        elif status == "resolved_from_1440m_label":
            resolved_count += 1
        elif status == "awaiting_label_replay":
            awaiting_label_count += 1
        entries.append(
            {
                "event_id": row.get("event_id"),
                "run_id": row.get("run_id"),
                "profile_id": row.get("profile_id"),
                "event_type": row.get("event_type"),
                "created_at": row.get("created_at"),
                "run_state": row.get("run_state"),
                "run_label": row.get("run_label"),
                "worker_status": row.get("worker_status"),
                "strategy_bundle_hash": row.get("strategy_bundle_hash"),
                "proposal": proposal,
                "outcome_24h": outcome,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "live_order_submitted": False,
            }
        )

    if proposal_count == 0 and parity_blocked_count == 0:
        status = "no_worker_events"
    elif resolved_count > 0:
        status = "recording_with_resolved_outcomes"
    elif awaiting_label_count > 0:
        status = "recording_awaiting_label_replay"
    elif pending_count > 0:
        status = "recording_pending_outcomes"
    else:
        status = "recording_blocked_before_proposal"

    live_runner_overview = build_live_runner_overview(
        db,
        status_payload=status_payload,
        now=now,
        limit=limit,
    )
    live_runner_summary = _as_dict(live_runner_overview.get("summary"))
    live_runner_gate = _as_dict(live_runner_overview.get("shadow_evidence_gate"))
    live_runner_live_order_submitted = bool(
        live_runner_summary.get("live_order_submitted") or live_runner_gate.get("live_order_submitted")
    )
    if live_runner_live_order_submitted:
        status = "safety_violation_live_order"
    summary = {
        "worker_poll_events": proposal_count,
        "resolved_outcomes": resolved_count,
        "pending_outcomes": pending_count,
        "awaiting_label_replay": awaiting_label_count,
        "parity_blocked_events": parity_blocked_count,
        "entries": len(entries),
        "live_runner_total_runs": live_runner_summary.get("total_runs", 0),
        "live_runner_total_decisions": live_runner_summary.get("total_decisions", 0),
        "live_runner_candidate_decisions": live_runner_summary.get("candidate_decisions", 0),
        "live_runner_pending_outcomes": live_runner_gate.get("pending_outcomes", 0),
        "live_runner_resolved_outcomes": live_runner_gate.get("resolved_outcomes", 0),
        "live_runner_awaiting_label_replay": live_runner_gate.get("awaiting_label_replay", 0),
        "live_runner_jsonl_backed": bool(live_runner_summary.get("jsonl_backed")),
        "live_order_submitted": live_runner_live_order_submitted,
    }
    rehearsal_proof = _build_paper_shadow_rehearsal_proof(
        db,
        artifact_status=status,
        summary=summary,
        entry_count=len(entries),
        entries=entries,
    )
    resolution_due_count = int(rehearsal_proof.get("resolution_due_count") or 0)
    live_order_submitted = bool(summary.get("live_order_submitted") or rehearsal_proof.get("live_order_submitted"))
    quick_read = {
        "status": status,
        "rehearsal_status": rehearsal_proof.get("status"),
        "worker_poll_events": proposal_count,
        "pending_outcomes": pending_count,
        "resolved_outcomes": resolved_count,
        "awaiting_label_replay": awaiting_label_count,
        "parity_blocked_events": parity_blocked_count,
        "can_poll_workers": rehearsal_proof.get("can_poll_workers"),
        "poll_blocked_by_pending_outcome": rehearsal_proof.get("poll_blocked_by_pending_outcome"),
        "next_reconcile_at": rehearsal_proof.get("next_reconcile_at"),
        "pending_hours_remaining_min": rehearsal_proof.get("pending_hours_remaining_min"),
        "resolution_due_count": resolution_due_count,
        "reconciliation_due": resolution_due_count > 0,
        "live_runner_status": live_runner_overview.get("status"),
        "live_runner_total_runs": live_runner_summary.get("total_runs", 0),
        "live_runner_total_decisions": live_runner_summary.get("total_decisions", 0),
        "live_runner_candidate_decisions": live_runner_gate.get("candidate_decisions", 0),
        "live_runner_pending_outcomes": live_runner_gate.get("pending_outcomes", 0),
        "live_runner_resolved_outcomes": live_runner_gate.get("resolved_outcomes", 0),
        "live_runner_jsonl_backed": bool(live_runner_summary.get("jsonl_backed")),
        "live_runner_next_reconcile_at": live_runner_gate.get("next_reconcile_at"),
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": live_order_submitted,
        "blocked_live_actions": rehearsal_proof.get("blocked_live_actions") or [],
        "operator_message": rehearsal_proof.get("operator_message"),
    }
    artifact = {
        "artifact_schema_version": 2,
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "status": status,
        "rehearsal_status": quick_read["rehearsal_status"],
        "mode": "paper_shadow_outcome_reconciliation",
        "source": "execution_run_events.paper_shadow_worker_poll+live_runner_decisions",
        "window_hours": PAPER_SHADOW_OUTCOME_WINDOW_HOURS,
        "label_source": "labels.simulated_pyramid_1440m",
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "live_order_submitted": live_order_submitted,
        "worker_poll_events": proposal_count,
        "pending_outcomes": pending_count,
        "resolved_outcomes": resolved_count,
        "awaiting_label_replay": awaiting_label_count,
        "parity_blocked_events": parity_blocked_count,
        "can_poll_workers": quick_read["can_poll_workers"],
        "poll_blocked_by_pending_outcome": quick_read["poll_blocked_by_pending_outcome"],
        "next_reconcile_at": quick_read["next_reconcile_at"],
        "pending_hours_remaining_min": quick_read["pending_hours_remaining_min"],
        "resolution_due_count": resolution_due_count,
        "reconciliation_due": quick_read["reconciliation_due"],
        "quick_read": quick_read,
        "summary": summary,
        "rehearsal_proof": rehearsal_proof,
        "live_runner": {
            "status": live_runner_overview.get("status"),
            "summary": live_runner_overview.get("summary"),
            "latest_run": live_runner_overview.get("latest_run"),
            "latest_decision": live_runner_overview.get("latest_decision"),
            "shadow_evidence_gate": live_runner_gate,
            "operator_message": live_runner_overview.get("operator_message"),
        },
        "live_runner_shadow_gate": live_runner_gate,
        "entries": entries,
        "operator_message": (
            "paper/shadow worker outcome reconciliation 已建立；它只核對演練 proposal 與 24h labels，不送單。"
            if entries
            else "尚未有 paper/shadow worker event 可做 outcome reconciliation。"
        ),
    }
    target_path = Path(artifact_path or PAPER_SHADOW_OUTCOME_ARTIFACT_PATH)
    if persist:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "artifact": artifact,
        "artifact_path": str(target_path),
        "persisted": bool(persist),
        # The overview route also needs this snapshot. Returning it avoids a
        # second N+1 outcome scan over the same live-runner decisions.
        "live_runner_overview": live_runner_overview,
    }



def _promotion_status_for_run(row: Dict[str, Any], worker_control: Dict[str, Any]) -> Dict[str, Any]:
    proposal = _as_dict(worker_control.get("latest_order_proposal"))
    exact_runtime = proposal.get("proposal_source") == "exact_strategy_runtime"
    bundle_complete = str(row.get("strategy_bundle_status") or "") == "persisted"
    paper_complete = bool(exact_runtime and proposal)
    progress = int(bundle_complete) + int(exact_runtime) + int(paper_complete)
    if exact_runtime:
        state = "paper_shadow_evidence_recorded"
        next_action = {
            "route": "/execution",
            "label": "執行 24h outcome reconciliation；Promotion 自動化尚未實作",
            "action": "reconcile_outcome",
        }
        operator_fix = None
    else:
        state = "runtime_binding_required"
        next_action = {"route": "/lab", "label": "重新回測並固化 exact fitted model", "action": "rerun_backtest"}
        operator_fix = "回到 Strategy Lab 重新執行 Hybrid 回測；系統會保存 fitted model、training-data、feature-schema checksums。"
    return {
        "state": state,
        "journey_contract_status": "partial_not_promotable",
        "journey_complete": False,
        "progress_current": progress,
        "progress_target": None,
        "declared_stage_count": 5,
        "progress_is_release_metric": False,
        "stages": [
            {"key": "bundle", "label": "策略 Bundle", "status": "complete" if bundle_complete else "blocked"},
            {"key": "exact_runtime", "label": "Exact Model Runtime", "status": "complete" if exact_runtime else "blocked"},
            {"key": "paper_shadow", "label": "Paper / Shadow", "status": "evidence_recorded" if paper_complete else "blocked"},
            {"key": "outcome_24h", "label": "24h Outcome", "status": "reconciliation_required" if paper_complete else "blocked"},
            {"key": "live_candidate", "label": "Live Candidate", "status": "not_implemented"},
        ],
        "next_action": next_action,
        "operator_fix": operator_fix,
        "blocking_reason": "Promotion journey 尚未具備可執行閉環；仍需真實 outcome reconciliation、current exact-bucket、venue lifecycle、bounded-canary gates 與明確 operator promotion action。",
        "safety": {
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
        },
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
    shadow_only = bool(runtime_binding_contract.get("shadow_only"))
    strategy_binding = _json_loads(row.get("strategy_snapshot_json"))
    if not isinstance(strategy_binding, dict):
        strategy_binding = None
    worker_control = _worker_control_contract(row, current_state)
    runtime_liveness = _as_dict(worker_control.get("runtime_liveness"))
    manual_poll_running = current_state == "running" and not bool(worker_control.get("continuous_worker"))
    state_truth = (
        "configured_manual_poll_not_continuous_worker"
        if manual_poll_running
        else "continuous_worker_healthy"
        if current_state == "running" and runtime_liveness.get("healthy")
        else current_state
    )
    return {
        "run_id": row.get("id"),
        "profile_id": row.get("profile_id"),
        "label": row.get("label"),
        "symbol": row.get("symbol"),
        "venue": row.get("venue"),
        "mode": row.get("mode"),
        "state": current_state,
        "state_truth": state_truth,
        "state_label": "已啟用（手動輪詢，非長駐 worker）" if manual_poll_running else _STATE_LABELS.get(current_state, current_state or "unknown"),
        "runtime_liveness": runtime_liveness,
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
        "strategy_binding": strategy_binding,
        "strategy_bundle_hash": row.get("strategy_bundle_hash"),
        "strategy_bundle_path": row.get("strategy_bundle_path"),
        "strategy_bundle_status": row.get("strategy_bundle_status"),
        "worker_status": row.get("worker_status") or worker_control.get("status"),
        "worker_control": worker_control,
        "promotion_status": _promotion_status_for_run(row, worker_control),
        "action_contract": {
            "can_pause": current_state == "running",
            "can_resume": current_state == "paused",
            "can_stop": current_state in {"running", "paused"},
            "shadow_only": shadow_only,
            "risk_on_order_enabled": False,
            "order_submission_enabled": False,
            "worker_control": worker_control,
            "upgrade_prerequisite": (
                "影子觀察運行只能收集即時決策與事件紀錄，不會送單；需等即時支持、場館證據鏈與單一 Bot 帳本通過後再升級。"
                if shadow_only
                else CONTROL_PLANE_UPGRADE_PREREQUISITE
            ),
        },
        "latest_event": latest_event,
        "recent_events": recent_events,
    }



def _serialize_profile(row: Dict[str, Any], current_run: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    snapshot = _json_loads(row.get("snapshot_json")) or {}
    strategy_binding = snapshot.get("strategy_binding") if isinstance(snapshot, dict) else None
    strategy_binding = strategy_binding if isinstance(strategy_binding, dict) else None
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
        "strategy_binding": strategy_binding,
        "snapshot": snapshot,
    }



def _ensure_optional_columns(db, table: str, columns: Dict[str, str]) -> None:
    existing = {
        str(row.get("name") or "")
        for row in _rows(db, f"PRAGMA table_info({table})")
    }
    for column_name, column_def in columns.items():
        if column_name in existing:
            continue
        db.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_def}"))



def ensure_execution_control_plane_schema(db) -> None:
    for statement in _SCHEMA_STATEMENTS:
        db.execute(text(statement))
    _ensure_optional_columns(
        db,
        "execution_runs",
        {
            "strategy_name": "TEXT",
            "strategy_source": "TEXT",
            "strategy_hash": "TEXT",
            "strategy_snapshot_json": "TEXT",
            "strategy_bundle_hash": "TEXT",
            "strategy_bundle_path": "TEXT",
            "strategy_bundle_status": "TEXT",
            "worker_status": "TEXT",
            "worker_control_json": "TEXT",
        },
    )
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
                "venue": execution_payload.get("venue") or "okx",
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
    profile_rows = _build_profile_rows(status_payload, overview_payload)
    run_rows = _rows(db, "SELECT * FROM execution_runs ORDER BY updated_at DESC, created_at DESC")
    events_by_run = _load_run_events(db, [str(row.get("id") or "") for row in run_rows])
    selected_runs_raw = _active_or_latest_run_by_profile(run_rows)
    selected_runs = {
        profile_id: _serialize_run(row, events_by_run.get(str(row.get("id") or ""), []), status_payload=status_payload)
        for profile_id, row in selected_runs_raw.items()
    }
    profiles = [_serialize_profile(row, selected_runs.get(str(row.get("id") or ""))) for row in profile_rows]
    runs = [_serialize_run(row, events_by_run.get(str(row.get("id") or ""), []), status_payload=status_payload) for row in run_rows]

    configured_running_rows = sum(1 for row in run_rows if str(row.get("state") or "") == "running")
    manual_poll_running_rows = sum(
        1 for run in runs if run.get("state_truth") == "configured_manual_poll_not_continuous_worker"
    )
    healthy_continuous_workers = sum(
        1 for run in runs if _as_dict(run.get("runtime_liveness")).get("healthy") is True
    )
    summary = {
        "total_profiles": len(profiles),
        "active_profiles": sum(1 for row in profile_rows if str(row.get("activation_status") or "") == "active"),
        "blocked_profiles": sum(1 for row in profile_rows if "blocked" in str(row.get("lifecycle_status") or "")),
        "standby_profiles": sum(1 for row in profile_rows if str(row.get("lifecycle_status") or "") == "standby"),
        "running_runs": configured_running_rows,
        "configured_running_rows": configured_running_rows,
        "manual_poll_running_rows": manual_poll_running_rows,
        "healthy_continuous_workers": healthy_continuous_workers,
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



def start_execution_profile_run(
    db,
    profile_id: str,
    status_payload: Dict[str, Any],
    overview_payload: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
    *,
    strategy_binding_override: Optional[Dict[str, Any]] = None,
    force_paper_shadow: bool = False,
) -> Dict[str, Any]:
    sync_execution_profiles(db, status_payload, overview_payload)
    snapshot = build_execution_control_plane_snapshot(db, status_payload, overview_payload)
    profile_row = _require_profile_row(db, profile_id)
    profile_snapshot = _json_loads(profile_row.get("snapshot_json")) or {}
    control_contract = profile_snapshot.get("control_contract") if isinstance(profile_snapshot, dict) else {}
    control_contract = control_contract if isinstance(control_contract, dict) else {}
    strategy_binding = profile_snapshot.get("strategy_binding") if isinstance(profile_snapshot, dict) else None
    strategy_binding = strategy_binding if isinstance(strategy_binding, dict) else None
    if strategy_binding_override is not None:
        override_sleeve = str(strategy_binding_override.get("primary_sleeve_key") or "").strip()
        if override_sleeve != profile_id:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "strategy_profile_mismatch",
                    "message": "所選策略與 execution sleeve 不一致，已拒絕建立錯誤綁定。",
                    "context": {"profile_id": profile_id, "strategy_sleeve": override_sleeve or None},
                },
            )
        strategy_binding = dict(strategy_binding_override)
    start_status = str(control_contract.get("start_status") or "")
    shadow_only = bool(force_paper_shadow or (control_contract.get("shadow_only") and start_status == "shadow_start_available"))
    shadow_mode = "paper_shadow" if force_paper_shadow else str(control_contract.get("shadow_mode") or "paper_shadow")
    high_conviction_topk = _as_dict(control_contract.get("high_conviction_topk"))
    if not force_paper_shadow and (start_status.startswith("blocked") or start_status.startswith("inactive")):
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

    allowed_start_statuses = {
        "ready_control_plane",
        "resume_available",
        "shadow_start_available",
        "already_running",
    }
    if not force_paper_shadow and start_status not in allowed_start_statuses:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "profile_not_startable",
                "message": "目前 control contract 不允許啟動這個 sleeve run。",
                "context": {
                    "profile_id": profile_id,
                    "start_status": start_status,
                    "allowed_start_statuses": sorted(allowed_start_statuses),
                },
            },
        )

    if shadow_only and not force_paper_shadow and (
        profile_id != "selective"
        or shadow_mode != "paper_shadow"
        or control_contract.get("risk_on_order_enabled") is not False
        or not high_conviction_topk
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "invalid_shadow_start_contract",
                "message": "影子觀察只能用高信念精選 sleeve，且必須保持不送單、不加倉。",
                "context": {
                    "profile_id": profile_id,
                    "start_status": start_status,
                    "shadow_mode": shadow_mode,
                    "risk_on_order_enabled": control_contract.get("risk_on_order_enabled"),
                },
            },
        )

    if shadow_only and not force_paper_shadow and (not strategy_binding or strategy_binding.get("status") == "missing_saved_strategy"):
        strategy_binding = _shadow_strategy_binding_from_control_contract(profile_id, control_contract)

    if force_paper_shadow and not strategy_binding:
        raise HTTPException(
            status_code=409,
            detail={"code": "paper_shadow_strategy_required", "message": "Paper/Shadow 啟動需要一份已儲存策略快照。"},
        )

    existing = _current_run_for_profile(db, profile_id)
    now = _utcnow_iso()
    if existing and str(existing.get("state") or "") == "running":
        existing_strategy_name = str(existing.get("strategy_name") or "").strip()
        requested_strategy_name = str((strategy_binding or {}).get("strategy_name") or "").strip()
        if force_paper_shadow and requested_strategy_name and existing_strategy_name != requested_strategy_name:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "profile_run_conflict",
                    "message": f"{profile_id} sleeve 已在執行「{existing_strategy_name or '另一個策略'}」；請先停止該 run 再切換。",
                    "context": {
                        "profile_id": profile_id,
                        "running_strategy_name": existing_strategy_name or None,
                        "requested_strategy_name": requested_strategy_name,
                        "run_id": existing.get("id"),
                    },
                },
            )
        existing_worker = _worker_control_contract(existing, "running")
        existing_worker_healthy = bool(
            _as_dict(existing_worker.get("runtime_liveness")).get("healthy")
        )
        if existing_worker_healthy:
            duplicate_event_type = "start_requested_while_running"
            duplicate_level = "info"
            duplicate_message = "此 run 的長駐 worker 已驗證健康；忽略重複 start。"
            duplicate_result = "noop_already_running"
            duplicate_operator_message = "此 bot run 的長駐 worker 已驗證健康；保留原狀。"
        else:
            duplicate_event_type = "start_requested_without_healthy_worker"
            duplicate_level = "warning"
            duplicate_message = "此 run 僅有 configured running state，未驗證到健康長駐 worker。"
            duplicate_result = "configured_running_without_healthy_worker"
            duplicate_operator_message = "已保留 configured running state；請執行 worker poll 或由 supervisor 重啟長駐 worker。"
        _insert_event(
            db,
            run_id=str(existing.get("id")),
            profile_id=profile_id,
            event_type=duplicate_event_type,
            level=duplicate_level,
            message=duplicate_message,
            payload={"action_result": duplicate_result},
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
                "last_event_type": duplicate_event_type,
                "last_event_message": duplicate_message,
                "last_event_at": now,
                "updated_at": now,
            },
        )
        db.commit()
        return {
            "action": "start",
            "action_result": duplicate_result,
            "operator_message": duplicate_operator_message,
            "snapshot": build_execution_control_plane_snapshot(db, status_payload, overview_payload),
            "run": get_execution_run_detail(db, str(existing.get("id")), status_payload=status_payload),
        }

    if existing and str(existing.get("state") or "") == "paused":
        existing_strategy_name = str(existing.get("strategy_name") or "").strip()
        requested_strategy_name = str((strategy_binding or {}).get("strategy_name") or "").strip()
        if force_paper_shadow and requested_strategy_name and existing_strategy_name != requested_strategy_name:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "profile_run_conflict",
                    "message": f"{profile_id} sleeve 已暫停「{existing_strategy_name or '另一個策略'}」；請先停止該 run 再切換。",
                    "context": {
                        "profile_id": profile_id,
                        "running_strategy_name": existing_strategy_name or None,
                        "requested_strategy_name": requested_strategy_name,
                        "run_id": existing.get("id"),
                    },
                },
            )
        resume_worker_control = _worker_control_contract(existing, "paused")
        resume_worker_control.update(
            {
                "status": "resume_requested_no_backend_worker",
                "state": "running",
                "backend_worker_bound": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "latest_command": "resumed",
                "latest_command_at": now,
                "operator_action": "run 已恢復為 running；但 backend worker 尚未綁定，送單前仍 fail-closed。",
            }
        )
        db.execute(
            text(
                """
                UPDATE execution_runs
                SET state = 'running',
                    stop_time = NULL,
                    stop_reason = NULL,
                    worker_status = :worker_status,
                    worker_control_json = :worker_control_json,
                    last_event_type = :last_event_type,
                    last_event_message = :last_event_message,
                    last_event_at = :last_event_at,
                    updated_at = :updated_at
                WHERE id = :run_id
                """
            ),
            {
                "run_id": existing.get("id"),
                "worker_status": resume_worker_control.get("status"),
                "worker_control_json": _json_dumps(resume_worker_control),
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
            payload={
                "state": "running",
                "runtime_binding_status": RUNTIME_BINDING_STATUS,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "worker_control": resume_worker_control,
            },
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
    run_mode = shadow_mode if shadow_only else profile_row.get("mode")
    runtime_binding_status = SHADOW_RUNTIME_BINDING_STATUS if shadow_only else RUNTIME_BINDING_STATUS
    selected_shadow_strategy_name = str((strategy_binding or {}).get("strategy_name") or "所選策略")
    message = (
        f"「{selected_shadow_strategy_name}」Paper/Shadow 演練已建立；目前只收集決策、事件與 24h outcome，不送單、不加倉。"
        if shadow_only and force_paper_shadow
        else "高信念精選影子觀察已建立；目前只收集即時決策、事件紀錄與同商品共享預覽，不送單、不加倉。"
        if shadow_only
        else "Execution run 已建立；目前是 stateful control-plane beta，尚未綁定真實 per-bot capital / order ledger。"
    )
    event_type = "shadow_started" if shadow_only else "started"
    action_result = "shadow_started" if shadow_only else "started"
    operator_message = (
        f"已把「{selected_shadow_strategy_name}」送入 Paper/Shadow 演練；不送單、不加倉。"
        if shadow_only and force_paper_shadow
        else "高信念精選影子觀察已啟動；不送單、不加倉。"
        if shadow_only
        else "已建立新的 execution run。"
    )
    worker_control = _initial_worker_control(run_id, profile_id, shadow_only=shadow_only)
    bundle_freeze = _freeze_strategy_bundle_for_run(
        strategy_binding,
        profile_id,
        run_id,
        config=config,
        status_payload=status_payload,
    ) if strategy_binding else {
        "status": "missing_strategy_binding",
        "strategy_bundle_summary": None,
        "strategy_bundle_hash": None,
        "strategy_bundle_path": None,
        "strategy_bundle_json": None,
    }
    strategy_binding_snapshot = dict(strategy_binding) if strategy_binding else None
    if strategy_binding_snapshot is not None:
        strategy_binding_snapshot["strategy_bundle"] = bundle_freeze.get("strategy_bundle_summary")
        strategy_binding_snapshot["strategy_bundle_status"] = bundle_freeze.get("status")
        strategy_binding_snapshot["strategy_bundle_hash"] = bundle_freeze.get("strategy_bundle_hash")
        strategy_binding_snapshot["strategy_bundle_path"] = bundle_freeze.get("strategy_bundle_path")
    db.execute(
        text(
            """
            INSERT INTO execution_runs (
                id, profile_id, label, symbol, venue, mode, state, control_mode,
                runtime_binding_status, budget_amount, budget_ratio, capital_currency,
                activation_status, lifecycle_status, start_time, stop_time, stop_reason,
                operator_note, strategy_name, strategy_source, strategy_hash, strategy_snapshot_json,
                strategy_bundle_hash, strategy_bundle_path, strategy_bundle_status,
                worker_status, worker_control_json,
                last_event_type, last_event_message, last_event_at,
                created_at, updated_at
            ) VALUES (
                :id, :profile_id, :label, :symbol, :venue, :mode, :state, :control_mode,
                :runtime_binding_status, :budget_amount, :budget_ratio, :capital_currency,
                :activation_status, :lifecycle_status, :start_time, :stop_time, :stop_reason,
                :operator_note, :strategy_name, :strategy_source, :strategy_hash, :strategy_snapshot_json,
                :strategy_bundle_hash, :strategy_bundle_path, :strategy_bundle_status,
                :worker_status, :worker_control_json,
                :last_event_type, :last_event_message, :last_event_at,
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
            "mode": run_mode,
            "state": "running",
            "control_mode": CONTROL_MODE,
            "runtime_binding_status": runtime_binding_status,
            "budget_amount": profile_row.get("planned_budget_amount"),
            "budget_ratio": profile_row.get("planned_budget_ratio"),
            "capital_currency": currency,
            "activation_status": profile_row.get("activation_status"),
            "lifecycle_status": profile_row.get("lifecycle_status"),
            "start_time": now,
            "stop_time": None,
            "stop_reason": None,
            "operator_note": control_contract.get("upgrade_prerequisite") if shadow_only else CONTROL_PLANE_UPGRADE_PREREQUISITE,
            "strategy_name": strategy_binding.get("strategy_name") if strategy_binding else None,
            "strategy_source": strategy_binding.get("strategy_source") if strategy_binding else None,
            "strategy_hash": strategy_binding.get("strategy_hash") if strategy_binding else None,
            "strategy_snapshot_json": _json_dumps(strategy_binding_snapshot) if strategy_binding_snapshot else None,
            "strategy_bundle_hash": bundle_freeze.get("strategy_bundle_hash"),
            "strategy_bundle_path": bundle_freeze.get("strategy_bundle_path"),
            "strategy_bundle_status": bundle_freeze.get("status"),
            "worker_status": worker_control.get("status"),
            "worker_control_json": _json_dumps(worker_control),
            "last_event_type": event_type,
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
        event_type=event_type,
        level="info",
        message=message,
        payload={
            "state": "running",
            "runtime_binding_status": runtime_binding_status,
            "budget_amount": profile_row.get("planned_budget_amount"),
            "budget_ratio": profile_row.get("planned_budget_ratio"),
            "shadow_only": shadow_only,
            "risk_on_order_enabled": False,
            "order_submission_enabled": False,
            "high_conviction_topk": high_conviction_topk if shadow_only else None,
            "strategy_bundle": bundle_freeze.get("strategy_bundle_summary"),
            "strategy_bundle_status": bundle_freeze.get("status"),
            "worker_control": worker_control,
        },
        created_at=now,
    )
    db.commit()
    return {
        "action": "start",
        "action_result": action_result,
        "operator_message": operator_message,
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
    worker_control = _worker_control_contract(run_row, current_state)
    transition_worker_status = "pause_requested_no_backend_worker" if target_state == "paused" else "stop_requested_no_backend_worker"
    worker_control.update(
        {
            "status": transition_worker_status,
            "state": target_state,
            "backend_worker_bound": False,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "latest_command": event_type,
            "latest_command_at": now,
            "cancel_open_orders_status": "not_bound_to_exchange_adapter" if target_state == "stopped" else "not_requested",
            "operator_action": (
                "run 已暫停；未來 worker 必須 poll 到 paused 並停止新 order proposal。"
                if target_state == "paused"
                else "run 已停止；不會在 control plane 內呼叫 OKX 下單，既有掛單需以 reconciliation / 人工場館確認。"
            ),
        }
    )
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
                worker_status = :worker_status,
                worker_control_json = :worker_control_json,
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
            "worker_status": worker_control.get("status"),
            "worker_control_json": _json_dumps(worker_control),
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
        payload={
            "state": target_state,
            "stop_reason": stop_reason,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "worker_control": worker_control,
        },
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
    run_row = _require_run_row(db, run_id)
    events = _load_run_events(db, [run_id], limit_per_run=20).get(run_id, [])
    return _serialize_run(run_row, events, status_payload=status_payload)
