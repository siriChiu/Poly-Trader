#!/usr/bin/env python3
"""Compact heartbeat runtime endpoint payloads into operator-safe summaries.

These probes intentionally read JSON from stdin so heartbeat verification can use the
same script against curl output, saved artifacts, or test fixtures without starting a
second application process.  The output is concise, stable JSON that keeps blocker-first
truth visible while avoiding accidental credential disclosure.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

_SECRET_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


def _first_present(*values: Any) -> Any:
    """Return the first value that is present, preserving falsey values like 0/False."""

    for value in values:
        if value is not None:
            return value
    return None


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _find_first_key(node: Any, key: str) -> Any:
    """Depth-first search for the first exact key in a nested JSON object."""

    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            found = _find_first_key(value, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_first_key(item, key)
            if found is not None:
                return found
    return None


def _find_all_keys(node: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(node, dict):
        if key in node:
            found.append(node[key])
        for value in node.values():
            found.extend(_find_all_keys(value, key))
    elif isinstance(node, list):
        for item in node:
            found.extend(_find_all_keys(item, key))
    return found


def _pick(mapping: Mapping[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    return {key: mapping[key] for key in keys if key in mapping}


def _redact(node: Any, key_path: Sequence[str] = ()) -> Any:
    """Redact obvious secret-bearing keys in output JSON."""

    if isinstance(node, dict):
        redacted: dict[str, Any] = {}
        for key, value in node.items():
            lowered = key.lower()
            if any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS):
                redacted[key] = value if isinstance(value, bool) or value is None else "[REDACTED]"
            else:
                redacted[key] = _redact(value, (*key_path, key))
        return redacted
    if isinstance(node, list):
        return [_redact(item, key_path) for item in node]
    return node


def _live_runtime_truth(payload: Mapping[str, Any]) -> dict[str, Any]:
    execution = _mapping(payload.get("execution"))
    surface = _mapping(payload.get("execution_surface_contract"))
    return _first_present(
        _mapping(execution.get("live_runtime_truth")) or None,
        _mapping(surface.get("live_runtime_truth")) or None,
        _mapping(payload.get("live_runtime_truth")) or None,
        {},
    )


def _high_conviction(payload: Mapping[str, Any]) -> dict[str, Any]:
    execution = _mapping(payload.get("execution"))
    surface = _mapping(payload.get("execution_surface_contract"))
    return _first_present(
        _mapping(payload.get("high_conviction_topk")) or None,
        _mapping(execution.get("high_conviction_topk")) or None,
        _mapping(surface.get("high_conviction_topk")) or None,
        {},
    )


def _live_canary_policy_gate(payload: Mapping[str, Any]) -> dict[str, Any]:
    execution = _mapping(payload.get("execution"))
    surface = _mapping(payload.get("execution_surface_contract"))
    execution_readiness = _mapping(payload.get("execution_readiness"))
    direct = _first_present(
        _mapping(surface.get("live_canary_policy_gate")) or None,
        _mapping(execution.get("live_canary_policy_gate")) or None,
        _mapping(payload.get("live_canary_policy_gate")) or None,
    )
    if direct:
        return direct
    for gate in _list(execution_readiness.get("gates")):
        if isinstance(gate, dict) and gate.get("key") == "live_canary_policy_gate":
            return gate
    return {}


def compact_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    live = _live_runtime_truth(payload)
    details = _mapping(live.get("deployment_blocker_details"))
    support_progress = _mapping(live.get("support_progress"))
    if not support_progress:
        support_progress = _mapping(details.get("support_progress"))
    semantic_signature_progress = _mapping(
        support_progress.get("semantic_signature_progress")
    )
    equilibrium_deadlock = _mapping(support_progress.get("equilibrium_deadlock"))
    forced_research_action = _mapping(
        equilibrium_deadlock.get("forced_research_action_artifact")
    )
    high_conviction = _high_conviction(payload)
    high_conviction_support = _mapping(high_conviction.get("support_context"))
    live_canary_policy_gate = _live_canary_policy_gate(payload)
    live_canary_policy_blockers = _list(live_canary_policy_gate.get("blockers"))

    return _redact(
        {
            "status": payload.get("status"),
            "current_live_structure_bucket": live.get("current_live_structure_bucket"),
            "deployment_blocker": live.get("deployment_blocker"),
            "deployment_blocker_source": live.get("deployment_blocker_source"),
            "deployment_blocker_reason": live.get("deployment_blocker_reason"),
            "support_route_verdict": _first_present(
                live.get("support_route_verdict"),
                details.get("support_route_verdict"),
            ),
            "support_governance_route": _first_present(
                live.get("support_governance_route"),
                details.get("support_governance_route"),
            ),
            "support_rows": _first_present(
                live.get("current_live_structure_bucket_rows"),
                live.get("support_rows"),
                details.get("current_live_structure_bucket_rows"),
                details.get("support_rows"),
            ),
            "minimum_support_rows": _first_present(
                live.get("minimum_support_rows"),
                details.get("minimum_support_rows"),
            ),
            "gap_to_minimum": _first_present(
                live.get("current_live_structure_bucket_gap_to_minimum"),
                live.get("gap_to_minimum"),
                details.get("current_live_structure_bucket_gap_to_minimum"),
                details.get("gap_to_minimum"),
            ),
            "support_progress_status": support_progress.get("status"),
            "support_progress_reason": support_progress.get("reason"),
            "support_regression_basis": support_progress.get("regression_basis"),
            "support_delta_vs_previous": support_progress.get("delta_vs_previous"),
            "support_previous_rows": support_progress.get("previous_rows"),
            "support_stagnant_run_count": support_progress.get("stagnant_run_count"),
            "support_stalled_support_accumulation": support_progress.get(
                "stalled_support_accumulation"
            ),
            "support_semantic_signature_previous_rows": semantic_signature_progress.get(
                "previous_rows"
            ),
            "support_semantic_signature_delta_vs_previous": _first_present(
                support_progress.get("semantic_signature_delta_vs_previous"),
                semantic_signature_progress.get("delta_vs_previous"),
            ),
            "support_semantic_signature_stagnant_run_count": _first_present(
                support_progress.get("semantic_signature_stagnant_run_count"),
                semantic_signature_progress.get("stagnant_run_count"),
            ),
            "support_semantic_signature_stalled_support_accumulation": _first_present(
                support_progress.get("semantic_signature_stalled_support_accumulation"),
                semantic_signature_progress.get("stalled_support_accumulation"),
            ),
            "support_equilibrium_deadlock_verdict": equilibrium_deadlock.get("verdict"),
            "support_equilibrium_deadlock_state": equilibrium_deadlock.get("state"),
            "support_equilibrium_deadlock_confirmed": equilibrium_deadlock.get(
                "confirmed"
            ),
            "support_forced_research_action_required": _first_present(
                support_progress.get("forced_research_action_required"),
                forced_research_action.get("required"),
            ),
            "support_forced_research_action_output_path": _first_present(
                support_progress.get("forced_research_action_output_path"),
                forced_research_action.get("output_path"),
            ),
            "runtime_closure_state": live.get("runtime_closure_state"),
            "owner_approved": live.get("owner_approved"),
            "strategy_release_ready": live.get("strategy_release_ready"),
            "strategy_release_status": live.get("strategy_release_status"),
            "statistical_gate_blocking": live.get("statistical_gate_blocking"),
            "statistical_warnings": _list(live.get("statistical_warnings")),
            "technical_execution_blockers": _list(live.get("technical_execution_blockers")),
            "support_evidence_ratio": live.get("support_evidence_ratio"),
            "model_evidence_ratio": live.get("model_evidence_ratio"),
            "evidence_score": live.get("evidence_score"),
            "evidence_tier": live.get("evidence_tier"),
            "recommended_max_layers": live.get("recommended_max_layers"),
            "runtime_binding_verified": live.get("runtime_binding_verified"),
            "release_ready": live.get("release_ready"),
            "allowed_layers": live.get("allowed_layers"),
            "signal": live.get("signal"),
            "high_conviction_deployable_rows": _first_present(
                high_conviction.get("deployable_count"),
                high_conviction.get("deployable_rows"),
            ),
            "high_conviction_owner_approved_rows": high_conviction.get("owner_approved_rows"),
            "high_conviction_strategy_release_ready_rows": high_conviction.get("strategy_release_ready_rows"),
            "high_conviction_runtime_blocked_candidates": high_conviction.get(
                "runtime_blocked_candidate_count"
            ),
            "high_conviction_support_route": high_conviction_support.get(
                "support_route_verdict"
            ),
            "high_conviction_deployment_blocker": high_conviction_support.get(
                "deployment_blocker"
            ),
            "live_canary_policy_gate_status": live_canary_policy_gate.get("status"),
            "live_canary_policy_gate_passed": live_canary_policy_gate.get("passed"),
            "live_canary_policy_gate_summary": live_canary_policy_gate.get("summary"),
            "live_canary_policy_gate_blockers": live_canary_policy_blockers,
        }
    )


def _leaderboard_rows(payload: Mapping[str, Any]) -> list[Any]:
    return _list(
        _first_present(
            payload.get("leaderboard"),
            payload.get("rows"),
            payload.get("models"),
            payload.get("items"),
        )
    )


def _first_row(rows: Any) -> dict[str, Any]:
    rows_list = _list(rows)
    if rows_list and isinstance(rows_list[0], dict):
        return rows_list[0]
    return {}


def compact_leaderboard(payload: Mapping[str, Any]) -> dict[str, Any]:
    high_conviction = _high_conviction(payload)
    support = _mapping(high_conviction.get("support_context"))
    artifact_freshness = _mapping(high_conviction.get("freshness"))
    refresh_state = _mapping(high_conviction.get("refresh_state"))
    support_freshness = _mapping(support.get("support_context_freshness"))
    support_refresh = _mapping(support.get("support_context_refresh"))
    live_truth_freshness = _mapping(support.get("live_truth_freshness"))
    stale_reference = _mapping(support.get("stale_support_context_reference"))
    governance = _mapping(payload.get("leaderboard_governance"))
    profile_split = _mapping(governance.get("profile_split"))
    governance_contract = _mapping(governance.get("governance_contract"))
    nearest = _first_row(high_conviction.get("nearest_deployable_rows"))
    if not nearest:
        nearest = _first_row(high_conviction.get("best_rows"))

    leaderboard_rows = _leaderboard_rows(payload)
    leaderboard_count = _first_present(
        payload.get("count"),
        payload.get("leaderboard_count"),
        len(leaderboard_rows) if leaderboard_rows else None,
    )

    return _redact(
        {
            "leaderboard_count": leaderboard_count,
            "payload_stale": _first_present(payload.get("stale"), payload.get("payload_stale")),
            "selected_feature_profile": _first_present(
                payload.get("selected_feature_profile"),
                governance.get("leaderboard_selected_profile"),
            ),
            "support_aware_profile": _first_present(
                payload.get("support_aware_profile"),
                governance.get("global_recommended_profile"),
                profile_split.get("production_profile"),
                governance_contract.get("production_profile"),
            ),
            "governance_contract": governance_contract.get("verdict"),
            "current_closure": governance_contract.get("current_closure"),
            "hc_status": _first_present(
                high_conviction.get("deployment_readiness_status"),
                high_conviction.get("status"),
            ),
            "hc_deployment_ready": high_conviction.get("deployment_ready"),
            "hc_artifact_freshness_status": _first_present(
                high_conviction.get("freshness_status"),
                high_conviction.get("artifact_freshness_status"),
                artifact_freshness.get("status"),
            ),
            "hc_artifact_freshness_reason": _first_present(
                high_conviction.get("freshness_blocker"),
                high_conviction.get("artifact_freshness_reason"),
                artifact_freshness.get("reason"),
            ),
            "hc_artifact_age_minutes": _first_present(
                high_conviction.get("artifact_age_minutes"),
                artifact_freshness.get("age_minutes"),
            ),
            "hc_artifact_stale_after_minutes": _first_present(
                high_conviction.get("stale_after_minutes"),
                high_conviction.get("artifact_stale_after_minutes"),
                artifact_freshness.get("stale_after_minutes"),
            ),
            "hc_artifact_deployment_blocking": _first_present(
                high_conviction.get("artifact_deployment_blocking"),
                artifact_freshness.get("deployment_blocking"),
            ),
            "hc_refreshing": _first_present(
                high_conviction.get("refreshing"),
                refresh_state.get("refreshing"),
            ),
            "hc_refresh_reason": _first_present(
                high_conviction.get("refresh_reason"),
                refresh_state.get("last_refresh_reason"),
            ),
            "hc_refresh_error": _first_present(
                high_conviction.get("refresh_error"),
                refresh_state.get("error"),
            ),
            "hc_samples": high_conviction.get("samples"),
            "hc_row_count": _first_present(
                high_conviction.get("row_count"),
                high_conviction.get("rows"),
            ),
            "hc_deployable_rows": _first_present(
                high_conviction.get("deployable_count"),
                high_conviction.get("deployable_rows"),
            ),
            "hc_owner_approved_rows": high_conviction.get("owner_approved_rows"),
            "hc_strategy_release_ready_rows": high_conviction.get("strategy_release_ready_rows"),
            "hc_risk_qualified_rows": _first_present(
                high_conviction.get("risk_qualified_count"),
                high_conviction.get("risk_qualified_rows"),
            ),
            "hc_runtime_blocked_candidates": high_conviction.get(
                "runtime_blocked_candidate_count"
            ),
            "hc_support_context_status": _first_present(
                support.get("support_context_status"),
                high_conviction.get("support_context_status"),
            ),
            "hc_support_context_freshness_status": support_freshness.get("status"),
            "hc_support_context_freshness_reason": support_freshness.get("reason"),
            "hc_support_context_age_minutes": support_freshness.get("age_minutes"),
            "hc_support_context_stale_after_minutes": support_freshness.get(
                "stale_after_minutes"
            ),
            "hc_support_context_deployment_blocking": support_freshness.get(
                "deployment_blocking"
            ),
            "hc_support_context_refresh_status": support_refresh.get("status"),
            "hc_support_context_refresh_attempted": support_refresh.get("attempted"),
            "hc_support_context_refresh_error": support_refresh.get("error"),
            "hc_live_truth_freshness_status": live_truth_freshness.get("status"),
            "hc_live_truth_freshness_reason": live_truth_freshness.get("reason"),
            "hc_live_truth_deployment_blocking": live_truth_freshness.get(
                "deployment_blocking"
            ),
            "hc_live_truth_overlay_blocker": support.get("live_truth_overlay_blocker"),
            "hc_bucket_rows": _first_present(
                support.get("current_live_structure_bucket_rows"),
                support.get("support_rows"),
            ),
            "hc_minimum_support_rows": support.get("minimum_support_rows"),
            "hc_gap": _first_present(
                support.get("current_live_structure_bucket_gap_to_minimum"),
                support.get("gap_to_minimum"),
            ),
            "hc_support_route": support.get("support_route_verdict"),
            "hc_deployment_blocker": support.get("deployment_blocker"),
            "hc_release_ready": support.get("release_ready"),
            "hc_current_recent_window_wins": _first_present(
                support.get("current_recent_window_wins"),
                nearest.get("current_recent_window_wins"),
            ),
            "hc_required_recent_window_wins": _first_present(
                support.get("required_recent_window_wins"),
                nearest.get("required_recent_window_wins"),
            ),
            "hc_additional_recent_window_wins_needed": _first_present(
                support.get("additional_recent_window_wins_needed"),
                nearest.get("additional_recent_window_wins_needed"),
            ),
            "hc_stale_reference_bucket_rows": stale_reference.get(
                "current_live_structure_bucket_rows"
            ),
            "hc_stale_reference_gap": stale_reference.get(
                "current_live_structure_bucket_gap_to_minimum"
            ),
            "hc_stale_reference_deployment_blocker": stale_reference.get(
                "deployment_blocker"
            ),
            "hc_nearest_model": _first_present(nearest.get("model"), nearest.get("model_name")),
            "hc_nearest_tier": nearest.get("deployment_candidate_tier"),
            "hc_nearest_support_route": _first_present(
                nearest.get("support_route"), nearest.get("support_route_verdict")
            ),
            "hc_nearest_deployment_blocker": nearest.get("deployment_blocker"),
            "hc_nearest_deployable_verdict": nearest.get("deployable_verdict"),
            "hc_nearest_owner_approved": nearest.get("owner_approved"),
            "hc_nearest_strategy_release_ready": nearest.get("strategy_release_ready"),
            "hc_nearest_strategy_release_status": nearest.get("strategy_release_status"),
            "hc_nearest_evidence_tier": nearest.get("evidence_tier"),
            "hc_nearest_recommended_max_layers": nearest.get("recommended_max_layers"),
            "hc_nearest_statistical_warnings": _list(nearest.get("statistical_warnings")),
            "hc_nearest_technical_execution_blockers": _list(nearest.get("technical_execution_blockers")),
            "hc_nearest_gate_failures": _list(nearest.get("gate_failures")),
            "hc_nearest_live_gate_failures": _list(nearest.get("live_gate_failures")),
        }
    )


def _flatten_blockers(values: Iterable[Any]) -> list[Any]:
    blockers: list[Any] = []
    for value in values:
        if isinstance(value, list):
            blockers.extend(value)
        elif value:
            blockers.append(value)
    # Preserve order while deduplicating simple scalar blockers.
    seen: set[str] = set()
    compacted: list[Any] = []
    for blocker in blockers:
        marker = json.dumps(blocker, ensure_ascii=False, sort_keys=True) if isinstance(blocker, (dict, list)) else str(blocker)
        if marker not in seen:
            seen.add(marker)
            compacted.append(blocker)
    return compacted


def compact_execution(payload: Mapping[str, Any]) -> dict[str, Any]:
    execution_readiness = _mapping(payload.get("execution_readiness"))
    venue_dry_run_proof = _mapping(payload.get("venue_dry_run_proof"))
    shadow_trade_ledger = _mapping(payload.get("shadow_trade_ledger"))
    paper_shadow_outcome = _mapping(payload.get("paper_shadow_outcome_reconciliation"))
    paper_shadow_artifact = _mapping(paper_shadow_outcome.get("artifact"))
    paper_shadow_summary = _mapping(
        _first_present(
            paper_shadow_outcome.get("summary"),
            paper_shadow_artifact.get("summary"),
        )
    )
    paper_shadow_proof = _mapping(
        _first_present(
            paper_shadow_outcome.get("rehearsal_proof"),
            paper_shadow_artifact.get("rehearsal_proof"),
        )
    )
    canary_gap_answers = _mapping(payload.get("canary_gap_answers"))
    time_to_evidence = _mapping(
        _first_present(
            execution_readiness.get("time_to_evidence"),
            canary_gap_answers.get("time_to_evidence"),
        )
    )
    alternative_solution_review = _mapping(
        _first_present(
            execution_readiness.get("alternative_solution_review"),
            canary_gap_answers.get("alternative_solution_review"),
        )
    )
    blockers = _flatten_blockers(
        [
            *_find_all_keys(payload, "venue_blockers"),
            *_find_all_keys(payload, "execution_blockers"),
            *_find_all_keys(payload, "live_ready_blockers"),
            *_find_all_keys(payload, "blockers"),
        ]
    )
    venue_runtime_ready = _find_first_key(payload, "venue_runtime_ready")
    if venue_runtime_ready is None:
        explicit_venue_ready = venue_dry_run_proof.get("runtime_ready")
        if isinstance(explicit_venue_ready, bool):
            venue_runtime_ready = explicit_venue_ready
        elif venue_dry_run_proof:
            venue_runtime_ready = venue_dry_run_proof.get("status") in {
                "ready",
                "runtime_ready",
                "runtime_backed_proof_ready",
            }
    shadow_entries = _list(shadow_trade_ledger.get("entries"))
    shadow_status = shadow_trade_ledger.get("status")
    paper_shadow = _find_first_key(payload, "paper_shadow")
    if paper_shadow is None and shadow_trade_ledger:
        paper_shadow = shadow_status in {
            "recording_ready",
            "recording_pending_outcomes",
            "pending_observation_window",
        }
    live_canary_policy_gate = _live_canary_policy_gate(payload)
    live_canary_policy_blockers = _list(live_canary_policy_gate.get("blockers"))

    return _redact(
        {
            "order_submission_enabled": _find_first_key(
                payload, "order_submission_enabled"
            ),
            "risk_on_order_enabled": _find_first_key(payload, "risk_on_order_enabled"),
            "venue_runtime_ready": venue_runtime_ready,
            "live_ready": _first_present(payload.get("live_ready"), execution_readiness.get("live_ready")),
            "canary_ready": _first_present(
                execution_readiness.get("canary_ready"),
                canary_gap_answers.get("canary_ready"),
                payload.get("canary_ready"),
            ),
            "blocking_gate": _first_present(
                execution_readiness.get("blocking_gate_key"),
                canary_gap_answers.get("blocked_gate_key"),
                canary_gap_answers.get("blocking_gate"),
            ),
            "live_canary_policy_gate_status": live_canary_policy_gate.get("status"),
            "live_canary_policy_gate_passed": live_canary_policy_gate.get("passed"),
            "live_canary_policy_gate_summary": live_canary_policy_gate.get("summary"),
            "live_canary_policy_gate_blockers": live_canary_policy_blockers,
            "readiness_state": _first_present(
                execution_readiness.get("status"),
                _find_first_key(payload, "readiness_state"),
                venue_dry_run_proof.get("status"),
                _find_first_key(payload, "state"),
            ),
            "readiness_stage_label": execution_readiness.get("stage_label"),
            "paper_shadow": paper_shadow,
            "shadow_trade_ledger_status": shadow_trade_ledger.get("status"),
            "shadow_trade_ledger_entries": len(shadow_entries),
            "shadow_rows": _first_present(_find_first_key(payload, "shadow_rows"), len(shadow_entries) if shadow_trade_ledger else None),
            "paper_shadow_outcome_status": _first_present(
                paper_shadow_outcome.get("status"),
                paper_shadow_artifact.get("status"),
            ),
            "paper_shadow_rehearsal_status": paper_shadow_proof.get("status"),
            "paper_shadow_worker_poll_events": paper_shadow_summary.get("worker_poll_events"),
            "paper_shadow_pending_outcomes": paper_shadow_summary.get("pending_outcomes"),
            "paper_shadow_resolved_outcomes": paper_shadow_summary.get("resolved_outcomes"),
            "paper_shadow_can_poll_workers": paper_shadow_proof.get("can_poll_workers"),
            "paper_shadow_poll_blocked_by_pending_outcome": paper_shadow_proof.get("poll_blocked_by_pending_outcome"),
            "paper_shadow_next_reconcile_at": paper_shadow_proof.get("next_reconcile_at"),
            "paper_shadow_pending_hours_remaining_min": paper_shadow_proof.get("pending_hours_remaining_min"),
            "paper_shadow_order_submission_enabled": _first_present(
                paper_shadow_proof.get("order_submission_enabled"),
                paper_shadow_outcome.get("order_submission_enabled"),
                paper_shadow_artifact.get("order_submission_enabled"),
            ),
            "paper_shadow_risk_on_order_enabled": _first_present(
                paper_shadow_proof.get("risk_on_order_enabled"),
                paper_shadow_outcome.get("risk_on_order_enabled"),
                paper_shadow_artifact.get("risk_on_order_enabled"),
            ),
            "paper_shadow_live_order_submitted": _first_present(
                paper_shadow_proof.get("live_order_submitted"),
                paper_shadow_summary.get("live_order_submitted"),
            ),
            "what_can_do_now": _list(execution_readiness.get("what_can_do_now")),
            "what_cannot_do_now": _list(execution_readiness.get("what_cannot_do_now")),
            "time_to_evidence_status": time_to_evidence.get("status"),
            "time_to_evidence_gap_to_minimum": time_to_evidence.get("gap_to_minimum"),
            "alternative_solution_status": alternative_solution_review.get("status"),
            "alternative_solution_required": _first_present(
                alternative_solution_review.get("status") == "required"
                if alternative_solution_review
                else None,
                time_to_evidence.get("alternative_solution_required"),
            ),
            "venue_blockers": [
                blocker for blocker in blockers if blocker not in live_canary_policy_blockers
            ],
            "venue_dry_run_status": venue_dry_run_proof.get("status"),
            "venue_credential_present": venue_dry_run_proof.get("credential_present"),
            "venue_secrets_redacted": venue_dry_run_proof.get("secrets_redacted"),
            "venue_order_preview_submission_enabled": _mapping(venue_dry_run_proof.get("order_preview")).get(
                "order_submission_enabled"
            ),
            "lane_count": _first_present(
                _find_first_key(payload, "lane_count"),
                len(_list(_find_first_key(payload, "venue_lanes")))
                if _find_first_key(payload, "venue_lanes") is not None
                else None,
            ),
        }
    )


def _load_stdin() -> Mapping[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("expected JSON payload on stdin")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("expected top-level JSON object")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("status", "leaderboard", "execution"),
        help="Endpoint payload type to compact.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit single-line JSON instead of pretty-printed JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = _load_stdin()
    if args.mode == "status":
        summary = compact_status(payload)
    elif args.mode == "leaderboard":
        summary = compact_leaderboard(payload)
    else:
        summary = compact_execution(payload)

    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":") if args.compact else None,
            indent=None if args.compact else 2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
