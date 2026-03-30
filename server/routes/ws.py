"""
WebSocket 路由：即時推送五感數據、交易信號、交易結果
"""

import asyncio
import json
from datetime import datetime
from typing import Set, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from server.dependencies import get_db, get_config, is_automation_enabled
from data_ingestion.collector import collect_all_senses, run_collection_and_save
from feature_engine.preprocessor import run_preprocessor
from model.predictor import predict as run_predict, DummyPredictor
from database.models import RawMarketData
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

# 已連接的 WebSocket 客戶端
_connected_clients: Set[WebSocket] = set()
_predictor = DummyPredictor()


async def _broadcast(message: Dict[str, Any]):
    """向所有已連接的客戶端廣播消息。"""
    if not _connected_clients:
        return
    data = json.dumps(message, default=str)
    disconnected = set()
    for ws in _connected_clients:
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.add(ws)
    _connected_clients -= disconnected


def _get_latest_raw() -> Dict[str, Any]:
    """讀取最新一筆 raw data 用於推送。"""
    db = get_db()
    row = (
        db.query(RawMarketData)
        .order_by(RawMarketData.timestamp.desc())
        .first()
    )
    if not row:
        return {}
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


async def _data_push_loop():
    """後台任務：定期收集五感數據並廣播。"""
    while True:
        try:
            if _connected_clients:
                db = get_db()
                cfg = get_config()
                symbol = cfg.get("trading", {}).get("symbol", "BTCUSDT")

                # 收集五感數據
                success = run_collection_and_save(db, symbol)
                if success:
                    raw = _get_latest_raw()
                    if raw:
                        await _broadcast({
                            "type": "senses",
                            "data": raw,
                        })

                    # 特徵工程
                    features = run_preprocessor(db, symbol)
                    if features:
                        # 預測
                        result = run_predict(db, predictor=_predictor)
                        if result:
                            await _broadcast({
                                "type": "signal",
                                "data": {
                                    "timestamp": result["timestamp"],
                                    "confidence": result["confidence"],
                                    "signal": result["signal"],
                                },
                            })

                            # 自動模式下執行交易
                            if is_automation_enabled() and result["confidence"] > cfg.get("trading", {}).get("confidence_threshold", 0.7):
                                # 觸發自動交易信號推送（實際下單由主循環控制）
                                await _broadcast({
                                    "type": "auto_signal",
                                    "data": {
                                        "timestamp": result["timestamp"],
                                        "confidence": result["confidence"],
                                        "signal": result["signal"],
                                        "message": "自動模式：信號觸發，準備執行",
                                    },
                                })

        except Exception as e:
            logger.error(f"數據推送循環錯誤: {e}")

        # 每 60 秒推送一次
        await asyncio.sleep(60)


@router.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    """即時數據推送 WebSocket"""
    await ws.accept()
    _connected_clients.add(ws)
    logger.info(f"WebSocket 客戶端連接，當前連接數: {len(_connected_clients)}")

    # 啟動後台推送任務（僅首次有客戶端時啟動）
    if not hasattr(_data_push_loop, "_task") or _data_push_loop._task.done():
        _data_push_loop._task = asyncio.create_task(_data_push_loop())

    # 發送當前系統狀態
    await ws.send_text(json.dumps({
        "type": "connected",
        "data": {
            "automation": is_automation_enabled(),
            "message": "已連接到 Poly-Trader 即時數據流",
        },
    }))

    # 發送最新一筆數據
    raw = _get_latest_raw()
    if raw:
        await ws.send_text(json.dumps({
            "type": "senses",
            "data": raw,
        }, default=str))

    try:
        while True:
            # 接收客戶端消息（如手動下單指令等）
            msg = await ws.receive_text()
            data = json.loads(msg)

            if data.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        _connected_clients.discard(ws)
        logger.info(f"WebSocket 客戶端斷開，剩餘連接數: {len(_connected_clients)}")
    except Exception as e:
        _connected_clients.discard(ws)
        logger.error(f"WebSocket 錯誤: {e}")
