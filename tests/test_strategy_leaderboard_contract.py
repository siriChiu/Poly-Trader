import asyncio

from server.routes import api as api_module


def test_api_strategy_leaderboard_strips_heavy_payload_fields(monkeypatch):
    heavy_results = {
        "overall_score": 0.91,
        "roi": 0.12,
        "profit_factor": 1.8,
        "max_drawdown": 0.08,
        "equity_curve": [{"timestamp": "2026-01-01T00:00:00Z", "equity": 10000.0}],
        "trades": [{"timestamp": "2026-01-01T00:00:00Z", "pnl": 12.3}],
        "score_series": [{"timestamp": "2026-01-01T00:00:00Z", "score": 0.71}],
        "chart_context": {
            "symbol": "BTCUSDT",
            "interval": "4h",
            "start": "2024-01-01T00:00:00Z",
            "end": "2026-01-01T00:00:00Z",
            "limit": 1000,
        },
    }
    monkeypatch.setattr(
        "backtesting.strategy_lab.load_all_strategies",
        lambda include_internal=False: [
            {
                "name": "demo-strategy",
                "definition": {"type": "rule_based", "params": {"investment_horizon": "medium"}},
                "metadata": {"primary_sleeve_label": "趨勢承接"},
                "last_results": heavy_results,
            }
        ],
    )

    payload = asyncio.run(api_module.api_strategy_leaderboard())

    assert payload["count"] == 1
    entry = payload["strategies"][0]
    assert entry["last_results"]["overall_score"] == 0.91
    assert "equity_curve" not in entry["last_results"]
    assert "trades" not in entry["last_results"]
    assert "score_series" not in entry["last_results"]
    assert entry["last_results"]["chart_context"] == {
        "symbol": "BTCUSDT",
        "interval": "4h",
        "start": "2024-01-01T00:00:00Z",
        "end": "2026-01-01T00:00:00Z",
    }
