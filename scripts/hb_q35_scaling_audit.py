#!/usr/bin/env python3
"""Audit whether current bull q35 lane is blocked by over-harsh scaling or by a real hold-only setup.

Produces a machine-readable artifact summarizing:
- current live row context
- historical exact-lane / same-bucket support
- bias50 percentile vs historical winners
- counterfactual layer eligibility if q35 caution or bias50 penalty were relaxed
- final governance verdict
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "poly_trader.db"
PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
OUT_JSON = PROJECT_ROOT / "data" / "q35_scaling_audit.json"
OUT_MD = PROJECT_ROOT / "docs" / "analysis" / "q35_scaling_audit.md"

import sys
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model import predictor as live_predictor
from model.q35_bias50_calibration import compute_piecewise_bias50_score


def _round(value: Any, digits: int = 4):
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except Exception:
        return None


def _pct_rank(values: list[float], current: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    le = sum(1 for v in ordered if v <= current)
    return round(le / len(ordered), 4)


def _quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "min": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "max": None,
            "mean": None,
        }
    ordered = sorted(values)

    def pick(q: float):
        idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
        return round(float(ordered[idx]), 4)

    return {
        "min": round(float(ordered[0]), 4),
        "p25": pick(0.25),
        "p50": pick(0.50),
        "p75": pick(0.75),
        "p90": pick(0.90),
        "p95": pick(0.95),
        "max": round(float(ordered[-1]), 4),
        "mean": round(float(mean(ordered)), 4),
    }


def _classify_percentile_band(percentile: float | None) -> str:
    if percentile is None:
        return "no_data"
    if percentile <= 0.50:
        return "core_normal"
    if percentile <= 0.75:
        return "warm"
    if percentile <= 0.90:
        return "elevated_but_within_p90"
    if percentile <= 0.95:
        return "borderline_overheat"
    return "overheat"


def _threshold_delta(current: float, threshold: float | None) -> float | None:
    if threshold is None:
        return None
    return round(current - float(threshold), 4)


def _cohort_calibration_view(summary: dict[str, Any], current_bias50: float) -> dict[str, Any]:
    dist = summary.get("bias50_distribution") or {}
    percentile = summary.get("current_bias50_percentile")
    rows = int(summary.get("rows") or 0)
    return {
        "rows": rows,
        "current_bias50_percentile": percentile,
        "percentile_band": _classify_percentile_band(percentile),
        "delta_vs_p50": _threshold_delta(current_bias50, dist.get("p50")),
        "delta_vs_p75": _threshold_delta(current_bias50, dist.get("p75")),
        "delta_vs_p90": _threshold_delta(current_bias50, dist.get("p90")),
        "delta_vs_p95": _threshold_delta(current_bias50, dist.get("p95")),
        "bias50_distribution": dist,
    }


def _select_segmented_reference_cohort(
    exact_summary: dict[str, Any],
    broader_bull_summary: dict[str, dict[str, Any]],
    current_bias50: float,
) -> dict[str, Any]:
    exact_dist = exact_summary.get("bias50_distribution") or {}
    exact_p90 = exact_dist.get("p90")
    exact_p95 = exact_dist.get("p95")
    exact_percentile = exact_summary.get("current_bias50_percentile")

    candidate_order = [
        ("same_gate_same_quality", "同 bull gate + 同 quality lane"),
        ("same_bucket", "同 bull structure bucket"),
        ("bull_all", "整體 bull cohort"),
    ]
    viable: list[dict[str, Any]] = []
    for key, label in candidate_order:
        summary = broader_bull_summary.get(key) or {}
        rows = int(summary.get("rows") or 0)
        if rows <= 0:
            continue
        dist = summary.get("bias50_distribution") or {}
        p90 = dist.get("p90")
        percentile = summary.get("current_bias50_percentile")
        if p90 is None or percentile is None:
            continue
        if current_bias50 > float(p90):
            continue
        viable.append(
            {
                "cohort": key,
                "label": label,
                "rows": rows,
                "current_bias50_percentile": percentile,
                "percentile_band": _classify_percentile_band(percentile),
                "bias50_distribution": dist,
                "delta_vs_exact_p90": _threshold_delta(float(p90), exact_p90),
                "delta_vs_exact_p95": _threshold_delta(float(p90), exact_p95),
            }
        )

    if not viable:
        return {
            "status": "no_viable_reference_cohort",
            "reason": "current bias50 仍高於所有候選 bull cohorts 的 p90；現階段較像 hold-only / overheat，而不是可直接做 segmented calibration。",
            "exact_lane_percentile": exact_percentile,
        }

    chosen = viable[0]
    chosen["status"] = "viable_reference_cohort"
    chosen["reason"] = (
        "current bias50 已超出 exact lane 常態區，但仍落在更廣 bull cohort 的 p90 內；"
        "下一步應以這個 cohort 做 segmented / piecewise calibration 研究，而不是直接 relax q35 gate。"
    )
    return chosen


def _runtime_contract_state(
    segmented_calibration: dict[str, Any],
    piecewise_runtime_preview: dict[str, Any],
) -> tuple[str, str]:
    """Describe whether piecewise calibration is implemented vs merely applicable.

    Heartbeat #1005 exposed a governance drift: runtime integration already existed in
    predictor.py, but the audit still reported `piecewise_runtime_pending` whenever the
    *current* row did not land inside the narrow extension zone. That wording falsely
    implied implementation was missing. This helper separates three cases:

    1. active on current row
    2. implemented, but current row is outside the extension zone / still hold-only
    3. truly not required / no segmented contract this round
    """

    if piecewise_runtime_preview.get("applied"):
        return (
            "piecewise_runtime_active",
            "piecewise bias50 calibration 已由 predictor / q35 audit 實際套用到 current bull q35 lane；後續 heartbeat 不得再把這題描述成 runtime 尚未吃到新公式。",
        )

    status = str(segmented_calibration.get("status") or "")
    exact_lane = segmented_calibration.get("exact_lane") or {}
    exact_lane_band = exact_lane.get("percentile_band")
    preview_segment = piecewise_runtime_preview.get("segment")
    preview_mode = piecewise_runtime_preview.get("mode")

    if status == "segmented_calibration_required":
        if preview_segment == "reference_overheat" or exact_lane_band == "overheat":
            return (
                "piecewise_runtime_ready_hold_only_current_row",
                "piecewise bias50 calibration 已經實作於 predictor / q35 audit；只是 current row 仍屬 exact/reference overheat lane，runtime 會正確維持 hold-only，而不是套用 extension score。",
            )
        if exact_lane_band in {"core_normal", "warm", "elevated_but_within_p90", "borderline_overheat"}:
            return (
                "piecewise_runtime_ready_current_row_outside_extension",
                "piecewise bias50 calibration 已經實作於 predictor / q35 audit；只是 current row 已回到 exact-lane 可接受區間或尚未進入 targeted extension zone，所以本列不需要套用 piecewise extension score。",
            )
        if preview_mode == "piecewise_quantile_calibration":
            return (
                "piecewise_runtime_ready_waiting_for_matching_row",
                "piecewise bias50 calibration 已經實作，但目前 current row 尚未落在會觸發該分段公式的條件；需等下一個 matching lane row 再看到非 legacy 分數。",
            )

    return (
        "piecewise_runtime_not_required",
        "本輪 audit 沒有要求 current row 套用 segmented calibration；runtime 可維持既有路徑。",
    )


def _current_row(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT f.*, l.simulated_pyramid_win
        FROM features_normalized f
        LEFT JOIN labels l
          ON l.timestamp = f.timestamp
         AND l.symbol = f.symbol
         AND l.horizon_minutes = 1440
        ORDER BY f.timestamp DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        raise RuntimeError("No latest feature row found")
    return row


def _build_row_context(row: sqlite3.Row) -> dict[str, Any]:
    features = {k: row[k] for k in row.keys()}
    regime = str(features.get("regime_label") or "unknown")
    gate_debug = live_predictor._compute_live_regime_gate_debug(
        features.get("feat_4h_bias200") or 0.0,
        regime,
        bb_pct_b_value=features.get("feat_4h_bb_pct_b"),
        dist_bb_lower_value=features.get("feat_4h_dist_bb_lower"),
        dist_swing_low_value=features.get("feat_4h_dist_swing_low"),
    )
    regime_gate = str(gate_debug.get("final_gate") or "BLOCK")
    structure_bucket = live_predictor._live_structure_bucket_from_debug(gate_debug)
    eq = live_predictor._live_entry_quality_component_breakdown(
        features.get("feat_4h_bias50") or 0.0,
        features.get("feat_nose") or 0.0,
        features.get("feat_pulse") or 0.0,
        features.get("feat_ear") or 0.0,
        bb_pct_b_value=features.get("feat_4h_bb_pct_b"),
        dist_bb_lower_value=features.get("feat_4h_dist_bb_lower"),
        dist_swing_low_value=features.get("feat_4h_dist_swing_low"),
        regime_label=regime,
        regime_gate=regime_gate,
        structure_bucket=structure_bucket,
    )
    entry_quality = float(eq.get("entry_quality") or 0.0)
    return {
        "timestamp": features.get("timestamp"),
        "symbol": features.get("symbol"),
        "regime_label": regime,
        "regime_gate": gate_debug.get("final_gate"),
        "base_gate": gate_debug.get("base_gate"),
        "gate_reason": gate_debug.get("final_reason"),
        "structure_bucket": structure_bucket,
        "structure_quality": gate_debug.get("structure_quality"),
        "entry_quality": _round(entry_quality),
        "entry_quality_label": live_predictor._quality_label(entry_quality),
        "allowed_layers_raw": live_predictor._allowed_layers_for_live_signal(str(gate_debug.get("final_gate") or "BLOCK"), entry_quality),
        "allowed_layers_reason": live_predictor._allowed_layers_reason_for_live_signal(str(gate_debug.get("final_gate") or "BLOCK"), entry_quality),
        "entry_quality_components": eq,
        "raw_features": {
            "feat_4h_bias50": _round(features.get("feat_4h_bias50")),
            "feat_4h_bias200": _round(features.get("feat_4h_bias200")),
            "feat_nose": _round(features.get("feat_nose")),
            "feat_pulse": _round(features.get("feat_pulse")),
            "feat_ear": _round(features.get("feat_ear")),
            "feat_4h_bb_pct_b": _round(features.get("feat_4h_bb_pct_b")),
            "feat_4h_dist_bb_lower": _round(features.get("feat_4h_dist_bb_lower")),
            "feat_4h_dist_swing_low": _round(features.get("feat_4h_dist_swing_low")),
        },
    }


def _historical_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT f.timestamp, f.symbol, f.regime_label,
               f.feat_4h_bias50, f.feat_4h_bias200,
               f.feat_nose, f.feat_pulse, f.feat_ear,
               f.feat_4h_bb_pct_b, f.feat_4h_dist_bb_lower, f.feat_4h_dist_swing_low,
               l.simulated_pyramid_win, l.simulated_pyramid_pnl, l.simulated_pyramid_quality,
               l.simulated_pyramid_drawdown_penalty, l.simulated_pyramid_time_underwater
        FROM features_normalized f
        JOIN labels l
          ON l.timestamp = f.timestamp
         AND l.symbol = f.symbol
         AND l.horizon_minutes = 1440
        WHERE l.simulated_pyramid_win IS NOT NULL
          AND f.feat_4h_bias50 IS NOT NULL
          AND f.feat_4h_bias200 IS NOT NULL
          AND f.feat_nose IS NOT NULL
          AND f.feat_pulse IS NOT NULL
          AND f.feat_ear IS NOT NULL
        ORDER BY f.timestamp
        """
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        ctx = _build_row_context(row)
        ctx.update(
            {
                "simulated_pyramid_win": row["simulated_pyramid_win"],
                "simulated_pyramid_pnl": row["simulated_pyramid_pnl"],
                "simulated_pyramid_quality": row["simulated_pyramid_quality"],
                "simulated_pyramid_drawdown_penalty": row["simulated_pyramid_drawdown_penalty"],
                "simulated_pyramid_time_underwater": row["simulated_pyramid_time_underwater"],
            }
        )
        out.append(ctx)
    return out


def _counterfactuals(current: dict[str, Any]) -> dict[str, Any]:
    eq = current["entry_quality_components"]
    base_quality = float(eq.get("base_quality") or 0.0)
    structure_quality = float(eq.get("structure_quality") or 0.0)
    trade_floor = float(eq.get("trade_floor") or 0.55)
    bias_score = 0.0
    for item in eq.get("base_components") or []:
        if item.get("feature") == "feat_4h_bias50":
            bias_score = float(item.get("normalized_score") or 0.0)
            break
    entry_if_allow = round(float(eq.get("entry_quality") or 0.0), 4)
    layers_if_allow = live_predictor._allowed_layers_for_live_signal("ALLOW", entry_if_allow)
    needed_entry_gain = max(0.0, trade_floor - entry_if_allow)
    needed_base_gain = needed_entry_gain / 0.75
    needed_bias_gain = needed_base_gain / 0.40
    needed_bias_score = min(1.0, round(bias_score + needed_bias_gain, 4))
    bias50_value = float(current["raw_features"]["feat_4h_bias50"] or 0.0)
    required_bias50_cap = round(2.4 - 5.0 * needed_bias_score, 4)
    no_bias_penalty_base = min(1.0, base_quality + 0.40 * (1.0 - bias_score))
    entry_if_bias50_fully_relaxed = round(0.75 * no_bias_penalty_base + 0.25 * structure_quality, 4)
    layers_if_bias50_fully_relaxed = live_predictor._allowed_layers_for_live_signal(current["regime_gate"], entry_if_bias50_fully_relaxed)
    return {
        "entry_if_gate_allow_only": entry_if_allow,
        "layers_if_gate_allow_only": layers_if_allow,
        "gate_allow_only_changes_layers": layers_if_allow != current["allowed_layers_raw"],
        "entry_if_bias50_fully_relaxed": entry_if_bias50_fully_relaxed,
        "layers_if_bias50_fully_relaxed": layers_if_bias50_fully_relaxed,
        "bias50_score_current": round(bias_score, 4),
        "trade_floor": trade_floor,
        "needed_entry_gain_to_cross_floor": round(needed_entry_gain, 4),
        "needed_base_gain_to_cross_floor": round(needed_base_gain, 4),
        "needed_bias50_score_for_floor": needed_bias_score,
        "required_bias50_cap_for_floor": required_bias50_cap,
        "current_bias50_value": round(bias50_value, 4),
    }


def _summarize_subset(rows: list[dict[str, Any]], current_bias50: float) -> dict[str, Any]:
    bias_vals = [float(r["raw_features"]["feat_4h_bias50"]) for r in rows if r["raw_features"].get("feat_4h_bias50") is not None]
    structure_vals = [float(r["structure_quality"]) for r in rows if r.get("structure_quality") is not None]
    eq_vals = [float(r["entry_quality"]) for r in rows if r.get("entry_quality") is not None]
    wins = [float(r["simulated_pyramid_win"]) for r in rows if r.get("simulated_pyramid_win") is not None]
    return {
        "rows": len(rows),
        "win_rate": _round(sum(wins) / len(wins)) if wins else None,
        "bias50_distribution": _quantiles(bias_vals),
        "structure_quality_distribution": _quantiles(structure_vals),
        "entry_quality_distribution": _quantiles(eq_vals),
        "current_bias50_percentile": _pct_rank(bias_vals, current_bias50),
    }


def _q35_scope_applicability(current: dict[str, Any]) -> dict[str, Any]:
    bucket = str(current.get("structure_bucket") or "")
    is_q35_lane = bucket.endswith("|q35")
    if is_q35_lane:
        return {
            "status": "current_live_q35_lane_active",
            "active_for_current_live_row": True,
            "current_structure_bucket": bucket,
            "target_structure_bucket": "CAUTION|structure_quality_caution|q35",
            "reason": "current live row 仍位於 q35 lane；本輪 q35 scaling / bias50 calibration 結論可直接視為 live governance 主路徑。",
        }
    return {
        "status": "reference_only_current_bucket_outside_q35",
        "active_for_current_live_row": False,
        "current_structure_bucket": bucket or None,
        "target_structure_bucket": "CAUTION|structure_quality_caution|q35",
        "reason": "current live row 已不在 q35 lane；q35 scaling audit 只能保留為 reference-only calibration artifact，不得誤寫成當前 live blocker 已落在 q35 formula review。",
    }


def main() -> None:
    probe = json.loads(PROBE_PATH.read_text(encoding="utf-8")) if PROBE_PATH.exists() else {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    current_row = _current_row(conn)
    current = _build_row_context(current_row)
    history = _historical_rows(conn)
    conn.close()

    current_bias50 = float(current["raw_features"]["feat_4h_bias50"] or 0.0)
    scope_applicability = _q35_scope_applicability(current)
    exact_lane = [
        r for r in history
        if r["regime_label"] == current["regime_label"]
        and r["regime_gate"] == current["regime_gate"]
        and r["entry_quality_label"] == current["entry_quality_label"]
        and r["structure_bucket"] == current["structure_bucket"]
    ]
    exact_lane_winners = [r for r in exact_lane if int(r.get("simulated_pyramid_win") or 0) == 1]
    same_bucket_any_regime = [r for r in history if r["structure_bucket"] == current["structure_bucket"]]
    broader_bull_same_gate_same_quality = [
        r for r in history
        if r["regime_label"] == current["regime_label"]
        and r["regime_gate"] == current["regime_gate"]
        and r["entry_quality_label"] == current["entry_quality_label"]
    ]
    broader_bull_same_bucket = [
        r for r in history
        if r["regime_label"] == current["regime_label"]
        and r["structure_bucket"] == current["structure_bucket"]
    ]
    broader_bull_all = [r for r in history if r["regime_label"] == current["regime_label"]]

    counterfactuals = _counterfactuals(current)
    exact_summary = _summarize_subset(exact_lane, current_bias50)
    winner_summary = _summarize_subset(exact_lane_winners, current_bias50)
    bucket_summary = _summarize_subset(same_bucket_any_regime, current_bias50)
    broader_bull_summary = {
        "same_gate_same_quality": _summarize_subset(broader_bull_same_gate_same_quality, current_bias50),
        "same_bucket": _summarize_subset(broader_bull_same_bucket, current_bias50),
        "bull_all": _summarize_subset(broader_bull_all, current_bias50),
    }
    segmented_reference = _select_segmented_reference_cohort(exact_summary, broader_bull_summary, current_bias50)
    segmented_calibration = {
        "exact_lane": _cohort_calibration_view(exact_summary, current_bias50),
        "broader_bull_cohorts": {
            key: _cohort_calibration_view(summary, current_bias50)
            for key, summary in broader_bull_summary.items()
        },
        "reference_cohort": segmented_reference,
    }

    gate_only_not_enough = not counterfactuals["gate_allow_only_changes_layers"]
    exact_p75 = exact_summary["bias50_distribution"].get("p75")
    exact_p90 = exact_summary["bias50_distribution"].get("p90")
    broader_same_gate_p90 = (broader_bull_summary["same_gate_same_quality"].get("bias50_distribution") or {}).get("p90")
    broader_same_bucket_p90 = (broader_bull_summary["same_bucket"].get("bias50_distribution") or {}).get("p90")
    broader_bull_all_p90 = (broader_bull_summary["bull_all"].get("bias50_distribution") or {}).get("p90")
    broader_same_gate_p75 = (broader_bull_summary["same_gate_same_quality"].get("bias50_distribution") or {}).get("p75")
    broader_same_bucket_p75 = (broader_bull_summary["same_bucket"].get("bias50_distribution") or {}).get("p75")
    broader_bull_all_p75 = (broader_bull_summary["bull_all"].get("bias50_distribution") or {}).get("p75")

    broader_overheat_confirmed = all(
        threshold is not None and current_bias50 > threshold
        for threshold in (exact_p90, broader_same_gate_p90, broader_same_bucket_p90, broader_bull_all_p90)
    )
    broader_recalibration_candidate = any(
        threshold is not None and current_bias50 <= threshold
        for threshold in (broader_same_gate_p75, broader_same_bucket_p75, broader_bull_all_p75)
    )
    broader_segmentation_candidate = (
        gate_only_not_enough
        and exact_p90 is not None
        and current_bias50 > exact_p90
        and any(
            threshold is not None and current_bias50 <= threshold
            for threshold in (broader_same_gate_p90, broader_same_bucket_p90, broader_bull_all_p90)
        )
    )

    if gate_only_not_enough and broader_overheat_confirmed:
        overall_verdict = "hold_only_bias50_overheat_confirmed"
        verdict_reason = "只把 q35 CAUTION 改回 ALLOW 仍無法增加層數；而 current bias50 不只高於 exact-lane p90，也高於更廣 bull cohorts 的 p90，代表主要是 bias50 過熱，不是 q35 結構縮放把可交易 lane 誤殺。"
    elif gate_only_not_enough and exact_p90 is not None and current_bias50 <= exact_p90:
        overall_verdict = "bias50_formula_may_be_too_harsh"
        verdict_reason = "current bias50 已回到 exact-lane p90 內，但 legacy 公式仍可能把它壓成 0 分；需改做 exact-lane 內的保守分段校準，而不是繼續把它視為 broader bull segmentation 問題。"
    elif broader_segmentation_candidate:
        overall_verdict = "broader_bull_cohort_recalibration_candidate"
        verdict_reason = "current bias50 已超出 exact-lane p90，但仍落在至少一個更廣 bull cohort 的 p90 內，表示現在更像『bull cohort segmentation / calibration 問題』，不能直接把 q35 lane 視為可放寬，也不能只沿用單一 exact-lane percentile 做結論。"
    elif gate_only_not_enough and broader_recalibration_candidate:
        overall_verdict = "broader_bull_cohort_recalibration_candidate"
        verdict_reason = "exact-lane 仍偏熱，但 current bias50 已回到至少一個更廣 bull cohort 的常見區間；若要主張公式過嚴，下一步應做分段 / 分位數校準，而不是直接放寬 q35 gate 或 trade floor。"
    else:
        overall_verdict = "mixed_needs_manual_followup"
        verdict_reason = "q35 縮放不是唯一因素，但 bias50 是否過嚴仍需更多 lane-level 比較。"

    structure_verdict = (
        "q35_structure_caution_not_root_cause"
        if gate_only_not_enough
        else "q35_structure_caution_changes_execution"
    )

    if overall_verdict == "broader_bull_cohort_recalibration_candidate":
        segmented_calibration["status"] = "segmented_calibration_required"
        segmented_calibration["recommended_mode"] = "piecewise_quantile_calibration"
        segmented_calibration["reason"] = (
            "exact lane 顯示過熱，但至少一個更廣 bull cohort 仍把 current bias50 視為 p90 內；"
            "應改做 bull cohort segmentation / piecewise quantile calibration，而不是直接 relax runtime gate。"
        )
    elif overall_verdict == "bias50_formula_may_be_too_harsh":
        segmented_calibration["status"] = "formula_review_required"
        segmented_calibration["recommended_mode"] = "exact_lane_formula_review"
        segmented_calibration["reason"] = "current bias50 已回到 exact lane p90 內；下一步應做 exact-lane 內的保守 bias50 校準 / 公式檢查，而不是再走 broader bull segmentation。"
    elif overall_verdict == "hold_only_bias50_overheat_confirmed":
        segmented_calibration["status"] = "hold_only_confirmed"
        segmented_calibration["recommended_mode"] = "keep_hold_only"
        segmented_calibration["reason"] = "current bias50 高於所有候選 cohorts 的 p90，沒有可用的分段校準參考 cohort。"
    else:
        segmented_calibration["status"] = "manual_followup"
        segmented_calibration["recommended_mode"] = "manual_lane_review"
        segmented_calibration["reason"] = "尚未找到足夠清晰的分段校準或 hold-only 證據，需要人工比對 lane-level artifact。"

    piecewise_runtime_preview = compute_piecewise_bias50_score(
        current_bias50,
        regime_label=current.get("regime_label"),
        regime_gate=current.get("regime_gate"),
        structure_bucket=current.get("structure_bucket"),
        audit={
            "overall_verdict": overall_verdict,
            "segmented_calibration": segmented_calibration,
            "current_live": current,
        },
    )
    runtime_contract_status, runtime_contract_reason = _runtime_contract_state(
        segmented_calibration,
        piecewise_runtime_preview,
    )
    segmented_calibration["runtime_contract_status"] = runtime_contract_status
    segmented_calibration["runtime_contract_reason"] = runtime_contract_reason

    report = {
        "generated_at": current["timestamp"],
        "target_col": probe.get("target_col", "simulated_pyramid_win"),
        "current_live": current,
        "scope_applicability": scope_applicability,
        "exact_lane_summary": exact_summary,
        "exact_lane_winner_summary": winner_summary,
        "same_bucket_any_regime_summary": bucket_summary,
        "broader_bull_cohorts": broader_bull_summary,
        "segmented_calibration": segmented_calibration,
        "piecewise_runtime_preview": piecewise_runtime_preview,
        "counterfactuals": counterfactuals,
        "structure_scaling_verdict": structure_verdict,
        "overall_verdict": overall_verdict,
        "verdict_reason": verdict_reason,
        "recommended_action": (
            "維持 q35=CAUTION；把本輪焦點放在 bias50 正規化是否應改成分段/分位數縮放，只有當 current bias50 落在 exact-lane 常見區間時才放寬。"
            if scope_applicability["active_for_current_live_row"]
            and overall_verdict in {"bias50_formula_may_be_too_harsh", "broader_bull_cohort_recalibration_candidate"}
            else (
                "current live row 已離開 q35 lane；本輪 q35 audit 僅保留為 reference-only。"
                "下一步應優先處理 current bucket 的 exact support / structure component blocker，"
                "不得把 q35 bias50 calibration 誤當成可直接放行 current live row 的 patch。"
            )
            if not scope_applicability["active_for_current_live_row"]
            else "把這條 current bull q35 lane 正式治理成 hold-only 候選；除非 bias50 校準審計證明 current 值屬於 exact-lane 常態，否則不要直接放寬 trade floor 或 q35 gate。"
        ),
    }

    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = [
        "# Q35 Scaling Audit",
        "",
        f"- generated_at: **{report['generated_at']}**",
        f"- overall_verdict: **{overall_verdict}**",
        f"- structure_scaling_verdict: **{structure_verdict}**",
        f"- scope_applicability: **{scope_applicability['status']}**",
        f"- reason: {verdict_reason}",
        f"- applicability_note: {scope_applicability['reason']}",
        "",
        "## Current live row",
        "",
        f"- regime/gate/quality: **{current['regime_label']} / {current['regime_gate']} / {current['entry_quality_label']}**",
        f"- structure_bucket: **{current['structure_bucket']}**",
        f"- entry_quality: **{current['entry_quality']}** (reason=`{current['allowed_layers_reason']}`)",
        f"- feat_4h_bias50: **{current['raw_features']['feat_4h_bias50']}**",
        f"- structure_quality: **{current['structure_quality']}**",
        "",
        "## Exact lane summary",
        "",
        f"- rows: **{exact_summary['rows']}** | win_rate: **{exact_summary['win_rate']}**",
        f"- bias50 distribution: {exact_summary['bias50_distribution']}",
        f"- current bias50 percentile in exact lane: **{exact_summary['current_bias50_percentile']}**",
        f"- winner-only bias50 distribution: {winner_summary['bias50_distribution']}",
        "",
        "## Broader bull cohorts",
        "",
        f"- same_gate_same_quality: rows=**{broader_bull_summary['same_gate_same_quality']['rows']}** | win_rate=**{broader_bull_summary['same_gate_same_quality']['win_rate']}** | bias50_pct=**{broader_bull_summary['same_gate_same_quality']['current_bias50_percentile']}** | dist={broader_bull_summary['same_gate_same_quality']['bias50_distribution']}",
        f"- same_bucket: rows=**{broader_bull_summary['same_bucket']['rows']}** | win_rate=**{broader_bull_summary['same_bucket']['win_rate']}** | bias50_pct=**{broader_bull_summary['same_bucket']['current_bias50_percentile']}** | dist={broader_bull_summary['same_bucket']['bias50_distribution']}",
        f"- bull_all: rows=**{broader_bull_summary['bull_all']['rows']}** | win_rate=**{broader_bull_summary['bull_all']['win_rate']}** | bias50_pct=**{broader_bull_summary['bull_all']['current_bias50_percentile']}** | dist={broader_bull_summary['bull_all']['bias50_distribution']}",
        "",
        "## Segmented calibration",
        "",
        f"- status: **{segmented_calibration['status']}** | mode: **{segmented_calibration['recommended_mode']}**",
        f"- runtime contract: **{segmented_calibration['runtime_contract_status']}** — {segmented_calibration['runtime_contract_reason']}",
        f"- exact lane band: **{segmented_calibration['exact_lane']['percentile_band']}** (pct={segmented_calibration['exact_lane']['current_bias50_percentile']}, Δp90={segmented_calibration['exact_lane']['delta_vs_p90']})",
        f"- same_gate_same_quality band: **{segmented_calibration['broader_bull_cohorts']['same_gate_same_quality']['percentile_band']}** (pct={segmented_calibration['broader_bull_cohorts']['same_gate_same_quality']['current_bias50_percentile']}, Δp90={segmented_calibration['broader_bull_cohorts']['same_gate_same_quality']['delta_vs_p90']})",
        f"- same_bucket band: **{segmented_calibration['broader_bull_cohorts']['same_bucket']['percentile_band']}** (pct={segmented_calibration['broader_bull_cohorts']['same_bucket']['current_bias50_percentile']}, Δp90={segmented_calibration['broader_bull_cohorts']['same_bucket']['delta_vs_p90']})",
        f"- bull_all band: **{segmented_calibration['broader_bull_cohorts']['bull_all']['percentile_band']}** (pct={segmented_calibration['broader_bull_cohorts']['bull_all']['current_bias50_percentile']}, Δp90={segmented_calibration['broader_bull_cohorts']['bull_all']['delta_vs_p90']})",
        f"- reference cohort: **{(segmented_calibration['reference_cohort'] or {}).get('cohort')}** / label={((segmented_calibration['reference_cohort'] or {}).get('label'))} / pct={((segmented_calibration['reference_cohort'] or {}).get('current_bias50_percentile'))}",
        f"- note: {segmented_calibration['reason']}",
        f"- runtime preview: applied=**{piecewise_runtime_preview['applied']}** | score=**{piecewise_runtime_preview['score']}** | legacy=**{piecewise_runtime_preview['legacy_score']}** | Δ=**{piecewise_runtime_preview['score_delta_vs_legacy']}** | segment=**{piecewise_runtime_preview['segment']}**",
        "",
        "## Counterfactuals",
        "",
        f"- gate -> ALLOW only: entry_quality **{counterfactuals['entry_if_gate_allow_only']}**, layers **{counterfactuals['layers_if_gate_allow_only']}**",
        f"- fully relax bias50 penalty: entry_quality **{counterfactuals['entry_if_bias50_fully_relaxed']}**, layers **{counterfactuals['layers_if_bias50_fully_relaxed']}**",
        f"- required bias50 cap to cross trade floor: **{counterfactuals['required_bias50_cap_for_floor']}** (current={counterfactuals['current_bias50_value']})",
        "",
        "## Recommended action",
        "",
        f"- {report['recommended_action']}",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({
        "json": str(OUT_JSON),
        "markdown": str(OUT_MD),
        "overall_verdict": overall_verdict,
        "structure_scaling_verdict": structure_verdict,
        "scope_applicability": scope_applicability["status"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
