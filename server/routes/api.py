"""
REST API 路由 v3.0 — 多感官策略回測引擎
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
    return {"senses": engine.get_senses_status(), "scores": scores, "recommendation": engine.generate_advice(scores)}

@router.get("/senses/config")
async def api_senses_cfg():
    return get_engine().get_config()

@router.put("/senses/config")
async def api_put_senses(update: SenseConfigUpdate):
    engine = get_engine()
    updates = {}
    if update.enabled is not None: updates["enabled"] = update.enabled
    if update.weight is not None: updates["weight"] = update.weight
    ok = engine.update_sense_config(update.sense, update.module, updates)
    if not ok: raise HTTPException(status_code=400, detail="無效感官或模組")
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
        candles = [{"time": int(b[0] / 1000), "open": b[1], "high": b[2], "low": b[3], "close": b[4], "volume": b[5]} for b in ohlcv]
        closes = [b[4] for b in ohlcv]
        indicators = {"ma20": [], "ma60": [], "rsi": [], "macd": None, "signal": [], "histogram": []}
        for i in range(len(closes)):
            indicators["ma20"].append(round(_calc_ma_at(closes, 20, i), 2))
            indicators["ma60"].append(round(_calc_ma_at(closes, 60, i), 2))
        if len(closes) >= 15:
            avg_g = [0] * len(closes); avg_l = [0] * len(closes)
            for i in range(1, len(closes)):
                d = closes[i] - closes[i - 1]
                if i < 14:
                    if d > 0: avg_g[i] = d
                    if d < 0: avg_l[i] = -d
                else:
                    avg_g[i] = (avg_g[i - 1] * 13 + max(d, 0)) / 14
                    avg_l[i] = (avg_l[i - 1] * 13 + max(-d, 0)) / 14
            indicators["rsi"] = [round(100 - 100 / (1 + (g / l if l > 0 else 999)), 1) if g + l > 0 else 50 for g, l in zip(avg_g, avg_l)]
        # MACD (12, 26, 9)
        if len(closes) >= 26:
            def _ema(v, period):
                k = 2 / (period + 1); r = [v[0]]
                for x in v[1:]: r.append(r[-1] * (1 - k) + x * k)
                return r
            ema12 = _ema(closes, 12); ema26 = _ema(closes, 26)
            macd_l = [f - s for f, s in zip(ema12, ema26)]
            signal_l = _ema(macd_l[26 - 1:], 9)
            signal_l = [None] * (26 - 1) + signal_l
            indicators["macd"] = [round(m, 4) if m is not None else None for m in macd_l]
            indicators["signal"] = [round(s, 4) if s is not None else None for s in signal_l]
            indicators["histogram"] = [round(m - s, 4) if (m is not None and s is not None) else None for m, s in zip(macd_l, signal_l)]
        return {"symbol": symbol, "candles": candles, "indicators": indicators}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backtest")
async def api_backtest(
    days: int = Query(default=30, ge=1, le=365),
    confidence_threshold: float = Query(default=0.55, ge=0.0, le=1.0),
    max_position_ratio: float = Query(default=0.05, ge=0.0, le=1.0),
    stop_loss_pct: float = Query(default=0.02, ge=0.0, le=1.0),
    test_days: int = Query(default=10, ge=1, le=90),
    train_days: int = Query(default=30, ge=1, le=180),
    n_windows: int = Query(default=5, ge=1, le=20),
    mode: str = Query(default="single", pattern="^(single|grid|walkforward)$"),
):
    """【多感官策略回測】支持單次回測、網格搜索與 walk-forward。"""
    try:
        db = get_db()
        cfg = get_config()
        symbol = cfg.get("trading", {}).get("symbol", "BTCUSDT")

        if mode == "grid":
            from backtesting.optimizer import grid_search
            end = datetime.utcnow()
            start = end - timedelta(days=days)
            df = grid_search(
                session=db,
                confidence_thresholds=[round(max(0.0, confidence_threshold - 0.05), 2), confidence_threshold, round(min(1.0, confidence_threshold + 0.05), 2)],
                max_position_ratios=[round(max(0.0, max_position_ratio - 0.02), 2), max_position_ratio, round(min(1.0, max_position_ratio + 0.02), 2)],
                stop_loss_pcts=[round(max(0.0, stop_loss_pct - 0.01), 2), stop_loss_pct, round(min(1.0, stop_loss_pct + 0.01), 2)],
                start_date=start,
                end_date=end,
                initial_capital=10000.0,
                symbol=symbol,
            )
            return {"mode": "grid", "rows": df.to_dict(orient="records"), "count": len(df)}

        if mode == "walkforward":
            from backtesting.walkforward import run_walk_forward
            res = run_walk_forward(
                db,
                {
                    "confidence_threshold": confidence_threshold,
                    "max_position_ratio": max_position_ratio,
                    "stop_loss_pct": stop_loss_pct,
                },
                train_days=train_days,
                test_days=test_days,
                n_windows=n_windows,
                initial_capital=10000.0,
                symbol=symbol,
            )
            return {"mode": "walkforward", **res}

        from backtesting.engine import run_backtest
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        res = run_backtest(
            session=db,
            start_date=start,
            end_date=end,
            initial_capital=10000.0,
            confidence_threshold=confidence_threshold,
            max_position_ratio=max_position_ratio,
            stop_loss_pct=stop_loss_pct,
            symbol=symbol,
        )
        if res is None:
            return {"error": "回測結果為空", "total_trades": 0, "equity_curve": [], "trades": []}
        return {
            "mode": "single",
            "confidence_threshold": confidence_threshold,
            "max_position_ratio": max_position_ratio,
            "stop_loss_pct": stop_loss_pct,
            "result": {
                "final_equity": res.get("final_equity"),
                "initial_capital": res.get("initial_capital"),
                "total_trades": res.get("total_trades"),
                "win_rate": res.get("win_rate"),
                "profit_loss_ratio": res.get("profit_factor"),
                "max_drawdown": res.get("max_drawdown"),
                "total_return": res.get("total_return"),
                "sell_win_rate": res.get("sell_win_rate"),
                "equity_curve": res.get("equity_curve").reset_index().to_dict(orient="records") if hasattr(res.get("equity_curve"), "reset_index") else [],
                "trades": res.get("trade_log").to_dict(orient="records") if hasattr(res.get("trade_log"), "to_dict") else [],
            },
        }
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        import traceback; traceback.print_exc()
        return {"error": str(e), "total_trades": 0, "equity_curve": [], "trades": []}

@router.get("/features")
async def api_features(days: int = Query(default=7, ge=1, le=90)):
    db = get_db()
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.query(FeaturesNormalized).filter(FeaturesNormalized.timestamp >= since).order_by(FeaturesNormalized.timestamp).all()
    return [{"timestamp": r.timestamp.isoformat() if r.timestamp else None,
        "feat_eye": getattr(r, 'feat_eye', None), "feat_ear": getattr(r, 'feat_ear', None),
        "feat_nose": getattr(r, 'feat_nose', None), "feat_tongue": getattr(r, 'feat_tongue', None),
        "feat_body": getattr(r, 'feat_body', None), "feat_pulse": getattr(r, 'feat_pulse', None),
        "feat_aura": getattr(r, 'feat_aura', None), "feat_mind": getattr(r, 'feat_mind', None),
        "feat_whisper": getattr(r, 'feat_whisper', None), "feat_tone": getattr(r, 'feat_tone', None),
        "feat_chorus": getattr(r, 'feat_chorus', None), "feat_hype": getattr(r, 'feat_hype', None),
        "feat_oracle": getattr(r, 'feat_oracle', None), "feat_shock": getattr(r, 'feat_shock', None),
        "feat_tide": getattr(r, 'feat_tide', None), "feat_storm": getattr(r, 'feat_storm', None)
    } for r in rows]


@router.get("/model/stats")
async def api_model_stats():
    """返回模型準確率、IC 值等統計資訊，供 Web 顯示"""
    import os, pickle, numpy as np
    from model.train import FEATURE_COLS
    from model.predictor import MODEL_PATH
    from database.models import Labels, FeaturesNormalized
    from sqlalchemy import text

    db = get_db()
    stats = {
        "model_loaded": False,
        "sample_count": 0,
        "label_distribution": {},
        "cv_accuracy": None,
        "feature_importance": {},
        "ic_values": {},
        "model_params": {}
    }

    # 樣本數和標籤分布
    try:
        total = db.query(Labels).count()
        stats["sample_count"] = total
        dist = db.execute(text("SELECT label, COUNT(*) as cnt FROM labels GROUP BY label")).fetchall()
        stats["label_distribution"] = {str(r[0]): r[1] for r in dist}
    except Exception as e:
        logger.error(f"Stats label error: {e}")

    # 模型準確率 and feature importance
    try:
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            stats["model_loaded"] = True
            if hasattr(model, "feature_importances_"):
                imp = dict(zip(FEATURE_COLS, model.feature_importances_.tolist()))
                stats["feature_importance"] = {k: round(v, 4) for k, v in sorted(imp.items(), key=lambda x: -x[1])}
            if hasattr(model, "get_params"):
                p = model.get_params()
                stats["model_params"] = {k: p.get(k) for k in ["n_estimators", "max_depth", "reg_alpha", "reg_lambda"]}
    except Exception as e:
        logger.error(f"Stats model error: {e}")

    # IC 計算 (Pearson correlation for each feature vs label)
    try:
        rows = db.execute(text("""
            SELECT f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue, f.feat_body, l.label_sell_win
            FROM features_normalized f INNER JOIN labels l ON f.id = l.id
            WHERE f.feat_eye IS NOT NULL AND l.label_sell_win IS NOT NULL
        """)).fetchall()
        if len(rows) > 30:
            data = np.array(rows)
            labels_arr = data[:, -1]
            for i, name in enumerate(["eye", "ear", "nose", "tongue", "body"]):
                feats = data[:, i]
                if np.std(feats) > 0 and np.std(labels_arr) > 0:
                    ic = float(np.corrcoef(feats, labels_arr)[0, 1])
                    stats["ic_values"][name] = round(ic, 4)
    except Exception as e:
        logger.error(f"Stats IC error: {e}")

    return stats

@router.get("/optimizer")
async def api_optimizer(
    days: int = Query(default=30, ge=1, le=365),
    confidence_threshold: float = Query(default=0.55, ge=0.0, le=1.0),
    max_position_ratio: float = Query(default=0.05, ge=0.0, le=1.0),
    stop_loss_pct: float = Query(default=0.02, ge=0.0, le=1.0),
):
    db = get_db()
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    from backtesting.optimizer import grid_search
    df = grid_search(
        session=db,
        confidence_thresholds=[confidence_threshold],
        max_position_ratios=[max_position_ratio],
        stop_loss_pcts=[stop_loss_pct],
        start_date=start,
        end_date=end,
        initial_capital=10000.0,
        symbol=get_config().get("trading", {}).get("symbol", "BTCUSDT"),
    )
    return {"count": len(df), "rows": df.to_dict(orient="records")}

@router.post("/backtest/run")
async def api_run_backtest(days: int = Query(default=30)):
    return await api_backtest(days=days)


# ─── Confidence Prediction ───
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
        return {"error": "prediction failed", "confidence": 0.5, "signal": "HOLD", "confidence_level": "LOW", "should_trade": False}
    return result
