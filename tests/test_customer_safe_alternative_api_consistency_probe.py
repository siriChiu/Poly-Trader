from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "customer_safe_alternative_api_consistency_probe.py"


def _proof() -> dict:
    stable_fields = {
        "artifact": "customer_safe_alternative_proof",
        "generated_at": "2026-06-04T08:41:17Z",
        "canary_ready": False,
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "support_rows": 0,
        "minimum_support_rows": 50,
        "support_gap": 50,
        "blocking_gate": "circuit_breaker_gate",
        "primary_blocking_gate": "circuit_breaker_gate",
        "blocking_gates": ["circuit_breaker_gate", "current_live_support_gate"],
        "breaker_release_ready": False,
        "current_recent_window_wins": 9,
        "required_recent_window_wins": 15,
        "additional_recent_window_wins_needed": 6,
        "topk_deployable_rows": 0,
        "topk_risk_qualified_rows": 6,
        "topk_runtime_blocked_candidate_rows": 6,
        "topk_support_context_status": "fresh_live_probe_overlay",
        "topk_support_context_freshness_status": "fresh",
        "topk_support_context_deployment_blocking": False,
        "topk_live_truth_overlay_blocker": "—",
        "venue_runtime_ready": False,
        "venue_status": "blocked_missing_runtime_backed_proof",
        "blocked_live_lane_count": 1,
        "alternative_solution_required": True,
        "alternative_solution_option_count": 3,
        "alternative_solution_options": 3,
        "selected_alternative_solution": "paper_shadow_decision_support_sleeve",
        "selected_alternative": "paper_shadow_decision_support_sleeve",
        "selected_next_customer_artifact": "data/customer_safe_alternative_proof.json",
        "selected_next_artifact": "data/customer_safe_alternative_proof.json",
        "next_customer_action_count": 2,
    }
    return {
        **stable_fields,
        "summary": dict(stable_fields),
        "alternative_solution_portfolio": {
            "pm_challenge_answered": True,
            "option_count": 3,
            "selected_option": "paper_shadow_decision_support_sleeve",
            "selected_next_artifact": "data/customer_safe_alternative_proof.json",
            "time_to_evidence_bucket": "semantic_rebaseline_review_required_before_reference_rows_count",
            "missing_capability_class": "Constraint/Review",
        },
        "alternative_solutions": [
            {
                "id": "paper_shadow_decision_support_sleeve",
                "role": "customer_usable_now",
                "next_artifact": "data/customer_safe_alternative_proof.json",
                "deployable": False,
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "reference_window": None,
                "reference_rows": None,
            },
            {
                "id": "semantic_rebaseline_review",
                "role": "support_policy_alternative",
                "next_artifact": "OOS + Top-K + support audit replay",
                "deployable": False,
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "reference_window": "all",
                "reference_rows": 237,
            },
            {
                "id": "venue_dry_run_readiness_proof",
                "role": "delivery_risk_reduction",
                "next_artifact": "OKX/Binance dry-run lifecycle proof checklist",
                "deployable": False,
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "reference_window": None,
                "reference_rows": None,
            },
        ],
        "next_customer_actions": [
            {
                "id": "open_execution_paper_shadow",
                "surface": "/execution",
                "mode": "paper_shadow",
                "expected_evidence": "data/paper_shadow_outcome_reconciliation.json",
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
            },
            {
                "id": "track_breaker_and_exact_support",
                "surface": "artifacts",
                "mode": "gate_tracking",
                "expected_evidence": "data/customer_safe_alternative_proof.json",
                "breaker_release_ready": False,
                "current_recent_window_wins": 9,
                "required_recent_window_wins": 15,
                "support_rows": 0,
                "minimum_support_rows": 50,
                "support_gap": 50,
                "topk_deployable_rows": 0,
                "venue_runtime_ready": False,
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
            },
        ],
        "blocked_live_lanes": [
            {
                "id": "live_buy_add_exposure",
                "blocking_gate": "circuit_breaker_gate",
                "blocked_actions": ["live_buy", "live_add"],
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "allowed_alternative": "paper/shadow dry-run",
                "release_condition": {
                    "primary_blocking_gate": "circuit_breaker_gate",
                    "breaker_release_ready": False,
                    "current_recent_window_wins": 9,
                    "required_recent_window_wins": 15,
                    "additional_recent_window_wins_needed": 6,
                    "support_rows": 0,
                    "minimum_support_rows": 50,
                    "support_gap": 50,
                    "support_route_verdict": "exact_bucket_unsupported_block",
                    "topk_deployable_rows": 0,
                    "topk_support_context_status": "fresh_live_probe_overlay",
                    "topk_support_context_freshness_status": "fresh",
                    "topk_support_context_deployment_blocking": False,
                    "topk_live_truth_overlay_blocker": "—",
                    "venue_runtime_ready": False,
                    "venue_status": "blocked_missing_runtime_backed_proof",
                },
            }
        ],
        "source_artifacts": {"live_predict_probe": "not exposed by compact overview"},
    }


def _overview_payload(proof: dict) -> dict:
    return {"customer_safe_alternative_proof": proof}


def _run(args: list[str], *, input_payload: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=json.dumps(input_payload) if input_payload is not None else None,
        text=True,
        capture_output=True,
        cwd=PROJECT_ROOT,
    )


def test_probe_passes_when_overview_and_artifact_match_stable_customer_safe_projection(tmp_path: Path) -> None:
    proof = _proof()
    overview_file = tmp_path / "overview.json"
    artifact_file = tmp_path / "customer_safe_alternative_proof.json"
    overview_file.write_text(json.dumps(_overview_payload(proof)), encoding="utf-8")
    artifact_file.write_text(json.dumps(proof), encoding="utf-8")

    result = _run(
        [
            "--overview-file",
            str(overview_file),
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
    assert summary["summary_consistent"] is True
    assert summary["aliases_consistent"] is True
    assert summary["fail_closed"] is True
    assert summary["secret_safe"] is True


def test_probe_fails_strict_when_overview_and_artifact_support_gap_diverge() -> None:
    overview_proof = _proof()
    artifact_proof = _proof()
    overview_proof["support_gap"] = 49
    overview_proof["summary"] = dict(overview_proof["summary"], support_gap=49)

    result = _run(
        ["--strict"],
        input_payload={
            "execution_overview": _overview_payload(overview_proof),
            "artifact": artifact_proof,
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["api_consistent"] is False
    assert any(item["field"] == "support_gap" for item in summary["overview_artifact_mismatches"])


def test_probe_fails_strict_when_selected_aliases_drift() -> None:
    proof = _proof()
    artifact_proof = _proof()
    artifact_proof["selected_alternative"] = "semantic_rebaseline_review"
    artifact_proof["summary"] = dict(artifact_proof["summary"], selected_alternative="semantic_rebaseline_review")

    result = _run(
        ["--strict"],
        input_payload={
            "execution_overview": _overview_payload(proof),
            "artifact": artifact_proof,
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["aliases_consistent"] is False
    assert any(
        item["source"] == "artifact" and item["field"] == "selected_alternative"
        for item in summary["alias_mismatches"]
    )


def test_probe_fails_strict_when_fail_closed_flags_open_live_path() -> None:
    overview_proof = _proof()
    artifact_proof = _proof()
    artifact_proof["alternative_solutions"][0]["order_submission_enabled"] = True

    result = _run(
        ["--strict"],
        input_payload={
            "overview": _overview_payload(overview_proof),
            "artifact": artifact_proof,
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["artifact_fail_closed"] is False
    assert summary["fail_closed"] is False
    assert "alternative_solutions.0.order_submission_enabled" in summary["artifact_fail_closed_violations"]


def test_probe_fails_strict_when_payload_contains_secret_like_key_without_value_leak() -> None:
    overview_proof = _proof()
    artifact_proof = _proof()
    overview_proof["runtime_context"] = {"api_key": "should_not_leak"}

    result = _run(
        ["--strict"],
        input_payload={
            "api_execution_overview": _overview_payload(overview_proof),
            "artifact": artifact_proof,
        },
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["strict_ok"] is False
    assert summary["secret_safe"] is False
    assert "overview.runtime_context.api_key" in summary["secret_like_key_paths"]
    assert "should_not_leak" not in result.stdout
