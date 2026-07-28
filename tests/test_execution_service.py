from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from database.models import OrderLifecycleEvent, TradeHistory, init_db
from execution.account_sync import AccountSyncService
from execution.config import resolve_cost_aware_edge_config, resolve_trading_config
from execution.execution_service import ExecutionRejectError, ExecutionService
from execution.exchanges.base import OrderRequest
from execution.exchanges.okx_adapter import OKXAdapter
from execution.permit import sign_execution_permit


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
    assert cfg["cost_aware_edge"] == {
        "taker_fee_bps": 5.0,
        "spread_bps": 3.0,
        "slippage_bps": 2.0,
        "volatility_buffer_bps": 5.0,
        "drawdown_buffer_bps": 0.0,
    }


def test_resolve_cost_aware_edge_config_merges_defaults_legacy_and_execution_overrides():
    config = {
        "cost_aware_edge": {"fee_bps": "6", "spread_bps": "4"},
        "trading": {"slippage_bps": "3"},
        "execution": {"cost_aware_edge": {"volatility_buffer_bps": 7, "pyramid_drawdown_buffer_bps": 2}},
    }

    resolved = resolve_trading_config(config)
    cost = resolve_cost_aware_edge_config(config)

    assert resolved["cost_aware_edge"] == cost
    assert cost == {
        "taker_fee_bps": 6.0,
        "spread_bps": 4.0,
        "slippage_bps": 3.0,
        "volatility_buffer_bps": 7.0,
        "drawdown_buffer_bps": 2.0,
    }


def test_resolve_trading_config_reads_okx_credentials_from_env(monkeypatch):
    monkeypatch.setenv("OKX_API_KEY", "env-key")
    monkeypatch.setenv("OKX_API_SECRET", "env-secret")
    monkeypatch.setenv("OKX_PASSPHRASE", "env-pass")

    cfg = resolve_trading_config({"execution": {"venue": "okx", "venues": {"okx": {"enabled": True}}}})

    assert cfg["venues"]["okx"]["api_key"] == "env-key"
    assert cfg["venues"]["okx"]["api_secret"] == "env-secret"
    assert cfg["venues"]["okx"]["passphrase"] == "env-pass"


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


def test_execution_service_normalizes_okx_hyphen_symbol_format(monkeypatch):
    session = DummySession()
    service = ExecutionService({"execution": {"mode": "paper", "venue": "okx"}}, db_session=session)
    captured = {}

    class CaptureAdapter(FakeAdapter):
        def place_order(self, request):
            captured["symbol"] = request.symbol
            return super().place_order(request)

    monkeypatch.setattr(service, "get_adapter", lambda venue=None: CaptureAdapter(dry_run=True))
    payload = service.submit_order(symbol="BTC-USDT", side="buy", order_type="market", qty=0.01)
    assert captured["symbol"] == "BTC/USDT"
    assert payload["order"]["symbol"] == "BTC/USDT"


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


def test_live_buy_requires_explicit_canary_policy(monkeypatch):
    service = ExecutionService({"execution": {"mode": "live", "venue": "okx", "enable_live_trading": True}}, db_session=DummySession())
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: FakeAdapter(dry_run=False))

    try:
        service.submit_order(symbol="BTC/USDT", side="buy", order_type="market", qty=0.01)
    except Exception as exc:
        payload = exc.to_payload()
        assert payload["code"] == "live_canary_policy_required"
        assert "execution.live_canary.enabled" in payload["context"]["required_config"]
    else:
        raise AssertionError("live buy should require explicit tiny-canary policy")


def test_standalone_live_policy_cannot_bypass_canary_policy(monkeypatch):
    service = ExecutionService(
        {
            "execution": {
                "mode": "live",
                "venue": "okx",
                "enable_live_trading": True,
                # Historical standalone-runner escape hatch: this must not
                # disable the hard live-canary allowlist/qty cap guard.
                "live_policy": "explicit",
            }
        },
        db_session=DummySession(),
    )
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: FakeAdapter(dry_run=False))

    try:
        service.submit_order(symbol="BTCUSDT", side="buy", order_type="market", qty=0.01, price=62000.0)
    except ExecutionRejectError as exc:
        payload = exc.to_payload()
        assert payload["code"] == "live_canary_policy_required"
        assert payload["context"]["required_config"] == "execution.live_canary.enabled=true + allowed_symbols + max_base_qty_by_symbol"
    else:
        raise AssertionError("standalone live policy must still require explicit tiny-canary policy")


def test_live_canary_rejects_order_above_symbol_qty_cap(monkeypatch):
    service = ExecutionService(
        {
            "trading": {"dry_run": False},
            "execution": {
                "mode": "live",
                "venue": "okx",
                "enable_live_trading": True,
                "live_canary": {
                    "enabled": True,
                    "allowed_symbols": ["BTC/USDT"],
                    "max_base_qty_by_symbol": {"BTC/USDT": 0.001},
                },
            }
        },
        db_session=DummySession(),
    )
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: FakeAdapter(dry_run=False))

    try:
        service.submit_order(symbol="BTCUSDT", side="buy", order_type="market", qty=0.002)
    except Exception as exc:
        payload = exc.to_payload()
        assert payload["code"] == "live_canary_qty_cap_exceeded"
        assert payload["context"]["symbol"] == "BTC/USDT"
        assert payload["context"]["max_base_qty"] == 0.001
    else:
        raise AssertionError("live canary should reject orders above the configured cap")


def test_live_canary_still_requires_execution_permit(monkeypatch):
    service = ExecutionService(
        {
            "trading": {"dry_run": False},
            "execution": {
                "mode": "live",
                "venue": "okx",
                "enable_live_trading": True,
                "live_canary": {
                    "enabled": True,
                    "allowed_symbols": ["BTC/USDT"],
                    "max_base_qty_by_symbol": {"BTC/USDT": 0.001},
                },
            }
        },
        db_session=DummySession(),
    )
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: FakeAdapter(dry_run=False))

    with pytest.raises(ExecutionRejectError, match="permit") as excinfo:
        service.submit_order(symbol="BTCUSDT", side="buy", order_type="market", qty=0.001)

    assert excinfo.value.code == "execution_permit_required"


def _live_canary_config() -> dict:
    return {
        "trading": {"dry_run": False},
        "execution": {
            "mode": "live",
            "venue": "okx",
            "enable_live_trading": True,
            "live_canary": {
                "enabled": True,
                "allowed_symbols": ["BTC/USDT"],
                "max_base_qty_by_symbol": {"BTC/USDT": 0.001},
            },
        },
    }


def _permit_claims(*, expires_delta: timedelta = timedelta(minutes=2), side: str = "buy") -> dict:
    now = datetime.now(timezone.utc)
    return {
        "version": 1,
        "nonce": f"permit-{now.timestamp()}-{side}",
        "issued_at": now.isoformat(),
        "expires_at": (now + expires_delta).isoformat(),
        "run_id": "run-1",
        "profile_id": "trend",
        "strategy_hash": "strategy-sha256",
        "venue": "okx",
        "symbol": "BTC/USDT",
        "side": side,
        "order_type": "market",
        "reduce_only": False,
        "max_qty": 0.001,
        "max_notional": 100.0,
    }


def test_non_dry_adapter_cannot_bypass_live_config(monkeypatch):
    calls = []

    class CaptureAdapter(FakeAdapter):
        def place_order(self, request):
            calls.append(request)
            return super().place_order(request)

    service = ExecutionService({"trading": {"dry_run": False}, "execution": {"mode": "paper", "venue": "okx"}})
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: CaptureAdapter(dry_run=False))

    with pytest.raises(ExecutionRejectError) as excinfo:
        service.submit_order(symbol="BTC/USDT", side="buy", order_type="market", qty=0.001)

    assert excinfo.value.code == "live_config_not_enabled"
    assert calls == []


def test_valid_execution_permit_is_bound_and_single_use(monkeypatch, tmp_path):
    secret = "test-only-permit-secret-with-at-least-32-bytes"
    monkeypatch.setenv("POLY_TRADER_EXECUTION_PERMIT_SECRET", secret)
    session = init_db(f"sqlite:///{tmp_path / 'permit.db'}")
    calls = []

    class CaptureAdapter(FakeAdapter):
        def place_order(self, request):
            calls.append(request)
            return super().place_order(request)

    service = ExecutionService(_live_canary_config(), db_session=session)
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: CaptureAdapter(dry_run=False))
    permit = sign_execution_permit(_permit_claims(), secret=secret)
    kwargs = {
        "symbol": "BTC/USDT",
        "side": "buy",
        "order_type": "market",
        "qty": 0.001,
        "reference_price": 62000.0,
        "run_id": "run-1",
        "profile_id": "trend",
        "strategy_hash": "strategy-sha256",
        "execution_permit": permit,
    }

    payload = service.submit_order(**kwargs)
    assert payload["success"] is True
    assert payload["dry_run"] is False
    assert len(calls) == 1

    with pytest.raises(ExecutionRejectError) as excinfo:
        service.submit_order(**kwargs)
    assert excinfo.value.code == "execution_permit_replayed"
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("claims_update", "expected_code"),
    [
        ({"side": "sell"}, "execution_permit_scope_mismatch"),
        ({"strategy_hash": "other-strategy"}, "execution_permit_scope_mismatch"),
        ({"max_qty": 0.0005}, "execution_permit_limit_exceeded"),
        ({"max_notional": 50.0}, "execution_permit_limit_exceeded"),
    ],
)
def test_execution_permit_claim_mismatches_fail_closed(monkeypatch, tmp_path, claims_update, expected_code):
    secret = "test-only-permit-secret-with-at-least-32-bytes"
    monkeypatch.setenv("POLY_TRADER_EXECUTION_PERMIT_SECRET", secret)
    session = init_db(f"sqlite:///{tmp_path / 'permit-mismatch.db'}")
    service = ExecutionService(_live_canary_config(), db_session=session)
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: FakeAdapter(dry_run=False))
    claims = _permit_claims()
    claims.update(claims_update)
    permit = sign_execution_permit(claims, secret=secret)

    with pytest.raises(ExecutionRejectError) as excinfo:
        service.submit_order(
            symbol="BTC/USDT",
            side="buy",
            order_type="market",
            qty=0.001,
            reference_price=62000.0,
            run_id="run-1",
            profile_id="trend",
            strategy_hash="strategy-sha256",
            execution_permit=permit,
        )
    assert excinfo.value.code == expected_code


def test_expired_execution_permit_fails_closed(monkeypatch, tmp_path):
    secret = "test-only-permit-secret-with-at-least-32-bytes"
    monkeypatch.setenv("POLY_TRADER_EXECUTION_PERMIT_SECRET", secret)
    session = init_db(f"sqlite:///{tmp_path / 'permit-expired.db'}")
    service = ExecutionService(_live_canary_config(), db_session=session)
    monkeypatch.setattr(service, "get_adapter", lambda venue=None: FakeAdapter(dry_run=False))
    permit = sign_execution_permit(_permit_claims(expires_delta=timedelta(seconds=-1)), secret=secret)

    with pytest.raises(ExecutionRejectError) as excinfo:
        service.submit_order(
            symbol="BTC/USDT", side="buy", order_type="market", qty=0.001,
            reference_price=62000.0, run_id="run-1", profile_id="trend",
            strategy_hash="strategy-sha256", execution_permit=permit,
        )
    assert excinfo.value.code == "execution_permit_expired"


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
    assert set(cfg["venues"]) == {"okx", "binance"}
    assert cfg["venues"]["binance"]["enabled"] is True


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


def test_okx_market_rules_normalizes_hyphen_exchange_id_symbol(monkeypatch):
    market = {
        "base": "BTC",
        "quote": "USDT",
        "limits": {"amount": {"min": 0.001}, "cost": {"min": 10.0}},
        "precision": {"amount": 4, "price": 1},
        "info": {"lotSz": "0.0001", "tickSz": "0.1"},
    }
    captured = {}

    class FakeExchange:
        def __init__(self, _config):
            self.markets = {"BTC/USDT": market}

        def market(self, symbol):
            captured["symbol"] = symbol
            return self.markets[symbol]

    monkeypatch.setattr("execution.exchanges.okx_adapter.ccxt.okx", FakeExchange)
    adapter = OKXAdapter({}, dry_run=True)
    rules = adapter.market_rules("BTC-USDT")
    assert captured["symbol"] == "BTC/USDT"
    assert rules["symbol"] == "BTC/USDT"


def test_okx_adapter_omits_reduce_only_for_spot_sell_orders():
    captured = {}

    class FakeExchange:
        def create_market_order(self, symbol, side, qty, params):
            captured["symbol"] = symbol
            captured["side"] = side
            captured["qty"] = qty
            captured["params"] = params
            return {"id": "spot-sell-1", "status": "closed", "timestamp": 123, "clientOrderId": params.get("clOrdId")}

    adapter = OKXAdapter({"default_type": "spot"}, dry_run=False)
    adapter.exchange = FakeExchange()
    result = adapter.place_order(OrderRequest(
        symbol="BTCUSDT",
        side="sell",
        order_type="market",
        qty=0.001,
        reduce_only=True,
        client_order_id="cid-spot",
    ))

    assert result.dry_run is False
    assert result.order_id == "spot-sell-1"
    assert captured["symbol"] == "BTC/USDT"
    assert captured["side"] == "sell"
    assert captured["qty"] == 0.001
    assert captured["params"]["clOrdId"] == "cid-spot"
    assert "reduceOnly" not in captured["params"]


def test_okx_adapter_preserves_reduce_only_for_derivative_reduce_orders():
    captured = {}

    class FakeExchange:
        def create_market_order(self, symbol, side, qty, params):
            captured["symbol"] = symbol
            captured["params"] = params
            return {"id": "swap-sell-1", "status": "open", "timestamp": 456, "clientOrderId": params.get("clOrdId")}

    adapter = OKXAdapter({"default_type": "swap"}, dry_run=False)
    adapter.exchange = FakeExchange()
    result = adapter.place_order(OrderRequest(
        symbol="BTCUSDT",
        side="sell",
        order_type="market",
        qty=0.001,
        reduce_only=True,
        client_order_id="cid-swap",
    ))

    assert result.order_id == "swap-sell-1"
    assert captured["symbol"] == "BTC/USDT"
    assert captured["params"]["clOrdId"] == "cid-swap"
    assert captured["params"]["reduceOnly"] is True
