#!/usr/bin/env python3
"""Machine-readable q15 boundary replay + component counterfactual artifact.

Purpose:
- answer whether q15↔q35 boundary review truly creates exact-lane current-bucket support
  or merely relabels the live row into an already-supported q35 neighbor bucket
- turn the root-cause candidate `feat_4h_bb_pct_b` into a minimal counterfactual
  and verify whether it fixes support only, floor only, both, or neither
- leave behind JSON + markdown that the next heartbeat can ingest directly in Step 0.5

Inputs:
- data/live_predict_probe.json
- data/q15_support_audit.json
- data/q15_bucket_root_cause.json

Outputs:
- data/q15_boundary_replay.json
- docs/analysis/q15_boundary_replay.md
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
SUPPORT_AUDIT_PATH = PROJECT_ROOT / "data" / "q15_support_audit.json"
ROOT_CAUSE_PATH = PROJECT_ROOT / "data" / "q15_bucket_root_cause.json"
OUT_JSON = PROJECT_ROOT / "data" / "q15_boundary_replay.json"
OUT_MD = PROJECT_ROOT / "docs" / "analysis" / "q15_boundary_replay.md"

Q35_THRESHOLD = 0.35
TRADE_FLOOR = 0.55


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        result = float(value)
    except Exception:
        return default
    if math.isnan(result) or math.isinf(result):
        return default
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _bucket_swap_q15_to_q35(bucket: str | None) -> str | None:
    text = str(bucket or "").strip()
    if not text:
        return None
    return text.replace("|q15", "|q35") if text.endswith("|q15") else text


def _allowed_layers_reason(regime_gate: str | None, entry_quality: float | None) -> str | None:
    gate = str(regime_gate or "")
    score = _safe_float(entry_quality)
    if score is None:
        return None
    if gate == "BLOCK":
        return "regime_gate_block"
    if score < 0.55:
        return "entry_quality_below_trade_floor"
    if score < 0.68:
        return "entry_quality_C_single_layer"
    if gate == "CAUTION":
        return "regime_gate_caution_caps_two_layers"
    return "full_three_layers_allowed"


def _allowed_layers(regime_gate: str | None, entry_quality: float | None, max_layers: int = 3) -> int:
    gate = str(regime_gate or "")
    score = _safe_float(entry_quality)
    if score is None or gate == "BLOCK" or score < 0.55:
        return 0
    if score < 0.68:
        return min(max_layers, 1)
    if gate == "CAUTION":
        return min(max_layers, 2)
    return min(max_layers, 3)


def build_report(
    probe: dict[str, Any],
    support_audit: dict[str, Any],
    root_cause: dict[str, Any],
) -> dict[str, Any]:
    if not probe or not support_audit or not root_cause:
        return {
            "verdict": "missing_inputs",
            "reason": "缺少 live probe / q15 support audit / q15 root-cause artifact，無法做 q15 boundary replay。",
            "verify_next": "先重跑 hb_predict_probe.py、hb_q15_support_audit.py、hb_q15_bucket_root_cause.py。",
            "carry_forward": [
                "先確認 data/live_predict_probe.json、data/q15_support_audit.json、data/q15_bucket_root_cause.json 都存在且為同一輪輸出。"
            ],
        }

    current_live = root_cause.get("current_live") or {}
    support_current = support_audit.get("current_live") or {}
    support_route = support_audit.get("support_route") or {}
    floor_legality = support_audit.get("floor_cross_legality") or {}
    exact_lane = root_cause.get("exact_live_lane") or {}
    probe_components = probe.get("entry_quality_components") or {}
    scope_name = probe.get("decision_quality_calibration_scope") or "regime_label+regime_gate+entry_quality_label"
    scope_diag = (probe.get("decision_quality_scope_diagnostics") or {}).get(scope_name) or {}
    structure_counts = scope_diag.get("recent500_structure_bucket_counts") or {}

    current_bucket = (
        support_current.get("current_live_structure_bucket")
        or current_live.get("structure_bucket")
    )
    current_structure_quality = _safe_float(
        current_live.get("structure_quality"),
        _safe_float(probe_components.get("structure_quality")),
    )
    q35_threshold = _safe_float(current_live.get("q35_threshold"), Q35_THRESHOLD) or Q35_THRESHOLD
    gap_to_q35 = _round(max(0.0, q35_threshold - float(current_structure_quality or 0.0)))
    dominant_neighbor_bucket = exact_lane.get("dominant_neighbor_bucket") or _bucket_swap_q15_to_q35(current_bucket)
    dominant_neighbor_rows = _safe_int(exact_lane.get("dominant_neighbor_rows"), 0)
    near_boundary_rows = _safe_int(exact_lane.get("near_boundary_rows"), 0)
    legacy_scope_rows = _safe_int(support_current.get("current_live_structure_bucket_rows"), 0)
    replay_scope_rows = _safe_int(structure_counts.get(dominant_neighbor_bucket), 0)
    replay_generated_rows = near_boundary_rows
    replay_generated_excess = max(replay_generated_rows - replay_scope_rows, 0)
    replay_generated_exceeds_scope = replay_generated_excess > 0
    replay_preexisting_rows = max(replay_scope_rows - replay_generated_rows, 0)
    replay_generated_share = (
        _round(min(replay_generated_rows / replay_scope_rows, 1.0)) if replay_scope_rows > 0 else None
    )

    base_quality = _safe_float(probe_components.get("base_quality"))
    entry_before = _safe_float(probe.get("entry_quality"), _safe_float(probe_components.get("entry_quality")))
    bb_pct_b_raw = None
    for component in probe_components.get("structure_components") or []:
        if component.get("feature") == "feat_4h_bb_pct_b":
            bb_pct_b_raw = _safe_float(component.get("raw_value"))
            break

    candidate_patch = root_cause.get("candidate_patch") or {}
    bb_pct_b_delta = _safe_float(candidate_patch.get("needed_raw_delta_to_cross_q35"))
    bb_pct_b_after = _round((bb_pct_b_raw or 0.0) + (bb_pct_b_delta or 0.0)) if bb_pct_b_raw is not None and bb_pct_b_delta is not None else None
    structure_after = _round(current_structure_quality + gap_to_q35) if current_structure_quality is not None else None
    entry_after = (
        _round(0.75 * base_quality + 0.25 * structure_after)
        if base_quality is not None and structure_after is not None
        else None
    )
    trade_floor_gap_after = _round((entry_after - TRADE_FLOOR) if entry_after is not None else None)
    rebucketed_bucket = dominant_neighbor_bucket or _bucket_swap_q15_to_q35(current_bucket)
    rebucketed_layers = _allowed_layers(probe.get("regime_gate"), entry_after)
    rebucketed_layers_reason = _allowed_layers_reason(probe.get("regime_gate"), entry_after)

    verdict = "boundary_replay_not_applicable"
    reason = "目前 q15 root-cause verdict 不是 boundary_sensitivity_candidate，boundary replay 不是本輪主路徑。"
    verify_next = root_cause.get("verify_next") or "先依 q15 root-cause artifact 的 verify_next 行動。"
    next_action = "依 q15 root-cause / support audit 的既有 blocker 繼續治理。"

    root_verdict = root_cause.get("verdict")
    if root_verdict == "boundary_sensitivity_candidate":
        if replay_scope_rows <= 0:
            verdict = "boundary_replay_has_no_supported_target_bucket"
            reason = "就算把 q15↔q35 邊界向下回放，chosen scope 仍找不到可承接的 current bucket rows；boundary review 無法形成可部署支持。"
            verify_next = "改查 structure component scoring / support accumulation，不再延長 boundary review。"
            next_action = "停止把 boundary review 當主假設，回到 structure component 與 support accumulation。"
        elif replay_preexisting_rows > replay_generated_rows:
            verdict = "boundary_relabels_into_existing_q35_support"
            reason = (
                "boundary replay 主要是把 live row 改標到既有 q35 支撐 bucket；"
                "真正由邊界敏感新生成的 rows 只有極小一段，這不是 q15 exact-support 被修好，而是改走既有鄰近 q35 支撐。"
            )
            verify_next = (
                "把 boundary replay 視為治理證據，不可直接 relax runtime gate；"
                "下一輪應優先驗 feat_4h_bb_pct_b counterfactual 是否只造成 rebucket，且 trade floor 仍未跨越。"
            )
            next_action = (
                "將 q15 boundary review 降級為 reference-only；"
                "主焦點轉到 feat_4h_bb_pct_b 是否只是 bucket proxy，以及 bias50 / pulse 等真正 floor-gap component。"
            )
        else:
            verdict = "boundary_replay_requires_exact_support_validation"
            reason = "boundary replay 可帶來可見的 exact-lane rebucket rows，但仍需確認這不是把 blocker 假裝成已解。"
            verify_next = "用 exact-lane replay + runtime guardrail 驗證 rebucket 後的 rows 是否足夠且合法。"
            next_action = "保守保留 boundary replay 為候選，但不得跳過 legality / runtime 驗證。"

    counterfactual_verdict = "counterfactual_unavailable"
    counterfactual_reason = "缺少 feat_4h_bb_pct_b 當前值或 needed_raw_delta_to_cross_q35，無法做最小反事實。"
    if bb_pct_b_after is not None and structure_after is not None and entry_after is not None:
        if entry_after < TRADE_FLOOR and rebucketed_layers == 0:
            counterfactual_verdict = "bucket_proxy_only_not_trade_floor_fix"
            counterfactual_reason = (
                "只把 feat_4h_bb_pct_b 補到剛好跨 q35，只會把結構 bucket 從 q15 改成 q35；"
                "entry_quality 仍低於 trade floor，allowed_layers 仍是 0，表示它更像 bucket proxy，而不是 deployable floor fix。"
            )
        else:
            counterfactual_verdict = "counterfactual_crosses_floor_after_rebucket"
            counterfactual_reason = (
                "feat_4h_bb_pct_b 的最小反事實不只改變 bucket，也讓 entry_quality 跨過 trade floor；"
                "下一輪可升級成 guarded experiment。"
            )

    if (
        root_verdict == "same_lane_neighbor_bucket_dominates"
        and counterfactual_verdict == "bucket_proxy_only_not_trade_floor_fix"
    ):
        verdict = "same_lane_counterfactual_bucket_proxy_only"
        reason = (
            "目前不是 boundary 問題，而是 same-lane q35 鄰近 bucket 已足夠明確；"
            "最小 feat_4h_bb_pct_b 反事實只會把 current row 重新分桶到 q35，"
            "但 entry_quality 仍過不了 trade floor，因此它只能當 bucket proxy 證據，不能視為 deployable 修補。"
        )
        verify_next = (
            "保留 feat_4h_bb_pct_b counterfactual 作為 bucket-proxy 證據；"
            "下一輪改直接檢查 feat_4h_bias50 / base stack 或 support accumulation 是否才是 floor-gap 主因。"
        )
        next_action = (
            "停止把 q15 問題包裝成 boundary review；"
            "維持 feat_4h_bb_pct_b 為 structure proxy 診斷，主修補焦點轉到 bias50 / exact-support accumulation。"
        )

    carry_forward = [
        "先讀 data/q15_boundary_replay.json，確認 verdict 與 feat_4h_bb_pct_b counterfactual verdict。",
        "若 verdict=same_lane_counterfactual_bucket_proxy_only，下一輪不得再把 q15 blocker 寫成 boundary review 或 feat_4h_bb_pct_b 單點可部署修補；必須直接檢查 feat_4h_bias50 / support accumulation。",
        "若 verdict=boundary_relabels_into_existing_q35_support，下一輪不得把 q15 boundary review 當成 deployment patch；只能當治理參考。",
        "若 component_counterfactual.verdict=bucket_proxy_only_not_trade_floor_fix，下一輪不得把 feat_4h_bb_pct_b 單獨包裝成 floor-gap 修復；要改查 bias50 / pulse 或 support accumulation。",
        "只有當 boundary replay 與 component counterfactual 同時證明 exact support 合法且 trade floor 跨越時，才允許討論 runtime gate 調整。",
    ]

    return {
        "generated_at": probe.get("feature_timestamp") or current_live.get("generated_at"),
        "target_col": probe.get("target_col") or support_audit.get("target_col") or root_cause.get("target_col"),
        "current_live": {
            "signal": probe.get("signal"),
            "regime_label": probe.get("regime_label"),
            "regime_gate": probe.get("regime_gate"),
            "entry_quality_label": probe.get("entry_quality_label"),
            "structure_bucket": current_bucket,
            "structure_quality": current_structure_quality,
            "entry_quality": entry_before,
            "trade_floor_gap": _safe_float(probe_components.get("trade_floor_gap")),
            "support_route_verdict": support_route.get("verdict"),
            "floor_cross_legality_verdict": floor_legality.get("verdict"),
        },
        "boundary_replay": {
            "legacy_bucket": current_bucket,
            "legacy_current_bucket_rows": legacy_scope_rows,
            "legacy_q35_threshold": q35_threshold,
            "gap_to_q35_boundary": gap_to_q35,
            "replay_bucket": rebucketed_bucket,
            "replay_scope": scope_name,
            "replay_scope_bucket_rows": replay_scope_rows,
            "generated_rows_via_boundary_only": replay_generated_rows,
            "preexisting_rows_in_replay_bucket": replay_preexisting_rows,
            "generated_row_share": replay_generated_share,
            "generated_rows_exceed_replay_scope": replay_generated_exceeds_scope,
            "generated_rows_excess_over_scope": replay_generated_excess,
            "dominant_neighbor_bucket": dominant_neighbor_bucket,
            "dominant_neighbor_rows": dominant_neighbor_rows,
            "near_boundary_rows": near_boundary_rows,
        },
        "component_counterfactual": {
            "feature": "feat_4h_bb_pct_b",
            "raw_before": bb_pct_b_raw,
            "raw_delta_to_cross_q35": bb_pct_b_delta,
            "raw_after": bb_pct_b_after,
            "structure_quality_before": current_structure_quality,
            "structure_quality_after": structure_after,
            "bucket_after": rebucketed_bucket,
            "entry_quality_before": entry_before,
            "entry_quality_after": entry_after,
            "trade_floor_gap_after": trade_floor_gap_after,
            "allowed_layers_after": rebucketed_layers,
            "allowed_layers_reason_after": rebucketed_layers_reason,
            "scope_bucket_rows_after_rebucket": replay_scope_rows,
            "verdict": counterfactual_verdict,
            "reason": counterfactual_reason,
        },
        "verdict": verdict,
        "reason": reason,
        "next_action": next_action,
        "verify_next": verify_next,
        "carry_forward": carry_forward,
    }


def _markdown(report: dict[str, Any]) -> str:
    current = report.get("current_live") or {}
    replay = report.get("boundary_replay") or {}
    counterfactual = report.get("component_counterfactual") or {}
    return "\n".join(
        [
            "# q15 Boundary Replay",
            "",
            f"- generated_at: **{report.get('generated_at')}**",
            f"- target_col: **{report.get('target_col')}**",
            f"- verdict: **{report.get('verdict')}**",
            f"- reason: {report.get('reason')}",
            "",
            "## Current live row",
            f"- signal: **{current.get('signal')}**",
            f"- regime/gate: **{current.get('regime_label')} / {current.get('regime_gate')}**",
            f"- structure bucket: **{current.get('structure_bucket')}**",
            f"- structure_quality: **{current.get('structure_quality')}**",
            f"- entry_quality: **{current.get('entry_quality')}** (trade_floor_gap={current.get('trade_floor_gap')})",
            f"- support_route: **{current.get('support_route_verdict')}**",
            f"- floor_cross_legality: **{current.get('floor_cross_legality_verdict')}**",
            "",
            "## Boundary replay",
            f"- legacy bucket rows: **{replay.get('legacy_current_bucket_rows')}**",
            f"- replay bucket: **{replay.get('replay_bucket')}**",
            f"- replay bucket rows: **{replay.get('replay_scope_bucket_rows')}**",
            f"- generated_rows_via_boundary_only: **{replay.get('generated_rows_via_boundary_only')}**",
            f"- preexisting_rows_in_replay_bucket: **{replay.get('preexisting_rows_in_replay_bucket')}**",
            f"- generated_row_share: **{replay.get('generated_row_share')}**",
            f"- generated_rows_exceed_replay_scope: **{replay.get('generated_rows_exceed_replay_scope')}** (excess={replay.get('generated_rows_excess_over_scope')})",
            f"- dominant_neighbor_bucket: **{replay.get('dominant_neighbor_bucket')}** rows={replay.get('dominant_neighbor_rows')}",
            "",
            "## feat_4h_bb_pct_b minimal counterfactual",
            f"- raw before/after: **{counterfactual.get('raw_before')} → {counterfactual.get('raw_after')}**",
            f"- structure_quality: **{counterfactual.get('structure_quality_before')} → {counterfactual.get('structure_quality_after')}**",
            f"- bucket_after: **{counterfactual.get('bucket_after')}**",
            f"- entry_quality: **{counterfactual.get('entry_quality_before')} → {counterfactual.get('entry_quality_after')}**",
            f"- trade_floor_gap_after: **{counterfactual.get('trade_floor_gap_after')}**",
            f"- allowed_layers_after: **{counterfactual.get('allowed_layers_after')}** ({counterfactual.get('allowed_layers_reason_after')})",
            f"- counterfactual verdict: **{counterfactual.get('verdict')}**",
            f"- counterfactual reason: {counterfactual.get('reason')}",
            "",
            "## Next",
            f"- next_action: {report.get('next_action')}",
            f"- verify_next: {report.get('verify_next')}",
        ]
    )


def main() -> None:
    probe = _load_json(PROBE_PATH)
    support_audit = _load_json(SUPPORT_AUDIT_PATH)
    root_cause = _load_json(ROOT_CAUSE_PATH)
    report = build_report(probe, support_audit, root_cause)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"json": str(OUT_JSON), "markdown": str(OUT_MD), "verdict": report.get("verdict")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
