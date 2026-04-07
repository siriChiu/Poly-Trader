"""
REST API 路由 v4.0 — 多感官策略 + 策略實驗室 + 模型排行榜
"""
import ccxt
import math
import json
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from server.dependencies import get_db, get_config, is_automation_enabled, set_automation_enabled
from server.senses import get_engine
from database.models import TradeHistory, RawMarketData, FeaturesNormalized
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
FEATURE_KEY_MAP = {
    'feat_eye': 'eye', 'feat_ear': 'ear', 'feat_nose': 'nose',
    'feat_tongue': 'tongue', 'feat_body': 'body', 'feat_pulse': 'pulse',
    'feat_aura': 'aura', 'feat_mind': 'mind',
    'feat_vix': 'vix', 'feat_dxy': 'dxy',
    'feat_rsi14': 'rsi14', 'feat_macd_hist': 'macd_hist',
    'feat_atr_pct': 'atr_pct', 'feat_vwap_dev': 'vwap_dev',
    'feat_bb_pct_b': 'bb_pct_b',
    'feat_4h_bias50': '4h_bias50', 'feat_4h_bias20': '4h_bias20',
    'feat_4h_rsi14': '4h_rsi14', 'feat_4h_macd_hist': '4h_macd_hist',
    'feat_4h_bb_pct_b': '4h_bb_pct_b', 'feat_4h_ma_order': '4h_ma_order',
    'feat_4h_dist_swing_low': '4h_dist_sl',
    'feat_4h_dist_swing_high': '4h_dist_sh',
}

_ECDF_ANCHORS = {
    'feat_eye': (-4.5, 4.5), 'feat_ear': (-0.0005, 0.0005),
    'feat_nose': (0.15, 0.80), 'feat_tongue': (-0.001, 0.001),
    'feat_body': (-1.8, 1.3), 'feat_pulse': (0.0, 0.99),
    'feat_aura': (-0.003, 0.003), 'feat_mind': (-0.006, 0.004),
    'feat_vix': (12.0, 35.0), 'feat_dxy': (95.0, 110.0),
    'feat_rsi14': (0.1, 0.85), 'feat_macd_hist': (-0.0005, 0.0005),
    'feat_atr_pct': (0.005, 0.03), 'feat_vwap_dev': (-0.5, 0.5),
    'feat_bb_pct_b': (0.0, 1.0),
    'feat_4h_bias50': (-15.0, 10.0), 'feat_4h_bias20': (-10.0, 10.0),
    'feat_4h_rsi14': (10.0, 90.0), 'feat_4h_macd_hist': (-1500.0, 1500.0),
    'feat_4h_bb_pct_b': (-0.5, 1.5), 'feat_4h_ma_order': (-1.5, 1.5),
    'feat_4h_dist_swing_low': (-25.0, 20.0),
}


def normalize_for_api(raw_val, db_key):
    """ECDF 正規化: p5→0.05, p95→0.95"""
    if raw_val is None:
        return None
    anchors = _ECDF_ANCHORS.get(db_key)
    if not anchors:
        return max(0.0, min(1.0, (raw_val + 1) / 2))
    p5, p95 = anchors
    span = p95 - p5
    if span < 1e-10:
        return 0.5
    clamped = max(p5, min(p95, raw_val))
    return round(0.05 + 0.90 * (clamped - p5) / span, 4)


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


@router.get("/senses")
async def api_senses():
    engine = get_engine()
    scores = engine.calculate_all_scores()
    full_data = engine.get_latest_full_data()
    advice = engine.generate_advice(scores)
    return {
        "senses": engine.get_senses_status(),
        "scores": scores,
        "raw": full_data.get("raw", {}),
        "recommendation": advice,
    }


@router.get("/senses/config")
async def api_senses_cfg():
    return get_engine().get_config()


@router.put("/senses/config")
async def api_put_senses(update: SenseConfigUpdate):
    engine = get_engine()
    updates = {}
    if update.enabled is not None:
        updates["enabled"] = update.enabled
    if update.weight is not None:
        updates["weight"] = update.weight
    ok = engine.update_sense_config(update.sense, update.module, updates)
    if not ok:
        raise HTTPException(status_code=400, detail="無效感官或模組")
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
async def api_backtest(days: int = Query(default=30, ge=1, le=365)):
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
        initial = 10000.0
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


@router.get("/api/predict/confidence")
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
               f.feat_nose, f.feat_pulse, f.feat_ear
        FROM features_normalized f
        JOIN raw_market_data r ON r.timestamp = f.timestamp AND r.symbol = f.symbol
        WHERE f.feat_4h_bias50 IS NOT NULL AND r.close_price IS NOT NULL
        ORDER BY f.timestamp
    """).fetchall()
    conn.close()
    return rows


@router.get("/api/strategies/leaderboard")
async def api_strategy_leaderboard():
    """回傳所有已儲存策略的 Leaderboard（依 ROI 排序）"""
    from backtesting.strategy_lab import load_all_strategies
    strategies = load_all_strategies()
    return {"strategies": strategies, "count": len(strategies)}


@router.get("/api/strategies/{name}")
async def api_get_strategy(name: str):
    """取得單一策略定義"""
    from backtesting.strategy_lab import load_strategy
    s = load_strategy(name)
    if s is None:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    return s


@router.delete("/api/strategies/{name}")
async def api_delete_strategy(name: str):
    """刪除策略"""
    from backtesting.strategy_lab import delete_strategy
    ok = delete_strategy(name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    return {"ok": True, "deleted": name}


@router.post("/api/strategies/run")
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

    if stype == "rule_based":
        result = run_rule_backtest(
            prices, timestamps, bias50, bias50,
            nose, pulse, ear, params, initial)
    elif stype == "hybrid":
        conf = [max(0.0, min(1.0, 1.0 - b / 20.0)) for b in bias50]
        result = run_hybrid_backtest(
            prices, timestamps, bias50, bias50,
            nose, pulse, ear, conf, params, initial)
    else:
        return {"error": f"Unknown strategy type: {stype}"}

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


@router.post("/api/strategies/save")
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
# 8 個模型：Rule Baseline, LogisticRegression, XGBoost, LightGBM,
#           RandomForest, MLP, SVM, Ensemble
# 全部在固定金字塔框架 + Walk-Forward 驗證下比較
# ═══════════════════════════════════════════════

@router.get("/api/models/leaderboard")
async def api_model_leaderboard():
    """回傳所有 ML 模型的 Walk-Forward Leaderboard
    
    包含：XGBoost, LightGBM, RandomForest, LogisticRegression,
          MLP (Neural Net), SVM (RBF), Ensemble, Rule Baseline
    """
    import sqlite3
    import pandas as pd
    import numpy as np
    from backtesting.model_leaderboard import ModelLeaderboard

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT f.timestamp, r.close_price, l.label_sell_win,
               f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue,
               f.feat_body, f.feat_pulse, f.feat_aura, f.feat_mind,
               f.feat_vix, f.feat_dxy,
               f.feat_rsi14, f.feat_macd_hist, f.feat_atr_pct,
               f.feat_vwap_dev, f.feat_bb_pct_b,
               f.feat_4h_bias50, f.feat_4h_bias20, f.feat_4h_rsi14,
               f.feat_4h_macd_hist, f.feat_4h_bb_pct_b,
               f.feat_4h_ma_order, f.feat_4h_dist_swing_low
        FROM features_normalized f
        JOIN raw_market_data r ON r.timestamp = f.timestamp AND r.symbol = f.symbol
        LEFT JOIN labels l ON l.timestamp = f.timestamp AND l.symbol = f.symbol
        WHERE f.feat_4h_bias50 IS NOT NULL AND r.close_price IS NOT NULL
        ORDER BY f.timestamp
    """, conn)
    conn.close()

    df = df.fillna(0)
    df['label_sell_win'] = df['label_sell_win'].fillna(1).astype(int)

    lb = ModelLeaderboard(df)
    results = lb.run_all_models([
        "rule_baseline", "logistic_regression", "xgboost",
        "lightgbm", "random_forest", "mlp", "svm"
    ])

    leaderboard = []
    for r in results:
        fold_data = []
        for f in r.folds:
            fold_data.append({
                "fold": f.fold,
                "train_start": f.train_start,
                "train_end": f.train_end,
                "test_start": f.test_start,
                "test_end": f.test_end,
                "roi": round(f.roi, 4),
                "win_rate": round(f.win_rate, 4),
                "trades": f.total_trades,
                "max_dd": round(f.max_drawdown, 4),
                "profit_factor": round(f.profit_factor, 4),
            })
        leaderboard.append({
            "model_name": r.model_name,
            "avg_roi": round(r.avg_roi, 4),
            "avg_win_rate": round(r.avg_win_rate, 4),
            "avg_trades": int(r.avg_trades),
            "avg_max_dd": round(r.avg_max_drawdown, 4),
            "std_roi": round(r.std_roi, 4),
            "profit_factor": round(r.avg_profit_factor, 4),
            "train_acc": round(r.train_accuracy, 4),
            "test_acc": round(r.test_accuracy, 4),
            "train_test_gap": round(r.train_test_gap, 4),
            "composite": round(r.composite_score, 4),
            "folds": fold_data,
        })

    return {"leaderboard": leaderboard, "count": len(leaderboard)}
