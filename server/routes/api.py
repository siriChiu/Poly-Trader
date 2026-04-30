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
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, Body, Query, HTTPException, Request
import pandas as pd
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Callable, Tuple
from datetime import datetime, timedelta, timezone

from server.dependencies import (
    get_db,
    get_config,
    get_runtime_status,
    is_automation_enabled,
    set_automation_enabled,
    set_runtime_status,
)
from server.features_engine import ecdf_normalize, get_engine, normalize_feature
from server.live_pathology_summary import (
    build_live_pathology_patch_summary as shared_build_live_pathology_patch_summary,
    build_live_pathology_scope_summary as shared_build_live_pathology_scope_summary,
    load_bull_4h_pocket_ablation_summary as shared_load_bull_4h_pocket_ablation_summary,
)
from database.models import TradeHistory, RawEvent, RawMarketData, FeaturesNormalized, OrderLifecycleEvent
from model.runtime_closure import build_runtime_closure_state, build_runtime_closure_summary
from feature_engine.feature_history_policy import (
    FEATURE_KEY_MAP,
    assess_feature_quality,
    attach_forward_archive_meta,
    compute_raw_snapshot_stats,
    _compute_archive_window_coverage,
)
from execution.account_sync import AccountSyncService
from execution.console_overview import build_execution_overview
from execution.control_plane import (
    build_execution_control_plane_snapshot,
    build_execution_strategy_source_snapshot,
    get_execution_run_detail,
    pause_execution_run,
    start_execution_profile_run,
    stop_execution_run,
)
from execution.execution_service import ExecutionRejectError, ExecutionService
from execution.metadata_smoke import run_metadata_smoke
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = str(PROJECT_ROOT / "poly_trader.db")
MODEL_LB_CACHE_PATH = PROJECT_ROOT / "data" / "model_leaderboard_cache.json"
_LEADERBOARD_GOVERNANCE_PROBE_PATH = PROJECT_ROOT / "data" / "leaderboard_feature_profile_probe.json"
_LIVE_PREDICT_PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
_RECENT_DRIFT_REPORT_PATH = PROJECT_ROOT / "data" / "recent_drift_report.json"
_ISSUES_JSON_PATH = PROJECT_ROOT / "issues.json"
_STRATEGY_PARAM_SCAN_PATH = PROJECT_ROOT / "data" / "model_strategy_param_scan_latest.json"
HIGH_CONVICTION_TOPK_PATH = PROJECT_ROOT / "data" / "high_conviction_topk_oos_matrix.json"
_MODEL_LB_STALE_AFTER_SEC = 900
_MODEL_LB_REFRESH_COOLDOWN_SEC = 300
_LIVE_PREDICT_PROBE_RUNTIME_STALE_AFTER_SEC = 1800
_HIGH_CONVICTION_TOPK_STALE_AFTER_SEC = 3600
_MODEL_LB_CACHE: Dict[str, Any] = {
    "payload": None,
    "updated_at": None,
    "refreshing": False,
    "error": None,
    "last_refresh_attempt_at": None,
    "last_refresh_reason": None,
}
_MODEL_LB_CACHE_LOCK = threading.Lock()

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
_Q15_BUCKET_ROOT_CAUSE_PATH = Path(__file__).resolve().parents[2] / "data" / "q15_bucket_root_cause.json"
_Q35_SCALING_AUDIT_PATH = Path(__file__).resolve().parents[2] / "data" / "q35_scaling_audit.json"
_BULL_4H_POCKET_ABLATION_PATH = Path(__file__).resolve().parents[2] / "data" / "bull_4h_pocket_ablation.json"
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


def _strategy_confidence_lookup_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        dt = _parse_backtest_timestamp(text)
    except Exception:
        dt = None
    if dt is None:
        return text.split(".", 1)[0]
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _build_cache_key(*parts: Any) -> str:
    return "::".join(str(part) for part in parts)


def _assert_local_operator_request(request: Optional[Request]) -> None:
    client = getattr(request, "client", None)
    client_host = getattr(client, "host", None)
    if client_host in {"127.0.0.1", "::1", "localhost"}:
        return
    raise HTTPException(status_code=403, detail="operator write endpoints are restricted to local access")


STRATEGY_DECISION_TARGET_COL = "simulated_pyramid_win"
STRATEGY_DECISION_TARGET_LABEL = "Canonical Decision Quality"
STRATEGY_DECISION_SORT_SEMANTICS = "ROI -> lower max_drawdown -> avg_decision_quality_score -> profit_factor (win_rate reference only)"


def _strategy_decision_contract_meta(*, horizon_minutes: int = 1440) -> Dict[str, Any]:
    return {
        "target_col": STRATEGY_DECISION_TARGET_COL,
        "target_label": STRATEGY_DECISION_TARGET_LABEL,
        "sort_semantics": STRATEGY_DECISION_SORT_SEMANTICS,
        "decision_quality_horizon_minutes": int(horizon_minutes),
    }


def _empty_strategy_quality_profile(*, horizon_minutes: int = 1440) -> Dict[str, Any]:
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


def _normalize_timestamp_key(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("T", " ")
    if text.endswith("Z"):
        text = text[:-1]
    if "+" in text:
        text = text.split("+", 1)[0]
    return text[:19] if len(text) >= 19 else text


def _compute_decision_profile(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    default_gate_summary: Dict[str, int] = {"ALLOW": 0, "CAUTION": 0, "BLOCK": 0}
    if not trades:
        return {
            "avg_entry_quality": None,
            "avg_allowed_layers": 0.0,
            "avg_trade_quality": None,
            "dominant_regime_gate": None,
            "regime_gate_summary": default_gate_summary,
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
        gate_key = str(gate)
        gate_counts[gate_key] = gate_counts.get(gate_key, 0) + 1
    dominant_regime_gate = None
    if gate_counts:
        dominant_regime_gate = max(gate_counts.items(), key=lambda item: (item[1], item[0]))[0]

    regime_gate_summary = {**default_gate_summary, **gate_counts}

    return {
        "avg_entry_quality": None if not entry_quality_vals else round(sum(entry_quality_vals) / len(entry_quality_vals), 4),
        "avg_allowed_layers": round(sum(allowed_layers_vals) / len(allowed_layers_vals), 4) if allowed_layers_vals else 0.0,
        "avg_trade_quality": None if not trade_quality_vals else round(sum(trade_quality_vals) / len(trade_quality_vals), 4),
        "dominant_regime_gate": dominant_regime_gate,
        "regime_gate_summary": regime_gate_summary,
    }



def _compute_strategy_decision_quality_profile(
    trades: List[Dict[str, Any]],
    db=None,
    db_path: Optional[str] = None,
    horizon_minutes: int = 1440,
) -> Dict[str, Any]:
    profile = _empty_strategy_quality_profile(horizon_minutes=horizon_minutes)
    if not trades:
        return profile

    resolved_db_path = db_path or (_get_sqlite_db_path(db) if db is not None else None)
    timestamp_keys = sorted({
        key
        for key in (
            _normalize_timestamp_key(trade.get("entry_timestamp") or trade.get("timestamp"))
            for trade in trades
        )
        if key
    })

    if resolved_db_path and timestamp_keys:
        placeholders = ",".join("?" for _ in timestamp_keys)
        query = f"""
            SELECT substr(timestamp, 1, 19) AS ts_key,
                   simulated_pyramid_win,
                   simulated_pyramid_pnl,
                   simulated_pyramid_quality,
                   simulated_pyramid_drawdown_penalty,
                   simulated_pyramid_time_underwater
            FROM labels
            WHERE horizon_minutes = ?
              AND simulated_pyramid_win IS NOT NULL
              AND substr(timestamp, 1, 19) IN ({placeholders})
        """
        try:
            from model import predictor as predictor_module

            conn = sqlite3.connect(resolved_db_path)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(query, [horizon_minutes, *timestamp_keys]).fetchall()
            finally:
                conn.close()
        except Exception:
            rows = []

        if rows:
            def _avg(col: str) -> Optional[float]:
                vals = [float(row[col]) for row in rows if row[col] is not None]
                if not vals:
                    return None
                return round(sum(vals) / len(vals), 4)

            avg_expected_win_rate = _avg("simulated_pyramid_win")
            avg_expected_pyramid_pnl = _avg("simulated_pyramid_pnl")
            avg_expected_pyramid_quality = _avg("simulated_pyramid_quality")
            avg_expected_drawdown_penalty = _avg("simulated_pyramid_drawdown_penalty")
            avg_expected_time_underwater = _avg("simulated_pyramid_time_underwater")
            avg_decision_quality_score = predictor_module._compute_decision_quality_score(
                avg_expected_win_rate,
                avg_expected_pyramid_quality,
                avg_expected_drawdown_penalty,
                avg_expected_time_underwater,
            )
            profile.update({
                "avg_expected_win_rate": avg_expected_win_rate,
                "avg_expected_pyramid_pnl": avg_expected_pyramid_pnl,
                "avg_expected_pyramid_quality": avg_expected_pyramid_quality,
                "avg_expected_drawdown_penalty": avg_expected_drawdown_penalty,
                "avg_expected_time_underwater": avg_expected_time_underwater,
                "avg_decision_quality_score": avg_decision_quality_score,
                "decision_quality_label": predictor_module._decision_quality_label(avg_decision_quality_score),
                "decision_quality_sample_size": len(rows),
            })
            return profile

    pnl_vals = [float(t.get("pnl") or 0.0) for t in trades]
    if not pnl_vals:
        return profile
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
    profile.update({
        "avg_expected_win_rate": round(expected_win_rate, 4),
        "avg_expected_pyramid_pnl": round(expected_pyramid_pnl, 4),
        "avg_expected_pyramid_quality": round(expected_pyramid_quality, 4),
        "avg_expected_drawdown_penalty": round(sum(drawdown_penalties) / len(drawdown_penalties), 4),
        "avg_expected_time_underwater": round(sum(time_underwater) / len(time_underwater), 4),
        "avg_decision_quality_score": round(decision_quality_score, 4),
        "decision_quality_label": quality_label,
        "decision_quality_sample_size": len(trades),
    })
    return profile


def _compute_raw_snapshot_stats(db: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(db, sqlite3.Connection):
        return compute_raw_snapshot_stats(db)
    bind = getattr(db, "bind", None)
    if hasattr(bind, "raw_connection"):
        conn = bind.raw_connection()
        try:
            return compute_raw_snapshot_stats(conn)
        finally:
            conn.close()
    if hasattr(db, "execute") and not hasattr(db, "bind"):
        return compute_raw_snapshot_stats(db)
    return {}


def _row_timestamp_value(row: Any) -> Any:
    value = getattr(row, "timestamp", None)
    if isinstance(value, datetime):
        return value
    if hasattr(value, "timestamp") and callable(getattr(value, "timestamp")):
        try:
            return value.timestamp()
        except Exception:
            return value
    return value


def _recent_feature_rows(days: int = 30) -> List[Any]:
    db = get_db()
    rows = list(db.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all())
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(int(days), 1))
    filtered: List[Any] = []
    for row in rows:
        ts = _parse_utc_datetime(_row_timestamp_value(row))
        if ts is None or ts >= cutoff:
            filtered.append(row)
    return filtered or rows


def _feature_row_to_payload(row: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "timestamp": _iso_utc_timestamp(_row_timestamp_value(row)),
    }
    for db_key, clean_key in FEATURE_KEY_MAP.items():
        raw_value = getattr(row, db_key, None)
        payload[clean_key] = None if raw_value is None else normalize_feature(raw_value, db_key)
        payload[f"raw_{clean_key}"] = raw_value
    return payload


def _feature_coverage_from_rows(rows: List[Any], snapshot_stats: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    snapshot_stats = snapshot_stats or {}
    snapshot_counts = {subtype: row.get("count", 0) for subtype, row in snapshot_stats.items()}
    total_rows = len(rows)
    ordered_timestamps = [getattr(row, "timestamp", None) for row in rows]
    available_columns = {
        db_key for db_key in FEATURE_KEY_MAP if any(hasattr(row, db_key) for row in rows)
    }
    stats: List[Dict[str, Any]] = []
    for db_key, clean_key in FEATURE_KEY_MAP.items():
        if db_key in available_columns:
            feature_values = [getattr(row, db_key, None) for row in rows]
            non_null_values = [value for value in feature_values if value is not None]
            non_null = len(non_null_values)
            distinct = len({value for value in non_null_values})
            min_v = min(non_null_values) if non_null_values else None
            max_v = max(non_null_values) if non_null_values else None
        else:
            feature_values = [None] * total_rows
            non_null, distinct, min_v, max_v = 0, 0, None, None
        coverage_pct = (non_null / total_rows * 100.0) if total_rows else 0.0
        quality = assess_feature_quality(clean_key, coverage_pct, distinct, non_null, min_v, max_v)
        quality.update(_compute_archive_window_coverage(clean_key, ordered_timestamps, feature_values, snapshot_stats))
        quality = attach_forward_archive_meta(clean_key, quality, snapshot_counts, snapshot_stats)
        stats.append({
            "db_key": db_key,
            "key": clean_key,
            "non_null": non_null,
            "coverage_pct": round(coverage_pct, 2),
            "distinct": distinct,
            "min": min_v,
            "max": max_v,
            **quality,
        })
    stats.sort(key=lambda row: (row["chart_usable"], row["coverage_pct"], row["distinct"]))
    maturity_counts = {"core": 0, "research": 0, "blocked": 0}
    for row in stats:
        tier = str(row.get("maturity_tier") or "blocked")
        maturity_counts[tier] = maturity_counts.get(tier, 0) + 1
    return {
        "rows_total": total_rows,
        "usable_count": sum(1 for row in stats if row.get("chart_usable")),
        "hidden_count": sum(1 for row in stats if not row.get("chart_usable")),
        "maturity_counts": maturity_counts,
        "features": {row["key"]: row for row in stats},
    }


@router.get("/features")
async def api_features(days: int = 30) -> List[Dict[str, Any]]:
    return [_feature_row_to_payload(row) for row in _recent_feature_rows(days=days)]


@router.get("/features/coverage")
async def api_features_coverage(days: int = 90) -> Dict[str, Any]:
    db = get_db()
    return _feature_coverage_from_rows(_recent_feature_rows(days=days), snapshot_stats=_compute_raw_snapshot_stats(db))


@router.get("/backtest")
async def api_backtest(days: int = 30, initial_capital: float = 10000.0) -> Dict[str, Any]:
    from backtesting import strategy_lab

    exchange = ccxt.binance()
    try:
        candles_4h = exchange.fetch_ohlcv("BTCUSDT", "4h", limit=max(int(days) * 6, 20))
    except Exception:
        candles_4h = []
    try:
        candles_1d = exchange.fetch_ohlcv("BTCUSDT", "1d", limit=max(int(days), 5))
    except Exception:
        candles_1d = []

    trades: List[Dict[str, Any]] = []
    equity = float(initial_capital)
    for row in _recent_feature_rows(days=days):
        regime = str(getattr(row, "regime_label", None) or "unknown")
        bias200 = float(getattr(row, "feat_4h_bias200", 0.0) or 0.0)
        bb_pct_b = getattr(row, "feat_4h_bb_pct_b", None)
        dist_bb_lower = getattr(row, "feat_4h_dist_bb_lower", None)
        dist_swing_low = getattr(row, "feat_4h_dist_swing_low", None)
        regime_gate = strategy_lab._compute_regime_gate(
            bias200,
            regime,
            regime_min=0.0,
            bb_pct_b_value=bb_pct_b,
            dist_bb_lower_value=dist_bb_lower,
            dist_swing_low_value=dist_swing_low,
        )
        structure_quality = strategy_lab._compute_4h_structure_quality(
            bb_pct_b_value=bb_pct_b,
            dist_bb_lower_value=dist_bb_lower,
            dist_swing_low_value=dist_swing_low,
        )
        structure_bucket = strategy_lab._structure_bucket(regime_gate, structure_quality)
        entry_quality = strategy_lab._compute_entry_quality(
            float(getattr(row, "feat_4h_bias50", 0.0) or 0.0),
            float(getattr(row, "feat_nose", 0.0) or 0.0),
            float(getattr(row, "feat_pulse", 0.0) or 0.0),
            float(getattr(row, "feat_ear", 0.0) or 0.0),
            bb_pct_b_value=bb_pct_b,
            dist_bb_lower_value=dist_bb_lower,
            dist_swing_low_value=dist_swing_low,
            regime_label=regime,
            regime_gate=regime_gate,
            structure_bucket=structure_bucket,
        )
        allowed_layers = strategy_lab._allowed_layers_for_signal(regime_gate, entry_quality, 3)
        if allowed_layers <= 0:
            continue
        pnl = round((entry_quality - 0.5) * 0.1 * allowed_layers, 4)
        equity = round(equity + pnl * initial_capital, 4)
        trades.append({
            "entry_timestamp": _iso_utc_timestamp(_row_timestamp_value(row)),
            "entry_quality": round(entry_quality, 4),
            "entry_quality_label": strategy_lab._quality_label(entry_quality),
            "allowed_layers": allowed_layers,
            "regime_gate": regime_gate,
            "structure_bucket": structure_bucket,
            "pnl": pnl,
            "max_drawdown": 0.0 if pnl >= 0 else abs(pnl),
            "bars_held": 1,
            "equity": equity,
        })

    decision_profile = _compute_decision_profile(trades)
    decision_quality = _compute_strategy_decision_quality_profile(trades, db=get_db(), horizon_minutes=1440)
    return {
        "initial_capital": float(initial_capital),
        "total_trades": len(trades),
        "decision_contract": _strategy_decision_contract_meta(horizon_minutes=1440),
        **decision_profile,
        **decision_quality,
        "trades": _normalize_result_timestamps(trades),
        "price_data": _normalize_result_timestamps([
            {"timestamp": candle[0], "close": candle[4], "volume": candle[5]}
            for candle in candles_4h
        ]),
        "benchmark_daily": _normalize_result_timestamps([
            {"timestamp": candle[0], "close": candle[4]}
            for candle in candles_1d
        ]),
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

def _build_venue_runtime_proof_contract(venue: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """Expose venue readiness as a proof contract, not just public metadata OK/FAIL."""
    enabled = bool(item.get("enabled_in_config"))
    credentials_configured = bool(item.get("credentials_configured"))
    metadata_ok = bool(item.get("ok"))

    blockers: List[str] = []
    if not metadata_ok:
        blockers.append("元資料契約尚未通過")
    if not enabled:
        blockers.append("場館設定停用")
    if not credentials_configured:
        blockers.append("live exchange credential 尚未驗證")
    blockers.extend([
        "order ack lifecycle 尚未驗證",
        "fill lifecycle 尚未驗證",
    ])

    if not metadata_ok:
        proof_state = "metadata_contract_failed"
        operator_next_action = f"先修復 {venue} 元資料檢查，再評估憑證與實單生命週期。"
    elif not enabled:
        proof_state = "config_disabled_metadata_only"
        operator_next_action = f"若要啟用 {venue}，先開啟場館設定並配置憑證；目前只能作公開元資料觀測。"
    elif not credentials_configured:
        proof_state = "public_metadata_only"
        operator_next_action = f"先配置 {venue} 交易憑證，再用沙盒或極小額委託捕捉委託確認 / 成交 / 取消生命週期。"
    else:
        proof_state = "credentials_configured_missing_runtime_lifecycle"
        operator_next_action = f"使用 {venue} 沙盒或極小額實單捕捉交易所回傳的委託確認 / 成交 / 取消生命週期。"

    return {
        "proof_state": proof_state,
        "blockers": blockers,
        "operator_next_action": operator_next_action,
        "verify_next": "重跑元資料檢查，並在 /api/status 的場館生命週期通道看到交易所回傳的委託確認 / 成交 / 取消證據。",
        "readiness_scope": "venue_runtime_proof_required",
    }


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
        proof_contract = _build_venue_runtime_proof_contract(str(venue), item)
        venues.append({
            "venue": venue,
            "ok": bool(item.get("ok")),
            "enabled_in_config": bool(item.get("enabled_in_config")),
            "credentials_configured": bool(item.get("credentials_configured")),
            "error": item.get("error"),
            **proof_contract,
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
    support_identity = (
        payload.get("support_identity")
        or support_route.get("support_identity")
        or support_progress.get("support_identity")
    )

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
        "support_identity": support_identity if isinstance(support_identity, dict) else None,
        "artifact_context_freshness": payload.get("artifact_context_freshness"),
        "floor_cross_legality": floor_cross,
        "component_experiment": component_experiment,
        "current_live": current_live,
    }


def _enrich_confidence_with_q15_support_audit(result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
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
        details["support_progress"] = support_progress
        details["current_live_structure_bucket_rows"] = support_progress.get("current_rows")
        details["minimum_support_rows"] = support_progress.get("minimum_support_rows")
        details["current_live_structure_bucket_gap_to_minimum"] = support_progress.get("gap_to_minimum")
    if audit_summary.get("support_identity"):
        details["support_identity"] = audit_summary.get("support_identity")
    if audit_summary.get("artifact_context_freshness"):
        details["artifact_context_freshness"] = audit_summary.get("artifact_context_freshness")
    if audit_summary.get("support_route_verdict") is not None:
        details["support_route_verdict"] = audit_summary.get("support_route_verdict")
    if audit_summary.get("support_route_deployable") is not None:
        details["support_route_deployable"] = audit_summary.get("support_route_deployable")
    if audit_summary.get("support_governance_route") is not None:
        details["support_governance_route"] = audit_summary.get("support_governance_route")
    if floor_cross:
        details["floor_cross_legality"] = floor_cross
    if component_experiment:
        details["component_experiment"] = component_experiment

    enriched["deployment_blocker_details"] = details
    enriched["q15_support_audit"] = audit_summary
    enriched["support_progress"] = support_progress or enriched.get("support_progress")
    enriched["support_identity"] = audit_summary.get("support_identity") or enriched.get("support_identity")
    enriched["artifact_context_freshness"] = audit_summary.get("artifact_context_freshness") or enriched.get("artifact_context_freshness")
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


def _load_q15_bucket_root_cause_summary(current_structure_bucket: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not _Q15_BUCKET_ROOT_CAUSE_PATH.exists():
        return None
    try:
        payload = json.loads(_Q15_BUCKET_ROOT_CAUSE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    current_live = payload.get("current_live") if isinstance(payload.get("current_live"), dict) else {}
    exact_live_lane = payload.get("exact_live_lane") if isinstance(payload.get("exact_live_lane"), dict) else {}
    candidate_patch = payload.get("candidate_patch") if isinstance(payload.get("candidate_patch"), dict) else {}

    bucket = current_live.get("structure_bucket")
    if current_structure_bucket and bucket and str(current_structure_bucket) != str(bucket):
        return None

    artifact_context_freshness = (
        payload.get("artifact_context_freshness")
        if isinstance(payload.get("artifact_context_freshness"), dict)
        else {}
    )

    return {
        "generated_at": payload.get("generated_at"),
        "current_live_structure_bucket": bucket or current_structure_bucket,
        "bucket_scope_label": payload.get("bucket_scope_label"),
        "verdict": payload.get("verdict"),
        "candidate_patch_type": payload.get("candidate_patch_type"),
        "candidate_patch_feature": payload.get("candidate_patch_feature"),
        "reason": payload.get("reason"),
        "verify_next": payload.get("verify_next"),
        "structure_quality": current_live.get("structure_quality"),
        "q15_threshold": current_live.get("q15_threshold"),
        "q35_threshold": current_live.get("q35_threshold"),
        "support_status": current_live.get("support_status"),
        "support_route_verdict": current_live.get("support_route_verdict"),
        "support_current_rows": current_live.get("support_current_rows"),
        "support_minimum_rows": current_live.get("support_minimum_rows"),
        "support_gap_to_minimum": current_live.get("support_gap_to_minimum"),
        "gap_to_q35_boundary": current_live.get("gap_to_q35_boundary"),
        "dominant_neighbor_bucket": exact_live_lane.get("dominant_neighbor_bucket"),
        "dominant_neighbor_rows": exact_live_lane.get("dominant_neighbor_rows"),
        "near_boundary_rows": exact_live_lane.get("near_boundary_rows"),
        "candidate_patch": candidate_patch or None,
        "artifact_context_freshness_verdict": artifact_context_freshness.get("verdict"),
        "artifact_context_freshness_mismatched_fields": artifact_context_freshness.get("mismatched_fields") or [],
        "reference_mismatched_fields": artifact_context_freshness.get("reference_mismatched_fields") or [],
        "reference_artifact_warning": artifact_context_freshness.get("reference_artifact_warning"),
    }


def _load_q35_scaling_audit_summary(current_structure_bucket: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not current_structure_bucket or "q35" not in str(current_structure_bucket):
        return None
    if not _Q35_SCALING_AUDIT_PATH.exists():
        return None
    try:
        payload = json.loads(_Q35_SCALING_AUDIT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    applicability = payload.get("scope_applicability") if isinstance(payload.get("scope_applicability"), dict) else {}
    if not applicability.get("active_for_current_live_row"):
        return None

    audit_bucket = (
        applicability.get("current_structure_bucket")
        or ((payload.get("current_live") or {}).get("structure_bucket"))
        or current_structure_bucket
    )
    if audit_bucket and str(audit_bucket) != str(current_structure_bucket):
        return None

    segmented_calibration = payload.get("segmented_calibration") if isinstance(payload.get("segmented_calibration"), dict) else {}
    deployment_grade = payload.get("deployment_grade_component_experiment") if isinstance(payload.get("deployment_grade_component_experiment"), dict) else {}
    redesign = payload.get("base_stack_redesign_experiment") if isinstance(payload.get("base_stack_redesign_experiment"), dict) else {}
    recommended_mode = segmented_calibration.get("recommended_mode")
    next_patch_target = deployment_grade.get("next_patch_target")
    root_cause_action = recommended_mode or ("base_stack_redesign" if redesign.get("verdict") else None)
    return {
        "generated_at": payload.get("generated_at"),
        "current_live_structure_bucket": audit_bucket or current_structure_bucket,
        "target_structure_bucket": applicability.get("target_structure_bucket"),
        "scope_applicability_status": applicability.get("status"),
        "overall_verdict": payload.get("overall_verdict"),
        "verdict": payload.get("overall_verdict"),
        "verdict_reason": payload.get("verdict_reason"),
        "reason": payload.get("recommended_action") or payload.get("verdict_reason"),
        "recommended_action": payload.get("recommended_action"),
        "segmented_calibration_status": segmented_calibration.get("status"),
        "recommended_mode": recommended_mode,
        "candidate_patch_type": root_cause_action,
        "candidate_patch_feature": next_patch_target,
        "runtime_contract_status": segmented_calibration.get("runtime_contract_status"),
        "redesign_verdict": redesign.get("verdict"),
        "runtime_remaining_gap_to_floor": deployment_grade.get("runtime_remaining_gap_to_floor"),
        "remaining_gap_to_floor": deployment_grade.get("runtime_remaining_gap_to_floor"),
        "next_patch_target": next_patch_target,
        "verify_next": payload.get("verify_next") or deployment_grade.get("verify_next") or redesign.get("verify_next"),
        "q35_discriminative_redesign_applied": deployment_grade.get("q35_discriminative_redesign_applied"),
    }


def _enrich_confidence_with_q35_scaling_audit(result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return result

    blocker_details = result.get("deployment_blocker_details") if isinstance(result.get("deployment_blocker_details"), dict) else {}
    current_structure_bucket = (
        result.get("current_live_structure_bucket")
        or result.get("decision_quality_live_structure_bucket")
        or blocker_details.get("current_live_structure_bucket")
        or result.get("structure_bucket")
    )
    q35_summary = _load_q35_scaling_audit_summary(
        str(current_structure_bucket) if current_structure_bucket is not None else None
    )
    if not q35_summary:
        return result

    enriched = dict(result)
    details = dict(blocker_details)
    details["q35_scaling_audit"] = q35_summary
    enriched["deployment_blocker_details"] = details
    enriched["q35_scaling_audit"] = q35_summary
    enriched["q35_overall_verdict"] = q35_summary.get("overall_verdict")
    enriched["q35_redesign_verdict"] = q35_summary.get("redesign_verdict")
    enriched["q35_runtime_remaining_gap_to_floor"] = q35_summary.get("runtime_remaining_gap_to_floor")
    enriched["q35_recommended_mode"] = q35_summary.get("recommended_mode")
    enriched["q35_recommended_action"] = q35_summary.get("recommended_action")
    enriched["q35_next_patch_target"] = q35_summary.get("next_patch_target")
    if not enriched.get("current_bucket_root_cause"):
        enriched["current_bucket_root_cause"] = q35_summary
    return enriched


def _enrich_confidence_with_q15_bucket_root_cause(result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return result

    blocker_details = result.get("deployment_blocker_details") if isinstance(result.get("deployment_blocker_details"), dict) else {}
    current_structure_bucket = (
        result.get("current_live_structure_bucket")
        or result.get("decision_quality_live_structure_bucket")
        or blocker_details.get("current_live_structure_bucket")
        or result.get("structure_bucket")
    )
    root_cause_summary = _load_q15_bucket_root_cause_summary(
        str(current_structure_bucket) if current_structure_bucket is not None else None
    )
    if not root_cause_summary:
        return result

    enriched = dict(result)
    details = dict(blocker_details)
    details["q15_bucket_root_cause"] = root_cause_summary
    if not details.get("current_bucket_root_cause"):
        details["current_bucket_root_cause"] = root_cause_summary
    enriched["deployment_blocker_details"] = details
    enriched["q15_bucket_root_cause"] = root_cause_summary
    if not enriched.get("current_bucket_root_cause"):
        enriched["current_bucket_root_cause"] = root_cause_summary
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
        "operations_surface": {
            "route": "/execution",
            "label": "Execution Console / 實戰交易",
            "role": "operations-beta",
            "status": "live-routing-operator-view",
            "message": "Execution Console 已拆成獨立 trading operations surface，現在同時承載 live runtime truth、run control、manual trade / automation controls 與 account snapshot；深度 proof chain / recovery 仍回 Dashboard。",
            "upgrade_prerequisite": "下一步必須把 per-bot capital / position / order attribution 與 capital actions 接上 run-owned ledger，才能從 operator-view 升級成完整 execution console。",
        },
        "diagnostics_surface": {
            "route": "/execution/status",
            "label": "執行狀態 / Diagnostics",
            "role": "diagnostics-canonical",
            "status": "proof-chain",
            "message": "Execution Status 已拆成獨立 diagnostics / guardrail / recovery surface；Dashboard 只保留 execution summary。",
        },
        "shortcut_surface": {
            "name": "signal_banner",
            "role": "shortcut-only",
            "status": "not-upgraded",
            "message": "快捷面板目前只提供受阻塞點保護的下單入口 / 自動交易切換；完整執行狀態、保護欄脈絡與治理新鮮度必須回執行狀態頁檢查。",
            "upgrade_prerequisite": "必須先完整消費 /api/status 的監控跳動狀態、治理新鮮度與保護欄脈絡，才能升級第二執行路由。",
        },
        "readiness_scope": "runtime_governance_visibility_only",
        "live_ready": False,
        "live_ready_blockers": [
            "live exchange credential 尚未驗證",
            "order ack lifecycle 尚未驗證",
            "fill lifecycle 尚未驗證",
        ],
        "operator_message": "目前完成的是 execution governance / visibility closure，不是 live 或 canary readiness。Execution Console 已獨立出 operator view，但深度 proof chain / recovery 仍以 Dashboard 為準。",
    }


def _build_live_pathology_scope_summary(scope_diagnostics: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return shared_build_live_pathology_scope_summary(scope_diagnostics)


def _load_bull_4h_pocket_ablation_summary(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    return shared_load_bull_4h_pocket_ablation_summary(
        path or _BULL_4H_POCKET_ABLATION_PATH,
        warn=logger.warning,
    )


def _build_live_pathology_patch_summary(
    confidence_payload: Dict[str, Any],
    scope_summary: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    return shared_build_live_pathology_patch_summary(
        confidence_payload,
        scope_summary,
        artifact_path=_BULL_4H_POCKET_ABLATION_PATH,
        warn=logger.warning,
    )


def _build_live_runtime_closure_surface(confidence_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:

    from backtesting import strategy_lab

    payload = confidence_payload or {}
    blocker_details = payload.get("deployment_blocker_details") if isinstance(payload.get("deployment_blocker_details"), dict) else {}
    patch_active = bool(payload.get("q15_exact_supported_component_patch_applied"))
    signal = str(payload.get("signal") or "unknown")
    regime_label = payload.get("regime_label")
    regime_gate = payload.get("regime_gate")
    scope_diagnostics = payload.get("decision_quality_scope_diagnostics") if isinstance(payload.get("decision_quality_scope_diagnostics"), dict) else {}
    exact_scope = scope_diagnostics.get("regime_label+regime_gate+entry_quality_label") if isinstance(scope_diagnostics.get("regime_label+regime_gate+entry_quality_label"), dict) else {}
    current_live_structure_bucket = (
        payload.get("current_live_structure_bucket")
        or payload.get("decision_quality_live_structure_bucket")
        or blocker_details.get("current_live_structure_bucket")
        or payload.get("structure_bucket")
        or exact_scope.get("current_live_structure_bucket")
    )
    structure_bucket = current_live_structure_bucket or payload.get("structure_bucket")
    allowed_layers = payload.get("allowed_layers")
    support_progress = payload.get("support_progress") if isinstance(payload.get("support_progress"), dict) else {}
    current_rows = support_progress.get("current_rows")
    if current_rows is None:
        current_rows = payload.get("current_live_structure_bucket_rows")
    if current_rows is None:
        current_rows = blocker_details.get("current_live_structure_bucket_rows")
    if current_rows is None:
        current_rows = exact_scope.get("current_live_structure_bucket_rows")
    minimum_rows = support_progress.get("minimum_support_rows")
    if minimum_rows is None:
        minimum_rows = payload.get("minimum_support_rows")
    if minimum_rows is None:
        minimum_rows = blocker_details.get("minimum_support_rows")
    gap_to_minimum = payload.get("current_live_structure_bucket_gap_to_minimum")
    if gap_to_minimum is None:
        gap_to_minimum = blocker_details.get("current_live_structure_bucket_gap_to_minimum")
    if gap_to_minimum is None and current_rows is not None and minimum_rows is not None:
        try:
            gap_to_minimum = max(int(minimum_rows) - int(current_rows), 0)
        except (TypeError, ValueError):
            gap_to_minimum = None
    support_route_deployable = payload.get("support_route_deployable")
    if support_route_deployable is None:
        support_route_deployable = blocker_details.get("support_route_deployable")
    support_governance_route = payload.get("support_governance_route")
    if support_governance_route is None:
        support_governance_route = blocker_details.get("support_governance_route")
    scope_pathology_summary = _build_live_pathology_scope_summary(scope_diagnostics)
    spillover_patch_summary = _build_live_pathology_patch_summary(payload, scope_pathology_summary)
    if isinstance(scope_pathology_summary, dict) and isinstance(spillover_patch_summary, dict):
        scope_pathology_summary = {
            **scope_pathology_summary,
            "recommended_patch": spillover_patch_summary,
        }
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

    recommended_patch_summary = spillover_patch_summary if isinstance(spillover_patch_summary, dict) else None
    recommended_patch_profile = payload.get("recommended_patch_profile")
    if recommended_patch_profile is None and recommended_patch_summary is not None:
        recommended_patch_profile = recommended_patch_summary.get("recommended_profile")
    recommended_patch_status = payload.get("recommended_patch_status")
    if recommended_patch_status is None and recommended_patch_summary is not None:
        recommended_patch_status = recommended_patch_summary.get("status")
    recommended_patch_reference_scope = payload.get("recommended_patch_reference_scope")
    if recommended_patch_reference_scope is None and recommended_patch_summary is not None:
        recommended_patch_reference_scope = recommended_patch_summary.get("reference_patch_scope")
    recommended_patch_reference_source = payload.get("recommended_patch_reference_source")
    if recommended_patch_reference_source is None and recommended_patch_summary is not None:
        recommended_patch_reference_source = recommended_patch_summary.get("reference_source")
    recommended_patch_reason = payload.get("recommended_patch_reason")
    if recommended_patch_reason is None and recommended_patch_summary is not None:
        recommended_patch_reason = recommended_patch_summary.get("reason")
    recommended_patch_support_route = payload.get("recommended_patch_support_route")
    if recommended_patch_support_route is None and recommended_patch_summary is not None:
        recommended_patch_support_route = recommended_patch_summary.get("support_route_verdict")
    recommended_patch_gap_to_minimum = payload.get("recommended_patch_gap_to_minimum")
    if recommended_patch_gap_to_minimum is None and recommended_patch_summary is not None:
        recommended_patch_gap_to_minimum = recommended_patch_summary.get("gap_to_minimum")
    recommended_patch_current_rows = payload.get("recommended_patch_current_live_structure_bucket_rows")
    if recommended_patch_current_rows is None and recommended_patch_summary is not None:
        recommended_patch_current_rows = recommended_patch_summary.get("current_live_structure_bucket_rows")
    recommended_patch_minimum_rows = payload.get("recommended_patch_minimum_support_rows")
    if recommended_patch_minimum_rows is None and recommended_patch_summary is not None:
        recommended_patch_minimum_rows = recommended_patch_summary.get("minimum_support_rows")

    breaker_release = blocker_details.get("release_condition") if isinstance(blocker_details.get("release_condition"), dict) else {}
    breaker_recent_window = blocker_details.get("recent_window") if isinstance(blocker_details.get("recent_window"), dict) else {}
    release_window = breaker_release.get("recent_window") or breaker_recent_window.get("window_size") or 50
    release_floor = breaker_release.get("recent_win_rate_must_be_at_least")
    if release_floor is None:
        release_floor = breaker_recent_window.get("floor")
    current_wins = breaker_release.get("current_recent_window_wins")
    if current_wins is None:
        current_wins = breaker_recent_window.get("wins")
    wins_gap = breaker_release.get("additional_recent_window_wins_needed")

    runtime_payload = {
        **payload,
        "current_live_structure_bucket": current_live_structure_bucket,
        "current_live_structure_bucket_rows": current_rows,
        "minimum_support_rows": minimum_rows,
        "current_live_structure_bucket_gap_to_minimum": gap_to_minimum,
        "support_route_deployable": support_route_deployable,
        "support_governance_route": support_governance_route,
    }
    if support_progress:
        runtime_payload["support_progress"] = support_progress
    if current_live_structure_bucket and not runtime_payload.get("structure_bucket"):
        runtime_payload["structure_bucket"] = current_live_structure_bucket

    runtime_closure_state = build_runtime_closure_state(runtime_payload)
    runtime_closure_summary = build_runtime_closure_summary(
        runtime_payload,
        release_window=int(release_window),
        release_floor=release_floor,
        release_gap=wins_gap,
        current_wins=current_wins,
        breaker_release=breaker_release,
        scope_pathology_summary=scope_pathology_summary if isinstance(scope_pathology_summary, dict) else None,
    ) or (
        payload.get("deployment_blocker_reason")
        or payload.get("execution_guardrail_reason")
        or payload.get("allowed_layers_reason")
        or "runtime closure summary unavailable"
    )

    sleeve_routing = strategy_lab.build_regime_aware_sleeve_routing(
        regime_label=regime_label,
        regime_gate=regime_gate,
        structure_bucket=structure_bucket,
        allowed_layers=allowed_layers,
        entry_quality=payload.get("entry_quality"),
        deployment_blocker=payload.get("deployment_blocker"),
        execution_guardrail_reason=payload.get("execution_guardrail_reason"),
    )
    current_bucket_root_cause = (
        payload.get("current_bucket_root_cause")
        or payload.get("q15_bucket_root_cause")
        or _load_q15_bucket_root_cause_summary(
            str(current_live_structure_bucket) if current_live_structure_bucket is not None else None
        )
    )
    q15_bucket_root_cause = payload.get("q15_bucket_root_cause") or current_bucket_root_cause
    return {
        "runtime_closure_state": runtime_closure_state,
        "runtime_closure_summary": runtime_closure_summary,
        "signal": signal,
        "regime_label": regime_label,
        "regime_gate": regime_gate,
        "structure_bucket": structure_bucket,
        "current_live_structure_bucket": current_live_structure_bucket,
        "current_live_structure_bucket_rows": current_rows,
        "minimum_support_rows": minimum_rows,
        "current_live_structure_bucket_gap_to_minimum": gap_to_minimum,
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
        "q35_discriminative_redesign_applied": payload.get("q35_discriminative_redesign_applied"),
        "q35_discriminative_redesign": payload.get("q35_discriminative_redesign"),
        "q15_exact_supported_component_patch_applied": patch_active,
        "support_route_verdict": payload.get("support_route_verdict"),
        "support_route_deployable": support_route_deployable,
        "support_governance_route": support_governance_route,
        "support_progress": support_progress or None,
        "support_rows_text": f"{current_rows} / {minimum_rows}" if current_rows is not None and minimum_rows is not None else None,
        "runtime_exact_support_rows": current_rows,
        "calibration_exact_lane_rows": calibration_exact_lane_rows,
        "calibration_exact_lane_alerts": calibration_exact_lane_alerts,
        "support_alignment_status": support_alignment_status,
        "support_alignment_summary": support_alignment_summary,
        "recommended_patch": recommended_patch_summary,
        "recommended_patch_profile": recommended_patch_profile,
        "recommended_patch_status": recommended_patch_status,
        "recommended_patch_reference_scope": recommended_patch_reference_scope,
        "recommended_patch_reference_source": recommended_patch_reference_source,
        "recommended_patch_reason": recommended_patch_reason,
        "recommended_patch_support_route": recommended_patch_support_route,
        "recommended_patch_gap_to_minimum": recommended_patch_gap_to_minimum,
        "recommended_patch_current_live_structure_bucket_rows": recommended_patch_current_rows,
        "recommended_patch_minimum_support_rows": recommended_patch_minimum_rows,
        "sleeve_routing": sleeve_routing,
        "q35_scaling_audit": payload.get("q35_scaling_audit"),
        "q35_overall_verdict": payload.get("q35_overall_verdict"),
        "q35_redesign_verdict": payload.get("q35_redesign_verdict"),
        "q35_runtime_remaining_gap_to_floor": payload.get("q35_runtime_remaining_gap_to_floor"),
        "q35_recommended_mode": payload.get("q35_recommended_mode"),
        "q35_recommended_action": payload.get("q35_recommended_action"),
        "q35_next_patch_target": payload.get("q35_next_patch_target"),
        "q15_bucket_root_cause": q15_bucket_root_cause,
        "current_bucket_root_cause": current_bucket_root_cause,
        "decision_quality_recent_pathology_applied": payload.get("decision_quality_recent_pathology_applied"),
        "decision_quality_recent_pathology_reason": payload.get("decision_quality_recent_pathology_reason"),
        "decision_quality_recent_pathology_window": payload.get("decision_quality_recent_pathology_window"),
        "decision_quality_recent_pathology_alerts": payload.get("decision_quality_recent_pathology_alerts"),
        "decision_quality_recent_pathology_summary": payload.get("decision_quality_recent_pathology_summary"),
        "decision_quality_scope_pathology_summary": scope_pathology_summary,
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
            "exchange": getattr(event, "exchange", None),
            "is_dry_run": bool(getattr(event, "is_dry_run", None)) if getattr(event, "is_dry_run", None) is not None else None,
            "summary": getattr(event, "summary", None),
        }

    def _event_provenance(event: Optional[OrderLifecycleEvent]) -> Dict[str, Any]:
        if event is None:
            return {
                "level": "missing",
                "venue_backed": False,
                "exchange": None,
                "source": None,
                "is_dry_run": None,
                "summary": "尚未觀察到這個 artifact 的任何 lifecycle 證據。",
            }

        source = str(getattr(event, "source", None) or "")
        source_lower = source.lower()
        exchange = getattr(event, "exchange", None)
        is_dry_run_raw = getattr(event, "is_dry_run", None)
        is_dry_run = bool(is_dry_run_raw) if is_dry_run_raw is not None else None
        venue_source = (
            source_lower in {"exchange_adapter", "venue_adapter", "venue_websocket", "exchange_websocket"}
            or "exchange" in source_lower
            or "venue" in source_lower
        )

        if is_dry_run:
            level = "dry_run_only"
            summary = "目前只有 dry-run lifecycle 證據；尚未形成真實 venue artifact。"
        elif venue_source:
            level = "venue_backed"
            summary = "已觀察到 venue-backed lifecycle 證據，可直接對應真實交易所事件。"
        else:
            level = "internal_only"
            summary = "目前只有 internal/runtime DB 證據；尚未對上真實 venue artifact。"

        return {
            "level": level,
            "venue_backed": level == "venue_backed",
            "exchange": exchange,
            "source": source or None,
            "is_dry_run": is_dry_run,
            "summary": summary,
        }

    def _serialize_proof_chain_event(event: OrderLifecycleEvent) -> Dict[str, Any]:
        provenance = _event_provenance(event)
        return {
            "timestamp": _iso_utc_timestamp(getattr(event, "timestamp", None)),
            "event_type": getattr(event, "event_type", None),
            "order_state": getattr(event, "order_state", None),
            "summary": getattr(event, "summary", None),
            "source": getattr(event, "source", None),
            "exchange": getattr(event, "exchange", None),
            "order_id": getattr(event, "order_id", None),
            "client_order_id": getattr(event, "client_order_id", None),
            "provenance_level": provenance["level"],
            "provenance_summary": provenance["summary"],
            "venue_backed": provenance["venue_backed"],
            "is_dry_run": provenance["is_dry_run"],
        }

    def _build_proof_chain(
        matcher: Callable[[OrderLifecycleEvent], bool],
        *,
        fallback_summary: str,
    ) -> Dict[str, Any]:
        proof_events = [event for event in lifecycle_events if matcher(event)]
        if not proof_events:
            return {
                "proof_chain": [],
                "proof_chain_summary": fallback_summary,
            }

        serialized = [_serialize_proof_chain_event(event) for event in proof_events]
        venue_count = sum(1 for item in serialized if item.get("provenance_level") == "venue_backed")
        dry_run_count = sum(1 for item in serialized if item.get("provenance_level") == "dry_run_only")
        internal_count = sum(1 for item in serialized if item.get("provenance_level") == "internal_only")
        proof_chain_summary = (
            f"{len(serialized)} timeline events · "
            f"venue-backed {venue_count} · dry-run {dry_run_count} · internal {internal_count}"
        )
        return {
            "proof_chain": serialized,
            "proof_chain_summary": proof_chain_summary,
        }

    def _normalize_venue_lane(value: Any) -> str:
        lane = str(value or "").strip().lower()
        if not lane:
            return "unscoped_internal"
        if lane in {"binance", "okx"}:
            return lane
        return lane.replace(" ", "_")

    def _format_venue_lane_label(lane_key: str) -> str:
        if lane_key == "binance":
            return "Binance"
        if lane_key == "okx":
            return "OKX"
        if lane_key == "unscoped_internal":
            return "Unscoped internal"
        return lane_key.replace("_", " ").title()

    def _extract_artifact_lane_keys(entry: Dict[str, Any]) -> List[str]:
        lane_keys = {
            _normalize_venue_lane(item.get("exchange"))
            for item in (entry.get("proof_chain") or [])
            if item.get("exchange")
        }
        evidence = entry.get("evidence") or {}
        if isinstance(evidence, dict) and evidence.get("exchange"):
            lane_keys.add(_normalize_venue_lane(evidence.get("exchange")))
        if not lane_keys:
            lane_keys.add("unscoped_internal")
        return sorted(lane_keys)

    def _build_lane_remediation_contract(
        lane_key: str,
        lane_status: str,
        missing_keys: List[str],
        venue_backed_count: int,
    ) -> Dict[str, Any]:
        lane_label = _format_venue_lane_label(lane_key)
        missing_summary = " / ".join(missing_keys) if missing_keys else "none"
        if lane_status == "baseline_incomplete":
            return {
                "focus": "baseline_contract",
                "priority": "P0",
                "operator_action_summary": f"先補齊 {lane_label} baseline artifact，否則 restart replay 沒有可信起點。",
                "operator_instruction": (
                    f"補齊 {lane_label} 的 validation_passed / venue_ack / trade_history_persisted；"
                    f"目前缺口 {missing_summary}。若 exchange tagging 還沒進 lifecycle event，先修 order_manager / execution_service 的 venue 標記。"
                ),
                "verify_instruction": (
                    f"重刷 /api/status，確認 {lane_label} lane 變成 baseline_ready，且 missing required 不再列出 {missing_summary}。"
                ),
                "operator_next_check": "先看 lane missing required，再對照 artifact checklist proof chain。",
            }
        if lane_status == "baseline_ready_missing_path":
            return {
                "focus": "path_artifact_capture",
                "priority": "P0",
                "operator_action_summary": f"{lane_label} baseline 已齊，但還缺真實 path artifact。",
                "operator_instruction": (
                    f"用 {lane_label} 的真實/沙盒委託刻意捕捉 partial_fill 或 cancel_ack→canceled path，"
                    "讓 timeline 不再只有 validation/ack/trade_history。"
                ),
                "verify_instruction": (
                    f"重刷 /api/status，確認 {lane_label} lane 的 path observed > 0，且 timeline 出現 partial_fill / cancel 相關 event。"
                ),
                "operator_next_check": "先看 lane timeline 是否仍停在 trade_history_persisted。",
            }
        if lane_status == "path_observed_internal_only":
            return {
                "focus": "venue_backed_provenance",
                "priority": "P0",
                "operator_action_summary": f"{lane_label} 已看到 path，但證據仍停在 internal/dry-run。",
                "operator_instruction": (
                    f"把 {lane_label} venue adapter / execution service 的原始 ack/fill/cancel payload 寫進 lifecycle artifact，"
                    f"避免只剩 internal proof。當前 venue-backed artifact = {venue_backed_count}。"
                ),
                "verify_instruction": (
                    f"重刷 /api/status，確認 {lane_label} lane status 變成 venue_backed_path_ready，且 provenance venue-backed > 0。"
                ),
                "operator_next_check": "優先比對 lane artifacts 的 provenance_level，確認不再只有 dry_run_only/internal_only。",
            }
        return {
            "focus": "restart_replay_validation",
            "priority": "P1",
            "operator_action_summary": f"{lane_label} 已具備 venue-backed path，下一步是持續驗證 restart replay。",
            "operator_instruction": (
                f"保持 {lane_label} lane 的 partial_fill / cancel / restart replay 真實證據鏈，"
                "每次重啟後都要能從 venue-backed timeline 還原 order state。"
            ),
            "verify_instruction": (
                f"重刷 /api/status，確認 {lane_label} lane 仍維持 venue_backed_path_ready，且 restart_replay_status 不退回 blocked。"
            ),
            "operator_next_check": "定期核對 lane summary、timeline 與 artifact provenance 是否仍一致。",
        }

    def _build_venue_lanes(artifact_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not artifact_entries and not lifecycle_events and last_order is None and latest_trade is None:
            return {
                "venue_lanes_summary": "尚未建立任何 venue closure lane；先捕捉第一筆 runtime order。",
                "venue_lanes": [],
            }

        lane_keys = {
            _normalize_venue_lane(getattr(event, "exchange", None))
            for event in lifecycle_events
            if getattr(event, "exchange", None)
        }
        if getattr(latest_trade, "exchange", None):
            lane_keys.add(_normalize_venue_lane(getattr(latest_trade, "exchange", None)))
        if isinstance(last_order, dict) and last_order.get("exchange"):
            lane_keys.add(_normalize_venue_lane(last_order.get("exchange")))
        lane_keys.update(
            lane_key
            for entry in artifact_entries
            for lane_key in _extract_artifact_lane_keys(entry)
        )
        if not lane_keys:
            lane_keys = {"unscoped_internal"}

        preferred_order = {"binance": 0, "okx": 1, "unscoped_internal": 99}
        baseline_keys = {"validation_passed", "venue_ack", "trade_history_persisted"}
        path_keys = {"partial_fill", "cancel"}
        venue_lanes: List[Dict[str, Any]] = []

        for lane_key in sorted(lane_keys, key=lambda item: (preferred_order.get(item, 50), item)):
            lane_artifacts = [
                entry
                for entry in artifact_entries
                if lane_key in _extract_artifact_lane_keys(entry)
            ]
            lane_timeline_events = [
                _serialize_proof_chain_event(event)
                for event in lifecycle_events
                if _normalize_venue_lane(getattr(event, "exchange", None)) == lane_key
            ]
            if not lane_artifacts and not lane_timeline_events and lane_key != "unscoped_internal":
                continue
            baseline_entries = [entry for entry in lane_artifacts if str(entry.get("key") or "") in baseline_keys]
            baseline_required = sum(1 for entry in baseline_entries if entry.get("required"))
            baseline_observed = sum(1 for entry in baseline_entries if entry.get("observed"))
            path_entries = [entry for entry in lane_artifacts if str(entry.get("key") or "") in path_keys]
            path_observed = sum(1 for entry in path_entries if entry.get("observed"))
            restart_entry = next((entry for entry in lane_artifacts if str(entry.get("key") or "") == "restart_replay"), None)
            venue_backed_count = sum(1 for entry in lane_artifacts if entry.get("provenance_level") == "venue_backed")
            dry_run_count = sum(1 for entry in lane_artifacts if entry.get("provenance_level") == "dry_run_only")
            internal_count = sum(1 for entry in lane_artifacts if entry.get("provenance_level") == "internal_only")
            missing_keys = [
                str(entry.get("key") or "")
                for entry in lane_artifacts
                if entry.get("required") and not entry.get("observed")
            ]
            lane_artifact_drilldown_summary = (
                f"artifacts {len(lane_artifacts)} · observed {sum(1 for entry in lane_artifacts if entry.get('observed'))} · "
                f"required missing {len(missing_keys)}"
            )
            lane_timeline_summary = (
                f"timeline {len(lane_timeline_events)} events · latest "
                f"{lane_timeline_events[-1].get('event_type') if lane_timeline_events else 'none'}"
            )
            if baseline_required > 0 and baseline_observed < baseline_required:
                lane_status = "baseline_incomplete"
                next_artifact = missing_keys[0] if missing_keys else "backfill_required_lifecycle_events"
            elif path_observed <= 0:
                lane_status = "baseline_ready_missing_path"
                next_artifact = "partial_fill_or_cancel"
            elif venue_backed_count <= 0:
                lane_status = "path_observed_internal_only"
                next_artifact = "venue_backed_path_artifact"
            else:
                lane_status = "venue_backed_path_ready"
                next_artifact = "keep_validating_live_lifecycle"
            lane_label = _format_venue_lane_label(lane_key)
            lane_summary = (
                f"{lane_label}: baseline {baseline_observed}/{baseline_required or 0} · "
                f"path {path_observed}/2 · replay {restart_entry.get('status') if restart_entry else 'not_applicable'} · "
                f"venue-backed {venue_backed_count}"
            )
            remediation = _build_lane_remediation_contract(
                lane_key,
                lane_status,
                missing_keys,
                venue_backed_count,
            )
            venue_lanes.append(
                {
                    "venue": lane_key,
                    "label": lane_label,
                    "status": lane_status,
                    "summary": lane_summary,
                    "baseline_ready": baseline_required > 0 and baseline_observed >= baseline_required,
                    "baseline_observed": baseline_observed,
                    "baseline_required": baseline_required,
                    "path_observed": path_observed,
                    "path_expected": 2,
                    "restart_replay_status": restart_entry.get("status") if restart_entry else "not_applicable",
                    "operator_next_artifact": next_artifact,
                    "operator_action_summary": remediation["operator_action_summary"],
                    "operator_instruction": remediation["operator_instruction"],
                    "verify_instruction": remediation["verify_instruction"],
                    "operator_next_check": remediation["operator_next_check"],
                    "remediation_focus": remediation["focus"],
                    "remediation_priority": remediation["priority"],
                    "missing_required_artifacts": missing_keys,
                    "artifact_count": len(lane_artifacts),
                    "artifact_keys": [str(entry.get("key") or "") for entry in lane_artifacts],
                    "artifact_drilldown_summary": lane_artifact_drilldown_summary,
                    "timeline_count": len(lane_timeline_events),
                    "timeline_summary": lane_timeline_summary,
                    "timeline_events": lane_timeline_events,
                    "provenance_counts": {
                        "venue_backed": venue_backed_count,
                        "dry_run_only": dry_run_count,
                        "internal_only": internal_count,
                        "missing_or_not_applicable": sum(
                            1
                            for entry in lane_artifacts
                            if str(entry.get("provenance_level") or "") in {"missing", "not_applicable"}
                        ),
                    },
                    "artifacts": lane_artifacts,
                }
            )

        if not venue_lanes:
            venue_lanes.append(
                {
                    "venue": "unscoped_internal",
                    "label": "Unscoped internal",
                    "status": "baseline_incomplete",
                    "summary": "Unscoped internal: 尚未建立任何 venue-scoped artifact。",
                    "baseline_ready": False,
                    "baseline_observed": 0,
                    "baseline_required": 0,
                    "path_observed": 0,
                    "path_expected": 2,
                    "restart_replay_status": "not_applicable",
                    "operator_next_artifact": "capture_first_runtime_order",
                    "operator_action_summary": "先捕捉第一筆 runtime order，建立 unscoped internal baseline。",
                    "operator_instruction": "先讓 execution service 真正落下一筆 order 與 lifecycle event，再開始檢查 venue-scoped artifact。",
                    "verify_instruction": "重刷 /api/status，確認 venue lanes 不再是空集合，且 lane summary 開始出現 baseline / path 計數。",
                    "operator_next_check": "先確認 lifecycle timeline 已有 validation_passed 或 trade_history_persisted。",
                    "remediation_focus": "runtime_bootstrap",
                    "remediation_priority": "P0",
                    "missing_required_artifacts": [],
                    "artifact_count": 0,
                    "artifact_keys": [],
                    "artifact_drilldown_summary": "artifacts 0 · observed 0 · required missing 0",
                    "timeline_count": 0,
                    "timeline_summary": "timeline 0 events · latest none",
                    "timeline_events": [],
                    "provenance_counts": {
                        "venue_backed": 0,
                        "dry_run_only": 0,
                        "internal_only": 0,
                        "missing_or_not_applicable": 0,
                    },
                    "artifacts": [],
                }
            )

        venue_lanes_summary = " · ".join(lane.get("summary") or lane.get("label") or "lane" for lane in venue_lanes)
        return {
            "venue_lanes_summary": venue_lanes_summary,
            "venue_lanes": venue_lanes,
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
            "artifact_provenance_summary": "venue-backed 0 · dry-run only 0 · internal-only 0 · missing/not-applicable 2",
            "artifact_provenance_counts": {
                "venue_backed": 0,
                "dry_run_only": 0,
                "internal_only": 0,
                "missing": 1,
                "not_applicable": 1,
            },
            "artifact_checklist": [
                {
                    "key": "capture_first_runtime_order",
                    "label": "Capture first runtime order",
                    "status": "not_applicable",
                    "required": True,
                    "observed": False,
                    "count": 0,
                    "summary": "目前沒有 runtime order，因此無法建立 validation / replay checklist。",
                    "provenance_level": "missing",
                    "provenance_summary": "尚未建立 runtime order，因此沒有任何 artifact provenance。",
                    "venue_backed": False,
                    "proof_chain_summary": "尚未建立 runtime order，因此沒有任何 timeline proof chain。",
                    "proof_chain": [],
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
                    "provenance_level": "not_applicable",
                    "provenance_summary": "目前沒有 runtime order，restart replay provenance 不適用。",
                    "venue_backed": False,
                    "proof_chain_summary": "目前沒有 runtime order，restart replay proof chain 不適用。",
                    "proof_chain": [],
                    "evidence": None,
                },
            ],
            "venue_lanes_summary": "尚未建立任何 venue closure lane；先捕捉第一筆 runtime order。",
            "venue_lanes": [],
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
    artifact_provenance_counts = {
        "venue_backed": 0,
        "dry_run_only": 0,
        "internal_only": 0,
        "missing": 0,
        "not_applicable": 0,
    }

    def _append_artifact(entry: Dict[str, Any]) -> None:
        provenance_level = str(entry.get("provenance_level") or "missing")
        artifact_provenance_counts[provenance_level] = int(artifact_provenance_counts.get(provenance_level, 0)) + 1
        artifact_checklist.append(entry)

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
        provenance = _event_provenance(latest_event_by_type.get(event_type)) if observed else {
            "level": "missing" if required else "not_applicable",
            "venue_backed": False,
            "exchange": None,
            "source": None,
            "is_dry_run": None,
            "summary": (
                f"{label} 是 replay baseline 必要證據，當前仍缺失。"
                if required
                else f"當前 runtime path 不要求 {label}。"
            ),
        }
        proof_chain_data = _build_proof_chain(
            lambda event, expected_event_type=event_type: str(getattr(event, "event_type", "") or "unknown") == expected_event_type,
            fallback_summary=(
                f"尚未找到 {label} 的 timeline proof chain。"
                if required or observed
                else f"當前 runtime path 不要求 {label} proof chain。"
            ),
        )
        _append_artifact(
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
                "provenance_level": provenance["level"],
                "provenance_summary": provenance["summary"],
                "venue_backed": provenance["venue_backed"],
                "proof_chain_summary": proof_chain_data["proof_chain_summary"],
                "proof_chain": proof_chain_data["proof_chain"],
                "evidence": _event_evidence(latest_event_by_type.get(event_type)),
            }
        )

    partial_fill_provenance = _event_provenance(partial_fill_event) if partial_fill_observed else {
        "level": "missing",
        "venue_backed": False,
        "summary": (
            "baseline 已就緒，但尚未看到 partial fill path；仍需補充 venue path evidence。"
            if baseline_contract_status == "complete"
            else "先補齊 baseline lifecycle，再追 partial fill / cancel path artifact。"
        ),
    }
    partial_fill_chain = _build_proof_chain(
        lambda event: _normalize_order_state(getattr(event, "order_state", None)) == "partially_filled"
        or str(getattr(event, "event_type", "") or "unknown") == "partial_fill",
        fallback_summary=(
            "baseline 已就緒，但 partial fill timeline proof chain 仍缺失。"
            if baseline_contract_status == "complete"
            else "先補齊 baseline lifecycle，再追 partial fill proof chain。"
        ),
    )
    _append_artifact(
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
            "provenance_level": partial_fill_provenance["level"],
            "provenance_summary": partial_fill_provenance["summary"],
            "venue_backed": partial_fill_provenance["venue_backed"],
            "proof_chain_summary": partial_fill_chain["proof_chain_summary"],
            "proof_chain": partial_fill_chain["proof_chain"],
            "evidence": _event_evidence(partial_fill_event),
        }
    )
    cancel_provenance = _event_provenance(cancel_event) if cancel_observed else {
        "level": "missing",
        "venue_backed": False,
        "summary": (
            "baseline 已就緒，但尚未看到 cancel path；仍需補充 venue cancel evidence。"
            if baseline_contract_status == "complete"
            else "先補齊 baseline lifecycle，再追 partial fill / cancel path artifact。"
        ),
    }
    cancel_chain = _build_proof_chain(
        lambda event: _normalize_order_state(getattr(event, "order_state", None)) == "canceled"
        or str(getattr(event, "event_type", "") or "unknown") in {"canceled", "cancel_ack", "cancelled"},
        fallback_summary=(
            "baseline 已就緒，但 cancel timeline proof chain 仍缺失。"
            if baseline_contract_status == "complete"
            else "先補齊 baseline lifecycle，再追 cancel proof chain。"
        ),
    )
    _append_artifact(
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
            "provenance_level": cancel_provenance["level"],
            "provenance_summary": cancel_provenance["summary"],
            "venue_backed": cancel_provenance["venue_backed"],
            "proof_chain_summary": cancel_chain["proof_chain_summary"],
            "proof_chain": cancel_chain["proof_chain"],
            "evidence": _event_evidence(cancel_event),
        }
    )
    terminal_provenance = _event_provenance(terminal_event) if terminal_state_observed else {
        "level": "missing" if runtime_state != "absent" else "not_applicable",
        "venue_backed": False,
        "summary": (
            "目前尚未觀察到 terminal state；若 order 仍 open，需持續追蹤後續 lifecycle。"
            if runtime_state != "absent"
            else "目前沒有 runtime order，terminal state 不適用。"
        ),
    }
    terminal_chain = _build_proof_chain(
        lambda event: _normalize_order_state(getattr(event, "order_state", None)) in {"closed", "canceled", "rejected", "expired"},
        fallback_summary=(
            "目前尚未建立 terminal state timeline proof chain。"
            if runtime_state != "absent"
            else "目前沒有 runtime order，terminal state proof chain 不適用。"
        ),
    )
    _append_artifact(
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
            "provenance_level": terminal_provenance["level"],
            "provenance_summary": terminal_provenance["summary"],
            "venue_backed": terminal_provenance["venue_backed"],
            "proof_chain_summary": terminal_chain["proof_chain_summary"],
            "proof_chain": terminal_chain["proof_chain"],
            "evidence": _event_evidence(terminal_event),
        }
    )
    restart_provenance_level = (
        "venue_backed"
        if replay_readiness == "ready" and artifact_provenance_counts.get("venue_backed", 0) > 0
        else (
            "internal_only"
            if replay_readiness == "ready"
            else ("missing" if replay_readiness == "blocked" else "not_applicable")
        )
    )
    restart_provenance_summary = (
        "restart replay 已 ready，且當前 lifecycle 中已有 venue-backed artifact。"
        if replay_readiness == "ready" and restart_provenance_level == "venue_backed"
        else (
            "restart replay 已 ready，但目前觀察到的 closure 仍以 dry-run / internal artifact 為主。"
            if replay_readiness == "ready"
            else (
                f"restart replay 仍被擋下：{replay_readiness_reason}。"
                if replay_readiness == "blocked"
                else "目前沒有 runtime order，restart replay 不適用。"
            )
        )
    )
    restart_chain = _build_proof_chain(
        lambda event: True,
        fallback_summary=(
            "目前沒有 runtime order，restart replay proof chain 不適用。"
            if runtime_state == "absent"
            else "尚未建立 restart replay 所需的 lifecycle proof chain。"
        ),
    )
    _append_artifact(
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
            "provenance_level": restart_provenance_level,
            "provenance_summary": restart_provenance_summary,
            "venue_backed": artifact_provenance_counts.get("venue_backed", 0) > 0,
            "proof_chain_summary": restart_chain["proof_chain_summary"],
            "proof_chain": restart_chain["proof_chain"],
            "evidence": {
                "order_id": _record_text(last_order, "order_id") or getattr(latest_trade, "order_id", None),
                "client_order_id": _record_text(last_order, "client_order_id") or getattr(latest_trade, "client_order_id", None),
                "reason": replay_readiness_reason,
                "operator_next_artifact": operator_next_artifact,
            },
        }
    )

    artifact_provenance_summary = (
        f"venue-backed {artifact_provenance_counts.get('venue_backed', 0)} · "
        f"dry-run only {artifact_provenance_counts.get('dry_run_only', 0)} · "
        f"internal-only {artifact_provenance_counts.get('internal_only', 0)} · "
        f"missing/not-applicable {artifact_provenance_counts.get('missing', 0) + artifact_provenance_counts.get('not_applicable', 0)}"
    )

    artifact_checklist_summary = (
        f"baseline {baseline_observed_count}/{baseline_required_count or 0} ready · "
        f"path artifacts {path_observed_count}/2 observed · "
        f"restart replay {replay_readiness}"
    )
    venue_lane_data = _build_venue_lanes(artifact_checklist)

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
        "artifact_provenance_summary": artifact_provenance_summary,
        "artifact_provenance_counts": artifact_provenance_counts,
        "artifact_checklist": artifact_checklist,
        "venue_lanes_summary": venue_lane_data["venue_lanes_summary"],
        "venue_lanes": venue_lane_data["venue_lanes"],
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
            } if latest_trade is not None else None,
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


@router.get("/predict/confidence")
async def get_confidence_prediction() -> Dict[str, Any]:
    from config import load_config
    from database.models import init_db
    from model import predictor as predictor_module

    cfg = load_config() or {}
    database_url = ((cfg.get("database") or {}).get("url")) or "sqlite:///poly_trader.db"
    session = init_db(database_url)
    try:
        loaded = _get_loaded_predictor_cached()
        if isinstance(loaded, tuple):
            predictor = loaded[0]
            regime_models = loaded[1] if len(loaded) > 1 else None
        else:
            predictor = loaded
            regime_models = None
        result = predictor_module.predict(session, predictor, regime_models)
        result = result if isinstance(result, dict) else {}
        result = _enrich_confidence_with_q15_support_audit(dict(result))
        result = _overlay_confidence_with_live_predict_probe(result)
        result = _enrich_confidence_with_q35_scaling_audit(dict(result))
        return _enrich_confidence_with_q15_bucket_root_cause(dict(result))
    finally:
        close = getattr(session, "close", None)
        if callable(close):
            close()


@router.get("/status")
async def api_status() -> Dict[str, Any]:
    cfg = get_config() or {}
    trading_cfg = cfg.get("trading") if isinstance(cfg.get("trading"), dict) else {}
    symbol = str(trading_cfg.get("symbol") or "BTCUSDT")
    status_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    db = get_db()

    execution_service = ExecutionService(cfg, db_session=db)
    execution_summary = execution_service.execution_summary() if hasattr(execution_service, "execution_summary") else {}
    execution_summary = execution_summary if isinstance(execution_summary, dict) else {}
    execution_summary.setdefault("guardrails", {})
    execution_summary["guardrails"].setdefault("consecutive_failures", 0)

    account_sync = AccountSyncService(cfg)
    account_snapshot = account_sync.snapshot(symbol=symbol) if hasattr(account_sync, "snapshot") else {}
    account_snapshot = account_snapshot if isinstance(account_snapshot, dict) else {}

    maybe_confidence_payload = get_confidence_prediction()
    confidence_payload = await maybe_confidence_payload if hasattr(maybe_confidence_payload, "__await__") else maybe_confidence_payload
    live_runtime_truth = _build_live_runtime_closure_surface(confidence_payload)
    recent_canonical_drift = _load_recent_canonical_drift_summary()
    execution_summary["live_runtime_truth"] = live_runtime_truth
    execution_summary["recent_canonical_drift"] = recent_canonical_drift

    execution_reconciliation = _build_execution_reconciliation_summary(db, symbol, account_snapshot, execution_summary)
    metadata_smoke = _ensure_execution_metadata_smoke_governance(cfg, symbol)
    execution_surface_contract = _build_execution_surface_contract()
    execution_surface_contract["live_runtime_truth"] = live_runtime_truth
    execution_surface_contract["recent_canonical_drift"] = recent_canonical_drift
    operator_message = execution_surface_contract.get("operator_message") or ""
    if live_runtime_truth.get("runtime_closure_state") == "capacity_opened_signal_hold":
        operator_message = f"{operator_message} 目前 runtime 已開出 1 層 deployment capacity，但 signal 仍是 HOLD。".strip()
    execution_surface_contract["operator_message"] = operator_message

    return {
        "automation": bool(is_automation_enabled()),
        "dry_run": bool(trading_cfg.get("dry_run", False)),
        "symbol": symbol,
        "timestamp": status_timestamp,
        "execution": execution_summary,
        "account": account_snapshot,
        "raw_continuity": get_runtime_status("raw_continuity", {"status": "unknown"}),
        "feature_continuity": get_runtime_status("feature_continuity", {"status": "unknown"}),
        "execution_reconciliation": execution_reconciliation,
        "execution_metadata_smoke": metadata_smoke,
        "execution_surface_contract": execution_surface_contract,
        "recent_canonical_drift": recent_canonical_drift,
    }


@router.get("/execution/overview")
async def api_execution_overview() -> Dict[str, Any]:
    cfg = get_config() or {}
    status_payload = await api_status()
    base_overview = build_execution_overview(status_payload, config=cfg)
    db = get_db()
    control_plane = build_execution_control_plane_snapshot(db, status_payload, base_overview)
    return build_execution_overview(status_payload, config=cfg, control_plane=control_plane)


@router.get("/execution/strategies/source")
async def api_execution_strategy_source() -> Dict[str, Any]:
    return build_execution_strategy_source_snapshot()


@router.get("/execution/profiles")
async def api_execution_profiles() -> Dict[str, Any]:
    cfg = get_config() or {}
    status_payload = await api_status()
    base_overview = build_execution_overview(status_payload, config=cfg)
    db = get_db()
    control_plane = build_execution_control_plane_snapshot(db, status_payload, base_overview)
    return {
        "controls_mode": control_plane.get("controls_mode"),
        "operator_message": control_plane.get("operator_message"),
        "upgrade_prerequisite": control_plane.get("upgrade_prerequisite"),
        "summary": control_plane.get("summary"),
        "profiles": control_plane.get("profiles"),
    }


@router.get("/execution/runs")
async def api_execution_runs() -> Dict[str, Any]:
    cfg = get_config() or {}
    status_payload = await api_status()
    base_overview = build_execution_overview(status_payload, config=cfg)
    db = get_db()
    control_plane = build_execution_control_plane_snapshot(db, status_payload, base_overview)
    return {
        "controls_mode": control_plane.get("controls_mode"),
        "operator_message": control_plane.get("operator_message"),
        "upgrade_prerequisite": control_plane.get("upgrade_prerequisite"),
        "summary": control_plane.get("summary"),
        "profiles": control_plane.get("profiles"),
        "runs": control_plane.get("runs"),
    }


@router.post("/execution/runs/{profile_id}/start")
async def api_execution_start_run(profile_id: str, request: Request = None) -> Dict[str, Any]:
    _assert_local_operator_request(request)
    cfg = get_config() or {}
    status_payload = await api_status()
    base_overview = build_execution_overview(status_payload, config=cfg)
    db = get_db()
    return start_execution_profile_run(db, profile_id, status_payload, base_overview)


@router.post("/execution/runs/{run_id}/pause")
async def api_execution_pause_run(run_id: str, request: Request = None) -> Dict[str, Any]:
    _assert_local_operator_request(request)
    status_payload = await api_status()
    db = get_db()
    result = pause_execution_run(db, run_id, status_payload=status_payload)
    return {
        "action": "pause",
        "operator_message": "已更新 execution run 為 paused。",
        **result,
    }


@router.post("/execution/runs/{run_id}/stop")
async def api_execution_stop_run(run_id: str, request: Request = None) -> Dict[str, Any]:
    _assert_local_operator_request(request)
    status_payload = await api_status()
    db = get_db()
    result = stop_execution_run(db, run_id, status_payload=status_payload)
    return {
        "action": "stop",
        "operator_message": "已更新 execution run 為 stopped。",
        **result,
    }


@router.get("/execution/runs/{run_id}")
async def api_execution_run_detail(run_id: str) -> Dict[str, Any]:
    status_payload = await api_status()
    db = get_db()
    return get_execution_run_detail(db, run_id, status_payload=status_payload)


# ─── Models ───

_OVERFIT_GAP_THRESHOLD = 0.12
_OVERFIT_ACCURACY_THRESHOLD = 0.90
_MODEL_LEADERBOARD_HISTORY_LIMIT = 10
_MODEL_TIER_LABELS = {
    "xgboost": ("core", "核心模型"),
    "lightgbm": ("core", "核心模型"),
    "catboost": ("core", "核心模型"),
    "random_forest": ("core", "核心模型"),
    "logistic_regression": ("core", "核心模型"),
    "ensemble": ("core", "核心模型"),
    "rule_baseline": ("baseline", "基線模型"),
}


def _sqlite_table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    except sqlite3.Error:
        return []
    return [str(row[1]) for row in rows]



def _read_sql_frame(conn: sqlite3.Connection, query: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(query, conn)
    except Exception:
        return pd.DataFrame()



def _normalize_timestamp_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "timestamp" not in df.columns:
        return df
    normalized = df.copy()
    normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], format="mixed", errors="coerce")
    normalized = normalized.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return normalized



def _first_non_null_per_timestamp(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    if df.empty or value_col not in df.columns or "timestamp" not in df.columns:
        return pd.DataFrame(columns=["timestamp", value_col])
    subset = df[["timestamp", value_col]].copy()
    subset = subset.dropna(subset=[value_col])
    if subset.empty:
        return pd.DataFrame(columns=["timestamp", value_col])
    return subset.drop_duplicates(subset=["timestamp"], keep="first").reset_index(drop=True)



def load_model_leaderboard_frame(db_path: Optional[str] = None) -> pd.DataFrame:
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    try:
        feature_columns = _sqlite_table_columns(conn, "features_normalized")
        raw_columns = _sqlite_table_columns(conn, "raw_market_data")
        label_columns = _sqlite_table_columns(conn, "labels")
        if not feature_columns:
            return pd.DataFrame()

        selected_feature_cols = [
            col for col in [
                "timestamp",
                "symbol",
                "regime_label",
                "feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body", "feat_pulse", "feat_aura", "feat_mind",
                "feat_vix", "feat_dxy",
                "feat_rsi14", "feat_macd_hist", "feat_atr_pct", "feat_vwap_dev", "feat_bb_pct_b",
                "feat_nw_width", "feat_nw_slope", "feat_adx", "feat_choppiness", "feat_donchian_pos",
                "feat_4h_bias50", "feat_4h_bias20", "feat_4h_bias200", "feat_4h_rsi14", "feat_4h_macd_hist",
                "feat_4h_bb_pct_b", "feat_4h_dist_bb_lower", "feat_4h_ma_order", "feat_4h_dist_swing_low", "feat_4h_vol_ratio",
                "feat_local_bottom_score", "feat_local_top_score", "feat_turning_point_score",
            ] if col in feature_columns
        ]
        features_df = _read_sql_frame(
            conn,
            f"SELECT {', '.join(selected_feature_cols)} FROM features_normalized ORDER BY timestamp"
        )
        features_df = _normalize_timestamp_frame(features_df)
        if features_df.empty:
            return features_df

        if {"timestamp", "symbol", "close_price"}.issubset(set(raw_columns)):
            raw_df = _read_sql_frame(
                conn,
                "SELECT timestamp, symbol, close_price FROM raw_market_data ORDER BY timestamp"
            )
            raw_df = _normalize_timestamp_frame(raw_df)
            if not raw_df.empty:
                raw_df = raw_df.drop_duplicates(subset=["timestamp", "symbol"], keep="last")
                features_df = features_df.merge(raw_df, on=["timestamp", "symbol"], how="left")
        elif "close_price" not in features_df.columns:
            features_df["close_price"] = None

        wanted_label_cols = [
            col for col in [
                "timestamp",
                "symbol",
                "horizon_minutes",
                "label_spot_long_win",
                "simulated_pyramid_win",
                "simulated_pyramid_pnl",
                "simulated_pyramid_quality",
                "simulated_pyramid_drawdown_penalty",
                "simulated_pyramid_time_underwater",
            ] if col in label_columns
        ]
        if wanted_label_cols:
            label_query = f"SELECT {', '.join(wanted_label_cols)} FROM labels"
            if "horizon_minutes" in wanted_label_cols:
                label_query += " WHERE horizon_minutes = 1440 OR horizon_minutes IS NULL"
            label_query += " ORDER BY timestamp"
            labels_df = _read_sql_frame(conn, label_query)
            labels_df = _normalize_timestamp_frame(labels_df)
            if not labels_df.empty:
                dedupe_cols = [col for col in ["timestamp", "symbol"] if col in labels_df.columns]
                if dedupe_cols:
                    labels_df = labels_df.drop_duplicates(subset=dedupe_cols, keep="last")
                merge_cols = [col for col in ["timestamp", "symbol"] if col in labels_df.columns and col in features_df.columns]
                if merge_cols:
                    features_df = features_df.merge(labels_df, on=merge_cols, how="left")
                fallback_ts = labels_df[[col for col in labels_df.columns if col != "symbol"]].copy()
                for label_col in [
                    "label_spot_long_win",
                    "simulated_pyramid_win",
                    "simulated_pyramid_pnl",
                    "simulated_pyramid_quality",
                    "simulated_pyramid_drawdown_penalty",
                    "simulated_pyramid_time_underwater",
                ]:
                    if label_col not in fallback_ts.columns:
                        continue
                    fallback_df = _first_non_null_per_timestamp(fallback_ts, label_col)
                    if fallback_df.empty:
                        continue
                    fallback_name = f"__fallback_{label_col}"
                    features_df = features_df.merge(
                        fallback_df.rename(columns={label_col: fallback_name}),
                        on="timestamp",
                        how="left",
                    )
                    if label_col not in features_df.columns:
                        features_df[label_col] = features_df[fallback_name]
                    else:
                        features_df[label_col] = features_df[label_col].where(features_df[label_col].notna(), features_df[fallback_name])
                    features_df = features_df.drop(columns=[fallback_name])

        return features_df.sort_values("timestamp").reset_index(drop=True)
    finally:
        conn.close()



def _serialize_model_scores(scores: List[Any], leaderboard) -> List[Dict[str, Any]]:
    def _serialize_fold_result(fold: Any) -> Dict[str, Any]:
        if hasattr(fold, "__dataclass_fields__"):
            return asdict(fold)
        if isinstance(fold, dict):
            return dict(fold)
        data = getattr(fold, "__dict__", None)
        if isinstance(data, dict):
            return dict(data)
        return {"value": str(fold)}

    payload: List[Dict[str, Any]] = []
    for idx, score in enumerate(scores or [], start=1):
        model_name = str(getattr(score, "model_name", "unknown"))
        model_tier, model_tier_label = _MODEL_TIER_LABELS.get(model_name, ("research", "研究模型"))
        status = {}
        if leaderboard is not None:
            status = getattr(leaderboard, "last_model_statuses", {}).get(model_name, {}) or {}
        selected_deployment_profile = status.get("selected_deployment_profile", getattr(score, "deployment_profile", "standard"))
        selected_deployment_profile_label = status.get(
            "selected_deployment_profile_label",
            getattr(score, "deployment_profile_label", selected_deployment_profile),
        )
        selected_deployment_profile_source = status.get(
            "selected_deployment_profile_source",
            getattr(score, "deployment_profile_source", "code_backed"),
        )
        item = {
            "rank": idx,
            "rank_delta": 0,
            "model_name": model_name,
            "deployment_profile": getattr(score, "deployment_profile", selected_deployment_profile),
            "deployment_profile_label": getattr(score, "deployment_profile_label", selected_deployment_profile_label),
            "deployment_profile_source": getattr(score, "deployment_profile_source", selected_deployment_profile_source),
            "selected_deployment_profile": selected_deployment_profile,
            "selected_deployment_profile_label": selected_deployment_profile_label,
            "selected_deployment_profile_source": selected_deployment_profile_source,
            "feature_profile": getattr(score, "feature_profile", status.get("selected_feature_profile", "current_full")),
            "feature_profile_source": getattr(score, "feature_profile_source", status.get("selected_feature_profile_source", "code_default")),
            "selected_feature_profile": status.get("selected_feature_profile", getattr(score, "feature_profile", "current_full")),
            "selected_feature_profile_source": status.get("selected_feature_profile_source", getattr(score, "feature_profile_source", "code_default")),
            "selected_feature_profile_blocker_applied": bool(status.get("selected_feature_profile_blocker_applied", False)),
            "selected_feature_profile_blocker_reason": status.get("selected_feature_profile_blocker_reason"),
            "deployment_profiles_evaluated": status.get("deployment_profiles_evaluated", [getattr(score, "deployment_profile", "standard")]),
            "feature_profiles_evaluated": status.get("feature_profiles_evaluated", [getattr(score, "feature_profile", "current_full")]),
            "feature_profile_candidate_diagnostics": status.get("feature_profile_candidate_diagnostics", []),
            "feature_profile_support_cohort": status.get("feature_profile_support_cohort"),
            "feature_profile_support_rows": status.get("feature_profile_support_rows"),
            "feature_profile_exact_live_bucket_rows": status.get("feature_profile_exact_live_bucket_rows"),
            "evaluation_fold_window": status.get("evaluation_fold_window"),
            "evaluation_fold_indices": status.get("evaluation_fold_indices", []),
            "evaluation_fold_count": status.get("evaluation_fold_count"),
            "avg_roi": float(getattr(score, "avg_roi", 0.0) or 0.0),
            "avg_win_rate": float(getattr(score, "avg_win_rate", 0.0) or 0.0),
            "avg_trades": float(getattr(score, "avg_trades", 0.0) or 0.0),
            "avg_max_drawdown": float(getattr(score, "avg_max_drawdown", 0.0) or 0.0),
            "avg_profit_factor": float(getattr(score, "avg_profit_factor", 0.0) or 0.0),
            "avg_entry_quality": float(getattr(score, "avg_entry_quality", 0.0) or 0.0),
            "avg_allowed_layers": float(getattr(score, "avg_allowed_layers", 0.0) or 0.0),
            "avg_trade_quality": float(getattr(score, "avg_trade_quality", 0.0) or 0.0),
            "avg_decision_quality_score": float(getattr(score, "avg_decision_quality_score", 0.0) or 0.0),
            "avg_expected_win_rate": float(getattr(score, "avg_expected_win_rate", 0.0) or 0.0),
            "avg_expected_pyramid_quality": float(getattr(score, "avg_expected_pyramid_quality", 0.0) or 0.0),
            "avg_expected_drawdown_penalty": float(getattr(score, "avg_expected_drawdown_penalty", 0.0) or 0.0),
            "avg_expected_time_underwater": float(getattr(score, "avg_expected_time_underwater", 0.0) or 0.0),
            "regime_stability_score": float(getattr(score, "regime_stability_score", 0.0) or 0.0),
            "trade_count_score": float(getattr(score, "trade_count_score", 0.0) or 0.0),
            "roi_score": float(getattr(score, "roi_score", 0.0) or 0.0),
            "max_drawdown_score": float(getattr(score, "max_drawdown_score", 0.0) or 0.0),
            "profit_factor_score": float(getattr(score, "profit_factor_score", 0.0) or 0.0),
            "time_underwater_score": float(getattr(score, "time_underwater_score", 0.0) or 0.0),
            "decision_quality_component": float(getattr(score, "decision_quality_component", 0.0) or 0.0),
            "reliability_score": float(getattr(score, "reliability_score", 0.0) or 0.0),
            "return_power_score": float(getattr(score, "return_power_score", 0.0) or 0.0),
            "risk_control_score": float(getattr(score, "risk_control_score", 0.0) or 0.0),
            "capital_efficiency_score": float(getattr(score, "capital_efficiency_score", 0.0) or 0.0),
            "overall_score": float(getattr(score, "overall_score", getattr(score, "composite_score", 0.0)) or 0.0),
            "overfit_penalty": float(getattr(score, "overfit_penalty", 0.0) or 0.0),
            "std_roi": float(getattr(score, "std_roi", 0.0) or 0.0),
            "train_accuracy": float(getattr(score, "train_accuracy", 0.0) or 0.0),
            "test_accuracy": float(getattr(score, "test_accuracy", 0.0) or 0.0),
            "train_test_gap": float(getattr(score, "train_test_gap", 0.0) or 0.0),
            "composite_score": float(getattr(score, "composite_score", getattr(score, "overall_score", 0.0)) or 0.0),
            "model_tier": model_tier,
            "model_tier_label": model_tier_label,
            "folds": [_serialize_fold_result(fold) for fold in (getattr(score, "folds", []) or [])],
        }
        payload.append(item)
    return payload


def _split_model_leaderboard_rows(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
    comparable_rows: List[Dict[str, Any]] = []
    placeholder_rows: List[Dict[str, Any]] = []

    for source_rank, row in enumerate(rows or [], start=1):
        item = dict(row)
        raw_rank = item.get("rank")
        if raw_rank is None:
            raw_rank = source_rank
        avg_trades_raw = item.get("avg_trades", item.get("avg_total_trades"))
        has_trade_metric = avg_trades_raw is not None
        avg_trades = float(avg_trades_raw or 0.0) if has_trade_metric else None
        ranking_eligible_raw = item.get("ranking_eligible")
        if ranking_eligible_raw is None:
            ranking_eligible = True if not has_trade_metric else avg_trades > 0.0
        else:
            ranking_eligible = bool(ranking_eligible_raw)
        item["ranking_eligible"] = ranking_eligible
        if has_trade_metric:
            item["avg_trades"] = float(avg_trades or 0.0)
            item["avg_total_trades"] = float(avg_trades or 0.0)
        if not ranking_eligible or (has_trade_metric and float(avg_trades or 0.0) <= 0.0):
            item["ranking_status"] = item.get("ranking_status") or "no_trade_placeholder"
            item["placeholder_reason"] = item.get("placeholder_reason") or "no_trades_generated_under_current_deployment_profile"
            item["ranking_warning"] = item.get("ranking_warning") or (
                "此模型在當前 deployment profile 下未產生任何交易；僅作 placeholder 顯示，不納入正常排行榜比較。"
            )
            item["raw_rank"] = raw_rank
            item["rank"] = None
            placeholder_rows.append(item)
            continue
        comparable_rows.append(item)

    for idx, item in enumerate(comparable_rows, start=1):
        item["rank"] = idx

    leaderboard_warning = None
    if comparable_rows and placeholder_rows:
        leaderboard_warning = (
            f"模型排行榜已自動分離 {len(placeholder_rows)} 個 no-trade placeholder；"
            f"目前僅保留 {len(comparable_rows)} 個可比較模型進入正式排名。"
        )
    elif placeholder_rows and not comparable_rows:
        leaderboard_warning = (
            f"目前 {len(placeholder_rows)} 個模型都沒有產生任何交易；"
            "排行榜已降級為 placeholder 檢視，請勿把 #1 當成可部署排名。"
        )

    return comparable_rows, placeholder_rows, leaderboard_warning


def _model_leaderboard_payload_has_rows(payload: Dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    return bool(
        payload.get("leaderboard")
        or payload.get("placeholder_rows")
        or payload.get("placeholder_models")
    )


def _normalize_model_leaderboard_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    raw_rows = list(payload.get("leaderboard") or [])
    if payload.get("placeholder_rows"):
        raw_rows.extend(list(payload.get("placeholder_rows") or []))
    elif payload.get("placeholder_models"):
        raw_rows.extend(list(payload.get("placeholder_models") or []))

    comparable_rows, placeholder_rows, leaderboard_warning = _split_model_leaderboard_rows(raw_rows)
    normalized = dict(payload)
    normalized["leaderboard"] = comparable_rows
    normalized["count"] = len(comparable_rows)
    normalized["comparable_count"] = len(comparable_rows)
    normalized["placeholder_rows"] = placeholder_rows
    normalized["placeholder_models"] = placeholder_rows
    normalized["placeholder_count"] = len(placeholder_rows)
    normalized["evaluated_row_count"] = len(comparable_rows) + len(placeholder_rows)
    normalized["quadrant_points"] = [
        {
            "model_name": row.get("model_name"),
            "reliability_score": row.get("reliability_score"),
            "return_power_score": row.get("return_power_score"),
            "overall_score": row.get("overall_score"),
        }
        for row in comparable_rows
    ]
    snapshot_history = list(normalized.get("snapshot_history") or [])
    if snapshot_history and any(not isinstance(row, dict) or row.get("id") is None for row in snapshot_history):
        normalized["snapshot_history"] = _load_model_leaderboard_history(db_path=DB_PATH)
    resolved_warning = leaderboard_warning or normalized.get("leaderboard_warning") or normalized.get("data_warning")
    normalized["leaderboard_warning"] = resolved_warning
    normalized["data_warning"] = resolved_warning
    # Background refresh now skips expensive target-candidate rescoring. Normalize any
    # stale cached/snapshotted payloads to the same contract so live API consumers do
    # not keep seeing legacy candidate rows until the next full rebuild.
    normalized["target_candidates"] = []
    return normalized


def _choose_best_non_overfit_model(items: List[Dict[str, Any]], overfit_gap_threshold: float, overfit_accuracy_threshold: float) -> Optional[Dict[str, Any]]:

    if not items:
        return None
    non_overfit = [
        item for item in items
        if float(item.get("train_test_gap", 0.0) or 0.0) <= overfit_gap_threshold
        and float(item.get("train_accuracy", 0.0) or 0.0) <= overfit_accuracy_threshold
    ]
    candidates = non_overfit or items
    candidates = sorted(
        candidates,
        key=lambda item: (
            float(item.get("overall_score", item.get("composite_score", 0.0)) or 0.0),
            float(item.get("avg_decision_quality_score", 0.0) or 0.0),
            float(item.get("avg_win_rate", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return candidates[0]



def _summarize_target_candidates(
    data_df: pd.DataFrame,
    overfit_gap_threshold: float = _OVERFIT_GAP_THRESHOLD,
    overfit_accuracy_threshold: float = _OVERFIT_ACCURACY_THRESHOLD,
) -> List[Dict[str, Any]]:
    from backtesting.model_leaderboard import ModelLeaderboard

    summaries: List[Dict[str, Any]] = []
    target_specs = [
        ("simulated_pyramid_win", True, "主訓練 / 主排行榜 target"),
        ("label_spot_long_win", False, "僅供 path-aware 比較診斷，不作 canonical 排名主依據"),
    ]
    for target_col, is_canonical, usage_note in target_specs:
        if target_col not in data_df.columns:
            continue
        target_df = data_df[data_df[target_col].notna()].copy()
        if target_df.empty:
            continue
        leaderboard = ModelLeaderboard(target_df, target_col=target_col, background_refresh=True)
        refresh_models = list(getattr(leaderboard, "REFRESH_MODELS", getattr(leaderboard, "SUPPORTED_MODELS", []) or []))
        scores = leaderboard.run_all_models(refresh_models)
        serialized = _serialize_model_scores(scores, leaderboard)
        best_model = _choose_best_non_overfit_model(serialized, overfit_gap_threshold, overfit_accuracy_threshold)
        summaries.append({
            "target_col": target_col,
            "is_canonical": is_canonical,
            "usage_note": usage_note,
            "best_model": best_model,
            "model_count": len(serialized),
        })
    summaries.sort(key=lambda item: (bool(item.get("is_canonical")), float((item.get("best_model") or {}).get("overall_score", 0.0))), reverse=True)
    return summaries



def _ensure_model_leaderboard_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leaderboard_model_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at REAL,
            target_col TEXT,
            model_count INTEGER,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.commit()



def _load_model_leaderboard_history(limit: int = _MODEL_LEADERBOARD_HISTORY_LIMIT, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_model_leaderboard_tables(conn)
        rows = conn.execute(
            "SELECT id, created_at, updated_at, target_col, model_count FROM leaderboard_model_snapshots ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()



def _persist_model_leaderboard_snapshot(payload: Dict[str, Any], db_path: Optional[str] = None) -> None:
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    try:
        _ensure_model_leaderboard_tables(conn)
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        conn.execute(
            "INSERT INTO leaderboard_model_snapshots(created_at, updated_at, target_col, model_count, payload_json) VALUES (?, ?, ?, ?, ?)",
            (
                created_at,
                time.time(),
                payload.get("target_col"),
                payload.get("count"),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()



def _load_strategy_param_scan_summary(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    artifact_path = path or _STRATEGY_PARAM_SCAN_PATH
    try:
        if not artifact_path.exists():
            return None
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load strategy param scan summary: %s", exc)
        return None
    if not isinstance(payload, dict):
        return None

    saved_rows = list(payload.get("saved_strategies") or [])
    best_candidates = []
    for row in saved_rows[:10]:
        if not isinstance(row, dict):
            continue
        best_candidates.append(
            {
                "name": row.get("name"),
                "model_name": row.get("model_name"),
                "roi": row.get("roi"),
                "win_rate": row.get("win_rate"),
                "total_trades": row.get("total_trades"),
            }
        )

    combined_top = []
    for row in list(payload.get("combined_top_10") or [])[:10]:
        if not isinstance(row, dict):
            continue
        combined_top.append(
            {
                "model_name": row.get("model_name"),
                "variant": row.get("variant"),
                "roi": row.get("roi"),
                "win_rate": row.get("win_rate"),
                "max_drawdown": row.get("max_drawdown"),
                "profit_factor": row.get("profit_factor"),
                "total_trades": row.get("total_trades"),
            }
        )

    return {
        "generated_at": payload.get("generated_at"),
        "saved_strategy_count": len(saved_rows),
        "best_strategy_candidates": best_candidates,
        "combined_top_variants": combined_top,
        "source_artifact": str(artifact_path),
        "warning": (
            "canonical model leaderboard 仍是 placeholder-only；請改看策略參數重掃候選。"
            if best_candidates
            else None
        ),
    }



def _coerce_float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int_or_none(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


_HIGH_CONVICTION_LIVE_FAILURES = {"support_route_not_deployable", "deployment_blocker_active"}


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _topk_row_gate_parts(row: Dict[str, Any]) -> tuple[List[str], List[str], List[str], bool, bool, str]:
    gate_failures = _string_list(row.get("gate_failures"))
    model_gate_failures = _string_list(row.get("model_gate_failures"))
    live_gate_failures = _string_list(row.get("live_gate_failures"))
    if not model_gate_failures and not live_gate_failures:
        model_gate_failures = [item for item in gate_failures if item not in _HIGH_CONVICTION_LIVE_FAILURES]
        live_gate_failures = [item for item in gate_failures if item in _HIGH_CONVICTION_LIVE_FAILURES]
    explicit_oos = row.get("oos_gate_passed")
    oos_gate_passed = bool(explicit_oos) if explicit_oos is not None else not model_gate_failures
    explicit_runtime_blocked = row.get("blocked_only_by_live_guardrails")
    blocked_only_by_live_guardrails = (
        bool(explicit_runtime_blocked)
        if explicit_runtime_blocked is not None
        else bool(gate_failures) and oos_gate_passed and bool(live_gate_failures) and not model_gate_failures
    )
    deployable_verdict = str(row.get("deployable_verdict") or "not_deployable")
    deployment_candidate_tier = str(row.get("deployment_candidate_tier") or "")
    if not deployment_candidate_tier:
        if deployable_verdict == "deployable":
            deployment_candidate_tier = "deployable"
        elif blocked_only_by_live_guardrails:
            deployment_candidate_tier = "runtime_blocked_oos_pass"
        else:
            deployment_candidate_tier = "research_oos_gate_failed"
    return (
        gate_failures,
        model_gate_failures,
        live_gate_failures,
        oos_gate_passed,
        blocked_only_by_live_guardrails,
        deployment_candidate_tier,
    )


def _high_conviction_row_sort_key(row: Dict[str, Any]) -> tuple:
    (
        gate_failures,
        model_gate_failures,
        _live_gate_failures,
        oos_gate_passed,
        blocked_only_by_live_guardrails,
        _tier,
    ) = _topk_row_gate_parts(row)
    max_drawdown = _coerce_float_or_none(row.get("max_drawdown"))
    worst_fold = _coerce_float_or_none(row.get("worst_fold"))
    oos_roi = _coerce_float_or_none(row.get("oos_roi"))
    win_rate = _coerce_float_or_none(row.get("win_rate"))
    trade_count = _coerce_int_or_none(row.get("trade_count"))
    return (
        str(row.get("deployable_verdict") or "") == "deployable",
        blocked_only_by_live_guardrails,
        oos_gate_passed,
        -len(model_gate_failures),
        -len(gate_failures),
        -(max_drawdown if max_drawdown is not None else 999.0),
        worst_fold if worst_fold is not None else -999.0,
        oos_roi if oos_roi is not None else -999.0,
        win_rate if win_rate is not None else -999.0,
        trade_count if trade_count is not None else 0,
    )


def _compact_high_conviction_topk_row(
    row: Dict[str, Any],
    support_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    (
        gate_failures,
        model_gate_failures,
        live_gate_failures,
        oos_gate_passed,
        blocked_only_by_live_guardrails,
        deployment_candidate_tier,
    ) = _topk_row_gate_parts(row)
    support_context = support_context or {}

    def _support_value(row_key: str, context_key: Optional[str] = None) -> Any:
        if context_key:
            value = support_context.get(context_key)
            if value is not None:
                return value
        value = support_context.get(row_key)
        if value is not None:
            return value
        return row.get(row_key)

    return {
        "model": row.get("model") or row.get("model_name"),
        "model_name": row.get("model_name") or row.get("model"),
        "feature_profile": row.get("feature_profile"),
        "regime": row.get("regime"),
        "top_k": row.get("top_k"),
        "oos_roi": _coerce_float_or_none(row.get("oos_roi")),
        "win_rate": _coerce_float_or_none(row.get("win_rate")),
        "profit_factor": _coerce_float_or_none(row.get("profit_factor")),
        "max_drawdown": _coerce_float_or_none(row.get("max_drawdown")),
        "worst_fold": _coerce_float_or_none(row.get("worst_fold")),
        "trade_count": _coerce_int_or_none(row.get("trade_count")),
        "support_route": _support_value("support_route", "support_route_verdict"),
        "support_governance_route": _support_value("support_governance_route"),
        "deployment_blocker": _support_value("deployment_blocker"),
        "runtime_closure_state": _support_value("runtime_closure_state"),
        "current_live_structure_bucket": _support_value("current_live_structure_bucket"),
        "current_live_structure_bucket_rows": _support_value("current_live_structure_bucket_rows"),
        "minimum_support_rows": _support_value("minimum_support_rows"),
        "current_live_structure_bucket_gap_to_minimum": _support_value("current_live_structure_bucket_gap_to_minimum"),
        "support_route_deployable": _support_value("support_route_deployable"),
        "allowed_layers": _support_value("allowed_layers"),
        "execution_guardrail_reason": _support_value("execution_guardrail_reason"),
        "deployable_verdict": row.get("deployable_verdict") or "not_deployable",
        "deployment_candidate_tier": deployment_candidate_tier,
        "gate_failures": gate_failures,
        "model_gate_failures": model_gate_failures,
        "live_gate_failures": live_gate_failures,
        "oos_gate_passed": oos_gate_passed,
        "blocked_only_by_live_guardrails": blocked_only_by_live_guardrails,
    }



def _load_high_conviction_live_support_overlay(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    artifact_path = path or _LIVE_PREDICT_PROBE_PATH
    payload = _load_live_predict_probe_payload(artifact_path, log_context="live predict probe for high-conviction Top-K overlay")
    if not isinstance(payload, dict):
        return None

    blocker_details = payload.get("deployment_blocker_details") if isinstance(payload.get("deployment_blocker_details"), dict) else {}
    support_progress = payload.get("support_progress") if isinstance(payload.get("support_progress"), dict) else {}
    if not support_progress:
        support_progress = blocker_details.get("support_progress") if isinstance(blocker_details.get("support_progress"), dict) else {}
    support_identity = (
        payload.get("support_identity")
        or blocker_details.get("support_identity")
        or support_progress.get("support_identity")
    )

    current_bucket = (
        payload.get("current_live_structure_bucket")
        or blocker_details.get("current_live_structure_bucket")
        or payload.get("structure_bucket")
    )
    current_rows = support_progress.get("current_rows")
    if current_rows is None:
        current_rows = payload.get("current_live_structure_bucket_rows")
    if current_rows is None:
        current_rows = blocker_details.get("current_live_structure_bucket_rows")
    minimum_rows = support_progress.get("minimum_support_rows")
    if minimum_rows is None:
        minimum_rows = payload.get("minimum_support_rows")
    if minimum_rows is None:
        minimum_rows = blocker_details.get("minimum_support_rows")
    gap_to_minimum = payload.get("current_live_structure_bucket_gap_to_minimum")
    if gap_to_minimum is None:
        gap_to_minimum = blocker_details.get("current_live_structure_bucket_gap_to_minimum")
    if gap_to_minimum is None:
        gap_to_minimum = support_progress.get("gap_to_minimum")
    if gap_to_minimum is None and current_rows is not None and minimum_rows is not None:
        try:
            gap_to_minimum = max(int(minimum_rows) - int(current_rows), 0)
        except (TypeError, ValueError):
            gap_to_minimum = None

    support_route = payload.get("support_route_verdict") or blocker_details.get("support_route_verdict")
    support_governance_route = payload.get("support_governance_route") or blocker_details.get("support_governance_route")
    deployment_blocker = payload.get("deployment_blocker") or blocker_details.get("deployment_blocker")
    runtime_closure_state = payload.get("runtime_closure_state") or blocker_details.get("runtime_closure_state")
    if (
        current_bucket is None
        and current_rows is None
        and minimum_rows is None
        and support_route is None
        and support_governance_route is None
        and deployment_blocker is None
        and runtime_closure_state is None
    ):
        return None

    support_route_deployable = payload.get("support_route_deployable")
    if support_route_deployable is None:
        support_route_deployable = blocker_details.get("support_route_deployable")

    return {
        "generated_at": payload.get("generated_at") or payload.get("feature_timestamp"),
        "source_artifact": str(artifact_path),
        "current_live_structure_bucket": current_bucket,
        "current_live_structure_bucket_rows": current_rows,
        "minimum_support_rows": minimum_rows,
        "current_live_structure_bucket_gap_to_minimum": gap_to_minimum,
        "support_route_verdict": support_route,
        "support_governance_route": support_governance_route,
        "support_route_deployable": support_route_deployable,
        "deployment_blocker": deployment_blocker,
        "runtime_closure_state": runtime_closure_state,
        "allowed_layers": payload.get("allowed_layers"),
        "signal": payload.get("signal"),
        "support_progress": support_progress or None,
        "support_identity": support_identity if isinstance(support_identity, dict) else None,
        "regime_gate": payload.get("regime_gate"),
        "entry_quality_label": payload.get("entry_quality_label"),
        "execution_guardrail_reason": payload.get("execution_guardrail_reason") or payload.get("allowed_layers_reason"),
    }



def _overlay_high_conviction_support_context(
    context: Dict[str, Any],
    *,
    topk_generated_at: Any,
    live_truth: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not isinstance(live_truth, dict):
        return context
    topk_dt = _parse_utc_datetime(topk_generated_at)
    live_dt = _parse_utc_datetime(live_truth.get("generated_at"))
    if live_dt is None:
        return context
    if topk_dt is not None and live_dt < topk_dt:
        return context

    merged = dict(context)
    for key in (
        "current_live_structure_bucket",
        "current_live_structure_bucket_rows",
        "minimum_support_rows",
        "current_live_structure_bucket_gap_to_minimum",
        "support_route_verdict",
        "support_governance_route",
        "support_route_deployable",
        "deployment_blocker",
        "runtime_closure_state",
        "allowed_layers",
        "signal",
        "support_progress",
        "support_identity",
        "regime_gate",
        "entry_quality_label",
        "execution_guardrail_reason",
    ):
        value = live_truth.get(key)
        if value is not None:
            merged[key] = value
    merged["live_truth_generated_at"] = live_truth.get("generated_at")
    merged["live_truth_source_artifact"] = live_truth.get("source_artifact")
    merged["live_truth_overlay_applied"] = True
    return merged



def _build_high_conviction_topk_freshness(
    generated_at: Any,
    *,
    stale_after_sec: float = _HIGH_CONVICTION_TOPK_STALE_AFTER_SEC,
) -> Dict[str, Any]:
    """Return operator-facing freshness for the high-conviction Top-K matrix."""
    stale_after_minutes = stale_after_sec / 60.0
    checked_at = datetime.now(timezone.utc)
    freshness: Dict[str, Any] = {
        "status": "unavailable",
        "label": "unavailable",
        "reason": "missing_generated_at",
        "generated_at": generated_at,
        "checked_at": checked_at.isoformat(),
        "age_minutes": None,
        "age_seconds": None,
        "stale_after_minutes": stale_after_minutes,
        "deployment_blocking": True,
    }
    dt = _parse_utc_datetime(generated_at)
    if dt is None:
        if generated_at:
            freshness["reason"] = "invalid_generated_at"
        return freshness
    age_seconds = max((checked_at - dt).total_seconds(), 0.0)
    age_minutes = age_seconds / 60.0
    status = "fresh" if age_seconds <= stale_after_sec else "stale"
    freshness.update(
        {
            "status": status,
            "label": status,
            "reason": "artifact_within_policy" if status == "fresh" else "artifact_older_than_policy",
            "age_minutes": age_minutes,
            "age_seconds": age_seconds,
            "deployment_blocking": status != "fresh",
        }
    )
    return freshness


def _load_high_conviction_topk_summary(path: Optional[Path] = None, limit: int = 12) -> Optional[Dict[str, Any]]:
    artifact_path = path or HIGH_CONVICTION_TOPK_PATH
    try:
        if not artifact_path.exists():
            return None
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load high-conviction top-k matrix: %s", exc)
        return {
            "source_artifact": str(artifact_path),
            "status": "unreadable",
            "error": str(exc),
            "row_count": 0,
            "deployable_count": 0,
            "best_rows": [],
        }
    if not isinstance(payload, dict):
        return {
            "source_artifact": str(artifact_path),
            "status": "invalid_payload",
            "row_count": 0,
            "deployable_count": 0,
            "best_rows": [],
        }

    rows = [row for row in payload.get("rows", []) if isinstance(row, dict)]
    rows.sort(key=_high_conviction_row_sort_key, reverse=True)
    deployable_count = sum(1 for row in rows if row.get("deployable_verdict") == "deployable")
    risk_qualified_count = sum(1 for row in rows if _topk_row_gate_parts(row)[3])
    runtime_blocked_candidate_count = sum(1 for row in rows if _topk_row_gate_parts(row)[4])
    freshness = _build_high_conviction_topk_freshness(payload.get("generated_at"))
    freshness_status = str(freshness.get("status") or "unavailable")
    freshness_blocker = freshness.get("reason") if freshness.get("deployment_blocking") else None
    deployment_ready = deployable_count > 0 and freshness_status == "fresh"
    if deployment_ready:
        deployment_readiness_status = "deployable_candidates_available"
    elif freshness_status == "stale":
        deployment_readiness_status = "stale_artifact_shadow_only"
    elif freshness_status == "unavailable":
        deployment_readiness_status = "freshness_unknown_shadow_only"
    else:
        deployment_readiness_status = "paper_shadow_only"
    support_context = payload.get("support_context") if isinstance(payload.get("support_context"), dict) else {}
    support_context = _overlay_high_conviction_support_context(
        support_context,
        topk_generated_at=payload.get("generated_at"),
        live_truth=_load_high_conviction_live_support_overlay(),
    )
    compact_rows = [_compact_high_conviction_topk_row(row, support_context) for row in rows[:limit]]
    nearest_deployable_rows = [
        _compact_high_conviction_topk_row(row, support_context)
        for row in rows
        if _topk_row_gate_parts(row)[4] or str(row.get("deployable_verdict") or "") == "deployable"
    ][:limit]
    return {
        "source_artifact": str(artifact_path),
        "generated_at": payload.get("generated_at"),
        "freshness": freshness,
        "freshness_status": freshness_status,
        "freshness_blocker": freshness_blocker,
        "artifact_age_minutes": freshness.get("age_minutes"),
        "stale_after_minutes": freshness.get("stale_after_minutes"),
        "deployment_ready": deployment_ready,
        "deployment_readiness_status": deployment_readiness_status,
        "target_col": payload.get("target_col"),
        "samples": payload.get("samples"),
        "top_k_grid": payload.get("top_k_grid") if isinstance(payload.get("top_k_grid"), list) else [],
        "minimum_deployment_gates": payload.get("minimum_deployment_gates") if isinstance(payload.get("minimum_deployment_gates"), dict) else {},
        "support_context": support_context,
        "row_count": len(rows),
        "deployable_count": deployable_count,
        "risk_qualified_count": risk_qualified_count,
        "runtime_blocked_candidate_count": runtime_blocked_candidate_count,
        "status": deployment_readiness_status,
        "best_rows": compact_rows,
        "nearest_deployable_rows": nearest_deployable_rows or compact_rows,
    }



def _load_leaderboard_governance_summary(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    artifact_path = path or _LEADERBOARD_GOVERNANCE_PROBE_PATH
    try:
        if not artifact_path.exists():
            return None
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load leaderboard governance probe: %s", exc)
        return None
    if not isinstance(payload, dict):
        return None
    alignment = payload.get("alignment")
    if not isinstance(alignment, dict):
        return None
    governance = dict(alignment)
    governance["generated_at"] = payload.get("generated_at")
    governance["source_artifact"] = str(artifact_path)
    live_truth = _load_leaderboard_live_truth_overlay()
    if isinstance(live_truth, dict):
        governance = _overlay_leaderboard_governance_live_truth(governance, live_truth)
    return governance



def _load_live_predict_probe_payload(
    path: Optional[Path] = None,
    *,
    log_context: str = "live predict probe",
) -> Optional[Dict[str, Any]]:
    artifact_path = path or _LIVE_PREDICT_PROBE_PATH
    try:
        if not artifact_path.exists():
            return None
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load %s: %s", log_context, exc)
        return None
    if not isinstance(payload, dict):
        return None
    return payload



def _load_recent_canonical_drift_summary(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    artifact_path = path or _RECENT_DRIFT_REPORT_PATH
    try:
        if not artifact_path.exists():
            return None
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load recent canonical drift report: %s", exc)
        return None
    if not isinstance(payload, dict):
        return None

    def _has_recent_drift_window_truth(window_payload: Any) -> bool:
        if not isinstance(window_payload, dict):
            return False
        summary = window_payload.get("summary") if isinstance(window_payload.get("summary"), dict) else {}
        if window_payload.get("window") not in {None, ""}:
            return True
        alerts = window_payload.get("alerts")
        if isinstance(alerts, list) and alerts:
            return True
        return any(
            summary.get(key) is not None
            for key in ("rows", "win_rate", "drift_interpretation", "dominant_regime")
        )

    def _compact_feature_names(items: Any, limit: int = 3) -> List[str]:
        if not isinstance(items, list):
            return []
        names: List[str] = []
        for item in items:
            feature = None
            if isinstance(item, dict):
                feature = item.get("feature")
            elif isinstance(item, str):
                feature = item
            if isinstance(feature, str) and feature and feature not in names:
                names.append(feature)
            if len(names) >= limit:
                break
        return names

    def _compact_target_streak(streak: Any) -> Any:
        if not isinstance(streak, dict):
            return streak
        return {
            "target": streak.get("target"),
            "count": streak.get("count"),
            "start_timestamp": streak.get("start_timestamp"),
            "end_timestamp": streak.get("end_timestamp"),
        }

    def _normalize_recent_drift_window(window_payload: Any) -> Optional[Dict[str, Any]]:
        window = window_payload if isinstance(window_payload, dict) else {}
        summary = window.get("summary") if isinstance(window.get("summary"), dict) else {}
        quality = summary.get("quality_metrics") if isinstance(summary.get("quality_metrics"), dict) else {}
        feature_diag = summary.get("feature_diagnostics") if isinstance(summary.get("feature_diagnostics"), dict) else {}
        target_path = summary.get("target_path_diagnostics") if isinstance(summary.get("target_path_diagnostics"), dict) else {}
        reference = summary.get("reference_window_comparison") if isinstance(summary.get("reference_window_comparison"), dict) else {}
        reference_quality = reference.get("reference_quality") if isinstance(reference.get("reference_quality"), dict) else {}

        if not window and not summary:
            return None

        return {
            "window": window.get("window"),
            "alerts": window.get("alerts") if isinstance(window.get("alerts"), list) else [],
            "summary": {
                "rows": summary.get("rows"),
                "win_rate": summary.get("win_rate"),
                "drift_interpretation": summary.get("drift_interpretation"),
                "dominant_regime": summary.get("dominant_regime"),
                "dominant_regime_share": summary.get("dominant_regime_share"),
                "quality_metrics": {
                    "avg_simulated_pnl": quality.get("avg_simulated_pnl"),
                    "avg_simulated_quality": quality.get("avg_simulated_quality"),
                    "avg_drawdown_penalty": quality.get("avg_drawdown_penalty"),
                    "spot_long_win_rate": quality.get("spot_long_win_rate"),
                },
                "feature_diagnostics": {
                    "feature_count": feature_diag.get("feature_count"),
                    "low_variance_count": feature_diag.get("low_variance_count"),
                    "frozen_count": feature_diag.get("frozen_count"),
                    "compressed_count": feature_diag.get("compressed_count"),
                    "expected_static_count": feature_diag.get("expected_static_count"),
                    "expected_compressed_count": feature_diag.get("expected_compressed_count"),
                    "overlay_only_count": feature_diag.get("overlay_only_count"),
                    "unexpected_frozen_count": feature_diag.get("unexpected_frozen_count"),
                    "unexpected_compressed_count": feature_diag.get("unexpected_compressed_count"),
                    "null_heavy_count": feature_diag.get("null_heavy_count"),
                    "low_distinct_count": feature_diag.get("low_distinct_count"),
                    "low_distinct_features": _compact_feature_names(feature_diag.get("low_distinct_examples")),
                    "expected_compressed_features": _compact_feature_names(feature_diag.get("expected_compressed_examples")),
                    "unexpected_frozen_features": _compact_feature_names(feature_diag.get("unexpected_frozen_examples")),
                    "unexpected_compressed_features": _compact_feature_names(feature_diag.get("unexpected_compressed_examples")),
                },
                "target_path_diagnostics": {
                    "tail_target_streak": _compact_target_streak(target_path.get("tail_target_streak")),
                    "longest_target_streak": _compact_target_streak(target_path.get("longest_target_streak")),
                    "longest_zero_target_streak": _compact_target_streak(target_path.get("longest_zero_target_streak")),
                    "longest_one_target_streak": _compact_target_streak(target_path.get("longest_one_target_streak")),
                },
                "reference_window_comparison": {
                    "prev_win_rate": reference.get("prev_win_rate", reference_quality.get("win_rate")),
                    "prev_quality": reference.get("prev_quality", reference_quality.get("avg_simulated_quality")),
                    "prev_pnl": reference.get("prev_pnl", reference_quality.get("avg_simulated_pnl")),
                    "win_rate_delta": reference.get("win_rate_delta", reference.get("win_rate_delta_vs_reference")),
                    "quality_delta": reference.get("quality_delta", reference.get("avg_simulated_quality_delta_vs_reference")),
                    "pnl_delta": reference.get("pnl_delta", reference.get("avg_simulated_pnl_delta_vs_reference")),
                    "top_mean_shift_features": reference.get("top_mean_shift_features") if isinstance(reference.get("top_mean_shift_features"), list) else [],
                    "new_unexpected_frozen_features": reference.get("new_unexpected_frozen_features") if isinstance(reference.get("new_unexpected_frozen_features"), list) else [],
                    "new_unexpected_compressed_features": reference.get("new_unexpected_compressed_features") if isinstance(reference.get("new_unexpected_compressed_features"), list) else [],
                },
            },
        }

    def _normalize_recent_distribution_issue_fallback() -> Optional[Dict[str, Any]]:
        try:
            if not _ISSUES_JSON_PATH.exists():
                return None
            issues_payload = json.loads(_ISSUES_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(issues_payload, dict):
            return None
        issues = issues_payload.get("issues")
        if not isinstance(issues, list):
            return None

        issue_summary: Optional[Dict[str, Any]] = None
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            if issue.get("id") != "P0_recent_distribution_pathology":
                continue
            summary = issue.get("summary")
            if isinstance(summary, dict):
                issue_summary = summary
                break
        if not issue_summary:
            return None

        issue_window = issue_summary.get("window")
        issue_alerts = issue_summary.get("alerts") if isinstance(issue_summary.get("alerts"), list) else []

        windows = payload.get("windows") if isinstance(payload.get("windows"), dict) else {}
        report_window_summary = windows.get(str(issue_window)) if issue_window is not None else None
        if isinstance(report_window_summary, dict) and report_window_summary:
            report_alerts = report_window_summary.get("alerts") if isinstance(report_window_summary.get("alerts"), list) else issue_alerts
            return _normalize_recent_drift_window(
                {
                    "window": issue_window,
                    "alerts": report_alerts,
                    "summary": report_window_summary,
                }
            )

        fallback_reference_features = issue_summary.get("top_shift_features")
        if not isinstance(fallback_reference_features, list):
            fallback_reference_features = []
        fallback_target_path: Dict[str, Any] = {}
        fallback_tail = issue_summary.get("tail_streak")
        if isinstance(fallback_tail, str) and "x" in fallback_tail:
            count_text, _, target_text = fallback_tail.partition("x")
            try:
                fallback_target_path = {
                    "tail_target_streak": {
                        "count": int(count_text),
                        "target": target_text,
                    }
                }
            except ValueError:
                fallback_target_path = {}

        return _normalize_recent_drift_window(
            {
                "window": issue_window,
                "alerts": issue_alerts,
                "summary": {
                    "rows": issue_summary.get("rows", issue_window),
                    "win_rate": issue_summary.get("win_rate"),
                    "drift_interpretation": issue_summary.get("interpretation"),
                    "dominant_regime": issue_summary.get("dominant_regime"),
                    "dominant_regime_share": issue_summary.get("dominant_regime_share"),
                    "quality_metrics": {
                        "avg_simulated_pnl": issue_summary.get("avg_pnl"),
                        "avg_simulated_quality": issue_summary.get("avg_quality"),
                        "avg_drawdown_penalty": issue_summary.get("avg_drawdown_penalty"),
                        "spot_long_win_rate": issue_summary.get("spot_long_win_rate"),
                    },
                    "target_path_diagnostics": fallback_target_path,
                    "reference_window_comparison": {
                        "prev_win_rate": issue_summary.get("prev_win_rate"),
                        "prev_quality": issue_summary.get("prev_quality"),
                        "prev_pnl": issue_summary.get("prev_pnl"),
                        "win_rate_delta": issue_summary.get("delta_vs_prev"),
                        "top_mean_shift_features": [
                            {"feature": feature}
                            for feature in fallback_reference_features
                            if isinstance(feature, str) and feature
                        ],
                    },
                },
            }
        )

    def _normalize_canonical_tail_root_cause(root_cause_payload: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(root_cause_payload, dict):
            return None
        loss_path = root_cause_payload.get("loss_path_breakdown") if isinstance(root_cause_payload.get("loss_path_breakdown"), dict) else {}
        regime_breakdown = root_cause_payload.get("regime_breakdown") if isinstance(root_cause_payload.get("regime_breakdown"), dict) else {}
        feature_shift = root_cause_payload.get("feature_shift") if isinstance(root_cause_payload.get("feature_shift"), dict) else {}
        top_features = root_cause_payload.get("top_4h_shift_features")
        key_findings = root_cause_payload.get("key_findings")
        return {
            "generated_at": root_cause_payload.get("generated_at"),
            "window": root_cause_payload.get("window"),
            "rows": root_cause_payload.get("rows"),
            "losses": root_cause_payload.get("losses"),
            "wins": root_cause_payload.get("wins"),
            "loss_path_breakdown": {
                "tp_miss_count": loss_path.get("tp_miss_count"),
                "dd_breach_count": loss_path.get("dd_breach_count"),
                "high_underwater_count": loss_path.get("high_underwater_count"),
                "avg_time_underwater": loss_path.get("avg_time_underwater"),
            },
            "regime_breakdown": regime_breakdown,
            "dominant_loss_regime": root_cause_payload.get("dominant_loss_regime"),
            "top_4h_shift_features": top_features if isinstance(top_features, list) else [],
            "feature_shift": feature_shift,
            "key_findings": key_findings if isinstance(key_findings, list) else [],
        }

    primary = _normalize_recent_drift_window(payload.get("primary_window"))
    blocking = _normalize_recent_drift_window(payload.get("blocking_window"))
    if not _has_recent_drift_window_truth(blocking):
        issue_fallback = _normalize_recent_distribution_issue_fallback()
        if issue_fallback is not None:
            blocking = issue_fallback
    if primary is None and blocking is None:
        return None

    result = {
        "generated_at": payload.get("generated_at"),
        "source_artifact": str(artifact_path),
        "target_col": payload.get("target_col"),
        "horizon_minutes": payload.get("horizon_minutes"),
    }
    canonical_tail_root_cause = _normalize_canonical_tail_root_cause(payload.get("canonical_tail_root_cause"))
    if canonical_tail_root_cause is not None:
        result["canonical_tail_root_cause"] = canonical_tail_root_cause
    if primary is not None:
        result["primary_window"] = primary
    if blocking is not None:
        result["blocking_window"] = blocking
    return result



def _overlay_confidence_with_live_predict_probe(
    payload: Dict[str, Any],
    path: Optional[Path] = None,
    *,
    stale_after_sec: Optional[float] = None,
) -> Dict[str, Any]:
    current = dict(payload or {})
    probe_payload = _load_live_predict_probe_payload(path, log_context="live predict probe runtime overlay")
    if not isinstance(probe_payload, dict):
        return current

    probe_dt = _parse_utc_datetime(probe_payload.get("generated_at") or probe_payload.get("feature_timestamp"))
    if probe_dt is None:
        return current

    max_age = _LIVE_PREDICT_PROBE_RUNTIME_STALE_AFTER_SEC if stale_after_sec is None else stale_after_sec
    if max_age is not None:
        try:
            max_age_seconds = float(max_age)
        except (TypeError, ValueError):
            max_age_seconds = None
        if max_age_seconds is not None and max_age_seconds >= 0:
            age_seconds = (datetime.now(timezone.utc) - probe_dt).total_seconds()
            if age_seconds > max_age_seconds:
                return current

    merged = dict(current)
    for key, value in probe_payload.items():
        if value is not None:
            merged[key] = value

    current_details = current.get("deployment_blocker_details") if isinstance(current.get("deployment_blocker_details"), dict) else {}
    probe_details = probe_payload.get("deployment_blocker_details") if isinstance(probe_payload.get("deployment_blocker_details"), dict) else {}
    if current_details or probe_details:
        merged_details = dict(current_details)
        for key, value in probe_details.items():
            if value is not None:
                merged_details[key] = value
        merged["deployment_blocker_details"] = merged_details

    current_bucket = probe_payload.get("current_live_structure_bucket") or probe_payload.get("structure_bucket")
    if current_bucket is not None:
        merged["current_live_structure_bucket"] = current_bucket
        merged["structure_bucket"] = current_bucket

    merged["live_predict_probe_overlay_applied"] = True
    merged["live_predict_probe_overlay_generated_at"] = probe_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    merged["live_predict_probe_overlay_source_artifact"] = str(path or _LIVE_PREDICT_PROBE_PATH)
    return merged



def _load_leaderboard_live_truth_overlay(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    artifact_path = path or _LIVE_PREDICT_PROBE_PATH
    payload = _load_live_predict_probe_payload(artifact_path, log_context="live predict probe for leaderboard governance overlay")
    if not isinstance(payload, dict):
        return None

    blocker_details = payload.get("deployment_blocker_details") if isinstance(payload.get("deployment_blocker_details"), dict) else {}
    support_progress = payload.get("support_progress") if isinstance(payload.get("support_progress"), dict) else {}
    if not support_progress:
        support_progress = blocker_details.get("support_progress") if isinstance(blocker_details.get("support_progress"), dict) else {}
    support_identity = (
        payload.get("support_identity")
        or blocker_details.get("support_identity")
        or support_progress.get("support_identity")
    )

    current_bucket = (
        payload.get("current_live_structure_bucket")
        or blocker_details.get("current_live_structure_bucket")
        or payload.get("structure_bucket")
    )
    current_rows = support_progress.get("current_rows")
    if current_rows is None:
        current_rows = payload.get("current_live_structure_bucket_rows")
    if current_rows is None:
        current_rows = blocker_details.get("current_live_structure_bucket_rows")
    minimum_rows = support_progress.get("minimum_support_rows")
    if minimum_rows is None:
        minimum_rows = payload.get("minimum_support_rows")
    if minimum_rows is None:
        minimum_rows = blocker_details.get("minimum_support_rows")
    gap_to_minimum = payload.get("current_live_structure_bucket_gap_to_minimum")
    if gap_to_minimum is None:
        gap_to_minimum = blocker_details.get("current_live_structure_bucket_gap_to_minimum")
    if gap_to_minimum is None:
        gap_to_minimum = support_progress.get("gap_to_minimum")
    if gap_to_minimum is None and current_rows is not None and minimum_rows is not None:
        try:
            gap_to_minimum = max(int(minimum_rows) - int(current_rows), 0)
        except (TypeError, ValueError):
            gap_to_minimum = None

    if current_bucket is None and current_rows is None and minimum_rows is None and not support_progress:
        return None

    return {
        "generated_at": payload.get("generated_at") or payload.get("feature_timestamp"),
        "source_artifact": str(artifact_path),
        "live_current_structure_bucket": current_bucket,
        "live_current_structure_bucket_rows": current_rows,
        "minimum_support_rows": minimum_rows,
        "live_current_structure_bucket_gap_to_minimum": gap_to_minimum,
        "support_route_verdict": payload.get("support_route_verdict") or blocker_details.get("support_route_verdict"),
        "support_governance_route": payload.get("support_governance_route") or blocker_details.get("support_governance_route"),
        "support_progress": support_progress or None,
        "support_identity": support_identity if isinstance(support_identity, dict) else None,
        "live_regime_gate": payload.get("regime_gate"),
        "live_entry_quality_label": payload.get("entry_quality_label"),
        "live_execution_guardrail_reason": payload.get("execution_guardrail_reason") or payload.get("allowed_layers_reason"),
    }



def _overlay_leaderboard_governance_live_truth(
    governance: Dict[str, Any],
    live_truth: Dict[str, Any],
) -> Dict[str, Any]:
    governance_dt = _parse_utc_datetime(governance.get("generated_at"))
    live_truth_dt = _parse_utc_datetime(live_truth.get("generated_at"))
    if live_truth_dt is None:
        return governance
    if governance_dt is not None and live_truth_dt < governance_dt:
        return governance

    merged = dict(governance)
    for key in (
        "live_current_structure_bucket",
        "live_current_structure_bucket_rows",
        "minimum_support_rows",
        "live_current_structure_bucket_gap_to_minimum",
        "support_route_verdict",
        "support_governance_route",
        "support_progress",
        "support_identity",
        "live_regime_gate",
        "live_entry_quality_label",
        "live_execution_guardrail_reason",
    ):
        value = live_truth.get(key)
        if value is not None:
            merged[key] = value

    governance_contract = dict(merged.get("governance_contract") or {})
    if live_truth.get("support_governance_route") is not None:
        governance_contract["support_governance_route"] = live_truth.get("support_governance_route")
    if live_truth.get("live_current_structure_bucket_rows") is not None:
        governance_contract["live_current_structure_bucket_rows"] = live_truth.get("live_current_structure_bucket_rows")
    if live_truth.get("minimum_support_rows") is not None:
        governance_contract["minimum_support_rows"] = live_truth.get("minimum_support_rows")
    if live_truth.get("live_current_structure_bucket_gap_to_minimum") is not None:
        governance_contract["live_current_structure_bucket_gap_to_minimum"] = live_truth.get("live_current_structure_bucket_gap_to_minimum")
    if isinstance(live_truth.get("support_progress"), dict):
        governance_contract["support_progress"] = live_truth.get("support_progress")
    if isinstance(live_truth.get("support_identity"), dict):
        governance_contract["support_identity"] = live_truth.get("support_identity")
    if governance_contract:
        merged["governance_contract"] = governance_contract

    merged["live_truth_generated_at"] = live_truth.get("generated_at")
    merged["live_truth_source_artifact"] = live_truth.get("source_artifact")
    merged["live_truth_overlay_applied"] = True
    return merged



def _should_override_leaderboard_governance(
    current: Optional[Dict[str, Any]],
    candidate: Optional[Dict[str, Any]],
) -> bool:
    if not isinstance(candidate, dict):
        return False
    if not isinstance(current, dict):
        return True
    candidate_dt = _parse_utc_datetime(candidate.get("generated_at"))
    current_dt = _parse_utc_datetime(current.get("generated_at"))
    if candidate_dt is None:
        return False
    if current_dt is None:
        return True
    return candidate_dt >= current_dt



def _build_model_leaderboard_payload(db_path: Optional[str] = None) -> Dict[str, Any]:
    from backtesting.model_leaderboard import ModelLeaderboard

    db_path = db_path or DB_PATH
    strategy_param_scan = _load_strategy_param_scan_summary()
    leaderboard_governance = _load_leaderboard_governance_summary()
    high_conviction_topk = _load_high_conviction_topk_summary()
    data_df = load_model_leaderboard_frame(db_path)
    if data_df.empty:
        return {
            "target_col": "simulated_pyramid_win",
            "count": 0,
            "comparable_count": 0,
            "placeholder_count": 0,
            "evaluated_row_count": 0,
            "leaderboard": [],
            "placeholder_rows": [],
            "leaderboard_warning": None,
            "quadrant_points": [],
            "skipped_models": [],
            "snapshot_history": _load_model_leaderboard_history(db_path=db_path),
            "storage": {"canonical_store": f"sqlite:///{db_path}"},
            "overfit_gap_threshold": _OVERFIT_GAP_THRESHOLD,
            "overfit_accuracy_threshold": _OVERFIT_ACCURACY_THRESHOLD,
            "target_candidates": [],
            "evaluation_fold_window": "latest_bounded_walk_forward",
            "evaluation_max_folds": getattr(ModelLeaderboard, "EVALUATION_MAX_FOLDS", None),
            "strategy_param_scan": strategy_param_scan,
            "leaderboard_governance": leaderboard_governance,
            "high_conviction_topk": high_conviction_topk,
        }

    target_col = "simulated_pyramid_win" if "simulated_pyramid_win" in data_df.columns else "label_spot_long_win"
    leaderboard = ModelLeaderboard(data_df, target_col=target_col, background_refresh=True)
    refresh_models = list(getattr(leaderboard, "REFRESH_MODELS", getattr(leaderboard, "SUPPORTED_MODELS", []) or []))
    scores = leaderboard.run_all_models(refresh_models)
    serialized_rows = _serialize_model_scores(scores, leaderboard)
    leaderboard_rows, placeholder_rows, leaderboard_warning = _split_model_leaderboard_rows(serialized_rows)
    supported_models = list(getattr(leaderboard, "SUPPORTED_MODELS", []) or [])
    excluded_supported_models = [name for name in supported_models if name not in refresh_models]
    skipped_models = []
    for model_name, status in (getattr(leaderboard, "last_model_statuses", {}) or {}).items():
        if status.get("status") == "ok":
            continue
        skipped_models.append({
            "model_name": model_name,
            "status": status.get("status"),
            "reason": status.get("reason"),
            "detail": status.get("detail"),
        })
    quadrant_points = [
        {
            "model_name": row.get("model_name"),
            "reliability_score": row.get("reliability_score"),
            "return_power_score": row.get("return_power_score"),
            "overall_score": row.get("overall_score"),
        }
        for row in leaderboard_rows
    ]
    payload = _normalize_model_leaderboard_payload({
        "target_col": target_col,
        "count": len(leaderboard_rows),
        "leaderboard": leaderboard_rows,
        "quadrant_points": quadrant_points,
        "placeholder_models": placeholder_rows,
        "placeholder_count": len(placeholder_rows),
        "skipped_models": skipped_models,
        "refresh_model_scope": "production_refresh_shortlist",
        "evaluated_models": refresh_models,
        "excluded_supported_models": excluded_supported_models,
        "snapshot_history": _load_model_leaderboard_history(db_path=db_path),
        "storage": {"canonical_store": f"sqlite:///{db_path}"},
        "overfit_gap_threshold": _OVERFIT_GAP_THRESHOLD,
        "overfit_accuracy_threshold": _OVERFIT_ACCURACY_THRESHOLD,
        "target_candidates": [],
        "evaluation_fold_window": "latest_bounded_walk_forward",
        "evaluation_max_folds": getattr(leaderboard, "EVALUATION_MAX_FOLDS", None),
        "data_warning": leaderboard_warning,
        "strategy_param_scan": strategy_param_scan,
        "leaderboard_governance": leaderboard_governance,
        "high_conviction_topk": high_conviction_topk,
    })
    return payload



def _load_latest_model_leaderboard_snapshot_payload(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    try:
        _ensure_model_leaderboard_tables(conn)
        row = conn.execute(
            "SELECT payload_json, updated_at FROM leaderboard_model_snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row or not row[0]:
            return None
        payload = json.loads(row[0])
        if not isinstance(payload, dict):
            return None
        return {"payload": payload, "updated_at": float(row[1] or 0.0), "error": None}
    except Exception as exc:
        logger.warning("Failed to load latest model leaderboard snapshot payload: %s", exc)
        return None
    finally:
        conn.close()



def _load_model_leaderboard_cache_file() -> None:
    with _MODEL_LB_CACHE_LOCK:
        if bool(_MODEL_LB_CACHE.get("refreshing")):
            return

    loaded_payload: Optional[Dict[str, Any]] = None
    loaded_updated_at = 0.0
    loaded_error: Optional[str] = None
    if MODEL_LB_CACHE_PATH.exists():
        try:
            cached = json.loads(MODEL_LB_CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(cached, dict):
                payload = cached.get("payload") if isinstance(cached.get("payload"), dict) else None
                legacy_payload = cached if payload is None and isinstance(cached.get("leaderboard"), list) else None
                if payload is not None and _model_leaderboard_payload_has_rows(payload):
                    loaded_payload = payload
                    loaded_updated_at = float(cached.get("updated_at") or 0.0)
                    loaded_error = cached.get("error")
                elif legacy_payload is not None and _model_leaderboard_payload_has_rows(legacy_payload):
                    loaded_payload = legacy_payload
                    loaded_updated_at = float(MODEL_LB_CACHE_PATH.stat().st_mtime)
                    loaded_error = None
        except Exception as exc:
            logger.warning("Failed to load model leaderboard cache: %s", exc)

    snapshot = _load_latest_model_leaderboard_snapshot_payload()
    if snapshot:
        snapshot_payload = snapshot.get("payload") if isinstance(snapshot.get("payload"), dict) else None
        snapshot_updated_at = float(snapshot.get("updated_at") or 0.0)
        if snapshot_payload is not None and _model_leaderboard_payload_has_rows(snapshot_payload):
            if loaded_payload is None or snapshot_updated_at > loaded_updated_at:
                loaded_payload = snapshot_payload
                loaded_updated_at = snapshot_updated_at
                loaded_error = snapshot.get("error")
    if loaded_payload is not None:
        loaded_payload = _normalize_model_leaderboard_payload(loaded_payload)
        with _MODEL_LB_CACHE_LOCK:
            current_payload = _MODEL_LB_CACHE.get("payload")
            current_updated_at = float(_MODEL_LB_CACHE.get("updated_at") or 0.0)
            current_has_rows = _model_leaderboard_payload_has_rows(current_payload)
            should_adopt_loaded_payload = (
                not _MODEL_LB_CACHE.get("refreshing")
                and (
                    not current_has_rows
                    or (loaded_updated_at > 0 and loaded_updated_at > current_updated_at)
                )
            )
            if should_adopt_loaded_payload:
                _MODEL_LB_CACHE["payload"] = loaded_payload
                _MODEL_LB_CACHE["updated_at"] = loaded_updated_at
                _MODEL_LB_CACHE["error"] = loaded_error



def _write_model_leaderboard_cache(payload: Dict[str, Any], updated_at: float, error: Optional[str] = None) -> None:
    MODEL_LB_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_LB_CACHE_PATH.write_text(
        json.dumps({"payload": payload, "updated_at": updated_at, "error": error}, ensure_ascii=False),
        encoding="utf-8",
    )



def _refresh_model_leaderboard_cache(*, preclaimed: bool = False) -> None:
    attempt_started_at = time.time()
    if not preclaimed:
        with _MODEL_LB_CACHE_LOCK:
            if _MODEL_LB_CACHE.get("refreshing"):
                return
            _MODEL_LB_CACHE["refreshing"] = True
            _MODEL_LB_CACHE["error"] = None
            _MODEL_LB_CACHE["last_refresh_attempt_at"] = attempt_started_at
            _MODEL_LB_CACHE["last_refresh_reason"] = "direct_refresh"
    try:
        payload = _build_model_leaderboard_payload()
        updated_at = time.time()
        with _MODEL_LB_CACHE_LOCK:
            _MODEL_LB_CACHE.update({
                "payload": payload,
                "updated_at": updated_at,
                "refreshing": False,
                "error": None,
                "last_refresh_attempt_at": float(_MODEL_LB_CACHE.get("last_refresh_attempt_at") or attempt_started_at),
            })
        _write_model_leaderboard_cache(payload, updated_at)
        _persist_model_leaderboard_snapshot(payload)
    except Exception as exc:
        with _MODEL_LB_CACHE_LOCK:
            _MODEL_LB_CACHE["refreshing"] = False
            _MODEL_LB_CACHE["error"] = str(exc)
            _MODEL_LB_CACHE["last_refresh_attempt_at"] = float(_MODEL_LB_CACHE.get("last_refresh_attempt_at") or attempt_started_at)
        _write_model_leaderboard_cache(_MODEL_LB_CACHE.get("payload") or {}, float(_MODEL_LB_CACHE.get("updated_at") or 0.0), str(exc))
        logger.exception("Model leaderboard refresh failed")



def _spawn_model_leaderboard_refresh_thread(reason: str) -> bool:
    attempt_started_at = time.time()
    with _MODEL_LB_CACHE_LOCK:
        if _MODEL_LB_CACHE.get("refreshing"):
            return False
        _MODEL_LB_CACHE["refreshing"] = True
        _MODEL_LB_CACHE["error"] = None
        _MODEL_LB_CACHE["last_refresh_attempt_at"] = attempt_started_at
        _MODEL_LB_CACHE["last_refresh_reason"] = reason
    threading.Thread(
        target=_refresh_model_leaderboard_cache,
        kwargs={"preclaimed": True},
        daemon=True,
    ).start()
    return True



def _ensure_model_leaderboard_refresh(force: bool = False) -> None:
    now = time.time()
    with _MODEL_LB_CACHE_LOCK:
        payload = _MODEL_LB_CACHE.get("payload")
        refreshing = bool(_MODEL_LB_CACHE.get("refreshing"))
        updated_at = float(_MODEL_LB_CACHE.get("updated_at") or 0.0)
        last_refresh_attempt_at = float(_MODEL_LB_CACHE.get("last_refresh_attempt_at") or 0.0)
    if refreshing:
        return

    stale = updated_at <= 0 or (now - updated_at) > _MODEL_LB_STALE_AFTER_SEC
    if force:
        _spawn_model_leaderboard_refresh_thread("force_refresh")
        return
    if payload is None:
        _spawn_model_leaderboard_refresh_thread("cache_missing")
        return
    if stale:
        cooldown_remaining = _MODEL_LB_REFRESH_COOLDOWN_SEC - (now - last_refresh_attempt_at)
        if cooldown_remaining <= 0:
            _spawn_model_leaderboard_refresh_thread("cache_stale")


@lru_cache(maxsize=4)
def _load_predictor_cached(model_mtime_ns: int, regime_mtime_ns: int):
    from model import predictor as predictor_module

    return predictor_module.load_predictor()



def _safe_file_mtime_ns(path: Optional[str]) -> int:
    if not path:
        return -1
    try:
        return Path(path).stat().st_mtime_ns
    except OSError:
        return -1



def _get_loaded_predictor_cached():
    from model import predictor as predictor_module

    model_path = getattr(predictor_module, "MODEL_PATH", None)
    regime_path = None
    if model_path:
        regime_path = str(model_path).replace("xgb_model.pkl", "regime_models.pkl")
    return _load_predictor_cached(
        _safe_file_mtime_ns(model_path),
        _safe_file_mtime_ns(regime_path),
    )


@router.get("/models/leaderboard")
async def api_model_leaderboard(force: bool = False) -> Dict[str, Any]:
    """回傳所有 ML 模型的 Walk-Forward Leaderboard。

    採用 stale-while-revalidate：有 cache 時直接回 cache；只要快取過期就自動背景重算，
    但會套用 cooldown 避免 Strategy Lab 的輪詢把 leaderboard 重建打爆。
    """
    _load_model_leaderboard_cache_file()
    _ensure_model_leaderboard_refresh(force=force)

    with _MODEL_LB_CACHE_LOCK:
        payload = _MODEL_LB_CACHE.get("payload")
        updated_at = float(_MODEL_LB_CACHE.get("updated_at") or 0.0)
        refreshing = bool(_MODEL_LB_CACHE.get("refreshing"))
        error = _MODEL_LB_CACHE.get("error")
        last_refresh_attempt_at = float(_MODEL_LB_CACHE.get("last_refresh_attempt_at") or 0.0)
        last_refresh_reason = _MODEL_LB_CACHE.get("last_refresh_reason")

    payload = _normalize_model_leaderboard_payload(payload) if isinstance(payload, dict) else payload
    governance_payload = _load_leaderboard_governance_summary()
    high_conviction_topk_payload = _load_high_conviction_topk_summary()
    if isinstance(payload, dict) and _should_override_leaderboard_governance(
        payload.get("leaderboard_governance"),
        governance_payload,
    ):
        payload = {**payload, "leaderboard_governance": governance_payload}
    if isinstance(payload, dict) and isinstance(high_conviction_topk_payload, dict):
        # High-conviction Top-K is cheap to load but contains live deployment-support
        # overlays from live_predict_probe.json. Never serve stale cached support
        # routes here: Strategy Lab uses this endpoint to decide whether promising
        # OOS rows are deployable, and stale proxy governance can falsely imply
        # deployment closure after the live bucket changes.
        payload = {**payload, "high_conviction_topk": high_conviction_topk_payload}

    now = time.time()
    age_sec = now - updated_at if updated_at else None
    stale = age_sec is None or age_sec > _MODEL_LB_STALE_AFTER_SEC
    cooldown_remaining_sec = None
    if stale and last_refresh_attempt_at:
        cooldown_remaining_sec = max(int(_MODEL_LB_REFRESH_COOLDOWN_SEC - (now - last_refresh_attempt_at)), 0)
    next_retry_at = None
    if cooldown_remaining_sec:
        next_retry_at = datetime.utcfromtimestamp(last_refresh_attempt_at + _MODEL_LB_REFRESH_COOLDOWN_SEC).isoformat() + "Z"

    if payload:
        warning = None
        if refreshing:
            warning = "模型排行榜快取已過期；背景正在重算最新結果。"
        elif stale and cooldown_remaining_sec:
            warning = f"模型排行榜快取已過期；最近剛觸發背景重算，{cooldown_remaining_sec} 秒後若仍過期會自動再試。"
        elif stale:
            warning = "模型排行榜快取已過期；API 已排入背景重算最新結果。"
        return {
            **payload,
            "cached": True,
            "refreshing": refreshing,
            "stale": bool(stale),
            "updated_at": datetime.utcfromtimestamp(updated_at).isoformat() + "Z" if updated_at else None,
            "cache_age_sec": int(age_sec) if age_sec is not None else None,
            "warning": warning,
            "error": error,
            "refresh_reason": last_refresh_reason,
            "refresh_cooldown_sec": _MODEL_LB_REFRESH_COOLDOWN_SEC,
            "next_retry_at": next_retry_at,
        }

    if not refreshing:
        _ensure_model_leaderboard_refresh(force=True)

    return {
        "leaderboard": payload.get("leaderboard", []) if isinstance(payload, dict) else [],
        "quadrant_points": payload.get("quadrant_points", []) if isinstance(payload, dict) else [],
        "count": payload.get("count", 0) if isinstance(payload, dict) else 0,
        "cached": bool(payload),
        "refreshing": True,
        "stale": True,
        "updated_at": datetime.utcfromtimestamp(updated_at).isoformat() + "Z" if updated_at else None,
        "cache_age_sec": int(age_sec) if age_sec is not None else None,
        "warning": "Model leaderboard warming in background",
        "error": error,
        "refresh_reason": last_refresh_reason,
        "refresh_cooldown_sec": _MODEL_LB_REFRESH_COOLDOWN_SEC,
        "next_retry_at": next_retry_at,
    }



@router.get("/models/leaderboard/history")
async def api_model_leaderboard_history(limit: int = 10) -> Dict[str, Any]:
    history = _load_model_leaderboard_history(limit=limit)
    return {
        "count": len(history),
        "history": history,
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


def _set_strategy_job_progress(
    job_id: Optional[str],
    progress: int,
    detail: str,
    *,
    status: str = "running",
    stage_key: Optional[str] = None,
) -> None:
    if not job_id:
        return
    with _STRATEGY_RUN_LOCK:
        job = _STRATEGY_RUN_JOBS.get(job_id)
        if not job:
            return
        if stage_key:
            job["stage_key"] = stage_key
        active_stage_key = stage_key or job.get("stage_key")
        job.update({
            "status": status,
            "progress": max(0, min(100, int(progress))),
            "detail": detail,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        })
        _update_strategy_job_steps(job, active_stage_key, status=status)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


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
        pnl = float(trade.get("pnl", 0.0) or 0.0)
        bucket["trades"] += 1
        bucket["total_pnl"] += pnl
        if pnl > 0:
            bucket["wins"] += 1
            bucket["gross_profit"] += pnl
        else:
            bucket["losses"] += 1
            bucket["gross_loss"] += abs(pnl)

    ordered = []
    for regime in ("bull", "bear", "chop", "unknown"):
        bucket = grouped.get(regime)
        if not bucket:
            continue
        trades_count = bucket["trades"]
        ordered.append({
            "regime": regime,
            "trades": trades_count,
            "wins": bucket["wins"],
            "losses": bucket["losses"],
            "win_rate": round(bucket["wins"] / trades_count, 4) if trades_count else None,
            "total_pnl": round(bucket["total_pnl"], 2),
            "roi": round(bucket["total_pnl"] / initial_capital, 4) if initial_capital else None,
            "profit_factor": round(bucket["gross_profit"] / max(bucket["gross_loss"], 0.01), 4),
        })
    return ordered


def _compute_strategy_risk(last_results: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(last_results, dict):
        return {
            "stability_score": None,
            "stability_label": "—",
            "overfit_risk": "unknown",
            "trade_sufficiency": "unknown",
            "risk_reasons": ["尚未有回測結果"],
        }

    total_trades = int(last_results.get("total_trades") or 0)
    max_dd = float(last_results.get("max_drawdown") or 0.0)
    max_loss_streak = int(last_results.get("max_consecutive_losses") or 0)
    roi = float(last_results.get("roi") or 0.0)
    win_rate = float(last_results.get("win_rate") or 0.0)

    if total_trades >= 40:
        trade_sufficiency = "high"
    elif total_trades >= 20:
        trade_sufficiency = "medium"
    else:
        trade_sufficiency = "low"

    stability_score = max(
        0,
        min(
            100,
            round(100 - max_dd * 120 - max_loss_streak * 8 - max(0, 20 - total_trades) * 1.5),
        ),
    )
    if stability_score >= 75:
        stability_label = "穩定"
    elif stability_score >= 50:
        stability_label = "中等"
    else:
        stability_label = "脆弱"

    risk_points = 0
    reasons: List[str] = []
    if total_trades < 12:
        risk_points += 2
        reasons.append("交易數過少")
    elif total_trades < 25:
        risk_points += 1
        reasons.append("交易數偏少")

    if max_dd > 0.35:
        risk_points += 2
        reasons.append("最大回撤過大")
    elif max_dd > 0.22:
        risk_points += 1
        reasons.append("最大回撤偏高")

    if max_loss_streak >= 5:
        risk_points += 2
        reasons.append("連敗過長")
    elif max_loss_streak >= 3:
        risk_points += 1
        reasons.append("連敗偏多")

    if total_trades < 20 and (roi > 0.20 or win_rate > 0.70):
        risk_points += 2
        reasons.append("樣本少但表現過於漂亮")
    elif total_trades < 35 and (roi > 0.12 or win_rate > 0.65):
        risk_points += 1
        reasons.append("樣本不足下績效偏亮眼")

    if risk_points >= 4:
        overfit_risk = "high"
    elif risk_points >= 2:
        overfit_risk = "medium"
    else:
        overfit_risk = "low"

    return {
        "stability_score": stability_score,
        "stability_label": stability_label,
        "overfit_risk": overfit_risk,
        "trade_sufficiency": trade_sufficiency,
        "risk_reasons": reasons or ["樣本與風險指標正常"],
    }


STRATEGY_LB_SORT_SEMANTICS_V2 = "Overall -> Reliability -> Return Power -> Risk Control -> Capital Efficiency (win_rate reference only)"


def _compute_strategy_scorecard(last_results: Optional[Dict[str, Any]], risk: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not isinstance(last_results, dict):
        return {
            "overall_score": None,
            "reliability_score": None,
            "return_power_score": None,
            "risk_control_score": None,
            "capital_efficiency_score": None,
            "rank_delta": 0,
        }
    risk = risk or _compute_strategy_risk(last_results)
    roi = float(last_results.get("roi") or 0.0)
    max_dd = float(last_results.get("max_drawdown") or 0.0)
    profit_factor = float(last_results.get("profit_factor") or 0.0)
    avg_time_underwater = float(last_results.get("avg_expected_time_underwater") or 0.0)
    decision_quality = float(last_results.get("avg_decision_quality_score") or 0.0)
    avg_allowed_layers = float(last_results.get("avg_allowed_layers") or 0.0)
    total_trades = float(last_results.get("total_trades") or 0.0)
    overfit_risk = str((risk or {}).get("overfit_risk") or "unknown")
    overfit_penalty = 1.0 if overfit_risk == "high" else 0.5 if overfit_risk == "medium" else 0.0
    trade_count_score = _clamp01(total_trades / 30.0)
    roi_score = _clamp01(0.5 + roi / 0.20)
    max_drawdown_score = _clamp01(1.0 - max_dd / 0.35)
    profit_factor_score = _clamp01((profit_factor - 1.0) / 1.5)
    time_underwater_score = _clamp01(1.0 - avg_time_underwater / 0.60)
    decision_quality_score = _clamp01(decision_quality)
    allowed_layers_score = _clamp01(avg_allowed_layers / 3.0)

    reliability_score = round(
        0.35 * max_drawdown_score
        + 0.30 * time_underwater_score
        + 0.15 * (1.0 - overfit_penalty)
        + 0.10 * trade_count_score
        + 0.10 * _clamp01((float((risk or {}).get("stability_score") or 0.0)) / 100.0),
        4,
    )
    return_power_score = round(
        0.50 * roi_score
        + 0.30 * profit_factor_score
        + 0.20 * decision_quality_score,
        4,
    )
    risk_control_score = round(
        0.45 * max_drawdown_score
        + 0.35 * time_underwater_score
        + 0.20 * (1.0 - overfit_penalty),
        4,
    )
    capital_efficiency_score = round(
        0.45 * decision_quality_score
        + 0.25 * profit_factor_score
        + 0.15 * time_underwater_score
        + 0.15 * allowed_layers_score,
        4,
    )
    overall_score = round(
        0.35 * reliability_score
        + 0.30 * return_power_score
        + 0.20 * risk_control_score
        + 0.15 * capital_efficiency_score,
        4,
    )
    return {
        "overall_score": overall_score,
        "reliability_score": reliability_score,
        "return_power_score": return_power_score,
        "risk_control_score": risk_control_score,
        "capital_efficiency_score": capital_efficiency_score,
        "time_underwater_score": time_underwater_score,
        "decision_quality_component": decision_quality_score,
        "rank_delta": 0,
    }


def _ensure_strategy_leaderboard_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leaderboard_strategy_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            target_col TEXT,
            strategy_count INTEGER NOT NULL DEFAULT 0,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leaderboard_strategy_scorecards (
            snapshot_id INTEGER NOT NULL,
            rank INTEGER NOT NULL,
            strategy_name TEXT NOT NULL,
            overall_score REAL,
            reliability_score REAL,
            return_power_score REAL,
            risk_control_score REAL,
            capital_efficiency_score REAL,
            roi REAL,
            max_drawdown REAL,
            total_trades REAL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (snapshot_id, rank)
        )
        """
    )


def _load_recent_strategy_leaderboard_snapshots(limit: int = 12, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            _ensure_strategy_leaderboard_tables(conn)
            rows = conn.execute(
                "SELECT id, created_at, target_col, strategy_count FROM leaderboard_strategy_snapshots ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Failed to load strategy leaderboard snapshots: %s", exc)
        return []


def _compute_strategy_rank_deltas(rows: List[Dict[str, Any]], db_path: str = DB_PATH) -> Dict[str, int]:
    if len(rows) < 2:
        return {}
    latest_snapshot_id = rows[0].get("id")
    previous_snapshot_id = rows[1].get("id")
    try:
        conn = sqlite3.connect(db_path)
        try:
            latest_rows = conn.execute(
                "SELECT strategy_name, rank FROM leaderboard_strategy_scorecards WHERE snapshot_id=?",
                (latest_snapshot_id,),
            ).fetchall()
            previous_rows = conn.execute(
                "SELECT strategy_name, rank FROM leaderboard_strategy_scorecards WHERE snapshot_id=?",
                (previous_snapshot_id,),
            ).fetchall()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Failed to compute strategy rank deltas: %s", exc)
        return {}
    latest_map = {str(name): int(rank) for name, rank in latest_rows}
    previous_map = {str(name): int(rank) for name, rank in previous_rows}
    return {name: int(previous_map[name] - rank) for name, rank in latest_map.items() if name in previous_map}


def _load_strategy_rank_map(snapshot_id: Optional[int], db_path: str = DB_PATH) -> Dict[str, int]:
    if snapshot_id is None:
        return {}
    try:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT strategy_name, rank FROM leaderboard_strategy_scorecards WHERE snapshot_id=?",
                (snapshot_id,),
            ).fetchall()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Failed to load strategy rank map: %s", exc)
        return {}
    return {str(name): int(rank) for name, rank in rows}


def _compute_strategy_rank_deltas_against_latest_snapshot(current_rows: List[Dict[str, Any]], db_path: str = DB_PATH) -> Dict[str, int]:
    snapshot_history = _load_recent_strategy_leaderboard_snapshots(limit=1, db_path=db_path)
    if not snapshot_history:
        return {}
    latest_snapshot_id = snapshot_history[0].get("id")
    previous_map = _load_strategy_rank_map(latest_snapshot_id, db_path=db_path)
    current_map = {
        str(entry.get("name")): idx
        for idx, entry in enumerate(current_rows or [], start=1)
        if entry.get("name") is not None
    }
    return {
        name: int(previous_map[name] - rank)
        for name, rank in current_map.items()
        if name in previous_map
    }


def _persist_strategy_leaderboard_snapshot(strategies: List[Dict[str, Any]], db_path: str = DB_PATH) -> None:
    try:
        conn = sqlite3.connect(db_path)
        try:
            _ensure_strategy_leaderboard_tables(conn)
            created_at = datetime.utcnow().isoformat() + "Z"
            target_col = (strategies[0].get("last_results") or {}).get("target_col") if strategies else None
            cursor = conn.execute(
                "INSERT INTO leaderboard_strategy_snapshots(created_at, target_col, strategy_count, payload_json) VALUES (?, ?, ?, ?)",
                (created_at, target_col, len(strategies), json.dumps({"strategies": strategies}, ensure_ascii=False)),
            )
            snapshot_id = int(cursor.lastrowid)
            for rank, entry in enumerate(strategies, start=1):
                results = entry.get("last_results") or {}
                conn.execute(
                    "INSERT INTO leaderboard_strategy_scorecards(snapshot_id, rank, strategy_name, overall_score, reliability_score, return_power_score, risk_control_score, capital_efficiency_score, roi, max_drawdown, total_trades, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        snapshot_id,
                        rank,
                        entry.get("name"),
                        results.get("overall_score"),
                        results.get("reliability_score"),
                        results.get("return_power_score"),
                        results.get("risk_control_score"),
                        results.get("capital_efficiency_score"),
                        results.get("roi"),
                        results.get("max_drawdown"),
                        results.get("total_trades"),
                        json.dumps(entry, ensure_ascii=False),
                    ),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Failed to persist strategy leaderboard snapshot: %s", exc)


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
    *,
    timestamps: List[str],
    equity_curve: List[Dict[str, Any]],
    trades: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build chart payload from the full executed backtest window.

    Earlier versions cropped the persisted equity curve / chart context down to the
    first→last trade window. That made a real 2-year backtest *look* like a 1-year
    run whenever the strategy stayed flat for a long warm-up period before its first
    trade. Keep the full window so operators can distinguish:
    - no trades yet / flat equity in the first segment
    - versus a genuinely shorter backtest range.

    Productization follow-up: keeping the *entire* 2-year 4h equity curve in every
    Strategy Lab payload bloats `/api/strategies/{name}` into multi-megabyte
    responses. The chart itself already renders a bounded window (`chart_context`
    max 1000 points), so return a downsampled equity curve while preserving the
    full time span in `chart_context.start/end`.
    """
    full_timestamps = [str(point.get("timestamp")) for point in equity_curve if point.get("timestamp")]
    chart_timestamps = timestamps or full_timestamps
    chart_context = _build_strategy_chart_context(chart_timestamps)
    chart_limit = int(chart_context.get("limit") or 1000)
    return {
        "equity_curve": _downsample_strategy_series_points(equity_curve, limit=chart_limit),
        "chart_context": chart_context,
    }


def _filter_strategy_rows_by_backtest_range(
    rows: List[Any],
    *,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> tuple[List[Any], Dict[str, Any]]:
    filtered_rows = list(rows or [])
    requested_start = _parse_backtest_timestamp(start) if start else None
    requested_end = _parse_backtest_timestamp(end) if end else None
    available_start = _parse_backtest_timestamp(rows[0][0]) if rows else None
    available_end = _parse_backtest_timestamp(rows[-1][0]) if rows else None

    if requested_start or requested_end:
        filtered_rows = []
        for row in rows or []:
            row_dt = _parse_backtest_timestamp(row[0] if row else None)
            if row_dt is None:
                continue
            if requested_start and row_dt < requested_start:
                continue
            if requested_end and row_dt > requested_end:
                continue
            filtered_rows.append(row)

    effective_start = _iso_utc_timestamp(filtered_rows[0][0]) if filtered_rows else None
    effective_end = _iso_utc_timestamp(filtered_rows[-1][0]) if filtered_rows else None
    missing_start_days = 0.0
    missing_end_days = 0.0
    if requested_start and available_start and requested_start < available_start:
        missing_start_days = round((available_start - requested_start).total_seconds() / 86400.0, 2)
    if requested_end and available_end and requested_end > available_end:
        missing_end_days = round((requested_end - available_end).total_seconds() / 86400.0, 2)
    coverage_ok = (missing_start_days <= 0 and missing_end_days <= 0)
    return filtered_rows, {
        "requested": {
            "start": _iso_utc_timestamp(start),
            "end": _iso_utc_timestamp(end),
        },
        "effective": {
            "start": effective_start,
            "end": effective_end,
        },
        "backfill_required": not coverage_ok,
        "coverage_ok": coverage_ok,
        "missing_start_days": missing_start_days,
        "missing_end_days": missing_end_days,
        "row_count": len(filtered_rows),
    }



def _resolve_default_strategy_backtest_range(
    *,
    requested_start: Optional[str],
    requested_end: Optional[str],
    available_start: Optional[str],
    available_end: Optional[str],
    lookback_days: int = 730,
) -> tuple[Optional[str], Optional[str], Dict[str, Any]]:
    if requested_start or requested_end:
        return requested_start, requested_end, {
            "mode": "explicit_range",
            "lookback_days": int(lookback_days),
            "requested_range_was_empty": False,
        }

    available_start_dt = _parse_backtest_timestamp(available_start) if available_start else None
    available_end_dt = _parse_backtest_timestamp(available_end) if available_end else None
    if available_end_dt is None:
        return requested_start, requested_end, {
            "mode": "unavailable",
            "lookback_days": int(lookback_days),
            "requested_range_was_empty": True,
        }

    default_start_dt = available_end_dt - timedelta(days=max(int(lookback_days), 1))
    if available_start_dt and default_start_dt < available_start_dt:
        default_start_dt = available_start_dt

    return (
        _iso_utc_timestamp(default_start_dt),
        _iso_utc_timestamp(available_end_dt),
        {
            "mode": "latest_two_year_default",
            "lookback_days": int(lookback_days),
            "requested_range_was_empty": True,
        },
    )



def _get_sqlite_db_path(db) -> Optional[str]:
    try:
        bind = db.get_bind()
    except Exception:
        return None
    if bind is None:
        return None
    return bind.url.database or None


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


def _align_strategy_results_to_backtest_window(last_results: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(last_results, dict):
        return last_results

    backtest_range = last_results.get("backtest_range") if isinstance(last_results.get("backtest_range"), dict) else {}
    effective = backtest_range.get("effective") if isinstance(backtest_range.get("effective"), dict) else {}
    requested = backtest_range.get("requested") if isinstance(backtest_range.get("requested"), dict) else {}
    display_start = effective.get("start") or requested.get("start")
    display_end = effective.get("end") or requested.get("end")

    if display_start or display_end:
        chart_context = dict(last_results.get("chart_context") or {})
        if chart_context:
            current_start = _parse_backtest_timestamp(chart_context.get("start"))
            current_end = _parse_backtest_timestamp(chart_context.get("end"))
            target_start = _parse_backtest_timestamp(display_start) if display_start else None
            target_end = _parse_backtest_timestamp(display_end) if display_end else None
            if target_start and (current_start is None or target_start < current_start):
                chart_context["start"] = display_start
            if target_end and (current_end is None or target_end > current_end):
                chart_context["end"] = display_end
            last_results["chart_context"] = chart_context

        equity_curve = last_results.get("equity_curve")
        if isinstance(equity_curve, list) and equity_curve and display_start:
            first_point = equity_curve[0] if isinstance(equity_curve[0], dict) else None
            first_ts = _parse_backtest_timestamp(first_point.get("timestamp")) if first_point else None
            target_start = _parse_backtest_timestamp(display_start)
            if first_point and target_start and first_ts and target_start < first_ts:
                prefix_point = dict(first_point)
                prefix_point["timestamp"] = display_start
                prefix_point["position_pct"] = 0.0
                prefix_point["position_layers"] = 0
                last_results["equity_curve"] = [prefix_point, *equity_curve]

    return last_results



def _decorate_strategy_entry(entry: Dict[str, Any], db=None) -> Dict[str, Any]:
    enriched = dict(entry)
    last_results = dict(entry.get("last_results") or {})

    trades = last_results.get("trades") or []
    total_trades = int(last_results.get("total_trades") or 0)
    can_backfill_decision_profile = bool(trades) and (total_trades <= 0 or total_trades <= len(trades))
    if can_backfill_decision_profile:
        decision_profile = _compute_decision_profile(trades)
        for key, value in decision_profile.items():
            if key == "regime_gate_summary":
                existing_summary = last_results.get(key)
                if not isinstance(existing_summary, dict) or not existing_summary:
                    last_results[key] = value
                continue
            if last_results.get(key) is None:
                last_results[key] = value

    if db is not None:
        quality_profile = _compute_strategy_decision_quality_profile(last_results.get("trades") or [], db=db)
        for key, value in quality_profile.items():
            if last_results.get(key) is None:
                last_results[key] = value

    contract_horizon = int(last_results.get("decision_quality_horizon_minutes") or 1440)
    for key, value in _strategy_decision_contract_meta(horizon_minutes=contract_horizon).items():
        if last_results.get(key) is None:
            last_results[key] = value

    risk = _compute_strategy_risk(last_results)
    computed_scorecard = _compute_strategy_scorecard(last_results, risk)
    effective_scorecard: Dict[str, Any] = {}
    for key, value in computed_scorecard.items():
        if key == "rank_delta":
            effective_scorecard[key] = value
            continue
        if last_results.get(key) is None:
            last_results[key] = value
        effective_scorecard[key] = last_results.get(key)

    last_results["sort_semantics"] = STRATEGY_LB_SORT_SEMANTICS_V2
    last_results = _align_strategy_results_to_backtest_window(last_results)
    last_results = _normalize_result_timestamps(last_results)
    enriched["last_results"] = last_results or None
    enriched["decision_contract"] = {
        **_strategy_decision_contract_meta(horizon_minutes=contract_horizon),
        "sort_semantics": STRATEGY_LB_SORT_SEMANTICS_V2,
    }
    enriched.update(risk)
    enriched.update(effective_scorecard)
    return enriched


def _strategy_leaderboard_sort_key(entry: Dict[str, Any]):
    results = entry.get("last_results") or {}
    return (
        float(results.get("overall_score") if results.get("overall_score") is not None else -999.0),
        float(results.get("reliability_score") if results.get("reliability_score") is not None else -999.0),
        float(results.get("return_power_score") if results.get("return_power_score") is not None else -999.0),
        float(results.get("risk_control_score") if results.get("risk_control_score") is not None else -999.0),
        float(results.get("capital_efficiency_score") if results.get("capital_efficiency_score") is not None else -999.0),
        float(results.get("roi") if results.get("roi") is not None else -999.0),
        -(float(results.get("max_drawdown") if results.get("max_drawdown") is not None else 999.0)),
    )


def _ensure_auto_generated_strategy_leaderboard(force: bool = False) -> Dict[str, Any]:
    from backtesting.strategy_lab import AUTO_STRATEGY_NAME_PREFIX, load_all_strategies

    strategies = load_all_strategies(include_internal=True)
    auto_rows = [
        entry for entry in strategies
        if str(entry.get("name") or "").startswith(AUTO_STRATEGY_NAME_PREFIX)
    ]
    return {
        "force": bool(force),
        "auto_strategy_count": len(auto_rows),
        "status": "present" if auto_rows else "empty",
    }


def _execute_strategy_run(body: Dict[str, Any], *, job_id: Optional[str] = None) -> Dict[str, Any]:
    from backtesting.strategy_lab import (
        AUTO_STRATEGY_NAME_PREFIX,
        MANUAL_COPY_STRATEGY_PREFIX,
        _is_auto_leaderboard_strategy,
        load_strategy,
        run_hybrid_backtest,
        run_rule_backtest,
        save_strategy,
    )
    from scripts import backfill_backtest_range as backfill_module

    name = str(body.get("name", "unnamed_strategy") or "").strip()
    source_strategy_name = str(body.get("source_strategy_name") or "").strip()
    stype = body.get("type", "rule_based")
    params = body.get("params", {}) if isinstance(body.get("params"), dict) else {}
    initial = float(body.get("initial_capital", 10000.0) or 10000.0)
    auto_backfill = bool(body.get("auto_backfill", params.get("auto_backfill", False)))
    allow_internal_overwrite = bool(body.get("allow_internal_overwrite"))
    save_name = name
    if not allow_internal_overwrite:
        if not save_name:
            return {"error": "請先輸入策略名稱。"}
        source_is_system_generated = _is_auto_leaderboard_strategy(source_strategy_name) if source_strategy_name else False
        if source_is_system_generated and (
            save_name == source_strategy_name
            or save_name.startswith(AUTO_STRATEGY_NAME_PREFIX)
            or save_name.startswith(MANUAL_COPY_STRATEGY_PREFIX)
        ):
            return {"error": "系統生成策略不能直接儲存；請先輸入新的策略名稱。"}
        existing = load_strategy(save_name)
        if existing is not None and save_name != source_strategy_name:
            return {"error": "策略名稱已存在；請使用唯一名稱。"}
    requested_range = body.get("backtest_range") if isinstance(body.get("backtest_range"), dict) else {}
    requested_start = requested_range.get("start")
    requested_end = requested_range.get("end")

    _set_strategy_job_progress(job_id, 5, "正在載入回測資料與特徵欄位。", stage_key="load_data")
    rows = _load_strategy_data()
    if not rows:
        return {"error": "No data available for backtest"}

    requested_start, requested_end, backtest_policy = _resolve_default_strategy_backtest_range(
        requested_start=requested_start,
        requested_end=requested_end,
        available_start=_iso_utc_timestamp(rows[0][0]) if rows else None,
        available_end=_iso_utc_timestamp(rows[-1][0]) if rows else None,
    )

    active_rows = list(rows)
    range_meta = {
        "requested": {
            "start": _iso_utc_timestamp(requested_start),
            "end": _iso_utc_timestamp(requested_end),
        },
        "effective": {
            "start": _iso_utc_timestamp(rows[0][0]) if rows else None,
            "end": _iso_utc_timestamp(rows[-1][0]) if rows else None,
        },
        "backfill_required": False,
        "coverage_ok": True,
        "missing_start_days": 0.0,
        "missing_end_days": 0.0,
        "row_count": len(rows),
        "policy": backtest_policy,
    }
    if requested_start or requested_end:
        active_rows, range_meta = _filter_strategy_rows_by_backtest_range(rows, start=requested_start, end=requested_end)
        range_meta["policy"] = backtest_policy
        if auto_backfill and range_meta.get("backfill_required"):
            _set_strategy_job_progress(job_id, 14, "回測範圍超出本地資料，正在回填原始行情。", stage_key="backfill_raw")
            backfill_session = get_db()
            try:
                backfill_kwargs: Dict[str, Any] = {
                    "target_start": requested_start,
                    "target_end": requested_end,
                    "apply_changes": True,
                }
                symbol = body.get("symbol") or params.get("symbol")
                if symbol:
                    backfill_kwargs["symbol"] = symbol
                backfill_module.run_backfill_pipeline(backfill_session, **backfill_kwargs)
            finally:
                if hasattr(backfill_session, "close"):
                    backfill_session.close()
            _set_strategy_job_progress(job_id, 17, "原始行情已回填，正在補算 features。", stage_key="backfill_features")
            _set_strategy_job_progress(job_id, 19, "features 已補算，正在補算 labels。", stage_key="backfill_labels")
            _set_strategy_job_progress(job_id, 21, "回填完成，正在重新載入回測資料。", stage_key="reload_data")
            rows = _load_strategy_data()
            active_rows, range_meta = _filter_strategy_rows_by_backtest_range(rows, start=requested_start, end=requested_end)
            range_meta["policy"] = backtest_policy
        if not active_rows:
            return {"error": "No rows available inside requested backtest range"}
    elif not active_rows:
        return {"error": "No data available for backtest"}

    timestamps = [str(r[0]) for r in active_rows]
    prices = [float(r[1]) for r in active_rows]
    bias50 = [float(r[2]) if len(r) > 2 and r[2] is not None else 0.0 for r in active_rows]
    bias200 = [float(r[3]) if len(r) > 3 and r[3] is not None else 0.0 for r in active_rows]
    nose = [float(r[4]) if len(r) > 4 and r[4] is not None else 0.5 for r in active_rows]
    pulse = [float(r[5]) if len(r) > 5 and r[5] is not None else 0.5 for r in active_rows]
    ear = [float(r[6]) if len(r) > 6 and r[6] is not None else 0.0 for r in active_rows]
    regimes = [str(r[7]).lower() if len(r) > 7 and r[7] else "unknown" for r in active_rows]
    bb_pct_b_4h = [float(r[8]) if len(r) > 8 and r[8] is not None else None for r in active_rows]
    dist_bb_lower_4h = [float(r[9]) if len(r) > 9 and r[9] is not None else None for r in active_rows]
    dist_swing_low_4h = [float(r[10]) if len(r) > 10 and r[10] is not None else None for r in active_rows]
    local_bottom_score = [float(r[11]) if len(r) > 11 and r[11] is not None else None for r in active_rows]
    local_top_score = [float(r[12]) if len(r) > 12 and r[12] is not None else None for r in active_rows]
    score_series: List[Dict[str, Any]] = []

    db = get_db()
    try:
        db_path = _get_sqlite_db_path(db)
        if stype == "rule_based":
            _set_strategy_job_progress(job_id, 22, f"已載入 {len(active_rows)} 筆資料，正在執行 rule-based 回測。", stage_key="run_backtest")
            with ThreadPoolExecutor(max_workers=2) as executor:
                score_future = executor.submit(
                    _build_strategy_score_series,
                    timestamps,
                    bias50,
                    nose,
                    pulse,
                    ear,
                    bb_pct_b_4h=bb_pct_b_4h,
                    dist_bb_lower_4h=dist_bb_lower_4h,
                    dist_swing_low_4h=dist_swing_low_4h,
                )
                result = run_rule_backtest(
                    prices,
                    timestamps,
                    bias50,
                    bias200,
                    nose,
                    pulse,
                    ear,
                    params,
                    initial,
                    regimes=regimes,
                    bb_pct_b_4h=bb_pct_b_4h,
                    dist_bb_lower_4h=dist_bb_lower_4h,
                    dist_swing_low_4h=dist_swing_low_4h,
                    local_bottom_score=local_bottom_score,
                    local_top_score=local_top_score,
                )
                score_series = score_future.result()
        elif stype == "hybrid":
            model_name = str(params.get("model_name") or "xgboost")
            _set_strategy_job_progress(job_id, 24, f"Hybrid 模式：正在準備 {model_name} 訓練資料。", stage_key="prepare_hybrid")
            df = load_model_leaderboard_frame(DB_PATH)
            if df.empty:
                return {"error": "Hybrid 模式缺少可用訓練資料"}

            feature_cols = [c for c in df.columns if c.startswith("feat_")]
            target_col = "simulated_pyramid_win" if "simulated_pyramid_win" in df.columns else "label_spot_long_win"
            train_df = df.dropna(subset=[target_col]).copy()
            if train_df.empty:
                return {"error": "Hybrid 模式缺少 target 標籤資料"}

            from backtesting.model_leaderboard import ModelLeaderboard

            lb = ModelLeaderboard(train_df, target_col=target_col)
            signature = _build_cache_key(model_name, target_col, len(train_df), str(train_df["timestamp"].iloc[-1]))
            with _HYBRID_MODEL_LOCK:
                cached = _HYBRID_MODEL_CACHE.get(signature)
            if cached:
                confidence_map = cached["confidence_map"]
            else:
                _set_strategy_job_progress(job_id, 40, f"Hybrid 模式：正在訓練 {model_name}。", stage_key="train_model")
                model = lb._train_model(
                    train_df[feature_cols].fillna(0).values,
                    train_df[target_col].fillna(0).astype(int).values,
                    model_name,
                )
                if model is None:
                    return {"error": f"{model_name} 目前不可用"}
                confidence_map = {
                    _strategy_confidence_lookup_key(ts): float(conf)
                    for ts, conf in zip(
                        train_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S").values,
                        lb._get_confidence(model, train_df[feature_cols].fillna(0).values, model_name),
                    )
                }
                with _HYBRID_MODEL_LOCK:
                    _HYBRID_MODEL_CACHE[signature] = {
                        "confidence_map": confidence_map,
                        "updated_at": time.time(),
                    }
            conf = [
                confidence_map.get(_strategy_confidence_lookup_key(ts), max(0.0, min(1.0, 1.0 - b / 20.0)))
                for ts, b in zip(timestamps, bias50)
            ]
            _set_strategy_job_progress(job_id, 58, f"Hybrid 模式：{model_name} 已就緒，正在執行回測。", stage_key="run_backtest")
            with ThreadPoolExecutor(max_workers=2) as executor:
                score_future = executor.submit(
                    _build_strategy_score_series,
                    timestamps,
                    bias50,
                    nose,
                    pulse,
                    ear,
                    conf,
                    bb_pct_b_4h=bb_pct_b_4h,
                    dist_bb_lower_4h=dist_bb_lower_4h,
                    dist_swing_low_4h=dist_swing_low_4h,
                )
                result = run_hybrid_backtest(
                    prices,
                    timestamps,
                    bias50,
                    bias200,
                    nose,
                    pulse,
                    ear,
                    conf,
                    params,
                    initial,
                    regimes=regimes,
                    bb_pct_b_4h=bb_pct_b_4h,
                    dist_bb_lower_4h=dist_bb_lower_4h,
                    dist_swing_low_4h=dist_swing_low_4h,
                    local_bottom_score=local_bottom_score,
                    local_top_score=local_top_score,
                )
                score_series = score_future.result()
        else:
            return {"error": f"Unknown strategy type: {stype}"}

        _set_strategy_job_progress(job_id, 76, "回測核心完成，正在平行計算 benchmark、決策品質摘要與圖表上下文。", stage_key="postprocess")
        chart_payload = _select_strategy_chart_payload(
            timestamps=timestamps,
            equity_curve=result.equity_curve or [],
            trades=result.trades or [],
        )
        chart_context = chart_payload.get("chart_context") or _build_strategy_chart_context(timestamps)
        selected_equity_curve = chart_payload.get("equity_curve") or []
        full_trades = list(result.trades or [])
        strat_def = {"type": stype, "params": params}
        with ThreadPoolExecutor(max_workers=3) as executor:
            benchmarks_future = executor.submit(
                _compute_backtest_benchmarks,
                prices,
                timestamps,
                bias50,
                bias200,
                nose,
                pulse,
                ear,
                regimes,
                initial,
                params,
                bb_pct_b_4h=bb_pct_b_4h,
                dist_bb_lower_4h=dist_bb_lower_4h,
                dist_swing_low_4h=dist_swing_low_4h,
            )
            decision_profile_future = executor.submit(_compute_decision_profile, result.trades)
            canonical_quality_future = executor.submit(
                _compute_strategy_decision_quality_profile,
                result.trades,
                db=db,
                db_path=db_path,
            )
            benchmarks = benchmarks_future.result()
            decision_profile = decision_profile_future.result()
            canonical_quality_profile = canonical_quality_future.result()
        capital_management = params.get("capital_management") if isinstance(params.get("capital_management"), dict) else {}
        results_dict = {
            "roi": round(result.roi, 4),
            "win_rate": round(result.win_rate, 4),
            "total_trades": result.total_trades,
            "capital_mode": capital_management.get("mode") or "classic_pyramid",
            "wins": result.wins,
            "losses": result.losses,
            "max_drawdown": round(result.max_drawdown, 4),
            "profit_factor": round(result.profit_factor, 4),
            "total_pnl": round(result.total_pnl, 2),
            "avg_win": round(result.avg_win, 2),
            "avg_loss": round(result.avg_loss, 2),
            "max_consecutive_losses": result.max_consecutive_losses,
            "regime_breakdown": _compute_regime_breakdown(result.trades, initial),
            "benchmarks": benchmarks,
            "equity_curve": selected_equity_curve,
            "trades": full_trades,
            "score_series": score_series[-300:] if score_series else [],
            "chart_context": chart_context,
            "run_at": datetime.utcnow().isoformat() + "Z",
            **decision_profile,
            **canonical_quality_profile,
        }
        results_dict["backtest_range"] = range_meta
        contract_meta = _strategy_decision_contract_meta(
            horizon_minutes=int(results_dict.get("decision_quality_horizon_minutes") or 1440)
        )
        for key, value in contract_meta.items():
            results_dict.setdefault(key, value)

        _set_strategy_job_progress(job_id, 92, "正在儲存策略、整理圖表上下文與輸出結果。", stage_key="save_results")
        normalized_results = _normalize_result_timestamps(results_dict)
        save_strategy(save_name, strat_def, normalized_results)
        response = {
            "strategy": save_name,
            "requested_strategy_name": name,
            "type": stype,
            "params": params,
            "results": normalized_results,
            "decision_contract": contract_meta,
            "equity_curve": normalized_results.get("equity_curve") or [],
            "trades": normalized_results.get("trades") or [],
            "score_series": normalized_results.get("score_series") or [],
            "chart_context": _normalize_result_timestamps(chart_context),
        }
        _set_strategy_job_progress(job_id, 100, "回測、圖表與排行榜資料已全部同步完成。", status="completed", stage_key="save_results")
        return response
    finally:
        if hasattr(db, "close"):
            db.close()


@router.post("/strategies/run")
async def api_run_strategy(body: Dict[str, Any], request: Request = None):
    """同步執行策略回測。"""
    _assert_local_operator_request(request)
    return _execute_strategy_run(body)


@router.post("/strategies/run_async")
async def api_run_strategy_async(body: Dict[str, Any], request: Request = None):
    _assert_local_operator_request(request)
    job_id = uuid.uuid4().hex
    with _STRATEGY_RUN_LOCK:
        _STRATEGY_RUN_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "detail": "已建立回測任務，等待背景工作執行。",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "result": None,
            "error": None,
            "stage_key": "queued",
            "steps": _strategy_job_stage_plan(body),
        }

    def _runner() -> None:
        _set_strategy_job_progress(job_id, 2, "背景工作已啟動。", stage_key="queued")
        try:
            result = _execute_strategy_run(body, job_id=job_id)
            with _STRATEGY_RUN_LOCK:
                job = _STRATEGY_RUN_JOBS.get(job_id)
                if job is not None:
                    job["result"] = result
                    job["error"] = result.get("error") if isinstance(result, dict) else None
                    if isinstance(result, dict) and result.get("error"):
                        job["status"] = "failed"
                        _update_strategy_job_steps(job, job.get("stage_key"), status="failed")
                    else:
                        job["status"] = "completed"
                        job["progress"] = max(int(job.get("progress") or 0), 100)
                        job["updated_at"] = datetime.utcnow().isoformat() + "Z"
                        _update_strategy_job_steps(job, job.get("stage_key"), status="completed")
        except Exception as exc:
            logger.exception("Strategy async job failed")
            with _STRATEGY_RUN_LOCK:
                job = _STRATEGY_RUN_JOBS.get(job_id)
                if job is not None:
                    job.update({
                        "status": "failed",
                        "progress": 100,
                        "detail": f"回測失敗：{exc}",
                        "error": str(exc),
                        "updated_at": datetime.utcnow().isoformat() + "Z",
                    })
                    _update_strategy_job_steps(job, job.get("stage_key"), status="failed")

    _STRATEGY_RUN_EXECUTOR.submit(_runner)
    return {"job_id": job_id, "status": "queued", "progress": 0}


@router.get("/strategies/jobs/{job_id}")
async def api_strategy_job_status(job_id: str, request: Request = None):
    _assert_local_operator_request(request)
    with _STRATEGY_RUN_LOCK:
        job = _STRATEGY_RUN_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Strategy job '{job_id}' not found")
        return dict(job)


def _strategy_sort_key(entry: Dict[str, Any]):
    return _strategy_leaderboard_sort_key(entry)


_HEAVY_STRATEGY_RESULT_KEYS = {
    "equity_curve",
    "trades",
    "score_series",
}

_STRATEGY_DETAIL_EQUITY_CURVE_LIMIT = 1000
_STRATEGY_DETAIL_SCORE_SERIES_LIMIT = 300


def _downsample_strategy_series_points(points: Any, *, limit: int) -> List[Dict[str, Any]]:
    if not isinstance(points, list):
        return []
    normalized = [point for point in points if isinstance(point, dict)]
    if limit <= 0 or len(normalized) <= limit:
        return list(normalized)
    if limit == 1:
        return [normalized[-1]]

    max_index = len(normalized) - 1
    step = max_index / max(limit - 1, 1)
    selected_indices = {0, max_index}
    for slot in range(1, max(limit - 1, 1)):
        selected_indices.add(min(max_index, int(round(slot * step))))
    return [normalized[idx] for idx in sorted(selected_indices)]


def _prepare_strategy_detail_last_results(last_results: Any) -> Dict[str, Any]:
    if not isinstance(last_results, dict):
        return {}

    detail = dict(last_results)
    chart_context = detail.get("chart_context")
    chart_limit = _STRATEGY_DETAIL_EQUITY_CURVE_LIMIT
    if isinstance(chart_context, dict):
        raw_limit = chart_context.get("limit")
        try:
            parsed_limit = int(raw_limit)
        except (TypeError, ValueError):
            parsed_limit = _STRATEGY_DETAIL_EQUITY_CURVE_LIMIT
        chart_limit = max(2, min(parsed_limit or _STRATEGY_DETAIL_EQUITY_CURVE_LIMIT, _STRATEGY_DETAIL_EQUITY_CURVE_LIMIT))
        detail["chart_context"] = {
            **chart_context,
            "limit": chart_limit,
        }

    detail["equity_curve"] = _downsample_strategy_series_points(detail.get("equity_curve"), limit=chart_limit)
    score_series = detail.get("score_series")
    if isinstance(score_series, list):
        detail["score_series"] = list(score_series[-_STRATEGY_DETAIL_SCORE_SERIES_LIMIT:])
    return detail


def _prepare_strategy_detail_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    detail = dict(entry or {})
    detail["last_results"] = _prepare_strategy_detail_last_results(entry.get("last_results"))
    return detail


def _compact_strategy_last_results(last_results: Any) -> Dict[str, Any]:
    if not isinstance(last_results, dict):
        return {}
    compact = {key: value for key, value in last_results.items() if key not in _HEAVY_STRATEGY_RESULT_KEYS}
    chart_context = compact.get("chart_context")
    if isinstance(chart_context, dict):
        compact["chart_context"] = {
            "symbol": chart_context.get("symbol"),
            "interval": chart_context.get("interval"),
            "start": chart_context.get("start"),
            "end": chart_context.get("end"),
        }
    return compact



def _compact_strategy_leaderboard_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    compact = dict(entry or {})
    compact["last_results"] = _compact_strategy_last_results(entry.get("last_results"))
    return compact



def _dedupe_strategy_leaderboard_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from backtesting.strategy_lab import AUTO_STRATEGY_NAME_PREFIX, strategy_definition_signature

    deduped: List[Dict[str, Any]] = []
    seen_signatures: set[str] = set()
    for entry in entries:
        metadata = entry.get("metadata") if isinstance(entry, dict) else {}
        metadata = metadata if isinstance(metadata, dict) else {}
        last_results = entry.get("last_results") if isinstance(entry, dict) else {}
        last_results = last_results if isinstance(last_results, dict) else {}
        definition = entry.get("definition") if isinstance(entry, dict) else {}
        definition = definition if isinstance(definition, dict) else {}
        definition_params = definition.get("params") if isinstance(definition.get("params"), dict) else {}
        name = str((entry or {}).get("name") or "").strip()
        model_name = str(definition_params.get("model_name") or metadata.get("model_name") or "")
        is_auto = bool(metadata.get("source") == "auto_leaderboard") or name.startswith(AUTO_STRATEGY_NAME_PREFIX)
        if is_auto:
            signature = json.dumps({
                "scope": "auto-result",
                "type": definition.get("type"),
                "roi": round(float(last_results.get("roi") or 0.0), 4),
                "win_rate": round(float(last_results.get("win_rate") or 0.0), 4),
                "total_trades": int(last_results.get("total_trades") or 0),
                "profit_factor": round(float(last_results.get("profit_factor") or 0.0), 4),
                "max_drawdown": round(float(last_results.get("max_drawdown") or 0.0), 4),
            }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        else:
            if definition:
                signature = strategy_definition_signature(definition)
            else:
                signature = f"name::{name}"
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        deduped.append(entry)
    return deduped


@lru_cache(maxsize=4)
def _load_strategy_data_cached(db_mtime_ns: int):
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(
            """
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
            """
        ).fetchall()
    finally:
        conn.close()



def _load_strategy_data() -> List[Any]:
    try:
        db_mtime_ns = Path(DB_PATH).stat().st_mtime_ns
    except FileNotFoundError:
        db_mtime_ns = 0
    return list(_load_strategy_data_cached(db_mtime_ns))



def _parse_backtest_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("T", " ").replace("Z", "")
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


@router.get("/senses")
async def api_senses() -> Dict[str, Any]:
    engine = get_engine()
    scores = engine.calculate_all_scores()
    full_data = engine.get_latest_full_data()
    raw = full_data.get("raw", {}) if isinstance(full_data, dict) else {}
    return {
        "senses": scores,
        "scores": scores,
        "raw": raw,
        "recommendation": engine.generate_advice(scores),
    }


@router.get("/senses/config")
async def api_senses_cfg() -> Dict[str, Any]:
    return get_engine().get_config()


@router.put("/senses/config")
async def api_put_senses_cfg(update: "SenseConfigUpdate", request: Request = None) -> Dict[str, Any]:
    _assert_local_operator_request(request)
    engine = get_engine()
    updates: Dict[str, Any] = {}
    if update.enabled is not None:
        updates["enabled"] = update.enabled
    if update.weight is not None:
        updates["weight"] = update.weight
    ok = engine.update_feature_config(update.sense, update.module, updates)
    if not ok:
        raise HTTPException(status_code=400, detail="無效特徵或模組")
    return {"config": engine.get_config(), "scores": engine.calculate_all_scores()}


@router.post("/automation/toggle")
async def api_toggle_automation(payload: Optional[Dict[str, Any]] = Body(default=None), request: Request = None) -> Dict[str, Any]:
    _assert_local_operator_request(request)
    requested_enabled = payload.get("enabled") if isinstance(payload, dict) else None
    previous_state = bool(is_automation_enabled())
    if isinstance(requested_enabled, bool):
        new_state = requested_enabled
    else:
        new_state = not previous_state
    set_automation_enabled(new_state)
    changed = new_state != previous_state
    if changed:
        message = f"已切換至{'自動' if new_state else '手動'}模式"
    else:
        message = f"目前已是{'自動' if new_state else '手動'}模式"
    return {
        "automation": new_state,
        "changed": changed,
        "message": message,
    }


@router.get("/model/stats")
async def api_model_stats() -> Dict[str, Any]:
    import os
    import pickle

    stats: Dict[str, Any] = {
        "model_loaded": False,
        "sample_count": 0,
        "label_distribution": {},
        "feature_importance": {},
        "ic_values": {},
        "model_params": {},
        "feature_count": 0,
        "signal_4h": None,
    }
    try:
        from model.predictor import MODEL_PATH, BASE_FEATURE_COLS as PREDICTOR_FEATURES
        stats["feature_count"] = len(PREDICTOR_FEATURES)
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as handle:
                model = pickle.load(handle)
            stats["model_loaded"] = True
            if hasattr(model, "feature_importances_"):
                pairs = zip(PREDICTOR_FEATURES, getattr(model, "feature_importances_", []) or [])
                stats["feature_importance"] = {str(k): round(float(v), 4) for k, v in pairs}
            if hasattr(model, "get_params"):
                params = model.get_params()
                stats["model_params"] = {k: params.get(k) for k in ["n_estimators", "max_depth", "reg_alpha", "reg_lambda"]}
    except Exception as exc:
        logger.warning("api_model_stats 模型讀取失敗: %s", exc)
    try:
        from database.models import Labels
        db = get_db()
        stats["sample_count"] = int(db.query(Labels).count())
    except Exception as exc:
        logger.warning("api_model_stats 樣本統計失敗: %s", exc)
    return stats


@router.get("/chart/klines")
async def api_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 500,
    since: Optional[int] = Query(default=None),
    until: Optional[int] = Query(default=None),
    append_after: Optional[int] = Query(default=None),
) -> Dict[str, Any]:
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
        requested_limit = max(int(limit or 0), 1)
        fetch_since = since
        trim_after_time = append_after
        if append_after is not None:
            warmup_window_ms = interval_ms * _KLINE_INCREMENTAL_WARMUP_CANDLES
            warmup_since = max(0, append_after - warmup_window_ms)
            fetch_since = max(since or 0, warmup_since) if since is not None else warmup_since

        exchange = ccxt.binance()
        ohlcv: List[List[float]] = []
        current_since = fetch_since
        while True:
            if until is not None:
                remaining_by_limit = max(requested_limit - len(ohlcv), 0)
                remaining_by_time = None
                if current_since is not None:
                    remaining_by_time = max(int(math.ceil((until - current_since) / interval_ms)) + 1, 0)
                target_remaining = max(remaining_by_limit, remaining_by_time or 0)
                page_limit = max(min(target_remaining or requested_limit, 1000), 50)
            else:
                remaining = max(requested_limit - len(ohlcv), 1)
                page_limit = max(min(remaining, 1000), 50)

            page = exchange.fetch_ohlcv(symbol, interval, since=current_since, limit=page_limit)
            if not page:
                break
            if until is not None:
                page = [row for row in page if row[0] <= until]
            if ohlcv:
                last_ts = ohlcv[-1][0]
                page = [row for row in page if row[0] > last_ts]
            if not page:
                break
            ohlcv.extend(page)

            last_ts = ohlcv[-1][0]
            if until is not None and last_ts >= until:
                break
            if until is None and len(ohlcv) >= requested_limit:
                break
            if len(page) < page_limit:
                break

            next_since = last_ts + interval_ms
            if current_since is not None and next_since <= current_since:
                break
            current_since = next_since

        if until is None and requested_limit:
            ohlcv = ohlcv[:requested_limit]

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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/strategies/leaderboard")
async def api_strategy_leaderboard() -> Dict[str, Any]:
    """回傳策略排行榜；顯示所有非系統產生的策略，並保留 system-generated 列供比較。"""
    from backtesting.strategy_lab import load_all_strategies

    _ensure_auto_generated_strategy_leaderboard()
    db = get_db()
    try:
        loaded = load_all_strategies(include_internal=True)
        strategies = [_decorate_strategy_entry(entry, db=db) for entry in loaded]
    finally:
        if hasattr(db, "close"):
            db.close()

    visible = [entry for entry in strategies if not bool(entry.get("is_internal"))]
    auto_rows = [entry for entry in strategies if bool((entry.get("metadata") or {}).get("source") == "auto_leaderboard")]
    strategies = visible + [entry for entry in auto_rows if entry not in visible]
    if not strategies:
        strategies = visible or strategies

    strategies.sort(key=_strategy_leaderboard_sort_key, reverse=True)
    strategies = _dedupe_strategy_leaderboard_entries(strategies)
    compact_strategies = [_compact_strategy_leaderboard_entry(entry) for entry in strategies]
    snapshot_history = _load_recent_strategy_leaderboard_snapshots(limit=12, db_path=DB_PATH)
    rank_deltas = _compute_strategy_rank_deltas_against_latest_snapshot(compact_strategies, db_path=DB_PATH)
    compact_strategies = [
        {
            **entry,
            "rank_delta": rank_deltas.get(str(entry.get("name")), 0),
            "last_results": {
                **(entry.get("last_results") or {}),
                "rank_delta": rank_deltas.get(str(entry.get("name")), 0),
            },
        }
        for entry in compact_strategies
    ]
    quadrant_points = [
        {
            "strategy_name": entry.get("name"),
            "x": ((entry.get("last_results") or {}).get("reliability_score")),
            "y": ((entry.get("last_results") or {}).get("return_power_score")),
            "overall_score": ((entry.get("last_results") or {}).get("overall_score")),
            "risk_control_score": ((entry.get("last_results") or {}).get("risk_control_score")),
            "capital_efficiency_score": ((entry.get("last_results") or {}).get("capital_efficiency_score")),
            "rank_delta": entry.get("rank_delta", 0),
        }
        for entry in compact_strategies
    ]
    return {
        "strategies": compact_strategies,
        "count": len(compact_strategies),
        "quadrant_points": quadrant_points,
        "snapshot_history": snapshot_history,
        "score_dimensions": [
            {"key": "overall_score", "label": "Overall", "description": "綜合能力分數：可靠性 + 收益力 + 風控 + 資金效率"},
            {"key": "reliability_score", "label": "Reliability", "description": "低回撤、低深套、樣本充分、低過擬合風險"},
            {"key": "return_power_score", "label": "Return Power", "description": "ROI 與 PF 主導，勝率僅作輔助參考"},
            {"key": "risk_control_score", "label": "Risk Control", "description": "最大回撤、深套時間與穩定度"},
            {"key": "capital_efficiency_score", "label": "Capital Efficiency", "description": "decision quality、PF、深套時間與可部署層數"},
        ],
        **_strategy_decision_contract_meta(),
        "sort_semantics": STRATEGY_LB_SORT_SEMANTICS_V2,
    }


@router.get("/strategies/{name}")
async def api_get_strategy(name: str) -> Dict[str, Any]:
    from backtesting.strategy_lab import load_strategy

    strategy = load_strategy(name)
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")

    db = get_db()
    try:
        return _prepare_strategy_detail_entry(_decorate_strategy_entry(strategy, db=db))
    finally:
        if hasattr(db, "close"):
            db.close()


@router.get("/strategy_data_range")
async def api_strategy_data_range() -> Dict[str, Any]:
    return _strategy_data_range_summary(_load_strategy_data())


_NO_DEPLOY_RUNTIME_CLOSURE_STATES = {
    "circuit_breaker_active",
    "decision_quality_below_trade_floor",
    "patch_active_but_execution_blocked",
    "support_closed_but_trade_floor_blocked",
    "unsupported_exact_live_structure_bucket",
    "under_minimum_exact_live_structure_bucket",
    "exact_bucket_unsupported_block",
    "exact_live_lane_toxic_sub_bucket_current_bucket",
    "exact_live_lane_toxic_allow_lane",
}


def _current_live_buy_reject_payload(live_runtime_truth: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a structured reject payload when current-live truth forbids adding exposure."""
    payload = live_runtime_truth if isinstance(live_runtime_truth, dict) else {}
    deployment_blocker = payload.get("deployment_blocker")
    runtime_closure_state = payload.get("runtime_closure_state")
    signal = str(payload.get("signal") or "").upper()
    allowed_layers = payload.get("allowed_layers")
    allowed_layers_reason = payload.get("allowed_layers_reason")
    deployment_blocker_reason = payload.get("deployment_blocker_reason")
    execution_guardrail_reason = payload.get("execution_guardrail_reason")
    blocker_reason = (
        deployment_blocker_reason
        or execution_guardrail_reason
        or allowed_layers_reason
        or runtime_closure_state
        or deployment_blocker
        or "目前即時風控阻止買入 / 加倉訂單"
    )

    try:
        numeric_allowed_layers = int(allowed_layers) if allowed_layers is not None else None
    except (TypeError, ValueError):
        numeric_allowed_layers = None

    should_reject = bool(deployment_blocker) or signal == "CIRCUIT_BREAKER"
    should_reject = should_reject or runtime_closure_state in _NO_DEPLOY_RUNTIME_CLOSURE_STATES
    should_reject = should_reject or (numeric_allowed_layers is not None and numeric_allowed_layers <= 0 and bool(allowed_layers_reason))
    if not should_reject:
        return None

    blocker_details = payload.get("deployment_blocker_details") if isinstance(payload.get("deployment_blocker_details"), dict) else {}
    return {
        "success": False,
        "trade_blocked": True,
        "blocked_side": "buy",
        "reason": "manual_buy_blocked_by_current_live_blocker",
        "runtime_blocker": deployment_blocker or runtime_closure_state or execution_guardrail_reason or allowed_layers_reason,
        "allowed_actions": ["reduce", "diagnostics", "mode_toggle"],
        "code": "current_live_deployment_blocker",
        "message": "目前即時部署阻塞啟用：買入 / 加倉已暫停；減倉 / 賣出風險降低路徑仍允許。",
        "context": {
            "blocked_side": "buy",
            "allowed_sides": ["reduce", "sell"],
            "reduce_only_allowed": True,
            "deployment_blocker": deployment_blocker,
            "deployment_blocker_reason": deployment_blocker_reason,
            "runtime_closure_state": runtime_closure_state,
            "runtime_closure_summary": payload.get("runtime_closure_summary"),
            "execution_guardrail_reason": execution_guardrail_reason,
            "signal": payload.get("signal"),
            "allowed_layers": allowed_layers,
            "allowed_layers_reason": allowed_layers_reason,
            "current_live_structure_bucket": payload.get("current_live_structure_bucket"),
            "current_live_structure_bucket_rows": payload.get("current_live_structure_bucket_rows"),
            "minimum_support_rows": payload.get("minimum_support_rows"),
            "support_route_verdict": payload.get("support_route_verdict"),
            "release_condition": blocker_details.get("release_condition"),
            "operator_action": "前往 /execution/status，確認熔斷解除條件與即時部署阻塞點已解除後，再重試買入 / 加倉。",
            "reason": blocker_reason,
        },
    }


def _current_live_trade_blocker(live_runtime_truth: Dict[str, Any], side: str) -> Optional[Dict[str, Any]]:
    """Return a structured blocker only for add-exposure trade sides."""
    normalized_side = str(side or "").lower().strip()
    if normalized_side in {"reduce", "sell"}:
        return None
    return _current_live_buy_reject_payload(live_runtime_truth)


async def _load_current_live_buy_reject_payload() -> Optional[Dict[str, Any]]:
    try:
        maybe_confidence_payload = get_confidence_prediction()
        confidence_payload = await maybe_confidence_payload if hasattr(maybe_confidence_payload, "__await__") else maybe_confidence_payload
        live_runtime_truth = _build_live_runtime_closure_surface(confidence_payload)
    except Exception as exc:
        return {
            "success": False,
            "trade_blocked": True,
            "blocked_side": "buy",
            "reason": "manual_buy_blocked_by_current_live_guardrail_unavailable",
            "runtime_blocker": "current_live_guardrail_unavailable",
            "allowed_actions": ["reduce", "diagnostics", "mode_toggle"],
            "code": "current_live_guardrail_unavailable",
            "message": "目前即時風控無法取得：買入 / 加倉以失敗關閉暫停；減倉 / 賣出風險降低路徑仍允許。",
            "context": {
                "blocked_side": "buy",
                "allowed_sides": ["reduce", "sell"],
                "reduce_only_allowed": True,
                "error": str(exc),
                "operator_action": "重新整理 /execution/status 並恢復 /predict/confidence 後，再重試買入 / 加倉。",
            },
        }
    return _current_live_trade_blocker(live_runtime_truth, "buy")


@router.post("/trade")
async def api_trade(req: "TradeRequest", request: Request = None) -> Dict[str, Any]:
    _assert_local_operator_request(request)
    side = (req.side or "").lower().strip()
    if side not in {"buy", "reduce", "sell"}:
        raise HTTPException(status_code=400, detail="side must be one of: buy, reduce, sell")

    submit_side = "buy" if side == "buy" else "sell"
    reduce_only = side in {"reduce", "sell"}
    if not reduce_only:
        buy_reject = await _load_current_live_buy_reject_payload()
        if buy_reject is not None:
            raise HTTPException(status_code=409, detail=buy_reject)

    cfg = get_config() or {}
    db = get_db()
    try:
        service = ExecutionService(cfg, db_session=db)
        try:
            result = service.submit_order(
                side=submit_side,
                symbol=req.symbol,
                qty=req.qty,
                order_type="market",
                reduce_only=reduce_only,
            )
        except ExecutionRejectError as exc:
            raise HTTPException(status_code=409, detail=exc.to_payload()) from exc
    finally:
        if hasattr(db, "close"):
            db.close()

    order = result.get("order") if isinstance(result, dict) else {}
    order = order if isinstance(order, dict) else {}
    return {
        **(result if isinstance(result, dict) else {}),
        "order_id": order.get("id") or order.get("order_id"),
        "venue": (result.get("venue") if isinstance(result, dict) else None) or ((cfg.get("execution") or {}).get("venue")) or ((cfg.get("trading") or {}).get("venue")),
        "guardrails": (result.get("guardrails") if isinstance(result, dict) else None) or {},
        "order": order,
    }


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
    # Sparse-source features below use transformed feature-space ranges (tanh / centered)
    # rather than raw upstream ratios, so API history charts retain separation instead of
    # hard-clipping everything to the 0.02 floor.
    'feat_claw': (-0.91, 0.70), 'feat_claw_intensity': (0.02, 0.96),
    'feat_fang_pcr': (-0.563, -0.531), 'feat_fang_skew': (-0.00001, 0.00001),
    'feat_fin_netflow': (-1.0, 1.0), 'feat_web_whale': (0.0, 1.0),
    'feat_scales_ssr': (-0.137, -0.134), 'feat_nest_pred': (0.005, 0.0115),
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
    return float(ecdf_normalize(float(raw_val), float(p5), float(p95)))
