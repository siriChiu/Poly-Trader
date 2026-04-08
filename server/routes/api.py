"""
REST API 路由 v4.0 — 多特徵策略 + 策略實驗室 + 模型排行榜
"""
import ccxt
import math
import json
import sqlite3
import threading
import time
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

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
    'feat_bb_pct_b': (0.0, 1.0),
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
        quality = assess_feature_quality(clean_key, coverage_pct, distinct, len(non_null_values), min_val, max_val)
        quality = attach_forward_archive_meta(clean_key, quality, snapshot_counts, snapshot_stats)
        archive_window = _compute_archive_window_coverage(clean_key, timestamp_values, values, snapshot_stats)
        feature_stats[clean_key] = {
            "db_key": db_key,
            "non_null": len(non_null_values),
            "coverage_pct": round(coverage_pct, 2),
            "distinct": distinct,
            "min": min_val,
            "max": max_val,
            **quality,
            **archive_window,
        }
    return {
        "days": days,
        "rows": total_rows,
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
async def api_klines(symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 500):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, interval, limit=limit)
        candles = [{"time": int(b[0] / 1000), "open": b[1], "high": b[2],
                     "low": b[3], "close": b[4], "volume": b[5]} for b in ohlcv]
        closes = [b[4] for b in ohlcv]
        indicators = {"ma20": [], "ma60": [], "rsi": [], "macd": None,
                      "signal": [], "histogram": []}
        for i in range(len(closes)):
            indicators["ma20"].append(round(_calc_ma_at(closes, 20, i), 2))
            indicators["ma60"].append(round(_calc_ma_at(closes, 60, i), 2))
        if len(closes) >= 15:
            avg_g = [0] * len(closes)
            avg_l = [0] * len(closes)
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
                round(100 - 100 / (1 + (g / l if l > 0 else 999)), 1)
                if g + l > 0 else 50 for g, l in zip(avg_g, avg_l)]
        if len(closes) >= 26:
            def _ema(v, period):
                k = 2 / (period + 1)
                r = [v[0]]
                for x in v[1:]:
                    r.append(r[-1] * (1 - k) + x * k)
                return r
            ema12 = _ema(closes, 12)
            ema26 = _ema(closes, 26)
            macd_l = [f - s for f, s in zip(ema12, ema26)]
            signal_l = _ema(macd_l[26 - 1:], 9)
            signal_l = [None] * (26 - 1) + signal_l
            indicators["macd"] = [round(m, 4) if m is not None else None for m in macd_l]
            indicators["signal"] = [round(s, 4) if s is not None else None for s in signal_l]
            indicators["histogram"] = [
                round(m - s, 4) if (m is not None and s is not None) else None
                for m, s in zip(macd_l, signal_l)]
        return {"symbol": symbol, "candles": candles, "indicators": indicators}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest")
async def api_backtest(days: int = Query(default=30, ge=1, le=365), initial_capital: float = Query(default=10000.0, ge=100.0, le=10000000.0)):
    try:
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
        equity_curve = []
        trades = []
        threshold = 0.50
        exit_thresh = 0.45
        stop_p = 0.03
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
            vals = [feat.feat_eye_dist, feat.feat_ear_zscore,
                    feat.feat_nose_sigmoid, feat.feat_tongue_pct,
                    feat.feat_body_roc]
            valid = [v for v in vals if v is not None]
            if not valid:
                continue
            normed = [(v + 1) / 2 for v in valid]
            score = sum(normed) / len(normed)
            if position > 0 and price <= entry_price * (1 - stop_p):
                pnl = (price - entry_price) * position
                equity += pnl
                trades.append({"timestamp": datetime.fromtimestamp(dt).isoformat() + "Z",
                               "action": "sell", "price": round(price, 2),
                               "amount": position, "pnl": round(pnl, 2),
                               "reason": "stop_loss"})
                position = 0
            if score >= threshold and position == 0:
                position = (equity * 0.05) / price
                entry_price = price
            elif score < exit_thresh and position > 0:
                pnl = (price - entry_price) * position
                equity += pnl
                trades.append({"timestamp": datetime.fromtimestamp(dt).isoformat() + "Z",
                               "action": "sell", "price": round(price, 2),
                               "amount": position, "pnl": round(pnl, 2),
                               "reason": "signal_exit"})
                position = 0
            equity_curve.append({
                "timestamp": datetime.fromtimestamp(dt).isoformat() + "Z",
                "equity": round(equity + (position * price if position else 0), 2)})
        if position > 0:
            pnl = (c - entry_price) * position
            equity += pnl
            trades.append({"timestamp": datetime.fromtimestamp(ohlcv[-1][0] / 1000).isoformat() + "Z",
                           "action": "sell", "price": round(c, 2),
                           "amount": position, "pnl": round(pnl, 2), "reason": "end"})
        win = [t for t in trades if t["pnl"] > 0]
        aw = sum(t["pnl"] for t in win) / max(len(win), 1)
        al = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0)) / max(len(trades) - len(win), 1)
        return {
            "final_equity": round(equity, 2), "initial_capital": initial,
            "total_trades": len(trades),
            "win_rate": round(len(win) / max(len(trades), 1) * 100, 1),
            "profit_loss_ratio": round(aw / max(al, 0.01), 2),
            "max_drawdown": round(_calc_max_dd([e["equity"] for e in equity_curve]) * 100, 2),
            "total_return": round((equity - initial) / initial * 100, 2),
            "equity_curve": equity_curve[-200:], "trades": trades[-50:]
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
    predictor = load_predictor()
    result = predict(session, predictor)
    session.close()
    if result is None:
        return {"error": "prediction failed", "confidence": 0.5,
                "signal": "HOLD", "confidence_level": "LOW",
                "should_trade": False}
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
            })
        is_overfit = bool(r.train_test_gap > overfit_gap_threshold or r.train_accuracy > hard_train_acc_cap)
        leaderboard.append({
            "model_name": str(r.model_name),
            "avg_roi": float(round(r.avg_roi, 4)),
            "avg_win_rate": float(round(r.avg_win_rate, 4)),
            "avg_trades": int(r.avg_trades),
            "avg_max_dd": float(round(r.avg_max_drawdown, 4)),
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


def _summarize_target_candidates(df, overfit_gap_threshold: float, hard_train_acc_cap: float) -> List[Dict[str, Any]]:
    from backtesting.model_leaderboard import ModelLeaderboard

    summaries = []
    candidate_models = ["rule_baseline", "logistic_regression", "xgboost", "catboost"]
    target_specs = [
        ("label_spot_long_win", "Path-aware TP/DD"),
        ("simulated_pyramid_win", "Simulated Pyramid"),
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
        summaries.append({
            "target_col": target_col,
            "label": label,
            "samples": int(len(target_df)),
            "positive_ratio": float(round(target_df[target_col].mean(), 4)),
            "best_model": best,
            "models_evaluated": len(serialized),
        })
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
        features_df = pd.read_sql(
            """
            SELECT timestamp,
                   feat_eye, feat_ear, feat_nose, feat_tongue,
                   feat_body, feat_pulse, feat_aura, feat_mind,
                   feat_vix, feat_dxy,
                   feat_rsi14, feat_macd_hist, feat_atr_pct,
                   feat_vwap_dev, feat_bb_pct_b,
                   feat_4h_bias50, feat_4h_bias20, feat_4h_rsi14,
                   feat_4h_macd_hist, feat_4h_bb_pct_b,
                   feat_4h_ma_order, feat_4h_dist_swing_low
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


def _load_strategy_data():
    """載入回測用的完整資料"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT f.timestamp, r.close_price,
               f.feat_4h_bias50, f.feat_4h_dist_swing_low,
               f.feat_nose, f.feat_pulse, f.feat_ear,
               COALESCE(f.regime_label, 'unknown') AS regime_label
        FROM features_normalized f
        JOIN raw_market_data r ON r.timestamp = f.timestamp AND r.symbol = f.symbol
        WHERE f.feat_4h_bias50 IS NOT NULL AND r.close_price IS NOT NULL
        ORDER BY f.timestamp
    """).fetchall()
    conn.close()
    return rows


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


def _compute_backtest_benchmarks(
    prices: List[float],
    timestamps: List[str],
    bias50: List[float],
    nose: List[float],
    pulse: List[float],
    ear: List[float],
    regimes: List[str],
    initial_capital: float,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    from backtesting.strategy_lab import run_rule_backtest

    buy_hold_roi = 0.0
    if prices and prices[0]:
        buy_hold_roi = (prices[-1] - prices[0]) / prices[0]

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
        bias50,
        nose,
        pulse,
        ear,
        blind_params,
        initial_capital,
        regimes=regimes,
    )
    blind_summary = _summarize_trades(blind_result.trades, initial_capital)

    return {
        "buy_hold": {
            "label": "買入持有",
            "roi": round(buy_hold_roi, 4),
        },
        "blind_pyramid": {
            "label": "盲金字塔",
            **blind_summary,
        },
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


def _decorate_strategy_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(entry)
    risk = _compute_strategy_risk(entry.get("last_results"))
    enriched.update(risk)
    return enriched


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
    results = lb.run_all_models([
        "rule_baseline", "logistic_regression", "xgboost",
        "lightgbm", "catboost", "random_forest", "mlp", "svm"
    ])

    OVERFIT_GAP_THRESHOLD = 0.12
    HARD_TRAIN_ACC_CAP = 0.90

    leaderboard = _serialize_model_scores(results, OVERFIT_GAP_THRESHOLD, HARD_TRAIN_ACC_CAP)
    target_comparison = _summarize_target_candidates(df, OVERFIT_GAP_THRESHOLD, HARD_TRAIN_ACC_CAP)

    return {
        "leaderboard": leaderboard,
        "count": len(leaderboard),
        "overfit_gap_threshold": OVERFIT_GAP_THRESHOLD,
        "hard_train_acc_cap": HARD_TRAIN_ACC_CAP,
        "target_col": default_target_col,
        "target_label": "Simulated Pyramid" if default_target_col == "simulated_pyramid_win" else "Path-aware TP/DD",
        "target_comparison": target_comparison,
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


@router.get("/strategies/leaderboard")
async def api_strategy_leaderboard():
    """回傳所有已儲存策略的 Leaderboard（依 ROI 排序）"""
    from backtesting.strategy_lab import load_all_strategies
    strategies = [_decorate_strategy_entry(s) for s in load_all_strategies()]
    return {"strategies": strategies, "count": len(strategies)}


@router.get("/strategies/{name}")
async def api_get_strategy(name: str):
    """取得單一策略定義"""
    from backtesting.strategy_lab import load_strategy
    s = load_strategy(name)
    if s is None:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    return s


@router.delete("/strategies/{name}")
async def api_delete_strategy(name: str):
    """刪除策略"""
    from backtesting.strategy_lab import delete_strategy
    ok = delete_strategy(name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    return {"ok": True, "deleted": name}


@router.post("/strategies/run")
async def api_run_strategy(body: Dict[str, Any]):
    """
    執行策略回測
    Body: {name, type, params, initial_capital}
    """
    import sqlite3
    from backtesting.strategy_lab import (
        run_rule_backtest, run_hybrid_backtest, save_strategy)

    name = body.get("name", "unnamed_strategy")
    stype = body.get("type", "rule_based")
    params = body.get("params", {})
    initial = body.get("initial_capital", 10000.0)

    rows = _load_strategy_data()
    if not rows:
        return {"error": "No data available for backtest"}

    timestamps = [str(r[0]) for r in rows]
    prices = [float(r[1]) for r in rows]
    bias50 = [float(r[2]) if r[2] is not None else 0 for r in rows]
    dist_sl = [float(r[3]) if r[3] is not None else 100 for r in rows]
    nose = [float(r[4]) if r[4] is not None else 0.5 for r in rows]
    pulse = [float(r[5]) if r[5] is not None else 0.5 for r in rows]
    ear = [float(r[6]) if r[6] is not None else 0 for r in rows]
    regimes = [str(r[7]).lower() if r[7] else "unknown" for r in rows]

    if stype == "rule_based":
        result = run_rule_backtest(
            prices, timestamps, bias50, bias50,
            nose, pulse, ear, params, initial, regimes=regimes)
    elif stype == "hybrid":
        conf = [max(0.0, min(1.0, 1.0 - b / 20.0)) for b in bias50]
        result = run_hybrid_backtest(
            prices, timestamps, bias50, bias50,
            nose, pulse, ear, conf, params, initial, regimes=regimes)
    else:
        return {"error": f"Unknown strategy type: {stype}"}

    benchmarks = _compute_backtest_benchmarks(
        prices, timestamps, bias50, nose, pulse, ear, regimes, initial, params
    )

    strat_def = {"type": stype, "params": params}
    results_dict = {
        "roi": round(result.roi, 4),
        "win_rate": round(result.win_rate, 4),
        "total_trades": result.total_trades,
        "wins": result.wins, "losses": result.losses,
        "max_drawdown": round(result.max_drawdown, 4),
        "profit_factor": round(result.profit_factor, 4),
        "total_pnl": round(result.total_pnl, 2),
        "avg_win": round(result.avg_win, 2),
        "avg_loss": round(result.avg_loss, 2),
        "max_consecutive_losses": result.max_consecutive_losses,
        "regime_breakdown": _compute_regime_breakdown(result.trades, initial),
        "benchmarks": benchmarks,
        "run_at": datetime.utcnow().isoformat() + "Z",
    }
    save_strategy(name, strat_def, results_dict)
    result.equity_curve = result.equity_curve[-100:] if result.equity_curve else []
    return {
        "strategy": name, "type": stype, "params": params,
        "results": results_dict,
        "equity_curve": result.equity_curve,
        "trades": result.trades[-50:],
    }


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
