"""
訂單管理模組：向後相容包裝，底層改由 ExecutionService 處理多交易所執行。
"""

from typing import Optional, Dict
from sqlalchemy.orm import Session

from execution.execution_service import ExecutionService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class OrderManager:
    def __init__(self, config: Dict, db_session: Session):
        self.config = config
        self.session = db_session
        self.execution_service = ExecutionService(config, db_session=db_session)
        self.dry_run = not self.execution_service.is_live_enabled()
        self.confidence = 0.0

    @property
    def exchange(self):
        return self.execution_service.get_adapter().exchange

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: float,
        price: Optional[float] = None,
        stop_loss_pct: float = 0.03,
        venue: Optional[str] = None,
        reason: Optional[str] = None,
        reduce_only: bool = False,
    ) -> Optional[Dict]:
        try:
            payload = self.execution_service.submit_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                qty=qty,
                price=price,
                venue=venue,
                reduce_only=reduce_only,
                reason=reason or f"stop_loss_pct={stop_loss_pct:.4f}",
                model_confidence=self.confidence,
            )
            order = payload.get("order") or {}
            return {
                "id": order.get("id"),
                "status": order.get("status"),
                "symbol": order.get("symbol"),
                "side": order.get("side"),
                "type": order.get("type"),
                "amount": order.get("qty"),
                "price": order.get("price"),
                "timestamp": order.get("timestamp"),
                "dry_run": payload.get("dry_run", True),
                "venue": payload.get("venue"),
            }
        except Exception as exc:
            logger.exception(f"下單失敗: {exc}")
            return None
