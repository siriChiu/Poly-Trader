#!/usr/bin/env python3
"""Synchronize docs/pm/pm-status.md from current runtime artifacts.

The engineering heartbeat refreshes live artifacts before the next PM heartbeat
runs.  This helper keeps the PM status document aligned with those artifacts so
`scripts/pm_heartbeat_check.py` catches real drift instead of stale literals.
It is stdlib-only and secret-safe: it never emits DB URLs or credential values.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = PROJECT_ROOT / "docs" / "pm" / "pm-status.md"
TOPK_STALE_AFTER_MINUTES = 60.0
TOPK_LIVE_SUPPORT_STALE_AFTER_MINUTES = 30.0
PM_CURRENT_ARTIFACT_STALE_AFTER_MINUTES = 24.0 * 60.0
PM_CURRENT_ARTIFACT_FRESHNESS_PATHS = (
    "data/live_predict_probe.json",
    "data/live_decision_quality_drilldown.json",
    "data/circuit_breaker_audit.json",
    "data/recent_drift_report.json",
    "data/execution_metadata_smoke.json",
    "data/venue_dry_run_proof.json",
    "data/q15_support_audit.json",
    "data/q15_support_fill_feasibility.json",
    "data/q15_exact_bucket_row_harvest_proof.json",
    "data/q15_drift_rebaseline_backtest.json",
    "data/q15_map_signal_redesign_proof.json",
    "data/customer_safe_alternative_proof.json",
    "data/live_canary_structural_pivot.json",
    "data/no_trade_lane_replay.json",
    "data/paper_shadow_outcome_reconciliation.json",
)


def _load_json(rel_path: str) -> dict[str, Any]:
    path = PROJECT_ROOT / rel_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"__missing__": rel_path}
    except json.JSONDecodeError as exc:
        return {"__error__": f"{rel_path}: {exc}"}
    return payload if isinstance(payload, dict) else {"__error__": f"{rel_path}: root is not an object"}


def _artifact_freshness_fields(
    generated_at: Any,
    *,
    stale_after_minutes: float,
    now: datetime | None = None,
) -> dict[str, Any]:
    checked_at = (now or datetime.now().astimezone()).astimezone(timezone.utc)
    payload: dict[str, Any] = {
        "artifact_freshness_status": "unavailable",
        "artifact_freshness_reason": "missing_generated_at",
        "artifact_age_minutes": None,
        "artifact_stale_after_minutes": stale_after_minutes,
        "artifact_deployment_blocking": True,
        "artifact_freshness_checked_at": checked_at.isoformat(),
    }
    if not generated_at:
        return payload
    try:
        generated_dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    except ValueError:
        payload["artifact_freshness_reason"] = "invalid_generated_at"
        return payload
    if generated_dt.tzinfo is None:
        generated_dt = generated_dt.replace(tzinfo=timezone.utc)
    age_minutes = max((checked_at - generated_dt.astimezone(timezone.utc)).total_seconds(), 0.0) / 60.0
    status = "fresh" if age_minutes <= stale_after_minutes else "stale"
    payload.update(
        {
            "artifact_freshness_status": status,
            "artifact_freshness_reason": "artifact_within_policy" if status == "fresh" else "artifact_older_than_policy",
            "artifact_age_minutes": age_minutes,
            "artifact_deployment_blocking": status != "fresh",
        }
    )
    return payload


def _topk_freshness_fields(generated_at: Any, *, now: datetime | None = None) -> dict[str, Any]:
    return _artifact_freshness_fields(
        generated_at,
        stale_after_minutes=TOPK_STALE_AFTER_MINUTES,
        now=now,
    )


def _topk_live_support_freshness_fields(
    generated_at: Any,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    freshness = _artifact_freshness_fields(
        generated_at,
        stale_after_minutes=TOPK_LIVE_SUPPORT_STALE_AFTER_MINUTES,
        now=now,
    )
    return {
        "support_context_freshness_status": freshness.get("artifact_freshness_status"),
        "support_context_freshness_reason": freshness.get("artifact_freshness_reason"),
        "support_context_age_minutes": freshness.get("artifact_age_minutes"),
        "support_context_stale_after_minutes": freshness.get("artifact_stale_after_minutes"),
        "support_context_deployment_blocking": freshness.get("artifact_deployment_blocking"),
    }


def _first_present(*values: Any, default: Any = "—") -> Any:
    for value in values:
        if value is not None:
            return value
    return default


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _support_ready(rows: Any, minimum: Any, gap: Any, support_route: Any) -> bool:
    rows_int = _as_int(rows)
    minimum_int = _as_int(minimum)
    gap_int = _as_int(gap)
    return bool(
        support_route == "exact_bucket_supported"
        or (
            rows_int is not None
            and minimum_int is not None
            and rows_int >= minimum_int
            and (gap_int is None or gap_int <= 0)
        )
    )


def _support_clause(*, rows: Any, minimum: Any, gap: Any, support_route: Any, support_ready: bool) -> str:
    if support_ready:
        return (
            f"current exact support 已達 `{rows}/{minimum}`（gap `{gap}`、route `{support_route}`），"
            "但這只是 support gate，不是 deployment closure"
        )
    return (
        f"current exact support 仍是 `{rows}/{minimum}`、gap `{gap}`，"
        "尚未建立同一 support identity 的精準樣本"
    )


def _support_handoff_clause(*, rows: Any, minimum: Any, gap: Any, support_ready: bool) -> str:
    if support_ready:
        return f"承認 current-live exact support 已達 `{rows}/{minimum}`（gap `{gap}`），但 live gate 仍由 breaker / Top-K / venue runtime proof 共同約束"
    return "維持 current-live exact-support blocker"


def _governance_route_interpretation(governance_route: Any, *, support_ready: bool) -> str:
    route_text = str(governance_route or "")
    if support_ready:
        return "是 exact-support evidence；仍不是部署閉環，必須等 breaker、Top-K、venue/runtime gates 一起通過"
    if "proxy" in route_text:
        return "只能當治理 / proxy reference，不是部署閉環"
    return "只能當 support-governance signal，不是部署閉環"


def _bool_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "—"
    return str(value)


def _num_text(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return _bool_text(value)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.{digits}f}"


def _pct_text(value: Any, digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return str(value)


def _hours_until(value: Any, *, now: datetime) -> str:
    if not value:
        return "—"
    try:
        target = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return "invalid_next_reconcile_at"
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    hours = max((target.astimezone(timezone.utc) - now.astimezone(timezone.utc)).total_seconds(), 0.0) / 3600.0
    return _num_text(hours, digits=3)


def _support_progress(probe: dict[str, Any]) -> dict[str, Any]:
    details = probe.get("deployment_blocker_details")
    if not isinstance(details, dict):
        details = {}
    progress = probe.get("support_progress") or details.get("support_progress") or {}
    return progress if isinstance(progress, dict) else {}


def _runtime_blocked_rows(topk: dict[str, Any]) -> list[dict[str, Any]]:
    rows = topk.get("rows") if isinstance(topk.get("rows"), list) else []
    return [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("deployment_candidate_tier") == "runtime_blocked_oos_pass"
    ]


def _best_topk_candidate(topk: dict[str, Any]) -> dict[str, Any]:
    for key in ("nearest_deployable_candidate", "best_not_deployable", "highest_roi_not_deployable"):
        value = topk.get(key)
        if isinstance(value, dict) and value:
            return value
    rows = _runtime_blocked_rows(topk)
    return rows[0] if rows else {}


def _drift_primary(drift: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    primary = drift.get("primary_window") or drift.get("blocking_window") or {}
    if isinstance(primary, dict):
        window = str(primary.get("window") or "—")
        summary = primary.get("summary") if isinstance(primary.get("summary"), dict) else primary
        return window, summary if isinstance(summary, dict) else {}
    windows = drift.get("windows") if isinstance(drift.get("windows"), dict) else {}
    if windows:
        window, payload = next(iter(windows.items()))
        summary = payload.get("summary") if isinstance(payload, dict) and isinstance(payload.get("summary"), dict) else payload
        return str(window), summary if isinstance(summary, dict) else {}
    return "—", {}


def _safe_join(values: Any) -> str:
    if isinstance(values, list):
        return ", ".join(str(item) for item in values) or "—"
    if values in (None, ""):
        return "—"
    return str(values)


def _redact(text: str) -> str:
    text = re.sub(r"\b[A-Z][A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD)\b", "[REDACTED]", text)
    text = re.sub(r"\b[a-zA-Z0-9]+[._-](?:api[_-]?key|token|secret|password)\b", "[REDACTED]", text)
    text = re.sub(r"sqlite:////?[^\s`]+", "[REDACTED]", text)
    return text


def _pm_artifact_freshness_lines(
    payloads: dict[str, dict[str, Any]],
    *,
    now: datetime,
) -> list[str]:
    lines: list[str] = []
    for rel_path in PM_CURRENT_ARTIFACT_FRESHNESS_PATHS:
        payload = payloads.get(rel_path) if isinstance(payloads.get(rel_path), dict) else {}
        freshness = _artifact_freshness_fields(
            payload.get("generated_at"),
            stale_after_minutes=PM_CURRENT_ARTIFACT_STALE_AFTER_MINUTES,
            now=now,
        )
        lines.append(
            f"- `{rel_path} freshness_status={freshness.get('artifact_freshness_status')}` / "
            f"`artifact_age_minutes={_num_text(freshness.get('artifact_age_minutes'), 2)}` / "
            f"`artifact_stale_after_minutes={_num_text(freshness.get('artifact_stale_after_minutes'), 1)}` / "
            f"`freshness_reason={freshness.get('artifact_freshness_reason')}`。"
        )
    return lines


def build_pm_status_markdown(now: datetime | None = None) -> str:
    probe = _load_json("data/live_predict_probe.json")
    drilldown = _load_json("data/live_decision_quality_drilldown.json")
    breaker = _load_json("data/circuit_breaker_audit.json")
    topk = _load_json("data/high_conviction_topk_oos_matrix.json")
    execution = _load_json("data/execution_metadata_smoke.json")
    venue_dry_run = _load_json("data/venue_dry_run_proof.json")
    q15_support = _load_json("data/q15_support_audit.json")
    drift = _load_json("data/recent_drift_report.json")
    fill = _load_json("data/q15_support_fill_feasibility.json")
    exact_harvest = _load_json("data/q15_exact_bucket_row_harvest_proof.json")
    drift_rebaseline = _load_json("data/q15_drift_rebaseline_backtest.json")
    map_signal = _load_json("data/q15_map_signal_redesign_proof.json")
    alt = _load_json("data/customer_safe_alternative_proof.json")
    pivot = _load_json("data/live_canary_structural_pivot.json")
    no_trade = _load_json("data/no_trade_lane_replay.json")
    worker_outcome = _load_json("data/paper_shadow_outcome_reconciliation.json")

    local_now = now or datetime.now().astimezone()
    updated_at = local_now.strftime("%Y-%m-%d %H:%M %Z")
    pm_freshness_lines = _pm_artifact_freshness_lines(
        {
            "data/live_predict_probe.json": probe,
            "data/live_decision_quality_drilldown.json": drilldown,
            "data/circuit_breaker_audit.json": breaker,
            "data/recent_drift_report.json": drift,
            "data/execution_metadata_smoke.json": execution,
            "data/venue_dry_run_proof.json": venue_dry_run,
            "data/q15_support_audit.json": q15_support,
            "data/q15_support_fill_feasibility.json": fill,
            "data/q15_exact_bucket_row_harvest_proof.json": exact_harvest,
            "data/q15_drift_rebaseline_backtest.json": drift_rebaseline,
            "data/q15_map_signal_redesign_proof.json": map_signal,
            "data/customer_safe_alternative_proof.json": alt,
            "data/live_canary_structural_pivot.json": pivot,
            "data/no_trade_lane_replay.json": no_trade,
            "data/paper_shadow_outcome_reconciliation.json": worker_outcome,
        },
        now=local_now,
    )

    details = probe.get("deployment_blocker_details") if isinstance(probe.get("deployment_blocker_details"), dict) else {}
    progress = _support_progress(probe)
    semantic_progress = progress.get("semantic_signature_progress") if isinstance(progress.get("semantic_signature_progress"), dict) else {}
    semantic_delta = _first_present(
        progress.get("semantic_signature_delta_vs_previous"),
        semantic_progress.get("delta_vs_previous"),
    )
    semantic_stagnant = _first_present(
        progress.get("semantic_signature_stagnant_run_count"),
        semantic_progress.get("stagnant_run_count"),
    )
    semantic_stalled = _first_present(
        progress.get("semantic_signature_stalled_support_accumulation"),
        semantic_progress.get("stalled_support_accumulation"),
    )
    release = breaker.get("release_condition") if isinstance(breaker.get("release_condition"), dict) else {}
    fill_verdict = fill.get("verdict") if isinstance(fill.get("verdict"), dict) else {}
    fill_identity = fill.get("support_identity") if isinstance(fill.get("support_identity"), dict) else {}
    alt_summary = alt.get("summary") if isinstance(alt.get("summary"), dict) else {}
    alt_gate_nested = alt.get("live_deployment_gate") if isinstance(alt.get("live_deployment_gate"), dict) else {}
    alt_gate = {**alt_gate_nested, **alt_summary}
    alt_support_nested = alt.get("current_live_support") if isinstance(alt.get("current_live_support"), dict) else {}
    alt_support = {
        **alt_support_nested,
        "current_rows": _first_present(alt_summary.get("support_rows"), alt_support_nested.get("current_rows")),
        "minimum_support_rows": _first_present(
            alt_summary.get("minimum_support_rows"),
            alt_support_nested.get("minimum_support_rows"),
        ),
        "gap_to_minimum": _first_present(alt_summary.get("support_gap"), alt_support_nested.get("gap_to_minimum")),
        "support_route_verdict": _first_present(
            alt_summary.get("support_route_verdict"),
            alt_support_nested.get("support_route_verdict"),
        ),
        "support_governance_route": _first_present(
            alt_summary.get("support_governance_route"),
            alt_support_nested.get("support_governance_route"),
        ),
        "structure_bucket": _first_present(
            alt_summary.get("current_live_structure_bucket"),
            alt_support_nested.get("structure_bucket"),
        ),
    }
    alt_topk = alt.get("topk_shadow_candidate_context") if isinstance(alt.get("topk_shadow_candidate_context"), dict) else {}
    alt_venue = alt.get("venue_runtime_proof") if isinstance(alt.get("venue_runtime_proof"), dict) else {}
    pivot_truth = pivot.get("current_truth") if isinstance(pivot.get("current_truth"), dict) else {}
    pivot_gate = pivot.get("micro_canary_gate") if isinstance(pivot.get("micro_canary_gate"), dict) else {}
    pivot_decision = pivot.get("structural_decision") if isinstance(pivot.get("structural_decision"), dict) else {}
    pivot_config = pivot.get("operator_config_snapshot_redacted") if isinstance(pivot.get("operator_config_snapshot_redacted"), dict) else {}
    pivot_lane_actionability = pivot_truth.get("current_lane_actionability") or "—"
    pivot_support_evidence_role = pivot_truth.get("support_evidence_role") or "—"
    pivot_operator_interpretation = pivot_truth.get("operator_interpretation") or "—"
    no_trade_decision = no_trade.get("replay_decision") if isinstance(no_trade.get("replay_decision"), dict) else {}
    no_trade_truth = no_trade.get("current_truth") if isinstance(no_trade.get("current_truth"), dict) else {}
    no_trade_checks = no_trade.get("machine_checks") if isinstance(no_trade.get("machine_checks"), dict) else {}
    no_trade_replay = no_trade.get("replay") if isinstance(no_trade.get("replay"), dict) else {}
    no_trade_recent_context = (
        no_trade_replay.get("recent_drift_shadow_context")
        if isinstance(no_trade_replay.get("recent_drift_shadow_context"), dict)
        else {}
    )

    q15_support_route = q15_support.get("support_route") if isinstance(q15_support.get("support_route"), dict) else {}
    q15_support_progress = (
        q15_support_route.get("support_progress")
        if isinstance(q15_support_route.get("support_progress"), dict)
        else {}
    )
    q15_equilibrium = q15_support.get("equilibrium_deadlock")
    if not isinstance(q15_equilibrium, dict):
        q15_equilibrium = q15_support_progress.get("equilibrium_deadlock")
    if not isinstance(q15_equilibrium, dict):
        q15_equilibrium = {}
    q15_forced_artifact = (
        q15_equilibrium.get("forced_research_action_artifact")
        if isinstance(q15_equilibrium.get("forced_research_action_artifact"), dict)
        else {}
    )
    q15_active_repair = (
        q15_support.get("active_repair_plan")
        if isinstance(q15_support.get("active_repair_plan"), dict)
        else {}
    )
    q15_forced_branch = q15_support.get("forced_branch_decision")
    if not isinstance(q15_forced_branch, dict):
        q15_forced_branch = q15_active_repair.get("forced_branch_decision")
    if not isinstance(q15_forced_branch, dict):
        q15_forced_branch = {}

    current_bucket = _first_present(
        probe.get("current_live_structure_bucket"),
        details.get("current_live_structure_bucket"),
        alt_support.get("structure_bucket"),
    )
    rows = _first_present(probe.get("current_live_structure_bucket_rows"), details.get("current_live_structure_bucket_rows"), alt_support.get("current_rows"))
    minimum = _first_present(probe.get("minimum_support_rows"), details.get("minimum_support_rows"), alt_support.get("minimum_support_rows"))
    gap = _first_present(
        probe.get("current_live_structure_bucket_gap_to_minimum"),
        details.get("current_live_structure_bucket_gap_to_minimum"),
        alt_support.get("gap_to_minimum"),
    )
    support_route = _first_present(probe.get("support_route_verdict"), details.get("support_route_verdict"), alt_support.get("support_route_verdict"))
    governance_route = _first_present(probe.get("support_governance_route"), details.get("support_governance_route"), alt_support.get("support_governance_route"))
    support_ready = _support_ready(rows, minimum, gap, support_route)
    support_clause = _support_clause(
        rows=rows,
        minimum=minimum,
        gap=gap,
        support_route=support_route,
        support_ready=support_ready,
    )
    support_handoff_clause = _support_handoff_clause(
        rows=rows,
        minimum=minimum,
        gap=gap,
        support_ready=support_ready,
    )
    governance_route_interpretation = _governance_route_interpretation(
        governance_route,
        support_ready=support_ready,
    )
    release_ready = release.get("release_ready")
    breaker_active = (
        probe.get("deployment_blocker") == "circuit_breaker_active"
        or probe.get("runtime_closure_state") == "circuit_breaker_active"
        or breaker.get("verdict") == "canonical_breaker_active"
        or release_ready is False
    )
    release_wins = release.get("current_recent_window_wins", "—")
    release_window = release.get("recent_window", "—")
    release_required = release.get("required_recent_window_wins", "—")
    release_needed = release.get("additional_recent_window_wins_needed", "—")
    drift_rebaseline_verdict = (
        drift_rebaseline.get("verdict")
        if isinstance(drift_rebaseline.get("verdict"), dict)
        else {}
    )
    exact_harvest_verdict = (
        exact_harvest.get("verdict")
        if isinstance(exact_harvest.get("verdict"), dict)
        else {}
    )
    map_signal_verdict = (
        map_signal.get("verdict")
        if isinstance(map_signal.get("verdict"), dict)
        else {}
    )
    if breaker_active:
        breaker_verdict_line = (
            f"熔斷仍 active（recent `{release_wins}/{release_window}`，"
            f"需要 `{release_required}/{release_window}`，還差 `{release_needed}` 勝），"
            f"且 {support_clause}，"
            "所以 live buy/add 仍 fail-closed"
        )
        breaker_interpretation = (
            "PM interpretation: breaker is currently active; even after it clears, support evidence, Top-K deployability, "
            "and venue runtime proof must all remain verified before live exposure."
        )
    else:
        breaker_verdict_line = (
            f"熔斷已解除，但 {support_clause}，"
            "所以 live buy/add 仍 fail-closed"
        )
        breaker_interpretation = (
            "PM interpretation: breaker math is clear, but any remaining support, Top-K deployability, and venue runtime proof gates still block live exposure."
        )

    matrix_rows = topk.get("rows") if isinstance(topk.get("rows"), list) else []
    topk_freshness = _topk_freshness_fields(topk.get("generated_at"), now=local_now)
    topk_freshness_status = topk_freshness.get("artifact_freshness_status", "unavailable")
    topk_support_context = topk.get("support_context") if isinstance(topk.get("support_context"), dict) else {}
    topk_support_context_refresh = (
        topk_support_context.get("support_context_refresh")
        if isinstance(topk_support_context.get("support_context_refresh"), dict)
        else {}
    )
    topk_live_support_freshness = _topk_live_support_freshness_fields(
        probe.get("generated_at"),
        now=local_now,
    )
    topk_live_support_status = topk_live_support_freshness.get(
        "support_context_freshness_status",
        "unavailable",
    )
    topk_live_support_context_status = (
        "fresh_live_probe_overlay"
        if topk_live_support_status == "fresh"
        else "stale_live_probe_shadow_only"
    )
    topk_live_support_overlay_blocker = (
        topk_support_context.get("live_truth_overlay_blocker")
        or "—"
        if topk_live_support_status == "fresh"
        else topk_live_support_freshness.get("support_context_freshness_reason", "artifact_older_than_policy")
    )
    topk_verdict = (
        "Top-K remains fresh research / paper-shadow evidence. Strategy Lab 可優先顯示 nearest-deployable research rows，但 `deployable_rows=0` means no risk-on live action."
        if topk_freshness_status == "fresh" and topk_live_support_status == "fresh"
        else "Top-K artifact 可維持研究參考，但 live support overlay 目前 stale/reference-only；Strategy Lab / leaderboard 必須標示 shadow-only，刷新 live probe 前不可把候選包裝成 risk-on live action。"
        if topk_freshness_status == "fresh"
        else "Top-K matrix 目前已 stale/reference-only；Strategy Lab / leaderboard 必須標示 stale 或 shadow-only，重跑 matrix 前不可把候選包裝成 risk-on live action。"
    )
    runtime_blocked = _runtime_blocked_rows(topk)
    candidate = _best_topk_candidate(topk)
    worker_artifact = worker_outcome.get("artifact") if isinstance(worker_outcome.get("artifact"), dict) else worker_outcome
    worker_summary = worker_artifact.get("summary") if isinstance(worker_artifact.get("summary"), dict) else {}
    worker_proof = worker_artifact.get("rehearsal_proof") if isinstance(worker_artifact.get("rehearsal_proof"), dict) else {}
    worker_status = worker_artifact.get("status", "no_worker_outcome_artifact")
    worker_proof_status = worker_proof.get("status", "not_available")
    worker_can_poll = worker_proof.get("can_poll_workers")
    worker_next_reconcile_at = worker_proof.get("next_reconcile_at", "—")
    worker_artifact_pending_hours = worker_proof.get("pending_hours_remaining_min", "—")
    worker_current_pending_hours = _hours_until(worker_next_reconcile_at, now=local_now)
    primary_window, primary_summary = _drift_primary(drift)
    venue_rows = execution.get("venues") if isinstance(execution.get("venues"), list) else []
    venue_lines = []
    for venue in venue_rows:
        if not isinstance(venue, dict):
            continue
        venue_lines.append(
            f"- {venue.get('venue', 'unknown')}: adapter_supported={_bool_text(venue.get('adapter_supported'))}, "
            f"enabled_in_config={_bool_text(venue.get('enabled_in_config'))}, "
            f"credentials_configured={_bool_text(venue.get('credentials_configured'))}, "
            f"proof_state={venue.get('proof_state', '—')}, runtime_ready={_bool_text(venue.get('runtime_ready'))}, "
            f"blockers={_safe_join(venue.get('blockers'))}。"
        )
    if not venue_lines:
        venue_lines.append("- 尚無 venue row；視為 runtime_ready=false。")
    venue_dry_run_venues = (
        venue_dry_run.get("venues")
        if isinstance(venue_dry_run.get("venues"), list)
        else []
    )
    venue_dry_run_rows = []
    for venue in venue_dry_run_venues:
        if not isinstance(venue, dict):
            continue
        order_preview = venue.get("order_preview") if isinstance(venue.get("order_preview"), dict) else {}
        venue_dry_run_rows.append(
            f"{venue.get('venue', 'unknown')}: preview={order_preview.get('status', '—')}, "
            f"runtime_ready={_bool_text(venue.get('runtime_ready'))}, "
            f"credentials_configured={_bool_text(venue.get('credentials_configured'))}"
        )
    venue_dry_run_rows_text = "; ".join(venue_dry_run_rows) or "—"

    decision_quality_score = _first_present(
        drilldown.get("decision_quality_score"),
        drilldown.get("score"),
        probe.get("decision_quality_score"),
        default=None,
    )

    text = f"""# PM Status — Poly-Trader Current Delivery State Only

_最後更新：{updated_at}_

> Current-state PM interpretation. Do not append hourly history here; this file is generated from current runtime artifacts by `scripts/sync_pm_status.py` so PM checks fail on real drift, not stale literals.

---

## 1. PM decision

**State：`ORANGE_framework_capture_risk` governance overlay；safe lane remains `YELLOW_shadow_or_paper_usable`；`ORANGE_alternative_solution_required` remains active.**

PM 結論：客戶成功仍是北極星，但 live buy/add safety gate 不可被 customer urgency 推翻。承接上一輪 PM handoff：{support_handoff_clause}、交付 paper/shadow / dry-run / falsification / support-fill proof，且不可降低 live gate。fresh runtime truth 顯示 current-live bucket 是 `{current_bucket}`；PM 決策不變：current exact support 是 `{rows}/{minimum}`、`gap={gap}`、`support_route_verdict={support_route}`，`support_governance_route={governance_route}` {governance_route_interpretation}。pivot lane role 是 `{pivot_lane_actionability}` / `{pivot_support_evidence_role}`：{pivot_operator_interpretation} no-trade replay verdict 是 `{no_trade_decision.get('verdict', '—')}` / `validated={_bool_text(no_trade_decision.get('validated'))}` / `deployable={_bool_text(no_trade_decision.get('deployable'))}` / `buy_add_support_closure_allowed={_bool_text(no_trade_decision.get('buy_add_support_closure_allowed'))}`。

安全答案：`signal={probe.get('signal', '—')}` / `should_trade={_bool_text(probe.get('should_trade'))}` / `deployment_blocker={probe.get('deployment_blocker', '—')}` / `runtime_closure_state={probe.get('runtime_closure_state', '—')}` / `allowed_layers_raw={probe.get('allowed_layers_raw')}` / `allowed_layers={probe.get('allowed_layers')}` / `allowed_layers_reason={probe.get('allowed_layers_reason', '—')}` / `execution_guardrail_reason={probe.get('execution_guardrail_reason', '—')}` / `api_trade_guardrail_active={_bool_text(probe.get('api_trade_guardrail_active'))}` / `api_trade_buy_guardrail={probe.get('api_trade_buy_guardrail', '—')}`。客戶可以使用 Dashboard、Strategy Lab、Execution Console、paper/shadow decision-support、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal；Execution API 只允許 `shadow_buy` / `paper_buy` 以強制 dry-run paper/shadow 模式寫入演練證據，不可繞過 current-live guardrail；**真實買入 / 加倉 / live buy/add / 自動送單 / 小額 live canary 仍不可放行**，除非 bounded live-canary policy、current-live gate、support/breaker gate 與 venue lifecycle proof 全部通過。

---

## 2. Artifact truth accepted by PM

### PM current-artifact freshness guard

{chr(10).join(pm_freshness_lines)}

### Current-live blocker

- `data/live_predict_probe.json` generated at `{probe.get('generated_at', '—')}`；canonical target is `{probe.get('target_col', 'simulated_pyramid_win')}`。
- Runtime signal: `signal={probe.get('signal', '—')}` / `should_trade={_bool_text(probe.get('should_trade'))}` / confidence `{_num_text(probe.get('confidence'), 6)}`；`regime_label={probe.get('regime_label', '—')}` / `regime_gate={probe.get('regime_gate', '—')}` / `entry_quality_label={probe.get('entry_quality_label', '—')}` / `decision_quality_score={_num_text(decision_quality_score)}`。
- Primary blocker: `deployment_blocker={probe.get('deployment_blocker', '—')}` / `runtime_closure_state={probe.get('runtime_closure_state', '—')}`。
- Guardrail truth: `allowed_layers_raw={probe.get('allowed_layers_raw')}` but `allowed_layers={probe.get('allowed_layers')}`；`allowed_layers_reason={probe.get('allowed_layers_reason', '—')}`；`execution_guardrail_reason={probe.get('execution_guardrail_reason', '—')}`。
- Current-live support: `current_live_structure_bucket={current_bucket}`, `support_route_verdict={support_route}`, `support_governance_route={governance_route}`, rows `{rows}/{minimum}`, `gap={gap}`。
- Current-lane role from structural pivot: `current_lane_actionability={pivot_lane_actionability}`, `support_evidence_role={pivot_support_evidence_role}`；{pivot_operator_interpretation}
- Support progress: `support_progress_status={progress.get('status', '—')}` / `regression_basis={progress.get('regression_basis', '—')}` / `previous_rows={progress.get('previous_rows', '—')}` / `delta_vs_previous={progress.get('delta_vs_previous', '—')}` / `stagnant_run_count={progress.get('stagnant_run_count', '—')}` / `semantic_signature_delta_vs_previous={semantic_delta}` / `semantic_signature_stagnant_run_count={semantic_stagnant}` / `semantic_signature_stalled_support_accumulation={_bool_text(semantic_stalled)}` / legacy reference is reference-only because support identity does not close current deployment.
- Direct action truth: `api_trade_guardrail_active={_bool_text(probe.get('api_trade_guardrail_active'))}`; `api_trade_buy_guardrail={probe.get('api_trade_buy_guardrail', '—')}`; live risk-off sides remain `{_safe_join(probe.get('api_trade_allowed_risk_off_sides'))}`；paper/shadow rehearsal sides are `shadow_buy,paper_buy` and must return `dry_run=true`, `live_order_submitted=false`。

**PM verdict：接受「{breaker_verdict_line}」。不可把 legacy rows、exact-live-lane proxy rows、Top-K OOS pass、或單一 support/governance gate 包裝成 deployable。**

### Circuit breaker

- Latest artifact `data/circuit_breaker_audit.json` generated at `{breaker.get('generated_at', '—')}`；verdict `{breaker.get('verdict', '—')}`。
- Release context: `release_ready={_bool_text(release.get('release_ready'))}`, recent-window wins `{release.get('current_recent_window_wins', '—')}/{release.get('recent_window', '—')}`, required wins `{release.get('required_recent_window_wins', '—')}/{release.get('recent_window', '—')}`, `additional_recent_window_wins_needed={release.get('additional_recent_window_wins_needed', '—')}`。
- {breaker_interpretation}

### Research-to-delivery candidates / Top-K

- `data/high_conviction_topk_oos_matrix.json` generated at `{topk.get('generated_at', '—')}`；`artifact_freshness_status={topk_freshness_status}`, `artifact_deployment_blocking={_bool_text(topk_freshness.get('artifact_deployment_blocking'))}`, `artifact_age_minutes={_num_text(topk_freshness.get('artifact_age_minutes'), 2)}`, `artifact_stale_after_minutes={_num_text(topk_freshness.get('artifact_stale_after_minutes'), 1)}`, `samples={topk.get('samples', '—')}`, `row_count={len(matrix_rows)}`, `runtime_blocked_candidate_rows={len(runtime_blocked)}`。
- Top-K live support overlay freshness：`support_context_status={topk_live_support_context_status}`, `support_context_freshness_status={topk_live_support_status}`, `support_context_freshness_reason={topk_live_support_freshness.get('support_context_freshness_reason', '—')}`, `support_context_deployment_blocking={_bool_text(topk_live_support_freshness.get('support_context_deployment_blocking'))}`, `support_context_age_minutes={_num_text(topk_live_support_freshness.get('support_context_age_minutes'), 2)}`, `support_context_stale_after_minutes={_num_text(topk_live_support_freshness.get('support_context_stale_after_minutes'), 1)}`, `support_context_refresh_status={topk_support_context_refresh.get('status', '—')}`, `support_context_refresh_attempted={_bool_text(topk_support_context_refresh.get('attempted'))}`, `support_context_refresh_error={topk_support_context_refresh.get('error', '—')}`, `live_truth_overlay_blocker={topk_live_support_overlay_blocker}`；freshness is recalculated from `data/live_predict_probe.json.generated_at`; if stale, Top-K remains reference-only until refreshed.
- Runtime API overlay：`/api/models/leaderboard` must overlay request-time runtime truth for Strategy Lab, accept Strategy Lab's `?refresh=true` alias as a force-refresh request, auto-queue stale Top-K matrix refresh, refreshes stale live support probe before matrix build, and serialize request-time ML cold-load before background model leaderboard refresh; compact probe fields `hc_support_context_status / hc_support_context_freshness_status / hc_live_truth_freshness_status / hc_support_context_refresh_status / hc_refreshing / hc_refresh_reason` are the current endpoint truth. Fresh runtime overlay can clear persisted-probe staleness, but it does not clear live gates unless support, breaker, model, and venue proof all pass.
- Matrix payload: `deployable_rows={topk.get('deployable_rows', '—')}`, `risk_qualified_rows={topk.get('risk_qualified_rows', alt_topk.get('risk_qualified_rows', '—'))}`, `support_route={topk.get('support_route_verdict', support_route)}`, `deployment_blocker={topk.get('deployment_blocker', probe.get('deployment_blocker', '—'))}`, `current_live_structure_bucket={topk.get('current_live_structure_bucket', current_bucket)}`, bucket rows `{topk.get('current_live_structure_bucket_rows', rows)}/{topk.get('minimum_support_rows', minimum)}`, `gap={topk.get('current_live_structure_bucket_gap_to_minimum', gap)}`。
- Nearest research candidate: `model={candidate.get('model', '—')}`, `feature_profile={candidate.get('feature_profile', '—')}`, `top_k={candidate.get('top_k', '—')}`, `oos_roi={_num_text(candidate.get('oos_roi'))}`, `win_rate={_num_text(candidate.get('win_rate'))}`, `profit_factor={_num_text(candidate.get('profit_factor'))}`, `max_drawdown={_num_text(candidate.get('max_drawdown'))}`, `worst_fold={_num_text(candidate.get('worst_fold'))}`, `trade_count={candidate.get('trade_count', '—')}`, `deployment_candidate_tier={candidate.get('deployment_candidate_tier', '—')}`, `deployable_verdict={candidate.get('deployable_verdict', '—')}`。

**PM verdict：{topk_verdict}**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `{execution.get('generated_at', alt_venue.get('generated_at', '—'))}`。
- Summary: `runtime_ready={_bool_text(execution.get('runtime_ready'))}`, `runtime_ready_count={execution.get('runtime_ready_count', '—')}`, `venues_checked={execution.get('venues_checked', '—')}`, `ok_count={execution.get('ok_count', '—')}`, `readiness_state={execution.get('readiness_state', '—')}`。
{chr(10).join(venue_lines)}
- `data/venue_dry_run_proof.json` generated at `{venue_dry_run.get('generated_at', '—')}`；`venue_dry_run_status={venue_dry_run.get('status', '—')}`, `runtime_ready={_bool_text(venue_dry_run.get('runtime_ready'))}`, `runtime_ready_count={venue_dry_run.get('runtime_ready_count', '—')}`, `venues_checked={venue_dry_run.get('venues_checked', '—')}`, `order_submission_enabled={_bool_text(venue_dry_run.get('order_submission_enabled'))}`, `risk_on_order_enabled={_bool_text(venue_dry_run.get('risk_on_order_enabled'))}`, `dry_run_only={_bool_text(venue_dry_run.get('dry_run_only'))}`。
- Dry-run lifecycle status: `ack={(venue_dry_run.get('ack_simulation') or {}).get('status', '—') if isinstance(venue_dry_run.get('ack_simulation'), dict) else '—'}`, `cancel={(venue_dry_run.get('cancel_simulation') or {}).get('status', '—') if isinstance(venue_dry_run.get('cancel_simulation'), dict) else '—'}`, `fill={(venue_dry_run.get('fill_simulation') or {}).get('status', '—') if isinstance(venue_dry_run.get('fill_simulation'), dict) else '—'}`, `reconciliation={(venue_dry_run.get('reconciliation_check') or {}).get('status', '—') if isinstance(venue_dry_run.get('reconciliation_check'), dict) else '—'}`；venue rows：{venue_dry_run_rows_text}。
- API source-of-truth: `/api/status` exposes `venue_dry_run_proof`, and `/api/execution/overview` prefers that artifact so UI/API/customer-safe proof use the same fail-closed venue lifecycle status.
- API consistency verification: save `/api/status` and `/api/execution/overview` JSON, then run `python scripts/venue_dry_run_api_consistency_probe.py --status-file <status.json> --overview-file <overview.json> --artifact-file data/venue_dry_run_proof.json --strict`; expected `strict_ok=true`, `api_consistent=true`, `artifact_consistent=true`, `fail_closed=true`, and `secret_safe=true`.
- `/api/status.execution_surface_contract.live_canary_policy_gate`, Execution Console readiness gate stack, and Dashboard / Execution Status / Strategy Lab status-only summaries now all expose `live_canary_policy_gate` with operator-safe blocker copy; canary readiness remains false unless mode/live flag/explicit allowed symbol/symbol cap/kill switch all satisfy the local bounded live-canary policy, even if runtime gates later pass.
- Credential-like values stay secret-safe；PM status accepts only boolean/proof-state language and redacts source credentials as `[REDACTED]`。

### Recent market/model risk

- `data/recent_drift_report.json` generated at `{drift.get('generated_at', '—')}`。
- Full sample rows `{((drift.get('full_sample') or {}).get('rows') if isinstance(drift.get('full_sample'), dict) else '—')}`。
- Recent canonical window `{primary_window}`: win_rate `{_pct_text(primary_summary.get('win_rate'))}`, dominant regime `{primary_summary.get('dominant_regime', '—')}({_pct_text(primary_summary.get('dominant_regime_share'))})`, alerts `{_safe_join(primary_summary.get('alerts') or primary_summary.get('alert_flags'))}`。

**PM verdict：recent drift reinforces paper/shadow-only research and root-cause work. It cannot be packaged as a live deployment patch.**

### Support-fill feasibility / alternative-solution pressure

- `data/q15_support_fill_feasibility.json` generated at `{fill.get('generated_at', '—')}`；scanned current support identity bucket is `{fill_identity.get('current_live_structure_bucket', current_bucket)}`。
- Verdict: `classification={fill_verdict.get('classification', '—')}`, current calibration window `{fill_verdict.get('current_calibration_window', fill_identity.get('calibration_window', '—'))}`, current exact bucket rows `{fill_verdict.get('current_exact_bucket_rows', rows)}/{fill_verdict.get('minimum_support_rows', minimum)}`, identity rows before bucket filter `{fill_verdict.get('current_exact_identity_rows', '—')}`, non-current-bucket identity rows `{fill_verdict.get('current_exact_identity_non_bucket_rows', '—')}`, `gap={fill_verdict.get('gap_to_minimum', gap)}`, `time_to_evidence_bucket={fill_verdict.get('time_to_evidence_bucket', '—')}`, `missing_capability_class={fill_verdict.get('missing_capability_class', '—')}`, `alternative_solution_required={_bool_text(fill_verdict.get('alternative_solution_required'))}`。
- Reference-only evidence: `best_reference_window={fill_verdict.get('best_reference_window', '—')}`, `best_reference_exact_bucket_rows={fill_verdict.get('best_reference_exact_bucket_rows', '—')}`, `best_reference_evidence_role={fill_verdict.get('best_reference_evidence_role', '—')}`；reference rows cannot be counted as deployable support unless support identity is deliberately rebaselined and fully reverified.
- Selected next safe artifact: `{fill_verdict.get('selected_next_alternative_artifact', 'data/customer_safe_alternative_proof.json')}`。

### Exact row-harvest proof

- `data/q15_exact_bucket_row_harvest_proof.json` generated at `{exact_harvest.get('generated_at', '—')}`。
- Verdict: `status={exact_harvest_verdict.get('status', '—')}`, current exact rows `{exact_harvest_verdict.get('current_exact_bucket_rows', rows)}/{exact_harvest_verdict.get('minimum_support_rows', minimum)}`, previous rows `{exact_harvest_verdict.get('previous_rows', '—')}`, `delta_vs_previous={exact_harvest_verdict.get('delta_vs_previous', '—')}`, `gap={exact_harvest_verdict.get('gap_to_minimum', gap)}`, `rows_needed={exact_harvest_verdict.get('rows_needed_to_minimum', '—')}`, `time_to_evidence_bucket={exact_harvest_verdict.get('time_to_evidence_bucket', '—')}`, `primary_failed_gate={exact_harvest_verdict.get('primary_failed_gate', '—')}`。
- Safety interpretation: `support_gate_ready={_bool_text(exact_harvest_verdict.get('support_gate_ready'))}`, `live_exposure_allowed={_bool_text(exact_harvest_verdict.get('live_exposure_allowed'))}`, `order_submission_enabled={_bool_text(exact_harvest_verdict.get('order_submission_enabled'))}`；row movement is support evidence only, not live deployment clearance.

### Drift-aware rebaseline backtest

- `data/q15_drift_rebaseline_backtest.json` generated at `{drift_rebaseline.get('generated_at', '—')}`。
- Verdict: `status={drift_rebaseline_verdict.get('status', '—')}`, `decision={drift_rebaseline_verdict.get('decision', '—')}`, `selected_candidate={drift_rebaseline_verdict.get('selected_candidate_id', '—')}`, `selected_candidate_status={drift_rebaseline_verdict.get('selected_candidate_status', '—')}`, current-window rows `{drift_rebaseline_verdict.get('selected_current_window_rows', '—')}/{drift_rebaseline_verdict.get('minimum_support_rows', minimum)}`, all-history rows `{drift_rebaseline_verdict.get('selected_all_history_rows', '—')}`, current exact bucket rows `{drift_rebaseline_verdict.get('current_exact_bucket_rows', rows)}/{drift_rebaseline_verdict.get('minimum_support_rows', minimum)}`, `gap={drift_rebaseline_verdict.get('gap_to_minimum', gap)}`, `primary_failed_gate={drift_rebaseline_verdict.get('primary_failed_gate', '—')}`。
- Safety interpretation: `live_exposure_allowed={_bool_text(drift_rebaseline_verdict.get('live_exposure_allowed'))}`, `order_submission_enabled={_bool_text(drift_rebaseline_verdict.get('order_submission_enabled'))}`；historical or semantic rebaseline candidates are OOS replay/redesign evidence only, not current-live deployment clearance.

### Map/Signal redesign proof

- `data/q15_map_signal_redesign_proof.json` generated at `{map_signal.get('generated_at', '—')}`。
- Verdict: `status={map_signal_verdict.get('status', '—')}`, `decision={map_signal_verdict.get('decision', '—')}`, `selected_candidate={map_signal_verdict.get('selected_candidate_id', '—')}`, `selected_candidate_status={map_signal_verdict.get('selected_candidate_status', '—')}`, `target_bucket={map_signal_verdict.get('selected_target_bucket', '—')}`, current-window rows `{map_signal_verdict.get('selected_current_window_rows', '—')}/{map_signal_verdict.get('minimum_support_rows', minimum)}`, all-history rows `{map_signal_verdict.get('selected_all_history_rows', '—')}`, `best_reference={map_signal_verdict.get('best_reference_candidate_id', '—')}:{map_signal_verdict.get('best_reference_all_history_rows', '—')}`, `primary_failed_gate={map_signal_verdict.get('primary_failed_gate', '—')}`。
- Root-cause link: `root_cause={((map_signal.get('root_cause_context') or {}).get('verdict') if isinstance(map_signal.get('root_cause_context'), dict) else '—')}`, `candidate_patch_type={((map_signal.get('root_cause_context') or {}).get('candidate_patch_type') if isinstance(map_signal.get('root_cause_context'), dict) else '—')}`, `candidate_patch_feature={((map_signal.get('root_cause_context') or {}).get('candidate_patch_feature') if isinstance(map_signal.get('root_cause_context'), dict) else '—')}`。
- Safety interpretation: `live_exposure_allowed={_bool_text(map_signal_verdict.get('live_exposure_allowed'))}`, `order_submission_enabled={_bool_text(map_signal_verdict.get('order_submission_enabled'))}`；neighbor/q35/reference rows are replay/redesign inputs only, not current exact support closure.

### Customer-safe alternative proof

- `data/customer_safe_alternative_proof.json` generated at `{alt.get('generated_at', '—')}`。
- Live gate: `canary_ready={_bool_text(alt_gate.get('canary_ready'))}`, `live_exposure_allowed={_bool_text(alt_gate.get('live_exposure_allowed'))}`, `order_submission_enabled={_bool_text(alt_gate.get('order_submission_enabled'))}`, `risk_on_order_enabled={_bool_text(alt_gate.get('risk_on_order_enabled'))}`, `support_ready={_bool_text(alt_gate.get('support_ready'))}`, `topk_deployable={_bool_text(alt_gate.get('topk_deployable'))}`, `venue_runtime_ready={_bool_text(alt_gate.get('venue_runtime_ready'))}`。
- Allowed today: paper/shadow decision-support, API `shadow_buy` / `paper_buy` dry-run rehearsal, Shadow Trade Ledger, venue dry-run checklist, reduce-only / wait modes. Not allowed: buy/add live exposure, automatic live order submission, canary live order without exact support and runtime venue proof.

### Paper/shadow worker parity

- `/api/execution/workers/poll` is a local-operator controlled state poller for running execution runs; it may write `paper_shadow_worker_poll` only when `execution_runs.state=running`, bundle hash parity passes, and the run does not already have a pending 24h proposal.
- Duplicate poll attempts during the observation window must return `pending_outcome_blocked` without writing another event; proposal payloads remain fail-closed with `order_submission_enabled=false`, `risk_on_order_enabled=false`, `live_order_submitted=false`.
- Current local artifact: `status={worker_status}`, `worker_poll_events={worker_summary.get('worker_poll_events', '—')}`, `pending_outcomes={worker_summary.get('pending_outcomes', '—')}`, `resolved_outcomes={worker_summary.get('resolved_outcomes', '—')}`, `awaiting_label_replay={worker_summary.get('awaiting_label_replay', '—')}`, `live_order_submitted={_bool_text(worker_summary.get('live_order_submitted'))}`。
- Rehearsal proof: `status={worker_proof_status}`, `can_poll_workers={_bool_text(worker_can_poll)}`, `poll_blocked_by_pending_outcome={_bool_text(worker_proof.get('poll_blocked_by_pending_outcome'))}`, `order_submission_enabled={_bool_text(worker_proof.get('order_submission_enabled'))}`, `risk_on_order_enabled={_bool_text(worker_proof.get('risk_on_order_enabled'))}`, `live_order_submitted={_bool_text(worker_proof.get('live_order_submitted'))}`, `next_reconcile_at={worker_next_reconcile_at}`, `current_pending_hours_remaining_hours={worker_current_pending_hours}`, `artifact_pending_hours_remaining_hours={worker_artifact_pending_hours}`；這是 customer-usable rehearsal evidence，不是 live trading readiness。

### Forced-execution / bounded live-canary structural pivot

- `forced-execution` trigger is active when same semantic signature repeats, support `delta_vs_previous=0`, `stagnant_run_count` rises, or the customer flags equilibrium/repetition.
- Forced lanes: **Venue lifecycle proof**, **Model shadow to decision**, **Strategy micro-canary readiness**, **Map-Signal redesign**, or **hard no-go single failed gate**；observation-only status refresh is not accepted.
- Current q15/current-support audit: `data/q15_support_audit.json` generated at `{q15_support.get('generated_at', '—')}`；`scope={((q15_support.get('scope_applicability') or {}).get('status') if isinstance(q15_support.get('scope_applicability'), dict) else '—')}`, `equilibrium_deadlock={q15_equilibrium.get('verdict', '—')}`, `equilibrium_deadlock_confirmed={_bool_text(q15_equilibrium.get('confirmed'))}`, `forced_research_action_required={_bool_text(q15_forced_artifact.get('required'))}`, `forced_branch_status={q15_forced_branch.get('status', '—')}`, `selected_branch={q15_forced_branch.get('selected_branch', '—')}`, `single_failed_gate={q15_forced_branch.get('single_failed_gate', '—')}`, `next_validation_artifact={q15_forced_branch.get('next_validation_artifact', '—')}`, `decision_clock={q15_forced_branch.get('decision_clock', '—')}`, `live_exposure_allowed={_bool_text(q15_forced_branch.get('live_exposure_allowed'))}`, `shadow_or_paper_allowed={_bool_text(q15_forced_branch.get('shadow_or_paper_allowed'))}`。若此列是 `hard_no_go_recorded`，PM 視為本輪已留下 single failed gate artifact，而不是 observation-only refresh。
- Exact row-harvest proof: `data/q15_exact_bucket_row_harvest_proof.json` generated at `{exact_harvest.get('generated_at', '—')}`；`status={exact_harvest_verdict.get('status', '—')}`, `current_rows={exact_harvest_verdict.get('current_exact_bucket_rows', rows)}/{exact_harvest_verdict.get('minimum_support_rows', minimum)}`, `previous_rows={exact_harvest_verdict.get('previous_rows', '—')}`, `delta_vs_previous={exact_harvest_verdict.get('delta_vs_previous', '—')}`, `rows_needed={exact_harvest_verdict.get('rows_needed_to_minimum', '—')}`, `primary_failed_gate={exact_harvest_verdict.get('primary_failed_gate', '—')}`, `live_exposure_allowed={_bool_text(exact_harvest_verdict.get('live_exposure_allowed'))}`；PM treats positive row movement as evidence, not live clearance.
- Drift rebaseline proof: `data/q15_drift_rebaseline_backtest.json` generated at `{drift_rebaseline.get('generated_at', '—')}`；`status={drift_rebaseline_verdict.get('status', '—')}`, `selected_candidate={drift_rebaseline_verdict.get('selected_candidate_id', '—')}`, `current_window_rows={drift_rebaseline_verdict.get('selected_current_window_rows', '—')}/{drift_rebaseline_verdict.get('minimum_support_rows', minimum)}`, `all_history_rows={drift_rebaseline_verdict.get('selected_all_history_rows', '—')}`, `primary_failed_gate={drift_rebaseline_verdict.get('primary_failed_gate', '—')}`, `live_exposure_allowed={_bool_text(drift_rebaseline_verdict.get('live_exposure_allowed'))}`；PM treats this as forced-branch evidence, not live clearance.
- Map/Signal redesign proof: `data/q15_map_signal_redesign_proof.json` generated at `{map_signal.get('generated_at', '—')}`；`status={map_signal_verdict.get('status', '—')}`, `selected_candidate={map_signal_verdict.get('selected_candidate_id', '—')}`, `target_bucket={map_signal_verdict.get('selected_target_bucket', '—')}`, `current_window_rows={map_signal_verdict.get('selected_current_window_rows', '—')}/{map_signal_verdict.get('minimum_support_rows', minimum)}`, `all_history_rows={map_signal_verdict.get('selected_all_history_rows', '—')}`, `best_reference={map_signal_verdict.get('best_reference_candidate_id', '—')}:{map_signal_verdict.get('best_reference_all_history_rows', '—')}`, `primary_failed_gate={map_signal_verdict.get('primary_failed_gate', '—')}`, `live_exposure_allowed={_bool_text(map_signal_verdict.get('live_exposure_allowed'))}`；PM treats this as forced-branch evidence, not live clearance.
- Structural pivot reference: `docs/plans/2026-05-23-live-canary-structural-pivot.md` and `data/live_canary_structural_pivot.json`；implementation guard is `execution.live_canary` in `execution/execution_service.py` with tests `tests/test_execution_service.py -k live_canary`.
- Structural pivot current truth: generated_at `{pivot.get('generated_at', '—')}`；bucket `{pivot_truth.get('structure_bucket', '—')}`；support `{pivot_truth.get('support_rows', '—')}/{pivot_truth.get('minimum_support_rows', '—')}` gap `{pivot_truth.get('support_gap', '—')}`；release_ready `{_bool_text(pivot_truth.get('release_ready'))}`；recent wins `{pivot_truth.get('recent_window_wins', '—')}/{pivot_truth.get('recent_window_size', '—')}`；Top-K deployable `{pivot_truth.get('deployable_rows', '—')}`；venue_runtime_ready `{_bool_text(pivot_truth.get('venue_runtime_ready'))}`；live_canary_policy_ready `{_bool_text(pivot_truth.get('live_canary_policy_ready'))}`。
- Structural pivot Map/Signal lane: `current_lane_actionability={pivot_lane_actionability}` / `support_evidence_role={pivot_support_evidence_role}` / `map_signal_forced_lane={pivot_decision.get('map_signal_forced_lane', '—')}`；next artifact `{pivot_decision.get('map_signal_next_validation_artifact', '—')}`。
- No-trade lane replay: `data/no_trade_lane_replay.json` generated at `{no_trade.get('generated_at', '—')}`；`verdict={no_trade_decision.get('verdict', '—')}` / `validated={_bool_text(no_trade_decision.get('validated'))}` / `deployable={_bool_text(no_trade_decision.get('deployable'))}` / `risk_on_order_enabled={_bool_text(no_trade_decision.get('risk_on_order_enabled'))}` / `order_submission_enabled={_bool_text(no_trade_decision.get('order_submission_enabled'))}` / `buy_add_support_closure_allowed={_bool_text(no_trade_decision.get('buy_add_support_closure_allowed'))}` / `checks_all_passed={_bool_text(no_trade_checks.get('all_passed'))}`；recent replay gate `{no_trade_recent_context.get('best_gate_id', '—')}` stayed shadow-only with kept win rate `{_pct_text(no_trade_recent_context.get('kept_win_rate'))}`。這是 no-trade / reduce-only / paper-shadow proof，不是 live buy/add support closure。
- Structural pivot 72h hard gate: `single_failed_gate_for_72h_decision={pivot_decision.get('single_failed_gate_for_72h_decision', pivot_gate.get('single_failed_gate_for_72h_decision', '—'))}`；`next_validation_artifact={pivot_decision.get('next_validation_artifact', '—')}`；`micro_canary_ready={_bool_text(pivot_gate.get('micro_canary_ready'))}`；`order_submission_enabled={_bool_text(pivot_gate.get('order_submission_enabled'))}`；config mode `{pivot_config.get('execution_mode', '—')}`。
- bounded live-canary policy is required for any live buy/add pilot: `execution.mode=live`, `enable_live_trading=true`, `execution.live_canary.enabled=true`, explicit `allowed_symbols`, symbol-specific `max_base_qty_by_symbol`, and adapter-pre cap enforcement. Missing policy is `live_canary_policy_required`; over-cap is `live_canary_qty_cap_exceeded`.
- **72h decision clock:** either verify a bounded micro-canary under policy after all live gates pass, or name the single failed gate and next artifact. “Continue observing” is forbidden as fallback.

---

## 3. Customer expectation vs PM answer

客戶想「現在就能用產品」，而不是每小時只收到「等」。PM 把這個需求視為產品風險，但不把它等同於 unsafe live trading。

Customer-usable lanes now:
1. **Dashboard**：看 current-live blocker、breaker release context、4H context、decision quality、feature/source blockers；主阻塞是 `{probe.get('deployment_blocker', '—')}`，support 邊界是 `{current_bucket}` `{rows}/{minimum} gap={gap}`。
2. **Strategy Lab**：看 Top-K / leaderboard 研究候選、OOS ROI、win rate、drawdown、profit factor、worst fold 與 runtime-blocked 原因；`deployable_rows={topk.get('deployable_rows', '—')}`、`artifact_freshness_status={topk_freshness_status}`、`support_context_freshness_status={topk_live_support_status}` 時只能作 research / paper-shadow evidence。
3. **Execution Console**：使用 paper/shadow selective sleeve、API `shadow_buy` / `paper_buy` dry-run rehearsal、`/api/execution/workers/poll` worker parity event、worker outcome reconciliation `rehearsal_proof`、Shadow Trade Ledger、dry-run readiness、`live_canary_policy_gate`、等待 / 觀望、減風險；不可做真實買入 / 加倉。
4. **Venue readiness checklist**：追 OKX/Binance 還差哪些 proof；credential 只顯示布林 / proof-state，不洩漏 secret。

---

## 4. framework-capture / alternative-solution / anti-equilibrium guard

本輪維持 **`ORANGE_framework_capture_risk` governance overlay** 與 **`ORANGE_alternative_solution_required`**，不是因為安全 gate 可被推翻，而是避免 PM 被工程 blocker 敘事捕獲。`customer-value delta`：PM status 已承認最新 bucket `{current_bucket}`、exact support `{rows}/{minimum} gap={gap}`、breaker `release_ready={_bool_text(release.get('release_ready'))}` / `{release.get('current_recent_window_wins', '—')}/{release.get('recent_window', '—')}`、Top-K `artifact_freshness_status={topk_freshness_status}` / `support_context_freshness_status={topk_live_support_status}` / `samples={topk.get('samples', '—')}`，並保留 Execution Console / Strategy Lab 的 paper-shadow lane；但 no live exposure。

**time-to-evidence：** `{fill_verdict.get('time_to_evidence_bucket', '—')}` for exact support movement；`same_day` for venue dry-run metadata proof if credentials/config are supplied；`within_week_or_unknown` for true venue lifecycle proof without credentials。PM 不把「治理參考」包裝成 deploy-ready；下輪必須產出 exact-row accumulation proof、missing-capability proof、recent-tail no-new-risk artifact、venue dry-run proof，或一個可驗證的 alternative-solution artifact。

**anti-equilibrium guard：** `anti-repeat` 結果是不能再只重複 support gap；若 same semantic signature + support `delta_vs_previous=0` 再出現，PM 必須轉入 `forced-execution`：Venue lifecycle proof、Model shadow to decision、Strategy micro-canary readiness、Map-Signal redesign、或 hard no-go single failed gate。`cost-of-delay` 是客戶信心、策略可用性與工程焦點繼續被單一路徑消耗；`hypothesis inversion` 是若 exact support 無法累積，最快會由 support stagnation counter、recent drift no-new-risk replay、與 venue dry-run proof 暴露；`option portfolio`：60% 主路徑追 exact support + source/data proof，20% 鄰近安全交付推 paper/shadow decision-support，20% 真替代評估縮小策略/市場範圍、外部資料/工具、manual workflow、替代模型/架構或 stop/pivot；`red-team PM` 挑戰：若下輪沒有客戶可見位移，就要求替代解法 artifact 或 bounded live-canary 72h hard gate，而不是改寫等待文案。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Exact current support lane**：刷新 live probe / support audit / support-fill feasibility，直接顯示 current exact bucket rows 是否從 `{rows}/{minimum}` 開始 movement，並同時列出 identity rows / non-current-bucket rows，避免把 near-lane/proxy/reference rows 誤包成 deployable；若 `delta_vs_previous=0` 或 `stagnant_run_count` 持續增加，必須說明缺的是 Map / Tool / Signal / Constraint / Review 哪一類能力。
2. **Recent tail root-cause lane**：針對 recent canonical pocket（window `{primary_window}` win_rate `{_pct_text(primary_summary.get('win_rate'))}`）交付一個 no-new-risk / shadow-only falsification artifact；不可把 shadow-only artifact 誤寫成 release patch。
3. **Top-K freshness lane**：維持 `data/high_conviction_topk_oos_matrix.json` 與 live support overlay 在 freshness target 內，或讓 `/api/models/leaderboard` / Strategy Lab 明確標示 stale/reference-only。
4. **Customer-usable lane**：用 route/API/test/browser proof 證明 `/execution` paper/shadow selective sleeve、worker parity event、worker outcome reconciliation `rehearsal_proof`、pending poll guard / ETA、Shadow Trade Ledger、range-chop playbook、dry-run readiness 或 `live_canary_policy_gate` 可操作。
5. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
6. **PM drift harness lane**：維持 `scripts/pm_heartbeat_check.py` 以 current runtime artifacts 驗證 `docs/pm/pm-status.md`，避免 stale literals 誤通過。
7. **alternative-solution lane**：至少列三個 alternative-solution，並選一個可於下輪驗證的 artifact；安全 gate 不可放鬆，但產品路線不可被單一路徑綁死。
8. **forced-execution lane**：若 same semantic signature / support delta=0 再重複，必須選 Venue lifecycle proof、Model shadow to decision、Strategy micro-canary readiness、Map-Signal redesign 或 hard no-go single failed gate；任何 live buy/add 都必須先通過 bounded live-canary policy 與 adapter-pre cap enforcement。

---

## 6. Next-hour gate

**Next-hour gate / Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據。最低可接受證據是：current exact support rows 從目前 `{rows}/{minimum}` 開始 movement 或明確證明 stagnation 的 missing capability；`data/no_trade_lane_replay.json` clearly labels `deployable=false` / `buy_add_support_closure_allowed=false` while validating abstain / reduce-only / paper-shadow behavior；Top-K matrix 與 live support overlay 保持 fresh，或明確標示 stale/reference-only；`/execution` paper/shadow worker parity event 可操作，且 outcome reconciliation 的 `rehearsal_proof.status=pending_observation_window` 於 pending 期間禁止重複 poll 並顯示 ETA，24h 後轉成 resolved 或 label replay；venue dry-run proof；或 forced-execution lane 的 72h bounded live-canary / single failed gate artifact。除此之外，PM 必須交付 time-to-evidence bucket 與 `alternative-solution` 候選。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 維持 `ORANGE_framework_capture_risk` 並升級 `ORANGE_alternative_solution_required`；若 same semantic signature + support delta=0 重複卻沒有 forced-execution lane，升級 `RED_forced_execution_required`；若連續三次沒有 artifact movement、safe product proof 或替代解法驗證，升級為 `RED_delivery_deadlock`。
"""
    return _redact(text).rstrip() + "\n"


def sync_pm_status() -> Path:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(build_pm_status_markdown(), encoding="utf-8")
    return STATUS_PATH


def main() -> int:
    path = sync_pm_status()
    print(f"PM status synced: {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
