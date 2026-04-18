#!/usr/bin/env python3
"""Summarize current live decision-quality pathology lanes.

Consumes the persisted `data/live_predict_probe.json` from hb_predict_probe.py and
writes a compact artifact + markdown note that highlight the current live lane,
chosen calibration scope, broader spillover lane, and shared 4H collapse shifts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.live_pathology_summary import build_live_pathology_scope_surface

PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
Q35_AUDIT_PATH = PROJECT_ROOT / "data" / "q35_scaling_audit.json"
BULL_4H_POCKET_ABLATION_PATH = PROJECT_ROOT / "data" / "bull_4h_pocket_ablation.json"
OUT_JSON = PROJECT_ROOT / "data" / "live_decision_quality_drilldown.json"
OUT_MD = PROJECT_ROOT / "docs" / "analysis" / "live_decision_quality_drilldown.md"


def _scope_summary(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    recent = payload.get("recent_pathology") or {}
    spillover = payload.get("spillover_vs_exact_live_lane") or {}
    live_bucket = payload.get("current_live_structure_bucket_metrics") or {}
    return {
        "scope": name,
        "rows": int(payload.get("rows") or 0),
        "win_rate": payload.get("win_rate"),
        "avg_pnl": payload.get("avg_pnl"),
        "avg_quality": payload.get("avg_quality"),
        "avg_drawdown_penalty": payload.get("avg_drawdown_penalty"),
        "avg_time_underwater": payload.get("avg_time_underwater"),
        "alerts": list(payload.get("alerts") or []),
        "recent_pathology_applied": bool(recent.get("applied")),
        "recent_pathology_window": recent.get("window"),
        "recent_pathology_reason": recent.get("reason"),
        "current_live_structure_bucket": payload.get("current_live_structure_bucket"),
        "current_live_structure_bucket_rows": int(payload.get("current_live_structure_bucket_rows") or 0),
        "current_live_structure_bucket_share": payload.get("current_live_structure_bucket_share"),
        "current_live_structure_bucket_metrics": live_bucket or None,
        "spillover_extra_rows": int(spillover.get("extra_rows") or 0),
        "spillover_extra_row_share": spillover.get("extra_row_share"),
        "spillover_worst_extra_regime_gate": spillover.get("worst_extra_regime_gate"),
        "spillover_top_shifts": ((spillover.get("worst_extra_regime_gate_feature_contrast") or {}).get("top_mean_shift_features") or []),
        "exact_gate_path": spillover.get("exact_live_gate_path_summary"),
        "spillover_gate_path": spillover.get("worst_extra_regime_gate_path_summary"),
    }


def _safe_round(value: Any, digits: int = 4) -> Any:
    if isinstance(value, (int, float)):
        return round(float(value), digits)
    return value


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_q35_audit_counterfactuals() -> dict[str, Any]:
    if not Q35_AUDIT_PATH.exists():
        return {}
    try:
        payload = json.loads(Q35_AUDIT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload.get("counterfactuals") or {}


def _runtime_blocker_summary(payload: dict[str, Any]) -> dict[str, Any] | None:
    signal = str(payload.get("signal") or "")
    model_type = str(payload.get("model_type") or "")
    if signal != "CIRCUIT_BREAKER" and model_type != "circuit_breaker":
        return None
    details = payload.get("deployment_blocker_details") or {}
    release_condition = details.get("release_condition") or {}
    recent_window = details.get("recent_window") or {}
    return {
        "type": "circuit_breaker",
        "signal": signal or "CIRCUIT_BREAKER",
        "model_type": model_type or "circuit_breaker",
        "reason": payload.get("reason"),
        "streak": payload.get("streak"),
        "win_rate": payload.get("win_rate"),
        "recent_window_win_rate": payload.get("recent_window_win_rate"),
        "recent_window_wins": payload.get("recent_window_wins"),
        "window_size": payload.get("window_size"),
        "triggered_by": payload.get("triggered_by") or [],
        "horizon_minutes": payload.get("horizon_minutes"),
        "allowed_layers": payload.get("allowed_layers"),
        "release_condition": release_condition,
        "recent_window": recent_window,
    }


def _deployment_blocker_summary(payload: dict[str, Any]) -> dict[str, Any] | None:
    blocker_type = payload.get("deployment_blocker")
    if not blocker_type:
        return None
    return {
        "type": blocker_type,
        "reason": payload.get("deployment_blocker_reason"),
        "source": payload.get("deployment_blocker_source"),
        "details": payload.get("deployment_blocker_details") or {},
    }


def _unavailable_component_gap_attribution(reason: str | None, blocker: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "trade_floor": None,
        "entry_quality": None,
        "remaining_gap_to_floor": None,
        "base_group_max_entry_gain": None,
        "structure_group_max_entry_gain": None,
        "best_single_component": None,
        "single_component_floor_crossers": [],
        "components_by_headroom": [],
        "bias50_floor_counterfactual": {
            "entry_if_bias50_fully_relaxed": None,
            "layers_if_bias50_fully_relaxed": None,
            "required_bias50_cap_for_floor": None,
            "current_bias50_value": None,
        },
        "unavailable_reason": reason,
        "runtime_blocker": blocker or None,
    }


def _component_gap_attribution(eq_components: dict[str, Any], q35_counterfactuals: dict[str, Any]) -> dict[str, Any]:
    runtime_trade_floor = float(eq_components.get("trade_floor") or 0.55)
    runtime_entry_quality = float(eq_components.get("entry_quality") or 0.0)
    base_outer = float(eq_components.get("base_quality_weight") or 1.0)
    structure_outer = float(eq_components.get("structure_quality_weight") or 0.0)

    analysis_components = dict(eq_components or {})
    q15_patch = analysis_components.get("q15_exact_supported_component_patch") or {}
    reconstructed_from_q15_patch = False
    if isinstance(q15_patch, dict) and q15_patch.get("applied"):
        patch_feature = str(q15_patch.get("feature") or "")
        original_score = _safe_float(q15_patch.get("original_normalized_score"))
        if patch_feature and original_score is not None:
            base_components = [dict(item) for item in (analysis_components.get("base_components") or [])]
            for item in base_components:
                if str(item.get("feature") or "") != patch_feature:
                    continue
                weight = float(item.get("weight") or 0.0)
                item["normalized_score"] = original_score
                item["weighted_contribution"] = _safe_round(weight * original_score)
                break
            analysis_components["base_components"] = base_components
            base_quality = sum(
                float(item.get("weight") or 0.0) * float(item.get("normalized_score") or 0.0)
                for item in base_components
            )
            structure_quality = float(analysis_components.get("structure_quality") or 0.0)
            baseline_entry_quality = base_outer * base_quality + structure_outer * structure_quality
            analysis_components["base_quality"] = _safe_round(base_quality)
            analysis_components["entry_quality"] = _safe_round(baseline_entry_quality)
            analysis_components["trade_floor_gap"] = _safe_round(baseline_entry_quality - runtime_trade_floor)
            reconstructed_from_q15_patch = True

    trade_floor = float(analysis_components.get("trade_floor") or runtime_trade_floor)
    entry_quality = float(analysis_components.get("entry_quality") or 0.0)
    floor_gap = max(0.0, trade_floor - entry_quality)

    components: list[dict[str, Any]] = []
    for group_name, outer_weight, items in (
        ("base", base_outer, analysis_components.get("base_components") or []),
        ("structure", structure_outer, analysis_components.get("structure_components") or []),
    ):
        for item in items:
            weight = float(item.get("weight") or 0.0)
            score = float(item.get("normalized_score") or 0.0)
            effective_weight = outer_weight * weight
            max_entry_gain = max(0.0, effective_weight * (1.0 - score))
            required_score_delta = None
            if floor_gap > 0 and effective_weight > 0:
                required_score_delta = floor_gap / effective_weight
            can_single_component_cross = bool(required_score_delta is not None and required_score_delta <= (1.0 - score) + 1e-9)
            components.append(
                {
                    "group": group_name,
                    "feature": item.get("feature"),
                    "raw_value": item.get("raw_value"),
                    "normalized_score": _safe_round(score),
                    "weight": _safe_round(weight),
                    "outer_weight": _safe_round(outer_weight),
                    "effective_weight": _safe_round(effective_weight),
                    "weighted_contribution": item.get("weighted_contribution"),
                    "headroom_to_perfect_score": _safe_round(1.0 - score),
                    "max_entry_gain_if_perfect": _safe_round(max_entry_gain),
                    "required_score_delta_to_cross_floor": _safe_round(required_score_delta) if required_score_delta is not None else None,
                    "can_single_component_cross_floor": can_single_component_cross,
                }
            )

    sortable = [
        c for c in components
        if c.get("required_score_delta_to_cross_floor") is not None
    ]
    best_single = None
    if sortable:
        best_single = sorted(
            sortable,
            key=lambda c: (
                0 if c.get("can_single_component_cross_floor") else 1,
                c.get("required_score_delta_to_cross_floor"),
                -float(c.get("max_entry_gain_if_perfect") or 0.0),
            ),
        )[0]

    group_headroom = {
        "base": _safe_round(sum(float(c.get("max_entry_gain_if_perfect") or 0.0) for c in components if c.get("group") == "base")),
        "structure": _safe_round(sum(float(c.get("max_entry_gain_if_perfect") or 0.0) for c in components if c.get("group") == "structure")),
    }
    components_sorted = sorted(
        components,
        key=lambda c: (
            -(float(c.get("max_entry_gain_if_perfect") or 0.0)),
            c.get("feature") or "",
        ),
    )
    ordered_crossers = [
        c for c in sorted(
            sortable,
            key=lambda c: (
                0 if c.get("can_single_component_cross_floor") else 1,
                c.get("required_score_delta_to_cross_floor"),
            ),
        )
        if c.get("can_single_component_cross_floor")
    ]

    return {
        "trade_floor": _safe_round(trade_floor),
        "entry_quality": _safe_round(entry_quality),
        "remaining_gap_to_floor": _safe_round(floor_gap),
        "reconstructed_from_q15_patch": reconstructed_from_q15_patch,
        "runtime_entry_quality_after_patch": _safe_round(runtime_entry_quality) if reconstructed_from_q15_patch else None,
        "runtime_trade_floor_gap_after_patch": _safe_round(runtime_entry_quality - runtime_trade_floor) if reconstructed_from_q15_patch else None,
        "base_group_max_entry_gain": group_headroom["base"],
        "structure_group_max_entry_gain": group_headroom["structure"],
        "best_single_component": best_single,
        "single_component_floor_crossers": ordered_crossers,
        "components_by_headroom": components_sorted,
        "bias50_floor_counterfactual": {
            "entry_if_bias50_fully_relaxed": q35_counterfactuals.get("entry_if_bias50_fully_relaxed"),
            "layers_if_bias50_fully_relaxed": q35_counterfactuals.get("layers_if_bias50_fully_relaxed"),
            "required_bias50_cap_for_floor": q35_counterfactuals.get("required_bias50_cap_for_floor"),
            "current_bias50_value": q35_counterfactuals.get("current_bias50_value"),
        },
    }


def main() -> None:
    payload = json.loads(PROBE_PATH.read_text(encoding="utf-8"))
    diags = payload.get("decision_quality_scope_diagnostics") or {}
    consensus = diags.get("pathology_consensus") or {}
    scope_pathology_summary = payload.get("decision_quality_scope_pathology_summary")
    if not isinstance(scope_pathology_summary, dict):
        scope_pathology_summary = build_live_pathology_scope_surface(
            payload,
            diags if isinstance(diags, dict) else {},
            artifact_path=BULL_4H_POCKET_ABLATION_PATH,
        )
    recommended_patch = (
        scope_pathology_summary.get("recommended_patch")
        if isinstance(scope_pathology_summary, dict)
        else None
    )
    runtime_blocker = _runtime_blocker_summary(payload)
    deployment_blocker = _deployment_blocker_summary(payload)

    chosen_scope = str(payload.get("decision_quality_calibration_scope") or "unknown")
    exact_scope_name = "regime_label+regime_gate+entry_quality_label"
    narrow_scope_name = "regime_label+entry_quality_label"
    broad_scope_name = "regime_gate+entry_quality_label"

    entry_quality_components = payload.get("entry_quality_components") or {}
    q35_counterfactuals = _load_q35_audit_counterfactuals()
    if entry_quality_components:
        component_gap_attribution = _component_gap_attribution(entry_quality_components, q35_counterfactuals)
    else:
        component_gap_attribution = _unavailable_component_gap_attribution(
            (runtime_blocker or {}).get("reason") or "entry_quality_components unavailable for current live row",
            blocker=runtime_blocker,
        )

    q15_patch_meta = (entry_quality_components.get("q15_exact_supported_component_patch") or {}) if isinstance(entry_quality_components, dict) else {}

    report = {
        "generated_at": payload.get("feature_timestamp"),
        "target_col": payload.get("target_col"),
        "signal": payload.get("signal"),
        "confidence": payload.get("confidence"),
        "should_trade": payload.get("should_trade"),
        "regime_label": payload.get("regime_label"),
        "regime_gate": payload.get("regime_gate"),
        "entry_quality": payload.get("entry_quality"),
        "entry_quality_label": payload.get("entry_quality_label"),
        "entry_quality_components": entry_quality_components,
        "component_gap_attribution": component_gap_attribution,
        "runtime_blocker": runtime_blocker,
        "deployment_blocker": deployment_blocker,
        "allowed_layers_raw": payload.get("allowed_layers_raw"),
        "allowed_layers_raw_reason": payload.get("allowed_layers_raw_reason"),
        "allowed_layers": payload.get("allowed_layers"),
        "allowed_layers_reason": payload.get("allowed_layers_reason"),
        "execution_guardrail_reason": payload.get("execution_guardrail_reason"),
        "q15_exact_supported_component_patch_applied": bool(payload.get("q15_exact_supported_component_patch_applied")),
        "q15_exact_supported_component_patch": q15_patch_meta or None,
        "runtime_closure_state": payload.get("runtime_closure_state"),
        "runtime_closure_summary": payload.get("runtime_closure_summary"),
        "support_route_verdict": payload.get("support_route_verdict"),
        "floor_cross_verdict": payload.get("floor_cross_verdict"),
        "chosen_scope": chosen_scope,
        "chosen_scope_summary": _scope_summary(chosen_scope, diags.get(chosen_scope) or {}),
        "exact_live_lane_summary": _scope_summary(exact_scope_name, diags.get(exact_scope_name) or {}),
        "narrow_same_regime_summary": _scope_summary(narrow_scope_name, diags.get(narrow_scope_name) or {}),
        "broad_same_gate_summary": _scope_summary(broad_scope_name, diags.get(broad_scope_name) or {}),
        "recent_pathology_reason": payload.get("decision_quality_recent_pathology_reason"),
        "recent_pathology_summary": payload.get("decision_quality_recent_pathology_summary"),
        "shared_top_shift_features": consensus.get("shared_top_shift_features") or [],
        "worst_pathology_scope": consensus.get("worst_pathology_scope") or {},
        "decision_quality_scope_pathology_summary": scope_pathology_summary,
        "recommended_patch": recommended_patch,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    shared = report["shared_top_shift_features"]
    shared_text = ", ".join(
        f"{item.get('feature')} (x{item.get('scope_count')})" for item in shared
    ) or "None"
    chosen = report["chosen_scope_summary"]
    exact = report["exact_live_lane_summary"]
    narrow = report["narrow_same_regime_summary"]
    broad = report["broad_same_gate_summary"]
    worst = report["worst_pathology_scope"]
    eq_components = report.get("entry_quality_components") or {}
    gap_attr = report.get("component_gap_attribution") or {}
    base_components = eq_components.get("base_components") or []
    structure_components = eq_components.get("structure_components") or []
    best_component = gap_attr.get("best_single_component") or {}
    crossers = gap_attr.get("single_component_floor_crossers") or []
    bias50_cf = gap_attr.get("bias50_floor_counterfactual") or {}
    q15_patch = report.get("q15_exact_supported_component_patch") or {}
    q15_patch_machine_read = q15_patch.get("machine_read_answer") or {}
    recommended_patch = report.get("recommended_patch") or {}
    recommended_patch_features = ", ".join(recommended_patch.get("collapse_features") or []) or "None"
    recommended_patch_status = recommended_patch.get("status") or "None"
    recommended_patch_profile = recommended_patch.get("recommended_profile") or "None"
    runtime_closure_state = report.get("runtime_closure_state") or (
        "support_closed_but_trade_floor_blocked"
        if (
            report.get("deployment_blocker") == "decision_quality_below_trade_floor"
            and report.get("support_route_verdict") == "exact_bucket_supported"
            and not report.get("q15_exact_supported_component_patch_applied")
        )
        else (
            "capacity_opened_signal_hold"
            if report.get("q15_exact_supported_component_patch_applied") and report.get("signal") == "HOLD" and (report.get("allowed_layers") or 0) > 0
            else (
                "patch_active_but_execution_blocked"
                if report.get("q15_exact_supported_component_patch_applied")
                else "patch_inactive_or_blocked"
            )
        )
    )
    runtime_closure_summary = report.get("runtime_closure_summary") or (
        (
            f"current live bucket {report.get('current_live_structure_bucket') or report.get('structure_bucket') or 'unknown_bucket'} 已完成 exact support closure"
            + (
                f"（{(report.get('support_progress') or {}).get('current_rows')}/{(report.get('support_progress') or {}).get('minimum_support_rows')}）"
                if isinstance(report.get('support_progress'), dict)
                and (report.get('support_progress') or {}).get('current_rows') is not None
                and (report.get('support_progress') or {}).get('minimum_support_rows') is not None
                else ""
            )
            + f"，但 top-level live baseline 仍停在 entry_quality={float(report.get('entry_quality') or 0.0):.4f} ({report.get('entry_quality_label') or '—'})"
            + (
                f" < trade floor {float((report.get('entry_quality_components') or {}).get('trade_floor')):.2f}"
                if isinstance(report.get('entry_quality_components'), dict)
                and (report.get('entry_quality_components') or {}).get('trade_floor') is not None
                else ""
            )
            + "；目前維持明確 no-deploy governance，不可把 support closure 誤讀成 deployment closure。"
        )
        if (
            report.get("deployment_blocker") == "decision_quality_below_trade_floor"
            and report.get("support_route_verdict") == "exact_bucket_supported"
            and not report.get("q15_exact_supported_component_patch_applied")
        )
        else (
            "capacity opened but signal still HOLD"
            if report.get("q15_exact_supported_component_patch_applied") and report.get("signal") == "HOLD" and (report.get("allowed_layers") or 0) > 0
            else (
                "patch active but execution still blocked"
                if report.get("q15_exact_supported_component_patch_applied")
                else "patch inactive or still blocked"
            )
        )
    )
    base_component_text = ", ".join(
        f"{item.get('feature')}={item.get('normalized_score')} (w={item.get('weight')}, contrib={item.get('weighted_contribution')})"
        for item in base_components
    ) or "None"
    structure_component_text = ", ".join(
        f"{item.get('feature')}={item.get('normalized_score')} (w={item.get('weight')}, contrib={item.get('weighted_contribution')})"
        for item in structure_components
    ) or "None"
    crosser_text = ", ".join(
        f"{item.get('feature')} (Δscore≈{item.get('required_score_delta_to_cross_floor')})"
        for item in crossers[:4]
    ) or "None"

    lines = [
        "# Live Decision-Quality Drilldown",
        "",
        f"- feature_timestamp: **{report['generated_at']}**",
        f"- target: `{report['target_col']}`",
        f"- live path: **{report['regime_label']} / {report['regime_gate']} / {report['entry_quality_label']}**",
        f"- signal: **{report['signal']}** @ confidence **{report['confidence']:.4f}**",
        f"- layers: **{report['allowed_layers_raw']} → {report['allowed_layers']}**",
        f"- allowed_layers_raw_reason: `{report['allowed_layers_raw_reason']}`",
        f"- allowed_layers_reason: `{report['allowed_layers_reason']}`",
        f"- execution_guardrail_reason: `{report['execution_guardrail_reason']}`",
        f"- runtime_blocker: `{(runtime_blocker or {}).get('type')}` | reason: `{(runtime_blocker or {}).get('reason')}`",
        f"- deployment_blocker: `{(deployment_blocker or {}).get('type')}` | reason: `{(deployment_blocker or {}).get('reason')}`",
        f"- q15 exact-supported patch: **{'active' if report['q15_exact_supported_component_patch_applied'] else 'inactive'}** | support_route `{report.get('support_route_verdict')}` | floor_cross `{report.get('floor_cross_verdict')}`",
        f"- runtime closure summary: **{runtime_closure_summary}**",
        f"- q15 patch machine-read: support_ready={q15_patch_machine_read.get('support_ready')} / entry_quality_ge_0_55={q15_patch_machine_read.get('entry_quality_ge_0_55')} / allowed_layers_gt_0={q15_patch_machine_read.get('allowed_layers_gt_0')} / preserves_positive_discrimination_status=`{q15_patch_machine_read.get('preserves_positive_discrimination_status')}`",
        f"- recommended_patch: **{recommended_patch_profile}** / status `{recommended_patch_status}` / support_route `{recommended_patch.get('support_route_verdict')}` / gap `{recommended_patch.get('gap_to_minimum')}`",
        f"- recommended_patch_features: {recommended_patch_features}",
        f"- recommended_patch_reason: {recommended_patch.get('reason')}",
        f"- recommended_patch_action: {recommended_patch.get('recommended_action')}",
        "",
        "## Entry-quality component breakdown",
        "",
        f"- final entry_quality: **{eq_components.get('entry_quality')}** / trade_floor **{eq_components.get('trade_floor')}** / gap **{eq_components.get('trade_floor_gap')}**",
        f"- base_quality: **{eq_components.get('base_quality')}** × weight **{eq_components.get('base_quality_weight')}**",
        f"- structure_quality: **{eq_components.get('structure_quality')}** × weight **{eq_components.get('structure_quality_weight')}**",
        f"- base components: {base_component_text}",
        f"- structure components: {structure_component_text}",
        "",
        "## Gap attribution（哪個 component 真正在卡 floor）",
        "",
        f"- remaining_gap_to_floor: **{gap_attr.get('remaining_gap_to_floor')}**",
        f"- base_group_max_entry_gain: **{gap_attr.get('base_group_max_entry_gain')}** | structure_group_max_entry_gain: **{gap_attr.get('structure_group_max_entry_gain')}**",
        f"- best_single_component: **{best_component.get('feature')}**（group={best_component.get('group')}, Δscore≈{best_component.get('required_score_delta_to_cross_floor')}, max_gain≈{best_component.get('max_entry_gain_if_perfect')}）",
        f"- single-component floor crossers: {crosser_text}",
        f"- bias50 fully relaxed: entry≈**{bias50_cf.get('entry_if_bias50_fully_relaxed')}** / layers≈**{bias50_cf.get('layers_if_bias50_fully_relaxed')}** / required_bias50_cap≈**{bias50_cf.get('required_bias50_cap_for_floor')}**",
        f"- unavailable_reason: `{gap_attr.get('unavailable_reason')}`",
        "",
        "## Scope comparison",
        "",
        "| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
        f"| chosen `{chosen_scope}` | {chosen.get('rows', 0)} | {chosen.get('win_rate')} | {chosen.get('avg_quality')} | {chosen.get('avg_drawdown_penalty')} | {chosen.get('avg_time_underwater')} | {chosen.get('current_live_structure_bucket_rows')} | {chosen.get('recent_pathology_applied')} |",
        f"| exact `{exact_scope_name}` | {exact.get('rows', 0)} | {exact.get('win_rate')} | {exact.get('avg_quality')} | {exact.get('avg_drawdown_penalty')} | {exact.get('avg_time_underwater')} | {exact.get('current_live_structure_bucket_rows')} | {exact.get('recent_pathology_applied')} |",
        f"| narrow `{narrow_scope_name}` | {narrow.get('rows', 0)} | {narrow.get('win_rate')} | {narrow.get('avg_quality')} | {narrow.get('avg_drawdown_penalty')} | {narrow.get('avg_time_underwater')} | {narrow.get('current_live_structure_bucket_rows')} | {narrow.get('recent_pathology_applied')} |",
        f"| broad `{broad_scope_name}` | {broad.get('rows', 0)} | {broad.get('win_rate')} | {broad.get('avg_quality')} | {broad.get('avg_drawdown_penalty')} | {broad.get('avg_time_underwater')} | {broad.get('current_live_structure_bucket_rows')} | {broad.get('recent_pathology_applied')} |",
        "",
        "## Shared shifts",
        "",
        f"- {shared_text}",
        f"- worst_pathology_scope: **{worst.get('scope')}** rows={worst.get('rows')} win_rate={worst.get('win_rate')} quality={worst.get('avg_quality')}",
        "",
        "## Interpretation",
        "",
        "- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.",
        "- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.",
        "- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.",
        "- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.",
        "- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.",
        "- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.",
    ]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "json": str(OUT_JSON),
        "markdown": str(OUT_MD),
        "chosen_scope": chosen_scope,
        "worst_pathology_scope": worst.get("scope"),
        "runtime_blocker": (runtime_blocker or {}).get("type"),
        "runtime_blocker_reason": (runtime_blocker or {}).get("reason"),
        "deployment_blocker": (deployment_blocker or {}).get("type"),
        "deployment_blocker_reason": (deployment_blocker or {}).get("reason"),
        "q15_exact_supported_component_patch_applied": report.get("q15_exact_supported_component_patch_applied"),
        "runtime_closure_state": runtime_closure_state,
        "runtime_closure_summary": runtime_closure_summary,
        "signal": report.get("signal"),
        "allowed_layers": report.get("allowed_layers"),
        "allowed_layers_reason": report.get("allowed_layers_reason"),
        "support_route_verdict": report.get("support_route_verdict"),
        "recommended_patch_profile": recommended_patch_profile,
        "recommended_patch_status": recommended_patch_status,
        "recommended_patch_support_route": recommended_patch.get("support_route_verdict"),
        "recommended_patch_gap_to_minimum": recommended_patch.get("gap_to_minimum"),
        "remaining_gap_to_floor": gap_attr.get("remaining_gap_to_floor"),
        "best_single_component": (best_component.get("feature") if best_component else None),
        "best_single_component_required_score_delta": (best_component.get("required_score_delta_to_cross_floor") if best_component else None),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
