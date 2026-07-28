#!/usr/bin/env python3
"""Refresh the live-canary structural pivot artifact from current runtime truth.

This artifact answers the PM forced-execution question without loosening live
trading gates: if a bounded micro-canary cannot execute in the 72h window, name
one primary failed gate, keep supplementary blockers visible, and point to the
next validation artifact.  It is generated from fresh heartbeat artifacts so the
live-canary plan does not keep stale breaker/support numbers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from customer_safe_alternative_proof import (  # noqa: E402
    _as_bool,
    _as_list,
    _first_present,
    _read_json,
    _to_int,
)

DATA_DIR = PROJECT_ROOT / "data"
DOCS_PLAN_DIR = PROJECT_ROOT / "docs" / "plans"
DEFAULT_JSON_OUT = DATA_DIR / "live_canary_structural_pivot.json"
DEFAULT_MARKDOWN_OUT = DOCS_PLAN_DIR / "2026-05-23-live-canary-structural-pivot.md"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

SOURCE_PATHS = {
    "live_predict_probe": DATA_DIR / "live_predict_probe.json",
    "circuit_breaker_audit": DATA_DIR / "circuit_breaker_audit.json",
    "high_conviction_topk_oos_matrix": DATA_DIR / "high_conviction_topk_oos_matrix.json",
    "execution_metadata_smoke": DATA_DIR / "execution_metadata_smoke.json",
    "customer_safe_alternative_proof": DATA_DIR / "customer_safe_alternative_proof.json",
    "q15_support_fill_feasibility": DATA_DIR / "q15_support_fill_feasibility.json",
    "q15_support_audit": DATA_DIR / "q15_support_audit.json",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _source_meta(payloads: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for name, path in SOURCE_PATHS.items():
        payload = payloads.get(name) or {}
        meta[name] = {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "exists": path.exists(),
            "generated_at": payload.get("generated_at") or payload.get("artifact_freshness_checked_at"),
        }
    return meta


def _execution_block(text: str) -> str:
    match = re.search(r"(?ms)^execution:\s*\n(?P<body>.*?)(?=^[^\s#][^\n]*:\s*|\Z)", text)
    return match.group("body") if match else ""


def _extract_scalar(block: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s+{re.escape(key)}:\s*([^#\n]+)", block)
    if not match:
        return None
    return match.group(1).strip().strip('"\'')


def _extract_bool(block: str, key: str) -> bool:
    value = _extract_scalar(block, key)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _config_snapshot(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Return a secret-safe view of local canary policy configuration."""

    try:
        text = config_path.read_text()
    except OSError:
        return {
            "config_path": str(config_path.relative_to(PROJECT_ROOT)),
            "exists": False,
            "execution_mode": None,
            "enable_live_trading": False,
            "live_canary_enabled": False,
            "allowed_symbols_configured": False,
            "max_base_qty_by_symbol_configured": False,
            "policy_ready": False,
            "credential_values_redacted": True,
        }

    block = _execution_block(text)
    mode = _extract_scalar(block, "mode") or "paper"
    enable_live_trading = _extract_bool(block, "enable_live_trading")
    live_canary_block = re.search(r"(?ms)^\s+live_canary:\s*\n(?P<body>.*?)(?=^\s{2}\S|^[^\s#]|\Z)", block)
    live_block = live_canary_block.group("body") if live_canary_block else ""
    live_canary_enabled = _extract_bool(live_block, "enabled") if live_block else False
    allowed_symbols_configured = bool(re.search(r"(?m)^\s+allowed_symbols:\s*\S", live_block))
    max_base_qty_by_symbol_configured = bool(re.search(r"(?m)^\s+max_base_qty_by_symbol:\s*", live_block))
    policy_ready = bool(
        mode in {"live", "live_canary"}
        and enable_live_trading
        and live_canary_enabled
        and allowed_symbols_configured
        and max_base_qty_by_symbol_configured
    )
    return {
        "config_path": str(config_path.relative_to(PROJECT_ROOT)),
        "exists": True,
        "execution_mode": mode,
        "enable_live_trading": enable_live_trading,
        "live_canary_enabled": live_canary_enabled,
        "allowed_symbols_configured": allowed_symbols_configured,
        "max_base_qty_by_symbol_configured": max_base_qty_by_symbol_configured,
        "policy_ready": policy_ready,
        "credential_values_redacted": True,
    }


def _release_context(live_probe: Mapping[str, Any], circuit_breaker_audit: Mapping[str, Any]) -> dict[str, Any]:
    details = live_probe.get("deployment_blocker_details") if isinstance(live_probe.get("deployment_blocker_details"), dict) else {}
    live_release = details.get("release_condition") if isinstance(details.get("release_condition"), dict) else {}
    release = circuit_breaker_audit.get("release_condition") if isinstance(circuit_breaker_audit.get("release_condition"), dict) else live_release
    release_ready = _as_bool(_first_present(release.get("release_ready"), live_probe.get("release_ready"), False))
    current_wins = _to_int(
        _first_present(
            release.get("current_recent_window_wins"),
            live_probe.get("current_recent_window_wins"),
            live_probe.get("recent_window_wins"),
            0,
        )
    )
    required_wins = _to_int(_first_present(release.get("required_recent_window_wins"), live_probe.get("required_recent_window_wins"), 15), default=15)
    additional_needed = _to_int(
        _first_present(
            release.get("additional_recent_window_wins_needed"),
            live_probe.get("additional_recent_window_wins_needed"),
            max(required_wins - current_wins, 0),
        )
    )
    return {
        "release_ready": release_ready,
        "blocked_by": release.get("blocked_by") or live_probe.get("triggered_by") or [],
        "current_streak": _to_int(_first_present(release.get("current_streak"), live_probe.get("streak"), 0)),
        "streak_must_be_below": _to_int(_first_present(release.get("streak_must_be_below"), 50), default=50),
        "recent_window": _to_int(_first_present(release.get("recent_window"), live_probe.get("window_size"), 50), default=50),
        "current_recent_window_win_rate": _first_present(
            release.get("current_recent_window_win_rate"),
            release.get("current_recent_window_win_rate"),
            live_probe.get("recent_window_win_rate"),
            0.0,
        ),
        "current_recent_window_wins": current_wins,
        "required_recent_window_wins": required_wins,
        "additional_recent_window_wins_needed": additional_needed,
    }


def _support_context(
    live_probe: Mapping[str, Any],
    topk: Mapping[str, Any],
    customer_safe: Mapping[str, Any],
    support_fill: Mapping[str, Any],
    q15_support_audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    q15_audit = q15_support_audit if isinstance(q15_support_audit, Mapping) else {}
    q15_support_route = q15_audit.get("support_route") if isinstance(q15_audit.get("support_route"), Mapping) else {}
    q15_support_progress = q15_support_route.get("support_progress") if isinstance(q15_support_route.get("support_progress"), Mapping) else {}
    q15_equilibrium = q15_audit.get("equilibrium_deadlock") if isinstance(q15_audit.get("equilibrium_deadlock"), Mapping) else {}
    if not q15_equilibrium and isinstance(q15_support_progress.get("equilibrium_deadlock"), Mapping):
        q15_equilibrium = q15_support_progress.get("equilibrium_deadlock")
    customer_support = customer_safe.get("current_live_support") if isinstance(customer_safe.get("current_live_support"), dict) else {}
    topk_support = topk.get("support_context") if isinstance(topk.get("support_context"), dict) else {}
    details = live_probe.get("deployment_blocker_details") if isinstance(live_probe.get("deployment_blocker_details"), dict) else {}
    support_progress = live_probe.get("support_progress") if isinstance(live_probe.get("support_progress"), dict) else {}
    if not support_progress and q15_support_progress:
        support_progress = q15_support_progress
    verdict = support_fill.get("verdict") if isinstance(support_fill.get("verdict"), dict) else {}

    rows = _to_int(
        _first_present(
            customer_support.get("current_rows"),
            live_probe.get("current_live_structure_bucket_rows"),
            details.get("current_live_structure_bucket_rows"),
            topk_support.get("current_live_structure_bucket_rows"),
            verdict.get("current_exact_bucket_rows"),
            0,
        )
    )
    minimum = _to_int(
        _first_present(
            customer_support.get("minimum_support_rows"),
            live_probe.get("minimum_support_rows"),
            details.get("minimum_support_rows"),
            topk_support.get("minimum_support_rows"),
            verdict.get("minimum_support_rows"),
            50,
        ),
        default=50,
    )
    gap = _to_int(
        _first_present(
            customer_support.get("gap_to_minimum"),
            live_probe.get("current_live_structure_bucket_gap_to_minimum"),
            details.get("current_live_structure_bucket_gap_to_minimum"),
            topk_support.get("current_live_structure_bucket_gap_to_minimum"),
            topk_support.get("gap_to_minimum"),
            verdict.get("gap_to_minimum"),
            max(minimum - rows, 0),
        )
    )
    route = _first_present(
        customer_support.get("support_route_verdict"),
        live_probe.get("support_route_verdict"),
        details.get("support_route_verdict"),
        topk_support.get("support_route_verdict"),
        verdict.get("q15_support_route_verdict"),
        "exact_bucket_unsupported_block",
    )
    deployable_hint = _first_present(
        customer_support.get("support_route_deployable"),
        live_probe.get("support_route_deployable"),
        details.get("support_route_deployable"),
        topk_support.get("support_route_deployable"),
        False,
    )
    support_ready = bool(_as_bool(deployable_hint) and rows >= minimum and gap == 0 and route == "exact_bucket_supported")
    return {
        "deployment_blocker": _first_present(
            live_probe.get("deployment_blocker"),
            customer_support.get("deployment_blocker"),
            topk_support.get("deployment_blocker"),
            "unsupported_exact_live_structure_bucket" if not support_ready else None,
        ),
        "structure_bucket": _first_present(
            live_probe.get("current_live_structure_bucket"),
            live_probe.get("structure_bucket"),
            customer_support.get("structure_bucket"),
            topk_support.get("current_live_structure_bucket"),
            "—",
        ),
        "support_route_verdict": route,
        "support_governance_route": _first_present(
            customer_support.get("support_governance_route"),
            live_probe.get("support_governance_route"),
            details.get("support_governance_route"),
            topk_support.get("support_governance_route"),
            "—",
        ),
        "support_rows": rows,
        "minimum_support_rows": minimum,
        "support_gap": gap,
        "support_ready": support_ready,
        "equilibrium_deadlock": q15_equilibrium,
        "equilibrium_deadlock_confirmed": _as_bool(q15_equilibrium.get("confirmed")) if isinstance(q15_equilibrium, Mapping) else False,
        "equilibrium_deadlock_verdict": q15_equilibrium.get("verdict") if isinstance(q15_equilibrium, Mapping) else None,
        "forced_research_action_required": _as_bool((q15_equilibrium.get("forced_research_action_artifact") or {}).get("required")) if isinstance(q15_equilibrium, Mapping) else False,
        "forced_research_action_output_path": (q15_equilibrium.get("forced_research_action_artifact") or {}).get("output_path") if isinstance(q15_equilibrium, Mapping) else None,
        "stagnant_run_count": _to_int(
            _first_present(
                support_progress.get("stagnant_run_count"),
                topk_support.get("stagnant_run_count"),
                topk_support.get("support_progress_stagnant_run_count"),
                0,
            )
        ),
        "support_delta_vs_previous": _to_int(
            _first_present(
                support_progress.get("delta_vs_previous"),
                topk_support.get("support_delta_vs_previous"),
                0,
            )
        ),
        "semantic_signature_delta_vs_previous": _to_int(
            _first_present(
                support_progress.get("semantic_signature_delta_vs_previous"),
                (support_progress.get("semantic_signature_progress") or {}).get("delta_vs_previous")
                if isinstance(support_progress.get("semantic_signature_progress"), Mapping)
                else None,
                topk_support.get("semantic_signature_delta_vs_previous"),
                0,
            )
        ),
        "semantic_signature_stagnant_run_count": _to_int(
            _first_present(
                support_progress.get("semantic_signature_stagnant_run_count"),
                (support_progress.get("semantic_signature_progress") or {}).get("stagnant_run_count")
                if isinstance(support_progress.get("semantic_signature_progress"), Mapping)
                else None,
                topk_support.get("semantic_signature_stagnant_run_count"),
                0,
            )
        ),
        "time_to_evidence_bucket": verdict.get("time_to_evidence_bucket"),
        "missing_capability_class": verdict.get("missing_capability_class"),
        "alternative_solution_required": _as_bool(verdict.get("alternative_solution_required", True)),
    }


def _topk_context(topk: Mapping[str, Any], customer_safe: Mapping[str, Any]) -> dict[str, Any]:
    customer_topk = customer_safe.get("topk_shadow_candidate_context") if isinstance(customer_safe.get("topk_shadow_candidate_context"), dict) else {}
    risk_qualified = _to_int(_first_present(customer_topk.get("risk_qualified_rows"), topk.get("risk_qualified_rows"), topk.get("risk_qualified_count")))
    runtime_blocked = _to_int(_first_present(customer_topk.get("runtime_blocked_candidate_rows"), topk.get("runtime_blocked_candidate_rows"), topk.get("runtime_blocked_candidate_count")))
    deployable = _to_int(_first_present(customer_topk.get("deployable_rows"), topk.get("deployable_rows"), topk.get("deployable_count")))
    nearest_rows = _as_list(topk.get("nearest_deployable_rows"))
    raw_nearest = nearest_rows[0] if nearest_rows and isinstance(nearest_rows[0], dict) else {}
    customer_nearest = customer_topk.get("nearest_candidate") if isinstance(customer_topk.get("nearest_candidate"), dict) else {}
    nearest = dict(raw_nearest)
    nearest.update(
        {
            key: value
            for key, value in customer_nearest.items()
            if value is not None and not (isinstance(value, str) and not value.strip())
        }
    )
    return {
        "risk_qualified_rows": risk_qualified,
        "runtime_blocked_candidate_rows": runtime_blocked,
        "deployable_rows": deployable,
        "topk_deployable": deployable > 0,
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
            "verdict": _first_present(nearest.get("verdict"), nearest.get("deployable_verdict")),
        },
    }


def _lane_actionability_context(live_probe: Mapping[str, Any], support: Mapping[str, Any]) -> dict[str, Any]:
    bucket = str(support.get("structure_bucket") or live_probe.get("current_live_structure_bucket") or "")
    regime_gate = str(live_probe.get("regime_gate") or "").upper()
    should_trade = _as_bool(live_probe.get("should_trade"))
    allowed_layers_raw = _to_int(live_probe.get("allowed_layers_raw"), default=None)
    allowed_layers = _to_int(live_probe.get("allowed_layers"), default=None)
    no_trade_block_lane = bool(
        bucket.startswith("BLOCK|")
        or regime_gate == "BLOCK"
        or (
            should_trade is False
            and allowed_layers_raw == 0
            and allowed_layers == 0
        )
    )
    if no_trade_block_lane:
        support_rows = _to_int(support.get("support_rows"), default=0)
        minimum_support_rows = _to_int(support.get("minimum_support_rows"), default=50)
        return {
            "current_lane_actionability": "no_trade_block_lane",
            "support_evidence_role": "no_trade_decision_validation_not_deployable_support",
            "operator_interpretation": (
                "當前即時 lane 是 BLOCK / 不交易決策 lane。"
                f"精準支持 {support_rows}/{minimum_support_rows} 只可視為無風險觀望驗證，"
                "不可視為買入 / 加倉部署 closure。"
            ),
            "map_signal_forced_lane": "no_trade_lane_audit",
            "next_validation_artifact": "data/no_trade_lane_replay.json；驗證觀望 / reduce-only 行為，不把它寫成 risk-on support closure。",
        }
    return {
        "current_lane_actionability": "risk_on_candidate_lane",
        "support_evidence_role": "deployment_support_identity_required",
        "operator_interpretation": (
            "Current live lane can become risk-on only after exact support, breaker, model-shadow, "
            "venue lifecycle, and live-canary policy gates all pass."
        ),
        "map_signal_forced_lane": "support_identity_redesign",
        "next_validation_artifact": _next_validation_artifact(
            "current_live_support_gate",
            support.get("structure_bucket"),
        ),
    }


def _venue_context(execution_smoke: Mapping[str, Any], customer_safe: Mapping[str, Any]) -> dict[str, Any]:
    customer_venue = customer_safe.get("venue_runtime_proof") if isinstance(customer_safe.get("venue_runtime_proof"), dict) else {}
    source = customer_venue if customer_venue else execution_smoke
    venues = []
    for row in _as_list(source.get("venues")):
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
    okx = next((venue for venue in venues if str(venue.get("venue") or "").lower() == "okx"), {})
    return {
        "runtime_ready": _as_bool(source.get("runtime_ready")),
        "readiness_state": source.get("readiness_state") or "blocked_until_runtime_lifecycle_proof",
        "runtime_ready_count": _to_int(source.get("runtime_ready_count")),
        "runtime_ready_blockers": [str(item) for item in _as_list(source.get("runtime_ready_blockers"))],
        "okx_credentials_configured": _as_bool(okx.get("credentials_configured")),
        "okx_runtime_ready": _as_bool(okx.get("runtime_ready")),
        "venues": venues,
    }


def _select_primary_failed_gate(
    *,
    support_ready: bool,
    breaker_ready: bool,
    topk_deployable: bool,
    venue_ready: bool,
    policy_ready: bool,
) -> str:
    """Pick the single operator-facing 72h gate.

    The single failed gate must follow current runtime blocker priority.  When the
    canonical circuit breaker is still active, naming support first makes the
    hard no-go artifact contradict `/api/status`, PM status, and the customer-safe
    alternative proof.  Exact support remains a required supplementary/live gate,
    but it becomes the primary 72h gate only after breaker release math clears.
    """

    if not breaker_ready:
        return "circuit_breaker_gate"
    if not support_ready:
        return "current_live_support_gate"
    if not topk_deployable:
        return "model_shadow_outcome_gate"
    if not venue_ready:
        return "venue_lifecycle_gate"
    if not policy_ready:
        return "live_canary_policy_gate"
    return "none"


def _gate_summary(
    support: Mapping[str, Any],
    release: Mapping[str, Any],
    topk: Mapping[str, Any],
    venue: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    support_ready = bool(support.get("support_ready"))
    breaker_ready = bool(release.get("release_ready"))
    topk_deployable = bool(topk.get("topk_deployable"))
    venue_ready = bool(venue.get("runtime_ready"))
    policy_ready = bool(config.get("policy_ready"))
    primary = _select_primary_failed_gate(
        support_ready=support_ready,
        breaker_ready=breaker_ready,
        topk_deployable=topk_deployable,
        venue_ready=venue_ready,
        policy_ready=policy_ready,
    )
    gates = {
        "current_live_support_gate": {
            "ready": support_ready,
            "current": support.get("support_rows"),
            "required": support.get("minimum_support_rows"),
            "gap": support.get("support_gap"),
            "reason": "current-live exact support must reach the minimum with matching support_identity.",
        },
        "circuit_breaker_gate": {
            "ready": breaker_ready,
            "current_recent_window_wins": release.get("current_recent_window_wins"),
            "required_recent_window_wins": release.get("required_recent_window_wins"),
            "additional_recent_window_wins_needed": release.get("additional_recent_window_wins_needed"),
            "current_streak": release.get("current_streak"),
            "reason": "recent canonical 24h outcomes must clear streak and win-rate release math.",
        },
        "model_shadow_outcome_gate": {
            "ready": topk_deployable,
            "risk_qualified_rows": topk.get("risk_qualified_rows"),
            "runtime_blocked_candidate_rows": topk.get("runtime_blocked_candidate_rows"),
            "deployable_rows": topk.get("deployable_rows"),
            "reason": "OOS pass / paper-shadow rows are not live deployability until deployable_rows>0 under current gates.",
        },
        "venue_lifecycle_gate": {
            "ready": venue_ready,
            "runtime_ready": venue.get("runtime_ready"),
            "okx_credentials_configured": venue.get("okx_credentials_configured"),
            "readiness_state": venue.get("readiness_state"),
            "reason": "exchange credential boolean plus ack/fill/cancel/reconciliation proof must be runtime-backed.",
        },
        "live_canary_policy_gate": {
            "ready": policy_ready,
            "execution_mode": config.get("execution_mode"),
            "enable_live_trading": config.get("enable_live_trading"),
            "live_canary_enabled": config.get("live_canary_enabled"),
            "allowed_symbols_configured": config.get("allowed_symbols_configured"),
            "max_base_qty_by_symbol_configured": config.get("max_base_qty_by_symbol_configured"),
            "reason": "local config must opt into explicit live_canary with symbol cap before adapter order submission.",
        },
    }
    supplementary = [name for name, gate in gates.items() if name != primary and not gate["ready"]]
    return {
        "micro_canary_ready": primary == "none",
        "live_exposure_allowed": primary == "none",
        "risk_on_order_enabled": primary == "none",
        "order_submission_enabled": primary == "none",
        "single_failed_gate_for_72h_decision": primary,
        "supplementary_blockers_not_used_as_single_gate": supplementary,
        "gates": gates,
    }


def _next_validation_artifact(primary_gate: str, structure_bucket: str | None = None) -> str:
    current_bucket_hint = f" for current bucket {structure_bucket}" if structure_bucket else ""
    current_support_artifact = (
        "data/q15_support_fill_feasibility.json "
        "(current support-fill q15/q35 compatibility artifact) + "
        f"data/live_predict_probe.json{current_bucket_hint} "
        "after Map/Signal redesign or exact-bucket row harvest"
    )
    mapping = {
        "current_live_support_gate": current_support_artifact,
        "circuit_breaker_gate": "data/circuit_breaker_audit.json after 24h canonical tail outcomes improve",
        "model_shadow_outcome_gate": "data/high_conviction_topk_oos_matrix.json + Shadow Trade Ledger 24h pyramid outcome rows",
        "venue_lifecycle_gate": "data/execution_metadata_smoke.json with runtime-backed OKX ack/cancel/fill/reconciliation proof",
        "live_canary_policy_gate": "config.yaml secret-safe live_canary policy diff + execution_service canary tests",
        "none": "first bounded micro-canary runbook + post-trade reconciliation artifact",
    }
    return mapping.get(primary_gate, current_support_artifact)


def build_live_canary_structural_pivot(
    *,
    live_predict_probe: Mapping[str, Any] | None = None,
    circuit_breaker_audit: Mapping[str, Any] | None = None,
    high_conviction_topk_oos_matrix: Mapping[str, Any] | None = None,
    execution_metadata_smoke: Mapping[str, Any] | None = None,
    customer_safe_alternative_proof: Mapping[str, Any] | None = None,
    q15_support_fill_feasibility: Mapping[str, Any] | None = None,
    q15_support_audit: Mapping[str, Any] | None = None,
    config_snapshot: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    live = dict(live_predict_probe or {})
    breaker = dict(circuit_breaker_audit or {})
    topk_payload = dict(high_conviction_topk_oos_matrix or {})
    execution = dict(execution_metadata_smoke or {})
    customer = dict(customer_safe_alternative_proof or {})
    support_fill = dict(q15_support_fill_feasibility or {})
    q15_audit = dict(q15_support_audit or {})
    config = dict(config_snapshot or _config_snapshot())

    release = _release_context(live, breaker)
    support = _support_context(live, topk_payload, customer, support_fill, q15_audit)
    topk = _topk_context(topk_payload, customer)
    venue = _venue_context(execution, customer)
    lane_actionability = _lane_actionability_context(live, support)
    gates = _gate_summary(support, release, topk, venue, config)
    primary_gate = gates["single_failed_gate_for_72h_decision"]
    next_artifact = _next_validation_artifact(primary_gate, support.get("structure_bucket"))
    support_redesign_artifact = _next_validation_artifact(
        "current_live_support_gate",
        support.get("structure_bucket"),
    )

    payloads = {
        "live_predict_probe": live,
        "circuit_breaker_audit": breaker,
        "high_conviction_topk_oos_matrix": topk_payload,
        "execution_metadata_smoke": execution,
        "customer_safe_alternative_proof": customer,
        "q15_support_fill_feasibility": support_fill,
        "q15_support_audit": q15_audit,
    }
    quick_read = {
        "deployment_blocker": support.get("deployment_blocker"),
        "current_live_structure_bucket": support.get("structure_bucket"),
        "current_lane_actionability": lane_actionability.get("current_lane_actionability"),
        "support_evidence_role": lane_actionability.get("support_evidence_role"),
        "map_signal_forced_lane": lane_actionability.get("map_signal_forced_lane"),
        "current_lane_next_validation_artifact": lane_actionability.get("next_validation_artifact"),
        "support_rows": support.get("support_rows"),
        "minimum_support_rows": support.get("minimum_support_rows"),
        "support_gap": support.get("support_gap"),
        "support_route_verdict": support.get("support_route_verdict"),
        "support_governance_route": support.get("support_governance_route"),
        "support_ready": support.get("support_ready"),
        "release_ready": release.get("release_ready"),
        "recent_window_wins": release.get("current_recent_window_wins"),
        "required_recent_window_wins": release.get("required_recent_window_wins"),
        "additional_recent_window_wins_needed": release.get("additional_recent_window_wins_needed"),
        "topk_deployable": topk.get("topk_deployable"),
        "deployable_rows": topk.get("deployable_rows"),
        "paper_shadow_available": topk.get("paper_shadow_available"),
        "venue_runtime_ready": venue.get("runtime_ready"),
        "live_canary_policy_ready": config.get("policy_ready"),
        "micro_canary_ready": gates.get("micro_canary_ready"),
        "live_exposure_allowed": gates.get("live_exposure_allowed"),
        "risk_on_order_enabled": gates.get("risk_on_order_enabled"),
        "order_submission_enabled": gates.get("order_submission_enabled"),
        "single_failed_gate_for_72h_decision": primary_gate,
        "single_failed_gate": primary_gate,
        "next_validation_artifact": next_artifact,
    }

    return {
        "generated_at": generated_at or _now_iso(),
        "artifact": "live_canary_structural_pivot",
        # Stable top-level quick-read fields for PM/API/operator checks that
        # should not have to infer readiness from nested gate payloads.
        "quick_read": quick_read,
        **quick_read,
        "source_artifacts": _source_meta(payloads),
        "pm_handoff_carried_forward": {
            "decision": "PM 強制反平衡：若 72h 內不能執行 bounded micro-canary，必須寫明單一失敗 gate 與下一個驗證 artifact；不得再只做 observation-only heartbeat。",
            "selected_customer_safe_lane": "paper_shadow_decision_support_sleeve",
            "forbidden_shortcut": "不可降低 live gate；不可把 proxy/reference/OOS/shadow/dry-run 包裝成 live deployability。",
        },
        "current_truth": {
            "deployment_blocker": support.get("deployment_blocker"),
            "structure_bucket": support.get("structure_bucket"),
            "current_lane_actionability": lane_actionability.get("current_lane_actionability"),
            "support_evidence_role": lane_actionability.get("support_evidence_role"),
            "operator_interpretation": lane_actionability.get("operator_interpretation"),
            "map_signal_forced_lane": lane_actionability.get("map_signal_forced_lane"),
            "support_rows": support.get("support_rows"),
            "minimum_support_rows": support.get("minimum_support_rows"),
            "support_gap": support.get("support_gap"),
            "support_route_verdict": support.get("support_route_verdict"),
            "support_governance_route": support.get("support_governance_route"),
            "support_delta_vs_previous": support.get("support_delta_vs_previous"),
            "stagnant_run_count": support.get("stagnant_run_count"),
            "semantic_signature_delta_vs_previous": support.get("semantic_signature_delta_vs_previous"),
            "semantic_signature_stagnant_run_count": support.get("semantic_signature_stagnant_run_count"),
            "equilibrium_deadlock_confirmed": support.get("equilibrium_deadlock_confirmed"),
            "equilibrium_deadlock_verdict": support.get("equilibrium_deadlock_verdict"),
            "forced_research_action_required": support.get("forced_research_action_required"),
            "forced_research_action_output_path": support.get("forced_research_action_output_path"),
            "release_ready": release.get("release_ready"),
            "recent_window_size": release.get("recent_window"),
            "recent_window_wins": release.get("current_recent_window_wins"),
            "required_recent_window_wins": release.get("required_recent_window_wins"),
            "additional_recent_window_wins_needed": release.get("additional_recent_window_wins_needed"),
            "current_streak": release.get("current_streak"),
            "venue_runtime_ready": venue.get("runtime_ready"),
            "okx_credentials_configured": venue.get("okx_credentials_configured"),
            "risk_qualified_rows": topk.get("risk_qualified_rows"),
            "runtime_blocked_candidate_rows": topk.get("runtime_blocked_candidate_rows"),
            "deployable_rows": topk.get("deployable_rows"),
            "paper_shadow_available": topk.get("paper_shadow_available"),
            "execution_mode": config.get("execution_mode"),
            "live_canary_policy_ready": config.get("policy_ready"),
            "nearest_candidate": topk.get("nearest_candidate"),
        },
        "structural_decision": {
            "decision": "停止重複 observation-only。每輪刷新 live-canary pivot，將 readiness 拆成 support、breaker、model-shadow、venue lifecycle、live-canary policy 五個 gate。",
            "non_negotiable_invariant": "No risk-on buy/add while any support, breaker, model-shadow, venue lifecycle, or canary policy gate is failing.",
            "single_failed_gate_for_72h_decision": primary_gate,
            "supplementary_blockers_not_used_as_single_gate": gates["supplementary_blockers_not_used_as_single_gate"],
            "next_validation_artifact": next_artifact,
            "artifact_refresh_patch": "scripts/live_canary_structural_pivot.py now derives this plan from fresh runtime artifacts and q15 support audit deadlock state, and is wired into hb_parallel_runner serial lanes.",
            "equilibrium_deadlock_verdict": support.get("equilibrium_deadlock_verdict"),
            "forced_research_action_required": support.get("forced_research_action_required"),
            "forced_research_action_output_path": support.get("forced_research_action_output_path"),
            "current_lane_actionability": lane_actionability.get("current_lane_actionability"),
            "support_evidence_role": lane_actionability.get("support_evidence_role"),
            "map_signal_forced_lane": lane_actionability.get("map_signal_forced_lane"),
            "map_signal_next_validation_artifact": lane_actionability.get("next_validation_artifact"),
        },
        "micro_canary_gate": gates,
        "lanes": [
            {
                "lane": "A_venue_lifecycle_proof",
                "goal": "Get real exchange plumbing out of theory: credential boolean, ack, cancel/fill/reconciliation lifecycle proof.",
                "can_start_now": True,
                "status": "ready" if venue.get("runtime_ready") else "blocked_missing_runtime_backed_proof",
                "blocks_strategy_risk": True,
                "live_exposure": "none_or_min_exchange_probe_only",
                "exit_gate": "okx runtime_ready=true, credentials_configured=true, no lifecycle blockers; no secret values logged.",
                "operator_steps": [
                    "Configure OKX credentials locally only; never paste secrets in chat or docs.",
                    "Run: PYTHONPATH=. venv/bin/python scripts/execution_metadata_smoke.py --symbol BTCUSDT --venues okx",
                    "If credentials are present, perform sandbox or minimum-size lifecycle proof and verify OrderLifecycleEvent contains validation_passed + venue_ack + cancel/fill/reconciliation evidence.",
                ],
            },
            {
                "lane": "B_model_shadow_to_decision",
                "goal": "Keep high-conviction model work producing actionable go/no-go evidence without pretending current-live support is deployable.",
                "can_start_now": bool(topk.get("paper_shadow_available")),
                "status": "paper_shadow_available" if topk.get("paper_shadow_available") else "waiting_for_shadow_candidate",
                "blocks_strategy_risk": True,
                "live_exposure": "paper_shadow_only",
                "exit_gate": "Top-K candidate remains OOS positive, breaker clears, exact support closes, and deployable_rows>0.",
                "operator_steps": [
                    "Start/selective sleeve shadow run for nearest top-k candidate.",
                    "Record 24h pyramid outcome, missed entry reason, and whether the signal would survive spread/slippage.",
                    "If same semantic signature + support delta=0 persists, switch to Map/Signal redesign instead of another observation-only heartbeat.",
                ],
            },
            {
                "lane": "C_strategy_micro_canary",
                "goal": "Actual strategy live exposure, but only as bounded pilot rather than full deployment.",
                "can_start_now": bool(gates.get("micro_canary_ready")),
                "status": "ready" if gates.get("micro_canary_ready") else f"blocked_by_{primary_gate}",
                "blocks_strategy_risk": False,
                "live_exposure": "max one first-layer position, tiny symbol cap, no auto-add, no pyramiding until post-trade proof is clean",
                "entry_gate": [
                    "current-live exact support rows >= minimum and support_route_deployable=true",
                    "circuit_breaker release_ready=true",
                    "Top-K/model-shadow gate deployable_rows>=1 or explicit operator pilot exception recorded in ORID",
                    "Venue lifecycle proof complete",
                    "execution.live_canary.enabled=true with allowed_symbols and max_base_qty_by_symbol",
                ],
                "kill_gate": [
                    "one failed venue ack/cancel/fill lifecycle event",
                    "daily loss >= configured canary budget",
                    "one slippage/reconciliation mismatch above configured tolerance",
                    "current runtime flips back to bear hard block or breaker active",
                ],
            },
            {
                "lane": "D_map_signal_redesign_for_current_bucket",
                "goal": (
                    (
                        "Current BLOCK/no-trade lane should be audited as abstain/reduce-only evidence, "
                        "not harvested as buy/add deployment support."
                    )
                    if lane_actionability.get("current_lane_actionability") == "no_trade_block_lane"
                    else (
                        "When exact current bucket support remains below minimum with support delta=0, "
                        "stop waiting for rows and produce a Map/Signal redesign proof path."
                    )
                ),
                "can_start_now": bool(
                    lane_actionability.get("current_lane_actionability") == "no_trade_block_lane"
                    or
                    support.get("forced_research_action_required")
                    or (
                        support.get("support_gap", 0) > 0
                        and (
                            support.get("support_delta_vs_previous") == 0
                            or support.get("semantic_signature_delta_vs_previous") == 0
                        )
                    )
                ),
                "status": (
                    "no_trade_lane_audit_required"
                    if lane_actionability.get("current_lane_actionability") == "no_trade_block_lane"
                    else (
                        "equilibrium_deadlock_required"
                        if support.get("equilibrium_deadlock_confirmed")
                        else (
                            "forced_research_action_required"
                            if support.get("forced_research_action_required")
                            else (
                                "required"
                                if support.get("support_gap", 0) > 0
                                and (
                                    support.get("support_delta_vs_previous") == 0
                                    or support.get("semantic_signature_delta_vs_previous") == 0
                                )
                                else "standby"
                            )
                        )
                    )
                ),
                "blocks_strategy_risk": True,
                "live_exposure": "none",
                "exit_gate": "A new support identity / semantic bucket map is proposed, replayed, and proven without reclassifying reference rows as deployable support.",
                "semantic_signature_delta_vs_previous": support.get("semantic_signature_delta_vs_previous"),
                "semantic_signature_stagnant_run_count": support.get("semantic_signature_stagnant_run_count"),
                "equilibrium_deadlock_confirmed": support.get("equilibrium_deadlock_confirmed"),
                "equilibrium_deadlock_verdict": support.get("equilibrium_deadlock_verdict"),
                "forced_research_action_required": support.get("forced_research_action_required"),
                "forced_research_action_output_path": support.get("forced_research_action_output_path"),
                "current_lane_actionability": lane_actionability.get("current_lane_actionability"),
                "support_evidence_role": lane_actionability.get("support_evidence_role"),
                "next_artifact": lane_actionability.get("next_validation_artifact") or support_redesign_artifact,
            },
        ],
        "operator_config_snapshot_redacted": config,
        "operator_config_template_redacted": {
            "execution": {
                "mode": "live_canary",
                "venue": "okx",
                "enable_live_trading": True,
                "kill_switch": False,
                "max_daily_loss_pct": 0.003,
                "max_consecutive_failures": 1,
                "live_canary": {
                    "enabled": True,
                    "allowed_symbols": ["BTC/USDT"],
                    "max_base_qty_by_symbol": {"BTC/USDT": 0.0001},
                },
                "venues": {
                    "okx": {
                        "enabled": True,
                        "api_key": "[REDACTED]",
                        "api_secret": "[REDACTED]",
                        "passphrase": "[REDACTED]",
                        "default_type": "spot",
                    }
                },
            }
        },
        "next_72h_sequence": [
            "T+0h: Keep buy/add fail-closed; refresh this pivot from artifacts and name the single failed gate.",
            "T+4h: If primary gate is breaker, refresh circuit_breaker_audit plus canonical tail root-cause and do not relabel support/proxy rows as breaker release.",
            "T+4h: If primary gate is venue, produce OKX runtime lifecycle proof; if credentials are missing, credential boolean remains false and secrets stay redacted.",
            "T+24h: Run/select Shadow Trade Ledger sleeve for the nearest Top-K candidate and collect 24h pyramid outcome without order submission.",
            "T+48h: If the single failed gate is support, produce Map/Signal redesign or exact-bucket support-harvest proof instead of another passive status refresh.",
            "T+72h: Either execute one bounded micro-canary after all gates pass, or record hard no-go with this artifact's single_failed_gate_for_72h_decision.",
        ],
        "hard_no_go_now": {
            "micro_canary_ready": gates.get("micro_canary_ready"),
            "live_exposure_allowed": gates.get("live_exposure_allowed"),
            "order_submission_enabled": gates.get("order_submission_enabled"),
            "reason": f"primary_failed_gate={primary_gate}; next_validation_artifact={next_artifact}",
        },
    }


def markdown(payload: Mapping[str, Any]) -> str:
    truth = payload.get("current_truth") if isinstance(payload.get("current_truth"), dict) else {}
    decision = payload.get("structural_decision") if isinstance(payload.get("structural_decision"), dict) else {}
    gate = payload.get("micro_canary_gate") if isinstance(payload.get("micro_canary_gate"), dict) else {}
    config = payload.get("operator_config_snapshot_redacted") if isinstance(payload.get("operator_config_snapshot_redacted"), dict) else {}

    lines = [
        "# Live canary structural pivot",
        "",
        f"- generated_at: `{payload.get('generated_at')}`",
        f"- PM handoff carried forward: `{(payload.get('pm_handoff_carried_forward') or {}).get('decision')}`",
        f"- deployment_blocker: `{truth.get('deployment_blocker')}`",
        f"- current bucket: `{truth.get('structure_bucket')}`",
        f"- lane actionability: `{truth.get('current_lane_actionability')}` / support evidence role: `{truth.get('support_evidence_role')}`",
        f"- operator interpretation: {truth.get('operator_interpretation')}",
        f"- support: `{truth.get('support_rows')}/{truth.get('minimum_support_rows')}` (gap `{truth.get('support_gap')}`, delta `{truth.get('support_delta_vs_previous')}`, stagnant `{truth.get('stagnant_run_count')}`)",
        f"- semantic-signature progress: delta `{truth.get('semantic_signature_delta_vs_previous')}`, stagnant `{truth.get('semantic_signature_stagnant_run_count')}` (does not relax strict support_identity)",
        f"- equilibrium deadlock: confirmed=`{truth.get('equilibrium_deadlock_confirmed')}`, verdict=`{truth.get('equilibrium_deadlock_verdict')}`, forced_artifact=`{truth.get('forced_research_action_output_path')}`",
        f"- release_ready: `{truth.get('release_ready')}` / recent wins `{truth.get('recent_window_wins')}/{truth.get('recent_window_size')}`, required `{truth.get('required_recent_window_wins')}`, needed `{truth.get('additional_recent_window_wins_needed')}`",
        f"- venue_runtime_ready: `{truth.get('venue_runtime_ready')}` / OKX credentials configured: `{truth.get('okx_credentials_configured')}`",
        f"- top-k: risk-qualified `{truth.get('risk_qualified_rows')}`, runtime-blocked `{truth.get('runtime_blocked_candidate_rows')}`, deployable `{truth.get('deployable_rows')}`",
        f"- local execution mode: `{truth.get('execution_mode')}` / live_canary_policy_ready: `{truth.get('live_canary_policy_ready')}`",
        f"- micro_canary_ready: **{gate.get('micro_canary_ready')}** / order_submission_enabled: **{gate.get('order_submission_enabled')}**",
        f"- single_failed_gate_for_72h_decision: `{decision.get('single_failed_gate_for_72h_decision')}`",
        f"- next_validation_artifact: `{decision.get('next_validation_artifact')}`",
        f"- map_signal_forced_lane: `{decision.get('map_signal_forced_lane')}` / next artifact: `{decision.get('map_signal_next_validation_artifact')}`",
        "",
        "## Decision",
        str(decision.get("decision")),
        "",
        "## Why this is not observation-only",
        "本 artifact 由 fresh runtime artifacts 重新生成，保留數字零值（例如 support_rows=0、deployable_rows=0），並把 72h 決策壓成一個主要失敗 gate；其餘 gate 只列為補充 blocker，不拿來稀釋責任。",
        "",
        "## Gates",
    ]
    gates = gate.get("gates") if isinstance(gate.get("gates"), dict) else {}
    for name, row in gates.items():
        if not isinstance(row, dict):
            continue
        lines.append(f"- `{name}`: ready=`{row.get('ready')}`, reason={row.get('reason')}")
    supplementary = gate.get("supplementary_blockers_not_used_as_single_gate") or []
    lines += [
        "",
        "## Supplementary blockers",
        ", ".join(f"`{item}`" for item in supplementary) if supplementary else "None",
        "",
        "## Lanes",
    ]
    for lane in payload.get("lanes") or []:
        if not isinstance(lane, dict):
            continue
        lines.append(
            f"- `{lane.get('lane')}`: status=`{lane.get('status')}`, can_start_now=`{lane.get('can_start_now')}`, live_exposure=`{lane.get('live_exposure')}`"
        )
    lines += [
        "",
        "## Local config snapshot (secret-safe)",
        f"- config: `{config.get('config_path')}` exists=`{config.get('exists')}`",
        f"- execution_mode: `{config.get('execution_mode')}`",
        f"- enable_live_trading: `{config.get('enable_live_trading')}`",
        f"- live_canary_enabled: `{config.get('live_canary_enabled')}`",
        f"- allowed_symbols_configured: `{config.get('allowed_symbols_configured')}`",
        f"- max_base_qty_by_symbol_configured: `{config.get('max_base_qty_by_symbol_configured')}`",
        f"- credential_values_redacted: `{config.get('credential_values_redacted')}`",
        "",
        "## 72h sequence",
    ]
    for idx, item in enumerate(payload.get("next_72h_sequence") or [], start=1):
        lines.append(f"{idx}. {item}")
    hard_no = payload.get("hard_no_go_now") if isinstance(payload.get("hard_no_go_now"), dict) else {}
    lines += [
        "",
        "## Hard no-go now",
        f"micro_canary_ready=`{hard_no.get('micro_canary_ready')}`, live_exposure_allowed=`{hard_no.get('live_exposure_allowed')}`, order_submission_enabled=`{hard_no.get('order_submission_enabled')}`.",
        str(hard_no.get("reason")),
    ]
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
    pivot = build_live_canary_structural_pivot(
        live_predict_probe=payloads["live_predict_probe"],
        circuit_breaker_audit=payloads["circuit_breaker_audit"],
        high_conviction_topk_oos_matrix=payloads["high_conviction_topk_oos_matrix"],
        execution_metadata_smoke=payloads["execution_metadata_smoke"],
        customer_safe_alternative_proof=payloads["customer_safe_alternative_proof"],
        q15_support_fill_feasibility=payloads["q15_support_fill_feasibility"],
        q15_support_audit=payloads["q15_support_audit"],
    )
    write_outputs(pivot, args.json_out, args.markdown_out)
    truth = pivot["current_truth"]
    decision = pivot["structural_decision"]
    gate = pivot["micro_canary_gate"]
    print(
        "live_canary_structural_pivot: "
        f"support={truth['support_rows']}/{truth['minimum_support_rows']} "
        f"release_ready={truth['release_ready']} "
        f"wins={truth['recent_window_wins']}/{truth['recent_window_size']} "
        f"deployable_rows={truth['deployable_rows']} "
        f"venue_ready={truth['venue_runtime_ready']} "
        f"policy_ready={truth['live_canary_policy_ready']} "
        f"micro_canary_ready={gate['micro_canary_ready']} "
        f"single_failed_gate={decision['single_failed_gate_for_72h_decision']} "
        f"json={args.json_out} md={args.markdown_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
