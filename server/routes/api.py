"""
REST API 路由
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from server.dependencies import (
    get_db, get_config, get_order_manager,
    is_automation_enabled, set_automation_enabled,
)
from data_ingestion.collector import collect_all_senses, run_collection_and_save
from feature_engine.preprocessor import run_preprocessor, load_latest_raw_data, compute_features_from_raw
from model.predictor import predict as run_predict, DummyPredictor
from analysis.sense_validator import validate_senses
from backtesting.engine import run_backtest
from database.models import TradeHistory, FeaturesNormalized, RawMarketData
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

# 全局共享 predictor 實例
_predictor = DummyPredictor()


# ─── Request / Response Models ───

class TradeRequest(BaseModel):
    side: str  # "buy" or "sell"
    symbol: str = "BTCUSDT"
    qty: float


class PredictResponse(BaseModel):
    timestamp: str
    confidence: float
    signal: str
    features: Dict[str, Any]


# ─── Endpoints ───

@router.get("/status")
async def get_status():
    """系統狀態"""
    db = get_db()
    cfg = get_config()
    raw_count = db.query(RawMarketData).count()
    feat_count = db.query(FeaturesNormalized).count()
    trade_count = db.query(TradeHistory).count()

    return {
        "automation": is_automation_enabled(),
        "dry_run": cfg.get("trading", {}).get("dry_run", True),
        "symbol": cfg.get("trading", {}).get("symbol", "BTCUSDT"),
        "confidence_threshold": cfg.get("trading", {}).get("confidence_threshold", 0.7),
        "data_counts": {
            "raw_market_data": raw_count,
            "features_normalized": feat_count,
            "trade_history": trade_count,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/senses/latest")
async def get_latest_senses():
    """最新一筆五感原始數據"""
    db = get_db()
    row = (
        db.query(RawMarketData)
        .order_by(RawMarketData.timestamp.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="尚無五感數據")

    return {
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "symbol": row.symbol,
        "close_price": row.close_price,
        "funding_rate": row.funding_rate,
        "fear_greed_index": row.fear_greed_index,
        "stablecoin_mcap": row.stablecoin_mcap,
        "polymarket_prob": row.polymarket_prob,
        "eye_dist": row.eye_dist,
        "ear_prob": row.ear_prob,
    }


@router.get("/features")
async def get_features(days: int = Query(default=7, ge=1, le=365)):
    """特徵歷史數據"""
    db = get_db()
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(FeaturesNormalized)
        .filter(FeaturesNormalized.timestamp >= since)
        .order_by(FeaturesNormalized.timestamp.asc())
        .all()
    )
    return [
        {
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "feat_eye_dist": r.feat_eye_dist,
            "feat_ear_zscore": r.feat_ear_zscore,
            "feat_nose_sigmoid": r.feat_nose_sigmoid,
            "feat_tongue_pct": r.feat_tongue_pct,
            "feat_body_roc": r.feat_body_roc,
        }
        for r in rows
    ]


@router.get("/trades")
async def get_trades():
    """交易歷史"""
    db = get_db()
    rows = (
        db.query(TradeHistory)
        .order_by(TradeHistory.timestamp.desc())
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


@router.post("/predict", response_model=PredictResponse)
async def trigger_predict():
    """觸發一次預測"""
    db = get_db()
    result = run_predict(db, predictor=_predictor)
    if not result:
        raise HTTPException(status_code=500, detail="預測失敗：無可用特徵數據")
    return PredictResponse(
        timestamp=result["timestamp"],
        confidence=result["confidence"],
        signal=result["signal"],
        features=result["features"],
    )


@router.post("/trade")
async def manual_trade(req: TradeRequest):
    """手動下單"""
    om = get_order_manager()
    cfg = get_config()
    db = get_db()

    # 取得最新價格
    latest_raw = (
        db.query(RawMarketData)
        .order_by(RawMarketData.timestamp.desc())
        .first()
    )
    price = latest_raw.close_price if latest_raw and latest_raw.close_price else 0.0

    result = om.place_order(
        symbol=req.symbol,
        side=req.side.lower(),
        order_type="market",
        qty=req.qty,
        price=price,
    )
    if not result:
        raise HTTPException(status_code=500, detail="下單失敗")

    return {
        "success": True,
        "order": result,
    }


@router.post("/automation/toggle")
async def toggle_automation():
    """切換自動/手動模式"""
    new_state = not is_automation_enabled()
    set_automation_enabled(new_state)
    return {
        "automation": new_state,
        "message": f"已切換至{'自動' if new_state else '手動'}模式",
    }


@router.get("/backtest")
async def trigger_backtest(
    days: int = Query(default=30, ge=1, le=365),
    initial_capital: float = Query(default=10000.0),
    confidence_threshold: float = Query(default=0.7, ge=0.0, le=1.0),
):
    """觸發回測"""
    db = get_db()
    cfg = get_config()
    symbol = cfg.get("trading", {}).get("symbol", "BTCUSDT")
    max_pos = cfg.get("trading", {}).get("max_position_ratio", 0.05)

    since = datetime.utcnow() - timedelta(days=days)
    results = run_backtest(
        session=db,
        start_date=since,
        initial_capital=initial_capital,
        confidence_threshold=confidence_threshold,
        max_position_ratio=max_pos,
        symbol=symbol,
    )
    if not results:
        raise HTTPException(status_code=500, detail="回測失敗：數據不足")

    equity_df = results["equity_curve"]
    trades_df = results["trade_log"]

    return {
        "final_equity": results["final_equity"],
        "initial_capital": initial_capital,
        "total_trades": len(trades_df) if trades_df is not None else 0,
        "equity_curve": [
            {"timestamp": str(idx), "equity": row["equity"]}
            for idx, row in equity_df.iterrows()
        ] if equity_df is not None and not equity_df.empty else [],
        "trades": [
            {
                "timestamp": str(row.get("timestamp", "")),
                "action": row.get("action", ""),
                "price": row.get("price", 0),
                "amount": row.get("amount", 0),
                "confidence": row.get("confidence"),
                "pnl": row.get("pnl"),
            }
            for _, row in trades_df.iterrows()
        ] if trades_df is not None and not trades_df.empty else [],
    }


@router.get("/validation")
async def get_validation():
    """感官有效性驗證"""
    db = get_db()
    cfg = get_config()
    symbol = cfg.get("trading", {}).get("symbol", "BTCUSDT")

    result = validate_senses(db, symbol)
    return result
