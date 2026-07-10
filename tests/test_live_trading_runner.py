from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import pytest
from sqlalchemy import text

from backtesting import strategy_lab
from database.models import FeaturesNormalized, Labels, OrderLifecycleEvent, RawMarketData, TradeHistory, init_db
from execution import live_runner as live_runner_module
from execution.execution_service import ExecutionService
from execution.control_plane import build_live_runner_overview
from execution.exchanges.base import ExchangeOrderResult
from execution.live_runner import (
    FrozenModelArtifact,
    LiveTradingRunner,
    ensure_model_artifact,
    load_latest_strategy_row,
    load_saved_strategy,
)

STRATEGY_NAME = "Auto Leaderboard · 重掃 random_forest Hybrid #01"


class FixedConfidenceModel:
    def __init__(self, confidence: float):
        self.confidence = float(confidence)

    def predict_proba(self, values):
        return [[1.0 - self.confidence, self.confidence] for _ in values]


def _strategy_definition() -> Dict[str, Any]:
    return {
        "type": "hybrid",
        "params": {
            "model_name": "random_forest",
            "entry": {
                "bias50_max": 3.0,
                "confidence_min": 0.45,
                "entry_quality_min": 0.5,
                "top_k_percent": 0.0,
                "allowed_regimes": ["bull", "chop"],
                "layer2_bias_max": 2.0,
                "layer3_bias_max": 0.5,
            },
            "layers": [0.25, 0.25, 0.5],
            "stop_loss": -0.05,
            "take_profit_bias": 999.0,
            "take_profit_roi": 999.0,
            "turning_point": {
                "enabled": True,
                "bottom_score_min": 0.56,
                "top_score_take_profit": 0.8,
            },
            "editor_modules": ["turning_point"],
        },
    }


@pytest.fixture
def isolated_strategies_dir(tmp_path: Path, monkeypatch):
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    monkeypatch.setattr(strategy_lab, "STRATEGIES_DIR", strategies_dir)
    return strategies_dir


def _save_target_strategy() -> Dict[str, Any]:
    strategy_lab.save_strategy(
        STRATEGY_NAME,
        _strategy_definition(),
        {"roi": 1.23, "win_rate": 0.62, "total_trades": 12, "avg_decision_quality_score": 0.8},
    )
    strategy = strategy_lab.load_strategy(STRATEGY_NAME)
    assert strategy is not None
    return strategy


def _session(tmp_path: Path):
    return init_db(f"sqlite:///{tmp_path / 'live_runner.db'}")


def _base_config(db_url: str) -> Dict[str, Any]:
    return {
        "database": {"url": db_url},
        "trading": {"symbol": "BTCUSDT", "venue": "okx", "dry_run": True},
        "execution": {"mode": "paper", "venue": "okx", "enable_live_trading": False},
        "live_runner": {
            "strategy_name": STRATEGY_NAME,
            "interval_seconds": 300,
            "capital_quote": 10000,
            "one_action_per_feature_timestamp": True,
            "order_type": "market",
        },
    }


def _fake_artifact(tmp_path: Path, confidence: float) -> FrozenModelArtifact:
    return FrozenModelArtifact(
        model=FixedConfidenceModel(confidence),
        model_path=tmp_path / "fixed-model.pkl",
        metadata_path=tmp_path / "fixed-model.json",
        metadata={
            "model_name": "random_forest",
            "feature_columns": [
                "feat_4h_bias50",
                "feat_4h_bias200",
                "feat_nose",
                "feat_pulse",
                "feat_ear",
                "feat_local_bottom_score",
                "feat_local_top_score",
            ],
        },
    )


def _seed_feature_row(
    session,
    ts: datetime,
    *,
    price: float = 100.0,
    symbol: str = "BTCUSDT",
    bottom_score: float = 0.8,
    top_score: float = 0.1,
    bias50: float = 0.0,
) -> None:
    session.add(
        RawMarketData(
            timestamp=ts,
            symbol=symbol,
            close_price=price,
            volume=1000.0,
        )
    )
    session.add(
        FeaturesNormalized(
            timestamp=ts,
            symbol=symbol,
            regime_label="bull",
            feat_eye=0.5,
            feat_ear=0.0,
            feat_nose=0.1,
            feat_tongue=0.5,
            feat_body=0.5,
            feat_pulse=0.9,
            feat_aura=0.5,
            feat_mind=0.5,
            feat_4h_bias50=bias50,
            feat_4h_bias20=0.0,
            feat_4h_bias200=1.0,
            feat_4h_bb_pct_b=0.8,
            feat_4h_dist_bb_lower=5.0,
            feat_4h_dist_swing_low=7.0,
            feat_local_bottom_score=bottom_score,
            feat_local_top_score=top_score,
        )
    )
    session.commit()


def _seed_training_frame(session, rows: int = 80) -> None:
    start = datetime(2026, 1, 1)
    for idx in range(rows):
        ts = start + timedelta(hours=4 * idx)
        _seed_feature_row(
            session,
            ts,
            price=100.0 + idx,
            bottom_score=0.65 if idx % 2 else 0.75,
            top_score=0.15,
            bias50=-1.0 + (idx % 5) * 0.25,
        )
        session.add(
            Labels(
                timestamp=ts,
                symbol="BTCUSDT",
                horizon_minutes=1440,
                future_return_pct=0.01 if idx % 2 else -0.01,
                future_max_drawdown=-0.02,
                future_max_runup=0.03,
                label_spot_long_win=idx % 2,
                simulated_pyramid_win=idx % 2,
            )
        )
    session.commit()


def _patch_fake_execution(monkeypatch):
    calls = []

    class FakeExecutionService:
        def __init__(self, config, db_session=None):
            self.config = config
            self.db_session = db_session

        def submit_order(self, **kwargs):
            calls.append(kwargs)
            return {
                "success": True,
                "dry_run": True,
                "order": {
                    "id": f"dry-{len(calls)}",
                    "client_order_id": f"client-{len(calls)}",
                    "symbol": kwargs["symbol"],
                    "side": kwargs["side"],
                    "qty": kwargs["qty"],
                    "price": kwargs.get("price"),
                },
            }

    monkeypatch.setattr(live_runner_module, "ExecutionService", FakeExecutionService)
    return calls


def test_live_runner_loads_exact_auto_strategy_name_and_slug(tmp_path: Path, isolated_strategies_dir: Path):
    saved = _save_target_strategy()

    loaded_by_name = load_saved_strategy(STRATEGY_NAME)
    loaded_by_slug = load_saved_strategy(saved["slug"])

    assert loaded_by_name["name"] == STRATEGY_NAME
    assert loaded_by_slug["name"] == STRATEGY_NAME
    assert loaded_by_name["slug"] == saved["slug"]


def test_live_model_artifact_freezes_random_forest_from_db(tmp_path: Path, isolated_strategies_dir: Path):
    session = _session(tmp_path)
    strategy = _save_target_strategy()
    _seed_training_frame(session)

    artifact = ensure_model_artifact(session=session, strategy=strategy, refresh=True, root=tmp_path / "models")
    loaded = ensure_model_artifact(session=session, strategy=strategy, refresh=False, root=tmp_path / "models")

    assert artifact.model_path.exists()
    assert artifact.metadata_path.exists()
    assert artifact.metadata["model_name"] == "random_forest"
    assert artifact.metadata["target"] == "simulated_pyramid_win"
    assert artifact.metadata["model_hash"]
    assert loaded.metadata["strategy_hash"] == artifact.metadata["strategy_hash"]
    session.close()


def test_live_runner_records_hold_without_order(tmp_path: Path, isolated_strategies_dir: Path, monkeypatch):
    session = _session(tmp_path)
    _save_target_strategy()
    db_url = f"sqlite:///{tmp_path / 'live_runner.db'}"
    _seed_feature_row(session, datetime(2026, 2, 1, 0, 0))
    calls = _patch_fake_execution(monkeypatch)
    runner = LiveTradingRunner(_base_config(db_url), session, model_artifact=_fake_artifact(tmp_path, 0.1))
    runner.start_run()

    decision = runner.run_cycle(collect_market=False, preprocess=False)
    rows = session.execute(text("SELECT action, reason FROM live_runner_decisions")).mappings().all()

    assert decision["action"] == "HOLD"
    assert decision["reason"] == "entry_conditions_not_met"
    assert calls == []
    assert rows[-1]["action"] == "HOLD"
    session.close()


def test_live_runner_forces_no_submit_shadow_candidate_and_24h_gate(tmp_path: Path, isolated_strategies_dir: Path, monkeypatch):
    session = _session(tmp_path)
    _save_target_strategy()
    db_url = f"sqlite:///{tmp_path / 'live_runner.db'}"
    feature_ts = datetime(2026, 2, 1, 0, 0)
    _seed_feature_row(session, feature_ts)
    calls = _patch_fake_execution(monkeypatch)
    config = _base_config(db_url)
    config["live_runner"].update(
        {
            "shadow_candidate_enabled": True,
            "shadow_evidence_mode": True,
            "shadow_candidate_qty": 0.00001,
        }
    )
    trading_root = tmp_path / "live_trading"
    runner = LiveTradingRunner(config, session, model_artifact=_fake_artifact(tmp_path, 0.1), trading_root=trading_root)
    runner.start_run()

    first = runner.run_cycle(collect_market=False, preprocess=False, submit_orders=True)
    second = runner.run_cycle(collect_market=False, preprocess=False, submit_orders=True)

    rows = session.execute(
        text("SELECT action, side, order_submitted, dry_run, reason, payload_json FROM live_runner_decisions ORDER BY id")
    ).mappings().all()
    assert first["action"] == "SHADOW_BUY_CANDIDATE"
    assert first["side"] == "buy"
    assert first["order_submitted"] == 0
    assert first["dry_run"] == 1
    assert first["reason"] == "shadow_candidate_for_24h_gate"
    assert first["payload"]["original_decision"]["action"] == "HOLD"
    assert first["payload"]["shadow_candidate_contract"]["order_submission_enabled"] is False
    assert second["action"] == "HOLD"
    assert second["reason"] == "shadow_candidate_already_recorded"
    assert calls == []
    assert rows[0]["action"] == "SHADOW_BUY_CANDIDATE"
    assert rows[0]["order_submitted"] == 0
    assert rows[0]["dry_run"] == 1
    assert json.loads(rows[0]["payload_json"])["shadow_candidate_contract"]["live_order_submitted"] is False

    pending = build_live_runner_overview(
        session,
        now=datetime(2026, 2, 1, 1, 0, tzinfo=timezone.utc),
        jsonl_root=trading_root,
    )
    assert pending["status"] == "runner_24h_pending_observation"
    assert pending["summary"]["candidate_decisions"] == 1
    assert pending["summary"]["jsonl_backed"] is True
    assert pending["shadow_evidence_gate"]["order_submission_enabled"] is False

    session.add(
        Labels(
            timestamp=feature_ts,
            symbol="BTCUSDT",
            horizon_minutes=1440,
            future_return_pct=0.02,
            future_max_drawdown=-0.01,
            future_max_runup=0.04,
            label_spot_long_win=1,
            simulated_pyramid_win=1,
            simulated_pyramid_pnl=0.018,
            simulated_pyramid_quality=0.61,
        )
    )
    session.commit()
    resolved = build_live_runner_overview(
        session,
        now=datetime(2026, 2, 2, 1, 0, tzinfo=timezone.utc),
        jsonl_root=trading_root,
    )
    assert resolved["status"] == "runner_24h_resolved_evidence_ready"
    assert resolved["shadow_evidence_gate"]["resolved_outcomes"] == 1
    assert resolved["shadow_evidence_gate"]["risk_on_order_enabled"] is False
    session.close()


def test_live_runner_latest_row_accepts_okx_hyphen_symbol_variant(tmp_path: Path, isolated_strategies_dir: Path):
    session = _session(tmp_path)
    _seed_feature_row(session, datetime(2026, 2, 1, 4, 0), symbol="BTC-USDT")

    row = load_latest_strategy_row(session, "BTCUSDT")

    assert row["close_price"] == pytest.approx(100.0)
    session.close()


def test_live_runner_redacts_okx_secrets_from_run_config(tmp_path: Path, isolated_strategies_dir: Path):
    session = _session(tmp_path)
    _save_target_strategy()
    db_url = f"sqlite:///{tmp_path / 'live_runner.db'}"
    config = _base_config(db_url)
    config["okx"] = {
        "api_key": "secret-key-value",
        "api_secret": "secret-secret-value",
        "passphrase": "secret-pass-value",
    }
    config["execution"]["venues"] = {
        "okx": {
            "enabled": True,
            "apiKey": "camel-key-value",
            "secret": "camel-secret-value",
            "password": "camel-pass-value",
        }
    }
    runner = LiveTradingRunner(config, session, model_artifact=_fake_artifact(tmp_path, 0.5))
    runner.start_run()

    stored = session.execute(text("SELECT config_json FROM live_runner_runs WHERE id=:id"), {"id": runner.run_id}).scalar()

    assert stored is not None
    assert "secret-key-value" not in stored
    assert "secret-secret-value" not in stored
    assert "secret-pass-value" not in stored
    assert "camel-key-value" not in stored
    assert "camel-secret-value" not in stored
    assert "camel-pass-value" not in stored
    assert stored.count("[REDACTED]") >= 6
    session.close()


def test_live_runner_buy_once_per_feature_timestamp(tmp_path: Path, isolated_strategies_dir: Path, monkeypatch):
    session = _session(tmp_path)
    _save_target_strategy()
    db_url = f"sqlite:///{tmp_path / 'live_runner.db'}"
    _seed_feature_row(session, datetime(2026, 2, 2, 0, 0))
    calls = _patch_fake_execution(monkeypatch)
    runner = LiveTradingRunner(_base_config(db_url), session, model_artifact=_fake_artifact(tmp_path, 0.9))
    runner.start_run()

    first = runner.run_cycle(collect_market=False, preprocess=False)
    second = runner.run_cycle(collect_market=False, preprocess=False)

    assert first["action"] == "BUY_LAYER"
    assert first["order_submitted"] == 1
    assert second["action"] == "HOLD"
    assert second["reason"] == "feature_timestamp_already_acted"
    assert len(calls) == 1
    session.close()


def test_live_runner_sell_all_for_turning_point(tmp_path: Path, isolated_strategies_dir: Path, monkeypatch):
    session = _session(tmp_path)
    _save_target_strategy()
    db_url = f"sqlite:///{tmp_path / 'live_runner.db'}"
    _seed_feature_row(session, datetime(2026, 2, 3, 0, 0), price=120.0, top_score=0.9)
    calls = _patch_fake_execution(monkeypatch)
    runner = LiveTradingRunner(_base_config(db_url), session, model_artifact=_fake_artifact(tmp_path, 0.9))
    runner.start_run()
    runner._record_decision(
        {
            "feature_timestamp": "2026-02-02 20:00:00",
            "price": 100.0,
            "signal": "BUY_L1",
            "action": "BUY_LAYER",
            "side": "buy",
            "qty": 1.0,
            "quote_amount": 100.0,
            "order_submitted": True,
            "dry_run": True,
            "model_confidence": 0.9,
            "entry_quality": 0.8,
            "allowed_layers": 3,
            "regime_gate": "ALLOW",
            "structure_bucket": "ALLOW|base_allow|q65",
            "reason": "buy_layer_1",
            "payload": {"layer": {"price": 100.0, "coins": 1.0, "layer": 1}},
        }
    )

    decision = runner.run_cycle(collect_market=False, preprocess=False)

    assert decision["action"] == "SELL_ALL"
    assert decision["reason"] == "tp_turning_point"
    assert calls[-1]["side"] == "sell"
    assert calls[-1]["reduce_only"] is True
    session.close()


def test_live_runner_live_buy_rejects_without_canary_policy(tmp_path: Path, isolated_strategies_dir: Path, monkeypatch):
    session = _session(tmp_path)
    _save_target_strategy()
    db_url = f"sqlite:///{tmp_path / 'live_runner.db'}"
    _seed_feature_row(session, datetime(2026, 2, 4, 0, 0))
    config = _base_config(db_url)
    config["trading"]["dry_run"] = False
    config["execution"].update({"mode": "live", "enable_live_trading": True})

    class LiveAdapter:
        venue = "okx"
        dry_run = False

        def fetch_balance(self):
            return {"venue": self.venue, "currency": "USDT", "free": 100000.0, "total": 100000.0, "dry_run": False}

        def market_rules(self, symbol):
            return {"symbol": symbol, "min_qty": 0.001, "min_cost": 10.0, "amount_precision": 8, "price_precision": 2}

        def place_order(self, request):
            raise AssertionError("live buy must reject before adapter.place_order without canary policy")

    monkeypatch.setattr(ExecutionService, "get_adapter", lambda self, venue=None: LiveAdapter())
    runner = LiveTradingRunner(config, session, model_artifact=_fake_artifact(tmp_path, 0.9))
    runner.start_run()

    decision = runner.run_cycle(collect_market=False, preprocess=False)
    trades = session.query(TradeHistory).all()
    events = session.query(OrderLifecycleEvent).order_by(OrderLifecycleEvent.id).all()

    assert decision["action"] == "BUY_LAYER"
    assert decision["order_submitted"] == 0
    assert decision["dry_run"] is None
    assert decision["reason"] == "execution_rejected:live_canary_policy_required"
    assert decision["payload"]["execution_reject"]["context"]["required_config"] == "execution.live_canary.enabled=true + allowed_symbols + max_base_qty_by_symbol"
    assert trades == []
    assert [event.event_type for event in events] == ["rejected"]
    assert getattr(events[0], "source") == "execution_guardrail"
    assert getattr(events[0], "order_state") == "rejected"
    session.close()


def test_live_runner_order_records_trade_history_and_lifecycle(tmp_path: Path, isolated_strategies_dir: Path, monkeypatch):
    session = _session(tmp_path)
    _save_target_strategy()
    db_url = f"sqlite:///{tmp_path / 'live_runner.db'}"
    _seed_feature_row(session, datetime(2026, 2, 5, 0, 0))

    class RecordingAdapter:
        venue = "okx"
        dry_run = True

        def fetch_balance(self):
            return {"venue": self.venue, "currency": "USDT", "free": 100000.0, "total": 100000.0, "dry_run": True}

        def market_rules(self, symbol):
            return {"symbol": symbol, "min_qty": 0.001, "min_cost": 10.0, "amount_precision": 8, "price_precision": 2}

        def place_order(self, request):
            return ExchangeOrderResult(
                venue=self.venue,
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                qty=request.qty,
                price=request.price,
                status="closed",
                order_id="paper-live-runner-1",
                client_order_id=request.client_order_id,
                timestamp=1234567890,
                raw={},
                dry_run=True,
            )

    monkeypatch.setattr(ExecutionService, "get_adapter", lambda self, venue=None: RecordingAdapter())
    runner = LiveTradingRunner(_base_config(db_url), session, model_artifact=_fake_artifact(tmp_path, 0.9))
    runner.start_run()

    decision = runner.run_cycle(collect_market=False, preprocess=False)
    trades = session.query(TradeHistory).all()
    events = session.query(OrderLifecycleEvent).order_by(OrderLifecycleEvent.id).all()

    assert decision["action"] == "BUY_LAYER"
    assert decision["order_submitted"] == 1
    assert len(trades) == 1
    assert trades[0].order_id == "paper-live-runner-1"
    assert [event.event_type for event in events] == ["validation_passed", "venue_ack", "trade_history_persisted"]
    session.close()
