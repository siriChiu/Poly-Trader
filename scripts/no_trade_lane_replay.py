#!/usr/bin/env python3
"""Build a no-trade lane replay proof from current runtime artifacts.

This artifact is deliberately not a deployment-readiness certificate. It
validates that the current BLOCK/no-trade live lane should be treated as
abstain / reduce-only / paper-shadow evidence, and that its exact support rows
must not be harvested as buy/add deployment support.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DOCS_ANALYSIS_DIR = PROJECT_ROOT / "docs" / "analysis"

DEFAULT_JSON_OUT = DATA_DIR / "no_trade_lane_replay.json"
DEFAULT_MARKDOWN_OUT = DOCS_ANALYSIS_DIR / "no_trade_lane_replay.md"

SOURCE_PATHS = {
    "live_predict_probe": DATA_DIR / "live_predict_probe.json",
    "recent_drift_report": DATA_DIR / "recent_drift_report.json",
    "live_canary_structural_pivot": DATA_DIR / "live_canary_structural_pivot.json",
    "live_decision_quality_drilldown": DATA_DIR / "live_decision_quality_drilldown.json",
    "customer_safe_alternative_proof": DATA_DIR / "customer_safe_alternative_proof.json",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "ready", "passed"}
    return bool(value)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


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


def _to_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct_text(value: Any) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return "—"
    return f"{numeric * 100:.1f}%"


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


def _is_block_no_trade_lane(live_probe: Mapping[str, Any], pivot_truth: Mapping[str, Any]) -> bool:
    bucket = str(
        _first_present(
            live_probe.get("current_live_structure_bucket"),
            live_probe.get("structure_bucket"),
            pivot_truth.get("structure_bucket"),
            default="",
        )
    )
    regime_gate = str(live_probe.get("regime_gate") or "").upper()
    should_trade = live_probe.get("should_trade")
    allowed_layers_raw = _to_int(live_probe.get("allowed_layers_raw"))
    allowed_layers = _to_int(live_probe.get("allowed_layers"))
    return bool(
        bucket.startswith("BLOCK|")
        or regime_gate == "BLOCK"
        or (
            should_trade is False
            and allowed_layers_raw == 0
            and allowed_layers == 0
        )
    )


def _select_shadow_gate(replay: Mapping[str, Any]) -> dict[str, Any]:
    explicit = replay.get("best_gate")
    if isinstance(explicit, dict):
        return dict(explicit)

    gates = [gate for gate in _as_list(replay.get("gates")) if isinstance(gate, dict)]
    if not gates:
        return {}

    best_id = replay.get("best_observable_gate")
    if best_id:
        for gate in gates:
            if gate.get("id") == best_id:
                return dict(gate)

    def _score(gate: Mapping[str, Any]) -> tuple[int, int, float, float, int]:
        verdict = str(gate.get("falsification_verdict") or "")
        runtime_candidate = _as_bool(gate.get("runtime_candidate"))
        uses_future = _as_bool(gate.get("uses_future_outcome_fields"))
        passes = verdict.startswith("passes_shadow_metric")
        return (
            1 if runtime_candidate and not uses_future else 0,
            1 if passes else 0,
            _to_float(gate.get("loss_capture_share"), 0.0) or 0.0,
            _to_float(gate.get("kept_win_rate"), 0.0) or 0.0,
            _to_int(gate.get("kept_rows")),
        )

    return dict(max(gates, key=_score))


def _recent_shadow_context(drift_report: Mapping[str, Any]) -> dict[str, Any]:
    tail = drift_report.get("canonical_tail_root_cause") if isinstance(drift_report.get("canonical_tail_root_cause"), dict) else {}
    replay = tail.get("no_new_risk_shadow_replay") if isinstance(tail.get("no_new_risk_shadow_replay"), dict) else {}
    baseline = replay.get("baseline") if isinstance(replay.get("baseline"), dict) else {}
    best_gate = _select_shadow_gate(replay)
    primary = drift_report.get("primary_window") if isinstance(drift_report.get("primary_window"), dict) else {}
    primary_summary = primary.get("summary") if isinstance(primary.get("summary"), dict) else {}
    if not primary_summary:
        primary_summary = drift_report.get("primary_summary") if isinstance(drift_report.get("primary_summary"), dict) else {}
    return {
        "source": "data/recent_drift_report.json",
        "shadow_only": _as_bool(replay.get("shadow_only", True)),
        "deployable": _as_bool(replay.get("deployable", False)),
        "deployment_verdict": replay.get("deployment_verdict", "not_deployable_shadow_only_runtime_blocked"),
        "mode": replay.get("mode", "shadow_only_no_new_risk_falsification"),
        "baseline_rows": baseline.get("rows"),
        "baseline_win_rate": baseline.get("win_rate"),
        "best_gate_id": best_gate.get("id"),
        "best_gate_verdict": best_gate.get("falsification_verdict"),
        "best_gate_runtime_candidate": best_gate.get("runtime_candidate"),
        "best_gate_uses_future_outcome_fields": best_gate.get("uses_future_outcome_fields"),
        "blocked_rows": best_gate.get("blocked_rows"),
        "blocked_losses": best_gate.get("blocked_losses"),
        "loss_capture_share": best_gate.get("loss_capture_share"),
        "win_cost_share": best_gate.get("win_cost_share"),
        "kept_rows": best_gate.get("kept_rows"),
        "kept_win_rate": best_gate.get("kept_win_rate"),
        "primary_window": primary.get("window") or primary_summary.get("window"),
        "primary_win_rate": primary_summary.get("win_rate"),
        "dominant_regime": primary_summary.get("dominant_regime"),
        "dominant_regime_share": primary_summary.get("dominant_regime_share"),
        "alerts": primary_summary.get("alerts") or primary_summary.get("alert_flags") or [],
    }


def build_no_trade_lane_replay(
    *,
    live_predict_probe: Mapping[str, Any],
    recent_drift_report: Mapping[str, Any],
    live_canary_structural_pivot: Mapping[str, Any] | None = None,
    live_decision_quality_drilldown: Mapping[str, Any] | None = None,
    customer_safe_alternative_proof: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    pivot = live_canary_structural_pivot or {}
    pivot_truth = pivot.get("current_truth") if isinstance(pivot.get("current_truth"), dict) else {}
    pivot_decision = pivot.get("structural_decision") if isinstance(pivot.get("structural_decision"), dict) else {}
    drilldown = live_decision_quality_drilldown or {}
    customer_safe = customer_safe_alternative_proof or {}

    details = live_predict_probe.get("deployment_blocker_details") if isinstance(live_predict_probe.get("deployment_blocker_details"), dict) else {}
    release = live_predict_probe.get("release_condition") if isinstance(live_predict_probe.get("release_condition"), dict) else {}
    if not release and isinstance(details.get("release_condition"), dict):
        release = details.get("release_condition")
    support_rows = _to_int(
        _first_present(
            live_predict_probe.get("current_live_structure_bucket_rows"),
            details.get("current_live_structure_bucket_rows"),
            pivot_truth.get("support_rows"),
            default=0,
        )
    )
    minimum_rows = _to_int(
        _first_present(
            live_predict_probe.get("minimum_support_rows"),
            details.get("minimum_support_rows"),
            pivot_truth.get("minimum_support_rows"),
            50,
        ),
        default=50,
    )
    support_gap = _to_int(
        _first_present(
            live_predict_probe.get("current_live_structure_bucket_gap_to_minimum"),
            details.get("current_live_structure_bucket_gap_to_minimum"),
            pivot_truth.get("support_gap"),
            max(minimum_rows - support_rows, 0),
        )
    )
    no_trade_lane = _is_block_no_trade_lane(live_predict_probe, pivot_truth)
    shadow_context = _recent_shadow_context(recent_drift_report)
    drift_shadow_only = bool(shadow_context.get("shadow_only") and not _as_bool(shadow_context.get("deployable")))
    risk_off_sides = [str(side) for side in _as_list(live_predict_probe.get("api_trade_allowed_risk_off_sides"))]
    paper_shadow_sides = [str(side) for side in _as_list(live_predict_probe.get("api_trade_allowed_paper_shadow_sides"))]
    allowed_actions = [str(action) for action in _as_list(live_predict_probe.get("api_trade_allowed_actions"))]
    reduce_only_visible = bool({"reduce", "sell"} & set(risk_off_sides))
    paper_shadow_visible = bool({"shadow_buy", "paper_buy"} & set(paper_shadow_sides))
    support_evidence_role = (
        pivot_truth.get("support_evidence_role")
        or ("no_trade_decision_validation_not_deployable_support" if no_trade_lane else "deployment_support_identity_required")
    )
    replay_validated = bool(
        no_trade_lane
        and live_predict_probe.get("should_trade") is False
        and _to_int(live_predict_probe.get("allowed_layers")) == 0
        and drift_shadow_only
    )
    verdict = (
        "validated_abstain_reduce_only_no_trade_lane"
        if replay_validated
        else "not_applicable_or_incomplete_no_trade_replay"
    )

    current_truth = {
        "signal": live_predict_probe.get("signal"),
        "should_trade": live_predict_probe.get("should_trade"),
        "deployment_blocker": live_predict_probe.get("deployment_blocker"),
        "runtime_closure_state": live_predict_probe.get("runtime_closure_state"),
        "regime_label": live_predict_probe.get("regime_label"),
        "regime_gate": live_predict_probe.get("regime_gate"),
        "current_live_structure_bucket": _first_present(
            live_predict_probe.get("current_live_structure_bucket"),
            live_predict_probe.get("structure_bucket"),
            pivot_truth.get("structure_bucket"),
            default="—",
        ),
        "current_lane_actionability": pivot_truth.get("current_lane_actionability")
        or ("no_trade_block_lane" if no_trade_lane else "risk_on_candidate_lane"),
        "support_evidence_role": support_evidence_role,
        "allowed_layers_raw": live_predict_probe.get("allowed_layers_raw"),
        "allowed_layers": live_predict_probe.get("allowed_layers"),
        "allowed_layers_reason": live_predict_probe.get("allowed_layers_reason"),
        "execution_guardrail_reason": live_predict_probe.get("execution_guardrail_reason"),
        "support_rows": support_rows,
        "minimum_support_rows": minimum_rows,
        "support_gap": support_gap,
        "support_route_verdict": live_predict_probe.get("support_route_verdict"),
        "support_governance_route": live_predict_probe.get("support_governance_route"),
        "recent_window_wins": _first_present(
            release.get("current_recent_window_wins"),
            live_predict_probe.get("current_recent_window_wins"),
            live_predict_probe.get("recent_window_wins"),
        ),
        "recent_window_size": _first_present(
            release.get("recent_window"),
            live_predict_probe.get("recent_window"),
            live_predict_probe.get("window_size"),
        ),
        "required_recent_window_wins": _first_present(
            release.get("required_recent_window_wins"),
            live_predict_probe.get("required_recent_window_wins"),
        ),
        "additional_recent_window_wins_needed": _first_present(
            release.get("additional_recent_window_wins_needed"),
            live_predict_probe.get("additional_recent_window_wins_needed"),
        ),
        "api_trade_guardrail_active": live_predict_probe.get("api_trade_guardrail_active"),
        "api_trade_buy_guardrail": live_predict_probe.get("api_trade_buy_guardrail"),
        "api_trade_allowed_actions": allowed_actions,
        "api_trade_allowed_risk_off_sides": risk_off_sides,
        "api_trade_allowed_paper_shadow_sides": paper_shadow_sides,
    }

    machine_checks = {
        "current_lane_is_no_trade_block_lane": no_trade_lane,
        "should_trade_false": live_predict_probe.get("should_trade") is False,
        "allowed_layers_zero": _to_int(live_predict_probe.get("allowed_layers")) == 0,
        "drift_replay_shadow_only": drift_shadow_only,
        "risk_off_paths_visible": reduce_only_visible,
        "paper_shadow_paths_visible": paper_shadow_visible,
        "support_evidence_not_deployable": support_evidence_role == "no_trade_decision_validation_not_deployable_support",
        "buy_add_support_closure_allowed": False,
        "risk_on_order_enabled": False,
        "order_submission_enabled": False,
        "live_exposure_allowed": False,
    }
    machine_checks["all_passed"] = all(
        bool(machine_checks[key])
        for key in [
            "current_lane_is_no_trade_block_lane",
            "should_trade_false",
            "allowed_layers_zero",
            "drift_replay_shadow_only",
            "risk_off_paths_visible",
            "paper_shadow_paths_visible",
            "support_evidence_not_deployable",
        ]
    )

    replay = {
        "source": "data/live_predict_probe.json + data/recent_drift_report.json",
        "mode": "abstain_reduce_only_no_trade_lane_replay",
        "abstain_path": {
            "validated": replay_validated,
            "operator_action": "等待 / 觀望",
            "adds_new_risk": False,
            "risk_on_order_enabled": False,
            "order_submission_enabled": False,
            "evidence": "signal/should_trade/allowed_layers/runtime guardrail all point to no new buy/add exposure.",
        },
        "reduce_only_path": {
            "validated": reduce_only_visible,
            "operator_action": "減碼 / 賣出風險降低",
            "adds_new_risk": False,
            "allowed_risk_off_sides": risk_off_sides,
            "requires_existing_exposure": True,
        },
        "paper_shadow_path": {
            "validated": paper_shadow_visible,
            "operator_action": "shadow_buy / paper_buy dry-run rehearsal",
            "live_order_submitted": False,
            "allowed_paper_shadow_sides": paper_shadow_sides,
        },
        "recent_drift_shadow_context": shadow_context,
        "decision_quality_context": {
            "chosen_scope": drilldown.get("chosen_scope"),
            "recent_pathology_reason": drilldown.get("recent_pathology_reason"),
            "exact_live_lane_rows": (drilldown.get("exact_live_lane_summary") or {}).get("rows")
            if isinstance(drilldown.get("exact_live_lane_summary"), dict)
            else None,
            "exact_live_lane_win_rate": (drilldown.get("exact_live_lane_summary") or {}).get("win_rate")
            if isinstance(drilldown.get("exact_live_lane_summary"), dict)
            else None,
        },
    }

    return {
        "generated_at": generated_at or _now_iso(),
        "artifact": "no_trade_lane_replay",
        "source_artifacts": _source_meta(
            {
                "live_predict_probe": live_predict_probe,
                "recent_drift_report": recent_drift_report,
                "live_canary_structural_pivot": pivot,
                "live_decision_quality_drilldown": drilldown,
                "customer_safe_alternative_proof": customer_safe,
            }
        ),
        "current_truth": current_truth,
        "replay_decision": {
            "verdict": verdict,
            "validated": replay_validated,
            "deployable": False,
            "deployment_verdict": "not_deployable_no_trade_decision_validation",
            "support_evidence_role": support_evidence_role,
            "buy_add_support_closure_allowed": False,
            "support_rows_counted_for_buy_add": False,
            "risk_on_order_enabled": False,
            "order_submission_enabled": False,
            "live_exposure_allowed": False,
            "operator_summary": (
                "當前 BLOCK / 不交易 lane 的 replay 結論是等待 / 觀望、減風險與 paper-shadow 可用；"
                "這份 artifact 不能作為買入 / 加倉 support closure。"
            ),
            "next_validation_artifact": "data/no_trade_lane_replay.json",
            "structural_pivot_next_artifact": pivot_decision.get("map_signal_next_validation_artifact"),
        },
        "replay": replay,
        "machine_checks": machine_checks,
        "customer_value_delta": (
            "把 current BLOCK lane 從口頭 no-go 轉成可重跑 abstain / reduce-only / paper-shadow replay proof，"
            "同時保留 live buy/add fail-closed。"
        ),
        "fail_closed_invariants": {
            "buy_add_live_exposure_forbidden": True,
            "reference_or_no_trade_support_not_deployable": True,
            "paper_shadow_is_not_live_order": True,
            "reduce_only_does_not_add_new_risk": True,
        },
    }


def render_markdown(payload: Mapping[str, Any]) -> str:
    truth = payload.get("current_truth") if isinstance(payload.get("current_truth"), Mapping) else {}
    decision = payload.get("replay_decision") if isinstance(payload.get("replay_decision"), Mapping) else {}
    replay = payload.get("replay") if isinstance(payload.get("replay"), Mapping) else {}
    drift = replay.get("recent_drift_shadow_context") if isinstance(replay.get("recent_drift_shadow_context"), Mapping) else {}
    checks = payload.get("machine_checks") if isinstance(payload.get("machine_checks"), Mapping) else {}
    lines = [
        "# No-Trade Lane Replay",
        "",
        f"_Generated at: `{payload.get('generated_at', '—')}`_",
        "",
        "## Decision",
        f"- verdict: `{decision.get('verdict', '—')}` / validated: `{decision.get('validated')}`",
        f"- deployable: `{decision.get('deployable')}` / risk_on_order_enabled: `{decision.get('risk_on_order_enabled')}` / order_submission_enabled: `{decision.get('order_submission_enabled')}`",
        f"- support evidence role: `{decision.get('support_evidence_role', '—')}`",
        f"- buy/add support closure allowed: `{decision.get('buy_add_support_closure_allowed')}`",
        f"- operator summary: {decision.get('operator_summary', '—')}",
        "",
        "## Current Lane",
        f"- signal: `{truth.get('signal', '—')}` / should_trade: `{truth.get('should_trade')}` / deployment_blocker: `{truth.get('deployment_blocker', '—')}`",
        f"- bucket: `{truth.get('current_live_structure_bucket', '—')}` / actionability: `{truth.get('current_lane_actionability', '—')}`",
        f"- support: `{truth.get('support_rows', '—')}/{truth.get('minimum_support_rows', '—')}` / gap: `{truth.get('support_gap', '—')}` / route: `{truth.get('support_route_verdict', '—')}`",
        f"- allowed actions: `{', '.join(truth.get('api_trade_allowed_actions') or [])}`",
        f"- risk-off sides: `{', '.join(truth.get('api_trade_allowed_risk_off_sides') or [])}` / paper-shadow sides: `{', '.join(truth.get('api_trade_allowed_paper_shadow_sides') or [])}`",
        "",
        "## Replay Evidence",
        f"- abstain path validated: `{(replay.get('abstain_path') or {}).get('validated')}`",
        f"- reduce-only path validated: `{(replay.get('reduce_only_path') or {}).get('validated')}`",
        f"- paper-shadow path validated: `{(replay.get('paper_shadow_path') or {}).get('validated')}`",
        f"- recent drift mode: `{drift.get('mode', '—')}` / deployment verdict: `{drift.get('deployment_verdict', '—')}`",
        f"- recent window: `{drift.get('primary_window', '—')}` / win_rate: `{_pct_text(drift.get('primary_win_rate'))}` / dominant_regime: `{drift.get('dominant_regime', '—')}`",
        f"- best shadow gate: `{drift.get('best_gate_id', '—')}` / verdict: `{drift.get('best_gate_verdict', '—')}` / kept_win_rate: `{_pct_text(drift.get('kept_win_rate'))}`",
        "",
        "## Machine Checks",
    ]
    for key, value in checks.items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(payload: Mapping[str, Any], json_out: Path, markdown_out: Path) -> tuple[Path, Path]:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_out.write_text(render_markdown(payload), encoding="utf-8")
    return json_out, markdown_out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    args = parser.parse_args(argv)

    payloads = {name: _read_json(path) for name, path in SOURCE_PATHS.items()}
    payload = build_no_trade_lane_replay(
        live_predict_probe=payloads["live_predict_probe"],
        recent_drift_report=payloads["recent_drift_report"],
        live_canary_structural_pivot=payloads["live_canary_structural_pivot"],
        live_decision_quality_drilldown=payloads["live_decision_quality_drilldown"],
        customer_safe_alternative_proof=payloads["customer_safe_alternative_proof"],
    )
    json_path, md_path = write_outputs(payload, args.json_out, args.markdown_out)
    decision = payload["replay_decision"]
    truth = payload["current_truth"]
    print(
        "no_trade_lane_replay: "
        f"verdict={decision.get('verdict')} "
        f"validated={decision.get('validated')} "
        f"bucket={truth.get('current_live_structure_bucket')} "
        f"support={truth.get('support_rows')}/{truth.get('minimum_support_rows')} "
        f"deployable={decision.get('deployable')} "
        f"risk_on_order_enabled={decision.get('risk_on_order_enabled')} "
        f"json={json_path} md={md_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
