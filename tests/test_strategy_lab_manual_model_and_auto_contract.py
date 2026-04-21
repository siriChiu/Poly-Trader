from pathlib import Path

import pandas as pd
import pytest

from backtesting import strategy_lab
from server.routes import api as api_module


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "web" / "src"


def _read(relative_path: str) -> str:
    return (WEB_SRC / relative_path).read_text(encoding="utf-8")


@pytest.fixture()
def isolated_strategies_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    monkeypatch.setattr(strategy_lab, "STRATEGIES_DIR", strategies_dir)
    return strategies_dir


def test_auto_leaderboard_strategy_metadata_marks_system_generated_and_immutable(isolated_strategies_dir: Path):
    strategy_lab.save_strategy(
        "Auto Leaderboard · 重掃 xgboost Hybrid #01",
        {
            "type": "hybrid",
            "params": {
                "model_name": "xgboost",
                "entry": {"bias50_max": 0.0},
            },
        },
        {"roi": 0.12, "win_rate": 0.63},
    )

    loaded = strategy_lab.load_strategy("Auto Leaderboard · 重掃 xgboost Hybrid #01")

    assert loaded is not None
    assert loaded["is_internal"] is True
    assert loaded["metadata"]["source"] == "auto_leaderboard"
    assert loaded["metadata"]["source_label"] == "系統生成排行榜"
    assert loaded["metadata"]["immutable"] is True
    assert loaded["metadata"]["editable_clone_required"] is True


@pytest.fixture()
def patched_strategy_run_env(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_save_strategy(name, strategy_def, results=None):
        captured["name"] = name
        captured["strategy_def"] = strategy_def
        captured["results"] = results
        return "/tmp/fake.json"

    monkeypatch.setattr(strategy_lab, "save_strategy", fake_save_strategy)
    monkeypatch.setattr(
        api_module,
        "load_model_leaderboard_frame",
        lambda db_path=None: pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2026-01-01 00:00:00", "2026-01-02 00:00:00", "2026-01-03 00:00:00"]),
                "feat_eye": [0.1, 0.2, 0.3],
                "simulated_pyramid_win": [1, 0, 1],
            }
        ),
    )
    monkeypatch.setattr(api_module, "get_db", lambda: None)
    monkeypatch.setattr(api_module, "_set_strategy_job_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(api_module, "_build_strategy_chart_context", lambda timestamps: {"symbol": "BTCUSDT", "interval": "4h", "start": timestamps[0], "end": timestamps[-1]})
    monkeypatch.setattr(api_module, "_select_strategy_chart_payload", lambda **kwargs: {"chart_context": {"symbol": "BTCUSDT", "interval": "4h", "start": kwargs["timestamps"][0], "end": kwargs["timestamps"][-1]}, "equity_curve": [], "trades": []})
    monkeypatch.setattr(api_module, "_compute_backtest_benchmarks", lambda *args, **kwargs: [])
    monkeypatch.setattr(api_module, "_compute_decision_profile", lambda trades: {"dominant_regime_gate": "CAUTION", "regime_gate_summary": {"ALLOW": 0, "CAUTION": 1, "BLOCK": 0}})
    monkeypatch.setattr(api_module, "_compute_strategy_decision_quality_profile", lambda *args, **kwargs: {"avg_decision_quality_score": 0.5})
    monkeypatch.setattr(api_module, "_normalize_result_timestamps", lambda payload: payload)
    monkeypatch.setattr(api_module, "_strategy_decision_contract_meta", lambda horizon_minutes=1440: {})
    monkeypatch.setattr(api_module, "_load_strategy_data", lambda: [
        ("2026-01-01 00:00:00", 100.0, 0.0, 10.0, 0.2, 1.0, 0.0, "bull", 0.5, 1.0, 1.0, 0.0, 0.0),
        ("2026-01-02 00:00:00", 101.0, -0.5, 10.0, 0.2, 1.0, 0.0, "bull", 0.5, 1.0, 1.0, 0.0, 0.0),
        ("2026-01-03 00:00:00", 102.0, -1.0, 10.0, 0.2, 1.0, 0.0, "bull", 0.5, 1.0, 1.0, 0.0, 0.0),
    ])

    class Result:
        roi = 0.1
        win_rate = 0.6
        total_trades = 1
        wins = 1
        losses = 0
        max_drawdown = 0.02
        profit_factor = 1.2
        total_pnl = 100.0
        avg_win = 100.0
        avg_loss = 0.0
        max_consecutive_losses = 0
        equity_curve = []
        trades = [{"timestamp": "2026-01-02 00:00:00", "regime_gate": "CAUTION"}]

    monkeypatch.setattr(strategy_lab, "run_hybrid_backtest", lambda *args, **kwargs: Result())
    monkeypatch.setattr(api_module, "_build_strategy_score_series", lambda *args, **kwargs: [])

    class FakeLeaderboard:
        def __init__(self, *args, **kwargs):
            pass

        def _train_model(self, *args, **kwargs):
            return object()

        def _get_confidence(self, model, X, model_name):
            return [0.8 for _ in range(len(X))]

    from backtesting import model_leaderboard as leaderboard_module
    monkeypatch.setattr(leaderboard_module, "ModelLeaderboard", FakeLeaderboard)
    return captured


def test_execute_strategy_run_rejects_system_generated_strategy_until_operator_supplies_unique_name(
    patched_strategy_run_env,
):
    payload = api_module._execute_strategy_run(
        {
            "name": "Auto Leaderboard · 重掃 xgboost Hybrid #01",
            "source_strategy_name": "Auto Leaderboard · 重掃 xgboost Hybrid #01",
            "type": "hybrid",
            "params": {"model_name": "xgboost", "entry": {"bias50_max": 0.0}},
        }
    )

    assert payload["error"] == "系統生成策略不能直接儲存；請先輸入新的策略名稱。"
    assert "name" not in patched_strategy_run_env



def test_execute_strategy_run_rejects_duplicate_custom_name_when_it_would_overwrite_another_strategy(
    monkeypatch: pytest.MonkeyPatch,
    patched_strategy_run_env,
):
    monkeypatch.setattr(
        strategy_lab,
        "load_strategy",
        lambda name: {"name": "My Existing Strategy"} if name == "My Existing Strategy" else None,
    )

    payload = api_module._execute_strategy_run(
        {
            "name": "My Existing Strategy",
            "source_strategy_name": "Auto Leaderboard · 重掃 xgboost Hybrid #01",
            "type": "hybrid",
            "params": {"model_name": "xgboost", "entry": {"bias50_max": 0.0}},
        }
    )

    assert payload["error"] == "策略名稱已存在；請使用唯一名稱。"
    assert "name" not in patched_strategy_run_env



def test_execute_strategy_run_allows_internal_overwrite_for_auto_leaderboard_refresh(
    patched_strategy_run_env,
):
    payload = api_module._execute_strategy_run(
        {
            "name": "Auto Leaderboard · 重掃 logistic_regression Hybrid #01",
            "type": "hybrid",
            "allow_internal_overwrite": True,
            "params": {"model_name": "logistic_regression", "entry": {"bias50_max": 0.0}},
        }
    )

    assert payload["strategy"] == "Auto Leaderboard · 重掃 logistic_regression Hybrid #01"
    assert payload["requested_strategy_name"] == "Auto Leaderboard · 重掃 logistic_regression Hybrid #01"
    assert patched_strategy_run_env["name"] == "Auto Leaderboard · 重掃 logistic_regression Hybrid #01"
    assert patched_strategy_run_env["strategy_def"]["params"]["model_name"] == "logistic_regression"


def test_strategy_lab_frontend_prefers_saved_backtest_range_after_initial_override():
    source = _read("pages/StrategyLab.tsx")
    start_override = source.index("availableRangeOverride?.start")
    start_backtest = source.index("backtestRange.start")
    start_requested = source.index("resultRange?.requested?.start")
    start_strategy_data = source.index("strategyDataRange?.start")
    assert start_override < start_backtest < start_requested < start_strategy_data

    end_override = source.index("availableRangeOverride?.end")
    end_backtest = source.index("backtestRange.end")
    end_requested = source.index("resultRange?.requested?.end")
    end_strategy_data = source.index("strategyDataRange?.end")
    assert end_override < end_backtest < end_requested < end_strategy_data


def test_strategy_lab_frontend_exposes_manual_model_selection_and_protects_system_generated_rows():
    source = _read("pages/StrategyLab.tsx")
    required_snippets = [
        "const MODEL_OPTIONS = [",
        "const selectedStrategyIsSystemGenerated",
        "const runNameError = useMemo(() => {",
        "setSelectedModelName",
        'model_name: strategyType === "hybrid" ? selectedModelName : "rule_based"',
        '${strategyType === "hybrid" ? "Hybrid" : "Rule"} · ${strategyType === "hybrid" ? selectedModelName : "rule_based"}',
        "策略類型",
        "手動選擇模型",
        "MODEL_OPTIONS.map",
        "系統生成排行榜",
        "系統生成策略不能直接儲存；請先輸入新的策略名稱。",
        'placeholder={selectedStrategyIsSystemGenerated ? "請輸入新的策略名稱" : undefined}',
        'setName(isSystemGeneratedStrategy(strategy) ? "" : strategy.name);',
        'if (runNameError) {',
        'setError(runNameError);',
        "目前只更新圖表 / 區間，尚未重新執行回測",
        "請按「執行回測」刷新 ROI / Trades / 最近交易",
    ]
    for snippet in required_snippets:
        assert snippet in source
