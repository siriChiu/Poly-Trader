import asyncio
import json
import time

from server.routes import api as api_module


def _seed_cache(
    monkeypatch,
    *,
    payload,
    updated_at,
    refreshing=False,
    error=None,
    last_refresh_attempt_at=None,
    last_refresh_reason=None,
):
    monkeypatch.setitem(api_module._MODEL_LB_CACHE, "payload", payload)
    monkeypatch.setitem(api_module._MODEL_LB_CACHE, "updated_at", updated_at)
    monkeypatch.setitem(api_module._MODEL_LB_CACHE, "refreshing", refreshing)
    monkeypatch.setitem(api_module._MODEL_LB_CACHE, "error", error)
    monkeypatch.setitem(api_module._MODEL_LB_CACHE, "last_refresh_attempt_at", last_refresh_attempt_at)
    monkeypatch.setitem(api_module._MODEL_LB_CACHE, "last_refresh_reason", last_refresh_reason)



def test_api_model_leaderboard_returns_cached_payload_without_blocking(monkeypatch):
    monkeypatch.setattr(api_module, "_load_model_leaderboard_cache_file", lambda: None)
    monkeypatch.setattr(api_module, "_ensure_model_leaderboard_refresh", lambda force=False: None)
    _seed_cache(
        monkeypatch,
        payload={
            "leaderboard": [{"model_name": "xgboost", "overall_score": 0.88}],
            "quadrant_points": [{"model_name": "xgboost", "overall_score": 0.88}],
            "count": 1,
        },
        updated_at=time.time(),
    )

    payload = asyncio.run(api_module.api_model_leaderboard())

    assert payload["cached"] is True
    assert payload["count"] == 1
    assert payload["leaderboard"][0]["model_name"] == "xgboost"
    assert payload["refreshing"] is False
    assert "cache_age_sec" in payload



def test_api_model_leaderboard_exposes_leaderboard_governance_payload(monkeypatch, tmp_path):
    monkeypatch.setattr(api_module, "_load_model_leaderboard_cache_file", lambda: None)
    monkeypatch.setattr(api_module, "_ensure_model_leaderboard_refresh", lambda force=False: None)
    governance_path = tmp_path / "leaderboard_feature_profile_probe.json"
    governance_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-19T01:02:03Z",
                "alignment": {
                    "dual_profile_state": "post_threshold_profile_governance_stalled",
                    "train_selected_profile": "core_plus_macro_plus_4h_structure_shift",
                    "train_selected_profile_source": "bull_4h_pocket_ablation.exact_supported_profile",
                    "leaderboard_selected_profile": "core_only",
                    "leaderboard_selected_profile_source": "feature_group_ablation.recommended_profile",
                    "live_current_structure_bucket": "CAUTION|structure_quality_caution|q15",
                    "live_current_structure_bucket_rows": 69,
                    "minimum_support_rows": 50,
                    "profile_split": {
                        "global_profile": "core_only",
                        "global_profile_role": "global_shrinkage_winner",
                        "production_profile": "core_plus_macro_plus_4h_structure_shift",
                        "production_profile_role": "bull_exact_supported_production_profile",
                        "split_required": True,
                        "verdict": "dual_role_required",
                    },
                    "governance_contract": {
                        "verdict": "post_threshold_governance_contract_needs_leaderboard_sync",
                        "treat_as_parity_blocker": True,
                        "current_closure": "exact_supported_but_leaderboard_not_synced",
                        "minimum_support_rows": 50,
                        "live_current_structure_bucket_rows": 69,
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(api_module, "_LEADERBOARD_GOVERNANCE_PROBE_PATH", governance_path)
    _seed_cache(
        monkeypatch,
        payload={
            "leaderboard": [{"model_name": "xgboost", "overall_score": 0.88}],
            "quadrant_points": [{"model_name": "xgboost", "overall_score": 0.88}],
            "count": 1,
        },
        updated_at=time.time(),
    )

    payload = asyncio.run(api_module.api_model_leaderboard())

    assert payload["leaderboard_governance"]["generated_at"] == "2026-04-19T01:02:03Z"
    assert payload["leaderboard_governance"]["dual_profile_state"] == "post_threshold_profile_governance_stalled"
    assert payload["leaderboard_governance"]["profile_split"]["production_profile"] == "core_plus_macro_plus_4h_structure_shift"
    assert payload["leaderboard_governance"]["governance_contract"]["verdict"] == "post_threshold_governance_contract_needs_leaderboard_sync"



def test_api_model_leaderboard_returns_refreshing_shell_when_no_cache(monkeypatch):
    monkeypatch.setattr(api_module, "_load_model_leaderboard_cache_file", lambda: None)
    calls = {"count": 0}

    def _fake_refresh(force=False):
        calls["count"] += 1

    monkeypatch.setattr(api_module, "_ensure_model_leaderboard_refresh", _fake_refresh)
    _seed_cache(monkeypatch, payload=None, updated_at=None)

    payload = asyncio.run(api_module.api_model_leaderboard())

    assert calls["count"] >= 1
    assert payload["refreshing"] is True
    assert payload["stale"] is True
    assert payload["leaderboard"] == []
    assert payload["quadrant_points"] == []



def test_api_model_leaderboard_stale_cache_triggers_background_refresh(monkeypatch):
    monkeypatch.setattr(api_module, "_load_model_leaderboard_cache_file", lambda: None)
    calls = []

    def _fake_spawn(reason: str):
        calls.append(reason)
        api_module._MODEL_LB_CACHE["refreshing"] = True
        api_module._MODEL_LB_CACHE["last_refresh_attempt_at"] = time.time()
        api_module._MODEL_LB_CACHE["last_refresh_reason"] = reason
        return True

    monkeypatch.setattr(api_module, "_spawn_model_leaderboard_refresh_thread", _fake_spawn)
    _seed_cache(
        monkeypatch,
        payload={
            "leaderboard": [{"model_name": "logistic_regression", "overall_score": 0.62}],
            "quadrant_points": [],
            "count": 1,
        },
        updated_at=time.time() - 90_000,
    )

    payload = asyncio.run(api_module.api_model_leaderboard())

    assert calls == ["cache_stale"]
    assert payload["cached"] is True
    assert payload["refreshing"] is True
    assert payload["stale"] is True
    assert payload["leaderboard"][0]["model_name"] == "logistic_regression"
    assert payload["refresh_reason"] == "cache_stale"
    assert payload["refresh_cooldown_sec"] == api_module._MODEL_LB_REFRESH_COOLDOWN_SEC
    assert "背景正在重算" in (payload["warning"] or "")



def test_api_model_leaderboard_stale_cache_respects_refresh_cooldown(monkeypatch):
    monkeypatch.setattr(api_module, "_load_model_leaderboard_cache_file", lambda: None)
    calls = []

    def _fake_spawn(reason: str):
        calls.append(reason)
        return True

    monkeypatch.setattr(api_module, "_spawn_model_leaderboard_refresh_thread", _fake_spawn)
    _seed_cache(
        monkeypatch,
        payload={
            "leaderboard": [{"model_name": "logistic_regression", "overall_score": 0.62}],
            "quadrant_points": [],
            "count": 1,
        },
        updated_at=time.time() - 90_000,
        last_refresh_attempt_at=time.time(),
        last_refresh_reason="cache_stale",
    )

    payload = asyncio.run(api_module.api_model_leaderboard())

    assert calls == []
    assert payload["cached"] is True
    assert payload["refreshing"] is False
    assert payload["stale"] is True
    assert payload["refresh_reason"] == "cache_stale"
    assert payload["next_retry_at"] is not None
    assert "自動再試" in (payload["warning"] or "")



def test_api_model_leaderboard_force_refresh_bypasses_cooldown(monkeypatch):
    monkeypatch.setattr(api_module, "_load_model_leaderboard_cache_file", lambda: None)
    calls = []

    def _fake_spawn(reason: str):
        calls.append(reason)
        api_module._MODEL_LB_CACHE["refreshing"] = True
        api_module._MODEL_LB_CACHE["last_refresh_attempt_at"] = time.time()
        api_module._MODEL_LB_CACHE["last_refresh_reason"] = reason
        return True

    monkeypatch.setattr(api_module, "_spawn_model_leaderboard_refresh_thread", _fake_spawn)
    _seed_cache(
        monkeypatch,
        payload={
            "leaderboard": [{"model_name": "catboost", "overall_score": 0.64}],
            "quadrant_points": [],
            "count": 1,
        },
        updated_at=time.time() - 90_000,
        last_refresh_attempt_at=time.time(),
        last_refresh_reason="cache_stale",
    )

    payload = asyncio.run(api_module.api_model_leaderboard(force=True))

    assert calls == ["force_refresh"]
    assert payload["cached"] is True
    assert payload["refreshing"] is True
    assert payload["refresh_reason"] == "force_refresh"
