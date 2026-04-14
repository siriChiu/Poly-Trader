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

from server.dependencies import get_db, get_config, is_automation_enabled, set_automation_enabled
from server.features_engine import get_engine
from database.models import TradeHistory, RawEvent, RawMarketData, FeaturesNormalized
from feature_engine.feature_history_policy import (
    FEATURE_KEY_MAP,
    assess_feature_quality,
    attach_forward_archive_meta,
    compute_raw_snapshot_stats,
    _compute_archive_window_coverage,
)
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
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
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
    return {
        "automation": is_automation_enabled(),
        "dry_run": cfg.get("trading", {}).get("dry_run", True),
        "symbol": cfg.get("trading", {}).get("symbol", "BTCUSDT"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


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
        ohlcv = exchange.fetch_ohlcv(symbol, interval, since=fetch_since, limit=fetch_limit)
        if until is not None:
            ohlcv = [row for row in ohlcv if row[0] <= until]
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
    """Dry-run trade endpoint for the web UI.

    The web app is spot-first, so allow buy / reduce / sell(close-only) but do not imply shorting.
    """
    side = (req.side or "").lower().strip()
    if side not in {"buy", "reduce", "sell"}:
        raise HTTPException(status_code=400, detail="side must be one of: buy, reduce, sell")

    cfg = get_config()
    dry_run = cfg.get("trading", {}).get("dry_run", True)
    action_text = {
        "buy": "spot buy",
        "reduce": "position reduce",
        "sell": "position close",
    }[side]
    return {
        "success": True,
        "dry_run": dry_run,
        "message": f"{action_text} accepted",
        "order": {
            "side": side,
            "symbol": req.symbol,
            "qty": req.qty,
            "mode": "dry_run" if dry_run else "live",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
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
        obj = {"timestamp": r.timestamp.isoformat() if r.timestamp else None}
        for db_key, clean_key in FEATURE_KEY_MAP.items():
            raw_val = getattr(r, db_key, None)
            obj[clean_key] = normalize_for_api(raw_val, db_key)
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
    return result


# ═══════════════════════════════════════════════
# Strategy Lab API
# ═══════════════════════════════════════════════

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
MODEL_LB_CACHE_PATH = Path('/tmp/polytrader_model_leaderboard_cache.json')
MODEL_LB_CACHE_TTL_SEC = 60 * 15
MODEL_LB_STALE_SEC = 60 * 60 * 6
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
               f.feat_4h_bb_pct_b, f.feat_4h_dist_bb_lower, f.feat_4h_dist_swing_low
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



def _get_sqlite_db_path(db) -> Optional[str]:
    try:
        bind = db.get_bind()
    except Exception:
        return None
    if bind is None:
        return None
    return bind.url.database or None



STRATEGY_DECISION_TARGET_COL = "simulated_pyramid_win"
STRATEGY_DECISION_TARGET_LABEL = "Canonical Decision Quality"
STRATEGY_DECISION_SORT_SEMANTICS = "ROI -> lower max_drawdown -> avg_decision_quality_score -> profit_factor (win_rate reference only)"


def _strategy_decision_contract_meta(horizon_minutes: int = 1440) -> Dict[str, Any]:
    return {
        "target_col": STRATEGY_DECISION_TARGET_COL,
        "target_label": STRATEGY_DECISION_TARGET_LABEL,
        "sort_semantics": STRATEGY_DECISION_SORT_SEMANTICS,
        "decision_quality_horizon_minutes": horizon_minutes,
    }


def _empty_strategy_quality_profile(horizon_minutes: int = 1440) -> Dict[str, Any]:
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



def _compute_strategy_decision_quality_profile(
    trades: List[Dict[str, Any]],
    db=None,
    db_path: Optional[str] = None,
    horizon_minutes: int = 1440,
) -> Dict[str, Any]:
    profile = _empty_strategy_quality_profile(horizon_minutes=horizon_minutes)
    if not trades:
        return profile

    db_path = db_path or (_get_sqlite_db_path(db) if db is not None else None)
    if not db_path:
        return profile

    timestamp_keys = []
    for trade in trades:
        ts_key = _normalize_timestamp_key(trade.get("entry_timestamp") or trade.get("timestamp"))
        if ts_key:
            timestamp_keys.append(ts_key)
    timestamp_keys = sorted(set(timestamp_keys))
    if not timestamp_keys:
        return profile

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

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(query, [horizon_minutes, *timestamp_keys]).fetchall()
        finally:
            conn.close()
    except Exception:
        return profile

    if not rows:
        return profile

    def _avg(col: str) -> Optional[float]:
        vals = [float(r[col]) for r in rows if r[col] is not None]
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



def _compute_decision_profile(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not trades:
        return {
            "avg_entry_quality": None,
            "avg_allowed_layers": None,
            "dominant_regime_gate": None,
            "regime_gate_summary": {"ALLOW": 0, "CAUTION": 0, "BLOCK": 0},
        }

    quality_values = [float(t.get("entry_quality")) for t in trades if t.get("entry_quality") is not None]
    allowed_layers = [float(t.get("allowed_layers")) for t in trades if t.get("allowed_layers") is not None]
    gate_summary = {"ALLOW": 0, "CAUTION": 0, "BLOCK": 0}
    for trade in trades:
        gate = str(trade.get("regime_gate") or "ALLOW").upper()
        if gate not in gate_summary:
            gate_summary[gate] = 0
        gate_summary[gate] += 1

    dominant_gate = max(gate_summary.items(), key=lambda item: item[1])[0] if gate_summary else None
    return {
        "avg_entry_quality": round(sum(quality_values) / len(quality_values), 4) if quality_values else None,
        "avg_allowed_layers": round(sum(allowed_layers) / len(allowed_layers), 2) if allowed_layers else None,
        "dominant_regime_gate": dominant_gate,
        "regime_gate_summary": gate_summary,
    }


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
        logger.warning(f"Failed to load strategy leaderboard snapshots: {exc}")
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
        logger.warning(f"Failed to compute strategy rank deltas: {exc}")
        return {}
    latest_map = {str(name): int(rank) for name, rank in latest_rows}
    previous_map = {str(name): int(rank) for name, rank in previous_rows}
    return {name: int(previous_map[name] - rank) for name, rank in latest_map.items() if name in previous_map}



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
        logger.warning(f"Failed to persist strategy leaderboard snapshot: {exc}")



def _decorate_strategy_entry(entry: Dict[str, Any], db=None) -> Dict[str, Any]:
    enriched = dict(entry)
    last_results = dict(entry.get("last_results") or {})
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
    scorecard = _compute_strategy_scorecard(last_results, risk)
    last_results.update({k: v for k, v in scorecard.items() if k != "rank_delta"})
    last_results["sort_semantics"] = STRATEGY_LB_SORT_SEMANTICS_V2
    last_results = _normalize_result_timestamps(last_results)
    enriched["last_results"] = last_results or None
    enriched["decision_contract"] = {
        **_strategy_decision_contract_meta(horizon_minutes=contract_horizon),
        "sort_semantics": STRATEGY_LB_SORT_SEMANTICS_V2,
    }
    enriched.update(risk)
    enriched.update(scorecard)
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


def _load_model_leaderboard_cache_file() -> None:
    if not MODEL_LB_CACHE_PATH.exists():
        return
    try:
        cached = json.loads(MODEL_LB_CACHE_PATH.read_text(encoding='utf-8'))
        with _MODEL_LB_LOCK:
            if cached.get("payload"):
                _MODEL_LB_CACHE["payload"] = cached["payload"]
                _MODEL_LB_CACHE["updated_at"] = float(cached.get("updated_at") or 0.0)
                _MODEL_LB_CACHE["error"] = cached.get("error")
    except Exception as exc:
        logger.warning(f"Failed to load model leaderboard cache: {exc}")


def _write_model_leaderboard_cache_file(payload: Dict[str, Any], updated_at: float, error: Optional[str] = None) -> None:
    try:
        MODEL_LB_CACHE_PATH.write_text(
            json.dumps({"payload": payload, "updated_at": updated_at, "error": error}, ensure_ascii=False),
            encoding='utf-8',
        )
    except Exception as exc:
        logger.warning(f"Failed to write model leaderboard cache: {exc}")


def _ensure_model_leaderboard_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leaderboard_model_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at REAL NOT NULL,
            target_col TEXT,
            model_count INTEGER NOT NULL DEFAULT 0,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leaderboard_model_scorecards (
            snapshot_id INTEGER NOT NULL,
            rank INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            overall_score REAL,
            reliability_score REAL,
            return_power_score REAL,
            risk_control_score REAL,
            capital_efficiency_score REAL,
            avg_roi REAL,
            avg_max_dd REAL,
            avg_expected_time_underwater REAL,
            profit_factor REAL,
            avg_trades REAL,
            overfit_penalty REAL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (snapshot_id, rank)
        )
        """
    )



def _persist_model_leaderboard_snapshot(payload: Dict[str, Any], updated_at: float, db_path: str = DB_PATH) -> None:
    try:
        conn = sqlite3.connect(db_path)
        try:
            _ensure_model_leaderboard_tables(conn)
            created_at = datetime.utcfromtimestamp(updated_at).isoformat() + "Z"
            cursor = conn.execute(
                "INSERT INTO leaderboard_model_snapshots(created_at, updated_at, target_col, model_count, payload_json) VALUES (?, ?, ?, ?, ?)",
                (
                    created_at,
                    float(updated_at),
                    payload.get("target_col"),
                    int(len(payload.get("leaderboard") or [])),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            snapshot_id = int(cursor.lastrowid)
            for rank, row in enumerate(payload.get("leaderboard") or [], start=1):
                conn.execute(
                    """
                    INSERT INTO leaderboard_model_scorecards(
                        snapshot_id, rank, model_name, overall_score, reliability_score, return_power_score,
                        risk_control_score, capital_efficiency_score, avg_roi, avg_max_dd,
                        avg_expected_time_underwater, profit_factor, avg_trades, overfit_penalty, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        rank,
                        row.get("model_name"),
                        row.get("overall_score"),
                        row.get("reliability_score"),
                        row.get("return_power_score"),
                        row.get("risk_control_score"),
                        row.get("capital_efficiency_score"),
                        row.get("avg_roi"),
                        row.get("avg_max_dd"),
                        row.get("avg_expected_time_underwater"),
                        row.get("profit_factor"),
                        row.get("avg_trades"),
                        row.get("overfit_penalty"),
                        json.dumps(row, ensure_ascii=False),
                    ),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning(f"Failed to persist model leaderboard snapshot: {exc}")


def _load_recent_model_leaderboard_snapshots(limit: int = 12, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    try:
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
    except Exception as exc:
        logger.warning(f"Failed to load model leaderboard snapshots: {exc}")
        return []



def _compute_model_rank_deltas(rows: List[Dict[str, Any]], db_path: str = DB_PATH) -> Dict[str, int]:
    if len(rows) < 2:
        return {}
    latest_snapshot_id = rows[0].get("id")
    previous_snapshot_id = rows[1].get("id")
    try:
        conn = sqlite3.connect(db_path)
        try:
            latest_rows = conn.execute(
                "SELECT model_name, rank FROM leaderboard_model_scorecards WHERE snapshot_id=?",
                (latest_snapshot_id,),
            ).fetchall()
            previous_rows = conn.execute(
                "SELECT model_name, rank FROM leaderboard_model_scorecards WHERE snapshot_id=?",
                (previous_snapshot_id,),
            ).fetchall()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning(f"Failed to compute model rank deltas: {exc}")
        return {}
    latest_map = {str(model_name): int(rank) for model_name, rank in latest_rows}
    previous_map = {str(model_name): int(rank) for model_name, rank in previous_rows}
    deltas: Dict[str, int] = {}
    for model_name, latest_rank in latest_map.items():
        prev_rank = previous_map.get(model_name)
        if prev_rank is None:
            continue
        deltas[model_name] = int(prev_rank - latest_rank)
    return deltas



def _build_model_leaderboard_payload() -> Dict[str, Any]:
    from backtesting.model_leaderboard import ModelLeaderboard

    df = load_model_leaderboard_frame(DB_PATH)
    if df.empty:
        return {"leaderboard": [], "count": 0, "warning": "No aligned 24h label rows found"}

    default_target_col = "simulated_pyramid_win" if "simulated_pyramid_win" in df.columns else "label_spot_long_win"
    df = df.fillna(0)
    if default_target_col in df.columns:
        df[default_target_col] = df[default_target_col].fillna(0).astype(int)

    lb = ModelLeaderboard(df, target_col=default_target_col)
    requested_models = [
        "rule_baseline", "logistic_regression", "xgboost",
        "lightgbm", "catboost", "random_forest", "mlp", "svm"
    ]
    results = lb.run_all_models(requested_models)

    OVERFIT_GAP_THRESHOLD = 0.12
    HARD_TRAIN_ACC_CAP = 0.90

    leaderboard = _serialize_model_scores(results, OVERFIT_GAP_THRESHOLD, HARD_TRAIN_ACC_CAP)
    target_comparison = _summarize_target_candidates(df, OVERFIT_GAP_THRESHOLD, HARD_TRAIN_ACC_CAP)
    skipped_models = [
        {"model_name": model_name, **status}
        for model_name, status in (lb.last_model_statuses or {}).items()
        if status.get("status") != "ok"
    ]

    metrics_path = Path(__file__).resolve().parents[2] / "model" / "last_metrics.json"
    regime_stats_path = Path(__file__).resolve().parents[2] / "model" / "regime_stats.json"
    global_metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else None
    regime_metrics = json.loads(regime_stats_path.read_text(encoding="utf-8")) if regime_stats_path.exists() else None

    snapshot_history = _load_recent_model_leaderboard_snapshots(limit=12, db_path=DB_PATH)
    rank_deltas = _compute_model_rank_deltas(snapshot_history, db_path=DB_PATH)
    leaderboard = [
        {
            **row,
            "rank_delta": rank_deltas.get(str(row.get("model_name")), 0),
            "selected_deployment_profile": (lb.last_model_statuses.get(str(row.get("model_name")), {}) or {}).get("selected_deployment_profile", row.get("deployment_profile")),
            "deployment_profiles_evaluated": (lb.last_model_statuses.get(str(row.get("model_name")), {}) or {}).get("deployment_profiles_evaluated", [row.get("deployment_profile")]),
            "selected_feature_profile": (lb.last_model_statuses.get(str(row.get("model_name")), {}) or {}).get("selected_feature_profile", row.get("feature_profile")),
            "selected_feature_profile_source": (lb.last_model_statuses.get(str(row.get("model_name")), {}) or {}).get("selected_feature_profile_source", row.get("feature_profile_source")),
            "feature_profiles_evaluated": (lb.last_model_statuses.get(str(row.get("model_name")), {}) or {}).get("feature_profiles_evaluated", [row.get("feature_profile")]),
            "feature_profile_support_cohort": (lb.last_model_statuses.get(str(row.get("model_name")), {}) or {}).get("feature_profile_support_cohort", row.get("feature_profile_support_cohort")),
            "feature_profile_support_rows": (lb.last_model_statuses.get(str(row.get("model_name")), {}) or {}).get("feature_profile_support_rows", row.get("feature_profile_support_rows")),
            "feature_profile_exact_live_bucket_rows": (lb.last_model_statuses.get(str(row.get("model_name")), {}) or {}).get("feature_profile_exact_live_bucket_rows", row.get("feature_profile_exact_live_bucket_rows")),
        }
        for row in leaderboard
    ]
    quadrant_points = [
        {
            "model_name": row.get("model_name"),
            "x": row.get("reliability_score"),
            "y": row.get("return_power_score"),
            "overall_score": row.get("overall_score"),
            "risk_control_score": row.get("risk_control_score"),
            "capital_efficiency_score": row.get("capital_efficiency_score"),
            "avg_roi": row.get("avg_roi"),
            "avg_max_dd": row.get("avg_max_dd"),
            "rank_delta": row.get("rank_delta"),
        }
        for row in leaderboard
    ]

    return {
        "leaderboard": leaderboard,
        "count": len(leaderboard),
        "overfit_gap_threshold": OVERFIT_GAP_THRESHOLD,
        "hard_train_acc_cap": HARD_TRAIN_ACC_CAP,
        "target_col": default_target_col,
        "target_label": "Simulated Pyramid" if default_target_col == "simulated_pyramid_win" else "Path-aware TP/DD",
        "target_comparison": target_comparison,
        "quadrant_points": quadrant_points,
        "score_dimensions": [
            {"key": "overall_score", "label": "Overall", "description": "綜合能力分數：可靠性 + 收益力 + 風控 + 資金效率"},
            {"key": "reliability_score", "label": "Reliability", "description": "低回撤、低深套、樣本充分、低過擬合風險"},
            {"key": "return_power_score", "label": "Return Power", "description": "ROI 與 PF 主導，勝率僅作輔助參考"},
            {"key": "risk_control_score", "label": "Risk Control", "description": "最大回撤、深套時間、波動與過擬合抑制"},
            {"key": "capital_efficiency_score", "label": "Capital Efficiency", "description": "decision quality、PF、深套時間與可部署層數"},
        ],
        "storage": {
            "canonical_store": "sqlite:leaderboard_model_snapshots + leaderboard_model_scorecards",
            "cache_store": str(MODEL_LB_CACHE_PATH),
        },
        "snapshot_history": [
            {
                "id": row.get("id"),
                "created_at": row.get("created_at"),
                "target_col": row.get("target_col"),
                "model_count": row.get("model_count"),
            }
            for row in snapshot_history
        ],
        "skipped_models": skipped_models,
        "global_metrics": global_metrics,
        "regime_metrics": regime_metrics,
    }


def _refresh_model_leaderboard_cache() -> None:
    with _MODEL_LB_LOCK:
        if _MODEL_LB_CACHE.get("refreshing"):
            return
        _MODEL_LB_CACHE["refreshing"] = True
        _MODEL_LB_CACHE["error"] = None
    try:
        payload = _build_model_leaderboard_payload()
        updated_at = time.time()
        with _MODEL_LB_LOCK:
            _MODEL_LB_CACHE["payload"] = payload
            _MODEL_LB_CACHE["updated_at"] = updated_at
            _MODEL_LB_CACHE["error"] = None
            _MODEL_LB_CACHE["refreshing"] = False
        _write_model_leaderboard_cache_file(payload, updated_at)
        _persist_model_leaderboard_snapshot(payload, updated_at, DB_PATH)
    except Exception as exc:
        with _MODEL_LB_LOCK:
            _MODEL_LB_CACHE["error"] = str(exc)
            _MODEL_LB_CACHE["refreshing"] = False
        _write_model_leaderboard_cache_file(_MODEL_LB_CACHE.get("payload") or {}, _MODEL_LB_CACHE.get("updated_at") or 0.0, str(exc))
        logger.exception("Model leaderboard refresh failed")


def _ensure_model_leaderboard_refresh(force: bool = False) -> None:
    with _MODEL_LB_LOCK:
        payload = _MODEL_LB_CACHE.get("payload")
        updated_at = float(_MODEL_LB_CACHE.get("updated_at") or 0.0)
        refreshing = bool(_MODEL_LB_CACHE.get("refreshing"))
    if refreshing:
        return
    age = time.time() - updated_at if updated_at else float('inf')
    if force or payload is None or age > MODEL_LB_CACHE_TTL_SEC:
        threading.Thread(target=_refresh_model_leaderboard_cache, daemon=True).start()


@router.get("/strategies/leaderboard/history")
async def api_strategy_leaderboard_history(limit: int = Query(default=12, ge=1, le=100)):
    rows = _load_recent_strategy_leaderboard_snapshots(limit=limit, db_path=DB_PATH)
    return {
        "history": rows,
        "count": len(rows),
    }


@router.get("/strategies/leaderboard")
async def api_strategy_leaderboard():
    """回傳所有已儲存策略的 Leaderboard（依 canonical decision-quality semantics 排序）"""
    from backtesting.strategy_lab import load_all_strategies

    db = get_db()
    try:
        strategies = [_decorate_strategy_entry(s, db=db) for s in load_all_strategies()]
    finally:
        db.close()
    strategies.sort(key=_strategy_leaderboard_sort_key, reverse=True)
    snapshot_history = _load_recent_strategy_leaderboard_snapshots(limit=12, db_path=DB_PATH)
    rank_deltas = _compute_strategy_rank_deltas(snapshot_history, db_path=DB_PATH)
    strategies = [
        {
            **entry,
            "rank_delta": rank_deltas.get(str(entry.get("name")), 0),
            "last_results": {
                **(entry.get("last_results") or {}),
                "rank_delta": rank_deltas.get(str(entry.get("name")), 0),
            },
        }
        for entry in strategies
    ]
    _persist_strategy_leaderboard_snapshot(strategies, db_path=DB_PATH)
    quadrant_points = [
        {
            "strategy_name": entry.get("name"),
            "x": (entry.get("last_results") or {}).get("reliability_score"),
            "y": (entry.get("last_results") or {}).get("return_power_score"),
            "overall_score": (entry.get("last_results") or {}).get("overall_score"),
            "risk_control_score": (entry.get("last_results") or {}).get("risk_control_score"),
            "capital_efficiency_score": (entry.get("last_results") or {}).get("capital_efficiency_score"),
            "rank_delta": entry.get("rank_delta", 0),
        }
        for entry in strategies
    ]
    return {
        "strategies": strategies,
        "count": len(strategies),
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
async def api_get_strategy(name: str):
    """取得單一策略定義"""
    from backtesting.strategy_lab import load_strategy

    s = load_strategy(name)
    if s is None:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")

    db = get_db()
    try:
        return _decorate_strategy_entry(s, db=db)
    finally:
        db.close()


@router.delete("/strategies/{name}")
async def api_delete_strategy(name: str):
    """刪除策略"""
    from backtesting.strategy_lab import delete_strategy
    ok = delete_strategy(name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    return {"ok": True, "deleted": name}


def _set_strategy_job_progress(job_id: Optional[str], progress: int, detail: str, *, status: str = "running") -> None:
    if not job_id:
        return
    with _STRATEGY_RUN_LOCK:
        job = _STRATEGY_RUN_JOBS.get(job_id)
        if not job:
            return
        job.update({
            "status": status,
            "progress": max(0, min(100, int(progress))),
            "detail": detail,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        })


def _execute_strategy_run(body: Dict[str, Any], *, job_id: Optional[str] = None) -> Dict[str, Any]:
    from backtesting.strategy_lab import run_rule_backtest, run_hybrid_backtest, save_strategy

    name = body.get("name", "unnamed_strategy")
    stype = body.get("type", "rule_based")
    params = body.get("params", {})
    initial = body.get("initial_capital", 10000.0)

    _set_strategy_job_progress(job_id, 5, "正在載入回測資料與特徵欄位。")
    rows = _load_strategy_data()
    if not rows:
        return {"error": "No data available for backtest"}

    timestamps = [str(r[0]) for r in rows]
    prices = [float(r[1]) for r in rows]
    bias50 = [float(r[2]) if r[2] is not None else 0 for r in rows]
    bias200 = [float(r[3]) if r[3] is not None else 0 for r in rows]
    nose = [float(r[4]) if r[4] is not None else 0.5 for r in rows]
    pulse = [float(r[5]) if r[5] is not None else 0.5 for r in rows]
    ear = [float(r[6]) if r[6] is not None else 0 for r in rows]
    regimes = [str(r[7]).lower() if r[7] else "unknown" for r in rows]
    bb_pct_b_4h = [float(r[8]) if r[8] is not None else None for r in rows]
    dist_bb_lower_4h = [float(r[9]) if r[9] is not None else None for r in rows]
    dist_swing_low_4h = [float(r[10]) if r[10] is not None else None for r in rows]
    score_series: List[Dict[str, Any]] = []

    db = get_db()
    try:
        db_path = _get_sqlite_db_path(db)
        if stype == "rule_based":
            _set_strategy_job_progress(job_id, 22, f"已載入 {len(rows)} 筆資料，正在執行 rule-based 回測。")
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
                    prices, timestamps, bias50, bias200, nose, pulse, ear, params, initial,
                    regimes=regimes,
                    bb_pct_b_4h=bb_pct_b_4h,
                    dist_bb_lower_4h=dist_bb_lower_4h,
                    dist_swing_low_4h=dist_swing_low_4h,
                )
                score_series = score_future.result()
        elif stype == "hybrid":
            model_name = str(params.get("model_name") or "xgboost")
            _set_strategy_job_progress(job_id, 24, f"Hybrid 模式：正在準備 {model_name} 訓練資料。")
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
                _set_strategy_job_progress(job_id, 40, f"Hybrid 模式：正在訓練 {model_name}。")
                model = lb._train_model(
                    train_df[feature_cols].fillna(0).values,
                    train_df[target_col].fillna(0).astype(int).values,
                    model_name,
                )
                if model is None:
                    return {"error": f"{model_name} 目前不可用"}
                confidence_map = {
                    str(ts): float(conf)
                    for ts, conf in zip(
                        train_df["timestamp"].dt.strftime('%Y-%m-%d %H:%M:%S').values,
                        lb._get_confidence(model, train_df[feature_cols].fillna(0).values, model_name),
                    )
                }
                with _HYBRID_MODEL_LOCK:
                    _HYBRID_MODEL_CACHE[signature] = {
                        "confidence_map": confidence_map,
                        "updated_at": time.time(),
                    }
            conf = [confidence_map.get(ts, max(0.0, min(1.0, 1.0 - b / 20.0))) for ts, b in zip(timestamps, bias50)]
            _set_strategy_job_progress(job_id, 58, f"Hybrid 模式：{model_name} 已就緒，正在執行回測。")
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
                    prices, timestamps, bias50, bias200, nose, pulse, ear, conf, params, initial,
                    regimes=regimes,
                    bb_pct_b_4h=bb_pct_b_4h,
                    dist_bb_lower_4h=dist_bb_lower_4h,
                    dist_swing_low_4h=dist_swing_low_4h,
                )
                score_series = score_future.result()
        else:
            return {"error": f"Unknown strategy type: {stype}"}

        _set_strategy_job_progress(job_id, 76, "回測核心完成，正在平行計算 benchmark、決策品質摘要與圖表上下文。")
        chart_context = _build_strategy_chart_context(timestamps)
        recent_equity_curve = result.equity_curve[-300:] if result.equity_curve else []
        recent_trades = result.trades[-80:] if result.trades else []
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
            "wins": result.wins, "losses": result.losses,
            "max_drawdown": round(result.max_drawdown, 4),
            "profit_factor": round(result.profit_factor, 4),
            "total_pnl": round(result.total_pnl, 2),
            "avg_win": round(result.avg_win, 2),
            "avg_loss": round(result.avg_loss, 2),
            "max_consecutive_losses": result.max_consecutive_losses,
            "regime_breakdown": _compute_regime_breakdown(result.trades, initial),
            "benchmarks": benchmarks,
            "equity_curve": recent_equity_curve,
            "trades": recent_trades,
            "score_series": score_series[-300:] if score_series else [],
            "chart_context": chart_context,
            "run_at": datetime.utcnow().isoformat() + "Z",
            **decision_profile,
            **canonical_quality_profile,
        }
        contract_meta = _strategy_decision_contract_meta(
            horizon_minutes=int(results_dict.get("decision_quality_horizon_minutes") or 1440)
        )
        for key, value in contract_meta.items():
            results_dict.setdefault(key, value)

        _set_strategy_job_progress(job_id, 92, "正在儲存策略、整理圖表上下文與輸出結果。")
        normalized_results = _normalize_result_timestamps(results_dict)
        save_strategy(name, strat_def, normalized_results)
        response = {
            "strategy": name,
            "type": stype,
            "params": params,
            "results": normalized_results,
            "decision_contract": contract_meta,
            "equity_curve": normalized_results.get("equity_curve") or [],
            "trades": normalized_results.get("trades") or [],
            "score_series": normalized_results.get("score_series") or [],
            "chart_context": _normalize_result_timestamps(chart_context),
        }
        _set_strategy_job_progress(job_id, 100, "回測、圖表與排行榜資料已全部同步完成。", status="completed")
        return response
    finally:
        db.close()


@router.post("/strategies/run")
async def api_run_strategy(body: Dict[str, Any]):
    """同步執行策略回測。"""
    return _execute_strategy_run(body)


@router.post("/strategies/run_async")
async def api_run_strategy_async(body: Dict[str, Any]):
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
        }

    def _runner() -> None:
        _set_strategy_job_progress(job_id, 2, "背景工作已啟動。")
        try:
            result = _execute_strategy_run(body, job_id=job_id)
            with _STRATEGY_RUN_LOCK:
                job = _STRATEGY_RUN_JOBS.get(job_id)
                if job is not None:
                    job["result"] = result
                    job["error"] = result.get("error") if isinstance(result, dict) else None
                    if result.get("error"):
                        job["status"] = "failed"
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

    _STRATEGY_RUN_EXECUTOR.submit(_runner)
    return {"job_id": job_id, "status": "queued", "progress": 0}


@router.get("/strategies/jobs/{job_id}")
async def api_strategy_job_status(job_id: str):
    with _STRATEGY_RUN_LOCK:
        job = _STRATEGY_RUN_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Strategy job '{job_id}' not found")
        return dict(job)


@router.post("/strategies/save")
async def api_save_strategy(body: Dict[str, Any]):
    """儲存策略定義（不跑回測）"""
    from backtesting.strategy_lab import save_strategy
    name = body.get("name", "unnamed")
    stype = body.get("type", "rule_based")
    params = body.get("params", {})
    path = save_strategy(name, {"type": stype, "params": params})
    return {"ok": True, "name": name, "path": path}


# ═══════════════════════════════════════════════
# Model Leaderboard API
# ═══════════════════════════════════════════════
# 9 個模型：Rule Baseline, LogisticRegression, XGBoost, LightGBM,
#           CatBoost, RandomForest, MLP, SVM, Ensemble
# 全部在固定金字塔框架 + Walk-Forward 驗證下比較
# ═══════════════════════════════════════════════

@router.get("/models/leaderboard/history")
async def api_model_leaderboard_history(limit: int = Query(default=12, ge=1, le=100)):
    rows = _load_recent_model_leaderboard_snapshots(limit=limit, db_path=DB_PATH)
    return {
        "history": [
            {
                "id": row.get("id"),
                "created_at": row.get("created_at"),
                "target_col": row.get("target_col"),
                "model_count": row.get("model_count"),
            }
            for row in rows
        ],
        "count": len(rows),
    }


@router.get("/models/leaderboard")
async def api_model_leaderboard(refresh: bool = Query(default=False)):
    """回傳所有 ML 模型的 Walk-Forward Leaderboard。

    採用 stale-while-revalidate：
    - 有 cache 時先回 cache，避免頁面初開等待 10~20 秒
    - cache 過期時背景重算
    - 使用者按刷新可觸發背景 refresh
    """
    _load_model_leaderboard_cache_file()
    _ensure_model_leaderboard_refresh(force=refresh)

    with _MODEL_LB_LOCK:
        payload = _MODEL_LB_CACHE.get("payload")
        updated_at = float(_MODEL_LB_CACHE.get("updated_at") or 0.0)
        refreshing = bool(_MODEL_LB_CACHE.get("refreshing"))
        error = _MODEL_LB_CACHE.get("error")

    now = time.time()
    age_sec = now - updated_at if updated_at else None
    stale = age_sec is None or age_sec > MODEL_LB_CACHE_TTL_SEC
    expired = age_sec is None or age_sec > MODEL_LB_STALE_SEC

    if payload and not expired:
        return {
            **payload,
            "cached": True,
            "refreshing": refreshing,
            "stale": bool(stale),
            "updated_at": datetime.utcfromtimestamp(updated_at).isoformat() + "Z" if updated_at else None,
            "cache_age_sec": int(age_sec) if age_sec is not None else None,
            "error": error,
        }

    if not refreshing:
        _ensure_model_leaderboard_refresh(force=True)

    return {
        "leaderboard": payload.get("leaderboard", []) if isinstance(payload, dict) else [],
        "count": payload.get("count", 0) if isinstance(payload, dict) else 0,
        "cached": bool(payload),
        "refreshing": True,
        "stale": True,
        "updated_at": datetime.utcfromtimestamp(updated_at).isoformat() + "Z" if updated_at else None,
        "cache_age_sec": int(age_sec) if age_sec is not None else None,
        "warning": "Model leaderboard warming in background",
        "error": error,
    }
