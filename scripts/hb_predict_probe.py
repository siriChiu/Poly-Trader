#!/usr/bin/env python
"""Heartbeat predictor probe.

Runs the canonical predictor path against the local DB and prints a compact JSON
summary that proves inference is aligned with the current feature stack.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.models import init_db
from model.predictor import load_latest_features, load_predictor, predict

DB_URL = f"sqlite:///{PROJECT_ROOT / 'poly_trader.db'}"
OUT_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
Q15_SUPPORT_AUDIT_PATH = PROJECT_ROOT / "data" / "q15_support_audit.json"
FOUR_H_COLS = [
    "feat_4h_bias50",
    "feat_4h_bias20",
    "feat_4h_bias200",
    "feat_4h_rsi14",
    "feat_4h_macd_hist",
    "feat_4h_bb_pct_b",
    "feat_4h_dist_bb_lower",
    "feat_4h_ma_order",
    "feat_4h_dist_swing_low",
    "feat_4h_vol_ratio",
]
LAG_STEPS = [12, 48, 288]


def _parse_isoish_timestamp(value) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _load_q15_support_audit(current_live_structure_bucket: str | None) -> dict | None:
    if not current_live_structure_bucket or "q15" not in str(current_live_structure_bucket):
        return None
    if not Q15_SUPPORT_AUDIT_PATH.exists():
        return None
    try:
        payload = json.loads(Q15_SUPPORT_AUDIT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    applicability = payload.get("scope_applicability") if isinstance(payload.get("scope_applicability"), dict) else {}
    if not applicability.get("active_for_current_live_row"):
        return None
    audit_bucket = (
        applicability.get("current_structure_bucket")
        or ((payload.get("current_live") or {}).get("current_live_structure_bucket"))
    )
    if audit_bucket and str(audit_bucket) != str(current_live_structure_bucket):
        return None
    return payload


def _q15_audit_matches_probe(payload: dict | None, *, current_live_structure_bucket: str | None, feature_timestamp: str | None) -> bool:
    if not payload:
        return False
    current_live = payload.get("current_live") if isinstance(payload.get("current_live"), dict) else {}
    applicability = payload.get("scope_applicability") if isinstance(payload.get("scope_applicability"), dict) else {}
    component_experiment = payload.get("component_experiment") if isinstance(payload.get("component_experiment"), dict) else {}
    machine_read = component_experiment.get("machine_read_answer") if isinstance(component_experiment.get("machine_read_answer"), dict) else {}
    positive_discrimination = component_experiment.get("positive_discrimination_evidence") if isinstance(component_experiment.get("positive_discrimination_evidence"), dict) else {}
    audit_bucket = applicability.get("current_structure_bucket") or current_live.get("current_live_structure_bucket")
    if current_live_structure_bucket and audit_bucket and str(audit_bucket) != str(current_live_structure_bucket):
        return False

    try:
        if not Q15_SUPPORT_AUDIT_PATH.exists() or not OUT_PATH.exists():
            return False
        if Q15_SUPPORT_AUDIT_PATH.stat().st_mtime + 1e-6 < OUT_PATH.stat().st_mtime:
            return False
    except OSError:
        return False

    probe_ts = _parse_isoish_timestamp(feature_timestamp)
    audit_ts = _parse_isoish_timestamp(payload.get("generated_at"))
    current_live_ts = _parse_isoish_timestamp(current_live.get("feature_timestamp"))
    comparable_audit_ts = current_live_ts or audit_ts
    if probe_ts is not None and comparable_audit_ts is not None:
        if abs((probe_ts - comparable_audit_ts).total_seconds()) >= 1:
            return False

    # Treat audit artifacts as stale when the q15 lane is exact-supported and component-ready
    # but the positive-discrimination check is still missing. This commonly happens when the
    # timestamp matches but the audit was generated before drilldown/probe surfaces converged.
    if (
        component_experiment.get("verdict") == "exact_supported_component_experiment_ready"
        and machine_read.get("support_ready")
        and machine_read.get("entry_quality_ge_0_55")
        and machine_read.get("allowed_layers_gt_0")
        and machine_read.get("preserves_positive_discrimination") is None
    ):
        status = str(machine_read.get("preserves_positive_discrimination_status") or positive_discrimination.get("status") or "")
        if status.startswith("not_measured"):
            return False

    return True


def _refresh_q15_support_audit(
    current_live_structure_bucket: str | None,
    feature_timestamp: str | None,
    *,
    force: bool = False,
) -> dict | None:
    if not current_live_structure_bucket or "q15" not in str(current_live_structure_bucket):
        return None
    current_payload = _load_q15_support_audit(current_live_structure_bucket)
    if (not force) and _q15_audit_matches_probe(
        current_payload,
        current_live_structure_bucket=current_live_structure_bucket,
        feature_timestamp=feature_timestamp,
    ):
        return current_payload

    script_path = PROJECT_ROOT / "scripts" / "hb_q15_support_audit.py"
    if not script_path.exists():
        return current_payload

    try:
        spec = importlib.util.spec_from_file_location("hb_q15_support_audit_runtime", script_path)
        if spec is None or spec.loader is None:
            return current_payload
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with contextlib.redirect_stdout(io.StringIO()):
            module.main()
    except Exception:
        return current_payload

    refreshed = _load_q15_support_audit(current_live_structure_bucket)
    return refreshed or current_payload


def _q15_patch_supported_by_audit(payload: dict | None) -> bool:
    if not isinstance(payload, dict):
        return False
    support_route = payload.get("support_route") if isinstance(payload.get("support_route"), dict) else {}
    floor_cross = payload.get("floor_cross_legality") if isinstance(payload.get("floor_cross_legality"), dict) else {}
    component_experiment = payload.get("component_experiment") if isinstance(payload.get("component_experiment"), dict) else {}
    machine_read = component_experiment.get("machine_read_answer") if isinstance(component_experiment.get("machine_read_answer"), dict) else {}
    return bool(
        support_route.get("verdict") == "exact_bucket_supported"
        and support_route.get("deployable")
        and floor_cross.get("verdict") == "legal_component_experiment_after_support_ready"
        and floor_cross.get("legal_to_relax_runtime_gate")
        and component_experiment.get("verdict") == "exact_supported_component_experiment_ready"
        and component_experiment.get("feature") == "feat_4h_bias50"
        and machine_read.get("support_ready")
        and machine_read.get("entry_quality_ge_0_55")
        and machine_read.get("allowed_layers_gt_0")
        and machine_read.get("preserves_positive_discrimination")
    )


def _q15_audit_current_live_matches_probe(payload: dict | None, probe: dict | None) -> bool:
    if not isinstance(payload, dict) or not isinstance(probe, dict):
        return False
    current_live = payload.get("current_live") if isinstance(payload.get("current_live"), dict) else {}
    if not current_live:
        return False
    probe_ts = str(probe.get("feature_timestamp") or "")
    audit_ts = str(current_live.get("feature_timestamp") or payload.get("generated_at") or "")
    if probe_ts and audit_ts and probe_ts != audit_ts:
        return False
    comparable_pairs = (
        ("entry_quality", current_live.get("entry_quality"), probe.get("entry_quality")),
        ("entry_quality_label", current_live.get("entry_quality_label"), probe.get("entry_quality_label")),
        ("allowed_layers", current_live.get("allowed_layers"), probe.get("allowed_layers")),
        ("allowed_layers_reason", current_live.get("allowed_layers_reason"), probe.get("allowed_layers_reason")),
    )
    for key, audit_value, probe_value in comparable_pairs:
        if key == "entry_quality":
            try:
                if abs(float(audit_value) - float(probe_value)) > 1e-6:
                    return False
            except (TypeError, ValueError):
                return False
        else:
            if audit_value != probe_value:
                return False
    return True


def _build_probe_payload(
    *,
    latest: dict,
    result: dict,
    target_col,
    used_model,
    current_live_structure_bucket,
    current_live_structure_bucket_rows,
    q15_support_audit: dict | None,
    four_h_non_null: dict,
    lag_non_null: dict,
) -> dict:
    support_route = q15_support_audit.get("support_route") if isinstance((q15_support_audit or {}).get("support_route"), dict) else {}
    support_progress = support_route.get("support_progress") if isinstance(support_route.get("support_progress"), dict) else {}
    floor_cross = q15_support_audit.get("floor_cross_legality") if isinstance((q15_support_audit or {}).get("floor_cross_legality"), dict) else {}
    component_experiment = q15_support_audit.get("component_experiment") if isinstance((q15_support_audit or {}).get("component_experiment"), dict) else {}
    deployment_blocker_details = result.get("deployment_blocker_details") if isinstance(result.get("deployment_blocker_details"), dict) else {}
    breaker_release = deployment_blocker_details.get("release_condition") if isinstance(deployment_blocker_details.get("release_condition"), dict) else {}
    breaker_recent_window = deployment_blocker_details.get("recent_window") if isinstance(deployment_blocker_details.get("recent_window"), dict) else {}
    release_window = breaker_release.get("recent_window") or breaker_recent_window.get("window_size") or 50
    release_floor = breaker_release.get("recent_win_rate_must_be_at_least")
    release_wins = breaker_release.get("required_recent_window_wins")
    release_gap = breaker_release.get("additional_recent_window_wins_needed")
    current_wins = breaker_release.get("current_recent_window_wins")
    return {
        "db_url": DB_URL,
        "feature_timestamp": str(latest.get("timestamp")),
        "target_col": target_col,
        "used_model": used_model,
        "model_type": result.get("model_type"),
        "signal": result.get("signal"),
        "confidence": round(float(result.get("confidence", 0.0)), 6),
        "should_trade": bool(result.get("should_trade", False)),
        "reason": result.get("reason"),
        "streak": result.get("streak"),
        "win_rate": result.get("win_rate"),
        "recent_window_win_rate": result.get("recent_window_win_rate"),
        "recent_window_wins": result.get("recent_window_wins"),
        "window_size": result.get("window_size"),
        "triggered_by": result.get("triggered_by"),
        "horizon_minutes": result.get("horizon_minutes"),
        "regime_label": result.get("regime_label") or latest.get("regime_label"),
        "model_route_regime": result.get("model_route_regime"),
        "regime_gate": result.get("regime_gate"),
        "structure_bucket": result.get("structure_bucket"),
        "current_live_structure_bucket": current_live_structure_bucket,
        "current_live_structure_bucket_rows": current_live_structure_bucket_rows,
        "entry_quality": result.get("entry_quality"),
        "entry_quality_label": result.get("entry_quality_label"),
        "entry_quality_components": result.get("entry_quality_components"),
        "q35_discriminative_redesign_applied": result.get("q35_discriminative_redesign_applied"),
        "q35_discriminative_redesign": result.get("q35_discriminative_redesign"),
        "q15_exact_supported_component_patch_applied": result.get("q15_exact_supported_component_patch_applied"),
        "allowed_layers_raw": result.get("allowed_layers_raw"),
        "allowed_layers_raw_reason": result.get("allowed_layers_raw_reason"),
        "allowed_layers": result.get("allowed_layers"),
        "allowed_layers_reason": result.get("allowed_layers_reason"),
        "execution_guardrail_applied": result.get("execution_guardrail_applied"),
        "execution_guardrail_reason": result.get("execution_guardrail_reason"),
        "deployment_blocker": result.get("deployment_blocker"),
        "deployment_blocker_reason": result.get("deployment_blocker_reason"),
        "deployment_blocker_source": result.get("deployment_blocker_source"),
        "deployment_blocker_details": deployment_blocker_details,
        "support_route_verdict": support_route.get("verdict"),
        "support_route_deployable": support_route.get("deployable"),
        "support_progress": support_progress or None,
        "minimum_support_rows": support_progress.get("minimum_support_rows"),
        "current_live_structure_bucket_gap_to_minimum": support_progress.get("gap_to_minimum"),
        "floor_cross_verdict": floor_cross.get("verdict"),
        "legal_to_relax_runtime_gate": floor_cross.get("legal_to_relax_runtime_gate"),
        "remaining_gap_to_floor": floor_cross.get("remaining_gap_to_floor"),
        "best_single_component": floor_cross.get("best_single_component"),
        "best_single_component_required_score_delta": floor_cross.get("best_single_component_required_score_delta"),
        "component_experiment_verdict": component_experiment.get("verdict"),
        "runtime_closure_state": (
            "circuit_breaker_active"
            if result.get("signal") == "CIRCUIT_BREAKER"
            else (
                "capacity_opened_signal_hold"
                if result.get("q15_exact_supported_component_patch_applied") and result.get("signal") == "HOLD" and (result.get("allowed_layers") or 0) > 0
                else (
                    "patch_active_but_execution_blocked"
                    if result.get("q15_exact_supported_component_patch_applied") and (
                        result.get("deployment_blocker")
                        or result.get("execution_guardrail_applied")
                        or (result.get("allowed_layers") or 0) <= 0
                    )
                    else "patch_inactive_or_blocked"
                )
            )
        ),
        "runtime_closure_summary": (
            (
                f"circuit breaker active：{result.get('reason')}; release condition = streak < {breaker_release.get('streak_must_be_below', 50)} 且 recent {release_window} win rate >= {((release_floor if isinstance(release_floor, (int, float)) else 0.3) * 100):.0f}%"
                + (
                    f"；目前 recent {release_window} 只贏 {current_wins}/{release_window}，至少還差 {release_gap} 勝。"
                    if release_gap not in (None, 0) and current_wins is not None
                    else "。"
                )
                + (
                    f" 同時 recent pathology={result.get('decision_quality_recent_pathology_reason')}。"
                    if result.get("decision_quality_recent_pathology_applied")
                    and result.get("decision_quality_recent_pathology_reason")
                    else ""
                )
            )
            if result.get("signal") == "CIRCUIT_BREAKER"
            else (
                "support-ready + patch active；runtime 已開出 1 層 deployment capacity，但 signal 仍是 HOLD，不等於自動 BUY。"
                if result.get("q15_exact_supported_component_patch_applied") and result.get("signal") == "HOLD" and (result.get("allowed_layers") or 0) > 0
                else (
                    f"q15 patch 已啟用並把 entry_quality 拉到 {float(result.get('entry_quality') or 0.0):.4f}，但 execution 仍被 blocker / guardrail 擋住；目前不可把 patch active 誤讀成可部署。"
                    if result.get("q15_exact_supported_component_patch_applied") and (
                        result.get("deployment_blocker")
                        or result.get("execution_guardrail_applied")
                        or (result.get("allowed_layers") or 0) <= 0
                    )
                    else None
                )
            )
        ),
        "q15_support_audit": q15_support_audit,
        "decision_quality_horizon_minutes": result.get("decision_quality_horizon_minutes"),
        "decision_quality_calibration_scope": result.get("decision_quality_calibration_scope"),
        "decision_quality_calibration_window": result.get("decision_quality_calibration_window"),
        "decision_quality_sample_size": result.get("decision_quality_sample_size"),
        "decision_quality_scope_diagnostics": result.get("decision_quality_scope_diagnostics"),
        "decision_quality_reference_from": result.get("decision_quality_reference_from"),
        "decision_quality_guardrail_applied": result.get("decision_quality_guardrail_applied"),
        "decision_quality_guardrail_reason": result.get("decision_quality_guardrail_reason"),
        "decision_quality_recent_pathology_applied": result.get("decision_quality_recent_pathology_applied"),
        "decision_quality_recent_pathology_window": result.get("decision_quality_recent_pathology_window"),
        "decision_quality_recent_pathology_alerts": result.get("decision_quality_recent_pathology_alerts"),
        "decision_quality_recent_pathology_reason": result.get("decision_quality_recent_pathology_reason"),
        "decision_quality_recent_pathology_summary": result.get("decision_quality_recent_pathology_summary"),
        "decision_quality_exact_live_lane_toxicity_applied": result.get("decision_quality_exact_live_lane_toxicity_applied"),
        "decision_quality_exact_live_lane_status": result.get("decision_quality_exact_live_lane_status"),
        "decision_quality_exact_live_lane_reason": result.get("decision_quality_exact_live_lane_reason"),
        "decision_quality_exact_live_lane_summary": result.get("decision_quality_exact_live_lane_summary"),
        "decision_quality_exact_live_lane_bucket_verdict": result.get("decision_quality_exact_live_lane_bucket_verdict"),
        "decision_quality_exact_live_lane_bucket_reason": result.get("decision_quality_exact_live_lane_bucket_reason"),
        "decision_quality_exact_live_lane_toxic_bucket": result.get("decision_quality_exact_live_lane_toxic_bucket"),
        "decision_quality_exact_live_lane_bucket_diagnostics": result.get("decision_quality_exact_live_lane_bucket_diagnostics"),
        "decision_quality_narrowed_pathology_applied": result.get("decision_quality_narrowed_pathology_applied"),
        "decision_quality_narrowed_pathology_scope": result.get("decision_quality_narrowed_pathology_scope"),
        "decision_quality_narrowed_pathology_reason": result.get("decision_quality_narrowed_pathology_reason"),
        "expected_win_rate": result.get("expected_win_rate"),
        "expected_pyramid_pnl": result.get("expected_pyramid_pnl"),
        "expected_pyramid_quality": result.get("expected_pyramid_quality"),
        "expected_drawdown_penalty": result.get("expected_drawdown_penalty"),
        "expected_time_underwater": result.get("expected_time_underwater"),
        "decision_quality_score": result.get("decision_quality_score"),
        "decision_quality_label": result.get("decision_quality_label"),
        "decision_profile_version": result.get("decision_profile_version"),
        "non_null_4h_features": sorted(four_h_non_null.keys()),
        "non_null_4h_feature_count": len(four_h_non_null),
        "non_null_4h_lags": sorted(lag_non_null.keys()),
        "non_null_4h_lag_count": len(lag_non_null),
    }


def main() -> None:
    session = init_db(DB_URL)
    try:
        predictor, regime_models = load_predictor()
        latest = load_latest_features(session)
        result = predict(session, predictor, regime_models)
        if latest is None or result is None:
            raise SystemExit("predictor probe failed: latest features or prediction result is missing")

        target_col = result.get("target_col") or getattr(getattr(predictor, "_global", predictor), "_target_col", None)
        used_model = result.get("used_model") or result.get("model_type")
        four_h_non_null = {col: latest.get(col) for col in FOUR_H_COLS if latest.get(col) is not None}
        lag_non_null = {
            f"{col}_lag{lag}": latest.get(f"{col}_lag{lag}")
            for col in FOUR_H_COLS
            for lag in LAG_STEPS
            if latest.get(f"{col}_lag{lag}") is not None
        }
        scope_diagnostics = result.get("decision_quality_scope_diagnostics") or {}
        exact_scope = scope_diagnostics.get("regime_label+regime_gate+entry_quality_label") or {}
        blocker_details = result.get("deployment_blocker_details") or {}
        current_live_structure_bucket = (
            result.get("decision_quality_live_structure_bucket")
            or exact_scope.get("current_live_structure_bucket")
            or result.get("structure_bucket")
        )
        current_live_structure_bucket_rows = (
            result.get("decision_quality_exact_live_structure_bucket_support_rows")
            or blocker_details.get("exact_live_structure_bucket_rows")
            or blocker_details.get("current_live_structure_bucket_rows")
            or exact_scope.get("current_live_structure_bucket_rows")
        )
        q15_support_audit = _load_q15_support_audit(current_live_structure_bucket)
        probe = _build_probe_payload(
            latest=latest,
            result=result,
            target_col=target_col,
            used_model=used_model,
            current_live_structure_bucket=current_live_structure_bucket,
            current_live_structure_bucket_rows=current_live_structure_bucket_rows,
            q15_support_audit=q15_support_audit,
            four_h_non_null=four_h_non_null,
            lag_non_null=lag_non_null,
        )
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(json.dumps(probe, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

        refreshed_q15_support_audit = _refresh_q15_support_audit(
            current_live_structure_bucket=current_live_structure_bucket,
            feature_timestamp=probe.get("feature_timestamp"),
        )
        if refreshed_q15_support_audit:
            refreshed_patch_supported = _q15_patch_supported_by_audit(refreshed_q15_support_audit)
            result_patch_applied = bool(result.get("q15_exact_supported_component_patch_applied"))
            if result_patch_applied != refreshed_patch_supported:
                result = predict(session, predictor, regime_models)
                if result is None:
                    raise SystemExit("predictor probe failed: refreshed q15 audit changed patch readiness but replay prediction returned no result")
                current_live_structure_bucket = (
                    result.get("decision_quality_live_structure_bucket")
                    or ((result.get("decision_quality_scope_diagnostics") or {}).get("regime_label+regime_gate+entry_quality_label") or {}).get("current_live_structure_bucket")
                    or result.get("structure_bucket")
                )
                blocker_details = result.get("deployment_blocker_details") or {}
                current_live_structure_bucket_rows = (
                    result.get("decision_quality_exact_live_structure_bucket_support_rows")
                    or blocker_details.get("exact_live_structure_bucket_rows")
                    or blocker_details.get("current_live_structure_bucket_rows")
                    or (((result.get("decision_quality_scope_diagnostics") or {}).get("regime_label+regime_gate+entry_quality_label") or {}).get("current_live_structure_bucket_rows"))
                )
            probe = _build_probe_payload(
                latest=latest,
                result=result,
                target_col=target_col,
                used_model=used_model,
                current_live_structure_bucket=current_live_structure_bucket,
                current_live_structure_bucket_rows=current_live_structure_bucket_rows,
                q15_support_audit=refreshed_q15_support_audit,
                four_h_non_null=four_h_non_null,
                lag_non_null=lag_non_null,
            )
            OUT_PATH.write_text(json.dumps(probe, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

            if not _q15_audit_current_live_matches_probe(refreshed_q15_support_audit, probe):
                synced_q15_support_audit = _refresh_q15_support_audit(
                    current_live_structure_bucket=current_live_structure_bucket,
                    feature_timestamp=probe.get("feature_timestamp"),
                    force=True,
                )
                if synced_q15_support_audit:
                    probe = _build_probe_payload(
                        latest=latest,
                        result=result,
                        target_col=target_col,
                        used_model=used_model,
                        current_live_structure_bucket=current_live_structure_bucket,
                        current_live_structure_bucket_rows=current_live_structure_bucket_rows,
                        q15_support_audit=synced_q15_support_audit,
                        four_h_non_null=four_h_non_null,
                        lag_non_null=lag_non_null,
                    )
                    OUT_PATH.write_text(json.dumps(probe, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

        print(json.dumps(probe, ensure_ascii=False, indent=2, default=str))
    finally:
        session.close()


if __name__ == "__main__":
    main()
