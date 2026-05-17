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
                "status": "stalled_under_minimum",
                "reason": "current live exact support stayed at the same count across heartbeats",
                "current_rows": 32,
                "minimum_support_rows": 50,
                "gap_to_minimum": 18,
                "previous_rows": 32,
                "delta_vs_previous": 0,
                "support_rows_needed": 18,
                "stagnant_run_count": 3,
                "stalled_support_accumulation": True,
                "escalate_to_blocker": True,
                "regression_basis": "same_identity_same_semantic_signature",
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
    assert facts["support_progress"]["status"] == "stalled_under_minimum"
    assert facts["support_progress"]["reason"] == "current live exact support stayed at the same count across heartbeats"
    assert facts["support_progress"]["previous_rows"] == 32
    assert facts["support_progress"]["delta_vs_previous"] == 0
    assert facts["support_progress"]["support_rows_needed"] == 18
    assert facts["support_progress"]["stagnant_run_count"] == 3
    assert facts["support_progress"]["stalled_support_accumulation"] is True
    assert facts["support_progress"]["escalate_to_blocker"] is True
    assert facts["support_progress"]["regression_basis"] == "same_identity_same_semantic_signature"
    assert facts["q15"]["gap_to_minimum"] == 18


def test_compact_source_blockers_projects_counts_and_redacts_secret_names():
    compact = hb_facts.compact_source_blockers(
        {
            "blocked_count": 3,
            "blocked_features": [
                {
                    "key": "fin_netflow",
                    "quality_flag": "source_auth_blocked",
                    "history_class": "archive_required",
                    "coverage_pct": 0.0,
                    "archive_window_coverage_pct": 0.0,
                    "forward_archive_ready": True,
                    "forward_archive_status": "ready",
                    "raw_snapshot_latest_status": "auth_missing",
                    "raw_snapshot_latest_age_min": 0.1,
                    "raw_snapshot_latest_message": "SENSITIVE_SOURCE_API_KEY is missing for SensitiveSource v4 auth.",
                    "recommended_action": "Configure SENSITIVE_SOURCE_API_KEY before using this source.",
                },
                {
                    "key": "nest_pred",
                    "quality_flag": "source_tls_verify_failed",
                    "history_class": "snapshot_only",
                    "coverage_pct": 16.1,
                    "raw_snapshot_latest_status": "tls_verify_failed",
                },
                {
                    "key": "web_whale",
                    "quality_flag": "source_history_gap",
                    "history_class": "short_window_public_api",
                    "coverage_pct": 24.1,
                    "raw_snapshot_latest_status": "ok",
                },
            ],
        }
    )

    assert compact["blocked_count"] == 3
    assert compact["history_class_counts"] == {
        "archive_required": 1,
        "snapshot_only": 1,
        "short_window_public_api": 1,
    }
    assert compact["quality_flag_counts"]["source_auth_blocked"] == 1
    assert compact["top_blockers"][0]["key"] == "fin_netflow"
    first = compact["top_blockers"][0]
    assert first["latest_status"] == "auth_missing"
    assert "COINGLASS" not in first["message"]
    assert "API_KEY" not in first["message"]
    assert "[REDACTED]" in first["message"]
    assert "COINGLASS" not in first["operator_action"]
    assert "API_KEY" not in first["operator_action"]


def test_compact_venue_readiness_keeps_runtime_proof_blockers():
    compact = hb_facts.compact_venue_readiness(
        {
            "generated_at": "2026-05-17T09:03:01Z",
            "all_ok": False,
            "venues_checked": 2,
            "runtime_ready": False,
            "runtime_ready_count": 0,
            "readiness_scope": "venue_runtime_proof_required",
            "readiness_state": "blocked_until_runtime_lifecycle_proof",
            "runtime_ready_blockers": [
                "live exchange credential 尚未驗證",
                "order ack lifecycle 尚未驗證",
                "fill lifecycle 尚未驗證",
            ],
            "venues": [
                {
                    "venue": "okx",
                    "ok": True,
                    "enabled_in_config": True,
                    "credentials_configured": False,
                    "proof_state": "public_metadata_only",
                    "readiness_state": "blocked_until_runtime_lifecycle_proof",
                    "runtime_ready": False,
                    "blockers": ["live exchange credential 尚未驗證", "order ack lifecycle 尚未驗證"],
                    "operator_next_action": "先配置 okx 交易憑證。",
                    "verify_next": "重跑元資料檢查。",
                },
                {
                    "venue": "binance",
                    "ok": False,
                    "enabled_in_config": False,
                    "credentials_configured": False,
                    "proof_state": "metadata_contract_failed",
                    "readiness_state": "blocked_until_runtime_lifecycle_proof",
                    "runtime_ready": False,
                    "blockers": ["元資料契約尚未通過", "場館設定停用"],
                    "operator_next_action": "先修復 binance 元資料檢查。",
                    "verify_next": "重跑元資料檢查。",
                },
            ],
        }
    )

    assert compact["venues_checked"] == 2
    assert compact["runtime_ready"] is False
    assert compact["runtime_ready_count"] == 0
    assert "order ack lifecycle 尚未驗證" in compact["runtime_ready_blockers"]
    assert compact["venues"][0]["venue"] == "okx"
    assert compact["venues"][0]["proof_state"] == "public_metadata_only"
    assert compact["venues"][0]["runtime_ready"] is False
    assert compact["venues"][1]["enabled_in_config"] is False


def test_build_runtime_facts_includes_source_and_venue_guardrail_context():
    facts = hb_facts.build_runtime_facts(
        probe={},
        drill={},
        summary={
            "source_blockers": {
                "blocked_features": [
                    {
                        "key": "fin_netflow",
                        "quality_flag": "source_auth_blocked",
                        "history_class": "archive_required",
                        "raw_snapshot_latest_status": "auth_missing",
                    }
                ]
            }
        },
        summary_path="data/heartbeat_1306-productization_summary.json",
        issues={"issues": []},
        topk={},
        q15={},
        execution_metadata_smoke={
            "venues_checked": 2,
            "runtime_ready": False,
            "venues": [
                {
                    "venue": "okx",
                    "proof_state": "public_metadata_only",
                    "runtime_ready": False,
                    "blockers": ["live exchange credential 尚未驗證"],
                }
            ],
        },
    )

    assert facts["source_blockers"]["blocked_count"] == 1
    assert facts["source_blockers"]["top_blockers"][0]["latest_status"] == "auth_missing"
    assert facts["venue_readiness"]["venues_checked"] == 2
    assert facts["venue_readiness"]["venues"][0]["proof_state"] == "public_metadata_only"
