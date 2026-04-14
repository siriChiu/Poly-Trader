
# WebSocket 路由：即時推送多特徵數據、交易信號


import asyncio
import json
from typing import Set, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from model.predictor import DummyPredictor
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


class WsManager:
    """管理 WebSocket 連接與後台推送"""

    def __init__(self):
        self.clients: Set[WebSocket] = set()
        self._task: Optional[asyncio.Task] = None
        self._predictor = DummyPredictor()

    async def broadcast(self, message: Dict[str, Any]):
        if not self.clients:
            return
        data = json.dumps(message, default=str)
        to_remove = set()
        for ws in self.clients:
            try:
                await ws.send_text(data)
            except Exception:
                to_remove.add(ws)
        self.clients -= to_remove

    def get_latest_raw(self) -> Dict[str, Any]:
        """讀取最新一筆 raw data"""
        try:
            from database.models import RawMarketData
            from server.dependencies import get_db
            db = get_db()
            row = db.query(RawMarketData).order_by(RawMarketData.timestamp.desc()).first()
            if not row:
                return {}
            return {
                "close_price": row.close_price,
                "funding_rate": row.funding_rate,
                "fear_greed_index": row.fear_greed_index,
                "eye_dist": row.eye_dist,
                "ear_prob": row.ear_prob,
                "stablecoin_mcap": row.stablecoin_mcap,
            }
        except Exception:
            return {}

    async def data_push_loop(self):
        """後台任務：定期收集多特徵數據並廣播"""
        while True:
            try:
                if self.clients:
                    from server.dependencies import get_db, get_config
                    from data_ingestion.collector import run_collection_and_save
                    from feature_engine.preprocessor import run_preprocessor
                    from model.predictor import predict as run_predict

                    db = get_db()
                    cfg = get_config()
                    symbol = cfg.get("trading", {}).get("symbol", "BTCUSDT")

                    success = run_collection_and_save(db, symbol)
                    if success:
                        raw = self.get_latest_raw()
                        if raw:
                            await self.broadcast({"type": "senses_update", "data": raw})

                        features = run_preprocessor(db, symbol)
                        if features:
                            result = run_predict(db, predictor=self._predictor)
                            if result:
                                await self.broadcast({
                                    "type": "senses_update",
                                    "data": {
                                        "scores": self._features_to_scores(features),
                                        "recommendation": {
                                            "confidence": result["confidence"],
                                            "signal": result["signal"],
                                            "timestamp": result["timestamp"],
                                        },
                                    },
                                })
            except Exception as e:
                logger.error(f"推送循環錯誤: {e}")

            await asyncio.sleep(60)

    def _features_to_scores(self, features: Dict) -> Dict[str, float]:
        """特徵轉 0~1 分數 — 使用與 features_engine.py 一致的 ECDF 歸一化"""
        from server.features_engine import normalize_feature

        # Correct mapping: DB column names match the feature keys now
        all_feats = {
            "eye": normalize_feature(features.get("feat_eye"), "feat_eye"),
            "ear": normalize_feature(features.get("feat_ear"), "feat_ear"),
            "nose": normalize_feature(features.get("feat_nose"), "feat_nose"),
            "tongue": normalize_feature(features.get("feat_tongue"), "feat_tongue"),
            "body": normalize_feature(features.get("feat_body"), "feat_body"),
            "pulse": normalize_feature(features.get("feat_pulse"), "feat_pulse"),
            "aura": normalize_feature(features.get("feat_aura"), "feat_aura"),
            "mind": normalize_feature(features.get("feat_mind"), "feat_mind"),
            "vix": normalize_feature(features.get("feat_vix"), "feat_vix"),
            "dxy": normalize_feature(features.get("feat_dxy"), "feat_dxy"),
            "rsi14": normalize_feature(features.get("feat_rsi14"), "feat_rsi14"),
            "macd_hist": normalize_feature(features.get("feat_macd_hist"), "feat_macd_hist"),
            "atr_pct": normalize_feature(features.get("feat_atr_pct"), "feat_atr_pct"),
            "vwap_dev": normalize_feature(features.get("feat_vwap_dev"), "feat_vwap_dev"),
            "bb_pct_b": normalize_feature(features.get("feat_bb_pct_b"), "feat_bb_pct_b"),
            "4h_bias50": normalize_feature(features.get("feat_4h_bias50"), "feat_4h_bias50"),
            "4h_bias20": normalize_feature(features.get("feat_4h_bias20"), "feat_4h_bias20"),
            "4h_rsi14": normalize_feature(features.get("feat_4h_rsi14"), "feat_4h_rsi14"),
            "4h_macd_hist": normalize_feature(features.get("feat_4h_macd_hist"), "feat_4h_macd_hist"),
            "4h_bb_pct_b": normalize_feature(features.get("feat_4h_bb_pct_b"), "feat_4h_bb_pct_b"),
            "4h_ma_order": normalize_feature(features.get("feat_4h_ma_order"), "feat_4h_ma_order"),
            "4h_dist_sl": normalize_feature(features.get("feat_4h_dist_swing_low"), "feat_4h_dist_swing_low"),
        }
        return all_feats


# 全局實例
ws_manager = WsManager()


@router.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await ws.accept()
    ws_manager.clients.add(ws)
    logger.info(f"WebSocket 連接，當前: {len(ws_manager.clients)}")

    # 後台推送任務
    if ws_manager._task is None or ws_manager._task.done():
        ws_manager._task = asyncio.create_task(ws_manager.data_push_loop())

    try:
        # 發送當前狀態
        await ws.send_text(json.dumps({
            "type": "connected",
            "data": {"message": "已連接"},
        }))

        # 發送最新數據
        raw = ws_manager.get_latest_raw()
        if raw:
            await ws.send_text(json.dumps({"type": "senses_update", "data": raw}, default=str))

        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)
            if data.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        logger.info("WebSocket 客戶端已中斷連線")
    except Exception as e:
        logger.error(f"WS 錯誤: {e}")
    finally:
        ws_manager.clients.discard(ws)
        logger.info(f"WebSocket 斷開，剩餘: {len(ws_manager.clients)}")
