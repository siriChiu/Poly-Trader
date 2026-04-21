import asyncio
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backtesting import strategy_lab
from scripts import backfill_backtest_range as backfill_module
from server.routes import api as api_module
from server.routes.api import (
    _compute_backtest_benchmarks,
    _compute_regime_breakdown,
    _compute_strategy_risk,
    _decorate_strategy_entry,
    _compute_strategy_decision_quality_profile,
    _strategy_decision_contract_meta,
    _strategy_leaderboard_sort_key,
    api_klines,
)


@pytest.fixture
def isolated_strategies_dir(tmp_path: Path, monkeypatch):
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    monkeypatch.setattr(strategy_lab, "STRATEGIES_DIR", strategies_dir)
    return strategies_dir


def _local_request():
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


def _remote_request():
    return SimpleNamespace(client=SimpleNamespace(host="10.0.0.8"))


def test_assert_local_operator_request_rejects_non_loopback():
    api_module._assert_local_operator_request(_local_request())
    with pytest.raises(HTTPException) as excinfo:
        api_module._assert_local_operator_request(_remote_request())
    assert excinfo.value.status_code == 403


def test_load_all_strategies_sanitizes_invalid_results_and_filters_internal(isolated_strategies_dir: Path):
    (isolated_strategies_dir / "tmp_run_count_check.json").write_text(
        """
        {
          "name": "tmp_run_count_check",
          "definition": {"type": "rule_based", "params": {}},
          "last_results": {"roi": 0.1},
          "run_count": 1
        }
        """.strip(),
        encoding="utf-8",
    )
    (isolated_strategies_dir / "visible.json").write_text(
        """
        {
          "name": "Visible Strategy",
          "definition": {"type": "rule_based", "params": {}},
          "last_results": {"roi": 0.0477, "win_rate": null, "profit_factor": "nan", "max_drawdown": 0.12},
          "run_count": 0
        }
        """.strip(),
        encoding="utf-8",
    )

    strategies = strategy_lab.load_all_strategies()

    assert [entry["name"] for entry in strategies] == ["Visible Strategy"]
    assert strategies[0]["run_count"] == 1
    assert strategies[0]["last_results"]["profit_factor"] is None
    assert strategies[0]["last_results"]["win_rate"] is None


def test_save_strategy_does_not_increment_run_count_when_only_saving_definition(isolated_strategies_dir: Path):
    strategy_lab.save_strategy("Persistent", {"type": "rule_based", "params": {}}, {"roi": 0.2, "win_rate": 0.6})
    strategy_lab.save_strategy("Persistent", {"type": "rule_based", "params": {"entry": {"bias50_max": -2}}})

    loaded = strategy_lab.load_strategy("Persistent")

    assert loaded is not None
    assert loaded["run_count"] == 1
    assert loaded["last_results"]["roi"] == pytest.approx(0.2)
    assert loaded["definition"]["params"]["entry"]["bias50_max"] == -2


def test_save_strategy_persists_detail_payload_and_strategy_metadata(isolated_strategies_dir: Path):
    strategy_lab.save_strategy(
        "Pyramid v3 Optimized",
        {
            "type": "rule_based",
            "params": {
                "entry": {"bias50_max": -1.5, "nose_max": 0.4, "layer2_bias_max": -3.0, "layer3_bias_max": -5.0},
                "layers": [0.2, 0.3, 0.5],
                "stop_loss": -0.05,
                "take_profit_bias": 4.0,
                "take_profit_roi": 0.08,
            },
        },
        {
            "roi": 0.18,
            "win_rate": 0.71,
            "total_trades": 21,
            "benchmarks": {"buy_hold": {"label": "買入持有", "roi": 0.04}},
            "equity_curve": [{"timestamp": "2026-01-01T00:00:00Z", "equity": 10000.0}],
            "trades": [{"timestamp": "2026-01-02T00:00:00Z", "entry": 100.0, "exit": 110.0, "pnl": 50.0, "reason": "tp_roi"}],
            "chart_context": {"symbol": "BTCUSDT", "interval": "4h", "start": "2026-01-01T00:00:00Z", "end": "2026-01-10T00:00:00Z"},
        },
    )

    loaded = strategy_lab.load_strategy("Pyramid v3 Optimized")

    assert loaded is not None
    assert loaded["last_results"]["benchmarks"]["buy_hold"]["roi"] == pytest.approx(0.04)
    assert loaded["last_results"]["equity_curve"][0]["equity"] == pytest.approx(10000.0)
    assert loaded["last_results"]["trades"][0]["entry"] == pytest.approx(100.0)
    assert loaded["last_results"]["chart_context"]["interval"] == "4h"
    assert loaded["metadata"]["title"] == "Pyramid v3 Optimized"
    assert "三層金字塔" in loaded["metadata"]["description"]


def test_save_strategy_reconstructs_backtest_range_when_legacy_results_dropped_it(isolated_strategies_dir: Path):
    strategy_lab.save_strategy(
        "Backtest Range Recovery",
        {
            "type": "hybrid",
            "params": {
                "model_name": "xgboost",
                "backtest_range": {
                    "start": "2024-04-19T22:40:00.000Z",
                    "end": "2026-04-19T22:40:00.000Z",
                },
            },
        },
        {
            "total_trades": 29,
            "run_at": "2026-04-20T07:12:13.836010Z",
            "chart_context": {
                "symbol": "BTCUSDT",
                "interval": "4h",
                "start": "2025-04-06T17:00:00Z",
                "end": "2026-04-19T22:34:02.344375Z",
            },
        },
    )

    loaded = strategy_lab.load_strategy("Backtest Range Recovery")

    assert loaded is not None
    recovered_range = loaded["last_results"]["backtest_range"]
    assert recovered_range["requested"]["start"] == "2024-04-19T22:40:00.000Z"
    assert recovered_range["requested"]["end"] == "2026-04-19T22:40:00.000Z"
    assert recovered_range["effective"]["start"] == "2024-04-19T22:40:00.000Z"
    assert recovered_range["effective"]["end"] == "2026-04-19T22:40:00.000Z"
    assert recovered_range["available"]["start"] == "2025-04-06T17:00:00Z"
    assert recovered_range["available"]["end"] == "2026-04-19T22:34:02.344375Z"
    assert recovered_range["coverage_ok"] is True
    assert recovered_range["backfill_required"] is False


def test_save_strategy_persists_decision_profile_fields(isolated_strategies_dir: Path):
    strategy_lab.save_strategy(
        "Decision Profile Demo",
        {"type": "rule_based", "params": {}},
        {
            "roi": 0.12,
            "win_rate": 0.66,
            "avg_entry_quality": 0.74,
            "avg_allowed_layers": 2.4,
            "dominant_regime_gate": "CAUTION",
            "regime_gate_summary": {"ALLOW": 2, "CAUTION": 5, "BLOCK": 0},
        },
    )

    loaded = strategy_lab.load_strategy("Decision Profile Demo")

    assert loaded is not None
    assert loaded["last_results"]["avg_entry_quality"] == pytest.approx(0.74)
    assert loaded["last_results"]["avg_allowed_layers"] == pytest.approx(2.4)
    assert loaded["last_results"]["dominant_regime_gate"] == "CAUTION"
    assert loaded["last_results"]["regime_gate_summary"]["CAUTION"] == 5



def test_save_strategy_sanitizes_auto_leaderboard_slugs_with_slashes(isolated_strategies_dir: Path):
    strategy_lab.save_strategy(
        "Auto Leaderboard · 10/90 後守 Rule #04",
        {"type": "rule_based", "params": {}},
        {"roi": 0.03, "win_rate": 0.51},
    )

    saved = list(isolated_strategies_dir.glob("*.json"))
    assert len(saved) == 1
    assert "/" not in saved[0].name
    loaded = strategy_lab.load_strategy("Auto Leaderboard · 10/90 後守 Rule #04")
    assert loaded is not None
    assert loaded["last_results"]["roi"] == pytest.approx(0.03)


def test_strategy_metadata_explains_rule_baseline_model(isolated_strategies_dir: Path):
    strategy_lab.save_strategy(
        "Rule Baseline Demo",
        {
            "type": "hybrid",
            "params": {
                "model_name": "rule_baseline",
                "entry": {"bias50_max": 1.0, "nose_max": 0.4, "layer2_bias_max": -1.5, "layer3_bias_max": -3.5},
                "layers": [0.2, 0.3, 0.5],
            },
        },
        {"roi": 0.02, "win_rate": 0.6},
    )

    loaded = strategy_lab.load_strategy("Rule Baseline Demo")

    assert loaded is not None
    assert "rule_baseline" in loaded["metadata"]["model_summary"]
    assert "Bias50" in loaded["metadata"]["model_summary"]


def test_strategy_metadata_mentions_reserve_capital_mode(isolated_strategies_dir: Path):
    strategy_lab.save_strategy(
        "Reserve Mode Demo",
        {
            "type": "rule_based",
            "params": {
                "entry": {"bias50_max": 0.5, "nose_max": 0.35, "layer2_bias_max": -2.5, "layer3_bias_max": -4.5},
                "layers": [0.2, 0.3, 0.5],
                "capital_management": {"mode": "reserve_90", "base_entry_fraction": 0.10, "reserve_trigger_drawdown": 0.10},
            },
        },
        {"roi": 0.05, "win_rate": 0.52},
    )

    loaded = strategy_lab.load_strategy("Reserve Mode Demo")

    assert loaded is not None
    assert "先用 10% 建倉" in loaded["metadata"]["description"]


def test_strategy_metadata_mentions_xgboost_local_top_exit_gate(isolated_strategies_dir: Path):
    strategy_lab.save_strategy(
        "Top Exit Hybrid",
        {
            "type": "hybrid",
            "params": {
                "model_name": "xgboost",
                "entry": {"bias50_max": -1.0, "confidence_min": 0.55},
                "turning_point": {"enabled": True, "bottom_score_min": 0.62, "top_score_take_profit": 0.68},
                "editor_modules": ["turning_point"],
            },
        },
        {"roi": 0.11, "win_rate": 0.63},
    )

    loaded = strategy_lab.load_strategy("Top Exit Hybrid")

    assert loaded is not None
    assert loaded["metadata"]["model_name"] == "xgboost"
    assert "xgboost" in loaded["metadata"]["model_summary"]
    assert "頂部轉折" in loaded["metadata"]["description"]


def test_build_auto_strategy_candidates_returns_diverse_templates():
    candidates = strategy_lab.build_auto_strategy_candidates(["random_forest", "xgboost"])

    assert len(candidates) >= 8
    assert len({candidate["name"] for candidate in candidates}) == len(candidates)
    assert {candidate["definition"]["type"] for candidate in candidates} == {"rule_based", "hybrid"}
    assert any(
        candidate["definition"]["params"].get("capital_management", {}).get("mode") == "reserve_90"
        for candidate in candidates
    )
    assert any(
        float(candidate["definition"]["params"].get("entry", {}).get("top_k_percent", 0) or 0) > 0
        for candidate in candidates
    )
    assert any(candidate["definition"]["params"].get("model_name") == "random_forest" for candidate in candidates)
    assert any(candidate["definition"]["params"].get("storm_unwind", {}).get("enabled") for candidate in candidates)
    assert any("turning_point" in (candidate["definition"]["params"].get("editor_modules") or []) for candidate in candidates)
    assert any(candidate["definition"]["params"].get("turning_point", {}).get("enabled") for candidate in candidates)
    assert any(
        candidate["definition"]["params"].get("model_name") == "xgboost"
        and candidate["definition"]["params"].get("turning_point", {}).get("enabled")
        for candidate in candidates
    )


def test_top_k_rolling_gate_uses_past_only_history():
    assert strategy_lab._passes_rolling_top_k_gate(0.62, [], 5) is True
    assert strategy_lab._passes_rolling_top_k_gate(0.62, [0.91, 0.87, 0.84, 0.81], 25) is False
    assert strategy_lab._passes_rolling_top_k_gate(0.92, [0.91, 0.87, 0.84, 0.81], 25) is True


def test_turning_point_gate_requires_local_bottom_signal_for_entry():
    prices = [100.0, 99.0, 98.0, 101.0]
    timestamps = [f"2026-01-01T00:0{i}:00Z" for i in range(len(prices))]
    bias50 = [-2.0, -2.5, -2.8, 3.5]
    bias200 = [0.0, 0.0, 0.0, 0.0]
    nose = [0.3, 0.3, 0.3, 0.3]
    pulse = [0.7, 0.7, 0.7, 0.7]
    ear = [0.0, 0.0, 0.0, 0.0]
    local_bottom = [0.1, 0.2, 0.9, 0.1]
    local_top = [0.1, 0.1, 0.2, 0.8]

    result = strategy_lab.run_rule_backtest(
        prices,
        timestamps,
        bias50,
        bias200,
        nose,
        pulse,
        ear,
        {
            "entry": {"bias50_max": -1.0, "nose_max": 0.4, "entry_quality_min": 0.0},
            "turning_point": {"enabled": True, "bottom_score_min": 0.7, "top_score_take_profit": 0.7},
            "take_profit_bias": 10.0,
            "take_profit_roi": 0.5,
        },
        local_bottom_score=local_bottom,
        local_top_score=local_top,
    )

    assert result.total_trades == 1
    assert result.trades[0]["entry_timestamp"] == timestamps[2]


def test_hybrid_turning_point_exit_gate_uses_local_top_score():
    prices = [100.0, 99.0, 98.0, 100.5, 101.5]
    timestamps = [f"2026-01-01T00:0{i}:00Z" for i in range(len(prices))]
    bias50 = [-2.0, -2.5, -3.0, -1.0, -0.5]
    bias200 = [0.0] * len(prices)
    nose = [0.3] * len(prices)
    pulse = [0.7] * len(prices)
    ear = [0.0] * len(prices)
    conf = [0.2, 0.3, 0.9, 0.7, 0.6]
    local_bottom = [0.1, 0.2, 0.85, 0.2, 0.1]
    local_top = [0.1, 0.1, 0.2, 0.75, 0.2]

    result = strategy_lab.run_hybrid_backtest(
        prices,
        timestamps,
        bias50,
        bias200,
        nose,
        pulse,
        ear,
        conf,
        {
            "entry": {"bias50_max": -1.0, "confidence_min": 0.55, "entry_quality_min": 0.0},
            "turning_point": {"enabled": True, "bottom_score_min": 0.7, "top_score_take_profit": 0.7},
            "take_profit_bias": 10.0,
            "take_profit_roi": 0.5,
            "model_name": "xgboost",
        },
        local_bottom_score=local_bottom,
        local_top_score=local_top,
    )

    assert result.total_trades == 1
    assert result.trades[0]["reason"] == "tp_turning_point"
    assert result.trades[0]["entry_timestamp"] == timestamps[2]


def test_compute_regime_breakdown_groups_by_entry_regime():
    trades = [
        {"entry_regime": "bull", "pnl": 100.0},
        {"entry_regime": "bull", "pnl": -40.0},
        {"entry_regime": "chop", "pnl": 30.0},
    ]

    breakdown = _compute_regime_breakdown(trades, 1000.0)

    assert [row["regime"] for row in breakdown] == ["bull", "chop"]
    assert breakdown[0]["trades"] == 2
    assert breakdown[0]["wins"] == 1
    assert breakdown[0]["losses"] == 1
    assert breakdown[0]["roi"] == pytest.approx(0.06)
    assert breakdown[1]["profit_factor"] == pytest.approx(3000.0)


def test_select_strategy_chart_payload_aligns_equity_with_trade_window():
    equity_curve = [
        {"timestamp": f"2025-01-01T00:{idx:02d}:00Z", "equity": 10000 + idx}
        for idx in range(10)
    ] + [
        {"timestamp": f"2026-01-01T00:{idx:02d}:00Z", "equity": 20000 + idx}
        for idx in range(10)
    ]
    trades = [
        {"entry_timestamp": "2025-01-01T00:02:00Z", "timestamp": "2025-01-01T00:04:00Z", "pnl": 10},
        {"entry_timestamp": "2025-01-01T00:05:00Z", "timestamp": "2025-01-01T00:07:00Z", "pnl": -5},
    ]

    payload = api_module._select_strategy_chart_payload(
        timestamps=[point["timestamp"] for point in equity_curve],
        equity_curve=equity_curve,
        trades=trades,
    )

    selected_times = [row["timestamp"] for row in payload["equity_curve"]]
    assert selected_times[0].startswith("2025-01-01T00:02")
    assert selected_times[-1].startswith("2025-01-01T00:07")
    assert payload["chart_context"]["start"].startswith("2025-01-01T00:02")
    assert payload["chart_context"]["end"].startswith("2025-01-01T00:07")


def test_filter_strategy_rows_by_backtest_range_reports_missing_history():
    rows = [
        ("2025-04-03 13:00:00", 100.0),
        ("2025-10-03 13:00:00", 110.0),
        ("2026-04-16 00:40:26", 120.0),
    ]

    filtered, meta = api_module._filter_strategy_rows_by_backtest_range(
        rows,
        start="2024-04-16T00:00:00Z",
        end="2026-04-16T00:40:26Z",
    )

    assert len(filtered) == 3
    assert meta["backfill_required"] is True
    assert meta["coverage_ok"] is False
    assert meta["missing_start_days"] > 300
    assert meta["effective"]["start"].startswith("2025-04-03")



def test_resolve_default_strategy_backtest_range_uses_latest_two_year_window_when_missing():
    start, end, policy = api_module._resolve_default_strategy_backtest_range(
        requested_start=None,
        requested_end=None,
        available_start="2023-01-01T00:00:00Z",
        available_end="2026-04-16T00:40:26Z",
    )

    assert start.startswith("2024-04-16")
    assert end.startswith("2026-04-16")
    assert policy["mode"] == "latest_two_year_default"
    assert policy["lookback_days"] == 730
    assert policy["requested_range_was_empty"] is True



def test_resolve_default_strategy_backtest_range_preserves_explicit_range():
    start, end, policy = api_module._resolve_default_strategy_backtest_range(
        requested_start="2025-01-01T00:00:00Z",
        requested_end="2025-12-31T00:00:00Z",
        available_start="2023-01-01T00:00:00Z",
        available_end="2026-04-16T00:40:26Z",
    )

    assert start.startswith("2025-01-01")
    assert end.startswith("2025-12-31")
    assert policy["mode"] == "explicit_range"
    assert policy["requested_range_was_empty"] is False



def test_api_strategy_data_range_uses_loaded_strategy_rows(monkeypatch):
    rows = [
        ("2025-04-03 13:00:00", 100.0),
        ("2026-04-16 00:40:26", 120.0),
    ]
    monkeypatch.setattr(api_module, "_load_strategy_data", lambda: rows)

    payload = asyncio.run(api_module.api_strategy_data_range())

    assert payload["count"] == 2
    assert payload["start"].startswith("2025-04-03")
    assert payload["end"].startswith("2026-04-16")
    assert payload["span_days"] > 300


def test_execute_strategy_run_auto_backfills_when_requested_range_exceeds_local_history(monkeypatch):
    rows_old = [
        ("2025-04-03 13:00:00", 100.0, -1.0, 0.0, 0.2, 0.8, 0.0, "bull", 0.5, 1.0, 1.0, 0.0, 0.0),
        ("2025-04-04 13:00:00", 101.0, -0.8, 0.0, 0.2, 0.8, 0.0, "bull", 0.5, 1.0, 1.0, 0.0, 0.0),
    ]
    rows_new = [
        ("2024-04-16 00:00:00", 90.0, -1.2, 0.0, 0.2, 0.8, 0.0, "bull", 0.5, 1.0, 1.0, 0.0, 0.0),
        ("2025-04-03 13:00:00", 100.0, -1.0, 0.0, 0.2, 0.8, 0.0, "bull", 0.5, 1.0, 1.0, 0.0, 0.0),
        ("2026-04-16 00:00:00", 120.0, 5.0, 0.0, 0.2, 0.8, 0.0, "bull", 0.5, 1.0, 1.0, 0.0, 0.0),
    ]
    load_calls = {"count": 0}
    backfill_calls = []

    def fake_load_strategy_data():
        load_calls["count"] += 1
        return rows_old if load_calls["count"] == 1 else rows_new

    class DummyDB:
        def close(self):
            return None

    def fake_backfill(session, *, target_start=None, target_end=None, apply_changes=None, symbol=None, **kwargs):
        backfill_calls.append({
            "target_start": target_start,
            "target_end": target_end,
            "apply_changes": apply_changes,
            "symbol": symbol,
            **kwargs,
        })
        return {
            "dry_run": False,
            "plan": {"needs_backfill": True},
            "actions": {"raw_rows_inserted": 10, "feature_rows_inserted": 10, "labels_saved": 10},
        }

    monkeypatch.setattr(api_module, "_load_strategy_data", fake_load_strategy_data)
    monkeypatch.setattr(api_module, "get_db", lambda: DummyDB())
    monkeypatch.setattr(backfill_module, "run_backfill_pipeline", fake_backfill)
    monkeypatch.setattr(api_module, "_compute_backtest_benchmarks", lambda *args, **kwargs: {})
    monkeypatch.setattr(api_module, "_compute_decision_profile", lambda trades: {})
    monkeypatch.setattr(api_module, "_compute_strategy_decision_quality_profile", lambda trades, db_path=None, db=None: {})
    monkeypatch.setattr(api_module, "_strategy_decision_contract_meta", lambda horizon_minutes=1440: {})
    monkeypatch.setattr(api_module, "_build_strategy_score_series", lambda *args, **kwargs: [])
    monkeypatch.setattr(strategy_lab, "save_strategy", lambda *args, **kwargs: None)

    def fake_run_rule_backtest(*args, **kwargs):
        result = strategy_lab.BacktestResult(
            roi=0.1,
            win_rate=1.0,
            total_trades=1,
            wins=1,
            losses=0,
            max_drawdown=0.01,
            profit_factor=2.0,
            total_pnl=100.0,
        )
        result.trades = [{"entry_timestamp": "2024-04-16T00:00:00Z", "timestamp": "2026-04-16T00:00:00Z", "pnl": 100.0, "entry_regime": "bull"}]
        result.equity_curve = [{"timestamp": "2024-04-16T00:00:00Z", "equity": 10000.0}]
        return result

    monkeypatch.setattr(strategy_lab, "run_rule_backtest", fake_run_rule_backtest)

    payload = api_module._execute_strategy_run(
        {
            "name": "Auto Backfill Demo",
            "type": "rule_based",
            "initial_capital": 10000.0,
            "auto_backfill": True,
            "backtest_range": {
                "start": "2024-04-16T00:00:00Z",
                "end": "2026-04-16T00:00:00Z",
            },
            "params": {
                "entry": {"bias50_max": 1.0, "nose_max": 0.4, "pulse_min": 0.0},
                "layers": [0.2, 0.3, 0.5],
                "stop_loss": -0.05,
                "take_profit_bias": 4.0,
                "take_profit_roi": 0.08,
            },
        }
    )

    assert backfill_calls, "auto_backfill should trigger backfill pipeline"
    assert backfill_calls[0]["apply_changes"] is True
    assert backfill_calls[0]["target_start"].startswith("2024-04-16")
    assert backfill_calls[0]["target_end"].startswith("2026-04-16")
    assert load_calls["count"] >= 2
    assert payload["results"]["backtest_range"]["backfill_required"] is False
    assert payload["results"]["backtest_range"]["effective"]["start"].startswith("2024-04-16")


def test_execute_strategy_run_hybrid_passes_local_turning_scores(monkeypatch):
    rows = [
        ("2025-04-03 13:00:00", 100.0, -1.0, -2.0, 0.2, 0.8, 0.0, "bull", 0.5, 1.0, 1.0, 0.66, 0.18),
        ("2025-04-04 13:00:00", 101.0, -0.8, -2.0, 0.2, 0.8, 0.0, "bull", 0.5, 1.0, 1.0, 0.71, 0.24),
    ]
    captured = {}

    class DummyDB:
        def close(self):
            return None

    train_df = api_module.pd.DataFrame(
        {
            "timestamp": api_module.pd.to_datetime(["2025-04-03 13:00:00", "2025-04-04 13:00:00"]),
            "close_price": [100.0, 101.0],
            "simulated_pyramid_win": [1, 0],
            "feat_4h_bias50": [-1.0, -0.8],
            "feat_4h_bias200": [-2.0, -2.0],
            "feat_nose": [0.2, 0.2],
            "feat_pulse": [0.8, 0.8],
            "feat_ear": [0.0, 0.0],
            "feat_local_bottom_score": [0.66, 0.71],
            "feat_local_top_score": [0.18, 0.24],
        }
    )

    class DummyModel:
        pass

    def fake_run_hybrid_backtest(*args, **kwargs):
        captured["local_bottom_score"] = kwargs.get("local_bottom_score")
        captured["local_top_score"] = kwargs.get("local_top_score")
        result = strategy_lab.BacktestResult(
            roi=0.12,
            win_rate=1.0,
            total_trades=1,
            wins=1,
            losses=0,
            max_drawdown=0.01,
            profit_factor=2.0,
            total_pnl=120.0,
        )
        result.trades = [{"entry_timestamp": "2025-04-03 13:00:00", "timestamp": "2025-04-04 13:00:00", "pnl": 120.0, "entry_regime": "bull"}]
        result.equity_curve = [{"timestamp": "2025-04-03 13:00:00", "equity": 10000.0}]
        return result

    monkeypatch.setattr(api_module, "_load_strategy_data", lambda: rows)
    monkeypatch.setattr(api_module, "get_db", lambda: DummyDB())
    monkeypatch.setattr(api_module, "_get_sqlite_db_path", lambda db: "test.db")
    monkeypatch.setattr(api_module, "load_model_leaderboard_frame", lambda db_path=None: train_df.copy())
    monkeypatch.setattr(api_module, "_compute_backtest_benchmarks", lambda *args, **kwargs: {})
    monkeypatch.setattr(api_module, "_compute_decision_profile", lambda trades: {})
    monkeypatch.setattr(api_module, "_compute_strategy_decision_quality_profile", lambda trades, db_path=None, db=None: {})
    monkeypatch.setattr(api_module, "_strategy_decision_contract_meta", lambda horizon_minutes=1440: {})
    monkeypatch.setattr(api_module, "_build_strategy_score_series", lambda *args, **kwargs: [])
    monkeypatch.setattr(strategy_lab, "save_strategy", lambda *args, **kwargs: None)
    monkeypatch.setattr(strategy_lab, "run_hybrid_backtest", fake_run_hybrid_backtest)

    from backtesting.model_leaderboard import ModelLeaderboard

    monkeypatch.setattr(ModelLeaderboard, "_train_model", lambda self, X_train, y_train, model_name: DummyModel())
    monkeypatch.setattr(ModelLeaderboard, "_get_confidence", lambda self, model, X_test, model_name: __import__("numpy").array([0.62, 0.65]))

    payload = api_module._execute_strategy_run(
        {
            "name": "Hybrid Local Score Demo",
            "type": "hybrid",
            "initial_capital": 10000.0,
            "params": {
                "model_name": "xgboost",
                "entry": {"bias50_max": 1.0, "confidence_min": 0.5, "entry_quality_min": 0.5},
                "layers": [0.2, 0.3, 0.5],
                "stop_loss": -0.05,
                "take_profit_bias": 4.0,
                "take_profit_roi": 0.08,
                "turning_point": {"enabled": True, "bottom_score_min": 0.62, "top_score_take_profit": 0.8},
                "editor_modules": ["turning_point"],
            },
        }
    )

    assert payload["results"]["roi"] == pytest.approx(0.12)
    assert captured["local_bottom_score"] == [0.66, 0.71]
    assert captured["local_top_score"] == [0.18, 0.24]


def test_strategy_async_job_status_exposes_segmented_steps(monkeypatch):
    monkeypatch.setattr(api_module.uuid, "uuid4", lambda: SimpleNamespace(hex="job-segmented"))

    submitted = {"called": False}

    class ImmediateExecutor:
        def submit(self, fn):
            submitted["called"] = True
            fn()
            return SimpleNamespace()

    monkeypatch.setattr(api_module, "_STRATEGY_RUN_EXECUTOR", ImmediateExecutor())

    def fake_execute(body, job_id=None):
        api_module._set_strategy_job_progress(job_id, 14, "正在回填 BTCUSDT 原始行情。", stage_key="backfill_raw")
        api_module._set_strategy_job_progress(job_id, 17, "正在補算 features。", stage_key="backfill_features")
        api_module._set_strategy_job_progress(job_id, 92, "正在儲存結果。", stage_key="save_results")
        return {"results": {"roi": 0.1}}

    monkeypatch.setattr(api_module, "_execute_strategy_run", fake_execute)

    kickoff = asyncio.run(api_module.api_run_strategy_async({"type": "rule_based", "auto_backfill": True, "params": {}}, request=_local_request()))
    status = asyncio.run(api_module.api_strategy_job_status(kickoff["job_id"], request=_local_request()))

    assert submitted["called"] is True
    assert status["stage_key"] == "save_results"
    assert isinstance(status.get("steps"), list) and status["steps"]
    by_key = {step["key"]: step["status"] for step in status["steps"]}
    assert by_key["backfill_raw"] == "completed"
    assert by_key["backfill_features"] == "completed"
    assert by_key["save_results"] == "completed"



def test_api_trade_uses_execution_service(monkeypatch):
    class DummyService:
        def __init__(self, cfg, db_session=None):
            self.cfg = cfg
        def submit_order(self, *, side, symbol, qty, order_type, reduce_only=False, **kwargs):
            return {
                "success": True,
                "dry_run": True,
                "venue": "binance",
                "guardrails": {"consecutive_failures": 0, "daily_loss_halt": False},
                "order": {"id": "abc123", "symbol": symbol, "side": side, "qty": qty, "type": order_type, "reduce_only": reduce_only},
            }

    monkeypatch.setattr(api_module, "get_config", lambda: {"execution": {"venue": "binance"}, "trading": {"venue": "binance"}})
    monkeypatch.setattr(api_module, "get_db", lambda: object())
    monkeypatch.setattr(api_module, "ExecutionService", DummyService)

    payload = asyncio.run(api_module.api_trade(api_module.TradeRequest(side="buy", symbol="BTCUSDT", qty=0.01), request=_local_request()))

    assert payload["success"] is True
    assert payload["venue"] == "binance"
    assert payload["order_id"] == "abc123"
    assert payload["guardrails"]["consecutive_failures"] == 0
    assert payload["order"]["type"] == "market"



def test_compute_backtest_benchmarks_returns_dynamic_buy_hold_and_blind():
    benchmarks = _compute_backtest_benchmarks(
        prices=[100.0, 105.0, 102.0, 110.0],
        timestamps=[
            "2026-01-01T00:00:00Z",
            "2026-01-01T01:00:00Z",
            "2026-01-01T02:00:00Z",
            "2026-01-01T03:00:00Z",
        ],
        bias50=[0.0, -2.0, -4.0, 5.0],
        bias200=[2.0, 2.0, 2.0, 2.0],
        nose=[0.2, 0.2, 0.2, 0.2],
        pulse=[0.6, 0.6, 0.6, 0.6],
        ear=[0.0, 0.0, 0.0, 0.0],
        regimes=["bull", "bull", "bull", "bull"],
        initial_capital=1000.0,
        params={
            "entry": {"bias50_max": 1.0, "nose_max": 0.4, "pulse_min": 0.0, "layer2_bias_max": -1.5, "layer3_bias_max": -3.5},
            "layers": [0.2, 0.3, 0.5],
            "stop_loss": -0.05,
            "take_profit_bias": 4.0,
            "take_profit_roi": 0.08,
        },
    )

    assert benchmarks["buy_hold"]["roi"] == pytest.approx(0.10)
    assert benchmarks["blind_pyramid"]["total_trades"] >= 1
    assert benchmarks["blind_pyramid"]["roi"] is not None


def test_compute_strategy_risk_flags_low_sample_and_high_drawdown():
    risk = _compute_strategy_risk({
        "total_trades": 8,
        "max_drawdown": 0.41,
        "max_consecutive_losses": 5,
        "roi": 0.26,
        "win_rate": 0.75,
    })

    assert risk["overfit_risk"] == "high"
    assert risk["trade_sufficiency"] == "low"
    assert "交易數過少" in risk["risk_reasons"]


def test_api_klines_incremental_append_only_returns_missing_tail(monkeypatch):
    base_ts = 1_700_000_000_000
    interval_ms = 3_600_000
    rows = [
        [base_ts + interval_ms * idx, 100 + idx, 101 + idx, 99 + idx, 100.5 + idx, 10 + idx]
        for idx in range(6)
    ]

    class DummyExchange:
        def __init__(self):
            self.calls = []

        def fetch_ohlcv(self, symbol, interval, since=None, limit=None):
            self.calls.append({"symbol": symbol, "interval": interval, "since": since, "limit": limit})
            return rows

    exchange = DummyExchange()
    monkeypatch.setattr(api_module.ccxt, "binance", lambda: exchange)
    api_module._KLINE_RESPONSE_CACHE.clear()

    payload = asyncio.run(
        api_klines(
            symbol="BTCUSDT",
            interval="1h",
            limit=120,
            since=base_ts,
            append_after=base_ts + interval_ms * 2,
        )
    )

    assert payload["incremental"] is True
    assert [candle["time"] for candle in payload["candles"]] == [
        int((base_ts + interval_ms * 3) / 1000),
        int((base_ts + interval_ms * 4) / 1000),
        int((base_ts + interval_ms * 5) / 1000),
    ]
    assert len(payload["indicators"]["ma20"]) == 3
    assert exchange.calls[0]["since"] <= base_ts + interval_ms * 2


def test_api_klines_paginates_when_requested_range_exceeds_1000_bars(monkeypatch):
    base_ts = 1_700_000_000_000
    interval_ms = 14_400_000
    first_page = [
        [base_ts + interval_ms * idx, 100 + idx, 101 + idx, 99 + idx, 100.5 + idx, 10 + idx]
        for idx in range(1000)
    ]
    second_page = [
        [base_ts + interval_ms * (1000 + idx), 200 + idx, 201 + idx, 199 + idx, 200.5 + idx, 20 + idx]
        for idx in range(200)
    ]

    class DummyExchange:
        def __init__(self):
            self.calls = []

        def fetch_ohlcv(self, symbol, interval, since=None, limit=None):
            self.calls.append({"symbol": symbol, "interval": interval, "since": since, "limit": limit})
            return first_page if len(self.calls) == 1 else second_page

    exchange = DummyExchange()
    monkeypatch.setattr(api_module.ccxt, "binance", lambda: exchange)
    api_module._KLINE_RESPONSE_CACHE.clear()

    payload = asyncio.run(
        api_klines(
            symbol="BTCUSDT",
            interval="4h",
            limit=1220,
            since=base_ts,
            until=base_ts + interval_ms * 1199,
        )
    )

    assert len(exchange.calls) >= 2
    assert len(payload["candles"]) == 1200
    assert payload["candles"][0]["time"] == int(base_ts / 1000)
    assert payload["candles"][-1]["time"] == int((base_ts + interval_ms * 1199) / 1000)


def test_decorate_strategy_entry_adds_risk_fields():
    entry = {
        "name": "Stable Strategy",
        "run_count": 2,
        "last_results": {
            "total_trades": 48,
            "max_drawdown": 0.12,
            "max_consecutive_losses": 1,
            "roi": 0.08,
            "win_rate": 0.58,
        },
    }

    enriched = _decorate_strategy_entry(entry)

    assert enriched["stability_label"] in {"穩定", "中等"}
    assert enriched["overfit_risk"] == "low"
    assert enriched["trade_sufficiency"] == "high"
    assert enriched["overall_score"] is not None
    assert enriched["last_results"]["overall_score"] == enriched["overall_score"]
    assert enriched["last_results"]["reliability_score"] is not None


def test_decorate_strategy_entry_attaches_decision_contract_meta():
    entry = {
        "name": "Canonical Strategy",
        "run_count": 1,
        "last_results": {
            "decision_quality_horizon_minutes": 240,
            "avg_decision_quality_score": 0.31,
        },
    }

    enriched = _decorate_strategy_entry(entry)

    assert enriched["decision_contract"]["target_col"] == _strategy_decision_contract_meta(horizon_minutes=240)["target_col"]
    assert enriched["decision_contract"]["decision_quality_horizon_minutes"] == 240
    assert enriched["decision_contract"]["sort_semantics"] is not None
    assert enriched["last_results"]["target_col"] == "simulated_pyramid_win"
    assert enriched["last_results"]["target_label"] == "Canonical Decision Quality"
    assert enriched["last_results"]["sort_semantics"] is not None
    assert "avg_expected_win_rate" not in enriched["decision_contract"]


def test_decorate_strategy_entry_surfaces_turning_point_exit_gate():
    entry = {
        "name": "Top Exit Hybrid",
        "definition": {
            "type": "hybrid",
            "params": {
                "model_name": "xgboost",
                "turning_point": {"enabled": True, "top_score_take_profit": 0.68},
            },
        },
        "metadata": {
            "title": "Top Exit Hybrid",
            "description": "頂部轉折 exit gate",
            "model_name": "xgboost",
            "model_summary": "xgboost：test",
        },
        "last_results": {
            "overall_score": 0.82,
            "roi": 0.12,
            "max_drawdown": 0.08,
            "win_rate": 0.61,
        },
    }

    enriched = _decorate_strategy_entry(entry)

    assert enriched["metadata"]["model_name"] == "xgboost"
    assert enriched["metadata"]["description"] == "頂部轉折 exit gate"
    assert enriched["last_results"]["overall_score"] is not None
    assert enriched["overall_score"] is not None


def test_api_get_strategy_decorates_detail_payload(monkeypatch):
    class DummyDB:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    strategy_entry = {
        "name": "Auto Leaderboard · 測試策略",
        "definition": {"type": "hybrid", "params": {"model_name": "xgboost"}},
        "run_count": 3,
        "last_results": {
            "roi": 0.18,
            "win_rate": 0.62,
            "max_drawdown": 0.09,
            "profit_factor": 1.55,
            "total_trades": 24,
            "wins": 15,
            "losses": 9,
            "avg_allowed_layers": 1.8,
            "avg_decision_quality_score": 0.33,
            "avg_expected_time_underwater": 0.27,
            "decision_quality_horizon_minutes": 1440,
            "trades": [
                {
                    "timestamp": "2026-04-01T00:00:00Z",
                    "entry": 100.0,
                    "exit": 110.0,
                    "pnl": 50.0,
                    "reason": "tp_roi",
                    "allowed_layers": 2,
                    "entry_quality": 0.64,
                    "regime_gate": "CAUTION",
                }
            ],
        },
    }
    db = DummyDB()

    monkeypatch.setattr(strategy_lab, "load_strategy", lambda name: strategy_entry if name == strategy_entry["name"] else None)
    monkeypatch.setattr(api_module, "get_db", lambda: db)

    payload = asyncio.run(api_module.api_get_strategy(strategy_entry["name"]))

    assert payload["name"] == strategy_entry["name"]
    assert payload["last_results"]["overall_score"] is not None
    assert payload["last_results"]["reliability_score"] is not None
    assert payload["last_results"]["target_label"] == "Canonical Decision Quality"
    assert payload["last_results"]["sort_semantics"] is not None
    assert payload["decision_contract"]["target_col"] == "simulated_pyramid_win"
    assert payload["last_results"]["trades"][0]["reason"] == "tp_roi"
    assert db.closed is True


def test_compute_decision_profile_returns_gate_summary():
    profile = api_module._compute_decision_profile(
        [
            {"entry_quality": 0.72, "allowed_layers": 3, "regime_gate": "ALLOW", "pnl": 120.0},
            {"entry_quality": 0.51, "allowed_layers": 1, "regime_gate": "CAUTION", "pnl": -30.0},
            {"entry_quality": 0.48, "allowed_layers": 0, "regime_gate": "CAUTION", "pnl": -10.0},
        ]
    )

    assert profile["dominant_regime_gate"] == "CAUTION"
    assert profile["regime_gate_summary"] == {"ALLOW": 1, "CAUTION": 2, "BLOCK": 0}


def test_decorate_strategy_entry_backfills_gate_summary_from_complete_trades():
    entry = {
        "name": "Legacy Strategy",
        "run_count": 1,
        "last_results": {
            "total_trades": 3,
            "trades": [
                {"entry_quality": 0.72, "allowed_layers": 3, "regime_gate": "ALLOW", "pnl": 120.0},
                {"entry_quality": 0.51, "allowed_layers": 1, "regime_gate": "CAUTION", "pnl": -30.0},
                {"entry_quality": 0.48, "allowed_layers": 0, "regime_gate": "CAUTION", "pnl": -10.0},
            ],
        },
    }

    enriched = _decorate_strategy_entry(entry)

    assert enriched["last_results"]["dominant_regime_gate"] == "CAUTION"
    assert enriched["last_results"]["regime_gate_summary"] == {"ALLOW": 1, "CAUTION": 2, "BLOCK": 0}


def test_api_strategy_leaderboard_keeps_manual_rows_visible_when_auto_candidates_exist(monkeypatch):
    class DummyDB:
        def close(self):
            return None

    called = {"ensure": 0}
    monkeypatch.setattr(api_module, "_ensure_auto_generated_strategy_leaderboard", lambda force=False: called.__setitem__("ensure", called["ensure"] + 1))
    monkeypatch.setattr(api_module, "get_db", lambda: DummyDB())
    monkeypatch.setattr(api_module, "_decorate_strategy_entry", lambda entry, db=None: entry)
    monkeypatch.setattr(api_module, "_persist_strategy_leaderboard_snapshot", lambda *args, **kwargs: None)
    monkeypatch.setattr(api_module, "_load_recent_strategy_leaderboard_snapshots", lambda *args, **kwargs: [])
    monkeypatch.setattr(api_module, "_compute_strategy_rank_deltas", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        strategy_lab,
        "load_all_strategies",
        lambda include_internal=False: [
            {"name": f"{strategy_lab.AUTO_STRATEGY_NAME_PREFIX}平衡承接 #01", "is_internal": True, "metadata": {"source": "auto_leaderboard"}, "last_results": {"overall_score": 0.8}},
            {"name": "Manual Scratch", "is_internal": False, "metadata": {"source": "user_saved"}, "last_results": {"overall_score": 0.9}},
        ],
    )

    payload = asyncio.run(api_module.api_strategy_leaderboard())

    assert called["ensure"] == 1
    assert [row["name"] for row in payload["strategies"]] == ["Manual Scratch", f"{strategy_lab.AUTO_STRATEGY_NAME_PREFIX}平衡承接 #01"]


def test_api_strategy_leaderboard_rank_delta_uses_fresh_snapshot(monkeypatch, tmp_path: Path):
    db_path = str(tmp_path / "strategy_lb.db")

    class DummyDB:
        def close(self):
            return None

    state = {
        "rows": [
            {"name": "Strategy A", "last_results": {"overall_score": 0.9}},
            {"name": "Strategy B", "last_results": {"overall_score": 0.8}},
        ]
    }

    monkeypatch.setattr(api_module, "DB_PATH", db_path)
    monkeypatch.setattr(api_module, "get_db", lambda: DummyDB())
    monkeypatch.setattr(api_module, "_ensure_auto_generated_strategy_leaderboard", lambda force=False: None)
    monkeypatch.setattr(api_module, "_decorate_strategy_entry", lambda entry, db=None: entry)
    monkeypatch.setattr(strategy_lab, "load_all_strategies", lambda include_internal=True: list(state["rows"]))
    api_module._persist_strategy_leaderboard_snapshot(list(state["rows"]), db_path=db_path)

    first = asyncio.run(api_module.api_strategy_leaderboard())
    first_by_name = {row["name"]: row["rank_delta"] for row in first["strategies"]}
    assert first_by_name == {"Strategy A": 0, "Strategy B": 0}

    state["rows"] = [
        {"name": "Strategy B", "last_results": {"overall_score": 0.95}},
        {"name": "Strategy A", "last_results": {"overall_score": 0.7}},
    ]
    second = asyncio.run(api_module.api_strategy_leaderboard())
    second_by_name = {row["name"]: row["rank_delta"] for row in second["strategies"]}

    assert second_by_name["Strategy B"] == 1
    assert second_by_name["Strategy A"] == -1


def test_compute_strategy_decision_quality_profile_uses_canonical_label_fields(tmp_path: Path):
    db_path = tmp_path / "strategy_quality.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE labels (
                timestamp TEXT,
                horizon_minutes INTEGER,
                simulated_pyramid_win REAL,
                simulated_pyramid_pnl REAL,
                simulated_pyramid_quality REAL,
                simulated_pyramid_drawdown_penalty REAL,
                simulated_pyramid_time_underwater REAL
            )
            """
        )
        conn.executemany(
            "INSERT INTO labels VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("2026-04-10 00:00:00", 1440, 0.80, 0.12, 0.66, 0.11, 0.18),
                ("2026-04-10 04:00:00", 1440, 0.60, 0.05, 0.44, 0.19, 0.31),
                ("2026-04-10 04:00:00", 240, 0.99, 0.30, 0.90, 0.01, 0.02),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    fake_db = SimpleNamespace(get_bind=lambda: SimpleNamespace(url=SimpleNamespace(database=str(db_path))))
    profile = _compute_strategy_decision_quality_profile(
        [
            {"entry_timestamp": "2026-04-10T00:00:00Z"},
            {"entry_timestamp": "2026-04-10 04:00:00"},
        ],
        db=fake_db,
    )

    assert profile["target_col"] == "simulated_pyramid_win"
    assert profile["decision_quality_horizon_minutes"] == 1440
    assert profile["decision_quality_sample_size"] == 2
    assert profile["avg_expected_win_rate"] == pytest.approx(0.7)
    assert profile["avg_expected_pyramid_pnl"] == pytest.approx(0.085)
    assert profile["avg_expected_pyramid_quality"] == pytest.approx(0.55)
    assert profile["avg_expected_drawdown_penalty"] == pytest.approx(0.15)
    assert profile["avg_expected_time_underwater"] == pytest.approx(0.245)
    assert profile["avg_decision_quality_score"] is not None
    assert profile["decision_quality_label"] is not None



def test_strategy_leaderboard_sort_key_prefers_overall_and_reliability_before_raw_win_rate():
    stronger_scorecard = {
        "last_results": {
            "overall_score": 0.72,
            "reliability_score": 0.75,
            "return_power_score": 0.63,
            "risk_control_score": 0.71,
            "capital_efficiency_score": 0.66,
            "roi": 0.18,
            "max_drawdown": 0.08,
        }
    }
    weaker_but_flashier = {
        "last_results": {
            "overall_score": 0.51,
            "reliability_score": 0.42,
            "return_power_score": 0.59,
            "risk_control_score": 0.38,
            "capital_efficiency_score": 0.44,
            "roi": 0.09,
            "max_drawdown": 0.27,
        }
    }

    assert _strategy_leaderboard_sort_key(stronger_scorecard) > _strategy_leaderboard_sort_key(weaker_but_flashier)



def test_entry_quality_penalizes_4h_collapse_pocket():
    supportive = strategy_lab._compute_entry_quality(-1.8, 0.22, 0.84, -0.04, 0.88, 8.4, 10.2)
    collapsing = strategy_lab._compute_entry_quality(-1.8, 0.22, 0.84, -0.04, 0.12, 0.4, 1.7)

    assert supportive > collapsing
    assert collapsing < 0.68



def test_compute_regime_gate_downgrades_allow_when_4h_structure_collapses():
    gate = strategy_lab._compute_regime_gate(
        2.0,
        "bull",
        -10.0,
        bb_pct_b_value=0.10,
        dist_bb_lower_value=0.35,
        dist_swing_low_value=1.5,
    )

    assert gate == "BLOCK"


def test_compute_regime_gate_downgrades_borderline_allow_q35_to_caution():
    gate = strategy_lab._compute_regime_gate(
        1.8,
        "bull",
        -10.0,
        bb_pct_b_value=0.45,
        dist_bb_lower_value=5.0,
        dist_swing_low_value=6.0,
    )

    assert gate == "CAUTION"


@pytest.mark.parametrize(
    ("bb_pct_b_value", "dist_bb_lower_value", "dist_swing_low_value"),
    [
        (0.45, 5.0, 6.0),
        (0.75, 6.2, 7.1),
    ],
)
def test_compute_regime_gate_blocks_bull_high_bias200_overheat_pocket(
    bb_pct_b_value,
    dist_bb_lower_value,
    dist_swing_low_value,
):
    gate = strategy_lab._compute_regime_gate(
        9.2,
        "bull",
        -10.0,
        bb_pct_b_value=bb_pct_b_value,
        dist_bb_lower_value=dist_bb_lower_value,
        dist_swing_low_value=dist_swing_low_value,
    )

    assert gate == "BLOCK"


def test_run_rule_backtest_records_regime_gate_and_entry_quality():
    result = strategy_lab.run_rule_backtest(
        prices=[100.0, 98.0, 96.0, 108.0],
        timestamps=[
            "2026-01-01T00:00:00Z",
            "2026-01-01T04:00:00Z",
            "2026-01-01T08:00:00Z",
            "2026-01-01T12:00:00Z",
        ],
        bias50=[-1.0, -2.2, -4.2, 5.0],
        bias200=[3.0, 2.5, 2.0, 3.5],
        nose=[0.22, 0.20, 0.18, 0.35],
        pulse=[0.82, 0.84, 0.86, 0.40],
        ear=[-0.05, -0.04, -0.03, 0.02],
        params={
            "entry": {
                "bias50_max": 1.0,
                "nose_max": 0.4,
                "pulse_min": 0.0,
                "layer2_bias_max": -1.5,
                "layer3_bias_max": -3.5,
                "regime_bias200_min": -10.0,
            },
            "layers": [0.2, 0.3, 0.5],
            "stop_loss": -0.05,
            "take_profit_bias": 4.0,
            "take_profit_roi": 0.08,
        },
        initial_capital=1000.0,
        regimes=["bull", "bull", "bull", "bull"],
    )

    assert result.total_trades == 1
    trade = result.trades[0]
    assert trade["regime_gate"] == "ALLOW"
    assert trade["allowed_layers"] == 3
    assert trade["entry_quality"] > 0.72


def test_run_rule_backtest_blocks_bull_q15_bias50_overextended_pocket():
    result = strategy_lab.run_rule_backtest(
        prices=[100.0, 100.5, 101.0, 101.5],
        timestamps=[
            "2026-02-02T00:00:00Z",
            "2026-02-02T04:00:00Z",
            "2026-02-02T08:00:00Z",
            "2026-02-02T12:00:00Z",
        ],
        bias50=[1.8, 1.8, 1.8, 4.5],
        bias200=[2.4, 2.4, 2.4, 2.4],
        nose=[0.0, 0.0, 0.0, 0.0],
        pulse=[1.0, 1.0, 1.0, 1.0],
        ear=[0.0, 0.0, 0.0, 0.0],
        params={
            "entry": {
                "bias50_max": 3.0,
                "nose_max": 1.0,
                "pulse_min": 0.0,
                "layer2_bias_max": 2.0,
                "layer3_bias_max": 0.5,
                "regime_bias200_min": -10.0,
                "entry_quality_min": 0.55,
            },
            "layers": [0.2, 0.3, 0.5],
            "stop_loss": -0.20,
            "take_profit_bias": 999.0,
            "take_profit_roi": 0.50,
        },
        initial_capital=1000.0,
        regimes=["bull"] * 4,
        bb_pct_b_4h=[0.30] * 4,
        dist_bb_lower_4h=[1.2] * 4,
        dist_swing_low_4h=[4.0] * 4,
    )

    assert result.total_trades == 0
    assert all(point["regime_gate"] == "BLOCK" for point in result.equity_curve)
    assert all(point["allowed_layers"] == 0 for point in result.equity_curve)


def test_run_rule_backtest_reserve_mode_uses_10_percent_probe_before_unlocking_reserve():
    result = strategy_lab.run_rule_backtest(
        prices=[100.0, 100.0, 89.0, 89.0, 108.0],
        timestamps=[
            "2026-01-01T00:00:00Z",
            "2026-01-01T01:00:00Z",
            "2026-01-01T02:00:00Z",
            "2026-01-01T03:00:00Z",
            "2026-01-01T04:00:00Z",
        ],
        bias50=[0.0, -3.0, -3.2, -3.4, 5.2],
        bias200=[1.0, 1.0, 1.0, 1.0, 1.0],
        nose=[0.2, 0.2, 0.2, 0.2, 0.2],
        pulse=[0.7, 0.7, 0.7, 0.7, 0.7],
        ear=[0.0, 0.0, 0.0, 0.0, 0.0],
        params={
            "entry": {
                "bias50_max": 0.5,
                "nose_max": 0.4,
                "pulse_min": 0.0,
                "layer2_bias_max": -2.0,
                "layer3_bias_max": -3.0,
            },
            "layers": [0.2, 0.3, 0.5],
            "capital_management": {"mode": "reserve_90", "base_entry_fraction": 0.10, "reserve_trigger_drawdown": 0.10},
            "stop_loss": -0.20,
            "take_profit_bias": 4.0,
            "take_profit_roi": 0.50,
        },
        initial_capital=1000.0,
        regimes=["bull"] * 5,
    )

    assert result.total_trades == 1
    assert result.trades[0]["capital_mode"] == "reserve_90"
    # First layer should be 10% probe, then remaining reserve unlocks on 11% drawdown.
    first_curve = next(point for point in result.equity_curve if point["position_layers"] == 1)
    two_layer_curve = next(point for point in result.equity_curve if point["position_layers"] >= 2)
    assert first_curve["position_pct"] == pytest.approx(0.10)
    assert two_layer_curve["position_pct"] > first_curve["position_pct"]
    assert result.total_pnl > 0



def test_run_rule_backtest_storm_unwind_releases_highest_trapped_layer():
    result = strategy_lab.run_rule_backtest(
        prices=[100.0, 50.0, 40.0, 42.0, 42.0],
        timestamps=[
            "2026-03-01T00:00:00Z",
            "2026-03-01T01:00:00Z",
            "2026-03-01T02:00:00Z",
            "2026-03-01T03:00:00Z",
            "2026-03-01T04:00:00Z",
        ],
        bias50=[0.0, -3.0, -5.0, 4.0, 4.0],
        bias200=[1.0, 1.0, 1.0, 1.0, 1.0],
        nose=[0.2, 0.2, 0.2, 0.2, 0.2],
        pulse=[0.7, 0.7, 0.7, 0.7, 0.7],
        ear=[0.0, 0.0, 0.0, 0.0, 0.0],
        params={
            "entry": {
                "bias50_max": 1.0,
                "nose_max": 0.4,
                "pulse_min": 0.0,
                "layer2_bias_max": -2.0,
                "layer3_bias_max": -4.0,
            },
            "layers": [0.2, 0.3, 0.5],
            "capital_management": {"mode": "reserve_90", "base_entry_fraction": 0.10, "reserve_trigger_drawdown": 0.10},
            "stop_loss": -0.90,
            "take_profit_bias": 3.0,
            "take_profit_roi": 0.50,
            "storm_unwind": {"enabled": True, "release_ratio": 0.25, "min_profit_pct": 0.01},
            "editor_modules": ["reserve_90", "storm_unwind"],
        },
        initial_capital=1000.0,
        regimes=["bull"] * 5,
    )

    storm_trade = next(trade for trade in result.trades if trade["reason"] == "storm_unwind_tp")
    assert storm_trade["storm_unwind_enabled"] is True
    assert storm_trade["storm_released_coins"] > 0
    assert storm_trade["storm_release_from_price"] == pytest.approx(100.0)
    assert storm_trade["remaining_trapped_coins"] > 0


def test_run_rule_backtest_caps_layers_when_regime_gate_is_caution():
    result = strategy_lab.run_rule_backtest(
        prices=[100.0, 98.0, 96.0, 109.0],
        timestamps=[
            "2026-02-01T00:00:00Z",
            "2026-02-01T04:00:00Z",
            "2026-02-01T08:00:00Z",
            "2026-02-01T12:00:00Z",
        ],
        bias50=[-1.0, -2.3, -4.5, 5.0],
        bias200=[-2.0, -2.0, -2.0, -2.0],
        nose=[0.22, 0.20, 0.18, 0.35],
        pulse=[0.82, 0.84, 0.86, 0.40],
        ear=[-0.05, -0.04, -0.03, 0.02],
        params={
            "entry": {
                "bias50_max": 1.0,
                "nose_max": 0.4,
                "pulse_min": 0.0,
                "layer2_bias_max": -1.5,
                "layer3_bias_max": -3.5,
                "regime_bias200_min": -10.0,
            },
            "layers": [0.2, 0.3, 0.5],
            "stop_loss": -0.05,
            "take_profit_bias": 4.0,
            "take_profit_roi": 0.08,
        },
        initial_capital=1000.0,
        regimes=["chop", "chop", "chop", "chop"],
    )

    assert result.total_trades == 1
    trade = result.trades[0]
    assert trade["regime_gate"] == "CAUTION"
    assert trade["allowed_layers"] == 2
    assert trade["layers"] == 2
