import asyncio
import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_model_leaderboard_api_probe.py"
spec = importlib.util.spec_from_file_location("hb_model_leaderboard_api_probe_test_module", MODULE_PATH)
hb_model_leaderboard_api_probe = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(hb_model_leaderboard_api_probe)


def test_default_wait_budget_leaves_heartbeat_subprocess_headroom():
    common_heartbeat_timeout_sec = 180.0
    required_headroom_sec = 30.0

    assert hb_model_leaderboard_api_probe.DEFAULT_MAX_WAIT_SEC <= (
        common_heartbeat_timeout_sec - required_headroom_sec
    )


class _FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    async def sleep(self, seconds: float):
        self.now += seconds


def test_run_probe_waits_for_in_process_refresh_completion(monkeypatch):
    responses = [
        {
            "cached": True,
            "refreshing": True,
            "stale": True,
            "updated_at": "2026-04-18T06:41:51Z",
            "cache_age_sec": 1000,
            "count": 6,
            "target_col": "simulated_pyramid_win",
            "warning": "模型排行榜快取已過期；背景正在重算最新結果。",
            "refresh_reason": "cache_stale",
        },
        {
            "cached": True,
            "refreshing": True,
            "stale": True,
            "updated_at": "2026-04-18T06:41:51Z",
            "cache_age_sec": 1005,
            "count": 6,
            "target_col": "simulated_pyramid_win",
            "warning": "模型排行榜快取已過期；背景正在重算最新結果。",
            "refresh_reason": "cache_stale",
        },
        {
            "cached": True,
            "refreshing": False,
            "stale": False,
            "updated_at": "2026-04-18T06:59:42Z",
            "cache_age_sec": 4,
            "count": 6,
            "target_col": "simulated_pyramid_win",
            "warning": None,
            "refresh_reason": "cache_stale",
        },
    ]
    call_count = {"value": 0}

    async def fake_api_model_leaderboard():
        idx = min(call_count["value"], len(responses) - 1)
        call_count["value"] += 1
        return responses[idx]

    clock = _FakeClock()
    monkeypatch.setattr(hb_model_leaderboard_api_probe.api_module, "api_model_leaderboard", fake_api_model_leaderboard)
    monkeypatch.setattr(hb_model_leaderboard_api_probe.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(hb_model_leaderboard_api_probe.asyncio, "sleep", clock.sleep)

    result = asyncio.run(
        hb_model_leaderboard_api_probe.run_probe(max_wait_sec=20.0, poll_interval_sec=5.0)
    )

    assert result["waited_for_refresh"] is True
    assert result["refresh_completed"] is True
    assert result["timed_out_waiting_for_refresh"] is False
    assert result["refresh_state_changed"] is True
    assert result["poll_attempts"] == 2
    assert result["wait_elapsed_sec"] == 10.0
    assert result["max_wait_sec"] == 20.0
    assert result["poll_interval_sec"] == 5.0
    assert result["suppressed_stdout"] == {"suppressed": False, "line_count": 0, "preview": []}
    assert result["suppressed_stderr"] == {"suppressed": False, "line_count": 0, "preview": []}
    assert result["stale"] is False
    assert result["refreshing"] is False
    assert result["initial_state"]["stale"] is True
    assert call_count["value"] == 3


def test_run_probe_reports_timeout_when_refresh_never_lands(monkeypatch):
    payload = {
        "cached": True,
        "refreshing": True,
        "stale": True,
        "updated_at": "2026-04-18T06:41:51Z",
        "cache_age_sec": 1000,
        "count": 6,
        "target_col": "simulated_pyramid_win",
        "warning": "模型排行榜快取已過期；背景正在重算最新結果。",
        "refresh_reason": "cache_stale",
    }
    call_count = {"value": 0}

    async def fake_api_model_leaderboard():
        call_count["value"] += 1
        return dict(payload)

    clock = _FakeClock()
    monkeypatch.setattr(hb_model_leaderboard_api_probe.api_module, "api_model_leaderboard", fake_api_model_leaderboard)
    monkeypatch.setattr(hb_model_leaderboard_api_probe.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(hb_model_leaderboard_api_probe.asyncio, "sleep", clock.sleep)

    result = asyncio.run(
        hb_model_leaderboard_api_probe.run_probe(max_wait_sec=10.0, poll_interval_sec=5.0)
    )

    assert result["waited_for_refresh"] is True
    assert result["refresh_completed"] is False
    assert result["timed_out_waiting_for_refresh"] is True
    assert result["refresh_state_changed"] is False
    assert result["poll_attempts"] == 2
    assert result["wait_elapsed_sec"] == 10.0
    assert result["max_wait_sec"] == 10.0
    assert result["poll_interval_sec"] == 5.0
    assert result["suppressed_stdout"] == {"suppressed": False, "line_count": 0, "preview": []}
    assert result["suppressed_stderr"] == {"suppressed": False, "line_count": 0, "preview": []}
    assert result["stale"] is True
    assert result["refreshing"] is True
    assert result["initial_state"]["stale"] is True
    assert call_count["value"] == 3


def test_run_probe_suppresses_background_refresh_logs(monkeypatch):
    responses = [
        {
            "cached": True,
            "refreshing": True,
            "stale": True,
            "updated_at": "2026-04-18T06:41:51Z",
            "cache_age_sec": 1000,
            "count": 6,
            "target_col": "simulated_pyramid_win",
            "warning": "模型排行榜快取已過期；背景正在重算最新結果。",
            "refresh_reason": "cache_stale",
        },
        {
            "cached": True,
            "refreshing": False,
            "stale": False,
            "updated_at": "2026-04-18T06:59:42Z",
            "cache_age_sec": 4,
            "count": 6,
            "target_col": "simulated_pyramid_win",
            "warning": None,
            "refresh_reason": "cache_stale",
        },
    ]
    call_count = {"value": 0}

    async def fake_api_model_leaderboard():
        print(f"refresh-log-{call_count['value']}")
        idx = min(call_count["value"], len(responses) - 1)
        call_count["value"] += 1
        return responses[idx]

    clock = _FakeClock()
    monkeypatch.setattr(hb_model_leaderboard_api_probe.api_module, "api_model_leaderboard", fake_api_model_leaderboard)
    monkeypatch.setattr(hb_model_leaderboard_api_probe.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(hb_model_leaderboard_api_probe.asyncio, "sleep", clock.sleep)

    result = asyncio.run(
        hb_model_leaderboard_api_probe.run_probe(max_wait_sec=10.0, poll_interval_sec=5.0)
    )

    assert result["suppressed_stdout"]["suppressed"] is True
    assert result["suppressed_stdout"]["line_count"] == 2
    assert result["suppressed_stdout"]["preview"] == ["refresh-log-0", "refresh-log-1"]
    assert result["suppressed_stderr"] == {"suppressed": False, "line_count": 0, "preview": []}
    assert result["refresh_completed"] is True
    assert call_count["value"] == 2


def test_run_probe_preserves_leaderboard_governance_summary(monkeypatch):
    payload = {
        "cached": True,
        "refreshing": False,
        "stale": False,
        "updated_at": "2026-04-18T17:28:03Z",
        "cache_age_sec": 3,
        "count": 5,
        "comparable_count": 5,
        "placeholder_count": 1,
        "target_col": "simulated_pyramid_win",
        "leaderboard_governance": {
            "generated_at": "2026-04-18T17:32:42Z",
            "dual_profile_state": "post_threshold_profile_governance_stalled",
            "train_selected_profile": "core_plus_macro_plus_4h_structure_shift",
            "train_selected_profile_source": "bull_4h_pocket_ablation.exact_supported_profile",
            "leaderboard_selected_profile": "core_only",
            "leaderboard_selected_profile_source": "feature_group_ablation.recommended_profile",
            "live_current_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "live_current_structure_bucket_rows": 55,
            "minimum_support_rows": 50,
            "profile_split": {
                "global_profile": "core_only",
                "production_profile": "core_plus_macro_plus_4h_structure_shift",
            },
            "governance_contract": {
                "verdict": "post_threshold_governance_contract_needs_leaderboard_sync",
                "current_closure": "exact_supported_but_leaderboard_not_synced",
            },
            "ignored_large_field": {"should": "not be copied"},
        },
    }

    async def fake_api_model_leaderboard():
        return dict(payload)

    clock = _FakeClock()
    monkeypatch.setattr(hb_model_leaderboard_api_probe.api_module, "api_model_leaderboard", fake_api_model_leaderboard)
    monkeypatch.setattr(hb_model_leaderboard_api_probe.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(hb_model_leaderboard_api_probe.asyncio, "sleep", clock.sleep)

    result = asyncio.run(
        hb_model_leaderboard_api_probe.run_probe(max_wait_sec=5.0, poll_interval_sec=1.0)
    )

    governance = result["leaderboard_governance"]
    assert governance["dual_profile_state"] == "post_threshold_profile_governance_stalled"
    assert governance["train_selected_profile"] == "core_plus_macro_plus_4h_structure_shift"
    assert governance["profile_split"] == {
        "global_profile": "core_only",
        "production_profile": "core_plus_macro_plus_4h_structure_shift",
    }
    assert governance["governance_contract"] == {
        "verdict": "post_threshold_governance_contract_needs_leaderboard_sync",
        "current_closure": "exact_supported_but_leaderboard_not_synced",
    }
    assert "ignored_large_field" not in governance


def test_run_probe_compacts_support_history_and_high_conviction_topk(monkeypatch):
    support_progress = {
        "status": "semantic_rebaseline_under_minimum",
        "reason": "current q15 exact support is 20/50",
        "regression_basis": "legacy_or_different_semantic_signature",
        "support_identity": {
            "target_col": "simulated_pyramid_win",
            "horizon_minutes": 1440,
            "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
            "regime_label": "bear",
            "regime_gate": "CAUTION",
            "entry_quality_label": "C",
            "calibration_window": 1000,
            "bucket_semantic_signature": "live_structure_bucket:q15_support_identity:v2",
            "large_extra": "drop-me",
        },
        "current_rows": 20,
        "minimum_support_rows": 50,
        "gap_to_minimum": 30,
        "legacy_supported_reference": {
            "heartbeat": "20260419b",
            "live_current_structure_bucket_rows": 53,
            "minimum_support_rows": 50,
            "semantic_identity_evidence": {
                "verdict": "reference_only_semantic_mismatch_or_missing_fields",
                "mismatched_fields": ["regime_label"],
                "supports_current_identity": False,
                "large_extra": "drop-me",
            },
            "large_extra": "drop-me",
        },
        "history": [{"heartbeat": str(idx), "large": "drop-me"} for idx in range(100)],
    }
    topk_row = {
        "model": "logistic_regression",
        "feature_profile": "current_full",
        "regime": "all",
        "top_k": "top_2pct",
        "oos_roi": 0.9324,
        "win_rate": 0.8621,
        "profit_factor": 19.8864,
        "max_drawdown": 0.022,
        "worst_fold": 0.2068,
        "trade_count": 58,
        "deployable_verdict": "not_deployable",
        "deployment_candidate_tier": "runtime_blocked_oos_pass",
        "gate_failures": ["support_route_not_deployable"],
        "model_gate_failures": [],
        "live_gate_failures": ["support_route_not_deployable"],
        "oos_gate_passed": True,
        "blocked_only_by_live_guardrails": True,
        "support_route": "exact_bucket_present_but_below_minimum",
        "support_governance_route": "exact_live_bucket_present_but_below_minimum",
        "deployment_blocker": "under_minimum_exact_live_structure_bucket",
        "runtime_closure_state": "patch_inactive_or_blocked",
        "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
        "current_live_structure_bucket_rows": 20,
        "minimum_support_rows": 50,
        "current_live_structure_bucket_gap_to_minimum": 30,
        "allowed_layers": 0,
        "signal": "HOLD",
        "large_extra": "drop-me",
    }
    payload = {
        "cached": True,
        "refreshing": False,
        "stale": False,
        "updated_at": "2026-05-14T14:02:55Z",
        "cache_age_sec": 2,
        "count": 6,
        "target_col": "simulated_pyramid_win",
        "leaderboard_governance": {
            "generated_at": "2026-05-14T14:02:56Z",
            "dual_profile_state": "leaderboard_global_winner_vs_train_support_fallback",
            "governance_contract": {
                "verdict": "single_role_governance_ok",
                "support_progress": support_progress,
                "large_extra": "drop-me",
            },
        },
        "high_conviction_topk": {
            "source_artifact": "data/high_conviction_topk_oos_matrix.json",
            "generated_at": "2026-05-14T13:24:12Z",
            "freshness_status": "fresh",
            "artifact_age_minutes": 38.9,
            "stale_after_minutes": 60.0,
            "deployment_ready": False,
            "deployment_readiness_status": "paper_shadow_only",
            "samples": 24286,
            "row_count": 24,
            "deployable_count": 0,
            "risk_qualified_count": 6,
            "runtime_blocked_candidate_count": 6,
            "support_context": {
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                "current_live_structure_bucket_rows": 20,
                "minimum_support_rows": 50,
                "current_live_structure_bucket_gap_to_minimum": 30,
                "support_route_verdict": "exact_bucket_present_but_below_minimum",
                "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                "deployment_blocker": "under_minimum_exact_live_structure_bucket",
                "runtime_closure_state": "patch_inactive_or_blocked",
                "allowed_layers": 0,
                "signal": "HOLD",
                "support_progress": support_progress,
                "large_extra": "drop-me",
            },
            "nearest_deployable_rows": [topk_row],
            "best_rows": [topk_row, {**topk_row, "model": "xgboost"}],
            "large_extra": "drop-me",
        },
    }

    async def fake_api_model_leaderboard():
        return dict(payload)

    clock = _FakeClock()
    monkeypatch.setattr(hb_model_leaderboard_api_probe.api_module, "api_model_leaderboard", fake_api_model_leaderboard)
    monkeypatch.setattr(hb_model_leaderboard_api_probe.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(hb_model_leaderboard_api_probe.asyncio, "sleep", clock.sleep)

    result = asyncio.run(
        hb_model_leaderboard_api_probe.run_probe(max_wait_sec=5.0, poll_interval_sec=1.0)
    )

    governance_progress = result["leaderboard_governance"]["governance_contract"]["support_progress"]
    assert governance_progress["current_rows"] == 20
    assert governance_progress["minimum_support_rows"] == 50
    assert governance_progress["gap_to_minimum"] == 30
    assert "history" not in governance_progress
    assert "large_extra" not in governance_progress["support_identity"]
    assert governance_progress["legacy_supported_reference"]["semantic_identity_evidence"] == {
        "mismatched_fields": ["regime_label"],
        "supports_current_identity": False,
        "verdict": "reference_only_semantic_mismatch_or_missing_fields",
    }

    topk = result["high_conviction_topk"]
    assert topk["deployable_count"] == 0
    assert topk["risk_qualified_count"] == 6
    assert topk["runtime_blocked_candidate_count"] == 6
    assert topk["support_context"]["current_live_structure_bucket_rows"] == 20
    assert "history" not in topk["support_context"]["support_progress"]
    assert topk["nearest_deployable_candidate"] == {
        "model": "logistic_regression",
        "feature_profile": "current_full",
        "regime": "all",
        "top_k": "top_2pct",
        "oos_roi": 0.9324,
        "win_rate": 0.8621,
        "profit_factor": 19.8864,
        "max_drawdown": 0.022,
        "worst_fold": 0.2068,
        "trade_count": 58,
        "deployable_verdict": "not_deployable",
        "deployment_candidate_tier": "runtime_blocked_oos_pass",
        "gate_failures": ["support_route_not_deployable"],
        "model_gate_failures": [],
        "live_gate_failures": ["support_route_not_deployable"],
        "oos_gate_passed": True,
        "blocked_only_by_live_guardrails": True,
        "support_route": "exact_bucket_present_but_below_minimum",
        "support_governance_route": "exact_live_bucket_present_but_below_minimum",
        "deployment_blocker": "under_minimum_exact_live_structure_bucket",
        "runtime_closure_state": "patch_inactive_or_blocked",
        "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
        "current_live_structure_bucket_rows": 20,
        "minimum_support_rows": 50,
        "current_live_structure_bucket_gap_to_minimum": 30,
        "allowed_layers": 0,
        "signal": "HOLD",
    }
    assert len(topk["best_rows"]) == 1
