"""
REST API 路由 v2.0
"""

import ccxt
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

# ─── Request / Response Models ───

class TradeRequest(BaseModel):
    side: str
    symbol: str = "BTCUSDT"
    qty: float = 0.001

class SenseConfigUpdate(BaseModel):
    sense: str
    module: str
    enabled: Optional[bool] = None
    weight: Optional[float] = None

# ─── Endpoints ───

@router.get("/status")
async def get_status():
    cfg = get_config()
    return {
        "automation": is_automation_enabled(),
        "dry_run": cfg.get("trading", {}).get("dry_run", True),
        "symbol": cfg.get("trading", {}).get("symbol", "BTCUSDT"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

@router.get("/senses")
async def get_senses():
    engine = get_engine()
    scores = engine.calculate_all_scores()
    rec = engine.generate_advice(scores)
    return {"senses": engine.get_senses_status(), "scores": scores, "recommendation": rec}

@router.get("/senses/config")
async def get_senses_cfg():
    return get_engine().get_config()

@router.put("/senses/config")
async def put_senses_cfg(update: SenseConfigUpdate):
    engine = get_engine()
    updates = {}
    if update.enabled is not None: updates["enabled"] = update.enabled
    if update.weight is not None: updates["weight"] = update.weight
    ok = engine.update_sense_config(update.sense, update.module, updates)
    if not ok: raise HTTPException(status_code=400, detail="無效感官或模組")
    scores = engine.calculate_all_scores()
    return {"config": engine.get_config(), "scores": scores, "recommendation": engine.generate_advice(scores)}

@router.get("/recommendation")
async def get_rec():
    engine = get_engine()
    return engine.generate_advice(engine.calculate_all_scores())

@router.get("/chart/klines")
async def get_klines(symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 500):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, interval, limit=limit)
        candles = [{"time": int(b[0]/1000), "open": b[1], "high": b[2], "low": b[3], "close": b[4], "volume": b[5]} for b in ohlcv]
        closes = [b[4] for b in ohlcv]
        indicators = {}
        if len(closes) >= 20:
            indicators["ma20"] = [_calc_ma(closes, 20)[i] for i in range(len(closes))]
        if len(closes) >= 60:
            indicators["ma60"] = [_calc_ma(closes, 60)[i] for i in range(len(closes))]
        if len(closes) >= 15:
            r = _calc_rsi(closes, 14)
            indicators["rsi"] = r
        if len(closes) >= 26:
            m, s, h = _calc_macd(closes)
            indicators["macd"] = {"macd": m, "signal": s, "histogram": h}
        return {"symbol": symbol, "candles": candles, "indicators": indicators}
    except Exception as e:
        logger.error(f"K 線失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backtest")
async def get_backtest(days: int = Query(default=30, ge=1, le=365)):
    """真實回測：用 Binance K 線跑 SMA20 策略"""
    try:
        symbol = "BTCUSDT"
        interval = "4h" if days <= 7 else "1d"
        limit = min(max(int(days * 24 / 4), 20), 500)
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, interval, limit=limit)
        if not ohlcv or len(ohlcv) < 20:
            return {"error": "數據不足", "total_trades": 0, "equity_curve": [], "trades": []}
        closes = [b[4] for b in ohlcv]
        sma20 = [_calc_ma_at(closes, 20, i) for i in range(len(closes))]
        initial = 10000.0
        equity = initial
        position = 0.0
        entry_price = 0.0
        equity_curve = []
        trades = []
        for i, bar in enumerate(ohlcv):
            price = bar[4]
            if position > 0 and price <= entry_price * 0.97:  # 3% 止損
                pnl = (price - entry_price) * position
                equity += pnl
                trades.append({"timestamp": datetime.fromtimestamp(bar[0]/1000).isoformat() + "Z",
                    "action": "sell", "price": round(price, 2), "amount": position, "pnl": round(pnl, 2), "reason": "stop"})
                position = 0
                entry_price = 0
            sma = sma20[i] if sma20[i] is not None else price
            if price > sma and position == 0:
                position = (equity * 0.05) / price
                entry_price = price
            elif price < sma and position > 0:
                pnl = (price - entry_price) * position
                equity += pnl
                trades.append({"timestamp": datetime.fromtimestamp(bar[0]/1000).isoformat() + "Z",
                    "action": "sell", "price": round(price, 2), "amount": position, "pnl": round(pnl, 2), "reason": "cross"})
                position = 0
                entry_price = 0
            equity_curve.append({"timestamp": datetime.fromtimestamp(bar[0]/1000).isoformat() + "Z",
                "equity": round(equity + (position * price if position else 0), 2)})
        if position > 0:
            pnl = (closes[-1] - entry_price) * position
            equity += pnl
            trades.append({"timestamp": datetime.fromtimestamp(ohlcv[-1][0]/1000).isoformat() + "Z",
                "action": "sell", "price": round(closes[-1], 2), "amount": position, "pnl": round(pnl, 2), "reason": "close"})
        win = [t for t in trades if t["pnl"] > 0]
        aw = sum(t["pnl"] for t in win) / max(len(win), 1)
        al = sum(abs(t["pnl"]) for t in trades if t["pnl"] < 0) / max(len(trades) - len(win), 1)
        return {"final_equity": round(equity, 2), "initial_capital": initial, "total_trades": len(trades),
            "win_rate": round(len(win)/max(len(trades),1)*100, 1), "profit_loss_ratio": round(aw/max(al,0.01), 2),
            "max_drawdown": round(_calc_max_dd([e["equity"] for e in equity_curve])*100, 2),
            "total_return": round((equity-initial)/initial*100, 2),
            "equity_curve": equity_curve[-200:], "trades": trades[-50:]}
    except Exception as e:
        logger.error(f"回測失敗: {e}")
        return {"error": str(e), "total_trades": 0, "equity_curve": [], "trades": []}

@router.get("/features")
async def get_features(days: int = Query(default=7, ge=1, le=90)):
    db = get_db()
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.query(FeaturesNormalized).filter(
        FeaturesNormalized.timestamp >= since).order_by(FeaturesNormalized.timestamp).all()
    return [{"timestamp": r.timestamp.isoformat() if r.timestamp else None,
        "feat_eye_dist": r.feat_eye_dist, "feat_ear_zscore": r.feat_ear_zscore,
        "feat_nose_sigmoid": r.feat_nose_sigmoid, "feat_tongue_pct": r.feat_tongue_pct,
        "feat_body_roc": r.feat_body_roc} for r in rows]

@router.post("/backtest/run")
async def run_backtest(days: int = Query(default=30)):
    return await get_backtest(days=days)

@router.post("/trade")
async def manual_trade(req: TradeRequest):
    try:
        exchange = ccxt.binance()
        price = exchange.fetch_ticker(req.symbol)["last"]
        return {"success": True, "dry_run": True,
            "order": {"side": req.side, "symbol": req.symbol, "qty": req.qty, "price": price}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades")
async def get_trades():
    try:
        db = get_db()
        rows = db.query(TradeHistory).order_by(TradeHistory.timestamp.desc()).limit(100).all()
        return [{"action": r.action, "price": r.price, "amount": r.amount,
                 "confidence": r.model_confidence, "pnl": r.pnl} for r in rows]
    except Exception:
        return []

# ─── Helpers ───

def _calc_ma(data, period):
    return [sum(data[max(0, i-period+1):i+1])/min(i+1, period) for i in range(len(data))]

def _calc_ma_at(data, period, i):
    s = max(0, i-period+1)
    n = i - s + 1
    return sum(data[s:i+1])/n if n > 0 else None

def _calc_rsi(data, period=14):
    rsi = [50.0] * len(data)
    gains, losses = [], []
    for i in range(1, len(data)):
        d = data[i] - data[i-1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
        if len(gains) >= period:
            ag = sum(gains[-period:])/period; al = sum(losses[-period:])/period
            rsi[i] = 100 - 100/(1+ag/al) if al > 0 else 100
    return rsi

def _calc_macd(data, fast=12, slow=26, signal=9):
    def ema(v, p):
        k=2/(p+1); r=[v[0]]
        for x in v[1:]: r.append(r[-1]*(1-k)+x*k)
        return r
    ef=ema(data,fast); es=ema(data,slow)
    ml=[f-s for f,s in zip(ef,es)]
    sl=ema(ml[slow-1:],signal)
    sl=[None]*(slow-1)+sl
    hl=[m-s if s is not None else None for m,s in zip(ml,sl)]
    return ml, sl, hl

def _calc_max_dd(eq):
    pk=eq[0]; mdd=0
    for v in eq:
        if v>pk: pk=v
        dd=(pk-v)/pk
        if dd>mdd: mdd=dd
    return mdd
