from __future__ import annotations

import time
from typing import Any, Dict, Optional

import ccxt

from execution.exchanges.base import BaseExchangeAdapter, ExchangeOrderResult, OrderRequest
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _okx_symbol_info(market: Dict[str, Any]) -> Dict[str, Any]:
    return (market.get("info") or {}) if isinstance(market, dict) else {}


def _normalize_okx_symbol(symbol: str) -> str:
    value = str(symbol or "").strip().upper()
    if not value or "/" in value:
        return value
    for quote in ("USDT", "USDC", "BTC", "ETH"):
        if value.endswith(quote) and len(value) > len(quote):
            return f"{value[:-len(quote)]}/{quote}"
    return value


class OKXAdapter(BaseExchangeAdapter):
    venue = "okx"

    def credentials_configured(self) -> bool:
        return bool(self.config.get("api_key") and self.config.get("api_secret") and self.config.get("passphrase"))

    def connect(self) -> bool:
        if self.exchange is not None:
            return True
        if not self.credentials_configured():
            return False
        try:
            self.exchange = ccxt.okx(
                {
                    "apiKey": self.config.get("api_key"),
                    "secret": self.config.get("api_secret"),
                    "password": self.config.get("passphrase"),
                    "enableRateLimit": True,
                    "options": {"defaultType": self.config.get("default_type", "spot")},
                }
            )
            self.exchange.load_markets()
            return True
        except Exception as exc:
            logger.error(f"OKX 連線失敗: {exc}")
            self.exchange = None
            return False

    def _require_exchange(self):
        if not self.connect():
            raise RuntimeError("OKX adapter is not connected")
        return self.exchange

    def fetch_balance(self) -> Dict[str, Any]:
        if self.dry_run and not self.credentials_configured():
            return {"venue": self.venue, "currency": "USDT", "free": None, "total": None, "dry_run": True}
        exchange = self._require_exchange()
        raw = exchange.fetch_balance()
        usdt = raw.get("USDT") or {}
        return {
            "venue": self.venue,
            "currency": "USDT",
            "free": usdt.get("free"),
            "used": usdt.get("used"),
            "total": usdt.get("total"),
            "dry_run": self.dry_run,
            "raw": raw,
        }

    def fetch_positions(self) -> Dict[str, Any]:
        if self.dry_run:
            return {"venue": self.venue, "positions": [], "dry_run": True}
        exchange = self._require_exchange()
        try:
            positions = exchange.fetch_positions()
        except Exception:
            positions = []
        return {"venue": self.venue, "positions": positions, "dry_run": self.dry_run}

    def fetch_open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        normalized_symbol = _normalize_okx_symbol(symbol) if symbol else None
        if self.dry_run:
            return {"venue": self.venue, "orders": [], "dry_run": True}
        exchange = self._require_exchange()
        orders = exchange.fetch_open_orders(normalized_symbol)
        return {"venue": self.venue, "orders": orders, "dry_run": self.dry_run}

    def market_rules(self, symbol: str) -> Dict[str, Any]:
        normalized_symbol = _normalize_okx_symbol(symbol)
        exchange = self._require_exchange() if self.credentials_configured() else ccxt.okx({"enableRateLimit": True})
        if not getattr(exchange, "markets", None):
            exchange.load_markets()
        market = exchange.market(normalized_symbol)
        limits = market.get("limits") or {}
        precision = market.get("precision") or {}
        info = _okx_symbol_info(market)
        step_size = info.get("lotSz") or info.get("minSz")
        tick_size = info.get("tickSz")
        return {
            "symbol": normalized_symbol,
            "base": market.get("base"),
            "quote": market.get("quote"),
            "min_qty": ((limits.get("amount") or {}).get("min")),
            "min_cost": ((limits.get("cost") or {}).get("min")),
            "amount_precision": precision.get("amount"),
            "price_precision": precision.get("price"),
            "step_size": step_size,
            "tick_size": tick_size,
            "qty_contract": {
                "step_size": step_size,
                "min_qty": ((limits.get("amount") or {}).get("min")),
                "precision": precision.get("amount"),
            },
            "price_contract": {
                "tick_size": tick_size,
                "precision": precision.get("price"),
            },
        }

    def place_order(self, request: OrderRequest) -> ExchangeOrderResult:
        normalized_symbol = _normalize_okx_symbol(request.symbol)
        if self.dry_run:
            return ExchangeOrderResult(
                venue=self.venue,
                symbol=normalized_symbol,
                side=request.side,
                order_type=request.order_type,
                qty=request.qty,
                price=request.price,
                status="closed",
                order_id=f"dry_run_{self.venue}_{int(time.time())}",
                client_order_id=request.client_order_id,
                timestamp=time.time() * 1000,
                raw={"params": request.params, "reduce_only": request.reduce_only},
                dry_run=True,
            )
        exchange = self._require_exchange()
        params = dict(request.params or {})
        if request.client_order_id:
            params.setdefault("clOrdId", request.client_order_id)
        if request.reduce_only:
            params.setdefault("reduceOnly", True)
        order_type = request.order_type.lower()
        if order_type == "limit":
            if request.price is None:
                raise ValueError("OKX limit order requires price")
            order = exchange.create_limit_order(normalized_symbol, request.side, request.qty, request.price, params)
        elif order_type == "market":
            order = exchange.create_market_order(normalized_symbol, request.side, request.qty, params)
        else:
            raise ValueError(f"Unsupported order type: {request.order_type}")
        return ExchangeOrderResult(
            venue=self.venue,
            symbol=normalized_symbol,
            side=request.side,
            order_type=request.order_type,
            qty=request.qty,
            price=order.get("price") or request.price,
            status=order.get("status") or "open",
            order_id=str(order.get("id")),
            client_order_id=order.get("clientOrderId") or order.get("clOrdId") or request.client_order_id,
            timestamp=order.get("timestamp"),
            raw=order,
            dry_run=False,
        )
