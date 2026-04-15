from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_Q35_AUDIT_PATH = PROJECT_ROOT / "data" / "q35_scaling_audit.json"

_AUDIT_CACHE: dict[str, Any] = {
    "path": None,
    "mtime": None,
    "data": None,
}


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def legacy_bias50_score(bias50_value: float) -> float:
    return _clamp01((-float(bias50_value) + 2.4) / 5.0)


def load_q35_scaling_audit(audit_path: Optional[Path] = None) -> Optional[dict[str, Any]]:
    path = Path(audit_path or DEFAULT_Q35_AUDIT_PATH)
    if not path.exists():
        return None

    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return None

    if _AUDIT_CACHE["path"] == str(path) and _AUDIT_CACHE["mtime"] == mtime:
        data = _AUDIT_CACHE.get("data")
        return data if isinstance(data, dict) else None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = None

    _AUDIT_CACHE.update({
        "path": str(path),
        "mtime": mtime,
        "data": data,
    })
    return data if isinstance(data, dict) else None


def compute_piecewise_bias50_score(
    bias50_value: float,
    *,
    regime_label: Optional[str] = None,
    regime_gate: Optional[str] = None,
    structure_bucket: Optional[str] = None,
    audit: Optional[dict[str, Any]] = None,
    audit_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Apply Heartbeat #1005/#1006 q35/bias50 calibration when applicable.

    The calibration stays intentionally narrow and only targets the current bull q35
    caution lane. Two conservative sub-zones are supported:

    1. exact-lane elevated-but-still-inside-p90 rows (formula review zone)
    2. reference-extension rows above exact-lane p90 but still inside the broader bull p90

    Both modes keep the lane below trade-floor by design; they only prevent the legacy
    linear mapping from forcing every high-but-still-supported bias50 row to zero.
    """

    legacy_score = legacy_bias50_score(bias50_value)
    report = audit if audit is not None else load_q35_scaling_audit(audit_path=audit_path)
    current_value = float(bias50_value)

    fallback = {
        "applied": False,
        "score": legacy_score,
        "legacy_score": legacy_score,
        "score_delta_vs_legacy": 0.0,
        "mode": "legacy_linear",
        "segment": None,
        "reference_cohort": None,
        "reason": "no segmented calibration artifact or current lane is outside the targeted bull q35 extension zone.",
        "exact_p90": None,
        "reference_p90": None,
    }

    if not isinstance(report, dict):
        return fallback
    if str(regime_label or "") != "bull":
        return fallback
    overall_verdict = str(report.get("overall_verdict") or "")
    if overall_verdict not in {
        "broader_bull_cohort_recalibration_candidate",
        "bias50_formula_may_be_too_harsh",
    }:
        return fallback

    segmented = report.get("segmented_calibration") or {}
    status = str(segmented.get("status") or "")
    recommended_mode = str(segmented.get("recommended_mode") or "")
    allowed_modes = {
        ("segmented_calibration_required", "piecewise_quantile_calibration"),
        ("formula_review_required", "exact_lane_formula_review"),
    }
    if (status, recommended_mode) not in allowed_modes:
        return fallback

    current_live = report.get("current_live") or {}
    target_gate = current_live.get("regime_gate")
    target_bucket = current_live.get("structure_bucket")
    if target_gate and regime_gate and str(target_gate) != str(regime_gate):
        return fallback
    if target_bucket and structure_bucket and str(target_bucket) != str(structure_bucket):
        return fallback

    exact_lane = segmented.get("exact_lane") or {}
    reference = segmented.get("reference_cohort") or {}
    reference_dist = reference.get("bias50_distribution") or {}
    exact_dist = exact_lane.get("bias50_distribution") or {}
    exact_p75 = _safe_float(exact_dist.get("p75"))
    exact_p90 = _safe_float(exact_dist.get("p90"))
    reference_p90 = _safe_float(reference_dist.get("p90"))
    reference_cohort = reference.get("cohort")

    if exact_p90 is None:
        return fallback

    if (
        status == "formula_review_required"
        and recommended_mode == "exact_lane_formula_review"
        and exact_p75 is not None
        and exact_p75 < exact_p90
        and exact_p75 <= current_value <= exact_p90
    ):
        elevated_share = (current_value - exact_p75) / (exact_p90 - exact_p75)
        elevated_share = _clamp01(elevated_share)
        calibrated_score = 0.18 + (0.10 - 0.18) * elevated_share
        calibrated_score = round(_clamp01(calibrated_score), 4)
        return {
            "applied": True,
            "score": calibrated_score,
            "legacy_score": round(legacy_score, 4),
            "score_delta_vs_legacy": round(calibrated_score - legacy_score, 4),
            "mode": "exact_lane_formula_review",
            "segment": "exact_lane_elevated_within_p90",
            "reference_cohort": reference_cohort,
            "reason": (
                "bias50 已回到 exact-lane p90 內、但仍位於高側 elevated 區；"
                "用保守的非零 score 取代 legacy 0 分，避免把仍受 exact lane 支持的 row 誤判成完全不可交易。"
            ),
            "exact_p75": round(exact_p75, 4),
            "exact_p90": round(exact_p90, 4),
            "reference_p90": round(reference_p90, 4) if reference_p90 is not None else None,
            "elevated_share": round(elevated_share, 4),
        }

    if not reference_cohort or reference_p90 is None or reference_p90 <= exact_p90:
        return fallback
    if current_value <= exact_p90:
        return fallback
    if current_value >= reference_p90:
        return {
            **fallback,
            "score": 0.0,
            "score_delta_vs_legacy": round(0.0 - legacy_score, 4),
            "mode": "piecewise_quantile_calibration",
            "segment": "reference_overheat",
            "reference_cohort": reference_cohort,
            "reason": "current bias50 is above the broader reference cohort p90; keep the lane in hold-only/overheat handling.",
            "exact_p90": round(exact_p90, 4),
            "reference_p90": round(reference_p90, 4),
        }

    # Map exact-lane p90 to a small-but-nonzero caution score, then decay toward a near-zero
    # value at the broader bull cohort p90. This preserves hold-only semantics for the
    # current row while differentiating 'exact-lane overheat' from 'broader bull normal high'.
    extension_share = (current_value - exact_p90) / (reference_p90 - exact_p90)
    extension_share = _clamp01(extension_share)
    calibrated_score = 0.35 + (0.05 - 0.35) * extension_share
    calibrated_score = round(_clamp01(calibrated_score), 4)

    return {
        "applied": True,
        "score": calibrated_score,
        "legacy_score": round(legacy_score, 4),
        "score_delta_vs_legacy": round(calibrated_score - legacy_score, 4),
        "mode": "piecewise_quantile_calibration",
        "segment": "bull_reference_extension",
        "reference_cohort": reference_cohort,
        "reason": (
            "bias50 is above the exact-lane p90 but still inside the broader bull reference p90; "
            "use a decaying extension score instead of forcing a zero score."
        ),
        "exact_p90": round(exact_p90, 4),
        "reference_p90": round(reference_p90, 4),
        "extension_share": round(extension_share, 4),
    }
