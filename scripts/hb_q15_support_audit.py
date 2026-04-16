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

import contextlib
import importlib.util
import io
import json
import os
from datetime import datetime, timezone
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


def _parse_isoish_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _probe_and_drilldown_in_sync(probe: dict[str, Any], drilldown: dict[str, Any]) -> bool:
    probe_ts = _parse_isoish_timestamp(probe.get("feature_timestamp"))
    drilldown_ts = _parse_isoish_timestamp(drilldown.get("generated_at"))
    if probe_ts is None or drilldown_ts is None:
        return False
    return abs((probe_ts - drilldown_ts).total_seconds()) < 1


def _refresh_live_drilldown_if_needed(probe: dict[str, Any], drilldown: dict[str, Any]) -> dict[str, Any]:
    if not probe:
        return drilldown
    if drilldown and _probe_and_drilldown_in_sync(probe, drilldown):
        return drilldown

    script_path = PROJECT_ROOT / "scripts" / "live_decision_quality_drilldown.py"
    if not script_path.exists():
        return drilldown

    try:
        spec = importlib.util.spec_from_file_location("live_decision_quality_drilldown_runtime", script_path)
        if spec is None or spec.loader is None:
            return drilldown
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with contextlib.redirect_stdout(io.StringIO()):
            module.main()
    except Exception:
        return drilldown

    refreshed = _load_json(DRILLDOWN_PATH)
    return refreshed or drilldown


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


def _extract_q15_support_diag(payload: dict[str, Any]) -> dict[str, Any]:
    return (
        payload.get("q15_support_audit")
        or payload.get("q15_support_audit_diagnostics")
        or {}
    )



def _load_recent_q15_support_history(
    *,
    current_entry: dict[str, Any],
    data_dir: Path | None = None,
) -> list[dict[str, Any]]:
    summaries_dir = data_dir or (PROJECT_ROOT / "data")
    summary_files = sorted(
        summaries_dir.glob("heartbeat_*_summary.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    history = [current_entry]
    current_timestamp = current_entry.get("observed_at")
    if isinstance(current_timestamp, datetime):
        current_observed_at = current_timestamp
    else:
        current_observed_at = None

    for path in summary_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        diag = _extract_q15_support_diag(payload)
        current_live = diag.get("current_live") or {}
        support_route = diag.get("support_route") or {}
        payload_timestamp = payload.get("timestamp") or diag.get("generated_at")
        payload_dt = None
        if payload_timestamp:
            try:
                payload_dt = datetime.fromisoformat(str(payload_timestamp).replace("Z", "+00:00"))
                if payload_dt.tzinfo is None:
                    payload_dt = payload_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                payload_dt = None
        if (
            current_observed_at is not None
            and payload_dt is not None
            and abs((current_observed_at - payload_dt).total_seconds()) < 120
        ):
            continue
        candidate = {
            "heartbeat": str(payload.get("heartbeat") or path.stem),
            "timestamp": payload_timestamp,
            "live_current_structure_bucket": current_live.get("current_live_structure_bucket"),
            "live_current_structure_bucket_rows": int(current_live.get("current_live_structure_bucket_rows") or 0),
            "minimum_support_rows": int(support_route.get("minimum_support_rows") or 0),
            "support_route_verdict": support_route.get("verdict"),
            "support_governance_route": support_route.get("support_governance_route"),
        }
        if not candidate["live_current_structure_bucket"]:
            continue
        history.append(candidate)
    return [
        {key: value for key, value in item.items() if key != "observed_at"}
        for item in history
    ]


def _summarize_support_progress(
    *,
    current_bucket: Any,
    support_route_verdict: str | None,
    support_governance_route: str | None,
    live_bucket_rows: Any,
    minimum_support_rows: int,
    current_label: str | None,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    current_rows = int(live_bucket_rows or 0)
    observed_at = datetime.now(timezone.utc)
    current_entry = {
        "heartbeat": str(current_label or "current"),
        "timestamp": observed_at.isoformat(),
        "observed_at": observed_at,
        "live_current_structure_bucket": current_bucket,
        "live_current_structure_bucket_rows": current_rows,
        "minimum_support_rows": int(minimum_support_rows or 0),
        "support_route_verdict": support_route_verdict,
        "support_governance_route": support_governance_route,
    }
    history = _load_recent_q15_support_history(current_entry=current_entry, data_dir=data_dir)
    same_bucket_history = [
        item
        for item in history
        if item.get("live_current_structure_bucket") == current_bucket
    ]
    relevant = same_bucket_history[:5]
    previous = relevant[1] if len(relevant) > 1 else None
    delta_vs_previous = None
    previous_route_changed = False
    if previous is not None:
        previous_rows = int(previous.get("live_current_structure_bucket_rows") or 0)
        delta_vs_previous = current_rows - previous_rows
        previous_route_changed = (
            previous.get("support_route_verdict") != support_route_verdict
            or previous.get("support_governance_route") != support_governance_route
        )

    stagnant_run_count = 0
    if previous is not None and int(previous.get("live_current_structure_bucket_rows") or 0) == current_rows:
        stagnant_run_count = 1
        for item in relevant[1:]:
            if int(item.get("live_current_structure_bucket_rows") or 0) == current_rows:
                stagnant_run_count += 1
                continue
            break

    minimum = int(minimum_support_rows or 0)
    if current_rows >= minimum:
        status = "exact_supported"
        reason = "current q15 exact bucket 已達 minimum support，可轉向 exact-supported deployment verify。"
    elif previous is None:
        status = "no_recent_comparable_history"
        reason = "目前找不到同一 q15 bucket 的最近 heartbeat 可比較；先持續累積 exact support。"
    elif delta_vs_previous and delta_vs_previous > 0:
        status = "accumulating"
        reason = "current q15 exact support 仍低於 minimum，但同 bucket rows 較上一輪增加。"
        if previous_route_changed:
            reason += " route 已切換，代表 support pathology 正在從缺樣本轉向 exact rows 累積。"
    elif delta_vs_previous == 0:
        status = "stalled_under_minimum"
        reason = "current q15 exact support 連續 heartbeat 停在同一數量，屬於 support accumulation 停滯。"
    else:
        status = "regressed_under_minimum"
        reason = "current q15 exact support 較上一輪回落，需檢查 current bucket / support artifact 是否切換或退化。"

    return {
        "status": status,
        "reason": reason,
        "current_rows": current_rows,
        "minimum_support_rows": minimum,
        "gap_to_minimum": max(minimum - current_rows, 0),
        "delta_vs_previous": delta_vs_previous,
        "previous_rows": None if previous is None else int(previous.get("live_current_structure_bucket_rows") or 0),
        "previous_route_changed": previous_route_changed,
        "previous_support_route_verdict": None if previous is None else previous.get("support_route_verdict"),
        "previous_support_governance_route": None if previous is None else previous.get("support_governance_route"),
        "stagnant_run_count": stagnant_run_count,
        "stalled_support_accumulation": status == "stalled_under_minimum",
        "escalate_to_blocker": status == "stalled_under_minimum" and stagnant_run_count >= 3,
        "history": relevant,
    }


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


def _resolve_current_live_context(
    probe: dict[str, Any],
    drilldown: dict[str, Any],
    bull_pocket: dict[str, Any],
) -> dict[str, Any]:
    probe_scopes = (probe.get("decision_quality_scope_diagnostics") or {}) if isinstance(probe, dict) else {}
    exact_scope = probe_scopes.get("regime_label+regime_gate+entry_quality_label") or {}
    chosen_scope = (drilldown.get("chosen_scope_summary") or {}) if isinstance(drilldown, dict) else {}
    bull_live = (bull_pocket.get("live_context") or {}) if isinstance(bull_pocket, dict) else {}

    current_bucket = (
        exact_scope.get("current_live_structure_bucket")
        or chosen_scope.get("current_live_structure_bucket")
        or bull_live.get("current_live_structure_bucket")
    )
    current_bucket_rows = _as_int(
        exact_scope.get("current_live_structure_bucket_rows"),
        _as_int(chosen_scope.get("current_live_structure_bucket_rows"), _as_int(bull_live.get("current_live_structure_bucket_rows"), 0)),
    )
    if "execution_guardrail_reason" in probe:
        execution_guardrail_reason = probe.get("execution_guardrail_reason")
    else:
        execution_guardrail_reason = (
            drilldown.get("execution_guardrail_reason")
            or bull_live.get("execution_guardrail_reason")
        )
    return {
        "regime_label": probe.get("regime_label") or bull_live.get("regime_label"),
        "regime_gate": probe.get("regime_gate") or bull_live.get("regime_gate"),
        "entry_quality_label": probe.get("entry_quality_label") or bull_live.get("entry_quality_label"),
        "current_live_structure_bucket": current_bucket,
        "current_live_structure_bucket_rows": current_bucket_rows,
        "execution_guardrail_reason": execution_guardrail_reason,
    }


def _scope_applicability(live_context: dict[str, Any]) -> dict[str, Any]:
    current_bucket = str(live_context.get("current_live_structure_bucket") or "")
    target_bucket = "CAUTION|structure_quality_caution|q15"
    if not current_bucket:
        return {
            "status": "unknown_current_live_bucket",
            "active_for_current_live_row": False,
            "current_structure_bucket": None,
            "target_structure_bucket": target_bucket,
            "reason": "無法判定 current live structure bucket，q15 support audit 只能保留為背景治理資訊。",
        }
    if current_bucket.endswith("|q15"):
        return {
            "status": "current_live_q15_lane_active",
            "active_for_current_live_row": True,
            "current_structure_bucket": current_bucket,
            "target_structure_bucket": target_bucket,
            "reason": "current live row 正位於 q15 lane；q15 support / component verify 可直接視為 current-live deployment 檢查。",
        }
    return {
        "status": "current_live_not_q15_lane",
        "active_for_current_live_row": False,
        "current_structure_bucket": current_bucket,
        "target_structure_bucket": target_bucket,
        "reason": "current live row 已不在 q15 lane；q15 support audit 只能描述 standby q15 route readiness，不可當成 current-live deployment closure。",
    }


def _component_experiment(
    support_route: dict[str, Any],
    floor_legality: dict[str, Any],
    component_gap: dict[str, Any],
    runtime_blocker: dict[str, Any] | None,
    scope_applicability: dict[str, Any],
) -> dict[str, Any]:
    best_single = component_gap.get("best_single_component") or {}
    feature = best_single.get("feature")
    remaining_gap = _as_float(component_gap.get("remaining_gap_to_floor"))
    bias50_counterfactual = component_gap.get("bias50_floor_counterfactual") or {}
    trade_floor = _as_float(component_gap.get("trade_floor"))
    entry_after = _as_float(bias50_counterfactual.get("entry_if_bias50_fully_relaxed"))
    layers_after = _as_int(bias50_counterfactual.get("layers_if_bias50_fully_relaxed"), 0)
    can_cross = bool(best_single.get("can_single_component_cross_floor"))
    required_delta = _as_float(best_single.get("required_score_delta_to_cross_floor"))

    if runtime_blocker:
        return {
            "verdict": "runtime_blocker_preempts_component_experiment",
            "feature": feature,
            "reason": f"目前先被 runtime blocker 擋下（{runtime_blocker.get('reason') or runtime_blocker.get('type')}），q15 component experiment 只能保留為背景研究。",
            "machine_read_answer": {
                "support_ready": bool(support_route.get("deployable")),
                "entry_quality_ge_0_55": False,
                "allowed_layers_gt_0": False,
                "preserves_positive_discrimination": None,
                "preserves_positive_discrimination_status": "not_measured_runtime_blocked",
            },
            "verify_next": "先清除 runtime blocker，再重跑 q15_support_audit / live_decision_quality_drilldown。",
        }

    if not support_route.get("deployable"):
        return {
            "verdict": "reference_only_until_exact_support_ready",
            "feature": feature,
            "reason": "exact support 尚未達 deployment 門檻；component experiment 只能作 reference-only 研究。",
            "machine_read_answer": {
                "support_ready": False,
                "entry_quality_ge_0_55": False,
                "allowed_layers_gt_0": False,
                "preserves_positive_discrimination": None,
                "preserves_positive_discrimination_status": "not_measured_support_missing",
            },
            "verify_next": "先把 current q15 exact bucket rows 補到 minimum support，再回來做 component experiment。",
        }

    if not feature:
        return {
            "verdict": "no_component_candidate",
            "feature": None,
            "reason": "component_gap_attribution 未提供最佳單點 component，無法形成 exact-supported experiment。",
            "machine_read_answer": {
                "support_ready": True,
                "entry_quality_ge_0_55": False,
                "allowed_layers_gt_0": False,
                "preserves_positive_discrimination": None,
                "preserves_positive_discrimination_status": "not_measured_no_candidate",
            },
            "verify_next": "先修復 live_decision_quality_drilldown 的 component gap attribution，再重跑 q15 audit。",
        }

    if not scope_applicability.get("active_for_current_live_row"):
        return {
            "verdict": "exact_supported_component_experiment_ready_but_current_live_not_q15",
            "feature": feature,
            "mode": "standby_q15_route",
            "remaining_gap_to_floor": remaining_gap,
            "required_score_delta_to_cross_floor": required_delta,
            "bias50_floor_counterfactual": bias50_counterfactual if feature == "feat_4h_bias50" else None,
            "reason": (
                f"exact q15 support 雖已達標，且 {feature} 仍是最佳 q15 component candidate；"
                "但 current live row 目前停在非 q15 bucket，故本 artifact 只能描述 standby q15 route readiness，"
                "不得當成 current-live deployment closure。"
            ),
            "machine_read_answer": {
                "support_ready": True,
                "entry_quality_ge_0_55": bool(can_cross),
                "allowed_layers_gt_0": bool(can_cross),
                "preserves_positive_discrimination": None,
                "preserves_positive_discrimination_status": "not_applicable_current_live_not_q15_lane",
                "active_for_current_live_row": False,
            },
            "verify_next": "若 live row 回到 q15 lane，再執行 q15 exact-supported deployment verify；目前應以 q35 current-live blocker 為主。",
        }

    entry_quality_ge_trade_floor = bool(can_cross)
    allowed_layers_gt_0 = bool(can_cross)
    experiment_mode = "single_component_headroom"
    if feature == "feat_4h_bias50" and entry_after is not None:
        if trade_floor is not None:
            entry_quality_ge_trade_floor = entry_after >= trade_floor
        allowed_layers_gt_0 = layers_after > 0
        experiment_mode = "bias50_floor_counterfactual"

    return {
        "verdict": "exact_supported_component_experiment_ready",
        "feature": feature,
        "mode": experiment_mode,
        "remaining_gap_to_floor": remaining_gap,
        "required_score_delta_to_cross_floor": required_delta,
        "bias50_floor_counterfactual": bias50_counterfactual if feature == "feat_4h_bias50" else None,
        "reason": (
            f"exact support 已達標，{feature} 可作為保守的 q15 component experiment；"
            "但是否保留正向 discrimination，仍需靠 pytest / fast heartbeat / live probe 做回歸驗證。"
        ),
        "machine_read_answer": {
            "support_ready": True,
            "entry_quality_ge_0_55": bool(entry_quality_ge_trade_floor),
            "allowed_layers_gt_0": bool(allowed_layers_gt_0),
            "preserves_positive_discrimination": None,
            "preserves_positive_discrimination_status": "not_measured_requires_followup_verify",
        },
        "verify_next": "用 exact-supported component patch + pytest + fast heartbeat 驗證 allowed_layers / execution_guardrail / live probe 是否仍一致。",
    }


def build_report(
    probe: dict[str, Any],
    drilldown: dict[str, Any],
    bull_pocket: dict[str, Any],
    leaderboard_probe: dict[str, Any],
) -> dict[str, Any]:
    live_context = _resolve_current_live_context(probe, drilldown, bull_pocket)
    support_summary = bull_pocket.get("support_pathology_summary") or {}
    alignment = leaderboard_probe.get("alignment") or {}
    component_gap = drilldown.get("component_gap_attribution") or {}
    runtime_blocker = drilldown.get("runtime_blocker") or None
    best_single = component_gap.get("best_single_component") or None
    minimum_support_rows = _as_int(support_summary.get("minimum_support_rows"), 50)
    current_bucket_rows = _as_int(live_context.get("current_live_structure_bucket_rows"), 0)

    scope_applicability = _scope_applicability(live_context)
    support_route = _support_route_decision(
        current_bucket_rows=current_bucket_rows,
        minimum_support_rows=minimum_support_rows,
        exact_bucket_proxy_rows=_as_int(alignment.get("bull_exact_live_bucket_proxy_rows"), 0),
        exact_lane_proxy_rows=_as_int(alignment.get("bull_exact_live_lane_proxy_rows"), 0),
        supported_neighbor_rows=_as_int(alignment.get("bull_support_neighbor_rows"), 0),
        exact_bucket_root_cause=str(support_summary.get("exact_bucket_root_cause") or ""),
        preferred_support_cohort=support_summary.get("preferred_support_cohort"),
        support_governance_route=alignment.get("support_governance_route"),
    )
    support_progress = _summarize_support_progress(
        current_bucket=live_context.get("current_live_structure_bucket"),
        support_route_verdict=support_route.get("verdict"),
        support_governance_route=alignment.get("support_governance_route"),
        live_bucket_rows=current_bucket_rows,
        minimum_support_rows=minimum_support_rows,
        current_label=os.getenv("HB_RUN_LABEL"),
    )
    floor_legality = _floor_cross_legality(
        support_route=support_route,
        runtime_blocker=runtime_blocker,
        remaining_gap_to_floor=_as_float(component_gap.get("remaining_gap_to_floor")),
        best_single_component=best_single,
    )
    component_experiment = _component_experiment(
        support_route=support_route,
        floor_legality=floor_legality,
        component_gap=component_gap,
        runtime_blocker=runtime_blocker,
        scope_applicability=scope_applicability,
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
    if not scope_applicability.get("active_for_current_live_row"):
        next_action = (
            "current live row 目前不在 q15 lane；q15 audit 只保留 standby route readiness。"
            "下一輪主焦點應回到 q35 current-live blocker / deployment verify，除非 live row 再次回到 q15 bucket。"
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
            "execution_guardrail_reason": probe.get("execution_guardrail_reason") if "execution_guardrail_reason" in probe else live_context.get("execution_guardrail_reason"),
            "current_live_structure_bucket": live_context.get("current_live_structure_bucket"),
            "current_live_structure_bucket_rows": _as_int(live_context.get("current_live_structure_bucket_rows"), 0),
        },
        "scope_applicability": scope_applicability,
        "support_route": {
            "support_governance_route": alignment.get("support_governance_route"),
            "preferred_support_cohort": support_route.get("preferred_support_cohort"),
            "verdict": support_route.get("verdict"),
            "deployable": support_route.get("deployable"),
            "governance_reference_only": support_route.get("governance_reference_only"),
            "reason": support_route.get("reason"),
            "release_condition": support_route.get("release_condition"),
            "route_hint": support_route.get("route_hint"),
            "minimum_support_rows": minimum_support_rows,
            "current_live_structure_bucket_gap_to_minimum": max(0, minimum_support_rows - current_bucket_rows),
            "exact_bucket_root_cause": support_summary.get("exact_bucket_root_cause") or support_route.get("route_hint") or support_route.get("verdict"),
            "recommended_action": support_summary.get("recommended_action") or support_route.get("release_condition"),
            "exact_live_bucket_proxy_rows": _as_int(alignment.get("bull_exact_live_bucket_proxy_rows"), 0),
            "exact_live_lane_proxy_rows": _as_int(alignment.get("bull_exact_live_lane_proxy_rows"), 0),
            "supported_neighbor_rows": _as_int(alignment.get("bull_support_neighbor_rows"), 0),
            "support_progress": support_progress,
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
        "component_experiment": component_experiment,
        "component_gap_attribution": component_gap,
        "runtime_blocker": runtime_blocker,
        "next_action": next_action,
    }


def _markdown(report: dict[str, Any]) -> str:
    current = report.get("current_live") or {}
    scope = report.get("scope_applicability") or {}
    support = report.get("support_route") or {}
    support_progress = support.get("support_progress") or {}
    floor = report.get("floor_cross_legality") or {}
    experiment = report.get("component_experiment") or {}
    experiment_answer = experiment.get("machine_read_answer") or {}
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
            "## Scope applicability",
            f"- status: **{scope.get('status')}**",
            f"- active_for_current_live_row: **{scope.get('active_for_current_live_row')}**",
            f"- current_structure_bucket: **{scope.get('current_structure_bucket')}**",
            f"- target_structure_bucket: **{scope.get('target_structure_bucket')}**",
            f"- reason: {scope.get('reason')}",
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
            f"- support_progress.status: **{support_progress.get('status')}**",
            f"- support_progress.current_rows / minimum: **{support_progress.get('current_rows')} / {support_progress.get('minimum_support_rows')}**",
            f"- support_progress.previous_rows: **{support_progress.get('previous_rows')}**",
            f"- support_progress.delta_vs_previous: **{support_progress.get('delta_vs_previous')}**",
            f"- support_progress.stagnant_run_count: **{support_progress.get('stagnant_run_count')}**",
            f"- support_progress.escalate_to_blocker: **{support_progress.get('escalate_to_blocker')}**",
            f"- support_progress.reason: {support_progress.get('reason')}",
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
            "## Exact-supported component experiment",
            f"- verdict: **{experiment.get('verdict')}**",
            f"- feature: **{experiment.get('feature')}**",
            f"- mode: **{experiment.get('mode')}**",
            f"- support_ready: **{experiment_answer.get('support_ready')}**",
            f"- entry_quality_ge_0_55: **{experiment_answer.get('entry_quality_ge_0_55')}**",
            f"- allowed_layers_gt_0: **{experiment_answer.get('allowed_layers_gt_0')}**",
            f"- preserves_positive_discrimination: **{experiment_answer.get('preserves_positive_discrimination')}** ({experiment_answer.get('preserves_positive_discrimination_status')})",
            f"- reason: {experiment.get('reason')}",
            f"- verify_next: {experiment.get('verify_next')}",
            "",
            "## Next action",
            f"- {report.get('next_action')}",
            "",
        ]
    )


def main() -> None:
    probe = _load_json(PROBE_PATH)
    drilldown = _load_json(DRILLDOWN_PATH)
    drilldown = _refresh_live_drilldown_if_needed(probe, drilldown)
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
                "component_experiment_verdict": (report.get("component_experiment") or {}).get("verdict"),
                "component_experiment_feature": (report.get("component_experiment") or {}).get("feature"),
                "component_experiment_machine_read_answer": (report.get("component_experiment") or {}).get("machine_read_answer"),
                "support_progress": (report.get("support_route") or {}).get("support_progress"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
