import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from backtesting import strategy_lab
from server.routes.api import (
    _compute_backtest_benchmarks,
    _compute_regime_breakdown,
    _compute_strategy_risk,
    _decorate_strategy_entry,
    _compute_strategy_decision_quality_profile,
    _strategy_leaderboard_sort_key,
)


@pytest.fixture
def isolated_strategies_dir(tmp_path: Path, monkeypatch):
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    monkeypatch.setattr(strategy_lab, "STRATEGIES_DIR", strategies_dir)
    return strategies_dir


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



def test_strategy_leaderboard_sort_key_prefers_decision_quality_before_roi():
    high_dq = {
        "last_results": {
            "avg_decision_quality_score": 0.41,
            "avg_expected_win_rate": 0.71,
            "avg_expected_drawdown_penalty": 0.14,
            "roi": 0.06,
            "total_trades": 40,
        }
    }
    low_dq_high_roi = {
        "last_results": {
            "avg_decision_quality_score": 0.22,
            "avg_expected_win_rate": 0.61,
            "avg_expected_drawdown_penalty": 0.28,
            "roi": 0.22,
            "total_trades": 40,
        }
    }

    assert _strategy_leaderboard_sort_key(high_dq) > _strategy_leaderboard_sort_key(low_dq_high_roi)



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
