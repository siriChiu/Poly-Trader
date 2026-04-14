#!/usr/bin/env python3
"""Summarize current live decision-quality pathology lanes.

Consumes the persisted `data/live_predict_probe.json` from hb_predict_probe.py and
writes a compact artifact + markdown note that highlight the current live lane,
chosen calibration scope, broader spillover lane, and shared 4H collapse shifts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
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


def main() -> None:
    payload = json.loads(PROBE_PATH.read_text(encoding="utf-8"))
    diags = payload.get("decision_quality_scope_diagnostics") or {}
    consensus = diags.get("pathology_consensus") or {}

    chosen_scope = str(payload.get("decision_quality_calibration_scope") or "unknown")
    exact_scope_name = "regime_label+regime_gate+entry_quality_label"
    narrow_scope_name = "regime_label+entry_quality_label"
    broad_scope_name = "regime_gate+entry_quality_label"

    report = {
        "generated_at": payload.get("feature_timestamp"),
        "target_col": payload.get("target_col"),
        "signal": payload.get("signal"),
        "confidence": payload.get("confidence"),
        "should_trade": payload.get("should_trade"),
        "regime_label": payload.get("regime_label"),
        "regime_gate": payload.get("regime_gate"),
        "entry_quality_label": payload.get("entry_quality_label"),
        "allowed_layers_raw": payload.get("allowed_layers_raw"),
        "allowed_layers": payload.get("allowed_layers"),
        "allowed_layers_reason": payload.get("allowed_layers_reason"),
        "execution_guardrail_reason": payload.get("execution_guardrail_reason"),
        "chosen_scope": chosen_scope,
        "chosen_scope_summary": _scope_summary(chosen_scope, diags.get(chosen_scope) or {}),
        "exact_live_lane_summary": _scope_summary(exact_scope_name, diags.get(exact_scope_name) or {}),
        "narrow_same_regime_summary": _scope_summary(narrow_scope_name, diags.get(narrow_scope_name) or {}),
        "broad_same_gate_summary": _scope_summary(broad_scope_name, diags.get(broad_scope_name) or {}),
        "recent_pathology_reason": payload.get("decision_quality_recent_pathology_reason"),
        "recent_pathology_summary": payload.get("decision_quality_recent_pathology_summary"),
        "shared_top_shift_features": consensus.get("shared_top_shift_features") or [],
        "worst_pathology_scope": consensus.get("worst_pathology_scope") or {},
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

    lines = [
        "# Live Decision-Quality Drilldown",
        "",
        f"- feature_timestamp: **{report['generated_at']}**",
        f"- target: `{report['target_col']}`",
        f"- live path: **{report['regime_label']} / {report['regime_gate']} / {report['entry_quality_label']}**",
        f"- signal: **{report['signal']}** @ confidence **{report['confidence']:.4f}**",
        f"- layers: **{report['allowed_layers_raw']} → {report['allowed_layers']}**",
        f"- allowed_layers_reason: `{report['allowed_layers_reason']}`",
        f"- execution_guardrail_reason: `{report['execution_guardrail_reason']}`",
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
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
