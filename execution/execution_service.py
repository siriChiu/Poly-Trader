from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from typing import Any, Dict, Optional

from sqlalchemy import func

from database.models import OrderLifecycleEvent, TradeHistory
from execution.config import resolve_trading_config
from execution.exchanges.base import BaseExchangeAdapter, ExchangeOrderResult, OrderRequest
from execution.exchanges.binance_adapter import BinanceAdapter
from execution.exchanges.okx_adapter import OKXAdapter
from execution.metadata_smoke import _build_contract_summary
from utils.logger import setup_logger

logger = setup_logger(__name__)

_EXECUTION_RUNTIME: Dict[str, Any] = {
    "consecutive_failures": 0,
    "last_failure": None,
    "last_reject": None,
    "last_order": None,
}


class ExecutionRejectError(RuntimeError):
    def __init__(self, code: str, message: str, *, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context or {}

    def to_payload(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "context": self.context}


class ExecutionService:
    def __init__(self, config: Dict[str, Any], db_session=None):
        self.config = config or {}
        self.db_session = db_session
        self.execution_cfg = resolve_trading_config(self.config)
        self._adapters: Dict[str, BaseExchangeAdapter] = {}

    def _build_adapter(self, venue: str) -> BaseExchangeAdapter:
        venue_key = str(venue or self.execution_cfg.get("venue") or "binance").lower()
        venue_cfg = (self.execution_cfg.get("venues") or {}).get(venue_key) or {}
        if not venue_cfg.get("enabled", False):
            raise ValueError(f"Venue '{venue_key}' is disabled in config")
        adapter_dry_run = self.execution_cfg.get("mode") != "live" or not self.execution_cfg.get("enable_live_trading")
        if venue_key == "binance":
            return BinanceAdapter(venue_cfg, dry_run=adapter_dry_run)
        if venue_key == "okx":
            return OKXAdapter(venue_cfg, dry_run=adapter_dry_run)
        raise ValueError(f"Unsupported venue: {venue}")

    def get_adapter(self, venue: Optional[str] = None) -> BaseExchangeAdapter:
        venue_key = str(venue or self.execution_cfg.get("venue") or "binance").lower()
        adapter = self._adapters.get(venue_key)
        if adapter is None:
            adapter = self._build_adapter(venue_key)
            self._adapters[venue_key] = adapter
        return adapter

    def is_live_enabled(self) -> bool:
        return self.execution_cfg.get("mode") == "live" and bool(self.execution_cfg.get("enable_live_trading"))

    def _normalize_symbol(self, symbol: str) -> str:
        value = str(symbol or "").strip()
        if not value or "/" in value:
            return value
        common_quotes = ("USDT", "USDC", "BUSD", "BTC", "ETH")
        for quote in common_quotes:
            if value.endswith(quote) and len(value) > len(quote):
                base = value[:-len(quote)]
                return f"{base}/{quote}"
        return value

    def venue_default_type(self, venue: Optional[str] = None) -> str:
        venue_key = str(venue or self.execution_cfg.get("venue") or "binance").lower()
        venue_cfg = (self.execution_cfg.get("venues") or {}).get(venue_key) or {}
        return str(venue_cfg.get("default_type") or "spot").lower()

    def get_account_balance(self, venue: Optional[str] = None) -> Optional[float]:
        adapter = self.get_adapter(venue)
        snapshot = adapter.fetch_balance()
        free = snapshot.get("free")
        total = snapshot.get("total")
        return float(free if free is not None else total) if (free is not None or total is not None) else None

    def _current_daily_loss_ratio(self, venue: Optional[str] = None) -> Optional[float]:
        if self.db_session is None:
            return None
        try:
            now = datetime.now(timezone.utc)
            start = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
            venue_name = str(venue or self.execution_cfg.get("venue") or "binance")
            total_pnl = self.db_session.query(func.coalesce(func.sum(TradeHistory.pnl), 0.0)).filter(
                TradeHistory.timestamp >= start,
                TradeHistory.exchange == venue_name,
                TradeHistory.pnl.isnot(None),
            ).scalar() or 0.0
            balance = self.get_account_balance(venue)
            if not balance or balance <= 0:
                return None
            return abs(float(total_pnl)) / float(balance) if float(total_pnl) < 0 else 0.0
        except Exception:
            return None

    def _round_down(self, value: float, decimals: Optional[int]) -> float:
        if decimals is None:
            return float(value)
        factor = 10 ** int(decimals)
        return math.floor(float(value) * factor) / factor

    def _floor_to_step(self, value: float, step: Optional[Any]) -> float:
        if step in (None, 0, 0.0, "0", "0.0"):
            return float(value)
        try:
            dec_value = Decimal(str(value))
            dec_step = Decimal(str(step))
            if dec_step <= 0:
                return float(value)
            quantized = (dec_value / dec_step).to_integral_value(rounding=ROUND_DOWN) * dec_step
            return float(quantized)
        except (InvalidOperation, ValueError, TypeError, ZeroDivisionError):
            return float(value)

    def _is_close(self, left: Optional[float], right: Optional[float], tol: float = 1e-12) -> bool:
        if left is None or right is None:
            return left is right
        return abs(float(left) - float(right)) <= tol

    def _format_adjustment_context(
        self,
        *,
        field: str,
        raw_value: Optional[float],
        adjusted_value: Optional[float],
        step_size: Optional[Any],
        precision: Optional[Any],
        rules: Dict[str, Any],
    ) -> Dict[str, Any]:
        delta = None
        if raw_value is not None and adjusted_value is not None:
            delta = float(raw_value) - float(adjusted_value)
        return {
            "field": field,
            "raw_value": raw_value,
            "adjusted_value": adjusted_value,
            "delta": delta,
            "step_size": step_size,
            "precision": precision,
            "rules": rules,
        }

    def _adjust_order_value(
        self,
        *,
        value: Optional[float],
        step_size: Optional[Any],
        precision: Optional[Any],
    ) -> Optional[float]:
        if value is None:
            return None
        adjusted = self._floor_to_step(value, step_size)
        if step_size in (None, 0, 0.0, "0", "0.0"):
            adjusted = self._round_down(adjusted, precision)
        return adjusted

    def _build_normalization_summary(
        self,
        *,
        request: OrderRequest,
        validated_request: OrderRequest,
        rules: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "requested": {
                "symbol": request.symbol,
                "qty": request.qty,
                "price": request.price,
                "side": request.side,
                "type": request.order_type,
            },
            "normalized": {
                "symbol": validated_request.symbol,
                "qty": validated_request.qty,
                "price": validated_request.price,
                "side": validated_request.side,
                "type": validated_request.order_type,
                "qty_changed": not self._is_close(request.qty, validated_request.qty),
                "price_changed": not self._is_close(request.price, validated_request.price),
            },
            "contract": _build_contract_summary(rules),
        }

    def guardrail_status(self, venue: Optional[str] = None) -> Dict[str, Any]:
        daily_loss_ratio = self._current_daily_loss_ratio(venue)
        max_daily_loss_pct = float(self.execution_cfg.get("max_daily_loss_pct") or 0.0)
        max_failures = int(self.execution_cfg.get("max_consecutive_failures") or 0)
        halted_by_loss = daily_loss_ratio is not None and max_daily_loss_pct > 0 and daily_loss_ratio >= max_daily_loss_pct
        halted_by_failures = max_failures > 0 and int(_EXECUTION_RUNTIME.get("consecutive_failures") or 0) >= max_failures
        return {
            "kill_switch": bool(self.execution_cfg.get("kill_switch")),
            "max_daily_loss_pct": max_daily_loss_pct,
            "daily_loss_ratio": daily_loss_ratio,
            "daily_loss_halt": halted_by_loss,
            "max_consecutive_failures": max_failures,
            "consecutive_failures": int(_EXECUTION_RUNTIME.get("consecutive_failures") or 0),
            "failure_halt": halted_by_failures,
            "last_failure": _EXECUTION_RUNTIME.get("last_failure"),
            "last_reject": _EXECUTION_RUNTIME.get("last_reject"),
            "last_order": _EXECUTION_RUNTIME.get("last_order"),
        }

    def execution_summary(self) -> Dict[str, Any]:
        try:
            adapter = self.get_adapter()
            health = adapter.health()
            venue = adapter.venue
        except Exception as exc:
            health = {"connected": False, "credentials_configured": False, "error": str(exc)}
            venue = str(self.execution_cfg.get("venue") or "binance")
        return {
            "mode": self.execution_cfg.get("mode"),
            "venue": venue,
            "live_enabled": self.is_live_enabled(),
            "kill_switch": bool(self.execution_cfg.get("kill_switch")),
            "health": health,
            "guardrails": self.guardrail_status(venue),
        }

    def _validate_order_request(self, adapter: BaseExchangeAdapter, request: OrderRequest) -> tuple[OrderRequest, Dict[str, Any]]:
        guardrails = self.guardrail_status(adapter.venue)
        if guardrails["kill_switch"]:
            raise ExecutionRejectError("kill_switch", "Kill switch is active; live execution is blocked", context=guardrails)
        if guardrails["daily_loss_halt"]:
            raise ExecutionRejectError("daily_loss_halt", "Daily loss halt triggered", context=guardrails)
        if guardrails["failure_halt"]:
            raise ExecutionRejectError("failure_halt", "Consecutive failure halt triggered", context=guardrails)

        rules = adapter.market_rules(request.symbol)
        qty_step = rules.get("step_size")
        price_tick = rules.get("tick_size")
        amount_precision = rules.get("amount_precision")
        price_precision = rules.get("price_precision")

        adjusted_qty = self._adjust_order_value(value=request.qty, step_size=qty_step, precision=amount_precision)
        adjusted_price = self._adjust_order_value(value=request.price, step_size=price_tick, precision=price_precision)
        notional = adjusted_qty * adjusted_price if adjusted_price is not None else None

        min_qty = rules.get("min_qty")
        min_cost = rules.get("min_cost")
        if adjusted_qty <= 0:
            raise ExecutionRejectError(
                "qty_invalid",
                "Quantity becomes zero after market-rule normalization",
                context=self._format_adjustment_context(
                    field="qty",
                    raw_value=request.qty,
                    adjusted_value=adjusted_qty,
                    step_size=qty_step,
                    precision=amount_precision,
                    rules=rules,
                ),
            )
        if not self._is_close(request.qty, adjusted_qty):
            reject_code = "qty_step_mismatch" if qty_step not in (None, 0, 0.0, "0", "0.0") else "qty_precision_mismatch"
            reject_message = (
                "Quantity does not satisfy exchange step-size contract"
                if reject_code == "qty_step_mismatch"
                else "Quantity has more precision than the venue allows"
            )
            raise ExecutionRejectError(
                reject_code,
                reject_message,
                context=self._format_adjustment_context(
                    field="qty",
                    raw_value=request.qty,
                    adjusted_value=adjusted_qty,
                    step_size=qty_step,
                    precision=amount_precision,
                    rules=rules,
                ),
            )
        if request.price is not None and not self._is_close(request.price, adjusted_price):
            reject_code = "price_tick_mismatch" if price_tick not in (None, 0, 0.0, "0", "0.0") else "price_precision_mismatch"
            reject_message = (
                "Price does not satisfy exchange tick-size contract"
                if reject_code == "price_tick_mismatch"
                else "Price has more precision than the venue allows"
            )
            raise ExecutionRejectError(
                reject_code,
                reject_message,
                context=self._format_adjustment_context(
                    field="price",
                    raw_value=request.price,
                    adjusted_value=adjusted_price,
                    step_size=price_tick,
                    precision=price_precision,
                    rules=rules,
                ),
            )
        if min_qty is not None and adjusted_qty < float(min_qty):
            raise ExecutionRejectError("min_qty", "Quantity is below exchange minimum", context={"qty": adjusted_qty, "min_qty": min_qty, "rules": rules})
        if min_cost is not None and notional is not None and notional < float(min_cost):
            raise ExecutionRejectError("min_notional", "Order notional is below exchange minimum", context={"notional": notional, "min_cost": min_cost, "rules": rules})

        return (
            OrderRequest(
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                qty=adjusted_qty,
                price=adjusted_price,
                reduce_only=request.reduce_only,
                client_order_id=request.client_order_id,
                params=request.params,
            ),
            rules,
        )

    def _record_lifecycle_event(
        self,
        *,
        exchange: Optional[str],
        symbol: Optional[str],
        order_id: Optional[str],
        client_order_id: Optional[str],
        event_type: str,
        order_state: Optional[str],
        source: str,
        summary: str,
        payload: Optional[Dict[str, Any]] = None,
        is_dry_run: Optional[bool] = None,
    ) -> None:
        if self.db_session is None:
            return
        try:
            event = OrderLifecycleEvent(
                exchange=exchange,
                symbol=symbol,
                order_id=order_id,
                client_order_id=client_order_id,
                event_type=event_type,
                order_state=order_state,
                source=source,
                summary=summary,
                payload_json=json.dumps(payload or {}, ensure_ascii=False, default=str),
                is_dry_run=1 if is_dry_run else 0 if is_dry_run is not None else None,
            )
            self.db_session.add(event)
            self.db_session.commit()
        except Exception as exc:
            self.db_session.rollback()
            logger.error(f"訂單 lifecycle event 保存失敗: {exc}")

    def submit_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        qty: float,
        price: Optional[float] = None,
        venue: Optional[str] = None,
        reduce_only: bool = False,
        reason: Optional[str] = None,
        model_confidence: float = 0.0,
        client_order_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        adapter = self.get_adapter(venue)
        request = OrderRequest(
            symbol=self._normalize_symbol(symbol),
            side=side.lower(),
            order_type=order_type.lower(),
            qty=float(qty),
            price=float(price) if price is not None else None,
            reduce_only=bool(reduce_only),
            client_order_id=client_order_id or f"poly_{adapter.venue}_{int(time.time())}",
            params=params or {},
        )
        normalization: Optional[Dict[str, Any]] = None
        try:
            validated_request, rules = self._validate_order_request(adapter, request)
            normalization = self._build_normalization_summary(
                request=request,
                validated_request=validated_request,
                rules=rules,
            )
            self._record_lifecycle_event(
                exchange=adapter.venue,
                symbol=validated_request.symbol,
                order_id=None,
                client_order_id=validated_request.client_order_id,
                event_type="validation_passed",
                order_state="validated",
                source="execution_service",
                summary="Order passed execution guardrails and venue normalization.",
                payload={
                    "reason": reason,
                    "normalization": normalization,
                    "reduce_only": validated_request.reduce_only,
                },
                is_dry_run=not self.is_live_enabled(),
            )
            result = adapter.place_order(validated_request)
            _EXECUTION_RUNTIME["consecutive_failures"] = 0
            _EXECUTION_RUNTIME["last_order"] = {
                "venue": result.venue,
                "symbol": result.symbol,
                "side": result.side,
                "qty": result.qty,
                "price": result.price,
                "status": result.status,
                "timestamp": result.timestamp,
                "order_id": result.order_id,
                "client_order_id": result.client_order_id,
                "normalization": normalization,
            }
            self._record_lifecycle_event(
                exchange=result.venue,
                symbol=result.symbol,
                order_id=result.order_id,
                client_order_id=result.client_order_id,
                event_type="venue_ack",
                order_state=result.status,
                source="exchange_adapter",
                summary="Venue acknowledged the order request.",
                payload={
                    "timestamp": result.timestamp,
                    "side": result.side,
                    "qty": result.qty,
                    "price": result.price,
                    "order_type": result.order_type,
                    "raw": result.raw,
                },
                is_dry_run=result.dry_run,
            )
            self._record_trade(result, reason=reason, model_confidence=model_confidence)
            return {
                "success": True,
                "dry_run": result.dry_run,
                "venue": result.venue,
                "mode": self.execution_cfg.get("mode"),
                "guardrails": self.guardrail_status(result.venue),
                "normalization": normalization,
                "order": {
                    "id": result.order_id,
                    "client_order_id": result.client_order_id,
                    "status": result.status,
                    "symbol": result.symbol,
                    "side": result.side,
                    "type": result.order_type,
                    "qty": result.qty,
                    "price": result.price,
                    "timestamp": result.timestamp,
                    "mode": "dry_run" if result.dry_run else "live",
                    "normalization": normalization,
                },
            }
        except ExecutionRejectError as exc:
            _EXECUTION_RUNTIME["last_reject"] = {**exc.to_payload(), "timestamp": datetime.utcnow().isoformat() + "Z"}
            self._record_lifecycle_event(
                exchange=adapter.venue,
                symbol=request.symbol,
                order_id=None,
                client_order_id=request.client_order_id,
                event_type="rejected",
                order_state="rejected",
                source="execution_guardrail",
                summary=exc.message,
                payload={
                    "reject": exc.to_payload(),
                    "request": {
                        "symbol": request.symbol,
                        "side": request.side,
                        "order_type": request.order_type,
                        "qty": request.qty,
                        "price": request.price,
                    },
                },
                is_dry_run=not self.is_live_enabled(),
            )
            raise
        except Exception as exc:
            _EXECUTION_RUNTIME["consecutive_failures"] = int(_EXECUTION_RUNTIME.get("consecutive_failures") or 0) + 1
            _EXECUTION_RUNTIME["last_failure"] = {"message": str(exc), "timestamp": datetime.utcnow().isoformat() + "Z"}
            self._record_lifecycle_event(
                exchange=adapter.venue,
                symbol=request.symbol,
                order_id=None,
                client_order_id=request.client_order_id,
                event_type="runtime_failure",
                order_state="failed",
                source="execution_service",
                summary=str(exc),
                payload={
                    "request": {
                        "symbol": request.symbol,
                        "side": request.side,
                        "order_type": request.order_type,
                        "qty": request.qty,
                        "price": request.price,
                    },
                    "normalization": normalization,
                },
                is_dry_run=not self.is_live_enabled(),
            )
            raise

    def _record_trade(self, result: ExchangeOrderResult, *, reason: Optional[str], model_confidence: float) -> None:
        if self.db_session is None:
            return
        try:
            trade = TradeHistory(
                action=result.side.upper(),
                price=float(result.price or 0.0),
                amount=float(result.qty),
                model_confidence=float(model_confidence or 0.0),
                pnl=None,
                reason=reason,
                regime_label=None,
                symbol=result.symbol,
                exchange=result.venue,
                order_id=result.order_id,
                client_order_id=result.client_order_id,
                order_status=result.status,
                is_dry_run=1 if result.dry_run else 0,
            )
            self.db_session.add(trade)
            self.db_session.commit()
            self._record_lifecycle_event(
                exchange=result.venue,
                symbol=result.symbol,
                order_id=result.order_id,
                client_order_id=result.client_order_id,
                event_type="trade_history_persisted",
                order_state=result.status,
                source="trade_history",
                summary="Order lifecycle persisted into trade_history.",
                payload={
                    "reason": reason,
                    "model_confidence": float(model_confidence or 0.0),
                    "action": trade.action,
                    "trade_timestamp": trade.timestamp.isoformat() if trade.timestamp else None,
                },
                is_dry_run=result.dry_run,
            )
        except Exception as exc:
            self.db_session.rollback()
            logger.error(f"交易記錄保存失敗: {exc}")
            self._record_lifecycle_event(
                exchange=result.venue,
                symbol=result.symbol,
                order_id=result.order_id,
                client_order_id=result.client_order_id,
                event_type="trade_history_persist_failed",
                order_state=result.status,
                source="trade_history",
                summary="Failed to persist order lifecycle into trade_history.",
                payload={"error": str(exc), "reason": reason},
                is_dry_run=result.dry_run,
            )
