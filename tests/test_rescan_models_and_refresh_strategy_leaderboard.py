from scripts import rescan_models_and_refresh_strategy_leaderboard as scan_module


def test_build_backtest_request_uses_rule_based_for_rule_baseline():
    row = {
        "model_name": "rule_baseline",
        "variant": "baseline-best",
        "params": {"model_name": "rule_baseline", "entry": {"bias50_max": 0.0}},
    }

    request = scan_module._build_backtest_request(row, rank_within_model=1)

    assert request["name"] == "Auto Leaderboard · 重掃 rule_baseline #01"
    assert request["type"] == "rule_based"
    assert request["params"]["model_name"] == "rule_baseline"


def test_build_backtest_request_keeps_hybrid_for_ml_models():
    row = {
        "model_name": "xgboost",
        "variant": "xgb-best",
        "params": {"model_name": "xgboost", "entry": {"bias50_max": 3.0}},
    }

    request = scan_module._build_backtest_request(row, rank_within_model=1)

    assert request["name"] == "Auto Leaderboard · 重掃 xgboost Hybrid #01"
    assert request["type"] == "hybrid"
    assert request["allow_internal_overwrite"] is True
    assert request["params"]["model_name"] == "xgboost"
