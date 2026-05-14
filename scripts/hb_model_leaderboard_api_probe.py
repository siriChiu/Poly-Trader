#!/usr/bin/env python3
"""Heartbeat probe for /api/models/leaderboard stale-while-revalidate state.

The API returns immediately and may spawn a background refresh thread in-process when the
cache is stale. Heartbeat verification therefore needs to keep the probe process alive long
enough to observe whether that refresh actually lands, instead of exiting on the first stale
response and reporting a false-negative forever.
"""
from __future__ import annotations

import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from server.routes import api as api_module  # noqa: E402

# Keep the default below common 180s heartbeat subprocess budgets so the probe
# can print a structured timeout summary instead of being killed by its parent.
DEFAULT_MAX_WAIT_SEC = 150.0
DEFAULT_POLL_INTERVAL_SEC = 5.0


SUMMARY_KEYS = (
    "cached",
    "refreshing",
    "stale",
    "warning",
    "leaderboard_warning",
    "error",
    "refresh_reason",
    "refresh_cooldown_sec",
    "next_retry_at",
    "updated_at",
    "cache_age_sec",
    "count",
    "comparable_count",
    "placeholder_count",
    "evaluated_row_count",
    "target_col",
)

LEADERBOARD_GOVERNANCE_KEYS = (
    "generated_at",
    "source_artifact",
    "dual_profile_state",
    "train_selected_profile",
    "train_selected_profile_source",
    "leaderboard_selected_profile",
    "leaderboard_selected_profile_source",
    "live_current_structure_bucket",
    "live_current_structure_bucket_rows",
    "minimum_support_rows",
    "live_current_structure_bucket_gap_to_minimum",
    "support_route_verdict",
    "support_governance_route",
    "profile_split",
    "governance_contract",
)

LEADERBOARD_GOVERNANCE_CONTRACT_KEYS = (
    "verdict",
    "treat_as_parity_blocker",
    "current_closure",
    "reason",
    "recommended_action",
    "global_profile",
    "global_profile_role",
    "production_profile",
    "production_profile_role",
    "support_governance_route",
    "split_required",
    "minimum_support_rows",
    "live_current_structure_bucket_rows",
    "live_current_structure_bucket_gap_to_minimum",
    "support_progress",
)

SUPPORT_IDENTITY_KEYS = (
    "target_col",
    "horizon_minutes",
    "current_live_structure_bucket",
    "regime_label",
    "regime_gate",
    "entry_quality_label",
    "calibration_window",
    "bucket_semantic_signature",
)

SEMANTIC_EVIDENCE_KEYS = (
    "source",
    "matched_fields",
    "mismatched_fields",
    "missing_fields",
    "supports_current_identity",
    "promotable_to_same_identity_history",
    "verdict",
)

SUPPORT_PROGRESS_KEYS = (
    "status",
    "reason",
    "regression_basis",
    "support_identity",
    "current_rows",
    "minimum_support_rows",
    "gap_to_minimum",
    "delta_vs_previous",
    "previous_rows",
    "previous_route_changed",
    "previous_support_route_verdict",
    "previous_support_governance_route",
    "regressed_from_supported",
    "recent_supported_rows",
    "recent_supported_heartbeat",
    "recent_supported_timestamp",
    "delta_vs_recent_supported",
    "legacy_supported_reference",
    "comparable_history_count",
    "legacy_reference_history_count",
    "stagnant_run_count",
    "stalled_support_accumulation",
    "escalate_to_blocker",
)

HIGH_CONVICTION_TOPK_KEYS = (
    "source_artifact",
    "generated_at",
    "freshness_status",
    "freshness_blocker",
    "artifact_age_minutes",
    "stale_after_minutes",
    "deployment_ready",
    "deployment_readiness_status",
    "target_col",
    "samples",
    "row_count",
    "deployable_count",
    "risk_qualified_count",
    "runtime_blocked_candidate_count",
    "support_context",
    "nearest_deployable_rows",
    "best_rows",
)

HIGH_CONVICTION_SUPPORT_CONTEXT_KEYS = (
    "live_truth_overlay_applied",
    "live_truth_generated_at",
    "live_truth_source_artifact",
    "current_live_structure_bucket",
    "current_live_structure_bucket_rows",
    "minimum_support_rows",
    "current_live_structure_bucket_gap_to_minimum",
    "support_route_verdict",
    "support_governance_route",
    "support_route_deployable",
    "deployment_blocker",
    "runtime_closure_state",
    "allowed_layers",
    "signal",
    "execution_guardrail_reason",
    "release_ready",
    "current_streak",
    "recent_window",
    "current_recent_window_win_rate",
    "current_recent_window_wins",
    "required_recent_window_wins",
    "additional_recent_window_wins_needed",
    "support_progress",
)

HIGH_CONVICTION_ROW_KEYS = (
    "model",
    "model_name",
    "feature_profile",
    "regime",
    "top_k",
    "oos_roi",
    "win_rate",
    "profit_factor",
    "max_drawdown",
    "worst_fold",
    "trade_count",
    "deployable_verdict",
    "deployment_candidate_tier",
    "gate_failures",
    "model_gate_failures",
    "live_gate_failures",
    "oos_gate_passed",
    "blocked_only_by_live_guardrails",
    "support_route",
    "support_governance_route",
    "support_route_deployable",
    "deployment_blocker",
    "runtime_closure_state",
    "current_live_structure_bucket",
    "current_live_structure_bucket_rows",
    "minimum_support_rows",
    "current_live_structure_bucket_gap_to_minimum",
    "allowed_layers",
    "signal",
    "execution_guardrail_reason",
    "release_ready",
    "current_recent_window_wins",
    "required_recent_window_wins",
    "additional_recent_window_wins_needed",
)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return value if value >= 0 else default


def _compact_dict(payload: Any, keys: tuple[str, ...]) -> Any:
    if not isinstance(payload, dict):
        return payload
    return {key: payload.get(key) for key in keys if payload.get(key) is not None}


def _compact_support_identity(identity: Any) -> Any:
    return _compact_dict(identity, SUPPORT_IDENTITY_KEYS)


def _compact_semantic_evidence(evidence: Any) -> Any:
    return _compact_dict(evidence, SEMANTIC_EVIDENCE_KEYS)


def _compact_legacy_supported_reference(reference: Any) -> Any:
    if not isinstance(reference, dict):
        return reference
    compact = _compact_dict(
        reference,
        (
            "heartbeat",
            "timestamp",
            "live_current_structure_bucket",
            "live_current_structure_bucket_rows",
            "minimum_support_rows",
            "support_route_verdict",
            "support_governance_route",
            "reference_only_reason",
        ),
    )
    evidence = _compact_semantic_evidence(reference.get("semantic_identity_evidence"))
    if isinstance(evidence, dict) and evidence:
        compact["semantic_identity_evidence"] = evidence
    return compact


def _compact_support_progress(progress: Any) -> Any:
    if not isinstance(progress, dict):
        return progress
    compact = _compact_dict(progress, SUPPORT_PROGRESS_KEYS)
    if isinstance(compact.get("support_identity"), dict):
        compact["support_identity"] = _compact_support_identity(compact["support_identity"])
    if isinstance(compact.get("legacy_supported_reference"), dict):
        compact["legacy_supported_reference"] = _compact_legacy_supported_reference(
            compact["legacy_supported_reference"]
        )
    # The full same-identity history can be hundreds of lines and makes the
    # heartbeat probe unusable as an operator surface. Keep counts/status and
    # current/legacy identity evidence; raw history stays in the source artifact.
    compact.pop("history", None)
    return compact


def _compact_governance_contract(contract: Any) -> Any:
    if not isinstance(contract, dict):
        return contract
    compact = _compact_dict(contract, LEADERBOARD_GOVERNANCE_CONTRACT_KEYS)
    if isinstance(compact.get("support_progress"), dict):
        compact["support_progress"] = _compact_support_progress(compact["support_progress"])
    return compact


def _compact_leaderboard_governance(governance: Any) -> Any:
    if not isinstance(governance, dict):
        return None
    compact = _compact_dict(governance, LEADERBOARD_GOVERNANCE_KEYS)
    if isinstance(compact.get("governance_contract"), dict):
        compact["governance_contract"] = _compact_governance_contract(
            compact["governance_contract"]
        )
    return compact


def _compact_high_conviction_support_context(context: Any) -> Any:
    if not isinstance(context, dict):
        return context
    compact = _compact_dict(context, HIGH_CONVICTION_SUPPORT_CONTEXT_KEYS)
    if isinstance(compact.get("support_progress"), dict):
        compact["support_progress"] = _compact_support_progress(compact["support_progress"])
    return compact


def _compact_high_conviction_row(row: Any) -> Any:
    return _compact_dict(row, HIGH_CONVICTION_ROW_KEYS)


def _compact_high_conviction_rows(rows: Any, *, limit: int = 1) -> list[Dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    compact_rows: list[Dict[str, Any]] = []
    for row in rows:
        compact = _compact_high_conviction_row(row)
        if isinstance(compact, dict):
            compact_rows.append(compact)
        if len(compact_rows) >= limit:
            break
    return compact_rows


def _compact_high_conviction_topk(topk: Any) -> Any:
    if not isinstance(topk, dict):
        return None
    compact = _compact_dict(topk, HIGH_CONVICTION_TOPK_KEYS)
    if isinstance(compact.get("support_context"), dict):
        compact["support_context"] = _compact_high_conviction_support_context(
            compact["support_context"]
        )
    nearest_rows = _compact_high_conviction_rows(topk.get("nearest_deployable_rows"))
    best_rows = _compact_high_conviction_rows(topk.get("best_rows"))
    if nearest_rows:
        compact["nearest_deployable_rows"] = nearest_rows
        compact["nearest_deployable_candidate"] = nearest_rows[0]
    else:
        compact.pop("nearest_deployable_rows", None)
    if best_rows:
        compact["best_rows"] = best_rows
    else:
        compact.pop("best_rows", None)
    return compact


def _summarize(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = {key: payload.get(key) for key in SUMMARY_KEYS}
    summary["leaderboard_governance"] = _compact_leaderboard_governance(
        payload.get("leaderboard_governance")
    )
    summary["high_conviction_topk"] = _compact_high_conviction_topk(
        payload.get("high_conviction_topk")
    )
    return summary


def _truncate_capture(text: str, *, max_lines: int = 20) -> Dict[str, Any]:
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return {
        "suppressed": bool(lines),
        "line_count": len(lines),
        "preview": lines[:max_lines],
    }


async def _fetch_summary() -> Dict[str, Any]:
    payload = await api_module.api_model_leaderboard()
    return _summarize(payload)


async def _run_probe_inner(
    *,
    max_wait_sec: float,
    poll_interval_sec: float,
) -> Dict[str, Any]:
    initial = await _fetch_summary()
    final = dict(initial)
    poll_attempts = 0
    waited_for_refresh = bool(initial.get("stale") and initial.get("refreshing"))
    refresh_completed = False
    timed_out_waiting = False
    refresh_state_changed = False
    started = time.monotonic()

    if waited_for_refresh:
        deadline = started + max_wait_sec
        while time.monotonic() < deadline:
            await asyncio.sleep(poll_interval_sec)
            poll_attempts += 1
            current = await _fetch_summary()
            if current != final:
                refresh_state_changed = True
            final = current
            if not final.get("refreshing"):
                break
        refresh_completed = bool(final.get("stale") is False and final.get("refreshing") is False)
        timed_out_waiting = bool(final.get("refreshing"))

    elapsed = round(time.monotonic() - started, 3)
    result = dict(final)
    result.update(
        {
            "waited_for_refresh": waited_for_refresh,
            "refresh_completed": refresh_completed,
            "timed_out_waiting_for_refresh": timed_out_waiting,
            "refresh_state_changed": refresh_state_changed,
            "poll_attempts": poll_attempts,
            "wait_elapsed_sec": elapsed,
            "max_wait_sec": max_wait_sec,
            "poll_interval_sec": poll_interval_sec,
            "initial_state": initial if waited_for_refresh else None,
        }
    )
    return result


async def run_probe(
    *,
    max_wait_sec: float = DEFAULT_MAX_WAIT_SEC,
    poll_interval_sec: float = DEFAULT_POLL_INTERVAL_SEC,
) -> Dict[str, Any]:
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        result = await _run_probe_inner(
            max_wait_sec=max_wait_sec,
            poll_interval_sec=poll_interval_sec,
        )
    result["suppressed_stdout"] = _truncate_capture(stdout_buffer.getvalue())
    result["suppressed_stderr"] = _truncate_capture(stderr_buffer.getvalue())
    return result


def main() -> None:
    summary = asyncio.run(
        run_probe(
            max_wait_sec=_env_float("HB_LB_WAIT_SEC", DEFAULT_MAX_WAIT_SEC),
            poll_interval_sec=_env_float("HB_LB_POLL_INTERVAL_SEC", DEFAULT_POLL_INTERVAL_SEC),
        )
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
