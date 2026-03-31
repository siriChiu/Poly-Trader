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
from database.models import TradeHistory, RawMarketData
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


# ─── Request / Response Models ───

class TradeRequest(BaseModel):
    side: str  # "buy" or "sell"
    symbol: str = "BTCUSDT"
    qty: float = 0.001


class SenseModuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    weight: Optional[float] = None


class SenseConfigUpdate(BaseModel):
    sense: str  # eye, ear, nose, tongue, body
    module: str  # sub-module key
    enabled: Optional[bool] = None
    weight: Optional[float] = None


# ─── Endpoints ───

@router.get("/status")
async def get_status():
    """系統狀態"""
    cfg = get_config()
    return {
        "automation": is_automation_enabled(),
        "dry_run": cfg.get("trading", {}).get("dry_run", True),
        "symbol": cfg.get("trading", {}).get("symbol", "BTCUSDT"),
        "confidence_threshold": cfg.get("trading", {}).get("confidence_threshold", 0.7),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/senses")
async def get_senses():
    """五感詳細狀態（含子模組組成、數據源、當前值）"""
    engine = get_engine()
    scores = engine.calculate_all_scores()
    rec = engine.generate_advice(scores)
    return {
        "senses": engine.get_senses_status(),
        "scores": scores,
        "recommendation": rec,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/senses/config")
async def get_senses_config():
    """感官配置（子模組、權重）"""
    engine = get_engine()
    return engine.get_config()


@router.put("/senses/config")
async def update_senses_config(update: SenseConfigUpdate):
    """更新感官配置（啟用/停用、調整權重）"""
    engine = get_engine()
    updates = {}
    if update.enabled is not None:
        updates["enabled"] = update.enabled
    if update.weight is not None:
        updates["weight"] = update.weight

    success = engine.update_sense_config(update.sense, update.module, updates)
    if not success:
        raise HTTPException(status_code=400, detail="無效的感官或子模組")

    # 返回更新後的分數預覽
    scores = engine.calculate_all_scores()
    rec = engine.generate_advice(scores)
    return {
        "success": True,
        "config": engine.get_config(),
        "scores": scores,
        "recommendation": rec,
    }


@router.get("/recommendation")
async def get_recommendation():
    """綜合建議（分數 + 自然語言）"""
    engine = get_engine()
    scores = engine.calculate_all_scores()
    return engine.generate_advice(scores)


@router.get("/chart/klines")
async def get_klines(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="1h"),
    limit: int = Query(default=500, ge=10, le=1000),
):
    """K 線數據（含技術指標）"""
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, interval, limit=limit)

        candles = []
        closes = []
        for bar in ohlcv:
            t, o, h, l, c, v = bar
            candles.append({
                "time": t // 1000,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v,
            })
            closes.append(c)

        # 計算技術指標
        indicators = {}
        if len(closes) >= 20:
            indicators["ma20"] = _calc_ma(closes, 20)
        if len(closes) >= 60:
            indicators["ma60"] = _calc_ma(closes, 60)
        if len(closes) >= 14:
            indicators["rsi"] = _calc_rsi(closes, 14)
        if len(closes) >= 26:
            macd_line, signal_line, histogram = _calc_macd(closes)
            indicators["macd"] = {
                "macd": macd_line,
                "signal": signal_line,
                "histogram": histogram,
            }

        return {
            "symbol": symbol,
            "interval": interval,
            "candles": candles,
            "indicators": indicators,
        }
    except Exception as e:
        logger.error(f"K 線數據獲取失敗: {e}")
        raise HTTPException(status_code=500, detail=f"K 線數據獲取失敗: {str(e)}")


@router.get("/backtest")
async def get_backtest():
    """回測結果"""
    # 返回模擬回測數據
    import random
    initial = 10000
    equity = initial
    equity_curve = []
    trades = []
    base_time = datetime.utcnow() - timedelta(days=30)

    for i in range(30 * 24):
        t = base_time + timedelta(hours=i)
        change = random.gauss(0.0002, 0.01)
        equity *= (1 + change)
        equity_curve.append({"timestamp": t.isoformat() + "Z", "equity": round(equity, 2)})

        if random.random() < 0.05:
            action = random.choice(["buy", "sell"])
            pnl = random.gauss(10, 50)
            trades.append({
                "timestamp": t.isoformat() + "Z",
                "action": action,
                "price": round(random.uniform(60000, 70000), 2),
                "amount": round(random.uniform(0.001, 0.01), 4),
                "confidence": round(random.uniform(0.5, 0.95), 2),
                "pnl": round(pnl, 2),
            })

    winning = [t for t in trades if t["pnl"] > 0]
    total_pnl = sum(t["pnl"] for t in trades)
    max_dd = _calc_max_drawdown([e["equity"] for e in equity_curve])

    return {
        "final_equity": round(equity, 2),
        "initial_capital": initial,
        "total_trades": len(trades),
        "win_rate": round(len(winning) / max(len(trades), 1) * 100, 1),
        "profit_loss_ratio": round(
            sum(t["pnl"] for t in winning) / max(len(winning), 1) /
            max(abs(sum(t["pnl"] for t in trades if t["pnl"] < 0)) / max(len(trades) - len(winning), 1), 0.01),
            2
        ) if trades else 0,
        "max_drawdown": round(max_dd * 100, 2),
        "total_return": round((equity - initial) / initial * 100, 2),
        "equity_curve": equity_curve[-200:],  # 最後 200 點
        "trades": trades[-50:],  # 最後 50 筆
    }


@router.post("/backtest/run")
async def run_backtest_api(
    days: int = Query(default=30, ge=1, le=365),
    initial_capital: float = Query(default=10000.0),
):
    """執行回測（同 GET /backtest，但可用 POST 觸發）"""
    return await get_backtest()


@router.post("/trade")
async def manual_trade(req: TradeRequest):
    """手動下單"""
    try:
        exchange = ccxt.binance()
        ticker = exchange.fetch_ticker(req.symbol)
        price = ticker["last"]

        # Dry run 模式下不下真實訂單
        return {
            "success": True,
            "dry_run": True,
            "order": {
                "side": req.side,
                "symbol": req.symbol,
                "qty": req.qty,
                "price": price,
                "value": round(price * req.qty, 2),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        }
    except Exception as e:
        logger.error(f"下單失敗: {e}")
        raise HTTPException(status_code=500, detail=f"下單失敗: {str(e)}")


@router.get("/trades")
async def get_trades():
    """交易歷史"""
    try:
        db = get_db()
        rows = (
            db.query(TradeHistory)
            .order_by(TradeHistory.timestamp.desc())
            .limit(100)
            .all()
        )
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "action": r.action,
                "price": r.price,
                "amount": r.amount,
                "model_confidence": r.model_confidence,
                "pnl": r.pnl,
            }
            for r in rows
        ]
    except Exception:
        # DB 可能未初始化，返回空列表
        return []


# ─── 技術指標計算 ───

def _calc_ma(data: List[float], period: int) -> List[Optional[float]]:
    result = []
    for i in range(len(data)):
        if i < period - 1:
            result.append(None)
        else:
            result.append(round(sum(data[i - period + 1:i + 1]) / period, 2))
    return result


def _calc_rsi(data: List[float], period: int = 14) -> List[Optional[float]]:
    result = [None] * period
    gains = []
    losses = []

    for i in range(1, len(data)):
        diff = data[i] - data[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    if len(gains) < period:
        return [None] * len(data)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(round(100 - 100 / (1 + rs), 2))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100 - 100 / (1 + rs), 2))

    # 補齊長度
    while len(result) < len(data):
        result.insert(0, None)

    return result


def _calc_macd(data: List[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """計算 MACD"""
    def ema(values, period):
        k = 2 / (period + 1)
        result = [values[0]]
        for v in values[1:]:
            result.append(result[-1] * (1 - k) + v * k)
        return result

    if len(data) < slow:
        return [None] * len(data), [None] * len(data), [None] * len(data)

    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)
    macd_line = [round(f - s, 4) for f, s in zip(ema_fast, ema_slow)]

    if len(macd_line) < signal:
        return macd_line, [None] * len(data), [None] * len(data)

    signal_line_raw = ema(macd_line[slow - 1:], signal)
    signal_line = [None] * (slow - 1) + [round(s, 4) for s in signal_line_raw]
    histogram = [round(m - s, 4) if s is not None else None for m, s in zip(macd_line, signal_line)]

    return macd_line[:len(data)], signal_line[:len(data)], histogram[:len(data)]


def _calc_max_drawdown(equity_curve: List[float]) -> float:
    peak = equity_curve[0]
    max_dd = 0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        if dd > max_dd:
            max_dd = dd
    return max_dd
