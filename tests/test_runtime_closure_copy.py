from model.runtime_closure import build_runtime_closure_summary


RAW_RUNTIME_COPY_SNIPPETS = [
    "circuit breaker active",
    "Recent 50-sample win rate",
    "release condition",
    "recent 50 win rate",
    "exact-vs-spillover",
    "quality",
    "scope",
    "spillover",
    "rows",
    "WR",
    "exact live lane",
    "current live bucket",
    "exact support closure",
    "top-level live baseline",
    "trade floor",
    "no-deploy governance",
    "support closure",
    "deployment closure",
    "reference_only",
    "non_current_live_scope",
    "deployment-grade",
    "minimum support",
    "exact rows",
    "support_route=",
    "score=",
    "舊 範圍",
    "舊範圍 的",
    "寬 範圍",
    "寬範圍 出現",
    "guardrail",
]


def test_runtime_closure_summary_humanizes_exact_support_trade_floor_blocker():
    summary = build_runtime_closure_summary(
        {
            "deployment_blocker": "decision_quality_below_trade_floor",
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q00",
            "current_live_structure_bucket_rows": 188,
            "minimum_support_rows": 50,
            "support_route_verdict": "exact_bucket_supported",
            "entry_quality": 0.2465,
            "entry_quality_label": "D",
            "entry_quality_components": {"trade_floor": 0.55},
            "decision_quality_label": "D",
            "allowed_layers": 0,
        }
    )

    assert summary is not None
    assert "當前即時分桶" in summary
    assert "精準樣本閉環" in summary
    assert "進場品質" in summary
    assert "交易門檻" in summary
    assert "不可部署治理" in summary
    assert "支持樣本閉環" in summary
    assert "部署閉環" in summary
    for leaked_copy in RAW_RUNTIME_COPY_SNIPPETS:
        assert leaked_copy not in summary


def test_runtime_closure_summary_humanizes_circuit_breaker_release_math_and_scope():
    summary = build_runtime_closure_summary(
        {
            "signal": "CIRCUIT_BREAKER",
            "reason": "Recent 50-sample win rate: 28.00% < 30%",
            "deployment_blocker": "circuit_breaker_active",
            "deployment_blocker_reason": "Recent 50-sample win rate: 28.00% < 30%",
        },
        release_window=50,
        release_floor=0.30,
        release_gap=1,
        current_wins=14,
        breaker_release={"streak_must_be_below": 50},
        scope_pathology_summary={
            "summary": "同 quality 寬 scope 出現 bull|BLOCK spillover，443 rows / WR 20.2% / 品質 -0.058，明顯劣於 exact live lane WR 58.9% / 品質 0.221。"
        },
    )

    assert summary is not None
    assert "風控熔斷啟用中" in summary
    assert "最近 50 筆勝率" in summary
    assert "解除條件" in summary
    assert "至少還差 1 勝" in summary
    assert "精準路徑與外溢對照" in summary
    assert "同品質寬範圍" in summary
    assert "牛市|阻塞" in summary
    assert "443 筆" in summary
    assert "勝率 20.2%" in summary
    assert "精準即時路徑" in summary
    for leaked_copy in RAW_RUNTIME_COPY_SNIPPETS:
        assert leaked_copy not in summary


def test_runtime_closure_summary_humanizes_reference_only_recommended_patch_scope():
    summary = build_runtime_closure_summary(
        {
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "deployment_blocker_reason": "current live structure bucket below minimum support",
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q35",
            "current_live_structure_bucket_rows": 28,
            "minimum_support_rows": 50,
            "support_route_verdict": "exact_bucket_present_but_below_minimum",
            "support_governance_route": "exact_live_bucket_present_but_below_minimum",
            "allowed_layers": 0,
        },
        scope_pathology_summary={
            "summary": "同 quality 寬 scope 出現 bull|CAUTION spillover，414 rows / WR 20.2% / 品質 -0.058，明顯劣於 exact live lane WR 57.7% / 品質 0.209。",
            "recommended_patch": {
                "recommended_profile": "core_plus_macro_plus_all_4h",
                "status": "reference_only_non_current_live_scope",
            },
        },
    )

    assert summary is not None
    assert "精準樣本未達最小門檻" in summary
    assert "非目前即時範圍，僅供治理參考" in summary
    assert "同品質寬範圍" in summary
    assert "精準即時路徑" in summary
    for leaked_copy in [*RAW_RUNTIME_COPY_SNIPPETS, "reference_only", "non_current_live_scope", "exact_live_bucket_present"]:
        assert leaked_copy not in summary
