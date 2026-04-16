from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    qty: float
    price: Optional[float] = None
    reduce_only: bool = False
    client_order_id: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExchangeOrderResult:
    venue: str
    symbol: str
    side: str
    order_type: str
    qty: float
    price: Optional[float]
    status: str
    order_id: str
    client_order_id: Optional[str] = None
    timestamp: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False


class BaseExchangeAdapter(ABC):
    venue: str = "unknown"

    def __init__(self, config: Dict[str, Any], *, dry_run: bool = True):
        self.config = config or {}
        self.dry_run = bool(dry_run)
        self.exchange = None

    @abstractmethod
    def connect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def credentials_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch_balance(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch_positions(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch_open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def market_rules(self, symbol: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def place_order(self, request: OrderRequest) -> ExchangeOrderResult:
        raise NotImplementedError

    def health(self) -> Dict[str, Any]:
        return {
            "venue": self.venue,
            "dry_run": self.dry_run,
            "connected": self.exchange is not None,
            "credentials_configured": self.credentials_configured(),
        }
