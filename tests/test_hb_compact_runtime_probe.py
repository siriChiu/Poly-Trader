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
                "deployment_blocker_details": {
                    "support_progress": {
                        "status": "semantic_rebaseline_under_minimum",
                        "reason": "same semantic signature still 0/50 rows",
                        "regression_basis": "same_identity_same_semantic_signature",
                        "delta_vs_previous": 0,
                        "previous_rows": 0,
                        "stagnant_run_count": 3,
                        "stalled_support_accumulation": True,
                        "semantic_signature_delta_vs_previous": 0,
                        "semantic_signature_stagnant_run_count": 3,
                        "semantic_signature_stalled_support_accumulation": True,
                        "semantic_signature_progress": {
                            "previous_rows": 0,
                            "delta_vs_previous": 0,
                            "stagnant_run_count": 3,
                            "stalled_support_accumulation": True,
                        },
                        "equilibrium_deadlock": {
                            "verdict": "equilibrium_deadlock_confirmed",
                            "state": "forced_branch_required",
                            "confirmed": True,
                            "forced_research_action_artifact": {
                                "required": True,
                                "output_path": "data/equilibrium_deadlock_research_action.json",
                            },
                        },
                    },
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
        "execution_surface_contract": {
            "live_canary_policy_gate": {
                "key": "live_canary_policy_gate",
                "status": "blocked",
                "passed": False,
                "summary": "mode=paper / enable_live_trading=false / live_canary.enabled=false / allowed_symbol=true / symbol_cap=0.0001",
                "blockers": [
                    "execution.mode must be live",
                    "enable_live_trading must be true",
                    "execution.live_canary.enabled must be true",
                ],
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
    assert summary["support_progress_status"] == "semantic_rebaseline_under_minimum"
    assert summary["support_regression_basis"] == "same_identity_same_semantic_signature"
    assert summary["support_delta_vs_previous"] == 0
    assert summary["support_previous_rows"] == 0
    assert summary["support_stagnant_run_count"] == 3
    assert summary["support_stalled_support_accumulation"] is True
    assert summary["support_semantic_signature_previous_rows"] == 0
    assert summary["support_semantic_signature_delta_vs_previous"] == 0
    assert summary["support_semantic_signature_stagnant_run_count"] == 3
    assert summary["support_semantic_signature_stalled_support_accumulation"] is True
    assert summary["support_equilibrium_deadlock_verdict"] == (
        "equilibrium_deadlock_confirmed"
    )
    assert summary["support_equilibrium_deadlock_state"] == "forced_branch_required"
    assert summary["support_equilibrium_deadlock_confirmed"] is True
    assert summary["support_forced_research_action_required"] is True
    assert summary["support_forced_research_action_output_path"] == (
        "data/equilibrium_deadlock_research_action.json"
    )
    assert summary["high_conviction_deployable_rows"] == 0
    assert summary["high_conviction_runtime_blocked_candidates"] == 3
    assert summary["live_canary_policy_gate_status"] == "blocked"
    assert summary["live_canary_policy_gate_passed"] is False
    assert "mode=paper" in summary["live_canary_policy_gate_summary"]
    assert summary["live_canary_policy_gate_blockers"] == [
        "execution.mode must be live",
        "enable_live_trading must be true",
        "execution.live_canary.enabled must be true",
    ]


def test_leaderboard_probe_summarizes_fail_closed_topk_context() -> None:
    payload = {
        "count": 6,
        "stale": False,
        "leaderboard_governance": {
            "leaderboard_selected_profile": "core_only",
            "global_recommended_profile": "current_full_no_bull_collapse_4h",
            "governance_contract": {
                "verdict": "single_role_governance_ok",
                "current_closure": "single_profile_alignment",
            },
        },
        "high_conviction_topk": {
            "status": "paper_shadow_only",
            "deployment_readiness_status": "paper_shadow_only",
            "deployment_ready": False,
            "freshness": {
                "status": "fresh",
                "reason": "artifact_within_policy",
                "age_minutes": 12.5,
                "stale_after_minutes": 60.0,
                "deployment_blocking": False,
            },
            "refresh_state": {
                "refreshing": True,
                "last_refresh_reason": "artifact_stale",
                "error": None,
            },
            "samples": 25439,
            "row_count": 24,
            "deployable_count": 0,
            "risk_qualified_count": 6,
            "runtime_blocked_candidate_count": 4,
            "support_context": {
                "support_context_status": "stale_live_probe_shadow_only",
                "support_context_freshness": {
                    "status": "stale",
                    "reason": "artifact_older_than_policy",
                    "age_minutes": 32.5,
                    "stale_after_minutes": 30.0,
                    "deployment_blocking": True,
                },
                "support_context_refresh": {
                    "attempted": True,
                    "status": "refresh_still_stale",
                    "error": "artifact_older_than_policy",
                },
                "live_truth_freshness": {
                    "status": "stale",
                    "reason": "artifact_older_than_policy",
                    "deployment_blocking": True,
                },
                "live_truth_overlay_blocker": "artifact_older_than_policy",
                "current_live_structure_bucket_rows": 0,
                "minimum_support_rows": 50,
                "current_live_structure_bucket_gap_to_minimum": 50,
                "support_route_verdict": "stale_live_support_context",
                "deployment_blocker": "stale_live_support_context",
                "release_ready": False,
                "current_recent_window_wins": 0,
                "required_recent_window_wins": 15,
                "additional_recent_window_wins_needed": 15,
                "stale_support_context_reference": {
                    "current_live_structure_bucket_rows": 6,
                    "current_live_structure_bucket_gap_to_minimum": 44,
                    "deployment_blocker": "circuit_breaker_active",
                },
            },
            "nearest_deployable_rows": [
                {
                    "model": "logistic_regression",
                    "deployment_candidate_tier": "runtime_blocked_oos_pass",
                    "support_route": "stale_live_support_context",
                    "deployment_blocker": "stale_live_support_context",
                    "deployable_verdict": "not_deployable",
                    "gate_failures": [
                        "support_route_not_deployable",
                        "deployment_blocker_active",
                        "breaker_release_not_ready",
                    ],
                    "live_gate_failures": [
                        "support_route_not_deployable",
                        "deployment_blocker_active",
                        "breaker_release_not_ready",
                    ],
                }
            ],
        },
    }

    summary = _run("hb_compact_leaderboard_probe.py", payload)

    assert summary["leaderboard_count"] == 6
    assert summary["selected_feature_profile"] == "core_only"
    assert summary["support_aware_profile"] == "current_full_no_bull_collapse_4h"
    assert summary["governance_contract"] == "single_role_governance_ok"
    assert summary["current_closure"] == "single_profile_alignment"
    assert summary["hc_status"] == "paper_shadow_only"
    assert summary["hc_deployment_ready"] is False
    assert summary["hc_artifact_freshness_status"] == "fresh"
    assert summary["hc_artifact_freshness_reason"] == "artifact_within_policy"
    assert summary["hc_artifact_age_minutes"] == 12.5
    assert summary["hc_artifact_stale_after_minutes"] == 60.0
    assert summary["hc_artifact_deployment_blocking"] is False
    assert summary["hc_refreshing"] is True
    assert summary["hc_refresh_reason"] == "artifact_stale"
    assert summary["hc_refresh_error"] is None
    assert summary["hc_samples"] == 25439
    assert summary["hc_row_count"] == 24
    assert summary["hc_deployable_rows"] == 0
    assert summary["hc_risk_qualified_rows"] == 6
    assert summary["hc_runtime_blocked_candidates"] == 4
    assert summary["hc_support_context_status"] == "stale_live_probe_shadow_only"
    assert summary["hc_support_context_freshness_status"] == "stale"
    assert summary["hc_support_context_freshness_reason"] == "artifact_older_than_policy"
    assert summary["hc_support_context_age_minutes"] == 32.5
    assert summary["hc_support_context_stale_after_minutes"] == 30.0
    assert summary["hc_support_context_deployment_blocking"] is True
    assert summary["hc_support_context_refresh_attempted"] is True
    assert summary["hc_support_context_refresh_status"] == "refresh_still_stale"
    assert summary["hc_support_context_refresh_error"] == "artifact_older_than_policy"
    assert summary["hc_live_truth_freshness_status"] == "stale"
    assert summary["hc_live_truth_freshness_reason"] == "artifact_older_than_policy"
    assert summary["hc_live_truth_deployment_blocking"] is True
    assert summary["hc_live_truth_overlay_blocker"] == "artifact_older_than_policy"
    assert summary["hc_bucket_rows"] == 0
    assert summary["hc_gap"] == 50
    assert summary["hc_support_route"] == "stale_live_support_context"
    assert summary["hc_deployment_blocker"] == "stale_live_support_context"
    assert summary["hc_release_ready"] is False
    assert summary["hc_current_recent_window_wins"] == 0
    assert summary["hc_required_recent_window_wins"] == 15
    assert summary["hc_additional_recent_window_wins_needed"] == 15
    assert summary["hc_stale_reference_bucket_rows"] == 6
    assert summary["hc_stale_reference_gap"] == 44
    assert summary["hc_stale_reference_deployment_blocker"] == "circuit_breaker_active"
    assert summary["hc_nearest_model"] == "logistic_regression"
    assert summary["hc_nearest_tier"] == "runtime_blocked_oos_pass"
    assert summary["hc_nearest_deployment_blocker"] == "stale_live_support_context"
    assert summary["hc_nearest_deployable_verdict"] == "not_deployable"
    assert summary["hc_nearest_gate_failures"] == [
        "support_route_not_deployable",
        "deployment_blocker_active",
        "breaker_release_not_ready",
    ]
    assert summary["hc_nearest_live_gate_failures"] == [
        "support_route_not_deployable",
        "deployment_blocker_active",
        "breaker_release_not_ready",
    ]


def test_execution_probe_keeps_order_and_venue_blockers() -> None:
    payload = {
        "live_ready": False,
        "execution_readiness": {
            "status": "shadow_reduce_only",
            "stage_label": "Shadow / Reduce-only",
            "canary_ready": False,
            "live_ready": False,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "venue_runtime_ready": False,
            "blocking_gate_key": "circuit_breaker_gate",
            "venue_blockers": [
                "live exchange credential 尚未驗證",
                "order ack lifecycle 尚未驗證",
            ],
            "what_can_do_now": [
                "啟動影子觀察並寫入 Shadow Trade Ledger",
                "減碼 / 取消掛單 / 賣出風險降低路徑仍可用",
            ],
            "what_cannot_do_now": [
                "買入 / 加倉仍鎖住",
            ],
            "time_to_evidence": {
                "status": "indeterminate_no_positive_delta",
                "gap_to_minimum": 44,
                "alternative_solution_required": True,
            },
            "alternative_solution_review": {
                "status": "required",
            },
            "gates": [
                {
                    "key": "live_canary_policy_gate",
                    "status": "blocked",
                    "passed": False,
                    "summary": "mode=paper / enable_live_trading=false / live_canary.enabled=false / allowed_symbol=true / symbol_cap=0.0001",
                    "blockers": [
                        "execution.mode must be live",
                        "enable_live_trading must be true",
                        "execution.live_canary.enabled must be true",
                    ],
                }
            ],
        },
        "shadow_trade_ledger": {
            "status": "recording_ready",
            "entries": [{"id": "shadow-1"}],
        },
        "paper_shadow_outcome_reconciliation": {
            "status": "recording_pending_outcomes",
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "summary": {
                "worker_poll_events": 1,
                "pending_outcomes": 1,
                "resolved_outcomes": 0,
                "live_order_submitted": False,
            },
            "rehearsal_proof": {
                "status": "pending_observation_window",
                "can_poll_workers": False,
                "poll_blocked_by_pending_outcome": True,
                "next_reconcile_at": "2026-06-04T09:54:57Z",
                "pending_hours_remaining_min": 23.5,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "live_order_submitted": False,
            },
        },
        "venue_dry_run_proof": {
            "status": "blocked_missing_runtime_backed_proof",
            "readiness_state": "blocked_missing_runtime_backed_proof",
            "credential_present": False,
            "secrets_redacted": True,
            "blockers": ["fill lifecycle 尚未驗證"],
            "order_preview": {
                "order_submission_enabled": False,
            },
        },
        "lanes": {
            "venue_lanes": [{"lane": "binance"}, {"lane": "okx"}],
        },
    }

    summary = _run("hb_compact_execution_overview_probe.py", payload)

    assert summary["readiness_state"] == "shadow_reduce_only"
    assert summary["readiness_stage_label"] == "Shadow / Reduce-only"
    assert summary["live_ready"] is False
    assert summary["canary_ready"] is False
    assert summary["blocking_gate"] == "circuit_breaker_gate"
    assert summary["live_canary_policy_gate_status"] == "blocked"
    assert summary["live_canary_policy_gate_passed"] is False
    assert "mode=paper" in summary["live_canary_policy_gate_summary"]
    assert summary["live_canary_policy_gate_blockers"] == [
        "execution.mode must be live",
        "enable_live_trading must be true",
        "execution.live_canary.enabled must be true",
    ]
    assert summary["order_submission_enabled"] is False
    assert summary["risk_on_order_enabled"] is False
    assert summary["venue_runtime_ready"] is False
    assert summary["paper_shadow"] is True
    assert summary["shadow_trade_ledger_status"] == "recording_ready"
    assert summary["shadow_trade_ledger_entries"] == 1
    assert summary["shadow_rows"] == 1
    assert summary["paper_shadow_outcome_status"] == "recording_pending_outcomes"
    assert summary["paper_shadow_rehearsal_status"] == "pending_observation_window"
    assert summary["paper_shadow_worker_poll_events"] == 1
    assert summary["paper_shadow_pending_outcomes"] == 1
    assert summary["paper_shadow_resolved_outcomes"] == 0
    assert summary["paper_shadow_can_poll_workers"] is False
    assert summary["paper_shadow_poll_blocked_by_pending_outcome"] is True
    assert summary["paper_shadow_next_reconcile_at"] == "2026-06-04T09:54:57Z"
    assert summary["paper_shadow_pending_hours_remaining_min"] == 23.5
    assert summary["paper_shadow_order_submission_enabled"] is False
    assert summary["paper_shadow_risk_on_order_enabled"] is False
    assert summary["paper_shadow_live_order_submitted"] is False
    assert summary["time_to_evidence_status"] == "indeterminate_no_positive_delta"
    assert summary["time_to_evidence_gap_to_minimum"] == 44
    assert summary["alternative_solution_status"] == "required"
    assert summary["alternative_solution_required"] is True
    assert "啟動影子觀察並寫入 Shadow Trade Ledger" in summary["what_can_do_now"]
    assert "買入 / 加倉仍鎖住" in summary["what_cannot_do_now"]
    assert summary["venue_dry_run_status"] == "blocked_missing_runtime_backed_proof"
    assert summary["venue_credential_present"] is False
    assert summary["venue_secrets_redacted"] is True
    assert summary["venue_order_preview_submission_enabled"] is False
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
