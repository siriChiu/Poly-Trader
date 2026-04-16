from __future__ import annotations

from typing import Any, Dict, Optional

from execution.config import resolve_trading_config
from execution.execution_service import ExecutionService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AccountSyncService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.execution_cfg = resolve_trading_config(self.config)
        self.service = ExecutionService(self.config)

    def snapshot(self, venue: Optional[str] = None, symbol: Optional[str] = None) -> Dict[str, Any]:
        try:
            adapter = self.service.get_adapter(venue)
            normalized_symbol = self.service._normalize_symbol(symbol) if symbol else None
            balance = adapter.fetch_balance()
            positions = adapter.fetch_positions()
            orders = adapter.fetch_open_orders(normalized_symbol)
            return {
                "venue": adapter.venue,
                "mode": self.execution_cfg.get("mode"),
                "dry_run": adapter.dry_run,
                "balance": balance,
                "positions": positions.get("positions") or [],
                "open_orders": orders.get("orders") or [],
                "health": adapter.health(),
            }
        except Exception as exc:
            logger.warning(f"account snapshot failed: {exc}")
            return {
                "venue": venue or self.execution_cfg.get("venue"),
                "mode": self.execution_cfg.get("mode"),
                "dry_run": self.execution_cfg.get("dry_run", True),
                "balance": None,
                "positions": [],
                "open_orders": [],
                "health": {"error": str(exc)},
            }
