#!/usr/bin/env python3
"""Build a PM-safe customer alternative proof without loosening live gates.

This artifact is intentionally not a live-readiness certificate.  It merges the
current exact-support blocker, Top-K shadow candidates, support-fill feasibility,
venue metadata proof, and recent no-new-risk falsification into one operator/PM
proof that says what can be used today (paper/shadow + reduce-only) and what
remains forbidden (buy/add/order submission) while support/venue gates are open.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DOCS_ANALYSIS_DIR = PROJECT_ROOT / "docs" / "analysis"
DEFAULT_JSON_OUT = DATA_DIR / "customer_safe_alternative_proof.json"
DEFAULT_MARKDOWN_OUT = DOCS_ANALYSIS_DIR / "customer_safe_alternative_proof.md"


SOURCE_PATHS = {
    "live_predict_probe": DATA_DIR / "live_predict_probe.json",
    "circuit_breaker_audit": DATA_DIR / "circuit_breaker_audit.json",
    "q15_support_fill_feasibility": DATA_DIR / "q15_support_fill_feasibility.json",
    "high_conviction_topk_oos_matrix": DATA_DIR / "high_conviction_topk_oos_matrix.json",
    "execution_metadata_smoke": DATA_DIR / "execution_metadata_smoke.json",
    "recent_drift_report": DATA_DIR / "recent_drift_report.json",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _to_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "ready", "passed"}
    return bool(value)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return default


def _source_meta(payloads: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for name, path in SOURCE_PATHS.items():
        payload = payloads.get(name) or {}
        meta[name] = {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "exists": path.exists(),
            "generated_at": payload.get("generated_at") or payload.get("artifact_freshness_checked_at"),
        }
    return meta


def _value_if_present(mapping: Mapping[str, Any], key: str) -> tuple[bool, Any]:
    """Return whether a key is present, preserving explicit JSON null values."""
    if key in mapping:
        return True, mapping.get(key)
    return False, None


def _support_context(live_probe: Mapping[str, Any], support_fill: Mapping[str, Any], topk: Mapping[str, Any]) -> dict[str, Any]:
    verdict = support_fill.get("verdict") if isinstance(support_fill.get("verdict"), dict) else {}
    support_ctx = topk.get("support_context") if isinstance(topk.get("support_context"), dict) else {}
    details = live_probe.get("deployment_blocker_details") if isinstance(live_probe.get("deployment_blocker_details"), dict) else {}

    rows = _to_int(
        _first_present(
            live_probe.get("current_live_structure_bucket_rows"),
            details.get("current_live_structure_bucket_rows"),
            support_ctx.get("current_live_structure_bucket_rows"),
            verdict.get("current_exact_bucket_rows"),
        )
    )
    minimum = _to_int(
        _first_present(
            live_probe.get("minimum_support_rows"),
            details.get("minimum_support_rows"),
            support_ctx.get("minimum_support_rows"),
            verdict.get("minimum_support_rows"),
            50,
        ),
        default=50,
    )
    gap = _to_int(
        _first_present(
            live_probe.get("current_live_structure_bucket_gap_to_minimum"),
            details.get("current_live_structure_bucket_gap_to_minimum"),
            support_ctx.get("current_live_structure_bucket_gap_to_minimum"),
            support_ctx.get("gap_to_minimum"),
            verdict.get("gap_to_minimum"),
            max(minimum - rows, 0),
        )
    )
    support_route_verdict = _first_present(
        live_probe.get("support_route_verdict"),
        details.get("support_route_verdict"),
        support_ctx.get("support_route_verdict"),
        verdict.get("q15_support_route_verdict"),
        "exact_bucket_unsupported_block",
    )
    deployable = bool(
        _as_bool(_first_present(support_ctx.get("support_route_deployable"), details.get("support_route_deployable"), support_route_verdict == "exact_bucket_supported"))
        and rows >= minimum
        and gap == 0
    )
    live_blocker_present, live_blocker = _value_if_present(live_probe, "deployment_blocker")
    support_blocker_present, support_blocker = _value_if_present(support_ctx, "deployment_blocker")
    if live_blocker_present:
        deployment_blocker = live_blocker
    elif support_blocker_present:
        deployment_blocker = support_blocker
    elif deployable:
        deployment_blocker = None
    else:
        deployment_blocker = "unsupported_exact_live_structure_bucket"
    return {
        "deployment_blocker": deployment_blocker,
        "structure_bucket": _first_present(
            live_probe.get("current_live_structure_bucket"),
            support_ctx.get("current_live_structure_bucket"),
            verdict.get("current_live_structure_bucket"),
            (support_fill.get("support_identity") or {}).get("current_live_structure_bucket") if isinstance(support_fill.get("support_identity"), dict) else None,
            "—",
        ),
        "support_route_verdict": support_route_verdict,
        "support_governance_route": _first_present(
            live_probe.get("support_governance_route"),
            details.get("support_governance_route"),
            support_ctx.get("support_governance_route"),
            verdict.get("q15_support_governance_route"),
            "—",
        ),
        "current_rows": rows,
        "minimum_support_rows": minimum,
        "gap_to_minimum": gap,
        "support_route_deployable": deployable,
        "reference_only_rows": _to_int(
            _first_present(
                (support_ctx.get("support_governance_reference_evidence") or {}).get("exact_live_lane_proxy_rows")
                if isinstance(support_ctx.get("support_governance_reference_evidence"), dict)
                else None,
                0,
            )
        ),
        "operator_summary": (
            f"目前 current-live 精準支持 {rows}/{minimum}，缺口 {gap}；"
            "reference/proxy/OOS evidence 只能作影子觀察或治理參考，不能關閉部署 gate。"
        ),
    }


def _breaker_context(live_probe: Mapping[str, Any], circuit_breaker_audit: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Normalize circuit-breaker release math as a first-class live gate.

    Support, model, and venue gates are necessary, but PM/engineering handoff
    treats an active circuit breaker as the immediate live-exposure blocker.
    Preserve explicit zeros and booleans from the probe; when no breaker release
    context is present, default to ready so legacy all-gates fixtures do not get
    blocked by absent data.
    """

    circuit_breaker_audit = circuit_breaker_audit or {}
    details = live_probe.get("deployment_blocker_details") if isinstance(live_probe.get("deployment_blocker_details"), dict) else {}
    release = details.get("release_condition") if isinstance(details.get("release_condition"), dict) else {}
    if not release and isinstance(live_probe.get("release_condition"), dict):
        release = live_probe.get("release_condition") or {}
    if not release and isinstance(circuit_breaker_audit.get("release_condition"), dict):
        release = circuit_breaker_audit.get("release_condition") or {}
    if not release and isinstance(circuit_breaker_audit.get("canonical_scope"), dict):
        canonical_scope = circuit_breaker_audit.get("canonical_scope") or {}
        release = {
            key: canonical_scope.get(key)
            for key in (
                "release_ready",
                "recent_window",
                "current_recent_window_wins",
                "required_recent_window_wins",
                "additional_recent_window_wins_needed",
            )
            if key in canonical_scope
        }

    deployment_blocker = live_probe.get("deployment_blocker")
    runtime_closure_state = live_probe.get("runtime_closure_state")
    blocker_active = deployment_blocker == "circuit_breaker_active" or runtime_closure_state == "circuit_breaker_active"

    explicit_release_ready = release.get("release_ready") if "release_ready" in release else None
    additional_wins_needed = _first_present(release.get("additional_recent_window_wins_needed"), default=None)
    current_wins = _first_present(release.get("current_recent_window_wins"), default=None)
    required_wins = _first_present(release.get("required_recent_window_wins"), default=None)
    if explicit_release_ready is None and current_wins is not None and required_wins is not None:
        explicit_release_ready = _to_int(current_wins) >= _to_int(required_wins)
    if explicit_release_ready is None and additional_wins_needed is not None:
        explicit_release_ready = _to_int(additional_wins_needed) == 0

    release_ready = bool(explicit_release_ready) if explicit_release_ready is not None else not blocker_active
    if blocker_active:
        release_ready = bool(explicit_release_ready) if explicit_release_ready is not None else False

    return {
        "deployment_blocker": deployment_blocker,
        "runtime_closure_state": runtime_closure_state,
        "release_ready": release_ready,
        "recent_window": _to_int(_first_present(release.get("recent_window"), 50), default=50),
        "current_recent_window_wins": None if current_wins is None else _to_int(current_wins),
        "required_recent_window_wins": None if required_wins is None else _to_int(required_wins),
        "additional_recent_window_wins_needed": None
        if additional_wins_needed is None
        else _to_int(additional_wins_needed),
        "operator_summary": (
            "熔斷 gate 已解除；仍需 exact support、Top-K 與 venue runtime proof 全部通過。"
            if release_ready
            else "熔斷 gate 尚未解除；最近窗勝場未達門檻前，live buy/add/order submission 必須 fail-closed。"
        ),
    }


def _topk_context(topk: Mapping[str, Any]) -> dict[str, Any]:
    risk_qualified = _to_int(_first_present(topk.get("risk_qualified_rows"), topk.get("risk_qualified_count")))
    runtime_blocked = _to_int(
        _first_present(topk.get("runtime_blocked_candidate_rows"), topk.get("runtime_blocked_candidate_count"))
    )
    deployable = _to_int(_first_present(topk.get("deployable_rows"), topk.get("deployable_count")))
    nearest_rows = _as_list(topk.get("nearest_deployable_rows"))
    nearest = nearest_rows[0] if nearest_rows and isinstance(nearest_rows[0], dict) else {}
    return {
        "artifact_freshness_status": topk.get("artifact_freshness_status"),
        "artifact_deployment_blocking": _as_bool(topk.get("artifact_deployment_blocking")),
        "risk_qualified_rows": risk_qualified,
        "runtime_blocked_candidate_rows": runtime_blocked,
        "deployable_rows": deployable,
        "paper_shadow_available": bool(risk_qualified > 0 and runtime_blocked > 0 and deployable == 0),
        "nearest_candidate": {
            "model": _first_present(nearest.get("model"), nearest.get("model_name")),
            "feature_profile": nearest.get("feature_profile"),
            "regime": nearest.get("regime"),
            "top_k": _first_present(nearest.get("top_k"), nearest.get("threshold_name")),
            "win_rate": nearest.get("win_rate"),
            "oos_roi": nearest.get("oos_roi"),
            "profit_factor": nearest.get("profit_factor"),
            "max_drawdown": nearest.get("max_drawdown"),
            "worst_fold": nearest.get("worst_fold"),
            "trade_count": nearest.get("trade_count"),
            "deployment_candidate_tier": nearest.get("deployment_candidate_tier"),
            "oos_gate_passed": nearest.get("oos_gate_passed"),
            "blocked_only_by_live_guardrails": nearest.get("blocked_only_by_live_guardrails"),
            "gate_failures": [str(item) for item in _as_list(nearest.get("gate_failures"))],
            "live_gate_failures": [str(item) for item in _as_list(nearest.get("live_gate_failures"))],
            "support_route": nearest.get("support_route"),
            "support_governance_route": nearest.get("support_governance_route"),
            "support_route_deployable": nearest.get("support_route_deployable"),
            "deployment_blocker": nearest.get("deployment_blocker"),
            "runtime_closure_state": nearest.get("runtime_closure_state"),
            "current_live_structure_bucket": nearest.get("current_live_structure_bucket"),
            "current_live_structure_bucket_rows": nearest.get("current_live_structure_bucket_rows"),
            "minimum_support_rows": nearest.get("minimum_support_rows"),
            "current_live_structure_bucket_gap_to_minimum": nearest.get("current_live_structure_bucket_gap_to_minimum"),
            "release_ready": nearest.get("release_ready"),
            "current_recent_window_wins": nearest.get("current_recent_window_wins"),
            "required_recent_window_wins": nearest.get("required_recent_window_wins"),
            "additional_recent_window_wins_needed": nearest.get("additional_recent_window_wins_needed"),
            "verdict": _first_present(nearest.get("deployable_verdict"), nearest.get("verdict")),
        },
    }


def _venue_context(execution_smoke: Mapping[str, Any]) -> dict[str, Any]:
    venues = []
    for row in _as_list(execution_smoke.get("venues")):
        if not isinstance(row, dict):
            continue
        venues.append(
            {
                "venue": row.get("venue"),
                "adapter_supported": _as_bool(row.get("adapter_supported")),
                "enabled_in_config": _as_bool(row.get("enabled_in_config")),
                "credentials_configured": _as_bool(row.get("credentials_configured")),
                "proof_state": row.get("proof_state"),
                "runtime_ready": _as_bool(row.get("runtime_ready")),
                "blockers": [str(item) for item in _as_list(row.get("blockers"))],
                "operator_next_action": row.get("operator_next_action"),
                "verify_next": row.get("verify_next"),
            }
        )
    runtime_ready = _as_bool(execution_smoke.get("runtime_ready")) and bool(venues) and all(v["runtime_ready"] for v in venues)
    return {
        "runtime_ready": runtime_ready,
        "readiness_state": execution_smoke.get("readiness_state") or "blocked_until_runtime_lifecycle_proof",
        "runtime_ready_count": _to_int(execution_smoke.get("runtime_ready_count")),
        "runtime_ready_blockers": [str(item) for item in _as_list(execution_smoke.get("runtime_ready_blockers"))],
        "venues": venues,
    }


def _recent_context(recent_drift: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize recent-tail no-new-risk proof from current and legacy shapes.

    `recent_drift_report.py` writes the shadow replay under
    `canonical_tail_root_cause.no_new_risk_shadow_replay`.  Older tests and
    hand-authored payloads may still put it at top level.  Preserve explicit
    false/zero values and never promote the replay to deployability.
    """

    root_cause = (
        recent_drift.get("canonical_tail_root_cause")
        if isinstance(recent_drift.get("canonical_tail_root_cause"), dict)
        else {}
    )
    replay = recent_drift.get("no_new_risk_shadow_replay")
    if not isinstance(replay, dict):
        replay = root_cause.get("no_new_risk_shadow_replay")
    if not isinstance(replay, dict):
        replay = {}

    primary = recent_drift.get("primary_summary")
    if not isinstance(primary, dict):
        primary_window = recent_drift.get("primary_window")
        if isinstance(primary_window, dict):
            nested_summary = primary_window.get("summary")
            if isinstance(nested_summary, dict):
                # recent_drift_report.py writes the operator-facing facts under
                # primary_window.summary, while primary_window itself carries the
                # window id / alerts.  Merge them so latest-window fields do not
                # fall back to canonical_tail_root_cause.dominant_loss_regime and
                # mislabel the customer-safe proof.
                primary = {
                    **nested_summary,
                    "window": _first_present(primary_window.get("window"), nested_summary.get("window")),
                    "alerts": _first_present(primary_window.get("alerts"), nested_summary.get("alerts")),
                }
            else:
                primary = primary_window
    if not isinstance(primary, dict):
        primary = root_cause.get("primary_summary")
    if not isinstance(primary, dict):
        primary = {}

    baseline = replay.get("baseline") if isinstance(replay.get("baseline"), dict) else {}
    best_gate = replay.get("best_gate") if isinstance(replay.get("best_gate"), dict) else {}
    gate_summary = best_gate.get("summary") if isinstance(best_gate.get("summary"), dict) else {}
    operator_message = (
        replay.get("operator_message")
        or replay.get("operator")
        or gate_summary.get("operator_message")
        or replay.get("deployment_verdict")
    )

    return {
        "latest_window": _first_present(
            recent_drift.get("latest_window"),
            recent_drift.get("primary_window_name"),
            primary.get("window"),
            baseline.get("rows"),
        ),
        "win_rate": _first_present(primary.get("win_rate"), baseline.get("win_rate")),
        "dominant_regime": _first_present(primary.get("dominant_regime"), root_cause.get("dominant_loss_regime")),
        "alerts": recent_drift.get("primary_alerts") or primary.get("alerts") or [],
        "shadow_falsification_mode": replay.get("mode"),
        "shadow_falsification_deployable": _as_bool(replay.get("deployable")),
        "shadow_falsification_order_submission_enabled": _as_bool(replay.get("order_submission_enabled")),
        "shadow_falsification_summary": operator_message,
        "shadow_falsification_best_gate": _first_present(best_gate.get("id"), gate_summary.get("id")),
        "shadow_falsification_kept_rows": _first_present(best_gate.get("kept_rows"), gate_summary.get("kept_rows")),
        "shadow_falsification_kept_win_rate": _first_present(best_gate.get("kept_win_rate"), gate_summary.get("kept_win_rate")),
        "shadow_falsification_loss_capture_share": _first_present(
            best_gate.get("loss_capture_share"),
            gate_summary.get("loss_capture_share"),
        ),
    }


def _alternative_solution_portfolio(
    support_fill: Mapping[str, Any],
    support: Mapping[str, Any],
    topk: Mapping[str, Any],
    venue: Mapping[str, Any],
    recent: Mapping[str, Any],
) -> dict[str, Any]:
    """Expose PM's option portfolio as a machine-readable, fail-closed artifact."""

    verdict = support_fill.get("verdict") if isinstance(support_fill.get("verdict"), dict) else {}
    raw_options = verdict.get("alternative_solutions") if isinstance(verdict.get("alternative_solutions"), list) else []
    if not raw_options:
        raw_options = [
            {
                "id": "paper_shadow_decision_support_sleeve",
                "role": "customer_usable_now",
                "next_artifact": "data/customer_safe_alternative_proof.json + Execution Console / Strategy Lab paper-shadow proof with deployable=false copy",
                "live_exposure_allowed": False,
            },
            {
                "id": "semantic_rebaseline_review",
                "role": "support_policy_alternative",
                "next_artifact": "OOS + Top-K + support audit replay under any proposed new calibration_window identity",
                "live_exposure_allowed": False,
            },
            {
                "id": "venue_dry_run_readiness_proof",
                "role": "delivery_risk_reduction",
                "next_artifact": "OKX/Binance dry-run lifecycle proof checklist with credential state as boolean only",
                "live_exposure_allowed": False,
            },
        ]

    normalized_options: list[dict[str, Any]] = []
    for option in raw_options:
        if not isinstance(option, dict):
            continue
        normalized_options.append(
            {
                "id": str(option.get("id") or "unnamed_alternative"),
                "role": str(option.get("role") or "alternative_solution"),
                "next_artifact": str(option.get("next_artifact") or "—"),
                "live_exposure_allowed": False,
                "deployable": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "reference_window": option.get("reference_window"),
                "reference_rows": option.get("reference_rows"),
            }
        )

    selected_option = normalized_options[0]["id"] if normalized_options else "paper_shadow_decision_support_sleeve"
    return {
        "pm_challenge_answered": True,
        "option_count": len(normalized_options),
        "selected_option": selected_option,
        "time_to_evidence_bucket": verdict.get("time_to_evidence_bucket"),
        "missing_capability_class": verdict.get("missing_capability_class"),
        "selected_next_artifact": verdict.get("selected_next_alternative_artifact")
        or "data/customer_safe_alternative_proof.json",
        "options": normalized_options,
        "safety_invariant": (
            "All alternatives are customer-safe only: deployable=false, live_exposure_allowed=false, "
            "order_submission_enabled=false until exact support, Top-K deployability, and venue runtime proof all pass."
        ),
        "evidence_summary": {
            "support_rows": support.get("current_rows"),
            "minimum_support_rows": support.get("minimum_support_rows"),
            "support_gap": support.get("gap_to_minimum"),
            "topk_risk_qualified_rows": topk.get("risk_qualified_rows"),
            "topk_deployable_rows": topk.get("deployable_rows"),
            "venue_runtime_ready": venue.get("runtime_ready"),
            "recent_shadow_mode": recent.get("shadow_falsification_mode"),
        },
    }


def build_customer_safe_alternative_proof(
    *,
    live_predict_probe: Mapping[str, Any] | None = None,
    circuit_breaker_audit: Mapping[str, Any] | None = None,
    q15_support_fill_feasibility: Mapping[str, Any] | None = None,
    high_conviction_topk_oos_matrix: Mapping[str, Any] | None = None,
    execution_metadata_smoke: Mapping[str, Any] | None = None,
    recent_drift_report: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    live_probe = dict(live_predict_probe or {})
    breaker_audit = dict(circuit_breaker_audit or {})
    support_fill = dict(q15_support_fill_feasibility or {})
    topk = dict(high_conviction_topk_oos_matrix or {})
    execution_smoke = dict(execution_metadata_smoke or {})
    recent_drift = dict(recent_drift_report or {})

    support = _support_context(live_probe, support_fill, topk)
    breaker = _breaker_context(live_probe, breaker_audit)
    topk_ctx = _topk_context(topk)
    venue = _venue_context(execution_smoke)
    recent = _recent_context(recent_drift)
    verdict = support_fill.get("verdict") if isinstance(support_fill.get("verdict"), dict) else {}

    breaker_ready = bool(breaker["release_ready"])
    support_ready = bool(support["support_route_deployable"] and support["current_rows"] >= support["minimum_support_rows"] and support["gap_to_minimum"] == 0)
    topk_deployable = topk_ctx["deployable_rows"] > 0
    venue_ready = bool(venue["runtime_ready"])
    live_exposure_allowed = bool(breaker_ready and support_ready and topk_deployable and venue_ready)
    order_submission_enabled = live_exposure_allowed
    canary_ready = live_exposure_allowed
    blocking_gates: list[str] = []
    if not breaker_ready:
        blocking_gates.append("circuit_breaker_gate")
    if not support_ready:
        blocking_gates.append("current_live_support_gate")
    if not topk_deployable:
        blocking_gates.append("model_gate")
    if not venue_ready:
        blocking_gates.append("venue_gate")
    primary_blocking_gate = blocking_gates[0] if blocking_gates else "none"

    customer_safe_lanes = [
        {
            "id": "paper_shadow_decision_support_sleeve",
            "role": "customer_usable_now",
            "status": "available" if topk_ctx["paper_shadow_available"] or verdict.get("shadow_or_paper_allowed") else "blocked_waiting_candidate",
            "deployable": False,
            "live_exposure_allowed": False,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "evidence": {
                "risk_qualified_rows": topk_ctx["risk_qualified_rows"],
                "runtime_blocked_candidate_rows": topk_ctx["runtime_blocked_candidate_rows"],
                "deployable_rows": topk_ctx["deployable_rows"],
                "support_rows": support["current_rows"],
                "support_minimum": support["minimum_support_rows"],
                "support_gap": support["gap_to_minimum"],
            },
            "operator_message": "可用作客戶決策支援 / 影子觀察：記錄訊號、假想 entry、24h outcome；不送單、不加倉。",
        },
        {
            "id": "venue_dry_run_readiness_proof",
            "role": "delivery_risk_reduction",
            "status": "ready" if venue_ready else "blocked_missing_runtime_backed_proof",
            "deployable": False,
            "live_exposure_allowed": False,
            "order_submission_enabled": False,
            "credential_values_redacted": True,
            "venues": venue["venues"],
            "operator_message": "場館證據鏈只能顯示 adapter / enabled / credential boolean 與 lifecycle blocker；不可輸出 credential 值。",
        },
        {
            "id": "support_fill_feasibility",
            "role": "proof_path_or_falsification",
            "status": verdict.get("classification") or "unknown_support_feasibility",
            "deployable": False,
            "live_exposure_allowed": False,
            "current_rows": support["current_rows"],
            "minimum_support_rows": support["minimum_support_rows"],
            "gap_to_minimum": support["gap_to_minimum"],
            "time_to_evidence_bucket": verdict.get("time_to_evidence_bucket"),
            "missing_capability_class": verdict.get("missing_capability_class"),
            "alternative_solution_required": bool(verdict.get("alternative_solution_required", True)),
        },
        {
            "id": "recent_window_no_new_risk_falsification",
            "role": "research_delivery_without_new_risk",
            "status": recent.get("shadow_falsification_mode") or "not_available",
            "deployable": False,
            "live_exposure_allowed": False,
            "order_submission_enabled": False,
            "latest_window": recent.get("latest_window"),
            "win_rate": recent.get("win_rate"),
            "dominant_regime": recent.get("dominant_regime"),
            "alerts": recent.get("alerts"),
            "operator_message": recent.get("shadow_falsification_summary") or "只允許 no-new-risk paper/shadow falsification。",
        },
    ]

    alternative_portfolio = _alternative_solution_portfolio(support_fill, support, topk_ctx, venue, recent)
    pm_handoff_decision = (
        "承接 PM handoff：不降低 live gate；fresh runtime 已證明 current exact support 達標，"
        "本輪轉往 Top-K/model gate 與 venue runtime proof，同時維持 paper/shadow、dry-run、falsification proof。"
        if support_ready
        else "維持 current-live exact-support blocker；若 exact rows 仍不足，交付 paper/shadow、dry-run、falsification 與 support-fill proof，不降低 live gate。"
    )
    next_gate = (
        "current exact support 已達標；Top-K deployable_rows>0、venue runtime lifecycle proof complete，"
        "且 circuit_breaker release_ready=true 後，才可考慮 live exposure。"
        if support_ready
        else f"circuit_breaker release_ready={breaker_ready}，current exact support rows {support['current_rows']}/{support['minimum_support_rows']} 必須補齊；"
        "同時 Top-K deployable_rows>0、venue runtime lifecycle proof complete，才允許最小 canary review。"
    )

    payloads = {
        "live_predict_probe": live_probe,
        "circuit_breaker_audit": breaker_audit,
        "q15_support_fill_feasibility": support_fill,
        "high_conviction_topk_oos_matrix": topk,
        "execution_metadata_smoke": execution_smoke,
        "recent_drift_report": recent_drift,
    }

    return {
        "generated_at": generated_at or _now_iso(),
        "artifact": "customer_safe_alternative_proof",
        "source_artifacts": _source_meta(payloads),
        "pm_handoff_carried_forward": {
            "decision": pm_handoff_decision,
            "current_live_blocker": support["deployment_blocker"],
            "selected_customer_safe_lane": "paper_shadow_decision_support_sleeve",
            "forbidden_shortcut": "不可降低 live-trading 門檻、不可把 proxy/reference/OOS/shadow 包裝成 live deployability。",
        },
        "live_deployment_gate": {
            "canary_ready": canary_ready,
            "live_exposure_allowed": live_exposure_allowed,
            "order_submission_enabled": order_submission_enabled,
            "risk_on_order_enabled": live_exposure_allowed,
            "support_ready": support_ready,
            "topk_deployable": topk_deployable,
            "venue_runtime_ready": venue_ready,
            "circuit_breaker_ready": breaker_ready,
            "breaker_release_ready": breaker_ready,
            "blocking_gate": primary_blocking_gate,
            "primary_blocking_gate": primary_blocking_gate,
            "blocking_gates": blocking_gates,
            "operator_summary": "可進 canary" if canary_ready else "目前只允許 customer-safe paper/shadow 與 reduce-only；買入 / 加倉 / 自動下單維持 fail-closed。",
        },
        "circuit_breaker_gate": breaker,
        "current_live_support": support,
        "topk_shadow_candidate_context": topk_ctx,
        "venue_runtime_proof": venue,
        "recent_window_context": recent,
        "alternative_solution_portfolio": alternative_portfolio,
        "customer_safe_lanes": customer_safe_lanes,
        "allowed_today": [
            "啟動 paper-shadow 訊號帳本並追蹤 24h pyramid outcome",
            "展示 Strategy Lab / Execution Console 的高信心 OOS 候選，但標示 deployable=false",
            "做 venue dry-run preview / ack simulation / cancel simulation / reconciliation checklist",
            "保留等待 / 觀望、減碼 / 取消掛單 / 賣出風險降低路徑",
        ],
        "not_allowed": [
            "買入 / 加倉",
            "啟用風險進攻自動下單或完整實單自動化",
            "把 exact-live-lane proxy、reference windows、OOS pass、paper/shadow 或 dry-run 證據包裝成 live deployment closure",
            "輸出 credential / API key / secret 值；只能顯示 boolean 或 [REDACTED]",
        ],
        "next_gate": next_gate,
        "fail_closed_invariants": {
            "support_reference_only_until_exact_rows_meet_minimum": not support_ready,
            "circuit_breaker_blocks_live_until_release_condition_met": not breaker_ready,
            "paper_shadow_is_not_live_deployability": True,
            "credential_values_redacted": True,
            "reduce_risk_paths_remain_allowed": True,
        },
    }


def _format_optional_metric(label: str, value: Any) -> str:
    return f"{label}=—" if value is None else f"{label}={value}"


def _candidate_tier_label(value: Any) -> str:
    labels = {
        "runtime_blocked_oos_pass": "OOS 已過、即時 gate 阻塞（paper-shadow only）",
    }
    return labels.get(str(value), "—" if value is None else str(value))


def _candidate_verdict_label(value: Any) -> str:
    labels = {
        "not_deployable": "不可部署",
        "deployable": "可部署",
        "runtime_blocked": "即時 gate 阻塞",
    }
    return labels.get(str(value), "—" if value is None else str(value))


def _nearest_candidate_markdown(nearest: Mapping[str, Any]) -> str:
    if not nearest:
        return "- 最近研究候選：`—`"
    model = _first_present(nearest.get("model"), "—")
    top_k = _first_present(nearest.get("top_k"), "—")
    metrics = " / ".join(
        [
            _format_optional_metric("OOS ROI", nearest.get("oos_roi")),
            _format_optional_metric("勝率", nearest.get("win_rate")),
            _format_optional_metric("profit factor", nearest.get("profit_factor")),
            _format_optional_metric("最大回撤", nearest.get("max_drawdown")),
            _format_optional_metric("最差 fold", nearest.get("worst_fold")),
            _format_optional_metric("交易數", nearest.get("trade_count")),
        ]
    )
    return (
        f"- 最近研究候選：`{model}` / `{top_k}` / {metrics} / "
        f"候選層級={_candidate_tier_label(nearest.get('deployment_candidate_tier'))} / "
        f"部署判定={_candidate_verdict_label(nearest.get('verdict'))} / "
        "僅允許 paper-shadow，直到 live gates 全部通過"
    )


def markdown(payload: Mapping[str, Any]) -> str:
    support = payload.get("current_live_support") if isinstance(payload.get("current_live_support"), dict) else {}
    gate = payload.get("live_deployment_gate") if isinstance(payload.get("live_deployment_gate"), dict) else {}
    breaker = payload.get("circuit_breaker_gate") if isinstance(payload.get("circuit_breaker_gate"), dict) else {}
    topk = payload.get("topk_shadow_candidate_context") if isinstance(payload.get("topk_shadow_candidate_context"), dict) else {}
    venue = payload.get("venue_runtime_proof") if isinstance(payload.get("venue_runtime_proof"), dict) else {}

    lines = [
        "# Customer-safe alternative proof",
        "",
        f"- generated_at: `{payload.get('generated_at')}`",
        f"- current_live_blocker: `{support.get('deployment_blocker')}`",
        f"- current_live_structure_bucket: `{support.get('structure_bucket')}`",
        f"- exact support: `{support.get('current_rows')}/{support.get('minimum_support_rows')}` (gap `{support.get('gap_to_minimum')}`)",
        f"- support_route_verdict: `{support.get('support_route_verdict')}`",
        f"- circuit_breaker_release_ready: `{breaker.get('release_ready')}` (wins `{breaker.get('current_recent_window_wins')}/{breaker.get('required_recent_window_wins')}`, gap `{breaker.get('additional_recent_window_wins_needed')}`)",
        f"- primary_blocking_gate: `{gate.get('primary_blocking_gate') or gate.get('blocking_gate')}`",
        f"- canary_ready: **{gate.get('canary_ready')}**",
        f"- live_exposure_allowed: **{gate.get('live_exposure_allowed')}**",
        f"- order_submission_enabled: **{gate.get('order_submission_enabled')}**",
        "",
        "## PM handoff carried forward",
        str((payload.get("pm_handoff_carried_forward") or {}).get("decision")),
        "",
        "## Customer-safe lane available today",
        f"- Top-K risk-qualified rows: `{topk.get('risk_qualified_rows')}`",
        f"- Runtime-blocked candidates: `{topk.get('runtime_blocked_candidate_rows')}`",
        f"- Deployable rows: `{topk.get('deployable_rows')}`",
        _nearest_candidate_markdown(topk.get("nearest_candidate") if isinstance(topk.get("nearest_candidate"), dict) else {}),
        f"- Venue runtime_ready: `{venue.get('runtime_ready')}` / `{venue.get('readiness_state')}`",
        "- Allowed today:",
    ]
    for item in payload.get("allowed_today") or []:
        lines.append(f"  - {item}")
    lines += ["", "## Not allowed"]
    for item in payload.get("not_allowed") or []:
        lines.append(f"- {item}")
    lines += ["", "## Lanes"]
    for lane in payload.get("customer_safe_lanes") or []:
        if not isinstance(lane, dict):
            continue
        lines.append(
            f"- `{lane.get('id')}`: status=`{lane.get('status')}`, deployable=`{lane.get('deployable')}`, "
            f"live_exposure_allowed=`{lane.get('live_exposure_allowed')}`"
        )
    portfolio = payload.get("alternative_solution_portfolio") if isinstance(payload.get("alternative_solution_portfolio"), dict) else {}
    if portfolio:
        lines += [
            "",
            "## Alternative solution option portfolio",
            f"- option_count: `{portfolio.get('option_count')}`",
            f"- selected_next_artifact: `{portfolio.get('selected_next_artifact')}`",
            f"- time_to_evidence_bucket: `{portfolio.get('time_to_evidence_bucket')}`",
            f"- safety_invariant: {portfolio.get('safety_invariant')}",
        ]
        for option in portfolio.get("options") or []:
            if not isinstance(option, dict):
                continue
            lines.append(
                f"- `{option.get('id')}`: role=`{option.get('role')}`, deployable=`{option.get('deployable')}`, "
                f"live_exposure_allowed=`{option.get('live_exposure_allowed')}`, next=`{option.get('next_artifact')}`"
            )
    lines += ["", "## Next gate", str(payload.get("next_gate")), ""]
    return "\n".join(lines)


def load_default_payloads() -> dict[str, dict[str, Any]]:
    return {name: _read_json(path) for name, path in SOURCE_PATHS.items()}


def write_outputs(payload: Mapping[str, Any], json_out: Path, markdown_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n")
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(markdown(payload) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    args = parser.parse_args(argv)

    payloads = load_default_payloads()
    proof = build_customer_safe_alternative_proof(
        live_predict_probe=payloads["live_predict_probe"],
        circuit_breaker_audit=payloads["circuit_breaker_audit"],
        q15_support_fill_feasibility=payloads["q15_support_fill_feasibility"],
        high_conviction_topk_oos_matrix=payloads["high_conviction_topk_oos_matrix"],
        execution_metadata_smoke=payloads["execution_metadata_smoke"],
        recent_drift_report=payloads["recent_drift_report"],
    )
    write_outputs(proof, args.json_out, args.markdown_out)
    gate = proof["live_deployment_gate"]
    support = proof["current_live_support"]
    print(
        "customer_safe_alternative_proof: "
        f"live_exposure_allowed={gate['live_exposure_allowed']} "
        f"order_submission_enabled={gate['order_submission_enabled']} "
        f"support={support['current_rows']}/{support['minimum_support_rows']} "
        f"gap={support['gap_to_minimum']} "
        f"blocking_gate={gate['blocking_gate']} "
        f"breaker_release_ready={gate.get('breaker_release_ready')} "
        f"json={args.json_out} md={args.markdown_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
