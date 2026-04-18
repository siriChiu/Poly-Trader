#!/usr/bin/env python3
"""Machine-readable root-cause artifact for current q15 exact-bucket gap.

Purpose:
- decide whether the current q15 exact-bucket miss is mainly a boundary issue,
  a structure-scoring issue, or a live-row/projection issue
- point to the smallest next patch target instead of repeating generic q15 blocker text
- leave behind JSON + markdown for heartbeat Step 0.5 carry-forward

Inputs:
- data/live_predict_probe.json
- data/live_decision_quality_drilldown.json
- data/bull_4h_pocket_ablation.json

Outputs:
- data/q15_bucket_root_cause.json
- docs/analysis/q15_bucket_root_cause.md
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import feature_group_ablation as feature_group_module
from scripts import bull_4h_pocket_ablation as bull_pocket_module

PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
DRILLDOWN_PATH = PROJECT_ROOT / "data" / "live_decision_quality_drilldown.json"
BULL_POCKET_PATH = PROJECT_ROOT / "data" / "bull_4h_pocket_ablation.json"
OUT_JSON = PROJECT_ROOT / "data" / "q15_bucket_root_cause.json"
OUT_MD = PROJECT_ROOT / "docs" / "analysis" / "q15_bucket_root_cause.md"

STRUCTURE_COMPONENTS = {
    "feat_4h_bb_pct_b": {"weight": 0.34, "scale": 1.0},
    "feat_4h_dist_bb_lower": {"weight": 0.33, "scale": 8.0},
    "feat_4h_dist_swing_low": {"weight": 0.33, "scale": 10.0},
}
Q35_THRESHOLD = 0.35
Q15_THRESHOLD = 0.15
BOUNDARY_EPSILON = 0.03


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
    except Exception:
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _clamp01(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


def _normalize(feature: str, raw_value: Any) -> float | None:
    raw = _safe_float(raw_value)
    if raw is None:
        return None
    scale = STRUCTURE_COMPONENTS[feature]["scale"]
    if scale == 1.0:
        return _clamp01(raw)
    return _clamp01(raw / scale)


def _needed_raw_delta_to_target(feature: str, current_raw: Any, target_normalized: float | None) -> float | None:
    current = _safe_float(current_raw)
    target = _safe_float(target_normalized)
    if current is None or target is None:
        return None
    scale = STRUCTURE_COMPONENTS[feature]["scale"]
    if scale == 1.0:
        needed_raw = target
    else:
        needed_raw = target * scale
    return round(needed_raw - current, 4)


def _needed_raw_delta_to_cross_q35(feature: str, current_raw: Any, current_score: float | None) -> float | None:
    current = _safe_float(current_raw)
    score = _safe_float(current_score)
    if current is None or score is None:
        return None
    weight = STRUCTURE_COMPONENTS[feature]["weight"]
    needed_norm_delta = max(0.0, (Q35_THRESHOLD - score) / weight)
    current_norm = _normalize(feature, current)
    if current_norm is None:
        return None
    target_norm = min(1.0, current_norm + needed_norm_delta)
    return _needed_raw_delta_to_target(feature, current, target_norm)


def _metric_delta(lhs: Any, rhs: Any) -> float | None:
    left = _safe_float(lhs)
    right = _safe_float(rhs)
    if left is None or right is None:
        return None
    return round(left - right, 4)


def _series_stats(series: pd.Series) -> dict[str, float | None]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {"rows": 0, "mean": None, "median": None, "p25": None, "p75": None}
    return {
        "rows": int(s.shape[0]),
        "mean": round(float(s.mean()), 4),
        "median": round(float(s.median()), 4),
        "p25": round(float(s.quantile(0.25)), 4),
        "p75": round(float(s.quantile(0.75)), 4),
    }


def _structure_component_gap_report(frame: pd.DataFrame, current_components: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for feature in STRUCTURE_COMPONENTS:
        current_raw = None
        for component in current_components.get("structure_components") or []:
            if component.get("feature") == feature:
                current_raw = component.get("raw_value")
                break
        current_norm = _normalize(feature, current_raw)
        stats = _series_stats(frame[feature]) if feature in frame.columns else {"rows": 0, "mean": None, "median": None, "p25": None, "p75": None}
        target_norm_p25 = _normalize(feature, stats.get("p25"))
        target_norm_median = _normalize(feature, stats.get("median"))
        report[feature] = {
            "current_raw": _safe_float(current_raw),
            "current_normalized": round(current_norm, 4) if current_norm is not None else None,
            "target_bucket_rows": stats.get("rows"),
            "target_bucket_mean": stats.get("mean"),
            "target_bucket_median": stats.get("median"),
            "target_bucket_p25": stats.get("p25"),
            "target_bucket_p75": stats.get("p75"),
            "delta_vs_target_median": _metric_delta(current_raw, stats.get("median")),
            "delta_vs_target_p25": _metric_delta(current_raw, stats.get("p25")),
            "needed_raw_delta_to_target_p25": _needed_raw_delta_to_target(feature, current_raw, target_norm_p25),
            "needed_raw_delta_to_target_median": _needed_raw_delta_to_target(feature, current_raw, target_norm_median),
            "needed_raw_delta_to_cross_q35": _needed_raw_delta_to_cross_q35(
                feature,
                current_raw,
                current_components.get("structure_quality"),
            ),
        }
    return report


def build_report(probe: dict[str, Any], drilldown: dict[str, Any], bull_pocket: dict[str, Any]) -> dict[str, Any]:
    if not probe:
        return {
            "verdict": "missing_live_probe",
            "candidate_patch_type": None,
            "candidate_patch_feature": None,
            "reason": "缺少 data/live_predict_probe.json，無法分析 q15 exact-bucket root cause。",
        }

    loaded = feature_group_module._load_training_frame()
    X, _, regimes = loaded[:3]
    frame = X.copy()
    frame["regime_label"] = regimes.values
    frame = bull_pocket_module._derive_live_bucket_columns(frame)

    live_regime = str(probe.get("regime_label") or "")
    live_gate = str(probe.get("regime_gate") or "")
    live_entry_quality_label = str(probe.get("entry_quality_label") or "")
    current_bucket = (
        ((probe.get("decision_quality_scope_diagnostics") or {}).get("regime_label+regime_gate+entry_quality_label") or {}).get("current_live_structure_bucket")
        or ((bull_pocket.get("live_context") or {}).get("current_live_structure_bucket"))
    )
    structure_components = (probe.get("entry_quality_components") or {}).get("structure_components") or []
    current_structure_quality = _safe_float((probe.get("entry_quality_components") or {}).get("structure_quality"))
    component_map = {item.get("feature"): item for item in structure_components if item.get("feature")}

    exact_lane_mask = (
        (frame["regime_label"].astype(str) == live_regime)
        & (frame["regime_gate"].astype(str) == live_gate)
        & (frame["entry_quality_label"].astype(str) == live_entry_quality_label)
    )
    exact_lane = frame.loc[exact_lane_mask].copy()
    exact_lane_rows = int(exact_lane.shape[0])

    bucket_counts_series = exact_lane["structure_bucket"].fillna("missing").value_counts() if exact_lane_rows else pd.Series(dtype=int)
    bucket_counts = {str(k): int(v) for k, v in bucket_counts_series.items()}
    dominant_neighbor_bucket = None
    dominant_neighbor_rows = 0
    for bucket, rows in bucket_counts.items():
        if bucket == current_bucket or rows <= dominant_neighbor_rows:
            continue
        dominant_neighbor_bucket = bucket
        dominant_neighbor_rows = rows

    dominant_neighbor_frame = exact_lane.loc[exact_lane["structure_bucket"] == dominant_neighbor_bucket].copy() if dominant_neighbor_bucket else exact_lane.iloc[0:0].copy()

    near_boundary_rows = 0
    boundary_window = None
    if current_structure_quality is not None and exact_lane_rows:
        boundary_window = {
            "lower": round(current_structure_quality, 4),
            "upper": Q35_THRESHOLD,
        }
        near_boundary_mask = (
            pd.to_numeric(exact_lane["structure_quality"], errors="coerce") >= current_structure_quality
        ) & (
            pd.to_numeric(exact_lane["structure_quality"], errors="coerce") < Q35_THRESHOLD
        )
        near_boundary_rows = int(near_boundary_mask.fillna(False).sum())

    component_gap_report = _structure_component_gap_report(dominant_neighbor_frame, probe.get("entry_quality_components") or {})
    ranked_components = sorted(
        [
            {
                "feature": feature,
                **payload,
            }
            for feature, payload in component_gap_report.items()
            if payload.get("needed_raw_delta_to_cross_q35") is not None
        ],
        key=lambda row: (
            abs(float(row.get("needed_raw_delta_to_cross_q35") or 999999.0)),
            abs(float(row.get("needed_raw_delta_to_target_p25") or 999999.0)),
            row.get("feature") or "",
        ),
    )
    best_feature = ranked_components[0] if ranked_components else {}

    non_null_4h_feature_count = probe.get("non_null_4h_feature_count")
    projection_issue = bool(non_null_4h_feature_count is not None and int(non_null_4h_feature_count) < 3)
    signal = str(probe.get("signal") or "").strip().upper()
    deployment_blocker = str(probe.get("deployment_blocker") or "").strip()
    deployment_blocker_source = str(probe.get("deployment_blocker_source") or "").strip()
    execution_guardrail_reason = str(probe.get("execution_guardrail_reason") or "").strip()
    runtime_blocker_preempts = bool(
        signal == "CIRCUIT_BREAKER"
        or deployment_blocker == "circuit_breaker_active"
        or deployment_blocker_source == "circuit_breaker"
        or execution_guardrail_reason == "circuit_breaker_blocks_trade"
    )

    verdict = "insufficient_scope_data"
    candidate_patch_type = None
    reason = "目前資料不足，尚無法判定 q15 exact bucket 0-row 的最小可修補原因。"
    verify_next = "先確保 live probe / bull pocket artifacts 完整，再重跑 q15 root-cause artifact。"

    if runtime_blocker_preempts:
        verdict = "runtime_blocker_preempts_bucket_root_cause"
        reason = "目前 live runtime 已先被 circuit breaker 擋下；q15 bucket root-cause 只能視為背景治理，不能誤報成 structure_quality / projection 問題。"
        verify_next = "先讓 canonical breaker release condition 接近解除，再重跑 hb_predict_probe.py 與 q15 root-cause artifact。"
    elif projection_issue:
        verdict = "live_row_projection_missing_4h_inputs"
        candidate_patch_type = "live_row_projection"
        reason = "live row 的 4H 欄位 non-null 數不足，應先修投影/對齊，而不是討論 q15↔q35 分桶。"
        verify_next = "修 projection 後重跑 hb_predict_probe.py，確認 non_null_4h_feature_count >= 3。"
    elif current_structure_quality is None:
        verdict = "missing_structure_quality"
        candidate_patch_type = "live_row_projection"
        reason = "目前 live row 無法算出 structure_quality，先修 4H 結構輸入。"
        verify_next = "重跑 hb_predict_probe.py，確認 entry_quality_components.structure_quality 有值。"
    elif current_structure_quality >= Q35_THRESHOLD:
        verdict = "current_row_already_above_q35_boundary"
        candidate_patch_type = "support_accumulation"
        reason = "目前 live row 已不在 q15/q35 邊界下方，問題改成 exact support 累積，不是 bucket repair。"
        verify_next = "確認 current_live_structure_bucket_rows 是否增加到 minimum_support_rows。"
    elif exact_lane_rows <= 0:
        verdict = "no_exact_live_lane_rows"
        candidate_patch_type = "scope_generation"
        reason = "連 exact live lane 都沒有資料，先補 same regime/gate/entry-quality lane，而不是只修 bucket 邊界。"
        verify_next = "重跑 bull_4h_pocket_ablation.py，確認 exact_scope_rows > 0。"
    elif dominant_neighbor_bucket and dominant_neighbor_rows > 0 and near_boundary_rows == 0:
        verdict = "structure_scoring_gap_not_boundary"
        candidate_patch_type = "structure_component_scoring"
        reason = (
            "exact live lane 的樣本全部落在鄰近 bucket，且 current_structure_quality 與 q35 邊界之間沒有 exact-lane 緩衝列；"
            "這代表單純放寬 q15/q35 boundary 不能生成 exact rows，應優先查結構 component scoring。"
        )
        verify_next = (
            "優先用 q15 root-cause artifact 鎖定的 component 做 counterfactual，"
            "確認 current row 是否能跨到 q35，且 exact-lane 仍不會因 boundary tweak 產生虛假支持。"
        )
    elif (Q35_THRESHOLD - current_structure_quality) <= BOUNDARY_EPSILON and near_boundary_rows > 0:
        verdict = "boundary_sensitivity_candidate"
        candidate_patch_type = "bucket_boundary_review"
        reason = (
            "current_structure_quality 已貼近 q35 邊界，且 exact-lane 存在 near-boundary rows；"
            "可把 q15↔q35 分桶公式列入候選，但仍需先做 exact-support legality 驗證。"
        )
        verify_next = "以歷史 lane 回放驗證 boundary review 不會把 0-row blocker 假裝成已解。"
    elif dominant_neighbor_bucket and dominant_neighbor_rows > 0:
        verdict = "same_lane_neighbor_bucket_dominates"
        candidate_patch_type = "structure_component_scoring"
        reason = (
            "same exact lane 有明顯鄰近 bucket 樣本，current row 與 q35 support 的差距主要來自結構 component，"
            "不是 generic breaker / q35 總體治理。"
        )
        verify_next = "比較 current row 與 dominant neighbor bucket 的 4H component 差值，再做最小 counterfactual。"

    component_deltas = {}
    for feature, payload in component_gap_report.items():
        current_payload = component_map.get(feature) or {}
        component_deltas[feature] = {
            **payload,
            "weighted_contribution": current_payload.get("weighted_contribution"),
        }

    candidate_patch_feature = best_feature.get("feature") or None
    candidate_patch = None
    if candidate_patch_feature:
        candidate_patch = {
            "type": candidate_patch_type,
            "feature": candidate_patch_feature,
            "current_raw": best_feature.get("current_raw"),
            "current_normalized": best_feature.get("current_normalized"),
            "needed_raw_delta_to_cross_q35": best_feature.get("needed_raw_delta_to_cross_q35"),
            "target_bucket_p25": best_feature.get("target_bucket_p25"),
            "target_bucket_median": best_feature.get("target_bucket_median"),
            "needed_raw_delta_to_target_p25": best_feature.get("needed_raw_delta_to_target_p25"),
            "needed_raw_delta_to_target_median": best_feature.get("needed_raw_delta_to_target_median"),
        }

    return {
        "generated_at": probe.get("feature_timestamp") or drilldown.get("generated_at"),
        "target_col": probe.get("target_col") or bull_pocket.get("target_col"),
        "current_live": {
            "regime_label": live_regime,
            "regime_gate": live_gate,
            "entry_quality_label": live_entry_quality_label,
            "structure_bucket": current_bucket,
            "structure_quality": round(current_structure_quality, 4) if current_structure_quality is not None else None,
            "q15_threshold": Q15_THRESHOLD,
            "q35_threshold": Q35_THRESHOLD,
            "gap_to_q35_boundary": round(max(Q35_THRESHOLD - current_structure_quality, 0.0), 4) if current_structure_quality is not None else None,
            "non_null_4h_feature_count": probe.get("non_null_4h_feature_count"),
            "execution_guardrail_reason": probe.get("execution_guardrail_reason"),
        },
        "exact_live_lane": {
            "rows": exact_lane_rows,
            "bucket_counts": bucket_counts,
            "dominant_neighbor_bucket": dominant_neighbor_bucket,
            "dominant_neighbor_rows": dominant_neighbor_rows,
            "near_boundary_window": boundary_window,
            "near_boundary_rows": near_boundary_rows,
        },
        "verdict": verdict,
        "candidate_patch_type": candidate_patch_type,
        "candidate_patch_feature": candidate_patch_feature,
        "reason": reason,
        "candidate_patch": candidate_patch,
        "component_deltas": component_deltas,
        "verify_next": verify_next,
        "carry_forward": [
            "先讀 data/q15_bucket_root_cause.json，確認本輪 verdict 與 candidate_patch_feature。",
            "若 verdict=structure_scoring_gap_not_boundary，下一輪不得把主焦點退回 generic q35/breaker；必須直接做 structure component counterfactual。",
            "若 verdict=boundary_sensitivity_candidate，先驗證 boundary review 是否真的增加 exact-lane current bucket rows，再決定是否 patch。",
            "若 verdict=live_row_projection_missing_4h_inputs，先修 projection / 4H 對齊，再重跑 q15 support audit。",
        ],
    }


def _markdown(report: dict[str, Any]) -> str:
    current = report.get("current_live") or {}
    lane = report.get("exact_live_lane") or {}
    candidate = report.get("candidate_patch") or {}
    component_lines = []
    for feature, payload in (report.get("component_deltas") or {}).items():
        component_lines.append(
            f"- `{feature}`: current={payload.get('current_raw')} / norm={payload.get('current_normalized')} / "
            f"Δto_cross_q35={payload.get('needed_raw_delta_to_cross_q35')} / "
            f"target_p25={payload.get('target_bucket_p25')} / target_median={payload.get('target_bucket_median')}"
        )
    if not component_lines:
        component_lines = ["- None"]
    carry_forward = "\n".join(f"- {item}" for item in report.get("carry_forward") or [])
    return "\n".join(
        [
            "# q15 Bucket Root Cause",
            "",
            f"- generated_at: **{report.get('generated_at')}**",
            f"- target_col: **{report.get('target_col')}**",
            f"- verdict: **{report.get('verdict')}**",
            f"- candidate_patch_type: **{report.get('candidate_patch_type')}**",
            f"- candidate_patch_feature: **{report.get('candidate_patch_feature')}**",
            "",
            "## Current live",
            f"- live path: **{current.get('regime_label')} / {current.get('regime_gate')} / {current.get('entry_quality_label')}**",
            f"- structure_bucket: `{current.get('structure_bucket')}`",
            f"- structure_quality: **{current.get('structure_quality')}**",
            f"- gap_to_q35_boundary: **{current.get('gap_to_q35_boundary')}**",
            f"- non_null_4h_feature_count: **{current.get('non_null_4h_feature_count')}**",
            f"- execution_guardrail_reason: `{current.get('execution_guardrail_reason')}`",
            "",
            "## Exact live lane",
            f"- rows: **{lane.get('rows')}**",
            f"- bucket_counts: `{lane.get('bucket_counts')}`",
            f"- dominant_neighbor_bucket: **{lane.get('dominant_neighbor_bucket')}** ({lane.get('dominant_neighbor_rows')} rows)",
            f"- near_boundary_window: `{lane.get('near_boundary_window')}`",
            f"- near_boundary_rows: **{lane.get('near_boundary_rows')}**",
            "",
            "## Decision",
            f"- reason: {report.get('reason')}",
            f"- candidate_patch: `{candidate}`",
            f"- verify_next: {report.get('verify_next')}",
            "",
            "## Component deltas",
            *component_lines,
            "",
            "## Carry-forward",
            carry_forward,
            "",
        ]
    )


def main() -> None:
    probe = _load_json(PROBE_PATH)
    drilldown = _load_json(DRILLDOWN_PATH)
    bull_pocket = _load_json(BULL_POCKET_PATH)
    report = build_report(probe, drilldown, bull_pocket)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "json": str(OUT_JSON.relative_to(PROJECT_ROOT)),
                "markdown": str(OUT_MD.relative_to(PROJECT_ROOT)),
                "verdict": report.get("verdict"),
                "candidate_patch_type": report.get("candidate_patch_type"),
                "candidate_patch_feature": report.get("candidate_patch_feature"),
                "gap_to_q35_boundary": ((report.get("current_live") or {}).get("gap_to_q35_boundary")),
                "dominant_neighbor_bucket": ((report.get("exact_live_lane") or {}).get("dominant_neighbor_bucket")),
                "near_boundary_rows": ((report.get("exact_live_lane") or {}).get("near_boundary_rows")),
                "verify_next": report.get("verify_next"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
