from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "high_conviction_topk_api_consistency_probe.py"


def _row(**overrides) -> dict:
    row = {
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
        "support_route": "exact_bucket_unsupported_block",
        "support_governance_route": "exact_live_lane_proxy_available",
        "support_route_deployable": False,
        "deployment_blocker": "circuit_breaker_active",
        "runtime_closure_state": "circuit_breaker_active",
        "current_live_structure_bucket": "BLOCK|bias200_below_min|q00",
        "current_live_structure_bucket_rows": 0,
        "minimum_support_rows": 50,
        "current_live_structure_bucket_gap_to_minimum": 50,
        "release_ready": False,
        "current_recent_window_wins": 9,
        "required_recent_window_wins": 15,
        "additional_recent_window_wins_needed": 6,
        "deployable_verdict": "not_deployable",
        "deployment_candidate_tier": "runtime_blocked_oos_pass",
        "gate_failures": [
            "support_route_not_deployable",
            "deployment_blocker_active",
            "breaker_release_not_ready",
        ],
        "model_gate_failures": [],
        "live_gate_failures": [
            "support_route_not_deployable",
            "deployment_blocker_active",
            "breaker_release_not_ready",
        ],
        "oos_gate_passed": True,
        "blocked_only_by_live_guardrails": True,
    }
    row.update(overrides)
    return row


def _artifact(**overrides) -> dict:
    nearest = _row()
    rows = [
        nearest,
        _row(
            model="xgboost",
            top_k="top_1pct",
            trade_count=29,
            worst_fold=-0.1356,
            model_gate_failures=["min_trades_not_met", "worst_fold_negative"],
            gate_failures=[
                "min_trades_not_met",
                "worst_fold_negative",
                "support_route_not_deployable",
                "deployment_blocker_active",
                "breaker_release_not_ready",
            ],
            oos_gate_passed=False,
            blocked_only_by_live_guardrails=False,
            deployment_candidate_tier="research_oos_gate_failed",
        ),
    ]
    payload = {
        "artifact": "data/high_conviction_topk_oos_matrix.json",
        "generated_at": "2026-06-04T07:48:34.949866+00:00",
        "target_col": "simulated_pyramid_win",
        "samples": 25792,
        "top_k_grid": ["top_1pct", "top_2pct"],
        "row_count": 2,
        "deployable_rows": 0,
        "risk_qualified_rows": 1,
        "runtime_blocked_candidate_rows": 1,
        "support_context": {
            "support_route_verdict": "exact_bucket_unsupported_block",
            "support_governance_route": "exact_live_lane_proxy_available",
            "support_route_deployable": False,
            "deployment_blocker": "circuit_breaker_active",
            "runtime_closure_state": "circuit_breaker_active",
            "current_live_structure_bucket": "BLOCK|bias200_below_min|q00",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "release_ready": False,
            "current_recent_window_wins": 9,
            "required_recent_window_wins": 15,
            "additional_recent_window_wins_needed": 6,
            "support_context_freshness": {
                "status": "fresh",
                "generated_at": "2026-06-04T08:18:19Z",
                "age_minutes": 0.1,
            },
        },
        "nearest_deployable_candidate": nearest,
        "nearest_deployable_rows": [nearest],
        "rows": rows,
    }
    payload.update(overrides)
    return payload


def _api_payload(artifact: dict, **topk_overrides) -> dict:
    support_context = dict(artifact["support_context"])
    support_context["support_context_freshness"] = {
        "status": "fresh",
        "generated_at": "2026-06-04T08:30:00Z",
        "age_minutes": 0.0,
    }
    topk = {
        "source_artifact": "/home/kazuha/Poly-Trader/data/high_conviction_topk_oos_matrix.json",
        "generated_at": artifact["generated_at"],
        "freshness_status": "fresh",
        "artifact_age_minutes": 33.0,
        "stale_after_minutes": 60.0,
        "deployment_ready": False,
        "deployment_readiness_status": "paper_shadow_only",
        "target_col": artifact["target_col"],
        "samples": artifact["samples"],
        "top_k_grid": artifact["top_k_grid"],
        "row_count": artifact["row_count"],
        "deployable_count": artifact["deployable_rows"],
        "risk_qualified_count": artifact["risk_qualified_rows"],
        "runtime_blocked_candidate_count": artifact["runtime_blocked_candidate_rows"],
        "support_context": support_context,
        "nearest_deployable_rows": [dict(artifact["nearest_deployable_candidate"])],
        "best_rows": [dict(artifact["nearest_deployable_candidate"])],
    }
    topk.update(topk_overrides)
    return {"count": 6, "stale": False, "high_conviction_topk": topk}


def _run(args: list[str], *, input_payload: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=json.dumps(input_payload) if input_payload is not None else None,
        text=True,
        capture_output=True,
        cwd=PROJECT_ROOT,
    )


def test_probe_passes_when_api_matches_stable_artifact_contract(tmp_path: Path) -> None:
    artifact = _artifact()
    leaderboard = _api_payload(artifact)
    leaderboard_file = tmp_path / "leaderboard.json"
    artifact_file = tmp_path / "high_conviction_topk_oos_matrix.json"
    leaderboard_file.write_text(json.dumps(leaderboard), encoding="utf-8")
    artifact_file.write_text(json.dumps(artifact), encoding="utf-8")

    result = _run(
        [
            "--leaderboard-file",
            str(leaderboard_file),
            "--artifact-file",
            str(artifact_file),
            "--strict",
            "--compact",
        ]
    )

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is True
    assert summary["api_consistent"] is True
    assert summary["artifact_internal_consistent"] is True
    assert summary["fail_closed_under_blockers"] is True
    assert summary["deployable_count"] == 0
    assert summary["runtime_blocked_candidate_count"] == 1
    assert summary["nearest_model"] == "logistic_regression"


def test_probe_accepts_nearest_candidate_model_name_alias() -> None:
    artifact = _artifact()
    artifact["nearest_deployable_candidate"]["model_name"] = artifact["nearest_deployable_candidate"].pop("model")
    artifact["nearest_deployable_rows"] = [dict(artifact["nearest_deployable_candidate"])]
    leaderboard = _api_payload(artifact)

    result = _run(
        ["--strict"],
        input_payload={"leaderboard": leaderboard, "artifact": artifact},
    )

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is True
    assert summary["nearest_model"] == "logistic_regression"


def test_probe_fails_strict_when_api_count_drifts_from_artifact() -> None:
    artifact = _artifact()
    leaderboard = _api_payload(artifact, deployable_count=1)

    result = _run(
        ["--strict"],
        input_payload={"leaderboard": leaderboard, "artifact": artifact},
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["api_consistent"] is False
    assert any(item["field"] == "deployable_count" for item in summary["api_artifact_mismatches"])


def test_probe_fails_strict_when_nearest_candidate_gate_drifts() -> None:
    artifact = _artifact()
    drifted_nearest = dict(artifact["nearest_deployable_candidate"], deployment_candidate_tier="deployable")
    leaderboard = _api_payload(artifact, nearest_deployable_rows=[drifted_nearest], best_rows=[drifted_nearest])

    result = _run(
        ["--strict"],
        input_payload={"leaderboard": leaderboard, "artifact": artifact},
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert any(
        item["field"] == "nearest.deployment_candidate_tier"
        for item in summary["api_artifact_mismatches"]
    )


def test_probe_fails_strict_when_blocked_live_gate_is_marked_deployable() -> None:
    artifact = _artifact()
    deployable_nearest = dict(artifact["nearest_deployable_candidate"], deployable_verdict="deployable")
    leaderboard = _api_payload(
        artifact,
        deployment_ready=True,
        deployable_count=1,
        nearest_deployable_rows=[deployable_nearest],
        best_rows=[deployable_nearest],
    )

    result = _run(
        ["--strict"],
        input_payload={"leaderboard": leaderboard, "artifact": artifact},
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["api_fail_closed_under_blockers"] is False
    assert summary["fail_closed_under_blockers"] is False


def test_probe_fails_strict_when_artifact_counts_do_not_match_rows() -> None:
    artifact = _artifact(risk_qualified_rows=2)
    leaderboard = _api_payload(artifact, risk_qualified_count=2)

    result = _run(
        ["--strict"],
        input_payload={"leaderboard": leaderboard, "artifact": artifact},
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["artifact_internal_consistent"] is False
    assert any(item["field"] == "risk_qualified_rows" for item in summary["artifact_internal_mismatches"])


def test_probe_fails_strict_when_payload_contains_secret_like_key_without_value_leak() -> None:
    artifact = _artifact()
    leaderboard = _api_payload(artifact)
    leaderboard["high_conviction_topk"]["support_context"]["api_key"] = "should_not_be_printed"

    result = _run(
        ["--strict"],
        input_payload={"leaderboard": leaderboard, "artifact": artifact},
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["secret_safe"] is False
    assert "api.support_context.api_key" in summary["secret_like_key_paths"]
    assert "should_not_be_printed" not in result.stdout
