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
from model.runtime_closure import (
    build_circuit_breaker_release_surface as shared_circuit_breaker_release_surface,
    runtime_patch_name as shared_runtime_patch_name,
    build_runtime_closure_state as shared_runtime_closure_state,
    build_runtime_closure_summary as shared_runtime_closure_summary,
    _humanize_runtime_text as shared_humanize_runtime_text,
)
from server.live_pathology_summary import build_live_pathology_scope_surface

DB_URL = f"sqlite:///{PROJECT_ROOT / 'poly_trader.db'}"
OUT_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
Q15_SUPPORT_AUDIT_PATH = PROJECT_ROOT / "data" / "q15_support_audit.json"
Q15_BUCKET_ROOT_CAUSE_PATH = PROJECT_ROOT / "data" / "q15_bucket_root_cause.json"
Q35_SCALING_AUDIT_PATH = PROJECT_ROOT / "data" / "q35_scaling_audit.json"
BULL_4H_POCKET_ABLATION_PATH = PROJECT_ROOT / "data" / "bull_4h_pocket_ablation.json"
NO_DEPLOY_RUNTIME_CLOSURE_STATES = {
    "circuit_breaker_active",
    "decision_quality_below_trade_floor",
    "patch_active_but_execution_blocked",
    "support_closed_but_trade_floor_blocked",
    "unsupported_exact_live_structure_bucket",
    "under_minimum_exact_live_structure_bucket",
}
API_TRADE_RISK_OFF_SIDES = ["reduce", "sell"]
API_TRADE_BLOCKED_ALLOWED_ACTIONS = ["wait", "reduce", "sell", "diagnostics", "mode_toggle"]
SUPPORT_ROUTE_OPERATOR_LABELS = {
    "exact_bucket_supported": "精準樣本已就緒",
    "exact_bucket_present_but_below_minimum": "精準樣本未達最小門檻",
    "exact_bucket_unsupported_block": "精準樣本尚未建立",
    "exact_bucket_missing_proxy_reference_only": "僅有近似樣本可作治理參考",
    "exact_bucket_missing_exact_lane_proxy_only": "僅有精準路徑近似樣本可作治理參考",
    "insufficient_support_everywhere": "所有支持路徑仍不足",
    "exact_live_bucket_supported": "目前即時分桶精準樣本已就緒",
    "exact_live_bucket_present_but_below_minimum": "目前即時分桶精準樣本未達最小門檻",
    "exact_live_bucket_proxy_available": "目前即時分桶僅有近似樣本可作治理參考",
    "exact_live_lane_proxy_available": "目前即時路徑僅有近似樣本可作治理參考",
    "no_support_proxy": "目前沒有可用近似樣本",
}
GENERIC_ZERO_EXACT_SUPPORT_VERDICTS = {
    "",
    "insufficient_support_everywhere",
    "exact_bucket_missing_proxy_reference_only",
    "exact_bucket_missing_exact_lane_proxy_only",
    "exact_bucket_present_but_below_minimum",
}
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



def _support_route_operator_label(verdict: object) -> str:
    if verdict is None:
        return "精準支持路徑未知"
    return SUPPORT_ROUTE_OPERATOR_LABELS.get(str(verdict), "精準支持路徑未知")



def _nonnegative_int_or_none(value) -> int | None:
    if value is None:
        return None
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return None



def _is_q15_current_bucket(current_live_structure_bucket: object) -> bool:
    return "q15" in str(current_live_structure_bucket or "")



def _normalize_generic_exact_support_route(
    *,
    support_route: dict,
    support_progress: dict,
    current_live_structure_bucket,
    current_live_structure_bucket_rows,
    minimum_support_rows,
) -> tuple[dict, dict]:
    """Canonicalize non-q15 exact-support truth for product surfaces.

    q15 audits can describe a non-q15 live row as `insufficient_support_everywhere` or
    proxy-reference-only.  For Dashboard/API/probe current-live truth, exact rows 0/50 must
    still surface as the generic unsupported exact-bucket blocker; proxy availability belongs
    in `support_governance_route`, not in the primary support-route verdict.
    """
    route = dict(support_route) if isinstance(support_route, dict) else {}
    progress = dict(support_progress) if isinstance(support_progress, dict) else {}
    progress_rows = _nonnegative_int_or_none(progress.get("current_rows"))
    current_rows = progress_rows
    if current_rows is None:
        current_rows = _nonnegative_int_or_none(current_live_structure_bucket_rows)
    minimum_rows = _nonnegative_int_or_none(progress.get("minimum_support_rows"))
    if minimum_rows is None:
        minimum_rows = _nonnegative_int_or_none(minimum_support_rows)

    if (
        current_rows == 0
        and minimum_rows is not None
        and minimum_rows > 0
        and not _is_q15_current_bucket(current_live_structure_bucket)
    ):
        verdict = str(route.get("verdict") or "")
        if verdict in GENERIC_ZERO_EXACT_SUPPORT_VERDICTS:
            route["verdict"] = "exact_bucket_unsupported_block"
            route["deployable"] = False
        if route.get("support_governance_route") == "exact_live_bucket_present_but_below_minimum":
            # 0 rows is unsupported/no-proxy unless later pathology context proves a proxy route.
            route.pop("support_governance_route", None)
        if not progress:
            progress = {
                "status": "stalled_under_minimum",
                "current_rows": 0,
                "minimum_support_rows": minimum_rows,
                "gap_to_minimum": minimum_rows,
            }
        else:
            progress["current_rows"] = 0
            progress["minimum_support_rows"] = minimum_rows
            progress["gap_to_minimum"] = minimum_rows
            if progress.get("status") in {None, "", "no_recent_comparable_history"}:
                progress["status"] = "stalled_under_minimum"
        route["support_progress"] = progress

    return route, progress



def _support_governance_route_from_patch(recommended_patch: dict | None) -> str | None:
    if not isinstance(recommended_patch, dict):
        return None
    cohort = str(recommended_patch.get("preferred_support_cohort") or "")
    if not cohort:
        return None
    if (
        "exact_live_bucket_proxy" in cohort
        or "exact_bucket_proxy" in cohort
        or "exact_lane_bucket_proxy" in cohort
    ):
        return "exact_live_bucket_proxy_available"
    if "exact_live_lane_proxy" in cohort or "exact_lane_proxy" in cohort:
        return "exact_live_lane_proxy_available"
    if "neighbor" in cohort or "support_aware" in cohort:
        return "supported_neighbor_only"
    return None



def _infer_support_governance_route(
    *,
    support_route: dict,
    deployment_blocker_details: dict,
    current_live_structure_bucket_rows,
    minimum_support_rows,
    scope_pathology_summary: dict | None,
) -> str | None:
    try:
        current_rows = max(int(current_live_structure_bucket_rows or 0), 0)
    except (TypeError, ValueError):
        current_rows = 0
    try:
        minimum_rows = max(int(minimum_support_rows or 0), 0)
    except (TypeError, ValueError):
        minimum_rows = 0

    existing = support_route.get("support_governance_route")
    if existing is None:
        existing = deployment_blocker_details.get("support_governance_route")
    if existing is not None:
        impossible_zero_row_routes = {
            "exact_live_bucket_present_but_below_minimum",
            "exact_live_bucket_supported",
        }
        if current_rows > 0 or str(existing) not in impossible_zero_row_routes:
            return existing

    verdict = support_route.get("verdict") or deployment_blocker_details.get("support_route_verdict")

    if current_rows > 0:
        if minimum_rows <= 0 or current_rows >= minimum_rows or verdict == "exact_bucket_supported":
            return "exact_live_bucket_supported"
        return "exact_live_bucket_present_but_below_minimum"

    if verdict in {"exact_bucket_unsupported_block", *GENERIC_ZERO_EXACT_SUPPORT_VERDICTS}:
        patch_route = _support_governance_route_from_patch(
            (scope_pathology_summary or {}).get("recommended_patch")
            if isinstance(scope_pathology_summary, dict)
            else None
        )
        if patch_route is not None:
            return patch_route
        return "no_support_proxy"

    return None



def _load_q15_support_audit(current_live_structure_bucket: str | None) -> dict | None:
    if not current_live_structure_bucket:
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
    current_live = payload.get("current_live") if isinstance(payload.get("current_live"), dict) else {}
    support_route = payload.get("support_route") if isinstance(payload.get("support_route"), dict) else {}
    support_progress = support_route.get("support_progress") if isinstance(support_route.get("support_progress"), dict) else {}
    support_identity = support_route.get("support_identity") if isinstance(support_route.get("support_identity"), dict) else {}
    if not support_identity and isinstance(support_progress.get("support_identity"), dict):
        support_identity = support_progress.get("support_identity") or {}

    audit_bucket = (
        applicability.get("current_structure_bucket")
        or current_live.get("current_live_structure_bucket")
        or current_live.get("structure_bucket")
        or support_identity.get("current_live_structure_bucket")
    )
    if audit_bucket and str(audit_bucket) != str(current_live_structure_bucket):
        return None

    is_q15_context = "q15" in str(current_live_structure_bucket) or "q15" in str(audit_bucket or "")
    if is_q15_context:
        if not applicability.get("active_for_current_live_row"):
            return None
        return payload

    # The q15 audit artifact also carries current-live support-route/progress
    # truth when the live row has drifted to q35.  Keep that support truth
    # visible while leaving the component experiment reference-only.
    current_live_bucket = current_live.get("current_live_structure_bucket") or current_live.get("structure_bucket")
    identity_bucket = support_identity.get("current_live_structure_bucket")
    if (
        str(current_live_bucket or identity_bucket or "") == str(current_live_structure_bucket)
        and (support_route.get("verdict") is not None or support_progress)
    ):
        return payload
    return None


def _load_q15_bucket_root_cause_summary(current_live_structure_bucket: str | None) -> dict | None:
    """Load the current-bucket root-cause artifact for probe/runtime surfaces.

    The artifact name is historical (q15), but the report now describes the
    *current live bucket* (q00/q15/q35).  Keep the summary compact and require
    the artifact bucket to match the freshly computed probe bucket so a stale
    q15 root-cause report cannot leak into a q00/q35 live row.
    """
    if not Q15_BUCKET_ROOT_CAUSE_PATH.exists():
        return None
    try:
        payload = json.loads(Q15_BUCKET_ROOT_CAUSE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None

    current_live = payload.get("current_live") if isinstance(payload.get("current_live"), dict) else {}
    exact_live_lane = payload.get("exact_live_lane") if isinstance(payload.get("exact_live_lane"), dict) else {}
    candidate_patch = payload.get("candidate_patch") if isinstance(payload.get("candidate_patch"), dict) else {}
    floor_gap = payload.get("floor_gap_attribution") if isinstance(payload.get("floor_gap_attribution"), dict) else {}
    artifact_context = (
        payload.get("artifact_context_freshness")
        if isinstance(payload.get("artifact_context_freshness"), dict)
        else {}
    )

    bucket = current_live.get("structure_bucket") or current_live.get("current_live_structure_bucket")
    if current_live_structure_bucket and bucket and str(bucket) != str(current_live_structure_bucket):
        return None

    return {
        "generated_at": payload.get("generated_at"),
        "current_live_structure_bucket": bucket or current_live_structure_bucket,
        "bucket_scope_label": payload.get("bucket_scope_label"),
        "verdict": payload.get("verdict"),
        "candidate_patch_type": payload.get("candidate_patch_type"),
        "candidate_patch_feature": payload.get("candidate_patch_feature"),
        "reason": payload.get("reason"),
        "verify_next": payload.get("verify_next"),
        "structure_quality": current_live.get("structure_quality"),
        "q15_threshold": current_live.get("q15_threshold"),
        "q35_threshold": current_live.get("q35_threshold"),
        "support_status": current_live.get("support_status"),
        "support_route_verdict": current_live.get("support_route_verdict"),
        "support_current_rows": current_live.get("support_current_rows"),
        "support_minimum_rows": current_live.get("support_minimum_rows"),
        "support_gap_to_minimum": current_live.get("support_gap_to_minimum"),
        "gap_to_q35_boundary": current_live.get("gap_to_q35_boundary"),
        "dominant_neighbor_bucket": exact_live_lane.get("dominant_neighbor_bucket"),
        "dominant_neighbor_rows": exact_live_lane.get("dominant_neighbor_rows"),
        "near_boundary_rows": exact_live_lane.get("near_boundary_rows"),
        "candidate_patch": candidate_patch or None,
        "trade_floor": floor_gap.get("trade_floor"),
        "entry_quality": floor_gap.get("entry_quality"),
        "remaining_gap_to_floor": floor_gap.get("remaining_gap_to_floor"),
        "best_single_component": floor_gap.get("best_single_component"),
        "single_component_floor_crossers": floor_gap.get("single_component_floor_crossers") or [],
        "artifact_context_freshness_verdict": artifact_context.get("verdict"),
        "artifact_context_freshness_mismatched_fields": artifact_context.get("mismatched_fields") or [],
        "reference_mismatched_fields": artifact_context.get("reference_mismatched_fields") or [],
        "reference_artifact_warning": artifact_context.get("reference_artifact_warning"),
    }


def _load_q35_scaling_audit_summary(current_live_structure_bucket: str | None) -> dict | None:
    if not current_live_structure_bucket or "q35" not in str(current_live_structure_bucket):
        return None
    if not Q35_SCALING_AUDIT_PATH.exists():
        return None
    try:
        payload = json.loads(Q35_SCALING_AUDIT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    applicability = payload.get("scope_applicability") if isinstance(payload.get("scope_applicability"), dict) else {}
    if not applicability.get("active_for_current_live_row"):
        return None
    audit_bucket = (
        applicability.get("current_structure_bucket")
        or ((payload.get("current_live") or {}).get("structure_bucket"))
        or current_live_structure_bucket
    )
    if audit_bucket and str(audit_bucket) != str(current_live_structure_bucket):
        return None
    segmented_calibration = payload.get("segmented_calibration") if isinstance(payload.get("segmented_calibration"), dict) else {}
    deployment_grade = payload.get("deployment_grade_component_experiment") if isinstance(payload.get("deployment_grade_component_experiment"), dict) else {}
    redesign = payload.get("base_stack_redesign_experiment") if isinstance(payload.get("base_stack_redesign_experiment"), dict) else {}
    recommended_mode = segmented_calibration.get("recommended_mode")
    next_patch_target = deployment_grade.get("next_patch_target")
    root_cause_action = recommended_mode or ("base_stack_redesign" if redesign.get("verdict") else None)
    redesign_machine = redesign.get("machine_read_answer") if isinstance(redesign.get("machine_read_answer"), dict) else {}
    redesign_best = redesign.get("best_discriminative_candidate") if isinstance(redesign.get("best_discriminative_candidate"), dict) else {}
    return {
        "generated_at": payload.get("generated_at"),
        "current_live_structure_bucket": audit_bucket or current_live_structure_bucket,
        "target_structure_bucket": applicability.get("target_structure_bucket"),
        "scope_applicability_status": applicability.get("status"),
        "overall_verdict": payload.get("overall_verdict"),
        "verdict": payload.get("overall_verdict"),
        "verdict_reason": payload.get("verdict_reason"),
        "reason": payload.get("recommended_action") or payload.get("verdict_reason"),
        "recommended_action": payload.get("recommended_action"),
        "segmented_calibration_status": segmented_calibration.get("status"),
        "recommended_mode": recommended_mode,
        "candidate_patch_type": root_cause_action,
        "candidate_patch_feature": next_patch_target,
        "runtime_contract_status": segmented_calibration.get("runtime_contract_status"),
        "redesign_verdict": redesign.get("verdict"),
        "redesign_entry_quality": redesign_best.get("current_entry_quality_after"),
        "redesign_raw_allowed_layers_after": redesign_best.get("raw_allowed_layers_after"),
        "redesign_allowed_layers_after": redesign_best.get("allowed_layers_after"),
        "redesign_positive_discriminative_gap": redesign_machine.get("positive_discriminative_gap"),
        "redesign_execution_blocked_after_floor_cross": redesign_machine.get("execution_blocked_after_floor_cross"),
        "runtime_execution_blocked": redesign.get("runtime_execution_blocked"),
        "runtime_execution_blocker": redesign.get("runtime_execution_blocker"),
        "runtime_allowed_layers": deployment_grade.get("runtime_allowed_layers"),
        "runtime_allowed_layers_raw": deployment_grade.get("runtime_allowed_layers_raw"),
        "runtime_allowed_layers_raw_reason": deployment_grade.get("runtime_allowed_layers_raw_reason"),
        "runtime_allowed_layers_reason": deployment_grade.get("runtime_allowed_layers_reason"),
        "runtime_deployment_blocker": deployment_grade.get("runtime_deployment_blocker"),
        "runtime_closure_state": deployment_grade.get("runtime_closure_state"),
        "support_route_verdict": deployment_grade.get("support_route_verdict"),
        "support_route_deployable": deployment_grade.get("support_route_deployable"),
        "current_live_structure_bucket_rows": deployment_grade.get("current_live_structure_bucket_rows"),
        "minimum_support_rows": deployment_grade.get("minimum_support_rows"),
        "current_live_structure_bucket_gap_to_minimum": deployment_grade.get("current_live_structure_bucket_gap_to_minimum"),
        "runtime_remaining_gap_to_floor": deployment_grade.get("runtime_remaining_gap_to_floor"),
        "remaining_gap_to_floor": deployment_grade.get("runtime_remaining_gap_to_floor"),
        "next_patch_target": next_patch_target,
        "verify_next": payload.get("verify_next") or deployment_grade.get("verify_next") or redesign.get("verify_next"),
        "q35_discriminative_redesign_applied": deployment_grade.get("q35_discriminative_redesign_applied"),
    }


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
    # Despite the historical name, hb_q15_support_audit.py is now the
    # canonical support-progress audit for the *current live bucket* as well as
    # the q15 component lane.  Refresh it for q00/q35 too; otherwise a heartbeat
    # can write live_predict_probe.json with a stale embedded audit while the
    # standalone q15_support_audit.json is refreshed later in the run.
    if not current_live_structure_bucket:
        return None
    current_payload = _load_q15_support_audit(current_live_structure_bucket)
    if (not force) and _q15_audit_matches_probe(
        current_payload,
        current_live_structure_bucket=current_live_structure_bucket,
        feature_timestamp=feature_timestamp,
    ):
        return current_payload

    script_path = PROJECT_ROOT / "scripts" / "hb_q15_support_audit.py"
    try:
        audit_path = Q15_SUPPORT_AUDIT_PATH.resolve()
        project_root = PROJECT_ROOT.resolve()
        audit_path_is_project_artifact = audit_path == project_root / "data" / "q15_support_audit.json" or project_root in audit_path.parents
    except OSError:
        audit_path_is_project_artifact = False
    if not audit_path_is_project_artifact:
        # Unit tests often monkeypatch Q15_SUPPORT_AUDIT_PATH to a tmp file while
        # leaving PROJECT_ROOT pointed at the real repository. Do not import and
        # execute the real audit script into a test tmp artifact in that mixed
        # context; callers still receive the current payload. Production paths
        # (and explicit tests that monkeypatch PROJECT_ROOT together with the
        # audit path) continue through the refresh branch.
        return current_payload
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


SUPPORT_IDENTITY_FIELDS = (
    "target_col",
    "horizon_minutes",
    "current_live_structure_bucket",
    "regime_label",
    "regime_gate",
    "entry_quality_label",
    "calibration_window",
)


def _extract_support_identity(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {}
    support_route = payload.get("support_route") if isinstance(payload.get("support_route"), dict) else {}
    support_progress = support_route.get("support_progress") if isinstance(support_route.get("support_progress"), dict) else {}
    for candidate in (
        payload.get("support_identity"),
        support_route.get("support_identity"),
        support_progress.get("support_identity"),
    ):
        if isinstance(candidate, dict) and candidate:
            return candidate
    return {}


def _current_support_identity(
    *,
    result: dict,
    target_col,
    current_live_structure_bucket,
    audit_identity: dict | None = None,
) -> dict:
    identity = {
        "target_col": target_col or result.get("target_col"),
        "horizon_minutes": result.get("decision_quality_horizon_minutes") or result.get("horizon_minutes"),
        "current_live_structure_bucket": current_live_structure_bucket or result.get("structure_bucket"),
        "regime_label": result.get("regime_label"),
        "regime_gate": result.get("regime_gate"),
        "entry_quality_label": result.get("entry_quality_label") or result.get("decision_quality_label"),
        "calibration_window": result.get("decision_quality_calibration_window"),
    }
    if isinstance(audit_identity, dict) and audit_identity.get("bucket_semantic_signature"):
        identity["bucket_semantic_signature"] = audit_identity.get("bucket_semantic_signature")
    return {key: value for key, value in identity.items() if value is not None}


def _q15_support_identity_mismatch(
    *,
    q15_support_audit: dict | None,
    result: dict,
    target_col,
    current_live_structure_bucket,
) -> dict | None:
    """Return mismatch details when a cached q15 audit describes another live lane.

    The q15 audit may contribute support-progress truth for the current live
    lane, including non-q15 buckets, but only when its explicit support identity
    still matches the freshly computed predictor identity. A stale C-lane audit
    must not overwrite a fresh D-lane runtime result.
    """
    audit_identity = _extract_support_identity(q15_support_audit)
    if not audit_identity:
        return None
    current_identity = _current_support_identity(
        result=result,
        target_col=target_col,
        current_live_structure_bucket=current_live_structure_bucket,
        audit_identity=audit_identity,
    )
    mismatches = []
    for field in SUPPORT_IDENTITY_FIELDS:
        audit_value = audit_identity.get(field)
        current_value = current_identity.get(field)
        if audit_value is None or current_value is None:
            continue
        if str(audit_value) != str(current_value):
            mismatches.append(
                {
                    "field": field,
                    "audit_value": audit_value,
                    "current_value": current_value,
                }
            )
    if not mismatches:
        return None
    return {
        "status": "support_identity_mismatch_current_live",
        "reason": "q15_support_audit support_identity no longer matches the freshly computed current-live predictor identity; ignoring audit support_route/support_progress overlays for this probe.",
        "audit_support_identity": audit_identity,
        "current_support_identity": current_identity,
        "mismatched_fields": mismatches,
    }


def _runtime_patch_name(result: dict) -> str | None:
    return shared_runtime_patch_name(result)



def _runtime_closure_state(result: dict) -> str:
    return shared_runtime_closure_state(result)



def _runtime_closure_summary(
    result: dict,
    *,
    release_window: int,
    release_floor,
    release_gap,
    current_wins,
    breaker_release: dict,
    scope_pathology_summary: dict | None = None,
) -> str | None:
    return shared_runtime_closure_summary(
        result,
        release_window=release_window,
        release_floor=release_floor,
        release_gap=release_gap,
        current_wins=current_wins,
        breaker_release=breaker_release,
        scope_pathology_summary=scope_pathology_summary,
    )



def _api_trade_guardrail_surface(runtime_result: dict, runtime_closure_state: str | None) -> dict:
    """Mirror /api/trade add-exposure fail-closed semantics in the probe artifact.

    The route-level guardrail is the production contract, but heartbeat artifacts
    are the machine-readable governance source.  Keep the same decision inputs
    here so Dashboard / Strategy Lab / docs can prove buy/add exposure is paused
    while wait/observe and reduce/sell risk-off actions remain available.
    """
    payload = runtime_result if isinstance(runtime_result, dict) else {}
    deployment_blocker = payload.get("deployment_blocker")
    signal = str(payload.get("signal") or "").upper()
    allowed_layers = payload.get("allowed_layers")
    allowed_layers_reason = payload.get("allowed_layers_reason")
    execution_guardrail_reason = payload.get("execution_guardrail_reason")

    try:
        numeric_allowed_layers = int(allowed_layers) if allowed_layers is not None else None
    except (TypeError, ValueError):
        numeric_allowed_layers = None

    guardrail_active = bool(deployment_blocker) or signal == "CIRCUIT_BREAKER"
    guardrail_active = guardrail_active or runtime_closure_state in NO_DEPLOY_RUNTIME_CLOSURE_STATES
    guardrail_active = guardrail_active or (
        numeric_allowed_layers is not None
        and numeric_allowed_layers <= 0
        and bool(allowed_layers_reason)
    )
    runtime_blocker = deployment_blocker or runtime_closure_state or execution_guardrail_reason or allowed_layers_reason
    if not guardrail_active:
        return {
            "api_trade_guardrail_active": False,
            "api_trade_buy_guardrail": "not_blocked",
            "api_trade_add_exposure_guardrail": "not_blocked",
            "api_trade_guardrail_code": None,
            "api_trade_guardrail_runtime_blocker": runtime_blocker,
            "api_trade_allowed_risk_off_sides": API_TRADE_RISK_OFF_SIDES,
            "api_trade_allowed_actions": ["buy", *API_TRADE_BLOCKED_ALLOWED_ACTIONS],
            "api_trade_guardrail_context": "即時部署阻塞未啟用；/api/trade 可送出買入，也可等待 / 觀望或減倉 / 賣出降低風險。",
        }

    return {
        "api_trade_guardrail_active": True,
        "api_trade_buy_guardrail": "current_live_deployment_blocker_409",
        "api_trade_add_exposure_guardrail": "current_live_deployment_blocker_409",
        "api_trade_guardrail_code": "current_live_deployment_blocker",
        "api_trade_guardrail_runtime_blocker": runtime_blocker,
        "api_trade_allowed_risk_off_sides": API_TRADE_RISK_OFF_SIDES,
        "api_trade_allowed_actions": list(API_TRADE_BLOCKED_ALLOWED_ACTIONS),
        "api_trade_guardrail_context": "買入 / 加倉會在 ExecutionService.submit_order 前先檢查即時部署阻塞點；阻塞時 /api/trade 回 409 current_live_deployment_blocker，只保留等待 / 觀望與減倉 / 賣出風險降低路徑。",
    }



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
    support_route = {}
    if result.get("support_route_verdict"):
        support_route = {
            "verdict": result.get("support_route_verdict"),
            "deployable": result.get("support_route_deployable"),
        }
    support_progress = result.get("support_progress") if isinstance(result.get("support_progress"), dict) else {}
    q15_support_identity_mismatch = _q15_support_identity_mismatch(
        q15_support_audit=q15_support_audit,
        result=result,
        target_col=target_col,
        current_live_structure_bucket=current_live_structure_bucket,
    )
    q15_support_overlay = {} if q15_support_identity_mismatch else (q15_support_audit or {})
    floor_cross = q15_support_overlay.get("floor_cross_legality") if isinstance(q15_support_overlay.get("floor_cross_legality"), dict) else {}
    component_experiment = q15_support_overlay.get("component_experiment") if isinstance(q15_support_overlay.get("component_experiment"), dict) else {}
    component_machine_answer = component_experiment.get("machine_read_answer") if isinstance(component_experiment.get("machine_read_answer"), dict) else {}
    positive_discrimination_evidence = component_experiment.get("positive_discrimination_evidence") if isinstance(component_experiment.get("positive_discrimination_evidence"), dict) else {}
    component_positive_status = (
        component_machine_answer.get("preserves_positive_discrimination_status")
        or positive_discrimination_evidence.get("status")
    )
    component_deployment_ready = bool(
        component_experiment.get("verdict") == "exact_supported_component_experiment_ready"
        and component_machine_answer.get("support_ready") is True
        and component_machine_answer.get("entry_quality_ge_0_55") is True
        and component_machine_answer.get("allowed_layers_gt_0") is True
        and component_machine_answer.get("preserves_positive_discrimination") is True
    )
    active_repair_plan = q15_support_overlay.get("active_repair_plan") if isinstance(q15_support_overlay.get("active_repair_plan"), dict) else {}
    deployment_blocker_details = dict(result.get("deployment_blocker_details")) if isinstance(result.get("deployment_blocker_details"), dict) else {}
    if q15_support_identity_mismatch:
        deployment_blocker_details["q15_support_audit_identity_mismatch"] = q15_support_identity_mismatch
    if active_repair_plan:
        deployment_blocker_details["active_repair_plan"] = active_repair_plan
    if component_experiment:
        deployment_blocker_details["component_experiment"] = component_experiment
        deployment_blocker_details["component_experiment_verdict"] = component_experiment.get("verdict")
        deployment_blocker_details["component_experiment_deployment_ready"] = component_deployment_ready
        if component_positive_status is not None:
            deployment_blocker_details["component_experiment_positive_discrimination_status"] = component_positive_status
        if component_machine_answer.get("preserves_positive_discrimination") is not None:
            deployment_blocker_details["component_experiment_preserves_positive_discrimination"] = component_machine_answer.get("preserves_positive_discrimination")
        if component_experiment.get("verify_next"):
            deployment_blocker_details["component_experiment_verify_next"] = component_experiment.get("verify_next")
    if isinstance(q15_support_overlay.get("support_route"), dict):
        support_route = q15_support_overlay.get("support_route")
        if isinstance(support_route.get("support_progress"), dict):
            support_progress = support_route.get("support_progress")
    support_identity = None
    artifact_context_freshness = None
    if isinstance(q15_support_overlay, dict) and q15_support_overlay:
        artifact_context_freshness = q15_support_overlay.get("artifact_context_freshness")
        support_identity = (
            q15_support_overlay.get("support_identity")
            or (support_route.get("support_identity") if isinstance(support_route, dict) else None)
            or (support_progress.get("support_identity") if isinstance(support_progress, dict) else None)
        )
    elif q15_support_identity_mismatch:
        support_identity = q15_support_identity_mismatch.get("current_support_identity")
        if support_progress and not support_progress.get("support_identity"):
            support_progress = dict(support_progress)
            support_progress["support_identity"] = support_identity
    if not support_route:
        generic_support_mode = (
            str(result.get("decision_quality_structure_bucket_support_mode") or "")
            or str(deployment_blocker_details.get("support_mode") or "")
        )
        generic_support_verdict = deployment_blocker_details.get("support_route_verdict")
        if not generic_support_verdict:
            blocker = str(result.get("deployment_blocker") or "")
            if blocker == "under_minimum_exact_live_structure_bucket" or generic_support_mode == "exact_bucket_present_but_below_minimum":
                generic_support_verdict = "exact_bucket_present_but_below_minimum"
            elif blocker == "unsupported_exact_live_structure_bucket" or generic_support_mode == "exact_bucket_unsupported_block":
                generic_support_verdict = "exact_bucket_unsupported_block"
            elif generic_support_mode.startswith("exact_bucket_supported"):
                generic_support_verdict = "exact_bucket_supported"
        if generic_support_verdict:
            support_route = {
                "verdict": generic_support_verdict,
                "deployable": deployment_blocker_details.get("support_route_deployable"),
            }
    if not support_progress:
        fallback_progress = deployment_blocker_details.get("support_progress") if isinstance(deployment_blocker_details.get("support_progress"), dict) else {}
        if fallback_progress:
            support_progress = fallback_progress
    support_route, support_progress = _normalize_generic_exact_support_route(
        support_route=support_route,
        support_progress=support_progress,
        current_live_structure_bucket=current_live_structure_bucket,
        current_live_structure_bucket_rows=current_live_structure_bucket_rows,
        minimum_support_rows=(
            support_progress.get("minimum_support_rows")
            if isinstance(support_progress, dict) and support_progress.get("minimum_support_rows") is not None
            else support_route.get("minimum_support_rows")
            if isinstance(support_route, dict) and support_route.get("minimum_support_rows") is not None
            else deployment_blocker_details.get("minimum_support_rows")
        ),
    )
    if support_progress:
        deployment_blocker_details["support_progress"] = support_progress
        progress_rows = support_progress.get("current_rows")
        progress_minimum_rows = support_progress.get("minimum_support_rows")
        progress_gap = support_progress.get("gap_to_minimum")
        if progress_minimum_rows is not None:
            deployment_blocker_details["minimum_support_rows"] = progress_minimum_rows
        if progress_gap is not None:
            deployment_blocker_details["current_live_structure_bucket_gap_to_minimum"] = progress_gap
        if progress_rows is not None:
            # A refreshed q15 support audit may carry the canonical current-bucket
            # support truth even when the predictor result still says
            # ``exact_bucket_supported`` from an older scope.  Do not leave
            # operator/API surfaces with impossible rows/gap combinations like
            # rows=50, minimum=50, gap=22: the progress artifact is the
            # under-minimum source of truth for this probe output.
            deployment_blocker_details["current_live_structure_bucket_rows"] = progress_rows
            deployment_blocker_details["exact_live_structure_bucket_rows"] = progress_rows
            current_live_structure_bucket_rows = progress_rows
    if support_identity:
        deployment_blocker_details["support_identity"] = support_identity
    if artifact_context_freshness:
        deployment_blocker_details["artifact_context_freshness"] = artifact_context_freshness
    if support_route:
        deployment_blocker_details["support_route_verdict"] = support_route.get("verdict")
        deployment_blocker_details["support_route_deployable"] = support_route.get("deployable")
    runtime_result = dict(result)
    if support_route.get("verdict") is not None:
        runtime_result["support_route_verdict"] = support_route.get("verdict")
    if support_route.get("deployable") is not None:
        runtime_result["support_route_deployable"] = support_route.get("deployable")
    if support_progress:
        runtime_result["support_progress"] = support_progress
    if component_experiment:
        runtime_result["component_experiment"] = component_experiment
        runtime_result["component_experiment_verdict"] = component_experiment.get("verdict")
        runtime_result["component_experiment_deployment_ready"] = component_deployment_ready
        runtime_result["component_experiment_positive_discrimination_status"] = component_positive_status
        runtime_result["component_experiment_preserves_positive_discrimination"] = component_machine_answer.get("preserves_positive_discrimination")
        runtime_result["component_experiment_verify_next"] = component_experiment.get("verify_next")
    runtime_result["current_live_structure_bucket"] = current_live_structure_bucket
    runtime_result["current_live_structure_bucket_rows"] = current_live_structure_bucket_rows
    scope_pathology_summary = build_live_pathology_scope_surface(
        runtime_result,
        result.get("decision_quality_scope_diagnostics") if isinstance(result.get("decision_quality_scope_diagnostics"), dict) else {},
        artifact_path=BULL_4H_POCKET_ABLATION_PATH,
    )
    support_governance_route = _infer_support_governance_route(
        support_route=support_route,
        deployment_blocker_details=deployment_blocker_details,
        current_live_structure_bucket_rows=(
            support_progress.get("current_rows")
            if isinstance(support_progress, dict) and support_progress.get("current_rows") is not None
            else current_live_structure_bucket_rows
        ),
        minimum_support_rows=(
            support_progress.get("minimum_support_rows")
            if isinstance(support_progress, dict) and support_progress.get("minimum_support_rows") is not None
            else deployment_blocker_details.get("minimum_support_rows")
        ),
        scope_pathology_summary=scope_pathology_summary if isinstance(scope_pathology_summary, dict) else None,
    )
    if support_governance_route is not None:
        if support_route:
            support_route["support_governance_route"] = support_governance_route
        deployment_blocker_details["support_governance_route"] = support_governance_route
        runtime_result["support_governance_route"] = support_governance_route

    try:
        progress_rows_value = int(support_progress.get("current_rows")) if support_progress.get("current_rows") is not None else None
    except (TypeError, ValueError):
        progress_rows_value = None
    try:
        progress_minimum_value = int(support_progress.get("minimum_support_rows")) if support_progress.get("minimum_support_rows") is not None else None
    except (TypeError, ValueError):
        progress_minimum_value = None
    if (
        progress_rows_value is not None
        and progress_minimum_value is not None
        and progress_rows_value < progress_minimum_value
        and result.get("deployment_blocker") in {
            "decision_quality_below_trade_floor",
            "under_minimum_exact_live_structure_bucket",
            "unsupported_exact_live_structure_bucket",
        }
    ):
        progress_gap_value = support_progress.get("gap_to_minimum")
        if progress_gap_value is None:
            progress_gap_value = progress_minimum_value - progress_rows_value
        decision_quality_label = result.get("decision_quality_label") or result.get("entry_quality_label")
        decision_quality_score = result.get("decision_quality_score")
        decision_quality_copy = ""
        if decision_quality_label:
            decision_quality_copy = f"；決策品質仍為 {decision_quality_label}"
            if decision_quality_score is not None:
                try:
                    decision_quality_copy += f" / 品質分數 {float(decision_quality_score):.4f}"
                except (TypeError, ValueError):
                    pass
        support_route_verdict = support_route.get("verdict")
        support_route_label = _support_route_operator_label(support_route_verdict)
        support_route_copy = support_route_label
        current_live_structure_bucket_copy = shared_humanize_runtime_text(current_live_structure_bucket)
        support_truth_reason = (
            f"當前即時結構分桶 `{current_live_structure_bucket_copy}` 的精準支持樣本仍停在 "
            f"{progress_rows_value}/{progress_minimum_value}（缺 {progress_gap_value}），"
            f"支持路徑={support_route_copy}，不可把舊範圍的支持閉環誤讀成部署閉環"
            f"{decision_quality_copy}；目前維持不可部署治理。"
        )
        deployment_blocker_details["reason"] = support_truth_reason
        if progress_rows_value <= 0 and support_route_verdict == "exact_bucket_unsupported_block":
            deployment_blocker_details["support_mode"] = "exact_bucket_unsupported_block"
        else:
            deployment_blocker_details["support_mode"] = "exact_bucket_present_but_below_minimum"
        runtime_result["deployment_blocker_reason"] = support_truth_reason
        runtime_result["deployment_blocker_details"] = deployment_blocker_details
    q35_scaling_audit = _load_q35_scaling_audit_summary(current_live_structure_bucket)
    q15_bucket_root_cause = _load_q15_bucket_root_cause_summary(
        str(current_live_structure_bucket) if current_live_structure_bucket is not None else None
    )
    current_bucket_root_cause = q15_bucket_root_cause or (
        result.get("current_bucket_root_cause") if isinstance(result.get("current_bucket_root_cause"), dict) else None
    )
    if q15_bucket_root_cause:
        deployment_blocker_details["q15_bucket_root_cause"] = q15_bucket_root_cause
        deployment_blocker_details["current_bucket_root_cause"] = current_bucket_root_cause
        runtime_result["q15_bucket_root_cause"] = q15_bucket_root_cause
        runtime_result["current_bucket_root_cause"] = current_bucket_root_cause
    recommended_patch_summary = (
        scope_pathology_summary.get("recommended_patch")
        if isinstance(scope_pathology_summary, dict)
        and isinstance(scope_pathology_summary.get("recommended_patch"), dict)
        else None
    )
    recommended_patch_profile = result.get("recommended_patch_profile")
    if recommended_patch_profile is None and recommended_patch_summary is not None:
        recommended_patch_profile = recommended_patch_summary.get("recommended_profile")
    recommended_patch_status = result.get("recommended_patch_status")
    if recommended_patch_status is None and recommended_patch_summary is not None:
        recommended_patch_status = recommended_patch_summary.get("status")
    recommended_patch_reference_scope = result.get("recommended_patch_reference_scope")
    if recommended_patch_reference_scope is None and recommended_patch_summary is not None:
        recommended_patch_reference_scope = recommended_patch_summary.get("reference_patch_scope")
    recommended_patch_reference_source = result.get("recommended_patch_reference_source")
    if recommended_patch_reference_source is None and recommended_patch_summary is not None:
        recommended_patch_reference_source = recommended_patch_summary.get("reference_source")
    recommended_patch_reason = result.get("recommended_patch_reason")
    if recommended_patch_reason is None and recommended_patch_summary is not None:
        recommended_patch_reason = recommended_patch_summary.get("reason")
    recommended_patch_support_route = result.get("recommended_patch_support_route")
    if recommended_patch_support_route is None and recommended_patch_summary is not None:
        recommended_patch_support_route = recommended_patch_summary.get("support_route_verdict")
    recommended_patch_gap_to_minimum = result.get("recommended_patch_gap_to_minimum")
    if recommended_patch_gap_to_minimum is None and recommended_patch_summary is not None:
        recommended_patch_gap_to_minimum = recommended_patch_summary.get("gap_to_minimum")
    recommended_patch_current_rows = result.get("recommended_patch_current_live_structure_bucket_rows")
    if recommended_patch_current_rows is None and recommended_patch_summary is not None:
        recommended_patch_current_rows = recommended_patch_summary.get("current_live_structure_bucket_rows")
    recommended_patch_minimum_rows = result.get("recommended_patch_minimum_support_rows")
    if recommended_patch_minimum_rows is None and recommended_patch_summary is not None:
        recommended_patch_minimum_rows = recommended_patch_summary.get("minimum_support_rows")
    breaker_release = deployment_blocker_details.get("release_condition") if isinstance(deployment_blocker_details.get("release_condition"), dict) else {}
    breaker_recent_window = deployment_blocker_details.get("recent_window") if isinstance(deployment_blocker_details.get("recent_window"), dict) else {}
    circuit_breaker_release_surface = shared_circuit_breaker_release_surface(runtime_result)
    if circuit_breaker_release_surface:
        runtime_result.update(circuit_breaker_release_surface)
        breaker_release = circuit_breaker_release_surface.get("release_condition") or breaker_release
    release_window = breaker_release.get("recent_window") or breaker_recent_window.get("window_size") or 50
    release_floor = breaker_release.get("recent_win_rate_must_be_at_least")
    release_wins = breaker_release.get("required_recent_window_wins")
    release_gap = breaker_release.get("additional_recent_window_wins_needed")
    current_wins = breaker_release.get("current_recent_window_wins")
    runtime_closure_state = _runtime_closure_state(runtime_result)
    runtime_closure_summary = _runtime_closure_summary(
        runtime_result,
        release_window=release_window,
        release_floor=release_floor,
        release_gap=release_gap,
        current_wins=current_wins,
        breaker_release=breaker_release,
        scope_pathology_summary=scope_pathology_summary,
    )
    api_trade_guardrail = _api_trade_guardrail_surface(runtime_result, runtime_closure_state)
    return {
        # Do not persist local connection strings into runtime artifacts.
        "db_url": "[REDACTED]",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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
        "deployment_blocker": runtime_result.get("deployment_blocker"),
        "deployment_blocker_reason": runtime_result.get("deployment_blocker_reason"),
        "deployment_blocker_source": runtime_result.get("deployment_blocker_source"),
        "deployment_blocker_details": deployment_blocker_details,
        **circuit_breaker_release_surface,
        "support_route_verdict": support_route.get("verdict"),
        "support_route_deployable": support_route.get("deployable"),
        "support_governance_route": support_governance_route,
        "support_identity": support_identity,
        "artifact_context_freshness": artifact_context_freshness,
        "support_progress": support_progress or None,
        "minimum_support_rows": (
            support_progress.get("minimum_support_rows")
            if support_progress
            else deployment_blocker_details.get("minimum_support_rows")
        ),
        "current_live_structure_bucket_gap_to_minimum": (
            support_progress.get("gap_to_minimum")
            if support_progress
            else deployment_blocker_details.get("current_live_structure_bucket_gap_to_minimum")
        ),
        "recommended_patch": recommended_patch_summary,
        "recommended_patch_profile": recommended_patch_profile,
        "recommended_patch_status": recommended_patch_status,
        "recommended_patch_reference_scope": recommended_patch_reference_scope,
        "recommended_patch_reference_source": recommended_patch_reference_source,
        "recommended_patch_reason": recommended_patch_reason,
        "recommended_patch_support_route": recommended_patch_support_route,
        "recommended_patch_gap_to_minimum": recommended_patch_gap_to_minimum,
        "recommended_patch_current_live_structure_bucket_rows": recommended_patch_current_rows,
        "recommended_patch_minimum_support_rows": recommended_patch_minimum_rows,
        "floor_cross_verdict": floor_cross.get("verdict"),
        "legal_to_relax_runtime_gate": floor_cross.get("legal_to_relax_runtime_gate"),
        "remaining_gap_to_floor": floor_cross.get("remaining_gap_to_floor"),
        "best_single_component": floor_cross.get("best_single_component"),
        "best_single_component_required_score_delta": floor_cross.get("best_single_component_required_score_delta"),
        "component_experiment_verdict": component_experiment.get("verdict"),
        "component_experiment_deployment_ready": component_deployment_ready,
        "component_experiment_positive_discrimination_status": component_positive_status,
        "component_experiment_preserves_positive_discrimination": component_machine_answer.get("preserves_positive_discrimination"),
        "component_experiment_verify_next": component_experiment.get("verify_next"),
        "component_experiment_reason": component_experiment.get("reason"),
        "active_repair_plan": active_repair_plan or None,
        "runtime_closure_state": runtime_closure_state,
        "runtime_closure_summary": runtime_closure_summary,
        **api_trade_guardrail,
        "q15_support_audit": q15_support_audit,
        "q15_support_audit_identity_mismatch": q15_support_identity_mismatch,
        "q15_bucket_root_cause": q15_bucket_root_cause,
        "current_bucket_root_cause": current_bucket_root_cause,
        "q35_scaling_audit": q35_scaling_audit,
        "q35_overall_verdict": q35_scaling_audit.get("overall_verdict") if isinstance(q35_scaling_audit, dict) else None,
        "q35_redesign_verdict": q35_scaling_audit.get("redesign_verdict") if isinstance(q35_scaling_audit, dict) else None,
        "q35_redesign_entry_quality": q35_scaling_audit.get("redesign_entry_quality") if isinstance(q35_scaling_audit, dict) else None,
        "q35_redesign_raw_allowed_layers_after": q35_scaling_audit.get("redesign_raw_allowed_layers_after") if isinstance(q35_scaling_audit, dict) else None,
        "q35_redesign_allowed_layers_after": q35_scaling_audit.get("redesign_allowed_layers_after") if isinstance(q35_scaling_audit, dict) else None,
        "q35_redesign_positive_discriminative_gap": q35_scaling_audit.get("redesign_positive_discriminative_gap") if isinstance(q35_scaling_audit, dict) else None,
        "q35_redesign_execution_blocked_after_floor_cross": q35_scaling_audit.get("redesign_execution_blocked_after_floor_cross") if isinstance(q35_scaling_audit, dict) else None,
        "q35_runtime_execution_blocked": q35_scaling_audit.get("runtime_execution_blocked") if isinstance(q35_scaling_audit, dict) else None,
        "q35_runtime_execution_blocker": q35_scaling_audit.get("runtime_execution_blocker") if isinstance(q35_scaling_audit, dict) else None,
        "q35_runtime_allowed_layers": q35_scaling_audit.get("runtime_allowed_layers") if isinstance(q35_scaling_audit, dict) else None,
        "q35_runtime_allowed_layers_raw": q35_scaling_audit.get("runtime_allowed_layers_raw") if isinstance(q35_scaling_audit, dict) else None,
        "q35_runtime_allowed_layers_reason": q35_scaling_audit.get("runtime_allowed_layers_reason") if isinstance(q35_scaling_audit, dict) else None,
        "q35_runtime_deployment_blocker": q35_scaling_audit.get("runtime_deployment_blocker") if isinstance(q35_scaling_audit, dict) else None,
        "q35_support_route_verdict": q35_scaling_audit.get("support_route_verdict") if isinstance(q35_scaling_audit, dict) else None,
        "q35_current_live_structure_bucket_rows": q35_scaling_audit.get("current_live_structure_bucket_rows") if isinstance(q35_scaling_audit, dict) else None,
        "q35_minimum_support_rows": q35_scaling_audit.get("minimum_support_rows") if isinstance(q35_scaling_audit, dict) else None,
        "q35_current_live_structure_bucket_gap_to_minimum": q35_scaling_audit.get("current_live_structure_bucket_gap_to_minimum") if isinstance(q35_scaling_audit, dict) else None,
        "q35_runtime_remaining_gap_to_floor": q35_scaling_audit.get("runtime_remaining_gap_to_floor") if isinstance(q35_scaling_audit, dict) else None,
        "q35_recommended_mode": q35_scaling_audit.get("recommended_mode") if isinstance(q35_scaling_audit, dict) else None,
        "q35_recommended_action": q35_scaling_audit.get("recommended_action") if isinstance(q35_scaling_audit, dict) else None,
        "q35_next_patch_target": q35_scaling_audit.get("next_patch_target") if isinstance(q35_scaling_audit, dict) else None,
        "decision_quality_horizon_minutes": result.get("decision_quality_horizon_minutes"),
        "decision_quality_calibration_scope": result.get("decision_quality_calibration_scope"),
        "decision_quality_calibration_window": result.get("decision_quality_calibration_window"),
        "decision_quality_sample_size": result.get("decision_quality_sample_size"),
        "decision_quality_scope_diagnostics": result.get("decision_quality_scope_diagnostics"),
        "decision_quality_scope_pathology_summary": scope_pathology_summary,
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

        result_patch_applied = bool(result.get("q15_exact_supported_component_patch_applied"))
        refreshed_q15_support_audit = _refresh_q15_support_audit(
            current_live_structure_bucket=current_live_structure_bucket,
            feature_timestamp=probe.get("feature_timestamp"),
        )
        if refreshed_q15_support_audit:
            refreshed_patch_supported = _q15_patch_supported_by_audit(refreshed_q15_support_audit)
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
                    synced_patch_supported = _q15_patch_supported_by_audit(synced_q15_support_audit)
                    current_result_patch_applied = bool(result.get("q15_exact_supported_component_patch_applied"))
                    if current_result_patch_applied != synced_patch_supported:
                        result = predict(session, predictor, regime_models)
                        if result is None:
                            raise SystemExit("predictor probe failed: force-refreshed q15 audit changed patch readiness but replay prediction returned no result")
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
