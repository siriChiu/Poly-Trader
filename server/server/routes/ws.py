"""
WebSocket 路由：即時推送五感分數 + 建議
"""

import asyncio
import json
from datetime import datetime
from typing import Set, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from server.senses import get_engine
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

# 已連接的 WebSocket 客戶端
_connected_clients: Set[WebSocket] = set()


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


async def _data_push_loop():
    """後台任務：定期計算五感分數並廣播。"""
    while True:
        try:
            if _connected_clients:
                engine = get_engine()
                scores = engine.calculate_all_scores()
                rec = engine.generate_advice(scores)

                await _broadcast({
                    "type": "senses_update",
                    "data": {
                        "scores": scores,
                        "recommendation": rec,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    },
                })
        except Exception as e:
            logger.error(f"數據推送循環錯誤: {e}")

        await asyncio.sleep(30)  # 每 30 秒推送


@router.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    """即時數據推送 WebSocket"""
    await ws.accept()
    _connected_clients.add(ws)
    logger.info(f"WebSocket 客戶端連接，當前連接數: {len(_connected_clients)}")

    # 啟動後台推送任務
    if not hasattr(_data_push_loop, "_task") or _data_push_loop._task.done():
        _data_push_loop._task = asyncio.create_task(_data_push_loop())

    # 發送連接確認
    engine = get_engine()
    scores = engine.calculate_all_scores()
    rec = engine.generate_advice(scores)

    await ws.send_text(json.dumps({
        "type": "connected",
        "data": {
            "message": "已連接到 Poly-Trader 即時數據流",
            "scores": scores,
            "recommendation": rec,
        },
    }, default=str))

    try:
        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)

            if data.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

            elif data.get("type") == "refresh":
                # 客戶端請求立即刷新
                engine = get_engine()
                scores = engine.calculate_all_scores()
                rec = engine.generate_advice(scores)
                await ws.send_text(json.dumps({
                    "type": "senses_update",
                    "data": {
                        "scores": scores,
                        "recommendation": rec,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    },
                }, default=str))

    except WebSocketDisconnect:
        _connected_clients.discard(ws)
        logger.info(f"WebSocket 客戶端斷開，剩餘連接數: {len(_connected_clients)}")
    except Exception as e:
        _connected_clients.discard(ws)
        logger.error(f"WebSocket 錯誤: {e}")
