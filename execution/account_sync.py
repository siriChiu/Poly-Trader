from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone

from execution.config import resolve_trading_config
from execution.execution_service import ExecutionService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AccountSyncService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.execution_cfg = resolve_trading_config(self.config)
        self.service = ExecutionService(self.config)

    def _snapshot_meta(self, *, requested_symbol: Optional[str], normalized_symbol: Optional[str]) -> Dict[str, Any]:
        return {
            "requested_symbol": requested_symbol,
            "normalized_symbol": normalized_symbol,
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def snapshot(self, venue: Optional[str] = None, symbol: Optional[str] = None) -> Dict[str, Any]:
        normalized_symbol = self.service._normalize_symbol(symbol) if symbol else None
        meta = self._snapshot_meta(requested_symbol=symbol, normalized_symbol=normalized_symbol)
        try:
            adapter = self.service.get_adapter(venue)
            balance = adapter.fetch_balance()
            positions_payload = adapter.fetch_positions()
            orders_payload = adapter.fetch_open_orders(normalized_symbol)
            positions = positions_payload.get("positions") or []
            open_orders = orders_payload.get("orders") or []
            return {
                "venue": adapter.venue,
                "mode": self.execution_cfg.get("mode"),
                "dry_run": adapter.dry_run,
                "balance": balance,
                "positions": positions,
                "open_orders": open_orders,
                "position_count": len(positions),
                "open_order_count": len(open_orders),
                "health": adapter.health(),
                "degraded": False,
                "operator_message": "account snapshot 已刷新，可直接用來核對目前 venue 的餘額 / 倉位 / 掛單真相。",
                "recovery_hint": None,
                **meta,
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
                "position_count": 0,
                "open_order_count": 0,
                "health": {"error": str(exc)},
                "degraded": True,
                "operator_message": "account snapshot 退化為不完整狀態；目前 UI 顯示的倉位 / 掛單真相不可視為已驗證。",
                "recovery_hint": "請檢查交易所憑證、網路連線、symbol 正規化與 adapter 健康狀態後再重試。",
                "error": str(exc),
                **meta,
            }
