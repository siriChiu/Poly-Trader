#!/usr/bin/env python3
"""Audit the current q15 live bucket support route and floor-cross legality.

Purpose:
- answer whether the current q15 live path is blocked by missing exact support,
  insufficient score, or both
- convert existing artifacts into a machine-readable governance verdict
- explicitly state whether `feat_4h_bias50` can *legally* release the floor gap
  for the current live row

Inputs:
- data/live_predict_probe.json
- data/live_decision_quality_drilldown.json
- data/bull_4h_pocket_ablation.json
- data/leaderboard_feature_profile_probe.json (optional, for support_governance_route)

Outputs:
- data/q15_support_audit.json
- docs/analysis/q15_support_audit.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
DRILLDOWN_PATH = PROJECT_ROOT / "data" / "live_decision_quality_drilldown.json"
BULL_POCKET_PATH = PROJECT_ROOT / "data" / "bull_4h_pocket_ablation.json"
LEADERBOARD_PROBE_PATH = PROJECT_ROOT / "data" / "leaderboard_feature_profile_probe.json"
OUT_JSON = PROJECT_ROOT / "data" / "q15_support_audit.json"
OUT_MD = PROJECT_ROOT / "docs" / "analysis" / "q15_support_audit.md"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _as_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _support_route_decision(
    current_bucket_rows: int,
    minimum_support_rows: int,
    exact_bucket_proxy_rows: int,
    exact_lane_proxy_rows: int,
    supported_neighbor_rows: int,
    exact_bucket_root_cause: str,
    preferred_support_cohort: str | None,
    support_governance_route: str | None,
) -> dict[str, Any]:
    if current_bucket_rows >= minimum_support_rows:
        return {
            "verdict": "exact_bucket_supported",
            "deployable": True,
            "governance_reference_only": False,
            "preferred_support_cohort": "exact_live_bucket",
            "reason": "current q15 exact bucket 已達 minimum support，可直接用 exact bucket 做 deployment 級驗證。",
            "release_condition": "保持 current_live_structure_bucket_rows >= minimum_support_rows，且 live row 仍通過 entry-quality / execution guardrail。",
        }

    route = str(support_governance_route or "")
    root = str(exact_bucket_root_cause or "")
    preferred = preferred_support_cohort or None

    if current_bucket_rows <= 0:
        if exact_bucket_proxy_rows > 0:
            exact_bucket_preferred = preferred
            if route == "exact_live_bucket_proxy_available" or not exact_bucket_preferred:
                exact_bucket_preferred = "bull_live_exact_bucket_proxy"
            return {
                "verdict": "exact_bucket_missing_proxy_reference_only",
                "deployable": False,
                "governance_reference_only": True,
                "preferred_support_cohort": exact_bucket_preferred,
                "reason": (
                    "current q15 exact bucket 仍為 0 rows；即使已有 exact-bucket proxy，也只能作治理參考，"
                    "不能作 deployment 放行證據。"
                ),
                "release_condition": (
                    "先把 current q15 exact bucket 補到 minimum support，再重查 entry floor；"
                    "proxy / neighbor 只能保留為比較與校準參考。"
                ),
                "route_hint": route or "exact_live_bucket_proxy_available",
            }
        if exact_lane_proxy_rows >= minimum_support_rows:
            return {
                "verdict": "exact_bucket_missing_exact_lane_proxy_only",
                "deployable": False,
                "governance_reference_only": True,
                "preferred_support_cohort": preferred or "bull_exact_live_lane_proxy",
                "reason": "current q15 exact bucket 缺樣本，只剩 same-lane proxy；這仍不足以解除 runtime blocker。",
                "release_condition": "必須先生成 current q15 exact bucket 真樣本，proxy 不可直接轉成 deployment allowance。",
                "route_hint": route or "exact_live_lane_proxy_only",
            }
        if supported_neighbor_rows >= minimum_support_rows:
            return {
                "verdict": "exact_bucket_missing_neighbor_reference_only",
                "deployable": False,
                "governance_reference_only": True,
                "preferred_support_cohort": preferred or "bull_supported_neighbor_buckets_proxy",
                "reason": "只有 neighbor bucket 有足夠支持；neighbor 只能當背景治理參考，不能替代 current q15 exact bucket。",
                "release_condition": "先補 current q15 exact bucket 真樣本，不能用 neighbor 直接解除 blocker。",
                "route_hint": route or "supported_neighbor_only",
            }

    if current_bucket_rows > 0 and current_bucket_rows < minimum_support_rows:
        return {
            "verdict": "exact_bucket_present_but_below_minimum",
            "deployable": False,
            "governance_reference_only": True,
            "preferred_support_cohort": preferred,
            "reason": "current q15 exact bucket 已出現，但 rows 尚未達 minimum support；仍需維持 blocker。",
            "release_condition": "exact bucket rows 達 minimum support 後，才可把 proxy 降級成純比較參考。",
            "route_hint": route or root or "exact_bucket_present_but_below_minimum",
        }

    return {
        "verdict": "insufficient_support_everywhere",
        "deployable": False,
        "governance_reference_only": True,
        "preferred_support_cohort": preferred,
        "reason": "current q15 live path 在 exact bucket / proxy / neighbor 都沒有 deployment 級支撐。",
        "release_condition": "先擴充 exact bucket 或縮小治理範圍，否則不得調整 runtime gate。",
        "route_hint": route or root or "insufficient_support_everywhere",
    }


def _floor_cross_legality(
    support_route: dict[str, Any],
    runtime_blocker: dict[str, Any] | None,
    remaining_gap_to_floor: float | None,
    best_single_component: dict[str, Any] | None,
) -> dict[str, Any]:
    if runtime_blocker:
        return {
            "verdict": "runtime_blocker_preempts_floor_analysis",
            "legal_to_relax_runtime_gate": False,
            "reason": f"目前先被 runtime blocker 擋下（{runtime_blocker.get('reason') or runtime_blocker.get('type')}），不能把 q15 floor-cross 當成當前 deploy 入口。",
        }

    gap = remaining_gap_to_floor
    component = best_single_component or {}
    feature = component.get("feature")
    can_cross = bool(component.get("can_single_component_cross_floor"))
    required_delta = component.get("required_score_delta_to_cross_floor")

    if gap is not None and gap <= 0:
        if support_route.get("deployable"):
            return {
                "verdict": "floor_already_crossed_and_support_ready",
                "legal_to_relax_runtime_gate": True,
                "reason": "當前 row 已跨過 trade floor，且 exact support 已達標；可進入正常 runtime guardrail 驗證。",
            }
        return {
            "verdict": "floor_crossed_but_support_not_ready",
            "legal_to_relax_runtime_gate": False,
            "reason": "即使 entry floor 已跨過，exact q15 support 仍未達標，不能把 proxy/neighbor 當 deployment 放行證據。",
        }

    if not support_route.get("deployable"):
        if can_cross and feature:
            return {
                "verdict": "math_cross_possible_but_illegal_without_exact_support",
                "legal_to_relax_runtime_gate": False,
                "reason": (
                    f"{feature} 在數學上可單點補足 floor gap（需要 score Δ≈{required_delta}），"
                    "但 current q15 exact support 尚未達 deployment 門檻，因此不得單靠 component calibration 解除 blocker。"
                ),
            }
        return {
            "verdict": "support_blocker_stands_before_component_fix",
            "legal_to_relax_runtime_gate": False,
            "reason": "目前先缺 q15 exact support；在 support 未補齊前，不得把 component-level 調整視為 deploy 放行。",
        }

    if can_cross and feature:
        return {
            "verdict": "legal_component_experiment_after_support_ready",
            "legal_to_relax_runtime_gate": True,
            "reason": (
                f"若 exact q15 support 已達標，則 {feature} 可作為下一輪優先 component experiment；"
                "但仍需通過 runtime guardrail 與回歸驗證。"
            ),
        }

    return {
        "verdict": "support_ready_but_component_insufficient",
        "legal_to_relax_runtime_gate": False,
        "reason": "即使 support 就緒，當前 component 頭寸仍不足以跨過 floor；不能直接放寬 runtime gate。",
    }


def build_report(
    probe: dict[str, Any],
    drilldown: dict[str, Any],
    bull_pocket: dict[str, Any],
    leaderboard_probe: dict[str, Any],
) -> dict[str, Any]:
    live_context = bull_pocket.get("live_context") or {}
    support_summary = bull_pocket.get("support_pathology_summary") or {}
    alignment = leaderboard_probe.get("alignment") or {}
    component_gap = drilldown.get("component_gap_attribution") or {}
    runtime_blocker = drilldown.get("runtime_blocker") or None
    best_single = component_gap.get("best_single_component") or None

    support_route = _support_route_decision(
        current_bucket_rows=_as_int(live_context.get("current_live_structure_bucket_rows"), 0),
        minimum_support_rows=_as_int(support_summary.get("minimum_support_rows"), 50),
        exact_bucket_proxy_rows=_as_int(alignment.get("bull_exact_live_bucket_proxy_rows"), 0),
        exact_lane_proxy_rows=_as_int(alignment.get("bull_exact_live_lane_proxy_rows"), 0),
        supported_neighbor_rows=_as_int(alignment.get("bull_support_neighbor_rows"), 0),
        exact_bucket_root_cause=str(support_summary.get("exact_bucket_root_cause") or ""),
        preferred_support_cohort=support_summary.get("preferred_support_cohort"),
        support_governance_route=alignment.get("support_governance_route"),
    )
    floor_legality = _floor_cross_legality(
        support_route=support_route,
        runtime_blocker=runtime_blocker,
        remaining_gap_to_floor=_as_float(component_gap.get("remaining_gap_to_floor")),
        best_single_component=best_single,
    )

    remaining_gap = _as_float(component_gap.get("remaining_gap_to_floor"))
    required_delta = (best_single or {}).get("required_score_delta_to_cross_floor")
    best_feature = (best_single or {}).get("feature")

    next_action = (
        "先補 current q15 exact bucket 真樣本到 minimum support，再重跑 live_decision_quality_drilldown / hb_q15_support_audit；"
        "在 support 未達標前，bias50 只能當 calibration research，不得解除 runtime blocker。"
    )
    if support_route.get("deployable") and floor_legality.get("legal_to_relax_runtime_gate"):
        next_action = (
            "exact support 已達標；下一輪可針對最佳 component 做保守 counterfactual 驗證，"
            "並以 pytest + fast heartbeat 驗證 runtime guardrail 不回歸。"
        )

    return {
        "generated_at": probe.get("feature_timestamp") or drilldown.get("generated_at"),
        "target_col": probe.get("target_col") or bull_pocket.get("target_col"),
        "current_live": {
            "signal": probe.get("signal"),
            "regime_label": probe.get("regime_label") or live_context.get("regime_label"),
            "regime_gate": probe.get("regime_gate") or live_context.get("regime_gate"),
            "entry_quality": probe.get("entry_quality"),
            "entry_quality_label": probe.get("entry_quality_label") or live_context.get("entry_quality_label"),
            "decision_quality_label": probe.get("decision_quality_label"),
            "allowed_layers": probe.get("allowed_layers"),
            "allowed_layers_reason": probe.get("allowed_layers_reason"),
            "execution_guardrail_reason": probe.get("execution_guardrail_reason") or live_context.get("execution_guardrail_reason"),
            "current_live_structure_bucket": live_context.get("current_live_structure_bucket"),
            "current_live_structure_bucket_rows": _as_int(live_context.get("current_live_structure_bucket_rows"), 0),
        },
        "support_route": {
            "support_governance_route": alignment.get("support_governance_route"),
            "preferred_support_cohort": support_route.get("preferred_support_cohort"),
            "verdict": support_route.get("verdict"),
            "deployable": support_route.get("deployable"),
            "governance_reference_only": support_route.get("governance_reference_only"),
            "reason": support_route.get("reason"),
            "release_condition": support_route.get("release_condition"),
            "route_hint": support_route.get("route_hint"),
            "minimum_support_rows": _as_int(support_summary.get("minimum_support_rows"), 50),
            "current_live_structure_bucket_gap_to_minimum": _as_int(support_summary.get("current_live_structure_bucket_gap_to_minimum"), 0),
            "exact_bucket_root_cause": support_summary.get("exact_bucket_root_cause"),
            "recommended_action": support_summary.get("recommended_action"),
            "exact_live_bucket_proxy_rows": _as_int(alignment.get("bull_exact_live_bucket_proxy_rows"), 0),
            "exact_live_lane_proxy_rows": _as_int(alignment.get("bull_exact_live_lane_proxy_rows"), 0),
            "supported_neighbor_rows": _as_int(alignment.get("bull_support_neighbor_rows"), 0),
        },
        "floor_cross_legality": {
            "verdict": floor_legality.get("verdict"),
            "legal_to_relax_runtime_gate": floor_legality.get("legal_to_relax_runtime_gate"),
            "reason": floor_legality.get("reason"),
            "remaining_gap_to_floor": remaining_gap,
            "best_single_component": best_feature,
            "best_single_component_required_score_delta": required_delta,
            "best_single_component_can_cross_floor": bool((best_single or {}).get("can_single_component_cross_floor")),
        },
        "component_gap_attribution": component_gap,
        "runtime_blocker": runtime_blocker,
        "next_action": next_action,
    }


def _markdown(report: dict[str, Any]) -> str:
    current = report.get("current_live") or {}
    support = report.get("support_route") or {}
    floor = report.get("floor_cross_legality") or {}
    return "\n".join(
        [
            "# q15 Support Audit",
            "",
            f"- generated_at: **{report.get('generated_at')}**",
            f"- target_col: **{report.get('target_col')}**",
            "",
            "## Current live row",
            f"- signal: **{current.get('signal')}**",
            f"- regime / gate / label: **{current.get('regime_label')} / {current.get('regime_gate')} / {current.get('entry_quality_label')}**",
            f"- current_live_structure_bucket: **{current.get('current_live_structure_bucket')}**",
            f"- current_live_structure_bucket_rows: **{current.get('current_live_structure_bucket_rows')}**",
            f"- allowed_layers: **{current.get('allowed_layers')}** ({current.get('allowed_layers_reason')})",
            f"- execution_guardrail_reason: **{current.get('execution_guardrail_reason')}**",
            "",
            "## Support route verdict",
            f"- support_governance_route: **{support.get('support_governance_route')}**",
            f"- verdict: **{support.get('verdict')}**",
            f"- deployable: **{support.get('deployable')}**",
            f"- governance_reference_only: **{support.get('governance_reference_only')}**",
            f"- preferred_support_cohort: **{support.get('preferred_support_cohort')}**",
            f"- current bucket gap to minimum: **{support.get('current_live_structure_bucket_gap_to_minimum')}**",
            f"- exact-bucket proxy rows: **{support.get('exact_live_bucket_proxy_rows')}**",
            f"- exact-lane proxy rows: **{support.get('exact_live_lane_proxy_rows')}**",
            f"- supported neighbor rows: **{support.get('supported_neighbor_rows')}**",
            f"- reason: {support.get('reason')}",
            f"- release_condition: {support.get('release_condition')}",
            "",
            "## Floor-cross legality",
            f"- verdict: **{floor.get('verdict')}**",
            f"- legal_to_relax_runtime_gate: **{floor.get('legal_to_relax_runtime_gate')}**",
            f"- remaining_gap_to_floor: **{floor.get('remaining_gap_to_floor')}**",
            f"- best_single_component: **{floor.get('best_single_component')}**",
            f"- best_single_component_required_score_delta: **{floor.get('best_single_component_required_score_delta')}**",
            f"- best_single_component_can_cross_floor: **{floor.get('best_single_component_can_cross_floor')}**",
            f"- reason: {floor.get('reason')}",
            "",
            "## Next action",
            f"- {report.get('next_action')}",
            "",
        ]
    )


def main() -> None:
    probe = _load_json(PROBE_PATH)
    drilldown = _load_json(DRILLDOWN_PATH)
    bull_pocket = _load_json(BULL_POCKET_PATH)
    leaderboard_probe = _load_json(LEADERBOARD_PROBE_PATH)

    report = build_report(probe, drilldown, bull_pocket, leaderboard_probe)
    markdown = _markdown(report)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(markdown + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "json": str(OUT_JSON),
                "markdown": str(OUT_MD),
                "support_route_verdict": (report.get("support_route") or {}).get("verdict"),
                "support_route_deployable": (report.get("support_route") or {}).get("deployable"),
                "floor_cross_verdict": (report.get("floor_cross_legality") or {}).get("verdict"),
                "legal_to_relax_runtime_gate": (report.get("floor_cross_legality") or {}).get("legal_to_relax_runtime_gate"),
                "remaining_gap_to_floor": (report.get("floor_cross_legality") or {}).get("remaining_gap_to_floor"),
                "best_single_component": (report.get("floor_cross_legality") or {}).get("best_single_component"),
                "best_single_component_required_score_delta": (report.get("floor_cross_legality") or {}).get("best_single_component_required_score_delta"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
