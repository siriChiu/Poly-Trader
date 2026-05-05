from types import SimpleNamespace

from database.models import OrderLifecycleEvent, TradeHistory
from execution.account_sync import AccountSyncService
from execution.config import resolve_trading_config
from execution.execution_service import ExecutionService
from execution.exchanges.okx_adapter import OKXAdapter


class DummySession:
    def __init__(self):
        self.added = []
        self.committed = False
        self.rolled_back = False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class FakeAdapter:
    venue = "okx"

    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.exchange = None

    def health(self):
        return {"venue": self.venue, "dry_run": self.dry_run, "connected": False, "credentials_configured": False}

    def fetch_balance(self):
        return {"venue": self.venue, "currency": "USDT", "free": 321.0, "total": 500.0, "dry_run": self.dry_run}

    def fetch_positions(self):
        return {"venue": self.venue, "positions": [{"symbol": "BTC/USDT", "size": 0.01}], "dry_run": self.dry_run}

    def fetch_open_orders(self, symbol=None):
        return {"venue": self.venue, "orders": [{"symbol": symbol or "BTC/USDT"}], "dry_run": self.dry_run}

    def market_rules(self, symbol):
        return {"symbol": symbol, "min_qty": 0.001, "min_cost": 10.0, "amount_precision": 3, "price_precision": 2}

    def place_order(self, request):
        from execution.exchanges.base import ExchangeOrderResult
        return ExchangeOrderResult(
            venue=self.venue, symbol=request.symbol, side=request.side, order_type=request.order_type,
            qty=request.qty, price=request.price, status="closed", order_id="ord-1", client_order_id=request.client_order_id,
            timestamp=1234567890, raw={}, dry_run=self.dry_run
        )


def test_resolve_trading_config_merges_execution_and_legacy_fields():
    cfg = resolve_trading_config({
        "trading": {"dry_run": False, "venue": "okx"},
        "okx": {"api_key": "okx-key", "api_secret": "s", "passphrase": "p"},
        "execution": {"mode": "live_canary", "venue": "okx", "venues": {"okx": {"enabled": True}}},
    })
    assert cfg["venue"] == "okx"
    assert cfg["mode"] == "live_canary"
    assert cfg["dry_run"] is True
    assert "binance" not in cfg["venues"]
    assert cfg["venues"]["okx"]["passphrase"] == "p"


def test_execution_service_submit_order_records_trade(monkeypatch):
    session = DummySession()
    service = ExecutionService({"execution": {"mode": "paper", "venue": "okx"}}, db_session=session)
    fake = FakeAdapter(dry_run=True)
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: fake)
    payload = service.submit_order(symbol="BTC/USDT", side="buy", order_type="market", qty=0.01, price=62000.0, reason="test")
    assert payload["success"] is True
    assert payload["venue"] == "okx"
    assert payload["order"]["id"] == "ord-1"
    assert payload["normalization"]["normalized"]["qty"] == 0.01
    assert payload["order"]["normalization"]["contract"]["min_cost"] == 10.0
    assert payload["guardrails"]["last_order"]["normalization"]["normalized"]["qty"] == 0.01
    assert payload["guardrails"]["last_order"]["order_id"] == "ord-1"
    assert payload["guardrails"]["last_order"]["client_order_id"] == payload["order"]["client_order_id"]
    assert session.committed is True
    trades = [obj for obj in session.added if isinstance(obj, TradeHistory)]
    lifecycle_events = [obj for obj in session.added if isinstance(obj, OrderLifecycleEvent)]
    assert len(trades) == 1
    assert trades[0].exchange == "okx"
    assert trades[0].symbol == "BTC/USDT"
    assert [event.event_type for event in lifecycle_events] == ["validation_passed", "venue_ack", "trade_history_persisted"]
    assert lifecycle_events[-1].order_id == "ord-1"


def test_account_sync_service_returns_combined_snapshot(monkeypatch):
    sync = AccountSyncService({"execution": {"mode": "paper", "venue": "okx"}})
    monkeypatch.setattr(sync.service, "get_adapter", lambda venue=None: FakeAdapter(dry_run=True))
    snapshot = sync.snapshot(symbol="BTCUSDT")
    assert snapshot["venue"] == "okx"
    assert snapshot["balance"]["free"] == 321.0
    assert snapshot["positions"][0]["symbol"] == "BTC/USDT"
    assert snapshot["open_orders"][0]["symbol"] == "BTC/USDT"
    assert snapshot["requested_symbol"] == "BTCUSDT"
    assert snapshot["normalized_symbol"] == "BTC/USDT"
    assert snapshot["position_count"] == 1
    assert snapshot["open_order_count"] == 1
    assert snapshot["degraded"] is False
    assert snapshot["captured_at"].endswith("Z")
    assert "核對目前場館" in snapshot["operator_message"]


def test_execution_service_normalizes_legacy_symbol_format(monkeypatch):
    session = DummySession()
    service = ExecutionService({"execution": {"mode": "paper", "venue": "okx"}}, db_session=session)
    captured = {}

    class CaptureAdapter(FakeAdapter):
        def place_order(self, request):
            captured["symbol"] = request.symbol
            return super().place_order(request)

    monkeypatch.setattr(service, "get_adapter", lambda venue=None: CaptureAdapter(dry_run=True))
    service.submit_order(symbol="BTCUSDT", side="buy", order_type="market", qty=0.01)
    assert captured["symbol"] == "BTC/USDT"


def test_account_sync_service_degrades_when_adapter_raises(monkeypatch):
    sync = AccountSyncService({"execution": {"mode": "live", "venue": "okx", "enable_live_trading": True}})

    class BrokenAdapter(FakeAdapter):
        venue = "okx"
        def fetch_balance(self):
            raise RuntimeError("broken")

    monkeypatch.setattr(sync.service, "get_adapter", lambda venue=None: BrokenAdapter(dry_run=False))
    snapshot = sync.snapshot(symbol="BTCUSDT")
    assert snapshot["health"]["error"] == "broken"
    assert snapshot["positions"] == []
    assert snapshot["open_orders"] == []
    assert snapshot["degraded"] is True
    assert snapshot["requested_symbol"] == "BTCUSDT"
    assert snapshot["normalized_symbol"] == "BTC/USDT"
    assert snapshot["position_count"] == 0
    assert snapshot["open_order_count"] == 0
    assert snapshot["captured_at"].endswith("Z")
    assert "不可視為已驗證" in snapshot["operator_message"]
    assert "symbol 正規化" in snapshot["recovery_hint"]


def test_execution_service_rejects_disabled_venue():
    service = ExecutionService({"execution": {"mode": "paper", "venue": "okx", "venues": {"okx": {"enabled": False}}}})
    try:
        service.get_adapter("okx")
    except ValueError as exc:
        assert "disabled" in str(exc)
    else:
        raise AssertionError("disabled venue should raise")


def test_execution_service_rejects_below_min_notional(monkeypatch):
    service = ExecutionService({"execution": {"mode": "paper", "venue": "okx"}}, db_session=DummySession())
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: FakeAdapter(dry_run=True))
    try:
        service.submit_order(symbol="BTC/USDT", side="buy", order_type="limit", qty=0.001, price=1000.0)
    except Exception as exc:
        assert hasattr(exc, "to_payload")
        payload = exc.to_payload()
        assert payload["code"] == "min_notional"
    else:
        raise AssertionError("should reject low notional order")


def test_execution_service_guardrail_summary_includes_last_reject(monkeypatch):
    service = ExecutionService({"execution": {"mode": "paper", "venue": "okx"}}, db_session=DummySession())
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: FakeAdapter(dry_run=True))
    try:
        service.submit_order(symbol="BTC/USDT", side="buy", order_type="limit", qty=0.001, price=1000.0)
    except Exception:
        pass
    summary = service.execution_summary()
    assert summary["guardrails"]["last_reject"]["code"] == "min_notional"


def test_execution_service_records_rejected_lifecycle_event(monkeypatch):
    session = DummySession()
    service = ExecutionService({"execution": {"mode": "paper", "venue": "okx"}}, db_session=session)
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: FakeAdapter(dry_run=True))
    try:
        service.submit_order(symbol="BTC/USDT", side="buy", order_type="limit", qty=0.001, price=1000.0)
    except Exception:
        pass
    lifecycle_events = [obj for obj in session.added if isinstance(obj, OrderLifecycleEvent)]
    assert [event.event_type for event in lifecycle_events] == ["rejected"]
    assert lifecycle_events[0].order_state == "rejected"


class FakeOKXStepAdapter(FakeAdapter):
    venue = "okx"

    def market_rules(self, symbol):
        return {
            "symbol": symbol,
            "min_qty": 0.001,
            "min_cost": 10.0,
            "amount_precision": 6,
            "price_precision": 2,
            "step_size": "0.001",
            "tick_size": "0.10",
        }


class FakeOKXTickAdapter(FakeAdapter):
    venue = "okx"

    def market_rules(self, symbol):
        return {
            "symbol": symbol,
            "min_qty": 0.001,
            "min_cost": 10.0,
            "amount_precision": 4,
            "price_precision": 1,
            "step_size": "0.0001",
            "tick_size": "0.1",
        }


def test_execution_service_rejects_qty_step_size_mismatch_for_okx(monkeypatch):
    service = ExecutionService({"execution": {"mode": "paper", "venue": "okx"}}, db_session=DummySession())
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: FakeOKXStepAdapter(dry_run=True))

    try:
        service.submit_order(symbol="BTC/USDT", side="buy", order_type="limit", qty=0.0015, price=62000.1)
    except Exception as exc:
        payload = exc.to_payload()
        assert payload["code"] == "qty_step_mismatch"
        assert payload["context"]["raw_value"] == 0.0015
        assert payload["context"]["adjusted_value"] == 0.001
        assert payload["context"]["step_size"] == "0.001"
    else:
        raise AssertionError("expected qty step-size reject")


def test_execution_service_rejects_price_tick_size_mismatch_for_okx(monkeypatch):
    service = ExecutionService({"execution": {"mode": "paper", "venue": "okx"}}, db_session=DummySession())
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: FakeOKXTickAdapter(dry_run=True))

    try:
        service.submit_order(symbol="BTC/USDT", side="buy", order_type="limit", qty=0.01, price=62000.15)
    except Exception as exc:
        payload = exc.to_payload()
        assert payload["code"] == "price_tick_mismatch"
        assert payload["context"]["raw_value"] == 62000.15
        assert payload["context"]["adjusted_value"] == 62000.1
        assert payload["context"]["step_size"] == "0.1"
    else:
        raise AssertionError("expected price tick-size reject")



def test_resolve_trading_config_records_unsupported_legacy_venue_without_enabling_it():
    cfg = resolve_trading_config({"execution": {"mode": "paper", "venue": "binance", "venues": {"binance": {"enabled": True}}}})
    assert cfg["venue"] == "okx"
    assert cfg["unsupported_venue_requested"] == "binance"
    assert set(cfg["venues"]) == {"okx"}


def test_execution_service_rejects_configured_unsupported_legacy_venue_before_adapter_build():
    service = ExecutionService({"execution": {"mode": "paper", "venue": "binance"}}, db_session=DummySession())
    try:
        service.get_adapter()
    except ValueError as exc:
        assert "Unsupported execution venue requested: binance" in str(exc)
        assert "Only OKX execution API is supported" in str(exc)
    else:
        raise AssertionError("unsupported configured venue should be fail-closed")


def test_execution_service_rejects_explicit_unsupported_venue_adapter():
    service = ExecutionService({"execution": {"mode": "paper", "venue": "okx"}}, db_session=DummySession())
    try:
        service.get_adapter("binance")
    except ValueError as exc:
        assert "Only OKX execution API is supported" in str(exc)
    else:
        raise AssertionError("unsupported venue should be unsupported")

def test_okx_market_rules_include_step_and_tick_sizes(monkeypatch):
    market = {
        "base": "BTC",
        "quote": "USDT",
        "limits": {"amount": {"min": 0.001}, "cost": {"min": 10.0}},
        "precision": {"amount": 4, "price": 1},
        "info": {"lotSz": "0.0001", "tickSz": "0.1"},
    }

    class FakeExchange:
        def __init__(self, _config):
            self.markets = {"BTC/USDT": market}

        def market(self, symbol):
            return self.markets[symbol]

    monkeypatch.setattr("execution.exchanges.okx_adapter.ccxt.okx", FakeExchange)
    adapter = OKXAdapter({}, dry_run=True)
    rules = adapter.market_rules("BTC/USDT")
    assert rules["step_size"] == "0.0001"
    assert rules["tick_size"] == "0.1"
    assert rules["price_contract"]["tick_size"] == "0.1"
