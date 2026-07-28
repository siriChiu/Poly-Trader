from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from typing import Any, Dict, Mapping, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from database.models import ExecutionPermitConsumption, OrderLifecycleEvent, TradeHistory
from execution.config import resolve_trading_config
from execution.exchanges.base import BaseExchangeAdapter, ExchangeOrderResult, OrderRequest
from execution.exchanges.okx_adapter import OKXAdapter
from execution.metadata_smoke import _build_contract_summary
from execution.permit import verify_execution_permit_signature
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

    def _venue_key(self, venue: Optional[str] = None) -> str:
        return str(venue or self.execution_cfg.get("venue") or "okx").strip().lower() or "okx"

    def _build_adapter(self, venue: str) -> BaseExchangeAdapter:
        unsupported_requested = self.execution_cfg.get("unsupported_venue_requested")
        if unsupported_requested:
            raise ValueError(
                f"Unsupported execution venue requested: {unsupported_requested}. "
                "Only OKX execution API is supported"
            )
        venue_key = self._venue_key(venue)
        if venue_key != "okx":
            raise ValueError(f"Unsupported venue: {venue_key}. Only OKX execution API is supported")
        venue_cfg = (self.execution_cfg.get("venues") or {}).get(venue_key) or {}
        if not venue_cfg.get("enabled", False):
            raise ValueError(f"Venue '{venue_key}' is disabled in config")
        adapter_dry_run = self.execution_cfg.get("mode") != "live" or not self.execution_cfg.get("enable_live_trading")
        return OKXAdapter(venue_cfg, dry_run=adapter_dry_run)

    def get_adapter(self, venue: Optional[str] = None) -> BaseExchangeAdapter:
        venue_key = self._venue_key(venue)
        adapter = self._adapters.get(venue_key)
        if adapter is None:
            adapter = self._build_adapter(venue_key)
            self._adapters[venue_key] = adapter
        return adapter

    def is_live_enabled(self) -> bool:
        return self.execution_cfg.get("mode") == "live" and bool(self.execution_cfg.get("enable_live_trading"))

    def _normalize_symbol(self, symbol: str) -> str:
        value = str(symbol or "").strip().upper()
        if not value:
            return value
        if "/" in value:
            return value
        common_quotes = ("USDT", "USDC", "BUSD", "BTC", "ETH")
        if "-" in value:
            base, sep, quote = value.partition("-")
            if sep and base and quote in common_quotes:
                return f"{base}/{quote}"
        for quote in common_quotes:
            if value.endswith(quote) and len(value) > len(quote):
                base = value[:-len(quote)].rstrip("-_")
                if base:
                    return f"{base}/{quote}"
        return value

    def _live_canary_policy(self) -> Dict[str, Any]:
        policy = self.execution_cfg.get("live_canary")
        return policy if isinstance(policy, dict) else {}

    def _live_canary_allowed_symbols(self) -> set[str]:
        policy = self._live_canary_policy()
        symbols = policy.get("allowed_symbols") or []
        return {self._normalize_symbol(str(symbol)).upper() for symbol in symbols if str(symbol or "").strip()}

    def _live_canary_max_qty_for_symbol(self, symbol: str) -> Optional[float]:
        policy = self._live_canary_policy()
        normalized_symbol = self._normalize_symbol(symbol).upper()
        by_symbol = policy.get("max_base_qty_by_symbol") or {}
        if isinstance(by_symbol, dict):
            for key, value in by_symbol.items():
                if self._normalize_symbol(str(key)).upper() == normalized_symbol:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        return None
        fallback = policy.get("max_base_qty")
        if fallback is None:
            return None
        try:
            return float(fallback)
        except (TypeError, ValueError):
            return None

    def _enforce_live_canary_policy(self, request: OrderRequest) -> None:
        """Require explicit tiny-canary limits before any live buy/add order.

        This does not make a blocked strategy deployable.  It only prevents a
        misconfigured live mode from turning into full-size risk-on execution
        once the higher-level current-live gates allow a buy request through.
        """
        if not self.is_live_enabled() or request.reduce_only or request.side.lower() != "buy":
            return

        policy = self._live_canary_policy()
        if not bool(policy.get("enabled", False)):
            raise ExecutionRejectError(
                "live_canary_policy_required",
                "Live buy/add execution requires execution.live_canary.enabled with explicit tiny-size limits",
                context={
                    "mode": self.execution_cfg.get("mode"),
                    "enable_live_trading": self.execution_cfg.get("enable_live_trading"),
                    "required_config": "execution.live_canary.enabled=true + allowed_symbols + max_base_qty_by_symbol",
                },
            )

        allowed_symbols = self._live_canary_allowed_symbols()
        normalized_symbol = self._normalize_symbol(request.symbol).upper()
        if allowed_symbols and normalized_symbol not in allowed_symbols:
            raise ExecutionRejectError(
                "live_canary_symbol_not_allowed",
                "Live canary order symbol is not in the explicit allowlist",
                context={"symbol": normalized_symbol, "allowed_symbols": sorted(allowed_symbols)},
            )

        max_qty = self._live_canary_max_qty_for_symbol(request.symbol)
        if max_qty is None or max_qty <= 0:
            raise ExecutionRejectError(
                "live_canary_qty_cap_required",
                "Live buy/add execution requires an explicit max base quantity cap for the symbol",
                context={"symbol": normalized_symbol, "configured_max_qty": max_qty},
            )
        if float(request.qty) > float(max_qty):
            raise ExecutionRejectError(
                "live_canary_qty_cap_exceeded",
                "Live canary order quantity exceeds the configured max base quantity cap",
                context={"symbol": normalized_symbol, "qty": float(request.qty), "max_base_qty": float(max_qty)},
            )

    def _parse_permit_datetime(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _authorize_live_submission(
        self,
        adapter: BaseExchangeAdapter,
        request: OrderRequest,
        *,
        execution_permit: Optional[Mapping[str, Any]],
        run_id: Optional[str],
        profile_id: Optional[str],
        strategy_hash: Optional[str],
        reference_price: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        if getattr(adapter, "dry_run", None) is True:
            return None

        raw_trading_cfg = self.config.get("trading")
        trading_cfg: Dict[str, Any] = raw_trading_cfg if isinstance(raw_trading_cfg, dict) else {}
        dual_live_enabled = bool(
            self.execution_cfg.get("mode") == "live"
            and self.execution_cfg.get("enable_live_trading") is True
            and trading_cfg.get("dry_run") is False
        )
        if not dual_live_enabled:
            raise ExecutionRejectError(
                "live_config_not_enabled",
                "A non-dry adapter requires execution.mode=live, enable_live_trading=true, and trading.dry_run=false",
                context={
                    "mode": self.execution_cfg.get("mode"),
                    "enable_live_trading": self.execution_cfg.get("enable_live_trading"),
                    "trading_dry_run": trading_cfg.get("dry_run"),
                    "adapter_dry_run": getattr(adapter, "dry_run", None),
                },
            )
        if not isinstance(execution_permit, Mapping):
            raise ExecutionRejectError(
                "execution_permit_required",
                "Live execution requires a signed, short-lived, single-use execution permit",
            )
        try:
            signature_valid, claims = verify_execution_permit_signature(execution_permit)
        except ValueError as exc:
            raise ExecutionRejectError(
                "execution_permit_secret_unavailable",
                "Live execution permit verification secret is unavailable or too short",
            ) from exc
        if not signature_valid:
            raise ExecutionRejectError(
                "execution_permit_signature_invalid",
                "Execution permit signature is invalid",
            )

        now = datetime.now(timezone.utc)
        issued_at = self._parse_permit_datetime(claims.get("issued_at"))
        expires_at = self._parse_permit_datetime(claims.get("expires_at"))
        if expires_at is not None and expires_at <= now:
            raise ExecutionRejectError("execution_permit_expired", "Execution permit has expired")
        if (
            claims.get("version") != 1
            or issued_at is None
            or expires_at is None
            or issued_at > now + timedelta(seconds=30)
            or expires_at <= issued_at
            or (expires_at - issued_at).total_seconds() > 300
        ):
            raise ExecutionRejectError(
                "execution_permit_window_invalid",
                "Execution permit must use version 1 and a valid window no longer than five minutes",
            )

        normalized_run_id = str(run_id or "").strip()
        normalized_profile_id = str(profile_id or "").strip()
        normalized_strategy_hash = str(strategy_hash or "").strip()
        nonce = str(claims.get("nonce") or "").strip()
        if not normalized_run_id or not normalized_profile_id or not normalized_strategy_hash:
            raise ExecutionRejectError(
                "execution_permit_context_required",
                "Live execution requires run_id, profile_id, and strategy_hash context",
            )
        if len(nonce) < 16 or len(nonce) > 128:
            raise ExecutionRejectError("execution_permit_nonce_invalid", "Execution permit nonce is missing or invalid")

        expected_scope = {
            "run_id": normalized_run_id,
            "profile_id": normalized_profile_id,
            "strategy_hash": normalized_strategy_hash,
            "venue": str(adapter.venue or "").strip().lower(),
            "symbol": self._normalize_symbol(request.symbol).upper(),
            "side": str(request.side or "").strip().lower(),
            "order_type": str(request.order_type or "").strip().lower(),
            "reduce_only": bool(request.reduce_only),
        }
        permit_scope = {
            "run_id": str(claims.get("run_id") or "").strip(),
            "profile_id": str(claims.get("profile_id") or "").strip(),
            "strategy_hash": str(claims.get("strategy_hash") or "").strip(),
            "venue": str(claims.get("venue") or "").strip().lower(),
            "symbol": self._normalize_symbol(str(claims.get("symbol") or "")).upper(),
            "side": str(claims.get("side") or "").strip().lower(),
            "order_type": str(claims.get("order_type") or "").strip().lower(),
            "reduce_only": claims.get("reduce_only") is True,
        }
        mismatches = sorted(key for key, value in expected_scope.items() if permit_scope.get(key) != value)
        if mismatches:
            raise ExecutionRejectError(
                "execution_permit_scope_mismatch",
                "Execution permit does not match the exact order and strategy scope",
                context={"mismatched_fields": mismatches},
            )

        try:
            max_qty_value = claims.get("max_qty")
            max_notional_value = claims.get("max_notional")
            price_value = request.price if request.price is not None else reference_price
            if max_qty_value is None or max_notional_value is None or price_value is None:
                raise TypeError("missing permit limit")
            max_qty = float(max_qty_value)
            max_notional = float(max_notional_value)
            effective_price = float(price_value)
        except (TypeError, ValueError):
            raise ExecutionRejectError(
                "execution_permit_limits_invalid",
                "Execution permit requires numeric max_qty/max_notional and a positive order/reference price",
            )
        notional = float(request.qty) * effective_price
        if max_qty <= 0 or max_notional <= 0 or effective_price <= 0:
            raise ExecutionRejectError(
                "execution_permit_limits_invalid",
                "Execution permit limits and order/reference price must be positive",
            )
        if float(request.qty) > max_qty + 1e-12 or notional > max_notional + 1e-9:
            raise ExecutionRejectError(
                "execution_permit_limit_exceeded",
                "Order exceeds the execution permit quantity or notional limit",
                context={
                    "qty": float(request.qty),
                    "max_qty": max_qty,
                    "notional": notional,
                    "max_notional": max_notional,
                },
            )

        authorized = dict(claims)
        authorized.update(
            {
                "nonce": nonce,
                "signature": str(execution_permit.get("signature") or ""),
                "expires_at_parsed": expires_at,
                "effective_notional": notional,
            }
        )
        return authorized

    def _consume_execution_permit(self, claims: Mapping[str, Any]) -> None:
        if self.db_session is None or not hasattr(self.db_session, "add"):
            raise ExecutionRejectError(
                "execution_permit_store_unavailable",
                "A durable database session is required to consume a live execution permit",
            )
        try:
            self.db_session.add(
                ExecutionPermitConsumption(
                    nonce=str(claims["nonce"]),
                    signature=str(claims["signature"]),
                    run_id=str(claims["run_id"]),
                    profile_id=str(claims["profile_id"]),
                    strategy_hash=str(claims["strategy_hash"]),
                    venue=str(claims["venue"]),
                    symbol=self._normalize_symbol(str(claims["symbol"])),
                    side=str(claims["side"]),
                    max_qty=float(claims["max_qty"]),
                    max_notional=float(claims["max_notional"]),
                    expires_at=claims["expires_at_parsed"].replace(tzinfo=None),
                )
            )
            self.db_session.commit()
        except IntegrityError as exc:
            self.db_session.rollback()
            raise ExecutionRejectError(
                "execution_permit_replayed",
                "Execution permit nonce has already been consumed",
            ) from exc
        except ExecutionRejectError:
            raise
        except Exception as exc:
            self.db_session.rollback()
            raise ExecutionRejectError(
                "execution_permit_store_unavailable",
                "Execution permit could not be durably consumed",
            ) from exc

    def venue_default_type(self, venue: Optional[str] = None) -> str:
        venue_key = self._venue_key(venue)
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
            venue_name = self._venue_key(venue)
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
            venue = str(self.execution_cfg.get("venue") or "okx")
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
        if request.price is not None and request.order_type.lower() != "market" and not self._is_close(request.price, adjusted_price):
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
        reference_price: Optional[float] = None,
        run_id: Optional[str] = None,
        profile_id: Optional[str] = None,
        strategy_hash: Optional[str] = None,
        execution_permit: Optional[Mapping[str, Any]] = None,
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
        authorized_permit: Optional[Dict[str, Any]] = None
        try:
            validated_request, rules = self._validate_order_request(adapter, request)
            self._enforce_live_canary_policy(validated_request)
            authorized_permit = self._authorize_live_submission(
                adapter,
                validated_request,
                execution_permit=execution_permit,
                run_id=run_id,
                profile_id=profile_id,
                strategy_hash=strategy_hash,
                reference_price=reference_price,
            )
            normalization = self._build_normalization_summary(
                request=request,
                validated_request=validated_request,
                rules=rules,
            )
            if authorized_permit is not None:
                self._consume_execution_permit(authorized_permit)
                normalization["execution_permit"] = {
                    "nonce": authorized_permit["nonce"],
                    "run_id": authorized_permit["run_id"],
                    "profile_id": authorized_permit["profile_id"],
                    "strategy_hash": authorized_permit["strategy_hash"],
                    "expires_at": authorized_permit["expires_at"],
                    "effective_notional": authorized_permit["effective_notional"],
                    "consumed": True,
                }
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
