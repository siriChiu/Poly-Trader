import asyncio
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
