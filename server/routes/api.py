"""
REST API 路由 v3.0 — 五感策略回測引擎
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
async def api_backtest(days: int = Query(default=30, ge=1, le=365)):
    """【五感策略回測】基於 XGBoost 信心分數的真實回測"""
    try:
        symbol = "BTCUSDT"
        interval = "4h" if days <= 7 else "1d"
        limit = max(int(days * 6), 20)
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, interval, limit=limit)
        if not ohlcv or len(ohlcv) < 20:
            return {"error": "數據不足", "total_trades": 0, "equity_curve": [], "trades": []}

        # 1. 讀取 DB 中對應時間區間的特徵
        db = get_db()
        start = datetime.fromtimestamp(ohlcv[0][0] / 1000)
        features = db.query(FeaturesNormalized).filter(
            FeaturesNormalized.timestamp >= start
        ).order_by(FeaturesNormalized.timestamp).all()
        feat_map = {}
        for f in features:
            feat_map[int(f.timestamp.timestamp())] = f

        # 2. 執行五感策略回測
        initial = 10000.0
        equity = initial; position = 0.0; entry_price = 0.0
        equity_curve = []; trades = []
        threshold = 0.55  # 買入閾值
        stop_p = 0.03  # 3% 止損

        for bar in ohlcv:
            t, o, h, l, c = bar[0], bar[1], bar[2], bar[3], bar[4]
            dt = int(t / 1000)
            price = c
            # 找最近的特徵 (2小時內)
            feat = None; min_diff = 999999
            for ft, f in feat_map.items():
                d = abs(ft - dt)
                if d < min_diff: min_diff = d; feat = f
            if not feat or min_diff > 2 * 3600:
                # 無特徵時繼續觀察但更新權益
                equity_curve.append({"timestamp": datetime.fromtimestamp(dt).isoformat() + "Z", "equity": round(equity + (position * price if position else 0), 2)})
                continue

            # 計算五感綜合分數 (0~1)
            vals = [feat.feat_eye_dist, feat.feat_ear_zscore, feat.feat_nose_sigmoid, feat.feat_tongue_pct, feat.feat_body_roc]
            valid = [v for v in vals if v is not None]
            if not valid: continue
            score = sum(valid) / len(valid)

            # 止損
            if position > 0 and price <= entry_price * (1 - stop_p):
                pnl = (price - entry_price) * position
                equity += pnl
                trades.append({"timestamp": datetime.fromtimestamp(dt).isoformat() + "Z", "action": "sell", "price": round(price, 2), "amount": position, "pnl": round(pnl, 2), "reason": "stop_loss"})
                position = 0

            # 策略邏輯
            if score >= threshold and position == 0:
                position = (equity * 0.05) / price
                entry_price = price
            elif score < 0.45 and position > 0:
                pnl = (price - entry_price) * position
                equity += pnl
                trades.append({"timestamp": datetime.fromtimestamp(dt).isoformat() + "Z", "action": "sell", "price": round(price, 2), "amount": position, "pnl": round(pnl, 2), "reason": "signal_exit"})
                position = 0

            equity_curve.append({"timestamp": datetime.fromtimestamp(dt).isoformat() + "Z", "equity": round(equity + (position * price if position else 0), 2)})

        if position > 0:
            pnl = (c - entry_price) * position
            equity += pnl
            trades.append({"timestamp": datetime.fromtimestamp(ohlcv[-1][0] / 1000).isoformat() + "Z", "action": "sell", "price": round(c, 2), "amount": position, "pnl": round(pnl, 2), "reason": "end"})

        win = [t for t in trades if t["pnl"] > 0]
        aw = sum(t["pnl"] for t in win) / max(len(win), 1)
        al = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0)) / max(len(trades) - len(win), 1)
        return {
            "final_equity": round(equity, 2), "initial_capital": initial,
            "total_trades": len(trades), "win_rate": round(len(win) / max(len(trades), 1) * 100, 1),
            "profit_loss_ratio": round(aw / max(al, 0.01), 2),
            "max_drawdown": round(_calc_max_dd([e["equity"] for e in equity_curve]) * 100, 2),
            "total_return": round((equity - initial) / initial * 100, 2),
            "equity_curve": equity_curve[-200:], "trades": trades[-50:]
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
        "feat_eye_dist": r.feat_eye_dist, "feat_ear_zscore": r.feat_ear_zscore,
        "feat_nose_sigmoid": r.feat_nose_sigmoid, "feat_tongue_pct": r.feat_tongue_pct,
        "feat_body_roc": r.feat_body_roc} for r in rows]

@router.post("/backtest/run")
async def api_run_backtest(days: int = Query(default=30)):
    return await api_backtest(days=days)
