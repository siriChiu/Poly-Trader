from pathlib import Path

import asyncio
import pandas as pd
import pytest

from backtesting import strategy_lab
from server.routes import api as api_module


class _DummyDb:
    def close(self):
        return None


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


def test_manual_test_named_strategy_is_visible_and_not_internal(isolated_strategies_dir: Path):
    strategy_lab.save_strategy(
        "Test",
        {
            "type": "hybrid",
            "params": {
                "model_name": "xgboost",
                "entry": {"bias50_max": 0.0},
            },
        },
        {"roi": 0.08, "win_rate": 0.55},
    )

    loaded = strategy_lab.load_strategy("Test")
    visible = strategy_lab.load_all_strategies(include_internal=False)

    assert loaded is not None
    assert loaded["is_internal"] is False
    assert loaded["metadata"]["source"] == "user_saved"
    assert [entry["name"] for entry in visible] == ["Test"]


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


def test_api_strategy_leaderboard_keeps_manual_rows_visible_alongside_auto_rows(monkeypatch: pytest.MonkeyPatch):
    manual_row = {
        "name": "Test",
        "is_internal": False,
        "definition": {
            "type": "hybrid",
            "params": {"model_name": "xgboost", "entry": {"bias50_max": 0.0}},
        },
        "metadata": {
            "source": "user_saved",
            "source_label": "手動策略",
            "immutable": False,
            "editable_clone_required": False,
        },
        "last_results": {
            "overall_score": 0.91,
            "reliability_score": 0.75,
            "return_power_score": 0.74,
            "risk_control_score": 0.70,
            "capital_efficiency_score": 0.68,
            "roi": 0.11,
            "max_drawdown": 0.04,
            "total_trades": 12,
        },
    }
    auto_row = {
        "name": "Auto Leaderboard · 重掃 xgboost Hybrid #01",
        "is_internal": True,
        "definition": {
            "type": "hybrid",
            "params": {"model_name": "xgboost", "entry": {"bias50_max": 0.0}},
        },
        "metadata": {
            "source": "auto_leaderboard",
            "source_label": "系統生成排行榜",
            "immutable": True,
            "editable_clone_required": True,
        },
        "last_results": {
            "overall_score": 0.88,
            "reliability_score": 0.72,
            "return_power_score": 0.71,
            "risk_control_score": 0.69,
            "capital_efficiency_score": 0.64,
            "roi": 0.13,
            "max_drawdown": 0.05,
            "total_trades": 20,
        },
    }

    monkeypatch.setattr(api_module, "_ensure_auto_generated_strategy_leaderboard", lambda force=False: None)
    monkeypatch.setattr(api_module, "get_db", lambda: _DummyDb())
    monkeypatch.setattr(strategy_lab, "load_all_strategies", lambda include_internal=True: [auto_row, manual_row])
    monkeypatch.setattr(api_module, "_decorate_strategy_entry", lambda entry, db=None: entry)
    monkeypatch.setattr(api_module, "_compact_strategy_leaderboard_entry", lambda entry: entry)
    monkeypatch.setattr(api_module, "_load_recent_strategy_leaderboard_snapshots", lambda limit=12, db_path=None: [])
    monkeypatch.setattr(api_module, "_compute_strategy_rank_deltas_against_latest_snapshot", lambda entries, db_path=None: {})

    payload = asyncio.run(api_module.api_strategy_leaderboard())

    assert payload["count"] == 2
    assert [entry["name"] for entry in payload["strategies"]] == ["Test", "Auto Leaderboard · 重掃 xgboost Hybrid #01"]


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
        '${strategyType === "hybrid" ? "混合策略" : "規則策略"} · ${strategyType === "hybrid" ? selectedModelName : "rule_based"}',
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
        "請按「執行回測」刷新 ROI / 交易數 / 最近交易",
    ]
    for snippet in required_snippets:
        assert snippet in source



def test_strategy_lab_frontend_prefills_workspace_with_unique_default_name_after_leaderboard_load():
    source = _read("pages/StrategyLab.tsx")
    required_snippets = [
        'const buildUniqueStrategyName = (existingNames: Set<string>, baseName = "My Strategy") => {',
        'const workspaceDefaultName = useMemo(() => buildUniqueStrategyName(existingStrategyNameSet, "My Strategy"), [existingStrategyNameSet]);',
        'if (selectedStrategy || name !== "My Strategy" || !existingStrategyNameSet.has(name)) return;',
        'setName(workspaceDefaultName);',
    ]
    for snippet in required_snippets:
        assert snippet in source



def test_strategy_lab_frontend_rehydrates_cached_selected_strategy_into_form_state_before_defaulting():
    source = _read("pages/StrategyLab.tsx")
    required_snippets = [
        'const restoredSelectedStrategyNameRef = useRef<string | null>(null);',
        'restoredSelectedStrategyNameRef.current = cached.selectedStrategy.name;',
        'applyStrategyToForm(cached.selectedStrategy);',
        'const restoredStrategyName = restoredSelectedStrategyNameRef.current;',
        'if (restoredStrategyName) {',
        'await selectStrategyByName(restoredStrategyName, dataRange);',
    ]
    for snippet in required_snippets:
        assert snippet in source



def test_strategy_lab_frontend_keeps_headline_metrics_above_workspace_chart():
    source = _read("pages/StrategyLab.tsx")
    metrics_def = source.index("const workspaceHeadlineMetrics = (")
    workspace_render = source.index("{workspaceHeadlineMetrics}")
    chart_render = source.index("<CandlestickChart")
    assert metrics_def < workspace_render < chart_render



def test_strategy_confidence_lookup_key_normalizes_microseconds():
    assert api_module._strategy_confidence_lookup_key("2024-04-21 13:00:00.000000") == "2024-04-21 13:00:00"
    assert api_module._strategy_confidence_lookup_key("2024-04-21T13:00:00Z") == "2024-04-21 13:00:00"
