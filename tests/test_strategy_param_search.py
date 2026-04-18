from backtesting.strategy_param_search import expand_search_space, rank_param_search_results


def test_expand_search_space_updates_nested_paths_and_preserves_fixed_exit():
    base = {
        "model_name": "xgboost",
        "entry": {"confidence_min": 0.58, "bias50_max": 0.5},
        "turning_point": {"enabled": True, "top_score_take_profit": 0.80},
    }
    variants = expand_search_space(
        base,
        {
            "entry.confidence_min": [0.55, 0.60],
            "entry.bias50_max": [0.5, 0.0],
        },
    )

    assert len(variants) == 4
    assert {v["params"]["entry"]["confidence_min"] for v in variants} == {0.55, 0.60}
    assert {v["params"]["entry"]["bias50_max"] for v in variants} == {0.5, 0.0}
    assert all(v["params"]["turning_point"]["top_score_take_profit"] == 0.80 for v in variants)


def test_rank_param_search_results_prefers_roi_then_lower_drawdown_then_pf():
    ranked = rank_param_search_results(
        [
            {"variant": "a", "roi": 0.05, "max_drawdown": 0.10, "profit_factor": 1.10, "avg_exit_local_top_score": 0.4},
            {"variant": "b", "roi": 0.07, "max_drawdown": 0.20, "profit_factor": 1.00, "avg_exit_local_top_score": 0.3},
            {"variant": "c", "roi": 0.07, "max_drawdown": 0.12, "profit_factor": 1.20, "avg_exit_local_top_score": 0.5},
        ]
    )

    assert [row["variant"] for row in ranked] == ["c", "b", "a"]
