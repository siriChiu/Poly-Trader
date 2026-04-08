from pathlib import Path

import pytest

from backtesting import strategy_lab
from server.routes.api import _compute_backtest_benchmarks, _compute_regime_breakdown, _compute_strategy_risk, _decorate_strategy_entry


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
