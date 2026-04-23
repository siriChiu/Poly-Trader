import asyncio
from pathlib import Path

from backtesting import strategy_lab
from scripts import rescan_models_and_refresh_strategy_leaderboard as rescan_module
from server.routes import api as api_module


class _DummyDb:
    def close(self):
        return None


def _auto_entry(name: str, *, model_name: str = "xgboost", overall_score: float = 0.6, entry_quality_min: float = 0.5):
    return {
        "name": name,
        "definition": {
            "type": "hybrid",
            "params": {
                "model_name": model_name,
                "entry": {
                    "bias50_max": 0.0,
                    "nose_max": 0.4,
                    "entry_quality_min": entry_quality_min,
                },
                "layers": [0.25, 0.25, 0.5],
            },
        },
        "last_results": {
            "overall_score": overall_score,
            "reliability_score": 0.6,
            "return_power_score": 0.6,
            "risk_control_score": 0.6,
            "capital_efficiency_score": 0.6,
            "roi": 0.1,
            "max_drawdown": 0.05,
            "total_trades": 20,
        },
        "is_internal": True,
        "metadata": {
            "model_name": model_name,
            "source": "auto_leaderboard",
            "source_label": "系統生成排行榜",
            "immutable": True,
            "editable_clone_required": True,
        },
    }


def test_save_best_rows_dedupes_duplicate_variants_before_persisting(monkeypatch):
    executed_requests = []

    def fake_execute_strategy_run(request):
        executed_requests.append(request)
        return {
            "strategy": request["name"],
            "results": {
                "roi": 0.1,
                "win_rate": 0.6,
                "total_trades": 20,
                "profit_factor": 1.4,
                "max_drawdown": 0.05,
            },
        }

    monkeypatch.setattr(rescan_module.api_module, "_execute_strategy_run", fake_execute_strategy_run)

    scan_results = [
        {
            "model_name": "xgboost",
            "top_10": [
                {
                    "model_name": "xgboost",
                    "variant": "dup-a",
                    "roi": 0.1,
                    "win_rate": 0.6,
                    "total_trades": 20,
                    "params": {
                        "model_name": "xgboost",
                        "entry": {"bias50_max": 0.0, "nose_max": 0.4, "entry_quality_min": 0.5},
                        "layers": [0.25, 0.25, 0.5],
                    },
                },
                {
                    "model_name": "xgboost",
                    "variant": "dup-b",
                    "roi": 0.1,
                    "win_rate": 0.6,
                    "total_trades": 20,
                    "params": {
                        "model_name": "xgboost",
                        "entry": {"bias50_max": 0.0, "nose_max": 0.4, "entry_quality_min": 0.55},
                        "layers": [0.25, 0.25, 0.5],
                    },
                },
            ],
        }
    ]

    saved = rescan_module._save_best_rows(scan_results, top_per_model=2)

    assert len(saved) == 1
    assert len(executed_requests) == 1
    assert saved[0]["name"] == "Auto Leaderboard · 重掃 xgboost Hybrid #01"



def test_api_strategy_leaderboard_dedupes_duplicate_auto_strategies_by_result_signature(monkeypatch):
    duplicate_rows = [
        _auto_entry("Auto Leaderboard · 重掃 xgboost Hybrid #01", overall_score=0.62, entry_quality_min=0.5),
        _auto_entry("Auto Leaderboard · 重掃 xgboost Hybrid #02", overall_score=0.61, entry_quality_min=0.55),
    ]

    monkeypatch.setattr(api_module, "_ensure_auto_generated_strategy_leaderboard", lambda force=False: None)
    monkeypatch.setattr(api_module, "get_db", lambda: _DummyDb())
    monkeypatch.setattr(strategy_lab, "load_all_strategies", lambda include_internal=True: duplicate_rows)
    monkeypatch.setattr(api_module, "_decorate_strategy_entry", lambda entry, db=None: entry)
    monkeypatch.setattr(api_module, "_compact_strategy_leaderboard_entry", lambda entry: entry)
    monkeypatch.setattr(api_module, "_load_recent_strategy_leaderboard_snapshots", lambda limit=12, db_path=None: [])
    monkeypatch.setattr(api_module, "_compute_strategy_rank_deltas_against_latest_snapshot", lambda entries, db_path=None: {})

    payload = asyncio.run(api_module.api_strategy_leaderboard())

    assert payload["count"] == 1
    assert len(payload["strategies"]) == 1
    assert payload["strategies"][0]["name"] == "Auto Leaderboard · 重掃 xgboost Hybrid #01"


def test_save_best_rows_dedupes_duplicate_results_across_models(monkeypatch):
    executed_requests = []

    def fake_execute_strategy_run(request):
        executed_requests.append(request)
        return {
            "strategy": request["name"],
            "results": {
                "roi": 0.1,
                "win_rate": 0.6,
                "total_trades": 20,
                "profit_factor": 1.4,
                "max_drawdown": 0.05,
            },
        }

    monkeypatch.setattr(rescan_module.api_module, "_execute_strategy_run", fake_execute_strategy_run)

    scan_results = [
        {
            "model_name": "catboost",
            "top_10": [
                {
                    "model_name": "catboost",
                    "variant": "same-outcome-a",
                    "roi": 0.1,
                    "win_rate": 0.6,
                    "total_trades": 20,
                    "profit_factor": 1.4,
                    "max_drawdown": 0.05,
                    "params": {
                        "model_name": "catboost",
                        "entry": {"bias50_max": 0.0, "nose_max": 0.4, "entry_quality_min": 0.5},
                        "layers": [0.25, 0.25, 0.5],
                    },
                }
            ],
        },
        {
            "model_name": "xgboost",
            "top_10": [
                {
                    "model_name": "xgboost",
                    "variant": "same-outcome-b",
                    "roi": 0.1,
                    "win_rate": 0.6,
                    "total_trades": 20,
                    "profit_factor": 1.4,
                    "max_drawdown": 0.05,
                    "params": {
                        "model_name": "xgboost",
                        "entry": {"bias50_max": 0.0, "nose_max": 0.4, "entry_quality_min": 0.5},
                        "layers": [0.25, 0.25, 0.5],
                    },
                }
            ],
        },
    ]

    saved = rescan_module._save_best_rows(scan_results, top_per_model=1)

    assert len(saved) == 1
    assert len(executed_requests) == 1
    assert saved[0]["name"] == "Auto Leaderboard · 重掃 catboost Hybrid #01"


def test_api_strategy_leaderboard_dedupes_cross_model_duplicate_auto_strategies(monkeypatch):
    duplicate_rows = [
        _auto_entry("Auto Leaderboard · 重掃 catboost Hybrid #01", model_name="catboost", overall_score=0.62, entry_quality_min=0.5),
        _auto_entry("Auto Leaderboard · 重掃 xgboost Hybrid #01", model_name="xgboost", overall_score=0.62, entry_quality_min=0.5),
    ]

    monkeypatch.setattr(api_module, "_ensure_auto_generated_strategy_leaderboard", lambda force=False: None)
    monkeypatch.setattr(api_module, "get_db", lambda: _DummyDb())
    monkeypatch.setattr(strategy_lab, "load_all_strategies", lambda include_internal=True: duplicate_rows)
    monkeypatch.setattr(api_module, "_decorate_strategy_entry", lambda entry, db=None: entry)
    monkeypatch.setattr(api_module, "_compact_strategy_leaderboard_entry", lambda entry: entry)
    monkeypatch.setattr(api_module, "_load_recent_strategy_leaderboard_snapshots", lambda limit=12, db_path=None: [])
    monkeypatch.setattr(api_module, "_compute_strategy_rank_deltas_against_latest_snapshot", lambda entries, db_path=None: {})

    payload = asyncio.run(api_module.api_strategy_leaderboard())

    assert payload["count"] == 1
    assert len(payload["strategies"]) == 1
    assert payload["strategies"][0]["name"] == "Auto Leaderboard · 重掃 catboost Hybrid #01"


def test_strategy_lab_prefers_same_origin_strategy_fetches_for_dev_runtime():
    source = (Path(__file__).resolve().parents[1] / "web/src/pages/StrategyLab.tsx").read_text(encoding="utf-8")
    required_snippets = [
        "const STRATEGY_LAB_SAME_ORIGIN_TIMEOUT_MS = 2500;",
        "const fetchStrategyLabEndpointJson = async (endpoint: string) => {",
        "const sameOriginController = new AbortController();",
        "const sameOriginTimeoutId = window.setTimeout(() => sameOriginController.abort(), STRATEGY_LAB_SAME_ORIGIN_TIMEOUT_MS);",
        "const sameOriginResponse = await window.fetch(endpoint, {",
        'signal: sameOriginController.signal,',
        "window.clearTimeout(sameOriginTimeoutId);",
        "Fall back to fetchApi below when same-origin proxy is unavailable or hangs.",
        "const res = await fetchStrategyLabEndpointJson(endpoint) as any;",
        "const data = await fetchStrategyLabEndpointJson(\"/api/strategy_data_range\")",
        "const detail = await fetchStrategyLabEndpointJson(`/api/strategies/${encodeURIComponent(strategyName)}`) as StrategyEntry;",
    ]
    for snippet in required_snippets:
        assert snippet in source
