from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"


def _run(script_name: str, payload: dict) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script_name)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        cwd=PROJECT_ROOT,
    )
    return json.loads(result.stdout)


def test_status_probe_keeps_nested_live_blocker_truth() -> None:
    payload = {
        "status": "ok",
        "execution": {
            "live_runtime_truth": {
                "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q00",
                "deployment_blocker": "unsupported_exact_live_structure_bucket",
                "deployment_blocker_source": "decision_quality_contract",
                "deployment_blocker_reason": "精準支持樣本 0/50，不可部署",
                "support_route_verdict": "exact_bucket_unsupported_block",
                "support_governance_route": "exact_live_lane_proxy_available",
                "current_live_structure_bucket_rows": 0,
                "minimum_support_rows": 50,
                "current_live_structure_bucket_gap_to_minimum": 50,
                "runtime_closure_state": "patch_inactive_or_blocked",
                "support_progress": {
                    "status": "stalled_under_minimum",
                    "reason": "0/50 rows",
                },
            },
            "high_conviction_topk": {
                "deployable_count": 0,
                "runtime_blocked_candidate_count": 3,
                "support_context": {
                    "support_route_verdict": "exact_bucket_unsupported_block",
                    "deployment_blocker": "unsupported_exact_live_structure_bucket",
                },
            },
        },
    }

    summary = _run("hb_compact_status_probe.py", payload)

    assert summary["status"] == "ok"
    assert summary["deployment_blocker"] == "unsupported_exact_live_structure_bucket"
    assert summary["support_route_verdict"] == "exact_bucket_unsupported_block"
    assert summary["support_rows"] == 0
    assert summary["minimum_support_rows"] == 50
    assert summary["gap_to_minimum"] == 50
    assert summary["high_conviction_deployable_rows"] == 0
    assert summary["high_conviction_runtime_blocked_candidates"] == 3


def test_leaderboard_probe_summarizes_fail_closed_topk_context() -> None:
    payload = {
        "count": 6,
        "stale": False,
        "high_conviction_topk": {
            "deployable_count": 0,
            "runtime_blocked_candidate_count": 4,
            "support_context": {
                "current_live_structure_bucket_rows": 0,
                "minimum_support_rows": 50,
                "current_live_structure_bucket_gap_to_minimum": 50,
                "support_route_verdict": "exact_bucket_unsupported_block",
                "deployment_blocker": "unsupported_exact_live_structure_bucket",
                "release_ready": False,
            },
            "nearest_deployable_rows": [
                {
                    "model": "logistic_regression",
                    "deployment_candidate_tier": "runtime_blocked_oos_pass",
                    "support_route": "exact_bucket_unsupported_block",
                    "deployment_blocker": "unsupported_exact_live_structure_bucket",
                }
            ],
        },
    }

    summary = _run("hb_compact_leaderboard_probe.py", payload)

    assert summary["leaderboard_count"] == 6
    assert summary["hc_deployable_rows"] == 0
    assert summary["hc_runtime_blocked_candidates"] == 4
    assert summary["hc_bucket_rows"] == 0
    assert summary["hc_gap"] == 50
    assert summary["hc_nearest_model"] == "logistic_regression"
    assert summary["hc_nearest_tier"] == "runtime_blocked_oos_pass"
    assert summary["hc_nearest_deployment_blocker"] == "unsupported_exact_live_structure_bucket"


def test_execution_probe_keeps_order_and_venue_blockers() -> None:
    payload = {
        "readiness": {
            "readiness_state": "blocked",
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "venue_runtime_ready": False,
            "venue_blockers": [
                "live exchange credential 尚未驗證",
                "order ack lifecycle 尚未驗證",
            ],
        },
        "lanes": {
            "venue_lanes": [{"lane": "binance"}, {"lane": "okx"}],
            "execution_blockers": ["fill lifecycle 尚未驗證"],
        },
    }

    summary = _run("hb_compact_execution_overview_probe.py", payload)

    assert summary["readiness_state"] == "blocked"
    assert summary["order_submission_enabled"] is False
    assert summary["risk_on_order_enabled"] is False
    assert summary["venue_runtime_ready"] is False
    assert summary["lane_count"] == 2
    assert summary["venue_blockers"] == [
        "live exchange credential 尚未驗證",
        "order ack lifecycle 尚未驗證",
        "fill lifecycle 尚未驗證",
    ]


def test_probe_redacts_secret_key_names() -> None:
    payload = {
        "secret_token": "should-not-leak",
        "execution": {
            "live_runtime_truth": {
                "deployment_blocker_details": {"api_key": "should-not-leak"},
            }
        },
    }

    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "hb_compact_runtime_probe.py"), "status"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        cwd=PROJECT_ROOT,
    )

    assert "should-not-leak" not in result.stdout
