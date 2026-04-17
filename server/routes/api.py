"""
REST API 路由 v4.0 — 多特徵策略 + 策略實驗室 + 模型排行榜
"""
import ccxt
import math
import json
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

from server.dependencies import (
    get_db,
    get_config,
    get_runtime_status,
    is_automation_enabled,
    set_automation_enabled,
    set_runtime_status,
)
from server.features_engine import get_engine
from database.models import TradeHistory, RawEvent, RawMarketData, FeaturesNormalized, OrderLifecycleEvent
from feature_engine.feature_history_policy import (
    FEATURE_KEY_MAP,
    assess_feature_quality,
    attach_forward_archive_meta,
    compute_raw_snapshot_stats,
    _compute_archive_window_coverage,
)
from execution.account_sync import AccountSyncService
from execution.execution_service import ExecutionService
from execution.metadata_smoke import run_metadata_smoke
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

_KLINE_CACHE_LOCK = threading.Lock()
_KLINE_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}
_STRATEGY_RUN_LOCK = threading.Lock()
_STRATEGY_RUN_JOBS: Dict[str, Dict[str, Any]] = {}
_STRATEGY_RUN_EXECUTOR = ThreadPoolExecutor(max_workers=2)
_BENCHMARK_PROCESS_EXECUTOR = ProcessPoolExecutor(max_workers=1)
_HYBRID_MODEL_LOCK = threading.Lock()
_HYBRID_MODEL_CACHE: Dict[str, Dict[str, Any]] = {}
_EXECUTION_METADATA_SMOKE_PATH = Path(__file__).resolve().parents[2] / "data" / "execution_metadata_smoke.json"
_EXECUTION_METADATA_EXTERNAL_MONITOR_PATH = Path(__file__).resolve().parents[2] / "data" / "execution_metadata_external_monitor.json"
_EXECUTION_METADATA_EXTERNAL_MONITOR_INSTALL_CONTRACT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "execution_metadata_external_monitor_install_contract.json"
)
_Q15_SUPPORT_AUDIT_PATH = Path(__file__).resolve().parents[2] / "data" / "q15_support_audit.json"
_EXECUTION_METADATA_EXTERNAL_MONITOR_COMMAND = (
    f"cd {Path(__file__).resolve().parents[2]} && "
    f"{Path(__file__).resolve().parents[2] / 'venv' / 'bin' / 'python'} "
    "scripts/execution_metadata_external_monitor.py --symbol {symbol}"
)
_EXECUTION_METADATA_SMOKE_STALE_AFTER_MINUTES = 30.0
_EXECUTION_METADATA_EXTERNAL_MONITOR_STALE_AFTER_MINUTES = 15.0
_EXECUTION_METADATA_SMOKE_AUTO_REFRESH_COOLDOWN_SECONDS = 300.0
_EXECUTION_METADATA_SMOKE_REFRESH_LOCK = threading.Lock()
_EXECUTION_METADATA_SMOKE_REFRESH_STATE: Dict[str, Any] = {
    "attempted_at": None,
    "completed_at": None,
    "status": "idle",
    "reason": "not_attempted",
    "next_retry_at": None,
    "error": None,
}
_EXECUTION_METADATA_SMOKE_BACKGROUND_STATE: Dict[str, Any] = {
    "status": "idle",
    "reason": "not_started",
    "checked_at": None,
    "freshness_status": None,
    "governance_status": None,
    "error": None,
    "interval_seconds": 60.0,
}

_STRATEGY_STAGE_LABELS = {
    "queued": "任務排隊",
    "load_data": "讀取本地資料",
    "backfill_raw": "回填原始行情",
    "backfill_features": "補算特徵",
    "backfill_labels": "補算標籤",
    "reload_data": "重新載入資料",
    "prepare_hybrid": "準備 Hybrid 訓練資料",
    "train_model": "訓練模型",
    "run_backtest": "執行回測",
    "postprocess": "整理結果",
    "save_results": "儲存與同步工作區",
}

_INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}

_KLINE_INCREMENTAL_WARMUP_CANDLES = 90


def _interval_ms(interval: str) -> int:
    return _INTERVAL_MS.get(interval, 3_600_000)


def _iso_utc_timestamp(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (datetime, int, float)):
        dt = _parse_utc_datetime(value)
        if dt is not None:
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("T", " ")
    if text.endswith("Z"):
        text = text[:-1]
    if "+" in text:
        text = text.split("+", 1)[0]
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            dt = datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return str(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_result_timestamps(payload: Any) -> Any:
    if isinstance(payload, list):
        return [_normalize_result_timestamps(item) for item in payload]
    if isinstance(payload, dict):
        normalized = dict(payload)
        for key in ("timestamp", "entry_timestamp", "start", "end", "run_at"):
            if key in normalized:
                normalized[key] = _iso_utc_timestamp(normalized.get(key))
        return {k: _normalize_result_timestamps(v) for k, v in normalized.items()}
    return payload


def _build_cache_key(*parts: Any) -> str:
    return "::".join(str(part) for part in parts)


def _strategy_decision_contract_meta(*, horizon_minutes: int = 1440) -> Dict[str, Any]:
    return {
        "target_col": "simulated_pyramid_win",
        "target_label": "Simulated Pyramid Win",
        "sort_semantics": "higher_decision_quality_is_better",
        "decision_quality_horizon_minutes": int(horizon_minutes),
    }


def _compute_decision_profile(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not trades:
        return {
            "avg_entry_quality": None,
            "avg_allowed_layers": 0.0,
            "avg_trade_quality": None,
            "dominant_regime_gate": None,
        }

    entry_quality_vals = [
        float(t["entry_quality"])
        for t in trades
        if t.get("entry_quality") is not None
    ]
    allowed_layers_vals = [
        float(t["allowed_layers"])
        for t in trades
        if t.get("allowed_layers") is not None
    ]
    pnl_vals = [float(t.get("pnl") or 0.0) for t in trades]
    pnl_scale = max(max((abs(v) for v in pnl_vals), default=0.0), 1e-9)
    trade_quality_vals = [0.5 + 0.5 * max(-1.0, min(1.0, pnl / pnl_scale)) for pnl in pnl_vals]

    gate_counts: Dict[str, int] = {}
    for trade in trades:
        gate = trade.get("regime_gate")
        if gate is None:
            continue
        gate_counts[str(gate)] = gate_counts.get(str(gate), 0) + 1
    dominant_regime_gate = None
    if gate_counts:
        dominant_regime_gate = max(gate_counts.items(), key=lambda item: (item[1], item[0]))[0]

    return {
        "avg_entry_quality": None if not entry_quality_vals else round(sum(entry_quality_vals) / len(entry_quality_vals), 4),
        "avg_allowed_layers": round(sum(allowed_layers_vals) / len(allowed_layers_vals), 4) if allowed_layers_vals else 0.0,
        "avg_trade_quality": None if not trade_quality_vals else round(sum(trade_quality_vals) / len(trade_quality_vals), 4),
        "dominant_regime_gate": dominant_regime_gate,
    }



def _compute_strategy_decision_quality_profile(
    trades: List[Dict[str, Any]],
    db=None,
    horizon_minutes: int = 1440,
) -> Dict[str, Any]:
    if not trades:
        return {
            **_strategy_decision_contract_meta(horizon_minutes=horizon_minutes),
            "avg_expected_win_rate": None,
            "avg_expected_pyramid_pnl": None,
            "avg_expected_pyramid_quality": None,
            "avg_expected_drawdown_penalty": None,
            "avg_expected_time_underwater": None,
            "avg_decision_quality_score": None,
            "decision_quality_label": None,
            "decision_quality_sample_size": 0,
        }

    pnl_vals = [float(t.get("pnl") or 0.0) for t in trades]
    wins = [1.0 if pnl > 0 else 0.0 for pnl in pnl_vals]
    abs_pnls = [abs(v) for v in pnl_vals]
    pnl_scale = max(max(abs_pnls, default=0.0), 1e-9)
    positive_scale = max(max((v for v in pnl_vals if v > 0), default=0.0), 1e-9)
    negative_scale = max(max((abs(v) for v in pnl_vals if v < 0), default=0.0), 1e-9)

    expected_win_rate = sum(wins) / len(wins)
    expected_pyramid_pnl = sum(pnl_vals) / len(pnl_vals)
    expected_pyramid_quality = sum(max(-1.0, min(1.0, pnl / pnl_scale)) for pnl in pnl_vals) / len(pnl_vals)
    drawdown_penalties = [
        0.0 if pnl >= 0 else min(abs(pnl) / negative_scale, 1.0)
        for pnl in pnl_vals
    ]
    time_underwater = [
        max(0.0, min(1.0, 1.0 - float(t.get("entry_quality") or 0.0)))
        for t in trades
    ]
    decision_quality_score = (
        expected_win_rate * 0.45
        + max(min(expected_pyramid_quality, 1.0), -1.0) * 0.25
        + max(min(expected_pyramid_pnl / positive_scale, 1.0), -1.0) * 0.15
        - (sum(drawdown_penalties) / len(drawdown_penalties)) * 0.10
        - (sum(time_underwater) / len(time_underwater)) * 0.05
    )

    if decision_quality_score >= 0.65:
        quality_label = "A"
    elif decision_quality_score >= 0.50:
        quality_label = "B"
    elif decision_quality_score >= 0.35:
        quality_label = "C"
    else:
        quality_label = "D"

    return {
        **_strategy_decision_contract_meta(horizon_minutes=horizon_minutes),
        "avg_expected_win_rate": round(expected_win_rate, 4),
        "avg_expected_pyramid_pnl": round(expected_pyramid_pnl, 4),
        "avg_expected_pyramid_quality": round(expected_pyramid_quality, 4),
        "avg_expected_drawdown_penalty": round(sum(drawdown_penalties) / len(drawdown_penalties), 4),
        "avg_expected_time_underwater": round(sum(time_underwater) / len(time_underwater), 4),
        "avg_decision_quality_score": round(decision_quality_score, 4),
        "decision_quality_label": quality_label,
        "decision_quality_sample_size": len(trades),
    }


def _parse_utc_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        raw = float(value)
        if not math.isfinite(raw):
            return None
        if abs(raw) >= 1_000_000_000_000:
            raw = raw / 1000.0
        try:
            dt = datetime.fromtimestamp(raw, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)



def _build_execution_metadata_smoke_freshness(
    generated_at: Any,
    *,
    stale_after_minutes: float = _EXECUTION_METADATA_SMOKE_STALE_AFTER_MINUTES,
) -> Dict[str, Any]:
    freshness = {
        "status": "unavailable",
        "label": "unavailable",
        "reason": "artifact_missing",
        "age_minutes": None,
        "stale_after_minutes": stale_after_minutes,
    }
    dt = _parse_utc_datetime(generated_at)
    if not dt:
        if generated_at:
            freshness["reason"] = "invalid_generated_at"
        return freshness
    age_minutes = max((datetime.now(timezone.utc) - dt).total_seconds() / 60.0, 0.0)
    status = "fresh" if age_minutes <= stale_after_minutes else "stale"
    freshness.update({
        "status": status,
        "label": status,
        "reason": "artifact_within_policy" if status == "fresh" else "artifact_older_than_policy",
        "age_minutes": age_minutes,
        "stale_after_minutes": stale_after_minutes,
    })
    return freshness

def _load_execution_metadata_smoke_summary() -> Optional[Dict[str, Any]]:
    if not _EXECUTION_METADATA_SMOKE_PATH.exists():
        return None
    try:
        payload = json.loads(_EXECUTION_METADATA_SMOKE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "available": False,
            "artifact_path": str(_EXECUTION_METADATA_SMOKE_PATH),
            "error": str(exc),
            "freshness": {
                "status": "unavailable",
                "label": "unavailable",
                "reason": "artifact_parse_failed",
                "age_minutes": None,
                "stale_after_minutes": _EXECUTION_METADATA_SMOKE_STALE_AFTER_MINUTES,
            },
        }

    results = payload.get("results") if isinstance(payload, dict) else {}
    if not isinstance(results, dict):
        results = {}

    venues = []
    for venue, item in results.items():
        item = item if isinstance(item, dict) else {}
        contract = item.get("contract") if isinstance(item.get("contract"), dict) else {}
        venues.append({
            "venue": venue,
            "ok": bool(item.get("ok")),
            "enabled_in_config": bool(item.get("enabled_in_config")),
            "credentials_configured": bool(item.get("credentials_configured")),
            "error": item.get("error"),
            "contract": {
                "symbol": contract.get("symbol"),
                "min_qty": contract.get("min_qty"),
                "min_cost": contract.get("min_cost"),
                "step_size": contract.get("step_size"),
                "tick_size": contract.get("tick_size"),
                "qty_contract": contract.get("qty_contract") or {},
                "price_contract": contract.get("price_contract") or {},
            },
        })

    generated_at = payload.get("generated_at")
    return {
        "available": True,
        "artifact_path": str(_EXECUTION_METADATA_SMOKE_PATH),
        "generated_at": generated_at,
        "symbol": payload.get("symbol"),
        "all_ok": bool(payload.get("all_ok")),
        "ok_count": payload.get("ok_count"),
        "venues_checked": payload.get("venues_checked"),
        "freshness": _build_execution_metadata_smoke_freshness(generated_at),
        "venues": venues,
    }


def _load_q15_support_audit_summary(current_structure_bucket: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not _Q15_SUPPORT_AUDIT_PATH.exists():
        return None
    try:
        payload = json.loads(_Q15_SUPPORT_AUDIT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    applicability = payload.get("scope_applicability") if isinstance(payload.get("scope_applicability"), dict) else {}
    current_live = payload.get("current_live") if isinstance(payload.get("current_live"), dict) else {}
    support_route = payload.get("support_route") if isinstance(payload.get("support_route"), dict) else {}
    floor_cross = payload.get("floor_cross_legality") if isinstance(payload.get("floor_cross_legality"), dict) else {}
    component_experiment = payload.get("component_experiment") if isinstance(payload.get("component_experiment"), dict) else {}
    support_progress = support_route.get("support_progress") if isinstance(support_route.get("support_progress"), dict) else {}

    active_for_current_live_row = bool(applicability.get("active_for_current_live_row"))
    audit_bucket = (
        applicability.get("current_structure_bucket")
        or current_live.get("current_live_structure_bucket")
        or current_live.get("structure_bucket")
    )
    if current_structure_bucket and audit_bucket and str(current_structure_bucket) != str(audit_bucket):
        return None
    if current_structure_bucket and "q15" not in str(current_structure_bucket):
        return None
    if audit_bucket and "q15" not in str(audit_bucket):
        return None
    if not active_for_current_live_row:
        return None

    return {
        "generated_at": payload.get("generated_at"),
        "current_structure_bucket": audit_bucket,
        "scope_applicability": applicability,
        "support_route_verdict": support_route.get("verdict"),
        "support_route_deployable": support_route.get("deployable"),
        "support_governance_route": support_route.get("support_governance_route"),
        "minimum_support_rows": support_route.get("minimum_support_rows"),
        "current_live_structure_bucket_gap_to_minimum": support_route.get("current_live_structure_bucket_gap_to_minimum"),
        "support_progress": support_progress,
        "floor_cross_legality": floor_cross,
        "component_experiment": component_experiment,
        "current_live": current_live,
    }


def _enrich_confidence_with_q15_support_audit(result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return result

    blocker = str(result.get("deployment_blocker") or "")
    if blocker not in {
        "under_minimum_exact_live_structure_bucket",
        "unsupported_exact_live_structure_bucket",
    }:
        return result

    blocker_details = result.get("deployment_blocker_details") if isinstance(result.get("deployment_blocker_details"), dict) else {}
    scope_diagnostics = result.get("decision_quality_scope_diagnostics") if isinstance(result.get("decision_quality_scope_diagnostics"), dict) else {}
    exact_scope = scope_diagnostics.get("regime_label+regime_gate+entry_quality_label") if isinstance(scope_diagnostics.get("regime_label+regime_gate+entry_quality_label"), dict) else {}
    current_structure_bucket = (
        result.get("current_live_structure_bucket")
        or result.get("decision_quality_live_structure_bucket")
        or blocker_details.get("current_live_structure_bucket")
        or result.get("structure_bucket")
        or exact_scope.get("current_live_structure_bucket")
    )
    audit_summary = _load_q15_support_audit_summary(str(current_structure_bucket) if current_structure_bucket is not None else None)
    if not audit_summary:
        return result

    enriched = dict(result)
    support_progress = audit_summary.get("support_progress") if isinstance(audit_summary.get("support_progress"), dict) else {}
    floor_cross = audit_summary.get("floor_cross_legality") if isinstance(audit_summary.get("floor_cross_legality"), dict) else {}
    component_experiment = audit_summary.get("component_experiment") if isinstance(audit_summary.get("component_experiment"), dict) else {}

    details = dict(blocker_details)
    if support_progress:
        details.setdefault("support_progress", support_progress)
        details.setdefault("current_live_structure_bucket_rows", support_progress.get("current_rows"))
        details.setdefault("minimum_support_rows", support_progress.get("minimum_support_rows"))
        details.setdefault("current_live_structure_bucket_gap_to_minimum", support_progress.get("gap_to_minimum"))
    if floor_cross:
        details.setdefault("floor_cross_legality", floor_cross)
    if component_experiment:
        details.setdefault("component_experiment", component_experiment)

    enriched["deployment_blocker_details"] = details
    enriched["q15_support_audit"] = audit_summary
    enriched["support_progress"] = support_progress or enriched.get("support_progress")
    enriched["support_route_verdict"] = audit_summary.get("support_route_verdict")
    enriched["support_route_deployable"] = audit_summary.get("support_route_deployable")
    enriched["support_governance_route"] = audit_summary.get("support_governance_route")
    enriched["minimum_support_rows"] = audit_summary.get("minimum_support_rows")
    enriched["current_live_structure_bucket_gap_to_minimum"] = audit_summary.get("current_live_structure_bucket_gap_to_minimum")
    enriched["floor_cross_verdict"] = floor_cross.get("verdict")
    enriched["legal_to_relax_runtime_gate"] = floor_cross.get("legal_to_relax_runtime_gate")
    enriched["remaining_gap_to_floor"] = floor_cross.get("remaining_gap_to_floor")
    enriched["best_single_component"] = floor_cross.get("best_single_component")
    enriched["best_single_component_required_score_delta"] = floor_cross.get("best_single_component_required_score_delta")
    enriched["component_experiment_verdict"] = component_experiment.get("verdict")
    return enriched


def _load_execution_metadata_external_monitor_install_contract() -> Optional[Dict[str, Any]]:
    if not _EXECUTION_METADATA_EXTERNAL_MONITOR_INSTALL_CONTRACT_PATH.exists():
        return None
    try:
        payload = json.loads(
            _EXECUTION_METADATA_EXTERNAL_MONITOR_INSTALL_CONTRACT_PATH.read_text(encoding="utf-8")
        )
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _build_execution_metadata_external_monitor_ticking_state(
    install_contract: Optional[Dict[str, Any]],
    freshness: Dict[str, Any],
    checked_at: Optional[str],
) -> Dict[str, Any]:
    install_status = install_contract.get("install_status") if isinstance(install_contract, dict) else None
    installed = bool((install_status or {}).get("installed"))
    active_lane = (install_status or {}).get("active_lane")
    freshness_status = freshness.get("status")
    age_minutes = freshness.get("age_minutes")
    stale_after_minutes = freshness.get("stale_after_minutes")

    if not installed:
        status = "install-ready"
        reason = "host_scheduler_not_installed"
        message = "host scheduler 尚未安裝；目前只有 install-ready contract，還沒有 observed ticking 證據。"
    elif freshness_status == "fresh":
        status = "observed-ticking"
        reason = "installed_and_fresh"
        message = "host scheduler 已安裝，且 external monitor artifact 在 freshness policy 內，已觀察到自然 ticking。"
    elif checked_at:
        status = "installed-but-not-ticking"
        reason = "installed_but_artifact_not_fresh"
        message = "host scheduler 已安裝，但 external monitor artifact 未維持 fresh；需視為 installed-but-not-ticking。"
    else:
        status = "installed"
        reason = "installed_waiting_for_first_observation"
        message = "host scheduler 已安裝，但尚未觀察到第一個 external monitor tick。"

    return {
        "status": status,
        "reason": reason,
        "message": message,
        "installed": installed,
        "active_lane": active_lane,
        "checked_at": checked_at,
        "freshness_status": freshness_status,
        "age_minutes": age_minutes,
        "stale_after_minutes": stale_after_minutes,
    }


def _load_execution_metadata_external_monitor_state(symbol: str = "BTCUSDT") -> Dict[str, Any]:
    install_contract = _load_execution_metadata_external_monitor_install_contract()
    base_freshness = {
        "status": "unavailable",
        "label": "unavailable",
        "reason": "artifact_missing",
        "age_minutes": None,
        "stale_after_minutes": _EXECUTION_METADATA_EXTERNAL_MONITOR_STALE_AFTER_MINUTES,
    }
    base = {
        "available": False,
        "artifact_path": str(_EXECUTION_METADATA_EXTERNAL_MONITOR_PATH),
        "source": "external_process",
        "status": "unavailable",
        "reason": "artifact_missing",
        "checked_at": None,
        "freshness_status": None,
        "governance_status": None,
        "error": None,
        "interval_seconds": None,
        "command": _EXECUTION_METADATA_EXTERNAL_MONITOR_COMMAND.format(symbol=symbol),
        "install_contract": install_contract,
        "freshness": base_freshness,
        "ticking_state": _build_execution_metadata_external_monitor_ticking_state(
            install_contract,
            base_freshness,
            None,
        ),
    }
    if not _EXECUTION_METADATA_EXTERNAL_MONITOR_PATH.exists():
        return base
    try:
        payload = json.loads(_EXECUTION_METADATA_EXTERNAL_MONITOR_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            **base,
            "reason": "artifact_parse_failed",
            "error": "external monitor artifact parse failed",
            "freshness": {
                "status": "unavailable",
                "label": "unavailable",
                "reason": "artifact_parse_failed",
                "age_minutes": None,
                "stale_after_minutes": _EXECUTION_METADATA_EXTERNAL_MONITOR_STALE_AFTER_MINUTES,
            },
            "ticking_state": _build_execution_metadata_external_monitor_ticking_state(
                install_contract,
                {
                    "status": "unavailable",
                    "label": "unavailable",
                    "reason": "artifact_parse_failed",
                    "age_minutes": None,
                    "stale_after_minutes": _EXECUTION_METADATA_EXTERNAL_MONITOR_STALE_AFTER_MINUTES,
                },
                None,
            ),
        }

    checked_at = payload.get("checked_at") or payload.get("generated_at")
    interval_seconds = payload.get("interval_seconds")
    stale_after_minutes = _EXECUTION_METADATA_EXTERNAL_MONITOR_STALE_AFTER_MINUTES
    if isinstance(interval_seconds, (int, float)) and interval_seconds > 0:
        stale_after_minutes = max(interval_seconds / 60.0 * 3.0, stale_after_minutes)
    freshness = _build_execution_metadata_smoke_freshness(
        checked_at,
        stale_after_minutes=stale_after_minutes,
    )
    payload_install_contract = payload.get("install_contract") if isinstance(payload.get("install_contract"), dict) else None
    resolved_install_contract = payload_install_contract or install_contract
    return {
        **base,
        "available": True,
        "source": str(payload.get("source") or "external_process"),
        "status": str(payload.get("status") or "unknown"),
        "reason": str(payload.get("reason") or "external_monitor_tick"),
        "checked_at": checked_at,
        "freshness_status": payload.get("freshness_status"),
        "governance_status": payload.get("governance_status"),
        "error": payload.get("error"),
        "interval_seconds": interval_seconds,
        "command": payload.get("command") or base["command"],
        "install_contract": resolved_install_contract,
        "freshness": freshness,
        "ticking_state": _build_execution_metadata_external_monitor_ticking_state(
            resolved_install_contract,
            freshness,
            checked_at,
        ),
    }


def _build_execution_metadata_smoke_refresh_state() -> Dict[str, Any]:
    return {
        "attempted_at": _EXECUTION_METADATA_SMOKE_REFRESH_STATE.get("attempted_at"),
        "completed_at": _EXECUTION_METADATA_SMOKE_REFRESH_STATE.get("completed_at"),
        "status": _EXECUTION_METADATA_SMOKE_REFRESH_STATE.get("status", "idle"),
        "reason": _EXECUTION_METADATA_SMOKE_REFRESH_STATE.get("reason", "not_attempted"),
        "next_retry_at": _EXECUTION_METADATA_SMOKE_REFRESH_STATE.get("next_retry_at"),
        "error": _EXECUTION_METADATA_SMOKE_REFRESH_STATE.get("error"),
        "cooldown_seconds": _EXECUTION_METADATA_SMOKE_AUTO_REFRESH_COOLDOWN_SECONDS,
    }


def _build_execution_metadata_smoke_background_state() -> Dict[str, Any]:
    return {
        "status": _EXECUTION_METADATA_SMOKE_BACKGROUND_STATE.get("status", "idle"),
        "reason": _EXECUTION_METADATA_SMOKE_BACKGROUND_STATE.get("reason", "not_started"),
        "checked_at": _EXECUTION_METADATA_SMOKE_BACKGROUND_STATE.get("checked_at"),
        "freshness_status": _EXECUTION_METADATA_SMOKE_BACKGROUND_STATE.get("freshness_status"),
        "governance_status": _EXECUTION_METADATA_SMOKE_BACKGROUND_STATE.get("governance_status"),
        "error": _EXECUTION_METADATA_SMOKE_BACKGROUND_STATE.get("error"),
        "interval_seconds": _EXECUTION_METADATA_SMOKE_BACKGROUND_STATE.get("interval_seconds", 60.0),
    }


def _build_execution_surface_contract() -> Dict[str, Any]:
    return {
        "canonical_execution_route": "dashboard",
        "canonical_surface_label": "Dashboard / Execution 狀態面板",
        "shortcut_surface": {
            "name": "signal_banner",
            "role": "shortcut-only",
            "status": "not-upgraded",
            "message": "SignalBanner 目前只提供快捷下單 / 自動交易切換；完整 Execution 狀態、Guardrail context 與 stale governance 必須回 Dashboard 檢查。",
            "upgrade_prerequisite": "必須先完整消費 /api/status 的 ticking_state、stale governance、guardrail context，才能升級第二 execution route。",
        },
        "readiness_scope": "runtime_governance_visibility_only",
        "live_ready": False,
        "live_ready_blockers": [
            "live exchange credential 尚未驗證",
            "order ack lifecycle 尚未驗證",
            "fill lifecycle 尚未驗證",
        ],
        "operator_message": "目前完成的是 execution governance / visibility closure，不是 live 或 canary readiness。",
    }


def _build_live_runtime_closure_surface(confidence_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = confidence_payload or {}
    patch_active = bool(payload.get("q15_exact_supported_component_patch_applied"))
    signal = str(payload.get("signal") or "—")
    allowed_layers = payload.get("allowed_layers")
    support_progress = payload.get("support_progress") if isinstance(payload.get("support_progress"), dict) else {}
    current_rows = support_progress.get("current_rows")
    minimum_rows = support_progress.get("minimum_support_rows")
    scope_diagnostics = payload.get("decision_quality_scope_diagnostics") if isinstance(payload.get("decision_quality_scope_diagnostics"), dict) else {}
    exact_scope = scope_diagnostics.get("regime_label+regime_gate+entry_quality_label") if isinstance(scope_diagnostics.get("regime_label+regime_gate+entry_quality_label"), dict) else {}
    calibration_exact_lane_rows = exact_scope.get("current_live_structure_bucket_rows")
    calibration_exact_lane_alerts = exact_scope.get("alerts") if isinstance(exact_scope.get("alerts"), list) else []

    support_alignment_status = "unavailable"
    support_alignment_summary = "尚未取得 exact live lane calibration 對照。"
    if current_rows is not None and calibration_exact_lane_rows is not None:
        if int(current_rows) > 0 and int(calibration_exact_lane_rows) == 0:
            support_alignment_status = "runtime_ahead_of_calibration"
            support_alignment_summary = (
                f"runtime 已有 {int(current_rows)} 筆 exact support，但 calibration exact lane 仍是 0 筆；"
                "目前 deployment capacity 應以 q15 support audit / runtime exact-support closure 為準，"
                "不能把 calibration 0 rows 誤讀成 runtime 未支援。"
            )
        elif int(current_rows) == int(calibration_exact_lane_rows):
            support_alignment_status = "aligned"
            support_alignment_summary = (
                f"runtime exact support 與 calibration exact lane 已對齊（{int(current_rows)} 筆）。"
            )
        elif int(current_rows) > int(calibration_exact_lane_rows):
            support_alignment_status = "runtime_above_calibration"
            support_alignment_summary = (
                f"runtime exact support={int(current_rows)}，高於 calibration exact lane={int(calibration_exact_lane_rows)}；"
                "operator 應優先確認 label replay / calibration artifact 是否落後。"
            )
        else:
            support_alignment_status = "calibration_above_runtime"
            support_alignment_summary = (
                f"calibration exact lane={int(calibration_exact_lane_rows)}，高於 runtime exact support={int(current_rows)}；"
                "需檢查 runtime current-live row / support bucket 是否切換。"
            )

    if signal == "CIRCUIT_BREAKER":
        runtime_closure_state = "circuit_breaker_active"
        runtime_closure_summary = (
            "canonical live path 目前由 circuit breaker 擋下；"
            f"{payload.get('reason') or '需檢查 recent 50 win rate / streak'}。"
            "release condition = streak < 50 且 recent 50 win rate >= 30%。"
        )
    elif patch_active and signal == "HOLD" and (allowed_layers or 0) > 0:
        runtime_closure_state = "capacity_opened_signal_hold"
        runtime_closure_summary = "q15 patch active，runtime 已開出 1 層 deployment capacity，但 signal 仍是 HOLD；這不是 patch missing，也不是自動 BUY readiness。"
    elif patch_active:
        runtime_closure_state = "patch_active"
        runtime_closure_summary = "q15 patch active，但當前 runtime 狀態不屬於 capacity_opened_signal_hold。"
    else:
        runtime_closure_state = "patch_inactive_or_blocked"
        runtime_closure_summary = "q15 patch 尚未 active 或目前仍被其他條件阻擋。"
    return {
        "runtime_closure_state": runtime_closure_state,
        "runtime_closure_summary": runtime_closure_summary,
        "signal": signal,
        "confidence": payload.get("confidence"),
        "entry_quality": payload.get("entry_quality"),
        "entry_quality_label": payload.get("entry_quality_label"),
        "allowed_layers": allowed_layers,
        "allowed_layers_reason": payload.get("allowed_layers_reason"),
        "allowed_layers_raw": payload.get("allowed_layers_raw"),
        "allowed_layers_raw_reason": payload.get("allowed_layers_raw_reason"),
        "execution_guardrail_applied": payload.get("execution_guardrail_applied"),
        "execution_guardrail_reason": payload.get("execution_guardrail_reason"),
        "deployment_blocker": payload.get("deployment_blocker"),
        "deployment_blocker_reason": payload.get("deployment_blocker_reason"),
        "deployment_blocker_source": payload.get("deployment_blocker_source"),
        "deployment_blocker_details": payload.get("deployment_blocker_details"),
        "q15_exact_supported_component_patch_applied": patch_active,
        "support_route_verdict": payload.get("support_route_verdict"),
        "support_progress": support_progress or None,
        "support_rows_text": f"{current_rows} / {minimum_rows}" if current_rows is not None and minimum_rows is not None else None,
        "runtime_exact_support_rows": current_rows,
        "calibration_exact_lane_rows": calibration_exact_lane_rows,
        "calibration_exact_lane_alerts": calibration_exact_lane_alerts,
        "support_alignment_status": support_alignment_status,
        "support_alignment_summary": support_alignment_summary,
    }


def _record_value(record: Any, *keys: str) -> Any:
    current = record
    for key in keys:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
    return current


def _record_text(record: Any, *keys: str) -> Optional[str]:
    value = _record_value(record, *keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_symbol_scope(symbol: str) -> str:
    value = str(symbol or "").strip()
    if not value or "/" in value:
        return value
    for quote in ("USDT", "USDC", "BUSD", "BTC", "ETH"):
        if value.endswith(quote) and len(value) > len(quote):
            return f"{value[:-len(quote)]}/{quote}"
    return value


def _extract_runtime_order_ids(order: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(order, dict):
        return []
    ids: List[str] = []
    for key in ("order_id", "client_order_id"):
        value = order.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                ids.append(text)
    return ids


def _extract_account_order_ids(order: Any) -> List[str]:
    ids: List[str] = []
    for key_path in (("id",), ("orderId",), ("ordId",), ("clientOrderId",), ("client_order_id",), ("info", "orderId"), ("info", "clientOrderId"), ("info", "clOrdId")):
        value = _record_text(order, *key_path)
        if value:
            ids.append(value)
    return ids


def _latest_trade_history_row(db) -> Optional[TradeHistory]:
    if db is None:
        return None
    try:
        return db.query(TradeHistory).order_by(TradeHistory.timestamp.desc()).first()
    except Exception:
        return None


def _latest_order_lifecycle_events(
    db,
    *,
    last_order: Optional[Dict[str, Any]],
    latest_trade: Optional[TradeHistory],
    limit: int = 8,
) -> List[OrderLifecycleEvent]:
    if db is None:
        return []
    order_ids = set(_extract_runtime_order_ids(last_order))
    if latest_trade is not None:
        for value in (getattr(latest_trade, "order_id", None), getattr(latest_trade, "client_order_id", None)):
            if value is not None and str(value).strip():
                order_ids.add(str(value).strip())
    if not order_ids:
        return []
    try:
        query = db.query(OrderLifecycleEvent).order_by(OrderLifecycleEvent.timestamp.desc())
        events = query.all()
    except Exception:
        return []
    matched: List[OrderLifecycleEvent] = []
    for event in events:
        event_ids = {
            value.strip()
            for value in [getattr(event, "order_id", None), getattr(event, "client_order_id", None)]
            if isinstance(value, str) and value.strip()
        }
        if event_ids.intersection(order_ids):
            matched.append(event)
    matched.sort(key=lambda event: _parse_utc_datetime(getattr(event, "timestamp", None)) or datetime.min.replace(tzinfo=timezone.utc))
    if limit > 0:
        matched = matched[-limit:]
    return matched


def _parse_lifecycle_payload(payload_json: Any) -> Optional[Dict[str, Any]]:
    text = str(payload_json or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _normalize_order_state(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not text:
        return "unknown"
    aliases = {
        "partiallyfilled": "partially_filled",
        "partialfilled": "partially_filled",
        "partial_fill": "partially_filled",
        "partially_filled": "partially_filled",
        "new": "open",
        "filled": "closed",
        "cancelled": "canceled",
    }
    return aliases.get(text, text)


def _build_execution_lifecycle_audit(
    *,
    account_degraded: bool,
    freshness_status: str,
    last_order: Optional[Dict[str, Any]],
    latest_trade: Optional[TradeHistory],
    trade_alignment_status: str,
    open_order_alignment_status: str,
    matched_account_order: Optional[Any],
) -> Dict[str, Any]:
    runtime_state = _normalize_order_state(_record_text(last_order, "status")) if last_order else "absent"
    trade_state = _normalize_order_state(getattr(latest_trade, "order_status", None)) if latest_trade is not None else "absent"
    matched_open_order_state = _normalize_order_state(_record_text(matched_account_order, "status") or _record_text(matched_account_order, "state")) if matched_account_order is not None else "absent"
    runtime_timestamp = _iso_utc_timestamp(_record_value(last_order, "timestamp")) if last_order else None
    trade_timestamp = _iso_utc_timestamp(getattr(latest_trade, "timestamp", None)) if latest_trade is not None else None

    if account_degraded:
        stage = "snapshot_degraded"
        reason = "account_snapshot_degraded_blocks_lifecycle_replay"
        restart_replay_required = True
        recovery_status = "degraded"
        operator_action = "先修復 account snapshot / venue 連線，再重新對帳 open orders、positions 與最新委託狀態。"
    elif last_order is None:
        stage = "no_runtime_order"
        reason = "runtime_has_not_recorded_an_order_yet"
        restart_replay_required = False
        recovery_status = "idle"
        operator_action = "目前尚無 runtime order 需要 replay；若預期已有委託，先檢查 execution service 是否真的送出單。"
    elif freshness_status != "fresh":
        stage = "snapshot_refresh_required"
        reason = "account_snapshot_not_fresh_enough_for_restart_replay"
        restart_replay_required = True
        recovery_status = "needs_snapshot_refresh"
        operator_action = "先刷新 account snapshot，再確認 open orders / positions / trade history 是否與 runtime last order 一致。"
    elif runtime_state in {"open", "partially_filled"}:
        if open_order_alignment_status == "matched" and trade_alignment_status in {"matched", "symbol_only_match"}:
            stage = "open_reconciled"
            reason = "runtime_open_order_is_visible_in_account_snapshot_and_trade_history"
            restart_replay_required = False
            recovery_status = "ready"
            operator_action = "目前 open order 已可對帳；若發生重啟，可依 order_id / client_order_id 重放 venue open orders。"
        elif open_order_alignment_status == "matched":
            stage = "open_missing_trade_history"
            reason = "account_snapshot_can_see_open_order_but_trade_history_is_missing_or_mismatched"
            restart_replay_required = True
            recovery_status = "needs_trade_history_replay"
            operator_action = "open order 還在，但 trade_history 缺 replay；需補寫 ack/open audit trail。"
        else:
            stage = "open_missing_from_snapshot"
            reason = "runtime_last_order_is_open_but_snapshot_cannot_replay_it"
            restart_replay_required = True
            recovery_status = "needs_open_order_replay"
            operator_action = "runtime 顯示仍有 open order，但 snapshot 沒看到；需重新抓 venue open orders 並驗證 restart replay。"
    elif runtime_state in {"closed", "canceled", "rejected", "expired"}:
        if trade_alignment_status in {"matched", "symbol_only_match"}:
            stage = "terminal_reconciled"
            reason = "terminal_order_is_persisted_in_trade_history"
            restart_replay_required = False
            recovery_status = "ready"
            operator_action = "terminal lifecycle 已落地；下一步應補 partial fill / cancel 細節與 restart replay 證據。"
        else:
            stage = "terminal_missing_trade_history"
            reason = "runtime_terminal_order_missing_trade_history_replay"
            restart_replay_required = True
            recovery_status = "needs_trade_history_replay"
            operator_action = "runtime 已進 terminal state，但 trade_history 沒對上；需補寫 fill/cancel replay artifact。"
    else:
        stage = "runtime_state_unknown"
        reason = "runtime_last_order_state_not_classified"
        restart_replay_required = True
        recovery_status = "manual_review"
        operator_action = "runtime last order 狀態未知；需人工檢查 exchange 回傳 payload 與 lifecycle mapping。"

    return {
        "stage": stage,
        "reason": reason,
        "runtime_state": runtime_state,
        "trade_history_state": trade_state,
        "matched_open_order_state": matched_open_order_state,
        "restart_replay_required": restart_replay_required,
        "recovery_status": recovery_status,
        "operator_action": operator_action,
        "evidence": {
            "runtime_order_timestamp": runtime_timestamp,
            "trade_history_timestamp": trade_timestamp,
            "trade_alignment_status": trade_alignment_status,
            "open_order_alignment_status": open_order_alignment_status,
        },
    }


def _build_execution_recovery_state(
    *,
    lifecycle_audit: Dict[str, Any],
    account_degraded: bool,
    freshness_status: str,
    trade_alignment_status: str,
    open_order_alignment_status: str,
) -> Dict[str, Any]:
    if account_degraded:
        status = "degraded"
        reason = "account_snapshot_degraded"
        summary = "account snapshot 退化；目前不能把 execution surface 視為可 replay 真相。"
    elif freshness_status != "fresh":
        status = "needs_snapshot_refresh"
        reason = "account_snapshot_not_fresh"
        summary = "snapshot 不夠新，restart reconciliation 仍缺少可驗證基礎。"
    elif lifecycle_audit.get("recovery_status") == "idle":
        status = "idle"
        reason = "no_runtime_order_to_replay"
        summary = "目前沒有可回放的 runtime order；若預期已有委託，需先確認 execution lane 是否真的送單。"
    elif lifecycle_audit.get("recovery_status") == "needs_open_order_replay":
        status = "needs_open_order_replay"
        reason = "runtime_open_order_missing_from_snapshot"
        summary = "runtime 顯示尚有 open order，但 account snapshot 無法重播它。"
    elif lifecycle_audit.get("recovery_status") == "needs_trade_history_replay":
        status = "needs_trade_history_replay"
        reason = "trade_history_not_persisted"
        summary = "最新 order lifecycle 尚未完整落到 trade_history，重啟後無法證明已可回放。"
    elif trade_alignment_status in {"matched", "symbol_only_match"} and open_order_alignment_status in {"matched", "not_open", "not_applicable"}:
        status = "ready_for_next_audit"
        reason = "summary_reconciliation_healthy"
        summary = "summary-level reconciliation 已對上；下一步應補 partial fill / cancel / restart replay artifact。"
    else:
        status = "manual_review"
        reason = "reconciliation_signals_mixed"
        summary = "reconciliation 訊號混雜，需人工檢查 lifecycle mapping 與 recovery lane。"

    return {
        "status": status,
        "reason": reason,
        "summary": summary,
        "operator_action": lifecycle_audit.get("operator_action"),
        "restart_replay_required": bool(lifecycle_audit.get("restart_replay_required")),
    }


def _build_execution_lifecycle_contract(
    *,
    lifecycle_events: List[OrderLifecycleEvent],
    lifecycle_audit: Dict[str, Any],
    last_order: Optional[Dict[str, Any]],
    latest_trade: Optional[TradeHistory],
) -> Dict[str, Any]:
    runtime_state = str(lifecycle_audit.get("runtime_state") or "absent")

    def _event_evidence(event: Optional[OrderLifecycleEvent]) -> Optional[Dict[str, Any]]:
        if event is None:
            return None
        return {
            "timestamp": _iso_utc_timestamp(getattr(event, "timestamp", None)),
            "event_type": getattr(event, "event_type", None),
            "order_state": getattr(event, "order_state", None),
            "source": getattr(event, "source", None),
            "summary": getattr(event, "summary", None),
        }

    if not lifecycle_events and last_order is None and latest_trade is None:
        return {
            "status": "absent",
            "summary": "尚未觀察到可供 replay 的 lifecycle artifact。",
            "event_type_counts": {},
            "event_types_seen": [],
            "required_event_types": [],
            "missing_event_types": [],
            "replay_key_ready": False,
            "replay_readiness": "not_applicable",
            "replay_readiness_reason": "no_runtime_order",
            "replay_verdict": "no_runtime_order",
            "replay_verdict_reason": "no_runtime_order",
            "replay_verdict_summary": "目前沒有可供 restart replay 的 runtime order。",
            "baseline_contract_status": "not_applicable",
            "partial_fill_observed": False,
            "cancel_observed": False,
            "terminal_state_observed": False,
            "artifact_coverage": "not_applicable",
            "operator_next_artifact": "capture_first_runtime_order",
            "artifact_checklist_summary": "尚未建立任何 runtime order artifact；先捕捉第一筆 order lifecycle。",
            "artifact_checklist": [
                {
                    "key": "capture_first_runtime_order",
                    "label": "Capture first runtime order",
                    "status": "not_applicable",
                    "required": True,
                    "observed": False,
                    "count": 0,
                    "summary": "目前沒有 runtime order，因此無法建立 validation / replay checklist。",
                    "evidence": None,
                },
                {
                    "key": "restart_replay",
                    "label": "Restart replay evidence",
                    "status": "not_applicable",
                    "required": False,
                    "observed": False,
                    "count": 0,
                    "summary": "先有 runtime order 與 replay key，才能評估 restart replay readiness。",
                    "evidence": None,
                },
            ],
        }

    event_type_counts: Dict[str, int] = {}
    event_types_seen: List[str] = []
    latest_event_by_type: Dict[str, OrderLifecycleEvent] = {}
    partial_fill_event: Optional[OrderLifecycleEvent] = None
    cancel_event: Optional[OrderLifecycleEvent] = None
    terminal_event: Optional[OrderLifecycleEvent] = None
    partial_fill_observed = False
    cancel_observed = False
    terminal_state_observed = False
    for event in lifecycle_events:
        event_type = str(getattr(event, "event_type", "") or "unknown")
        if event_type not in event_type_counts:
            event_types_seen.append(event_type)
        event_type_counts[event_type] = int(event_type_counts.get(event_type, 0)) + 1
        latest_event_by_type[event_type] = event
        normalized_state = _normalize_order_state(getattr(event, "order_state", None))
        if normalized_state == "partially_filled" or event_type == "partial_fill":
            partial_fill_observed = True
            partial_fill_event = event
        if normalized_state == "canceled" or event_type in {"canceled", "cancel_ack", "cancelled"}:
            cancel_observed = True
            cancel_event = event
        if normalized_state in {"closed", "canceled", "rejected", "expired"}:
            terminal_state_observed = True
            terminal_event = event

    required_event_types: List[str] = []
    if runtime_state != "absent":
        if runtime_state == "rejected":
            required_event_types = ["rejected"]
        else:
            required_event_types = ["validation_passed", "venue_ack", "trade_history_persisted"]
    missing_event_types = [event_type for event_type in required_event_types if event_type_counts.get(event_type, 0) <= 0]

    replay_key_ready = bool(
        _record_text(last_order, "order_id")
        or _record_text(last_order, "client_order_id")
        or getattr(latest_trade, "order_id", None)
        or getattr(latest_trade, "client_order_id", None)
    )

    if not required_event_types:
        baseline_contract_status = "not_applicable"
    elif missing_event_types:
        baseline_contract_status = "incomplete"
    else:
        baseline_contract_status = "complete"

    restart_replay_required = bool(lifecycle_audit.get("restart_replay_required"))
    if runtime_state == "absent":
        replay_readiness = "not_applicable"
        replay_readiness_reason = "no_runtime_order"
    elif baseline_contract_status != "complete":
        replay_readiness = "blocked"
        replay_readiness_reason = "missing_required_lifecycle_events"
    elif not replay_key_ready:
        replay_readiness = "blocked"
        replay_readiness_reason = "missing_replay_key"
    elif restart_replay_required:
        replay_readiness = "blocked"
        replay_readiness_reason = str(lifecycle_audit.get("reason") or "restart_replay_required")
    else:
        replay_readiness = "ready"
        replay_readiness_reason = "baseline_reconciliation_ready"

    if partial_fill_observed and cancel_observed:
        artifact_coverage = "partial_fill_and_cancel_observed"
    elif partial_fill_observed:
        artifact_coverage = "partial_fill_observed"
    elif cancel_observed:
        artifact_coverage = "cancel_observed"
    elif terminal_state_observed:
        artifact_coverage = "terminal_observed_without_partial_or_cancel"
    elif baseline_contract_status == "complete":
        artifact_coverage = "baseline_only"
    else:
        artifact_coverage = "incomplete"

    if baseline_contract_status != "complete":
        operator_next_artifact = "backfill_required_lifecycle_events"
        summary = "目前 only 有部分 lifecycle 記錄；先補齊 validation / venue ack / trade_history persist 基線事件。"
        status = "incomplete"
    elif replay_readiness != "ready":
        operator_next_artifact = "capture_restart_replay_evidence"
        summary = "基線 lifecycle 已存在，但 restart replay 仍缺可驗證證據。"
        status = "replay_blocked"
    elif artifact_coverage == "baseline_only":
        operator_next_artifact = "capture_partial_fill_or_cancel_artifacts"
        summary = "基線 lifecycle 已對上，但 partial fill / cancel artifact 尚未觀察到。"
        status = "baseline_only"
    else:
        operator_next_artifact = "keep_validating_live_lifecycle"
        summary = "lifecycle artifact 已涵蓋 baseline replay，且已觀察到額外 execution path evidence。"
        status = "extended_coverage"

    if status == "absent":
        replay_verdict = "no_runtime_order"
        replay_verdict_reason = "no_runtime_order"
        replay_verdict_summary = "目前沒有可供 restart replay 的 runtime order。"
    elif status == "incomplete":
        replay_verdict = "baseline_events_missing"
        replay_verdict_reason = "missing_required_lifecycle_events"
        replay_verdict_summary = "replay 尚未成立：validation / venue ack / trade_history persist 基線事件仍缺漏。"
    elif replay_readiness != "ready":
        replay_verdict = "restart_replay_blocked"
        replay_verdict_reason = replay_readiness_reason
        replay_verdict_summary = "基線 lifecycle 已存在，但 restart replay 仍被 recovery lane 擋下。"
    elif artifact_coverage in {"baseline_only", "terminal_observed_without_partial_or_cancel"}:
        replay_verdict = "baseline_replay_ready_missing_path_artifacts"
        replay_verdict_reason = artifact_coverage
        replay_verdict_summary = "baseline replay 已可驗證，但 partial fill / cancel 類 execution path artifact 還不夠。"
    else:
        replay_verdict = "replay_artifacts_observed"
        replay_verdict_reason = artifact_coverage
        replay_verdict_summary = "baseline replay 與額外 execution path artifact 都已觀察到，可持續擴充 venue coverage。"

    baseline_observed_count = 0
    baseline_required_count = 0
    path_observed_count = int(partial_fill_observed) + int(cancel_observed)

    artifact_checklist: List[Dict[str, Any]] = []
    for event_type, label in [
        ("validation_passed", "Validation passed"),
        ("venue_ack", "Venue ack"),
        ("trade_history_persisted", "Trade history persisted"),
    ]:
        required = event_type in required_event_types
        observed = event_type_counts.get(event_type, 0) > 0
        if required:
            baseline_required_count += 1
            baseline_observed_count += int(observed)
        artifact_checklist.append(
            {
                "key": event_type,
                "label": label,
                "status": "observed" if observed else ("missing" if required else "not_applicable"),
                "required": required,
                "observed": observed,
                "count": int(event_type_counts.get(event_type, 0)),
                "summary": (
                    f"已觀察到 {label.lower()} artifact。"
                    if observed
                    else (f"{label} 是 replay baseline 必要證據，當前仍缺失。" if required else f"當前 runtime path 不要求 {label}。")
                ),
                "evidence": _event_evidence(latest_event_by_type.get(event_type)),
            }
        )

    artifact_checklist.append(
        {
            "key": "partial_fill",
            "label": "Partial fill artifact",
            "status": "observed" if partial_fill_observed else ("pending_optional" if baseline_contract_status == "complete" else "waiting_baseline"),
            "required": False,
            "observed": partial_fill_observed,
            "count": int(event_type_counts.get("partial_fill", 0)),
            "summary": (
                "已觀察到 partial fill artifact，可支撐更完整的 venue replay closure。"
                if partial_fill_observed
                else (
                    "baseline 已就緒，但尚未看到 partial fill path；仍需補充 venue path evidence。"
                    if baseline_contract_status == "complete"
                    else "先補齊 baseline lifecycle，再追 partial fill / cancel path artifact。"
                )
            ),
            "evidence": _event_evidence(partial_fill_event),
        }
    )
    artifact_checklist.append(
        {
            "key": "cancel",
            "label": "Cancel artifact",
            "status": "observed" if cancel_observed else ("pending_optional" if baseline_contract_status == "complete" else "waiting_baseline"),
            "required": False,
            "observed": cancel_observed,
            "count": int(event_type_counts.get("cancel_ack", 0) + event_type_counts.get("canceled", 0) + event_type_counts.get("cancelled", 0)),
            "summary": (
                "已觀察到 cancel artifact，可驗證 order cancel/replay lane。"
                if cancel_observed
                else (
                    "baseline 已就緒，但尚未看到 cancel path；仍需補充 venue cancel evidence。"
                    if baseline_contract_status == "complete"
                    else "先補齊 baseline lifecycle，再追 partial fill / cancel path artifact。"
                )
            ),
            "evidence": _event_evidence(cancel_event),
        }
    )
    artifact_checklist.append(
        {
            "key": "terminal_state",
            "label": "Terminal state observed",
            "status": "observed" if terminal_state_observed else ("pending" if runtime_state != "absent" else "not_applicable"),
            "required": False,
            "observed": terminal_state_observed,
            "count": int(terminal_state_observed),
            "summary": (
                "已觀察到 closed / canceled / rejected / expired 類 terminal state。"
                if terminal_state_observed
                else "目前尚未觀察到 terminal state；若 order 仍 open，需持續追蹤後續 lifecycle。"
            ),
            "evidence": _event_evidence(terminal_event),
        }
    )
    artifact_checklist.append(
        {
            "key": "restart_replay",
            "label": "Restart replay evidence",
            "status": (
                "ready"
                if replay_readiness == "ready"
                else ("blocked" if replay_readiness == "blocked" else "not_applicable")
            ),
            "required": runtime_state != "absent",
            "observed": replay_readiness == "ready",
            "count": int(replay_readiness == "ready"),
            "summary": (
                "baseline replay 已 ready，可開始核對 restart replay closure。"
                if replay_readiness == "ready"
                else (
                    f"restart replay 仍被擋下：{replay_readiness_reason}。"
                    if replay_readiness == "blocked"
                    else "目前沒有 runtime order，restart replay 不適用。"
                )
            ),
            "evidence": {
                "order_id": _record_text(last_order, "order_id") or getattr(latest_trade, "order_id", None),
                "client_order_id": _record_text(last_order, "client_order_id") or getattr(latest_trade, "client_order_id", None),
                "reason": replay_readiness_reason,
                "operator_next_artifact": operator_next_artifact,
            },
        }
    )

    artifact_checklist_summary = (
        f"baseline {baseline_observed_count}/{baseline_required_count or 0} ready · "
        f"path artifacts {path_observed_count}/2 observed · "
        f"restart replay {replay_readiness}"
    )

    return {
        "status": status,
        "summary": summary,
        "event_type_counts": event_type_counts,
        "event_types_seen": event_types_seen,
        "required_event_types": required_event_types,
        "missing_event_types": missing_event_types,
        "replay_key_ready": replay_key_ready,
        "replay_readiness": replay_readiness,
        "replay_readiness_reason": replay_readiness_reason,
        "replay_verdict": replay_verdict,
        "replay_verdict_reason": replay_verdict_reason,
        "replay_verdict_summary": replay_verdict_summary,
        "baseline_contract_status": baseline_contract_status,
        "partial_fill_observed": partial_fill_observed,
        "cancel_observed": cancel_observed,
        "terminal_state_observed": terminal_state_observed,
        "artifact_coverage": artifact_coverage,
        "operator_next_artifact": operator_next_artifact,
        "artifact_checklist_summary": artifact_checklist_summary,
        "artifact_checklist": artifact_checklist,
    }


def _build_execution_reconciliation_summary(
    db,
    symbol: str,
    account_snapshot: Optional[Dict[str, Any]],
    execution_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    account_snapshot = account_snapshot or {}
    execution_summary = execution_summary or {}
    guardrails = execution_summary.get("guardrails") if isinstance(execution_summary, dict) else {}
    guardrails = guardrails if isinstance(guardrails, dict) else {}
    last_order = guardrails.get("last_order") if isinstance(guardrails.get("last_order"), dict) else None
    open_orders = account_snapshot.get("open_orders") if isinstance(account_snapshot.get("open_orders"), list) else []
    positions = account_snapshot.get("positions") if isinstance(account_snapshot.get("positions"), list) else []
    account_degraded = bool(account_snapshot.get("degraded"))
    captured_at = _parse_utc_datetime(account_snapshot.get("captured_at"))
    snapshot_age_minutes = None
    freshness_status = "unavailable"
    freshness_reason = "missing_snapshot_timestamp"
    if captured_at is not None:
        snapshot_age_minutes = max((datetime.now(timezone.utc) - captured_at).total_seconds() / 60.0, 0.0)
        if snapshot_age_minutes <= 5.0:
            freshness_status = "fresh"
            freshness_reason = "snapshot_within_policy"
        else:
            freshness_status = "stale"
            freshness_reason = "snapshot_older_than_policy"

    latest_trade = _latest_trade_history_row(db)
    lifecycle_events = _latest_order_lifecycle_events(db, last_order=last_order, latest_trade=latest_trade)
    runtime_order_ids = _extract_runtime_order_ids(last_order)
    latest_trade_order_ids = []
    if latest_trade is not None:
        latest_trade_order_ids = [value for value in [getattr(latest_trade, "order_id", None), getattr(latest_trade, "client_order_id", None)] if value]

    trade_alignment_status = "no_recent_runtime_order"
    trade_alignment_reason = "runtime_has_not_recorded_an_order_yet"
    if last_order is not None:
        if latest_trade is None:
            trade_alignment_status = "missing_trade_history"
            trade_alignment_reason = "runtime_has_last_order_but_trade_history_has_no_rows"
        elif runtime_order_ids and any(order_id in latest_trade_order_ids for order_id in runtime_order_ids):
            trade_alignment_status = "matched"
            trade_alignment_reason = "latest_trade_history_row_matches_runtime_last_order"
        elif not runtime_order_ids and _record_text(last_order, "symbol") == getattr(latest_trade, "symbol", None):
            trade_alignment_status = "symbol_only_match"
            trade_alignment_reason = "runtime_last_order_missing_ids_fell_back_to_symbol_match"
        else:
            trade_alignment_status = "mismatch"
            trade_alignment_reason = "latest_trade_history_row_does_not_match_runtime_last_order"

    open_order_alignment_status = "not_applicable"
    open_order_alignment_reason = "no_recent_runtime_order"
    matched_account_order = None
    if last_order is not None:
        order_status = str(last_order.get("status") or "").lower()
        matched_account_order = next(
            (
                order
                for order in open_orders
                if (
                    runtime_order_ids and any(order_id in _extract_account_order_ids(order) for order_id in runtime_order_ids)
                ) or (
                    _record_text(order, "symbol") == last_order.get("symbol")
                    and order_status in {"open", "new", "partially_filled"}
                )
            ),
            None,
        )
        if order_status in {"open", "new", "partially_filled"}:
            if matched_account_order is not None:
                open_order_alignment_status = "matched"
                open_order_alignment_reason = "runtime_last_order_is_visible_in_account_open_orders"
            elif account_degraded:
                open_order_alignment_status = "degraded"
                open_order_alignment_reason = "account_snapshot_is_degraded_so_open_order_truth_is_not_verified"
            else:
                open_order_alignment_status = "missing_from_account_snapshot"
                open_order_alignment_reason = "runtime_last_order_is_open_but_account_snapshot_cannot_find_it"
        else:
            open_order_alignment_status = "not_open"
            open_order_alignment_reason = "runtime_last_order_is_not_in_open_state"

    symbol_alignment_status = "matched"
    symbol_alignment_reason = "account_snapshot_scope_matches_config_symbol"
    normalized_symbol = account_snapshot.get("normalized_symbol")
    requested_symbol = account_snapshot.get("requested_symbol")
    expected_normalized_symbol = _normalize_symbol_scope(symbol)
    if requested_symbol and requested_symbol != symbol:
        symbol_alignment_status = "scope_override"
        symbol_alignment_reason = "account_snapshot_requested_symbol_differs_from_config_symbol"
    elif normalized_symbol and normalized_symbol not in {symbol, expected_normalized_symbol}:
        symbol_alignment_status = "normalized_symbol_mismatch"
        symbol_alignment_reason = "account_snapshot_normalized_symbol_differs_from_config_scope"

    issues: List[str] = []
    if account_degraded:
        issues.append("account_snapshot_degraded")
    if freshness_status == "stale":
        issues.append("account_snapshot_stale")
    if trade_alignment_status in {"missing_trade_history", "mismatch"}:
        issues.append(f"trade_history_{trade_alignment_status}")
    if open_order_alignment_status == "missing_from_account_snapshot":
        issues.append("open_order_missing_from_snapshot")
    if symbol_alignment_status != "matched":
        issues.append(symbol_alignment_status)

    lifecycle_audit = _build_execution_lifecycle_audit(
        account_degraded=account_degraded,
        freshness_status=freshness_status,
        last_order=last_order,
        latest_trade=latest_trade,
        trade_alignment_status=trade_alignment_status,
        open_order_alignment_status=open_order_alignment_status,
        matched_account_order=matched_account_order,
    )
    recovery_state = _build_execution_recovery_state(
        lifecycle_audit=lifecycle_audit,
        account_degraded=account_degraded,
        freshness_status=freshness_status,
        trade_alignment_status=trade_alignment_status,
        open_order_alignment_status=open_order_alignment_status,
    )
    lifecycle_contract = _build_execution_lifecycle_contract(
        lifecycle_events=lifecycle_events,
        lifecycle_audit=lifecycle_audit,
        last_order=last_order,
        latest_trade=latest_trade,
    )

    if account_degraded:
        status = "degraded"
        summary = "account snapshot 退化，暫時不能把 UI 上的倉位 / 掛單列表當成已對帳真相。"
    elif issues:
        status = "warning"
        summary = "runtime / account / trade history 已有可見對帳訊號，但仍存在 mismatch 或 stale blocker。"
    else:
        status = "healthy"
        summary = "runtime last order、account snapshot 與 trade history 目前沒有發現明顯對帳落差。"

    return {
        "status": status,
        "summary": summary,
        "checked_at": checked_at,
        "issues": issues,
        "lifecycle_audit": lifecycle_audit,
        "recovery_state": recovery_state,
        "lifecycle_contract": lifecycle_contract,
        "lifecycle_timeline": {
            "status": "available" if lifecycle_events else "absent",
            "replay_key": {
                "order_id": _record_text(last_order, "order_id") or getattr(latest_trade, "order_id", None),
                "client_order_id": _record_text(last_order, "client_order_id") or getattr(latest_trade, "client_order_id", None),
            },
            "total_events": len(lifecycle_events),
            "latest_event": {
                "timestamp": _iso_utc_timestamp(lifecycle_events[-1].timestamp),
                "event_type": lifecycle_events[-1].event_type,
                "order_state": lifecycle_events[-1].order_state,
                "summary": lifecycle_events[-1].summary,
            } if lifecycle_events else None,
            "events": [
                {
                    "timestamp": _iso_utc_timestamp(event.timestamp),
                    "event_type": event.event_type,
                    "order_state": event.order_state,
                    "source": event.source,
                    "summary": event.summary,
                    "order_id": event.order_id,
                    "client_order_id": event.client_order_id,
                    "exchange": event.exchange,
                    "symbol": event.symbol,
                    "is_dry_run": bool(event.is_dry_run) if event.is_dry_run is not None else None,
                    "payload": _parse_lifecycle_payload(event.payload_json),
                }
                for event in lifecycle_events
            ],
        },
        "account_snapshot": {
            "captured_at": account_snapshot.get("captured_at"),
            "freshness": {
                "status": freshness_status,
                "reason": freshness_reason,
                "age_minutes": round(snapshot_age_minutes, 2) if snapshot_age_minutes is not None else None,
                "stale_after_minutes": 5.0,
            },
            "degraded": account_degraded,
            "position_count": account_snapshot.get("position_count", len(positions)),
            "open_order_count": account_snapshot.get("open_order_count", len(open_orders)),
        },
        "symbol_scope": {
            "config_symbol": symbol,
            "requested_symbol": requested_symbol,
            "normalized_symbol": normalized_symbol,
            "status": symbol_alignment_status,
            "reason": symbol_alignment_reason,
        },
        "runtime_last_order": {
            "status": "present" if last_order is not None else "absent",
            "order": last_order,
        },
        "trade_history_alignment": {
            "status": trade_alignment_status,
            "reason": trade_alignment_reason,
            "latest_trade": {
                "timestamp": _iso_utc_timestamp(getattr(latest_trade, "timestamp", None)) if latest_trade is not None else None,
                "symbol": getattr(latest_trade, "symbol", None) if latest_trade is not None else None,
                "exchange": getattr(latest_trade, "exchange", None) if latest_trade is not None else None,
                "action": getattr(latest_trade, "action", None) if latest_trade is not None else None,
                "order_id": getattr(latest_trade, "order_id", None) if latest_trade is not None else None,
                "client_order_id": getattr(latest_trade, "client_order_id", None) if latest_trade is not None else None,
                "order_status": getattr(latest_trade, "order_status", None) if latest_trade is not None else None,
                "is_dry_run": bool(getattr(latest_trade, "is_dry_run", 0)) if latest_trade is not None else None,
            },
        },
        "open_order_alignment": {
            "status": open_order_alignment_status,
            "reason": open_order_alignment_reason,
            "matched_open_order": {
                "id": _record_text(matched_account_order, "id") or _record_text(matched_account_order, "orderId") or _record_text(matched_account_order, "ordId"),
                "symbol": _record_text(matched_account_order, "symbol") or _record_text(matched_account_order, "instId"),
                "status": _record_text(matched_account_order, "status") or _record_text(matched_account_order, "state"),
            } if matched_account_order is not None else None,
        },
    }


def _record_execution_metadata_smoke_background_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    _EXECUTION_METADATA_SMOKE_BACKGROUND_STATE.update(payload or {})
    snapshot = _build_execution_metadata_smoke_background_state()
    set_runtime_status("execution_metadata_smoke_background", snapshot)
    return snapshot


def _refresh_execution_metadata_smoke_artifact(cfg: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    attempted_at = datetime.now(timezone.utc)
    attempted_at_iso = attempted_at.isoformat().replace("+00:00", "Z")
    with _EXECUTION_METADATA_SMOKE_REFRESH_LOCK:
        next_retry_at = _EXECUTION_METADATA_SMOKE_REFRESH_STATE.get("next_retry_at")
        next_retry_dt = _parse_utc_datetime(next_retry_at)
        if next_retry_dt and attempted_at < next_retry_dt:
            _EXECUTION_METADATA_SMOKE_REFRESH_STATE.update({
                "attempted_at": attempted_at_iso,
                "completed_at": _EXECUTION_METADATA_SMOKE_REFRESH_STATE.get("completed_at"),
                "status": "cooldown",
                "reason": "cooldown_active",
                "next_retry_at": next_retry_dt.isoformat().replace("+00:00", "Z"),
                "error": None,
            })
            return {
                "attempted": False,
                "status": "cooldown",
                "reason": "cooldown_active",
                "attempted_at": attempted_at_iso,
                "completed_at": _EXECUTION_METADATA_SMOKE_REFRESH_STATE.get("completed_at"),
                "next_retry_at": _EXECUTION_METADATA_SMOKE_REFRESH_STATE.get("next_retry_at"),
                "error": None,
                "cooldown_seconds": _EXECUTION_METADATA_SMOKE_AUTO_REFRESH_COOLDOWN_SECONDS,
            }

        _EXECUTION_METADATA_SMOKE_REFRESH_STATE.update({
            "attempted_at": attempted_at_iso,
            "completed_at": None,
            "status": "running",
            "reason": "refresh_started",
            "next_retry_at": None,
            "error": None,
        })
        try:
            payload = run_metadata_smoke(cfg, symbol=symbol)
            _EXECUTION_METADATA_SMOKE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _EXECUTION_METADATA_SMOKE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            completed_at_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            _EXECUTION_METADATA_SMOKE_REFRESH_STATE.update({
                "attempted_at": attempted_at_iso,
                "completed_at": completed_at_iso,
                "status": "succeeded",
                "reason": "refresh_completed",
                "next_retry_at": None,
                "error": None,
            })
            return {
                "attempted": True,
                "status": "succeeded",
                "reason": "refresh_completed",
                "attempted_at": attempted_at_iso,
                "completed_at": completed_at_iso,
                "next_retry_at": None,
                "error": None,
                "cooldown_seconds": _EXECUTION_METADATA_SMOKE_AUTO_REFRESH_COOLDOWN_SECONDS,
            }
        except Exception as exc:
            completed_at_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            next_retry_iso = (datetime.now(timezone.utc) + timedelta(seconds=_EXECUTION_METADATA_SMOKE_AUTO_REFRESH_COOLDOWN_SECONDS)).isoformat().replace("+00:00", "Z")
            _EXECUTION_METADATA_SMOKE_REFRESH_STATE.update({
                "attempted_at": attempted_at_iso,
                "completed_at": completed_at_iso,
                "status": "failed",
                "reason": "refresh_failed",
                "next_retry_at": next_retry_iso,
                "error": str(exc),
            })
            return {
                "attempted": True,
                "status": "failed",
                "reason": "refresh_failed",
                "attempted_at": attempted_at_iso,
                "completed_at": completed_at_iso,
                "next_retry_at": next_retry_iso,
                "error": str(exc),
                "cooldown_seconds": _EXECUTION_METADATA_SMOKE_AUTO_REFRESH_COOLDOWN_SECONDS,
            }


def _build_execution_metadata_smoke_governance(summary: Optional[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
    freshness = (summary or {}).get("freshness") if isinstance(summary, dict) else None
    freshness_status = freshness.get("status") if isinstance(freshness, dict) else "unavailable"
    refresh_state = _build_execution_metadata_smoke_refresh_state()
    background_state = _build_execution_metadata_smoke_background_state()
    external_state = _load_execution_metadata_external_monitor_state(symbol)
    command = f"source venv/bin/activate && python scripts/execution_metadata_smoke.py --symbol {symbol}"
    if freshness_status == "fresh":
        return {
            "status": "healthy",
            "operator_action": "none",
            "operator_message": "metadata smoke artifact 在 freshness policy 內，無需額外治理動作。",
            "refresh_command": command,
            "escalation_message": None,
            "auto_refresh": refresh_state,
            "background_monitor": background_state,
            "external_monitor": external_state,
        }
    if freshness_status == "stale":
        escalation = "若自動 refresh 連續失敗或長時間維持 stale，背景監看器需升級為 execution metadata blocker；若 API process 不在場，請改看 external monitor lane。"
        return {
            "status": "refresh_required",
            "operator_action": "rerun_metadata_smoke",
            "operator_message": "metadata smoke artifact 已過 stale policy；API 與背景監看器都會嘗試自動 refresh，operator 需確認 refresh 結果與 Dashboard badge 是否回到 FRESH。",
            "refresh_command": command,
            "escalation_message": escalation,
            "auto_refresh": refresh_state,
            "background_monitor": background_state,
            "external_monitor": external_state,
        }
    escalation = "artifact 缺失或無法解析；若自動 refresh、背景監看器與 external monitor 都無法恢復，需升級為 execution metadata blocker 並檢查腳本 / 檔案權限 / venue metadata lane。"
    return {
        "status": "artifact_unavailable",
        "operator_action": "rebuild_artifact",
        "operator_message": "metadata smoke artifact 不可用；API 會優先嘗試自動重建，背景監看器也會持續檢查，若失敗需立刻檢查 artifact lane。",
        "refresh_command": command,
        "escalation_message": escalation,
        "auto_refresh": refresh_state,
        "background_monitor": background_state,
        "external_monitor": external_state,
    }


def _ensure_execution_metadata_smoke_governance(cfg: Dict[str, Any], symbol: str) -> Optional[Dict[str, Any]]:
    summary = _load_execution_metadata_smoke_summary()
    freshness = summary.get("freshness") if isinstance(summary, dict) else None
    freshness_status = freshness.get("status") if isinstance(freshness, dict) else "unavailable"
    if freshness_status in {"stale", "unavailable"}:
        refresh_info = _refresh_execution_metadata_smoke_artifact(cfg, symbol)
        if refresh_info.get("status") == "succeeded":
            summary = _load_execution_metadata_smoke_summary()
    summary_payload = summary or {
        "available": False,
        "artifact_path": str(_EXECUTION_METADATA_SMOKE_PATH),
        "freshness": {
            "status": "unavailable",
            "label": "unavailable",
            "reason": "artifact_missing",
            "age_minutes": None,
            "stale_after_minutes": _EXECUTION_METADATA_SMOKE_STALE_AFTER_MINUTES,
        },
    }
    summary_payload["governance"] = _build_execution_metadata_smoke_governance(summary_payload, symbol)
    return summary_payload


def run_execution_metadata_smoke_background_governance(
    cfg: Dict[str, Any],
    symbol: str,
    *,
    reason: str = "background_monitor_tick",
    interval_seconds: float = 60.0,
) -> Optional[Dict[str, Any]]:
    checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _record_execution_metadata_smoke_background_state({
        "status": "running",
        "reason": reason,
        "checked_at": checked_at,
        "freshness_status": None,
        "governance_status": None,
        "error": None,
        "interval_seconds": interval_seconds,
    })
    try:
        summary = _ensure_execution_metadata_smoke_governance(cfg, symbol)
        governance = summary.get("governance") if isinstance(summary, dict) else {}
        freshness = summary.get("freshness") if isinstance(summary, dict) else {}
        freshness_status = freshness.get("status") if isinstance(freshness, dict) else None
        governance_status = governance.get("status") if isinstance(governance, dict) else None
        monitor_status = "healthy" if freshness_status == "fresh" else "attention_required"
        _record_execution_metadata_smoke_background_state({
            "status": monitor_status,
            "reason": reason,
            "checked_at": checked_at,
            "freshness_status": freshness_status,
            "governance_status": governance_status,
            "error": None,
            "interval_seconds": interval_seconds,
        })
        return summary
    except Exception as exc:
        _record_execution_metadata_smoke_background_state({
            "status": "failed",
            "reason": reason,
            "checked_at": checked_at,
            "freshness_status": None,
            "governance_status": None,
            "error": str(exc),
            "interval_seconds": interval_seconds,
        })
        raise


def _strategy_job_stage_plan(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    params = body.get("params", {}) if isinstance(body.get("params"), dict) else {}
    stype = str(body.get("type", "rule_based") or "rule_based")
    auto_backfill = bool(body.get("auto_backfill", params.get("auto_backfill", False)))
    keys: List[str] = ["queued", "load_data"]
    if auto_backfill:
        keys.extend(["backfill_raw", "backfill_features", "backfill_labels", "reload_data"])
    if stype == "hybrid":
        keys.extend(["prepare_hybrid", "train_model"])
    keys.extend(["run_backtest", "postprocess", "save_results"])
    return [{"key": key, "label": _STRATEGY_STAGE_LABELS.get(key, key), "status": "pending"} for key in keys]


def _update_strategy_job_steps(job: Dict[str, Any], stage_key: Optional[str], *, status: str) -> None:
    steps = job.get("steps")
    if not isinstance(steps, list) or not steps:
        return
    if not stage_key:
        if status == "completed":
            for step in steps:
                step["status"] = "completed"
        return
    current_index = next((idx for idx, step in enumerate(steps) if step.get("key") == stage_key), None)
    if current_index is None:
        return
    for idx, step in enumerate(steps):
        if idx < current_index and step.get("status") not in {"completed", "failed"}:
            step["status"] = "completed"
        elif idx == current_index:
            step["status"] = "failed" if status == "failed" else ("completed" if status == "completed" and current_index == len(steps) - 1 else "running")
        elif idx > current_index and step.get("status") == "running":
            step["status"] = "pending"


# ─── Models ───
class TradeRequest(BaseModel):
    side: str
    symbol: str = "BTCUSDT"
    qty: float = 0.001


class SenseConfigUpdate(BaseModel):
    sense: str
    module: str
    enabled: Optional[bool] = None
    weight: Optional[float] = None


# ─── Core Helpers ───
def _calc_ma_at(data, period, i):
    s = max(0, i - period + 1)
    n = i - s + 1
    return sum(data[s:i + 1]) / n if n > 0 else 0


def _compute_chart_indicators(ohlcv: List[List[float]]) -> Dict[str, Any]:
    closes = [float(row[4]) for row in ohlcv]
    indicators: Dict[str, Any] = {
        "ma20": [],
        "ma60": [],
        "rsi": [],
        "macd": [],
        "signal": [],
        "histogram": [],
    }
    for i in range(len(closes)):
        indicators["ma20"].append(round(_calc_ma_at(closes, 20, i), 2))
        indicators["ma60"].append(round(_calc_ma_at(closes, 60, i), 2))

    if len(closes) >= 15:
        avg_g = [0.0] * len(closes)
        avg_l = [0.0] * len(closes)
        for i in range(1, len(closes)):
            d = closes[i] - closes[i - 1]
            if i < 14:
                if d > 0:
                    avg_g[i] = d
                if d < 0:
                    avg_l[i] = -d
            else:
                avg_g[i] = (avg_g[i - 1] * 13 + max(d, 0)) / 14
                avg_l[i] = (avg_l[i - 1] * 13 + max(-d, 0)) / 14
        indicators["rsi"] = [
            round(100 - 100 / (1 + (g / l if l > 0 else 999)), 1) if g + l > 0 else 50
            for g, l in zip(avg_g, avg_l)
        ]

    if len(closes) >= 26:
        def _ema(values: List[float], period: int) -> List[float]:
            k = 2 / (period + 1)
            result = [values[0]]
            for value in values[1:]:
                result.append(result[-1] * (1 - k) + value * k)
            return result

        ema12 = _ema(closes, 12)
        ema26 = _ema(closes, 26)
        macd_line = [fast - slow for fast, slow in zip(ema12, ema26)]
        signal_line = _ema(macd_line[25:], 9)
        signal_line = [None] * 25 + signal_line
        indicators["macd"] = [round(value, 4) if value is not None else None for value in macd_line]
        indicators["signal"] = [round(value, 4) if value is not None else None for value in signal_line]
        indicators["histogram"] = [
            round(macd - signal, 4) if macd is not None and signal is not None else None
            for macd, signal in zip(macd_line, signal_line)
        ]

    return indicators


def _build_chart_payload(symbol: str, interval: str, ohlcv: List[List[float]]) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "interval": interval,
        "candles": [
            {
                "time": int(row[0] / 1000),
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
            }
            for row in ohlcv
        ],
        "indicators": _compute_chart_indicators(ohlcv),
    }


def _slice_chart_payload(payload: Dict[str, Any], start_index: int) -> Dict[str, Any]:
    if start_index <= 0:
        return payload
    indicators = payload.get("indicators") or {}
    return {
        "symbol": payload.get("symbol"),
        "interval": payload.get("interval"),
        "candles": (payload.get("candles") or [])[start_index:],
        "indicators": {
            "ma20": (indicators.get("ma20") or [])[start_index:],
            "ma60": (indicators.get("ma60") or [])[start_index:],
            "rsi": (indicators.get("rsi") or [])[start_index:],
            "macd": (indicators.get("macd") or [])[start_index:],
            "signal": (indicators.get("signal") or [])[start_index:],
            "histogram": (indicators.get("histogram") or [])[start_index:],
        },
    }


def _calc_max_dd(eq):
    """計算最大回撤"""
    if not eq:
        return 0
    pk = eq[0]
    mdd = 0
    for v in eq:
        if v > pk:
            pk = v
        dd = (pk - v) / pk
        if dd > mdd:
            mdd = dd
    return mdd


# ─── Feature Key Map ───


_ECDF_ANCHORS = {
    'feat_eye': (-4.5, 4.5), 'feat_ear': (-0.0005, 0.0005),
    'feat_nose': (0.15, 0.80), 'feat_tongue': (-0.001, 0.001),
    'feat_body': (-1.8, 1.3), 'feat_pulse': (0.0, 0.99),
    'feat_aura': (-0.003, 0.003), 'feat_mind': (-0.006, 0.004),
    'feat_vix': (12.0, 35.0), 'feat_dxy': (95.0, 110.0),
    'feat_rsi14': (0.1, 0.85), 'feat_macd_hist': (-0.0005, 0.0005),
    'feat_atr_pct': (0.005, 0.03), 'feat_vwap_dev': (-0.5, 0.5),
    'feat_bb_pct_b': (0.0, 1.0), 'feat_nw_width': (0.0, 0.08),
    'feat_nw_slope': (-0.03, 0.03), 'feat_adx': (0.0, 0.8),
    'feat_choppiness': (0.25, 0.75), 'feat_donchian_pos': (0.0, 1.0),
    'feat_nq_return_1h': (-0.03, 0.03), 'feat_nq_return_24h': (-0.08, 0.08),
    'feat_claw': (0.0, 1.0), 'feat_claw_intensity': (0.0, 1.5),
    'feat_fang_pcr': (0.5, 1.5), 'feat_fang_skew': (-0.5, 0.5),
    'feat_fin_netflow': (-1.0, 1.0), 'feat_web_whale': (-1.0, 1.0),
    'feat_scales_ssr': (0.5, 1.5), 'feat_nest_pred': (-1.0, 1.0),
    'feat_4h_bias50': (-15.0, 10.0), 'feat_4h_bias20': (-10.0, 10.0),
    'feat_4h_bias200': (-20.0, 20.0),
    'feat_4h_rsi14': (10.0, 90.0), 'feat_4h_macd_hist': (-1500.0, 1500.0),
    'feat_4h_bb_pct_b': (-0.5, 1.5), 'feat_4h_dist_bb_lower': (-10.0, 20.0),
    'feat_4h_ma_order': (-1.5, 1.5), 'feat_4h_dist_swing_low': (-25.0, 20.0),
    'feat_4h_vol_ratio': (0.3, 3.0),
}


def normalize_for_api(raw_val, db_key):
    """Soft ECDF normalization for feature history API."""
    if raw_val is None:
        return None
    anchors = _ECDF_ANCHORS.get(db_key)
    if not anchors:
        return max(0.0, min(1.0, (raw_val + 1) / 2))
    p5, p95 = anchors
    span = p95 - p5
    if span < 1e-10:
        return 0.5
    soft_margin = span * 0.5
    soft_lo = p5 - soft_margin
    soft_hi = p95 + soft_margin
    if raw_val <= p5:
        v = max(soft_lo, raw_val)
        return round(0.02 + 0.08 * (v - soft_lo) / max(p5 - soft_lo, 1e-10), 4)
    if raw_val >= p95:
        v = min(soft_hi, raw_val)
        return round(0.90 + 0.08 * (v - p95) / max(soft_hi - p95, 1e-10), 4)
    return round(0.10 + 0.80 * (raw_val - p5) / span, 4)




def _compute_raw_snapshot_stats(db) -> Dict[str, Dict[str, Any]]:
    try:
        bind = db.get_bind()
        if bind is None:
            return {}
        db_path = bind.url.database
        if not db_path:
            return {}
        conn = sqlite3.connect(db_path)
        try:
            return compute_raw_snapshot_stats(conn)
        finally:
            conn.close()
    except Exception:
        return {}


def _compute_feature_coverage(db, days: int = 90) -> Dict[str, Any]:
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(FeaturesNormalized)
        .filter(FeaturesNormalized.timestamp >= since)
        .order_by(FeaturesNormalized.timestamp)
        .all()
    )
    snapshot_stats = _compute_raw_snapshot_stats(db)
    snapshot_counts = {subtype: row.get("count", 0) for subtype, row in snapshot_stats.items()}
    total_rows = len(rows)
    feature_stats: Dict[str, Any] = {}
    timestamp_values = [getattr(r, "timestamp", None) for r in rows]
    for db_key, clean_key in FEATURE_KEY_MAP.items():
        values = [getattr(r, db_key, None) for r in rows]
        non_null_values = [v for v in values if v is not None]
        distinct = len({round(float(v), 10) for v in non_null_values}) if non_null_values else 0
        coverage_pct = (len(non_null_values) / total_rows * 100.0) if total_rows else 0.0
        min_val = min(non_null_values) if non_null_values else None
        max_val = max(non_null_values) if non_null_values else None
        archive_window = _compute_archive_window_coverage(clean_key, timestamp_values, values, snapshot_stats)
        quality = assess_feature_quality(clean_key, coverage_pct, distinct, len(non_null_values), min_val, max_val)
        quality.update(archive_window)
        quality = attach_forward_archive_meta(clean_key, quality, snapshot_counts, snapshot_stats)
        feature_stats[clean_key] = {
            "db_key": db_key,
            "non_null": len(non_null_values),
            "coverage_pct": round(coverage_pct, 2),
            "distinct": distinct,
            "min": min_val,
            "max": max_val,
            **quality,
        }
    maturity_counts = {
        "core": sum(1 for meta in feature_stats.values() if meta.get("maturity_tier") == "core"),
        "research": sum(1 for meta in feature_stats.values() if meta.get("maturity_tier") == "research"),
        "blocked": sum(1 for meta in feature_stats.values() if meta.get("maturity_tier") == "blocked"),
    }
    return {
        "days": days,
        "rows": total_rows,
        "maturity_counts": maturity_counts,
        "features": feature_stats,
    }


# ─── API Endpoints ───
@router.get("/status")
async def api_status():
    cfg = get_config()
    db = get_db()
    symbol = cfg.get("trading", {}).get("symbol", "BTCUSDT")
    execution = ExecutionService(cfg, db_session=db)
    account_snapshot = AccountSyncService(cfg).snapshot(symbol=symbol)
    execution_summary = execution.execution_summary()
    try:
        confidence_result = get_confidence_prediction()
        if hasattr(confidence_result, "__await__"):
            confidence_payload = await confidence_result
        else:
            confidence_payload = confidence_result
    except Exception:
        confidence_payload = None
    live_runtime_truth = _build_live_runtime_closure_surface(confidence_payload if isinstance(confidence_payload, dict) else None)
    execution_summary["live_runtime_truth"] = live_runtime_truth
    account_snapshot["live_runtime_truth"] = live_runtime_truth
    if live_runtime_truth.get("runtime_closure_state") == "capacity_opened_signal_hold":
        execution_summary["operator_message"] = live_runtime_truth["runtime_closure_summary"]
        account_snapshot["operator_message"] = f"account snapshot 已刷新；{live_runtime_truth['runtime_closure_summary']}"
    status_payload = {
        "automation": is_automation_enabled(),
        "dry_run": cfg.get("trading", {}).get("dry_run", True),
        "symbol": symbol,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "execution": execution_summary,
        "account": account_snapshot,
        "execution_reconciliation": _build_execution_reconciliation_summary(
            db,
            symbol,
            account_snapshot,
            execution_summary,
        ),
        "execution_metadata_smoke": _ensure_execution_metadata_smoke_governance(cfg, symbol),
        "execution_surface_contract": _build_execution_surface_contract(),
        "raw_continuity": get_runtime_status("raw_continuity", None),
        "feature_continuity": get_runtime_status("feature_continuity", None),
    }
    status_payload["execution_surface_contract"]["live_runtime_truth"] = live_runtime_truth
    if live_runtime_truth.get("runtime_closure_state") == "capacity_opened_signal_hold":
        status_payload["execution_surface_contract"]["operator_message"] = f"{status_payload['execution_surface_contract']['operator_message']} 另外，{live_runtime_truth['runtime_closure_summary']}"
    return status_payload


@router.get("/features/status")
async def api_features_status():
    """返回全部 22 特徵的即時狀態"""
    engine = get_engine()
    scores = engine.calculate_all_scores()
    full_data = engine.get_latest_full_data()
    advice = engine.generate_advice(scores)
    return {
        "features": engine.get_features_status(),
        "scores": scores,
        "raw": full_data.get("raw", {}),
        "recommendation": advice,
    }


@router.get("/features/config")
async def api_features_cfg():
    return get_engine().get_config()


@router.put("/features/config")
async def api_put_features(update: SenseConfigUpdate):
    engine = get_engine()
    updates = {}
    if update.enabled is not None:
        updates["enabled"] = update.enabled
    if update.weight is not None:
        updates["weight"] = update.weight
    ok = engine.update_feature_config(update.sense, update.module, updates)
    if not ok:
        raise HTTPException(status_code=400, detail="無效特徵或模組")
    return {"config": engine.get_config(), "scores": engine.calculate_all_scores()}


@router.get("/senses")
async def api_senses():
    """返回最新特徵（多特徵）分數 — 前端雷達圖 + 價格 × 特徵 overlay 用"""
    engine = get_engine()
    scores = engine.calculate_all_scores()
    full_data = engine.get_latest_full_data()
    raw = full_data.get("raw", {})
    return {
        "senses": scores,  # 前端欄位名稱 (向後相容)
        "scores": scores,
        "raw": raw,
        "recommendation": engine.generate_advice(scores),
    }


@router.get("/senses/config")
async def api_senses_cfg():
    """返回特徵配置（舊路由，向後相容）"""
    return get_engine().get_config()


@router.put("/senses/config")
async def api_put_senses_cfg(update: SenseConfigUpdate):
    """更新特徵配置（舊路由，向後相容）"""
    engine = get_engine()
    updates = {}
    if update.enabled is not None:
        updates["enabled"] = update.enabled
    if update.weight is not None:
        updates["weight"] = update.weight
    ok = engine.update_feature_config(update.sense, update.module, updates)
    if not ok:
        raise HTTPException(status_code=400, detail="無效特徵或模組")
    return {"config": engine.get_config(), "scores": engine.calculate_all_scores()}


@router.get("/recommendation")
async def api_rec():
    engine = get_engine()
    return engine.generate_advice(engine.calculate_all_scores())


@router.get("/chart/klines")
async def api_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 500,
    since: Optional[int] = Query(default=None),
    until: Optional[int] = Query(default=None),
    append_after: Optional[int] = Query(default=None),
):
    since = since if isinstance(since, (int, float)) else None
    until = until if isinstance(until, (int, float)) else None
    append_after = append_after if isinstance(append_after, (int, float)) else None
    cache_key = _build_cache_key("chart_klines", symbol, interval, limit, since or "", until or "", append_after or "")
    with _KLINE_CACHE_LOCK:
        cached = _KLINE_RESPONSE_CACHE.get(cache_key)
        if cached and (time.time() - cached.get("updated_at", 0.0) < 180):
            return cached["payload"]
    try:
        interval_ms = _interval_ms(interval)
        fetch_limit = max(min(limit, 1000), 50)
        fetch_since = since
        trim_after_time = append_after
        if append_after is not None:
            warmup_window_ms = interval_ms * _KLINE_INCREMENTAL_WARMUP_CANDLES
            warmup_since = max(0, append_after - warmup_window_ms)
            fetch_since = max(since or 0, warmup_since) if since is not None else warmup_since
            if until is not None and until > fetch_since:
                incremental_span = max(until - fetch_since, interval_ms)
                fetch_limit = max(fetch_limit, min(1000, math.ceil(incremental_span / interval_ms) + 5))

        exchange = ccxt.binance()
        if until is not None and fetch_since is not None:
            target_bars = max(1, math.ceil((until - fetch_since) / interval_ms) + 1)
        else:
            target_bars = max(1, fetch_limit)
        ohlcv: List[List[float]] = []
        cursor_since = fetch_since
        remaining = target_bars
        while remaining > 0:
            page_limit = max(50, min(1000, remaining))
            page = exchange.fetch_ohlcv(symbol, interval, since=cursor_since, limit=page_limit)
            if not page:
                break
            if until is not None:
                page = [row for row in page if row[0] <= until]
            if not page:
                break
            ohlcv.extend(page)
            if len(page) < page_limit:
                break
            last_open_time = int(page[-1][0])
            next_since = last_open_time + interval_ms
            if cursor_since is not None and next_since <= cursor_since:
                break
            cursor_since = next_since
            remaining = target_bars - len(ohlcv)
            if until is not None and cursor_since > until:
                break
        if ohlcv:
            deduped = {int(row[0]): row for row in ohlcv}
            ohlcv = [deduped[key] for key in sorted(deduped)]
        payload = _build_chart_payload(symbol, interval, ohlcv)
        if trim_after_time is not None:
            trim_index = 0
            while trim_index < len(ohlcv) and int(ohlcv[trim_index][0]) <= trim_after_time:
                trim_index += 1
            payload = _slice_chart_payload(payload, trim_index)
            payload["incremental"] = True
            payload["append_after"] = int(trim_after_time / 1000)
        else:
            payload["incremental"] = False
        with _KLINE_CACHE_LOCK:
            _KLINE_RESPONSE_CACHE[cache_key] = {"updated_at": time.time(), "payload": payload}
        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest")
async def api_backtest(days: int = Query(default=30, ge=1, le=365), initial_capital: float = Query(default=10000.0, ge=100.0, le=10000000.0)):
    try:
        from model import predictor as predictor_module

        symbol = "BTCUSDT"
        interval = "4h" if days <= 7 else "1d"
        limit = max(int(days * 6), 20)
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, interval, limit=limit)
        if not ohlcv or len(ohlcv) < 20:
            return {"error": "數據不足", "total_trades": 0,
                    "equity_curve": [], "trades": []}
        db = get_db()
        start = datetime.fromtimestamp(ohlcv[0][0] / 1000)
        features = db.query(FeaturesNormalized).filter(
            FeaturesNormalized.timestamp >= start
        ).order_by(FeaturesNormalized.timestamp).all()
        feat_map = {}
        for f in features:
            feat_map[int(f.timestamp.timestamp())] = f
        initial = float(initial_capital)
        equity = initial
        position = 0.0
        entry_price = 0.0
        entry_timestamp = None
        open_trade_profile: Dict[str, Any] = {}
        equity_curve = []
        trades = []
        threshold = 0.55
        exit_thresh = 0.48
        stop_p = 0.03
        canonical_core_cols = [
            "feat_eye", "feat_ear", "feat_nose", "feat_tongue",
            "feat_body", "feat_pulse", "feat_aura", "feat_mind",
        ]
        for bar in ohlcv:
            t, o, h, l, c = bar[0], bar[1], bar[2], bar[3], bar[4]
            dt = int(t / 1000)
            price = c
            feat = None
            min_diff = 999999
            for ft, f in feat_map.items():
                d = abs(ft - dt)
                if d < min_diff:
                    min_diff = d
                    feat = f
            if not feat or min_diff > 2 * 3600:
                equity_curve.append({
                    "timestamp": datetime.fromtimestamp(dt).isoformat() + "Z",
                    "equity": round(equity + (position * price if position else 0), 2)})
                continue

            feature_values = {col: getattr(feat, col, None) for col in canonical_core_cols}
            feature_values.update({
                "feat_4h_bias50": getattr(feat, "feat_4h_bias50", None),
                "feat_4h_bias200": getattr(feat, "feat_4h_bias200", None),
                "regime_label": getattr(feat, "regime_label", None),
            })
            normed = [
                normalize_for_api(feature_values[col], col)
                for col in canonical_core_cols
                if normalize_for_api(feature_values[col], col) is not None
            ]
            if not normed:
                equity_curve.append({
                    "timestamp": datetime.fromtimestamp(dt).isoformat() + "Z",
                    "equity": round(equity + (position * price if position else 0), 2)})
                continue

            score = sum(normed) / len(normed)
            decision_profile = predictor_module._build_live_decision_profile(feature_values)

            if position > 0 and price <= entry_price * (1 - stop_p):
                pnl = (price - entry_price) * position
                equity += pnl
                trades.append({
                    "timestamp": datetime.fromtimestamp(dt).isoformat() + "Z",
                    "entry_timestamp": entry_timestamp,
                    "action": "sell",
                    "price": round(price, 2),
                    "amount": position,
                    "pnl": round(pnl, 2),
                    "reason": "stop_loss",
                    **open_trade_profile,
                })
                position = 0
                entry_timestamp = None
                open_trade_profile = {}

            can_enter = (
                position == 0
                and score >= threshold
                and (decision_profile.get("allowed_layers") or 0) > 0
                and decision_profile.get("regime_gate") != "BLOCK"
            )
            if can_enter:
                position = (equity * 0.05) / price
                entry_price = price
                entry_timestamp = datetime.fromtimestamp(dt).isoformat() + "Z"
                open_trade_profile = {
                    "regime_gate": decision_profile.get("regime_gate"),
                    "entry_quality": decision_profile.get("entry_quality"),
                    "entry_quality_label": decision_profile.get("entry_quality_label"),
                    "allowed_layers": decision_profile.get("allowed_layers"),
                }
            elif score < exit_thresh and position > 0:
                pnl = (price - entry_price) * position
                equity += pnl
                trades.append({
                    "timestamp": datetime.fromtimestamp(dt).isoformat() + "Z",
                    "entry_timestamp": entry_timestamp,
                    "action": "sell",
                    "price": round(price, 2),
                    "amount": position,
                    "pnl": round(pnl, 2),
                    "reason": "signal_exit",
                    **open_trade_profile,
                })
                position = 0
                entry_timestamp = None
                open_trade_profile = {}
            equity_curve.append({
                "timestamp": datetime.fromtimestamp(dt).isoformat() + "Z",
                "equity": round(equity + (position * price if position else 0), 2)})
        if position > 0:
            pnl = (c - entry_price) * position
            equity += pnl
            trades.append({
                "timestamp": datetime.fromtimestamp(ohlcv[-1][0] / 1000).isoformat() + "Z",
                "entry_timestamp": entry_timestamp,
                "action": "sell",
                "price": round(c, 2),
                "amount": position,
                "pnl": round(pnl, 2),
                "reason": "end",
                **open_trade_profile,
            })
        win = [t for t in trades if t["pnl"] > 0]
        aw = sum(t["pnl"] for t in win) / max(len(win), 1)
        al = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0)) / max(len(trades) - len(win), 1)
        decision_profile_summary = _compute_decision_profile(trades)
        decision_quality_profile = _compute_strategy_decision_quality_profile(trades, db=db, horizon_minutes=1440)
        return {
            "final_equity": round(equity, 2),
            "initial_capital": initial,
            "total_trades": len(trades),
            "win_rate": round(len(win) / max(len(trades), 1) * 100, 1),
            "profit_loss_ratio": round(aw / max(al, 0.01), 2),
            "max_drawdown": round(_calc_max_dd([e["equity"] for e in equity_curve]) * 100, 2),
            "total_return": round((equity - initial) / initial * 100, 2),
            "equity_curve": equity_curve[-200:],
            "trades": trades[-50:],
            **decision_profile_summary,
            **decision_quality_profile,
            "decision_contract": _strategy_decision_contract_meta(horizon_minutes=1440),
        }
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "total_trades": 0, "equity_curve": [], "trades": []}


@router.post("/trade")
async def api_trade(req: TradeRequest):
    """Execution endpoint for the web UI. Supports paper / live_canary / live via ExecutionService."""
    side = (req.side or "").lower().strip()
    if side not in {"buy", "reduce", "sell"}:
        raise HTTPException(status_code=400, detail="side must be one of: buy, reduce, sell")

    cfg = get_config()
    db = get_db()
    service = ExecutionService(cfg, db_session=db)
    reduce_only = side == "reduce" and service.venue_default_type() != "spot"
    try:
        result = service.submit_order(
            symbol=req.symbol,
            side="sell" if reduce_only else "buy",
            order_type="market",
            qty=req.qty,
            venue=(cfg.get("execution", {}) or {}).get("venue") or cfg.get("trading", {}).get("venue"),
            reduce_only=reduce_only,
            reason=f"manual_api:{side}",
            model_confidence=0.0,
        )
    except Exception as exc:
        payload = exc.to_payload() if hasattr(exc, "to_payload") else {"message": str(exc)}
        raise HTTPException(status_code=400, detail=payload)

    order = result.get("order") or {}
    action_text = {
        "buy": "spot buy",
        "reduce": "position reduce",
        "sell": "position close",
    }[side]
    return {
        "success": True,
        "dry_run": result.get("dry_run", True),
        "message": f"{action_text} accepted",
        "venue": result.get("venue"),
        "order_id": order.get("id"),
        "order": order,
        "guardrails": result.get("guardrails"),
    }


@router.get("/features")
async def api_features(days: int = Query(default=7, ge=1, le=90)):
    """返回全部 22+ 特徵的時間序列資料（正確 key mapping + ECDF 正規化）"""
    db = get_db()
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(FeaturesNormalized)
        .filter(FeaturesNormalized.timestamp >= since)
        .order_by(FeaturesNormalized.timestamp)
        .all()
    )
    result = []
    for r in rows:
        obj = {"timestamp": _iso_utc_timestamp(r.timestamp)}
        for db_key, clean_key in FEATURE_KEY_MAP.items():
            raw_val = getattr(r, db_key, None)
            obj[clean_key] = normalize_for_api(raw_val, db_key)
            obj[f"raw_{clean_key}"] = raw_val
        result.append(obj)
    return result


@router.get("/features/coverage")
async def api_features_coverage(days: int = Query(default=90, ge=1, le=365)):
    """Coverage/distinctness audit for feature history chart rendering."""
    db = get_db()
    return _compute_feature_coverage(db, days=days)


@router.get("/model/stats")
async def api_model_stats():
    """返回模型準確率、IC 值等統計資訊，供 Web 顯示"""
    import os, pickle, numpy as np
    from model.train import FEATURE_COLS
    from model.predictor import BASE_FEATURE_COLS as PREDICTOR_FEATURES
    from model.predictor import MODEL_PATH
    from database.models import Labels, FeaturesNormalized
    from sqlalchemy import text

    db = get_db()
    all_features = PREDICTOR_FEATURES
    stats = {
        "model_loaded": False, "sample_count": 0,
        "label_distribution": {}, "cv_accuracy": None,
        "feature_importance": {}, "ic_values": {},
        "model_params": {}, "feature_count": len(all_features),
        "signal_4h": _get_4h_signal(),
    }
    try:
        total = db.query(Labels).count()
        stats["sample_count"] = total
        dist = db.execute(text(
            "SELECT label, COUNT(*) as cnt FROM labels GROUP BY label"
        )).fetchall()
        stats["label_distribution"] = {str(r[0]): r[1] for r in dist}
    except Exception as e:
        logger.error(f"Stats label error: {e}")
    try:
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            stats["model_loaded"] = True
            if hasattr(model, "feature_importances_"):
                imp = dict(zip(FEATURE_COLS, model.feature_importances_.tolist()))
                stats["feature_importance"] = {
                    k: round(v, 4) for k, v in sorted(imp.items(), key=lambda x: -x[1])}
            if hasattr(model, "get_params"):
                p = model.get_params()
                stats["model_params"] = {
                    k: p.get(k) for k in ["n_estimators", "max_depth",
                                           "reg_alpha", "reg_lambda"]}
    except Exception as e:
        logger.error(f"Stats model error: {e}")
    try:
        ic_path = os.path.join(os.path.dirname(MODEL_PATH), "ic_signs.json")
        if os.path.exists(ic_path):
            with open(ic_path) as f:
                ic_data = json.load(f)
            for src_key in ["ic_global", "ic_map", "core_ic_summary", "tw_ic_summary"]:
                if src_key in ic_data:
                    for feat, val in ic_data[src_key].items():
                        clean = feat.replace("feat_", "").replace("4h_", "4h_")
                        stats["ic_values"][clean] = round(float(val), 4)
    except Exception as e:
        logger.error(f"Stats IC error: {e}")
    return stats


@router.post("/backtest/run")
async def api_run_backtest(days: int = Query(default=30)):
    return await api_backtest(days=days)


@router.get("/predict/confidence")
async def get_confidence_prediction():
    """返回模型信心分層預測"""
    from model.predictor import predict, load_predictor
    from database.models import init_db
    from config import load_config
    cfg = load_config()
    session = init_db(cfg["database"]["url"])
    try:
        predictor, regime_models = load_predictor()
        result = predict(session, predictor, regime_models)
    finally:
        session.close()
    if result is None:
        return {
            "error": "prediction failed",
            "confidence": 0.5,
            "signal": "HOLD",
            "confidence_level": "LOW",
            "should_trade": False,
            "regime_gate": None,
            "entry_quality": None,
            "entry_quality_label": None,
            "allowed_layers": None,
            "decision_quality_horizon_minutes": 1440,
            "decision_quality_calibration_scope": None,
            "decision_quality_sample_size": 0,
            "decision_quality_reference_from": None,
            "expected_win_rate": None,
            "expected_pyramid_pnl": None,
            "expected_pyramid_quality": None,
            "expected_drawdown_penalty": None,
            "expected_time_underwater": None,
            "decision_quality_score": None,
            "decision_quality_label": None,
            "decision_profile_version": "phase16_baseline_v2",
        }
    return _enrich_confidence_with_q15_support_audit(result)


# ═══════════════════════════════════════════════
# Strategy Lab API
# ═══════════════════════════════════════════════

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
MODEL_LB_CACHE_PATH = Path('/tmp/polytrader_model_leaderboard_cache.json')
MODEL_LB_CACHE_TTL_SEC = 60 * 15
MODEL_LB_STALE_SEC = 60 * 60 * 6
MODEL_LB_OVERFIT_GAP_THRESHOLD = 0.12
MODEL_LB_HARD_TRAIN_ACC_CAP = 0.85
_MODEL_LB_LOCK = threading.Lock()
_MODEL_LB_CACHE: Dict[str, Any] = {
    "payload": None,
    "updated_at": 0.0,
    "refreshing": False,
    "error": None,
}


def _serialize_model_scores(results, overfit_gap_threshold: float, hard_train_acc_cap: float) -> List[Dict[str, Any]]:
    leaderboard = []
    for r in results:
        fold_data = []
        for f in r.folds:
            fold_data.append({
                "fold": int(f.fold),
                "train_start": str(f.train_start),
                "train_end": str(f.train_end),
                "test_start": str(f.test_start),
                "test_end": str(f.test_end),
                "roi": float(round(f.roi, 4)),
                "win_rate": float(round(f.win_rate, 4)),
                "trades": int(f.total_trades),
                "max_dd": float(round(f.max_drawdown, 4)),
                "profit_factor": float(round(f.profit_factor, 4)),
                "avg_decision_quality_score": float(round(getattr(f, "avg_decision_quality_score", 0.0), 4)),
                "avg_expected_win_rate": float(round(getattr(f, "avg_expected_win_rate", 0.0), 4)),
                "avg_expected_pyramid_quality": float(round(getattr(f, "avg_expected_pyramid_quality", 0.0), 4)),
                "avg_expected_drawdown_penalty": float(round(getattr(f, "avg_expected_drawdown_penalty", 0.0), 4)),
                "avg_expected_time_underwater": float(round(getattr(f, "avg_expected_time_underwater", 0.0), 4)),
                "deployment_profile": str(getattr(f, "deployment_profile", "standard")),
                "feature_profile": str(getattr(f, "feature_profile", "current_full")),
                "feature_profile_source": str(getattr(f, "feature_profile_source", "code_default")),
            })
        is_overfit = bool(r.train_test_gap > overfit_gap_threshold or r.train_accuracy > hard_train_acc_cap)
        tier_meta = _model_tier_for_name(str(r.model_name))
        leaderboard.append({
            "model_name": str(r.model_name),
            "deployment_profile": str(getattr(r, "deployment_profile", "standard")),
            "feature_profile": str(getattr(r, "feature_profile", "current_full")),
            "feature_profile_source": str(getattr(r, "feature_profile_source", "code_default")),
            "feature_profile_support_cohort": (getattr(r, "feature_profile_meta", {}) or {}).get("support_cohort"),
            "feature_profile_support_rows": (getattr(r, "feature_profile_meta", {}) or {}).get("support_rows"),
            "feature_profile_exact_live_bucket_rows": (getattr(r, "feature_profile_meta", {}) or {}).get("exact_live_bucket_rows"),
            **tier_meta,
            "avg_roi": float(round(r.avg_roi, 4)),
            "avg_win_rate": float(round(r.avg_win_rate, 4)),
            "avg_trades": int(r.avg_trades),
            "avg_max_dd": float(round(r.avg_max_drawdown, 4)),
            "avg_entry_quality": float(round(getattr(r, "avg_entry_quality", 0.0), 4)),
            "avg_allowed_layers": float(round(getattr(r, "avg_allowed_layers", 0.0), 4)),
            "avg_trade_quality": float(round(getattr(r, "avg_trade_quality", 0.0), 4)),
            "avg_decision_quality_score": float(round(getattr(r, "avg_decision_quality_score", 0.0), 4)),
            "avg_expected_win_rate": float(round(getattr(r, "avg_expected_win_rate", 0.0), 4)),
            "avg_expected_pyramid_quality": float(round(getattr(r, "avg_expected_pyramid_quality", 0.0), 4)),
            "avg_expected_drawdown_penalty": float(round(getattr(r, "avg_expected_drawdown_penalty", 0.0), 4)),
            "avg_expected_time_underwater": float(round(getattr(r, "avg_expected_time_underwater", 0.0), 4)),
            "regime_stability_score": float(round(getattr(r, "regime_stability_score", 0.0), 4)),
            "trade_count_score": float(round(getattr(r, "trade_count_score", 0.0), 4)),
            "roi_score": float(round(getattr(r, "roi_score", 0.0), 4)),
            "max_drawdown_score": float(round(getattr(r, "max_drawdown_score", 0.0), 4)),
            "profit_factor_score": float(round(getattr(r, "profit_factor_score", 0.0), 4)),
            "time_underwater_score": float(round(getattr(r, "time_underwater_score", 0.0), 4)),
            "decision_quality_component": float(round(getattr(r, "decision_quality_component", 0.0), 4)),
            "reliability_score": float(round(getattr(r, "reliability_score", 0.0), 4)),
            "return_power_score": float(round(getattr(r, "return_power_score", 0.0), 4)),
            "risk_control_score": float(round(getattr(r, "risk_control_score", 0.0), 4)),
            "capital_efficiency_score": float(round(getattr(r, "capital_efficiency_score", 0.0), 4)),
            "overall_score": float(round(getattr(r, "overall_score", getattr(r, "composite_score", 0.0)), 4)),
            "overfit_penalty": float(round(getattr(r, "overfit_penalty", 0.0), 4)),
            "std_roi": float(round(r.std_roi, 4)),
            "profit_factor": float(round(r.avg_profit_factor, 4)),
            "train_acc": float(round(r.train_accuracy, 4)),
            "test_acc": float(round(r.test_accuracy, 4)),
            "train_test_gap": float(round(r.train_test_gap, 4)),
            "composite": float(round(r.composite_score, 4)),
            "is_overfit": bool(is_overfit),
            "overfit_reason": "train_test_gap" if r.train_test_gap > overfit_gap_threshold else ("train_accuracy_cap" if r.train_accuracy > hard_train_acc_cap else None),
            "folds": fold_data,
        })
    return leaderboard


def _model_tier_for_name(model_name: str) -> Dict[str, str]:
    normalized = str(model_name or "").strip().lower()
    if normalized in {"rule_baseline", "random_forest", "xgboost", "logistic_regression"}:
        return {
            "model_tier": "core",
            "model_tier_label": "核心模型",
            "model_tier_reason": "最符合目前 Poly-Trader 的多特徵、低頻高信念、可解釋與穩定度優先主線。",
        }
    if normalized in {"lightgbm", "catboost", "ensemble"}:
        return {
            "model_tier": "control",
            "model_tier_label": "對照模型",
            "model_tier_reason": "適合作為 XGBoost / RandomForest 的對照與補充，不是當前第一主線。",
        }
    if normalized in {"mlp", "svm"}:
        return {
            "model_tier": "research",
            "model_tier_label": "研究模型",
            "model_tier_reason": "目前保留在研究層，用來觀察是否有額外訊號，不建議當前主線優先投入。",
        }
    return {
        "model_tier": "control",
        "model_tier_label": "對照模型",
        "model_tier_reason": "未明確歸類，預設先放在對照層，避免過早升為主線。",
    }


def _summarize_target_candidates(df, overfit_gap_threshold: float, hard_train_acc_cap: float) -> List[Dict[str, Any]]:
    from backtesting.model_leaderboard import ModelLeaderboard

    summaries = []
    candidate_models = ["rule_baseline", "logistic_regression", "xgboost", "catboost"]
    target_specs = [
        ("simulated_pyramid_win", "Simulated Pyramid"),
        ("label_spot_long_win", "Path-aware TP/DD"),
    ]
    for target_col, label in target_specs:
        if target_col not in df.columns:
            continue
        target_df = df.dropna(subset=[target_col]).copy()
        if target_df.empty:
            continue
        target_df[target_col] = target_df[target_col].fillna(0).astype(int)
        lb = ModelLeaderboard(target_df, target_col=target_col)
        results = lb.run_all_models(candidate_models)
        serialized = _serialize_model_scores(results, overfit_gap_threshold, hard_train_acc_cap)
        non_overfit = [row for row in serialized if not row["is_overfit"]]
        best = non_overfit[0] if non_overfit else (serialized[0] if serialized else None)
        is_canonical = target_col == "simulated_pyramid_win"
        summaries.append({
            "target_col": target_col,
            "label": label,
            "is_canonical": is_canonical,
            "usage_note": (
                "主訓練 / 主排行榜 target"
                if is_canonical
                else "僅供 path-aware 比較診斷，不作主 target"
            ),
            "samples": int(len(target_df)),
            "positive_ratio": float(round(target_df[target_col].mean(), 4)),
            "best_model": best,
            "models_evaluated": len(serialized),
        })
    summaries.sort(key=lambda row: (not row.get("is_canonical", False), row["target_col"]))
    return summaries


def _load_model_leaderboard_cache_payload() -> Optional[Dict[str, Any]]:
    if not MODEL_LB_CACHE_PATH.exists():
        return None
    try:
        payload = json.loads(MODEL_LB_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _write_model_leaderboard_cache_payload(payload: Dict[str, Any]) -> None:
    try:
        MODEL_LB_CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning(f"failed to write model leaderboard cache: {exc}")


def _compute_rank_deltas(current_rows: List[Dict[str, Any]], previous_rows: List[Dict[str, Any]]) -> None:
    previous_rank_by_model = {
        str(row.get("model_name")): idx
        for idx, row in enumerate(previous_rows or [], start=1)
        if row.get("model_name")
    }
    for idx, row in enumerate(current_rows or [], start=1):
        model_name = str(row.get("model_name") or "")
        previous_rank = previous_rank_by_model.get(model_name)
        row["rank"] = idx
        row["previous_rank"] = previous_rank
        row["rank_delta"] = 0 if previous_rank is None else int(previous_rank - idx)


def _snapshot_history_from_payload(payload: Optional[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    history = payload.get("snapshot_history")
    if isinstance(history, list):
        return [item for item in history if isinstance(item, dict)][:limit]
    return []


def _build_model_leaderboard_payload(force_refresh: bool = False) -> Dict[str, Any]:
    cached_payload = None
    cached_updated_at = 0.0
    with _MODEL_LB_LOCK:
        if not force_refresh and isinstance(_MODEL_LB_CACHE.get("payload"), dict):
            cached_payload = _MODEL_LB_CACHE.get("payload")
            cached_updated_at = float(_MODEL_LB_CACHE.get("updated_at") or 0.0)
            if time.time() - cached_updated_at <= MODEL_LB_CACHE_TTL_SEC:
                return cached_payload

    file_cache_payload = _load_model_leaderboard_cache_payload()
    if file_cache_payload is not None:
        try:
            cache_age = max(time.time() - MODEL_LB_CACHE_PATH.stat().st_mtime, 0.0)
        except Exception:
            cache_age = float("inf")
        if not force_refresh and cache_age <= MODEL_LB_CACHE_TTL_SEC:
            with _MODEL_LB_LOCK:
                _MODEL_LB_CACHE["payload"] = file_cache_payload
                _MODEL_LB_CACHE["updated_at"] = time.time()
                _MODEL_LB_CACHE["error"] = None
            return file_cache_payload

    previous_payload = cached_payload or file_cache_payload or {}
    previous_rows = previous_payload.get("leaderboard") if isinstance(previous_payload, dict) else []
    previous_rows = previous_rows if isinstance(previous_rows, list) else []
    previous_history = _snapshot_history_from_payload(previous_payload)

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    target_col = "simulated_pyramid_win"
    leaderboard: List[Dict[str, Any]] = []
    quadrant_points: List[Dict[str, Any]] = []
    skipped_models: List[Dict[str, Any]] = []
    target_candidates: List[Dict[str, Any]] = []

    try:
        df = load_model_leaderboard_frame(DB_PATH)
        if not df.empty:
            if target_col not in df.columns and "label_spot_long_win" in df.columns:
                target_col = "label_spot_long_win"
            target_df = df.dropna(subset=[target_col]).copy() if target_col in df.columns else df.copy()
            if target_col in target_df.columns:
                target_df[target_col] = target_df[target_col].fillna(0).astype(int)

            from backtesting.model_leaderboard import ModelLeaderboard

            leaderboard_runner = ModelLeaderboard(target_df, target_col=target_col)
            model_names = list(getattr(leaderboard_runner, "SUPPORTED_MODELS", []) or [])
            results = leaderboard_runner.run_all_models(model_names or None)
            leaderboard = _serialize_model_scores(
                results,
                MODEL_LB_OVERFIT_GAP_THRESHOLD,
                MODEL_LB_HARD_TRAIN_ACC_CAP,
            )

            model_statuses = getattr(leaderboard_runner, "last_model_statuses", {}) or {}
            for row in leaderboard:
                status = model_statuses.get(row.get("model_name"), {}) if isinstance(model_statuses, dict) else {}
                row["selected_deployment_profile"] = status.get("selected_deployment_profile", row.get("deployment_profile"))
                row["selected_feature_profile"] = status.get("selected_feature_profile", row.get("feature_profile"))
                row["selected_feature_profile_source"] = status.get("selected_feature_profile_source", row.get("feature_profile_source"))
                row["selected_feature_profile_blocker_applied"] = bool(status.get("selected_feature_profile_blocker_applied", False))
                row["selected_feature_profile_blocker_reason"] = status.get("selected_feature_profile_blocker_reason")
                row["deployment_profiles_evaluated"] = list(status.get("deployment_profiles_evaluated") or [row.get("deployment_profile")])
                row["feature_profiles_evaluated"] = list(status.get("feature_profiles_evaluated") or [row.get("feature_profile")])
                row["feature_profile_candidate_diagnostics"] = list(status.get("feature_profile_candidate_diagnostics") or [])

            _compute_rank_deltas(leaderboard, previous_rows)
            quadrant_points = [
                {
                    "model_name": row.get("model_name"),
                    "x": row.get("avg_roi"),
                    "y": row.get("avg_decision_quality_score"),
                    "overall_score": row.get("overall_score"),
                    "model_tier": row.get("model_tier"),
                }
                for row in leaderboard
            ]

            if isinstance(model_statuses, dict):
                skipped_models = [
                    {
                        "model_name": model_name,
                        "status": status.get("status"),
                        "reason": status.get("reason"),
                        "detail": status.get("detail"),
                    }
                    for model_name, status in model_statuses.items()
                    if isinstance(status, dict) and status.get("status") != "ok"
                ]

            target_candidates = _summarize_target_candidates(
                df,
                MODEL_LB_OVERFIT_GAP_THRESHOLD,
                MODEL_LB_HARD_TRAIN_ACC_CAP,
            )
    except Exception as exc:
        logger.exception("failed_to_build_model_leaderboard_payload")
        if isinstance(previous_payload, dict) and previous_payload.get("leaderboard"):
            fallback_payload = dict(previous_payload)
            fallback_payload["generated_at"] = generated_at
            fallback_payload["cache_status"] = "stale_fallback_after_refresh_error"
            fallback_payload["error"] = str(exc)
            with _MODEL_LB_LOCK:
                _MODEL_LB_CACHE["payload"] = fallback_payload
                _MODEL_LB_CACHE["updated_at"] = time.time()
                _MODEL_LB_CACHE["error"] = str(exc)
            return fallback_payload
        raise

    snapshot_entry = {
        "created_at": generated_at,
        "target_col": target_col,
        "count": len(leaderboard),
        "top_model": leaderboard[0].get("model_name") if leaderboard else None,
        "selected_feature_profile": leaderboard[0].get("selected_feature_profile") if leaderboard else None,
        "selected_feature_profile_source": leaderboard[0].get("selected_feature_profile_source") if leaderboard else None,
    }
    snapshot_history = [snapshot_entry]
    snapshot_history.extend(
        item for item in previous_history
        if item.get("created_at") != generated_at
    )
    snapshot_history = snapshot_history[:10]

    payload = {
        "generated_at": generated_at,
        "target_col": target_col,
        "count": len(leaderboard),
        "leaderboard": leaderboard,
        "quadrant_points": quadrant_points,
        "snapshot_history": snapshot_history,
        "storage": {
            "canonical_store": f"sqlite:///{DB_PATH}",
            "cache_path": str(MODEL_LB_CACHE_PATH),
            "cache_ttl_sec": MODEL_LB_CACHE_TTL_SEC,
            "stale_after_sec": MODEL_LB_STALE_SEC,
        },
        "cache_status": "fresh",
        "overfit_gap_threshold": MODEL_LB_OVERFIT_GAP_THRESHOLD,
        "hard_train_acc_cap": MODEL_LB_HARD_TRAIN_ACC_CAP,
        "skipped_models": skipped_models,
        "target_candidates": target_candidates,
        "error": None,
    }

    _write_model_leaderboard_cache_payload(payload)
    with _MODEL_LB_LOCK:
        _MODEL_LB_CACHE["payload"] = payload
        _MODEL_LB_CACHE["updated_at"] = time.time()
        _MODEL_LB_CACHE["error"] = None
    return payload


def load_model_leaderboard_frame(db_path: str = DB_PATH):
    """Load leaderboard training frame using timestamp-nearest alignment.

    Exact SQL joins are too brittle for this project because historical rows can
    differ slightly in timestamp precision and symbol normalization. Training code
    already relies on nearest-timestamp merges; reuse the same idea here so the
    leaderboard reflects the real available data instead of collapsing to zero rows.
    """
    import sqlite3
    import pandas as pd

    conn = sqlite3.connect(db_path)
    try:
        feature_cols = {row[1] for row in conn.execute("PRAGMA table_info(features_normalized)").fetchall()}
        requested_feature_cols = [
            "feat_eye", "feat_ear", "feat_nose", "feat_tongue",
            "feat_body", "feat_pulse", "feat_aura", "feat_mind",
            "feat_vix", "feat_dxy",
            "feat_rsi14", "feat_macd_hist", "feat_atr_pct",
            "feat_vwap_dev", "feat_bb_pct_b", "feat_nw_width",
            "feat_nw_slope", "feat_adx", "feat_choppiness", "feat_donchian_pos",
            "feat_4h_bias50", "feat_4h_bias20", "feat_4h_bias200", "feat_4h_rsi14",
            "feat_4h_macd_hist", "feat_4h_bb_pct_b", "feat_4h_dist_bb_lower",
            "feat_4h_ma_order", "feat_4h_dist_swing_low", "feat_4h_vol_ratio",
        ]
        selected_feature_cols = [col for col in requested_feature_cols if col in feature_cols]
        features_select = ",\n                   ".join(["timestamp", *selected_feature_cols])
        features_df = pd.read_sql(
            f"""
            SELECT {features_select}
            FROM features_normalized
            WHERE feat_4h_bias50 IS NOT NULL
            ORDER BY timestamp
            """,
            conn,
        )
        raw_df = pd.read_sql(
            "SELECT timestamp, close_price FROM raw_market_data WHERE close_price IS NOT NULL ORDER BY timestamp",
            conn,
        )
        label_cols = {row[1] for row in conn.execute("PRAGMA table_info(labels)").fetchall()}
        primary_target = "simulated_pyramid_win" if "simulated_pyramid_win" in label_cols else "label_spot_long_win"
        required_label_cols = [col for col in ("label_spot_long_win", primary_target) if col in label_cols]
        optional_label_cols = [
            "label_spot_long_tp_hit",
            "label_spot_long_quality",
            "simulated_pyramid_pnl",
            "simulated_pyramid_quality",
            "simulated_pyramid_drawdown_penalty",
            "simulated_pyramid_time_underwater",
        ]
        selected_optional = [col for col in optional_label_cols if col in label_cols]
        labels_select = ", ".join(dict.fromkeys(["timestamp", *required_label_cols, *selected_optional]))
        label_not_null_clause = " OR ".join(f"{col} IS NOT NULL" for col in required_label_cols)
        labels_df = pd.read_sql(
            f"SELECT {labels_select} FROM labels WHERE horizon_minutes = 1440 AND ({label_not_null_clause}) ORDER BY timestamp",
            conn,
        )
    finally:
        conn.close()

    if features_df.empty or raw_df.empty or labels_df.empty:
        return pd.DataFrame()

    for df in (features_df, raw_df, labels_df):
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
        df.sort_values("timestamp", inplace=True)

    merged = pd.merge_asof(
        features_df,
        raw_df,
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("10min"),
    )
    merged = pd.merge_asof(
        merged,
        labels_df,
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("10min"),
    )
    merged = merged.dropna(subset=["close_price", primary_target]).reset_index(drop=True)
    return merged


def _get_4h_signal():
    """返回目前 4H 狀態摘要"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("""
        SELECT timestamp, feat_4h_bias50, feat_4h_dist_swing_low,
               feat_4h_rsi14, feat_4h_macd_hist, feat_4h_ma_order
        FROM features_normalized
        WHERE feat_4h_bias50 IS NOT NULL
        ORDER BY timestamp DESC LIMIT 1
    """).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "timestamp": str(row[0]),
        "bias50": float(row[1]) if row[1] else None,
        "dist_swing": float(row[2]) if row[2] else None,
        "rsi14": float(row[3]) if row[3] else None,
        "macd_hist": float(row[4]) if row[4] else None,
        "ma_order": float(row[5]) if row[5] else None,
    }


@lru_cache(maxsize=4)
def _load_strategy_data_cached(db_mtime_ns: int):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT f.timestamp, r.close_price,
               f.feat_4h_bias50, f.feat_4h_bias200,
               f.feat_nose, f.feat_pulse, f.feat_ear,
               COALESCE(f.regime_label, 'unknown') AS regime_label,
               f.feat_4h_bb_pct_b, f.feat_4h_dist_bb_lower, f.feat_4h_dist_swing_low,
               f.feat_local_bottom_score, f.feat_local_top_score
        FROM features_normalized f
        JOIN raw_market_data r ON r.timestamp = f.timestamp AND r.symbol = f.symbol
        WHERE f.feat_4h_bias50 IS NOT NULL AND r.close_price IS NOT NULL
        ORDER BY f.timestamp
    """).fetchall()
    conn.close()
    return rows


def _load_strategy_data():
    """載入回測用的完整資料（依 DB mtime 快取）。"""
    try:
        db_mtime_ns = Path(DB_PATH).stat().st_mtime_ns
    except FileNotFoundError:
        db_mtime_ns = 0
    return _load_strategy_data_cached(db_mtime_ns)


def _parse_backtest_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("T", " ")
    if normalized.endswith("Z"):
        normalized = normalized[:-1]
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            dt = datetime.strptime(normalized[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _strategy_data_range_summary(rows: List[Any]) -> Dict[str, Any]:
    if not rows:
        return {"start": None, "end": None, "count": 0, "span_days": 0.0}
    timestamps = [str(row[0]) for row in rows if row and row[0] is not None]
    start = _iso_utc_timestamp(timestamps[0]) if timestamps else None
    end = _iso_utc_timestamp(timestamps[-1]) if timestamps else None
    start_dt = _parse_backtest_timestamp(start)
    end_dt = _parse_backtest_timestamp(end)
    span_days = 0.0
    if start_dt and end_dt:
        span_days = max(0.0, round((end_dt - start_dt).total_seconds() / 86400.0, 2))
    return {"start": start, "end": end, "count": len(rows), "span_days": span_days}


def _filter_strategy_rows_by_backtest_range(
    rows: List[Any],
    *,
    start: Optional[Any] = None,
    end: Optional[Any] = None,
) -> tuple[List[Any], Dict[str, Any]]:
    available = _strategy_data_range_summary(rows)
    start_dt = _parse_backtest_timestamp(start)
    end_dt = _parse_backtest_timestamp(end)
    if start_dt and end_dt and start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    filtered: List[Any] = []
    for row in rows:
        row_dt = _parse_backtest_timestamp(row[0] if row else None)
        if row_dt is None:
            continue
        if start_dt and row_dt < start_dt:
            continue
        if end_dt and row_dt > end_dt:
            continue
        filtered.append(row)

    requested_start = _iso_utc_timestamp(start_dt) if start_dt else None
    requested_end = _iso_utc_timestamp(end_dt) if end_dt else None
    effective = _strategy_data_range_summary(filtered)
    available_start_dt = _parse_backtest_timestamp(available.get("start"))
    available_end_dt = _parse_backtest_timestamp(available.get("end"))
    requested_span_days = None
    if start_dt and end_dt:
        requested_span_days = round(max(0.0, (end_dt - start_dt).total_seconds() / 86400.0), 2)

    coverage_ok = True
    missing_start_days = 0.0
    missing_end_days = 0.0
    if start_dt and available_start_dt and start_dt < available_start_dt:
        coverage_ok = False
        missing_start_days = round((available_start_dt - start_dt).total_seconds() / 86400.0, 2)
    if end_dt and available_end_dt and end_dt > available_end_dt:
        coverage_ok = False
        missing_end_days = round((end_dt - available_end_dt).total_seconds() / 86400.0, 2)

    return filtered, {
        "requested_start": requested_start,
        "requested_end": requested_end,
        "requested_span_days": requested_span_days,
        "available": available,
        "effective": effective,
        "coverage_ok": coverage_ok,
        "backfill_required": not coverage_ok,
        "missing_start_days": missing_start_days,
        "missing_end_days": missing_end_days,
    }


def _summarize_trades(trades: List[Dict[str, Any]], initial_capital: float) -> Dict[str, Any]:
    total_pnl = float(sum(float(t.get("pnl", 0.0) or 0.0) for t in trades))
    wins = sum(1 for t in trades if float(t.get("pnl", 0.0) or 0.0) > 0)
    losses = max(len(trades) - wins, 0)
    gross_profit = sum(float(t.get("pnl", 0.0) or 0.0) for t in trades if float(t.get("pnl", 0.0) or 0.0) > 0)
    gross_loss = abs(sum(float(t.get("pnl", 0.0) or 0.0) for t in trades if float(t.get("pnl", 0.0) or 0.0) <= 0))
    return {
        "roi": round(total_pnl / initial_capital, 4) if initial_capital else None,
        "win_rate": round(wins / len(trades), 4) if trades else None,
        "total_pnl": round(total_pnl, 2),
        "profit_factor": round(gross_profit / max(gross_loss, 0.01), 4) if trades else None,
        "total_trades": len(trades),
        "wins": wins,
        "losses": losses,
    }


def _build_strategy_chart_context(timestamps: List[str]) -> Dict[str, Any]:
    if not timestamps:
        return {"symbol": "BTCUSDT", "interval": "4h", "start": None, "end": None, "limit": 300}
    return {
        "symbol": "BTCUSDT",
        "interval": "4h",
        "start": _iso_utc_timestamp(timestamps[0]),
        "end": _iso_utc_timestamp(timestamps[-1]),
        "limit": min(max(len(timestamps), 150), 1000),
    }


def _select_strategy_chart_payload(
    timestamps: List[str],
    equity_curve: List[Dict[str, Any]],
    trades: List[Dict[str, Any]],
    *,
    max_trades: int = 80,
    fallback_equity_points: int = 300,
) -> Dict[str, Any]:
    selected_trades = list(trades[-max_trades:]) if trades else []
    if not selected_trades:
        selected_equity = list(equity_curve[-fallback_equity_points:]) if equity_curve else []
        context_times = [str(point.get("timestamp")) for point in selected_equity if point.get("timestamp")]
        if not context_times:
            context_times = list(timestamps[-fallback_equity_points:]) if timestamps else []
        return {
            "equity_curve": selected_equity,
            "trades": selected_trades,
            "chart_context": _build_strategy_chart_context(context_times),
        }

    trade_window_points = []
    for trade in selected_trades:
        for key in ("entry_timestamp", "timestamp"):
            ts = trade.get(key)
            if ts:
                trade_window_points.append(str(ts))
    trade_window_points = sorted(trade_window_points)
    if not trade_window_points:
        selected_equity = list(equity_curve[-fallback_equity_points:]) if equity_curve else []
        context_times = [str(point.get("timestamp")) for point in selected_equity if point.get("timestamp")]
        return {
            "equity_curve": selected_equity,
            "trades": selected_trades,
            "chart_context": _build_strategy_chart_context(context_times),
        }

    window_start = _iso_utc_timestamp(trade_window_points[0])
    window_end = _iso_utc_timestamp(trade_window_points[-1])
    selected_equity = [
        point for point in equity_curve
        if point.get("timestamp")
        and (window_start is None or _iso_utc_timestamp(point.get("timestamp")) >= window_start)
        and (window_end is None or _iso_utc_timestamp(point.get("timestamp")) <= window_end)
    ]
    if not selected_equity:
        selected_equity = list(equity_curve[-fallback_equity_points:]) if equity_curve else []

    context_times = [str(point.get("timestamp")) for point in selected_equity if point.get("timestamp")]
    if not context_times:
        context_times = trade_window_points
    chart_context = _build_strategy_chart_context(context_times)
    if window_start is not None:
        chart_context["start"] = window_start
    if window_end is not None:
        chart_context["end"] = window_end
    chart_context["limit"] = min(max(len(context_times), 150), 1000) if context_times else 300
    return {
        "equity_curve": selected_equity,
        "trades": selected_trades,
        "chart_context": chart_context,
    }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _compute_chart_entry_quality(
    bias50_value: float,
    nose_value: float,
    pulse_value: float,
    ear_value: float,
    bb_pct_b_value: Optional[float] = None,
    dist_bb_lower_value: Optional[float] = None,
    dist_swing_low_value: Optional[float] = None,
) -> float:
    from backtesting import strategy_lab as strategy_lab_module

    return strategy_lab_module._compute_entry_quality(
        bias50_value,
        nose_value,
        pulse_value,
        ear_value,
        bb_pct_b_value,
        dist_bb_lower_value,
        dist_swing_low_value,
    )


def _build_strategy_score_series(
    timestamps: List[str],
    bias50: List[float],
    nose: List[float],
    pulse: List[float],
    ear: List[float],
    model_confidence: Optional[List[float]] = None,
    bb_pct_b_4h: Optional[List[float]] = None,
    dist_bb_lower_4h: Optional[List[float]] = None,
    dist_swing_low_4h: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for idx, timestamp in enumerate(timestamps):
        entry_quality = _compute_chart_entry_quality(
            bias50[idx] if idx < len(bias50) else 0.0,
            nose[idx] if idx < len(nose) else 0.5,
            pulse[idx] if idx < len(pulse) else 0.5,
            ear[idx] if idx < len(ear) else 0.0,
            bb_pct_b_4h[idx] if bb_pct_b_4h and idx < len(bb_pct_b_4h) else None,
            dist_bb_lower_4h[idx] if dist_bb_lower_4h and idx < len(dist_bb_lower_4h) else None,
            dist_swing_low_4h[idx] if dist_swing_low_4h and idx < len(dist_swing_low_4h) else None,
        )
        confidence = None
        if model_confidence is not None and idx < len(model_confidence):
            confidence = round(float(model_confidence[idx]), 4)
        composite_score = round((0.6 * confidence + 0.4 * entry_quality), 4) if confidence is not None else entry_quality
        points.append({
            "timestamp": timestamp,
            "entry_quality": entry_quality,
            "model_confidence": confidence,
            "score": composite_score,
        })
    return points


def _compute_blind_pyramid_benchmark(
    prices: List[float],
    timestamps: List[str],
    bias50: List[float],
    bias200: List[float],
    nose: List[float],
    pulse: List[float],
    ear: List[float],
    regimes: List[str],
    initial_capital: float,
    params: Dict[str, Any],
    bb_pct_b_4h: Optional[List[float]] = None,
    dist_bb_lower_4h: Optional[List[float]] = None,
    dist_swing_low_4h: Optional[List[float]] = None,
) -> Dict[str, Any]:
    from backtesting.strategy_lab import run_rule_backtest

    blind_params = json.loads(json.dumps(params or {}))
    blind_entry = blind_params.setdefault("entry", {})
    blind_entry["bias50_max"] = 999.0
    blind_entry["nose_max"] = 1.0
    blind_entry["pulse_min"] = 0.0
    blind_entry["regime_bias200_min"] = -999.0
    blind_result = run_rule_backtest(
        prices,
        timestamps,
        bias50,
        bias200,
        nose,
        pulse,
        ear,
        blind_params,
        initial_capital,
        regimes=regimes,
        bb_pct_b_4h=bb_pct_b_4h,
        dist_bb_lower_4h=dist_bb_lower_4h,
        dist_swing_low_4h=dist_swing_low_4h,
    )
    return {
        "label": "盲金字塔",
        **_summarize_trades(blind_result.trades, initial_capital),
    }


def _compute_backtest_benchmarks(
    prices: List[float],
    timestamps: List[str],
    bias50: List[float],
    bias200: List[float],
    nose: List[float],
    pulse: List[float],
    ear: List[float],
    regimes: List[str],
    initial_capital: float,
    params: Dict[str, Any],
    bb_pct_b_4h: Optional[List[float]] = None,
    dist_bb_lower_4h: Optional[List[float]] = None,
    dist_swing_low_4h: Optional[List[float]] = None,
) -> Dict[str, Any]:
    buy_hold_roi = 0.0
    if prices and prices[0]:
        buy_hold_roi = (prices[-1] - prices[0]) / prices[0]
    buy_hold_summary = {
        "label": "買入持有",
        "roi": round(buy_hold_roi, 4),
    }

    blind_future = _BENCHMARK_PROCESS_EXECUTOR.submit(
        _compute_blind_pyramid_benchmark,
        prices,
        timestamps,
        bias50,
        bias200,
        nose,
        pulse,
        ear,
        regimes,
        initial_capital,
        params,
        bb_pct_b_4h,
        dist_bb_lower_4h,
        dist_swing_low_4h,
    )
    try:
        blind_summary = blind_future.result(timeout=180)
    except Exception:
        logger.exception("Blind benchmark process failed; falling back to in-process execution")
        blind_summary = _compute_blind_pyramid_benchmark(
            prices,
            timestamps,
            bias50,
            bias200,
            nose,
            pulse,
            ear,
            regimes,
            initial_capital,
            params,
            bb_pct_b_4h=bb_pct_b_4h,
            dist_bb_lower_4h=dist_bb_lower_4h,
            dist_swing_low_4h=dist_swing_low_4h,
        )

    return {
        "buy_hold": buy_hold_summary,
        "blind_pyramid": blind_summary,
    }


def _compute_regime_breakdown(trades: List[Dict[str, Any]], initial_capital: float) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for trade in trades:
        regime = (trade.get("entry_regime") or "unknown").lower()
        bucket = grouped.setdefault(regime, {
            "regime": regime,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
        })
