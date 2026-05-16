import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_extract_runtime_facts.py"
spec = importlib.util.spec_from_file_location("hb_extract_runtime_facts", MODULE_PATH)
hb_facts = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(hb_facts)


def test_compact_topk_never_projects_full_rows_list():
    topk = {
        "generated_at": "2026-05-15T23:02:13+00:00",
        "artifact_freshness_status": "fresh",
        "row_count": 24,
        "rows": [{"model": "xgboost"}] * 24,
        "deployable_rows": 0,
        "risk_qualified_rows": 6,
        "runtime_blocked_candidate_rows": 6,
        "nearest_deployable_candidate": {
            "model": "logistic_regression",
            "feature_profile": "current_full",
            "regime": "all",
            "top_k": "top_2pct",
            "deployment_candidate_tier": "runtime_blocked_oos_pass",
            "oos_gate_passed": True,
            "deployable_verdict": "not_deployable",
            "support_route_deployable": False,
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "allowed_layers": 0,
        },
    }

    compact = hb_facts.compact_topk({}, topk)

    assert compact["rows"] == 24
    assert isinstance(compact["rows"], int)
    assert compact["freshness"] == "fresh"
    assert compact["deployable_rows"] == 0
    assert compact["risk_qualified_rows"] == 6
    assert compact["runtime_blocked_candidates"] == 6
    assert compact["nearest_candidate"] == {
        "model": "logistic_regression",
        "feature_profile": "current_full",
        "regime": "all",
        "top_k": "top_2pct",
        "deployment_candidate_tier": "runtime_blocked_oos_pass",
        "oos_gate_passed": True,
        "deployable_verdict": "not_deployable",
        "support_route_deployable": False,
        "deployment_blocker": "under_minimum_exact_live_structure_bucket",
        "allowed_layers": 0,
    }


def test_compact_circuit_breaker_projects_release_math_without_rows():
    audit = {
        "heartbeat": "1263",
        "target_col": "simulated_pyramid_win",
        "trigger_thresholds": {"horizon_minutes": 1440},
        "mixed_scope": {
            "triggered": True,
            "triggered_by": ["recent_win_rate"],
            "release_ready": False,
            "release_condition": {
                "current_streak": 13,
                "streak_must_be_below": 50,
                "recent_window": 50,
                "current_recent_window_win_rate": 0.18,
                "current_recent_window_wins": 9,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 6,
            },
            "recent_window": {"rows": [{"target": 0}] * 50, "losses": 41},
        },
        "aligned_scope": {
            "triggered": False,
            "release_ready": True,
            "release_condition": {
                "current_streak": 32,
                "streak_must_be_below": 50,
                "recent_window": 50,
                "current_recent_window_win_rate": 0.36,
                "current_recent_window_wins": 18,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 0,
            },
            "streak": {"rows": [{"target": 0}] * 32},
        },
        "root_cause": {
            "verdict": "mixed_horizon_false_positive",
            "summary": "混合 horizon false positive",
            "recommended_patch": "對齊 canonical 1440m。",
        },
    }

    compact = hb_facts.compact_circuit_breaker_audit({}, audit)

    assert compact["verdict"] == "mixed_horizon_false_positive"
    assert compact["canonical_horizon_minutes"] == 1440
    assert compact["mixed_scope"]["additional_recent_window_wins_needed"] == 6
    assert compact["aligned_scope"]["release_ready"] is True
    assert compact["aligned_scope"]["current_recent_window_wins"] == 18
    summary = compact["operator_guardrail_summary"]
    assert "混合週期訊號屬誤報" in summary
    assert "金字塔 24h 解除條件已達標" in summary
    assert "不可因此繞過目前即時精準支持阻塞" in summary
    assert "canonical" not in summary
    assert "false positive" not in summary
    assert "rows" not in compact["mixed_scope"]
    assert "rows" not in compact["aligned_scope"]


def test_compact_circuit_breaker_explains_canonical_active_release_gap():
    audit = {
        "heartbeat": "1275",
        "target_col": "simulated_pyramid_win",
        "trigger_thresholds": {"horizon_minutes": 1440},
        "aligned_scope": {
            "triggered": True,
            "triggered_by": ["recent_win_rate"],
            "release_ready": False,
            "release_condition": {
                "current_streak": 48,
                "streak_must_be_below": 50,
                "recent_window": 50,
                "current_recent_window_win_rate": 0.04,
                "current_recent_window_wins": 2,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 13,
            },
            "tail_pathology": {
                "wins_in_recent_window": 2,
                "losses_in_recent_window": 48,
                "loss_share": 0.96,
                "examples": [{"target": 0}] * 3,
            },
        },
        "root_cause": {"verdict": "canonical_breaker_active"},
    }

    compact = hb_facts.compact_circuit_breaker_audit({}, audit)

    assert compact["verdict"] == "canonical_breaker_active"
    assert compact["aligned_scope"]["current_recent_window_wins"] == 2
    assert compact["aligned_scope"]["additional_recent_window_wins_needed"] == 13
    summary = compact["operator_guardrail_summary"]
    assert "最近 50 筆目前 2/50 勝" in summary
    assert "解除至少需要 15 勝，還差 13 勝" in summary
    assert "買入 / 加倉維持關閉" in summary
    assert "減風險路徑保留" in summary
    assert "2/15" not in summary
    assert "canonical" not in summary
    assert "fail-closed" not in summary
    assert "examples" not in compact["aligned_scope"]


def test_build_runtime_facts_uses_summary_counts_and_reference_only_patch():
    facts = hb_facts.build_runtime_facts(
        probe={
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "current_live_structure_bucket": "BLOCK|structure_quality_block|q00",
            "current_live_structure_bucket_rows": 32,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 18,
            "support_route_verdict": "exact_bucket_present_but_below_minimum",
            "support_progress": {
                "status": "no_recent_comparable_history",
                "current_rows": 32,
                "minimum_support_rows": 50,
                "gap_to_minimum": 18,
            },
            "api_trade_guardrail_active": True,
            "api_trade_buy_guardrail": "current_live_deployment_blocker_409",
            "api_trade_allowed_risk_off_sides": ["reduce", "sell"],
        },
        drill={
            "recommended_patch_profile": "core_plus_macro_plus_all_4h",
            "recommended_patch_status": "reference_only_non_current_live_scope",
            "recommended_patch_reference_scope": "bull|CAUTION",
            "recommended_patch_reference_source": "bull_4h_pocket_ablation.bull_collapse_q35",
            "support_blocker_summary": {
                "operator_summary": "建議修補方案 core_plus_macro_plus_all_4h 目前為僅供治理參考，不是目前即時可部署修補。",
                "recommended_patch_profile": "core_plus_macro_plus_all_4h",
                "recommended_patch_status": "reference_only_non_current_live_scope",
                "recommended_patch_reference_only": True,
            },
        },
        summary={
            "heartbeat": "1262",
            "mode": "fast",
            "timestamp": "2026-05-15T23:02:27+00:00",
            "db_counts": {
                "raw_market_data": 33341,
                "features_normalized": 24492,
                "labels": 66578,
                "simulated_pyramid_win_rate": 0.5677,
            },
            "high_conviction_topk": {
                "rows": 24,
                "artifact_freshness_status": "fresh",
                "deployable_rows": 0,
                "risk_qualified_rows": 6,
                "runtime_blocked_candidate_rows": 6,
            },
        },
        summary_path="data/heartbeat_1262_summary.json",
        issues={"issues": [{"id": "P0_current_live_deployment_blocker"}]},
        topk={"rows": [{"model": "xgboost"}] * 99},
        q15={
            "current_live": {"current_live_structure_bucket": "BLOCK|structure_quality_block|q00", "current_live_structure_bucket_rows": 32},
            "support_route": {"verdict": "exact_bucket_present_but_below_minimum", "minimum_support_rows": 50, "current_live_structure_bucket_gap_to_minimum": 18},
        },
    )

    assert facts["summary_path"] == "data/heartbeat_1262_summary.json"
    assert facts["counts"] == {"raw": 33341, "features": 24492, "labels": 66578, "latest_raw_timestamp": None}
    assert facts["simulated_pyramid_win"] == 0.5677
    assert facts["topk"]["rows"] == 24
    assert facts["topk"]["runtime_blocked_candidates"] == 6
    assert facts["recommended_patch"]["recommended_patch_status"] == "reference_only_non_current_live_scope"
    assert facts["support_blocker_summary"]["recommended_patch_reference_only"] is True
    assert facts["api_trade_guardrail"]["api_trade_buy_guardrail"] == "current_live_deployment_blocker_409"
    assert facts["q15"]["gap_to_minimum"] == 18
