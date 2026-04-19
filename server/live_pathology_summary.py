from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BULL_4H_POCKET_ABLATION_PATH = PROJECT_ROOT / "data" / "bull_4h_pocket_ablation.json"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _fmt_pct(value: Any, digits: int = 1) -> str:
    if not _is_number(value):
        return "—"
    return f"{float(value):.{digits}%}"


def _fmt_float(value: Any, digits: int = 3) -> str:
    if not _is_number(value):
        return "—"
    return f"{float(value):.{digits}f}"


def build_live_pathology_scope_summary(scope_diagnostics: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(scope_diagnostics, dict):
        return None

    exact_scope = scope_diagnostics.get("regime_label+regime_gate+entry_quality_label")
    if not isinstance(exact_scope, dict):
        exact_scope = {}

    exact_live_lane = {
        "scope": "regime_label+regime_gate+entry_quality_label",
        "rows": exact_scope.get("rows"),
        "win_rate": exact_scope.get("win_rate"),
        "avg_pnl": exact_scope.get("avg_pnl"),
        "avg_quality": exact_scope.get("avg_quality"),
        "avg_drawdown_penalty": exact_scope.get("avg_drawdown_penalty"),
        "avg_time_underwater": exact_scope.get("avg_time_underwater"),
        "current_live_structure_bucket": exact_scope.get("current_live_structure_bucket"),
        "current_live_structure_bucket_rows": exact_scope.get("current_live_structure_bucket_rows"),
    }

    candidate_scopes = [
        ("regime_label+entry_quality_label", "同 regime + quality 寬 scope"),
        ("entry_quality_label", "同 quality 寬 scope"),
        ("regime_label", "同 regime 寬 scope"),
        ("regime_gate", "同 gate 寬 scope"),
    ]

    best_candidate: Optional[Dict[str, Any]] = None
    best_rank: Optional[tuple[Any, ...]] = None
    for scope_name, scope_label in candidate_scopes:
        scope_payload = scope_diagnostics.get(scope_name)
        if not isinstance(scope_payload, dict) or not scope_payload:
            continue
        spillover = scope_payload.get("spillover_vs_exact_live_lane")
        if not isinstance(spillover, dict) or not spillover:
            continue

        extra_rows = int(spillover.get("extra_rows") or 0)
        worst_pocket = spillover.get("worst_extra_regime_gate")
        if extra_rows <= 0 or not isinstance(worst_pocket, dict) or not worst_pocket:
            continue

        pocket_quality = float(worst_pocket.get("avg_quality")) if _is_number(worst_pocket.get("avg_quality")) else float("inf")
        pocket_win_rate = float(worst_pocket.get("win_rate")) if _is_number(worst_pocket.get("win_rate")) else float("inf")
        pocket_rows = int(worst_pocket.get("rows") or 0)
        rank = (
            0 if pocket_quality < 0 else 1,
            pocket_quality,
            pocket_win_rate,
            -extra_rows,
            -pocket_rows,
        )
        if best_rank is None or rank < best_rank:
            best_rank = rank
            best_candidate = {
                "focus_scope": scope_name,
                "focus_scope_label": scope_label,
                "focus_scope_rows": scope_payload.get("rows"),
                "spillover": {
                    "extra_rows": extra_rows,
                    "extra_row_share": spillover.get("extra_row_share"),
                    "win_rate_delta_vs_exact": spillover.get("win_rate_delta_vs_exact"),
                    "avg_pnl_delta_vs_exact": spillover.get("avg_pnl_delta_vs_exact"),
                    "avg_quality_delta_vs_exact": spillover.get("avg_quality_delta_vs_exact"),
                    "avg_drawdown_penalty_delta_vs_exact": spillover.get("avg_drawdown_penalty_delta_vs_exact"),
                    "avg_time_underwater_delta_vs_exact": spillover.get("avg_time_underwater_delta_vs_exact"),
                    "worst_extra_regime_gate": worst_pocket,
                    "top_mean_shift_features": (
                        (spillover.get("worst_extra_regime_gate_feature_contrast") or {}).get("top_mean_shift_features")
                        if isinstance(spillover.get("worst_extra_regime_gate_feature_contrast"), dict)
                        else []
                    ) or [],
                },
            }

    if not best_candidate:
        return None

    spillover = best_candidate["spillover"]
    worst_pocket = spillover.get("worst_extra_regime_gate") if isinstance(spillover, dict) else {}
    summary = (
        f"{best_candidate['focus_scope_label']} 出現 {worst_pocket.get('regime_gate') or 'unknown'} spillover，"
        f"{int(spillover.get('extra_rows') or 0)} rows / WR {_fmt_pct(worst_pocket.get('win_rate'))}"
        f" / 品質 {_fmt_float(worst_pocket.get('avg_quality'))}，"
        f"明顯劣於 exact live lane WR {_fmt_pct(exact_live_lane.get('win_rate'))}"
        f" / 品質 {_fmt_float(exact_live_lane.get('avg_quality'))}。"
    )

    return {
        **best_candidate,
        "exact_live_lane": exact_live_lane,
        "summary": summary,
    }


def load_bull_4h_pocket_ablation_summary(
    path: Optional[Path] = None,
    *,
    warn: Optional[Callable[[str], None]] = None,
) -> Optional[Dict[str, Any]]:
    artifact_path = path or DEFAULT_BULL_4H_POCKET_ABLATION_PATH
    try:
        if not artifact_path.exists():
            return None
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception as exc:
        if warn is not None:
            warn(f"Failed to load bull 4h pocket ablation summary: {exc}")
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def build_live_pathology_patch_summary(
    confidence_payload: Dict[str, Any],
    scope_summary: Optional[Dict[str, Any]],
    *,
    artifact_path: Optional[Path] = None,
    warn: Optional[Callable[[str], None]] = None,
) -> Optional[Dict[str, Any]]:
    if not isinstance(scope_summary, dict):
        return None
    spillover = scope_summary.get("spillover")
    if not isinstance(spillover, dict):
        return None
    worst_pocket = spillover.get("worst_extra_regime_gate")
    if not isinstance(worst_pocket, dict):
        return None

    spillover_regime_gate = str(worst_pocket.get("regime_gate") or "").strip()
    reference_patch_scope = spillover_regime_gate

    resolved_artifact_path = artifact_path or DEFAULT_BULL_4H_POCKET_ABLATION_PATH
    ablation = load_bull_4h_pocket_ablation_summary(resolved_artifact_path, warn=warn)
    if not isinstance(ablation, dict):
        return None
    cohorts = ablation.get("cohorts") if isinstance(ablation.get("cohorts"), dict) else {}
    cohort = cohorts.get("bull_collapse_q35") if isinstance(cohorts.get("bull_collapse_q35"), dict) else {}
    recommended_profile = cohort.get("recommended_profile")
    if not recommended_profile:
        return None

    profile_metrics = (cohort.get("profiles") or {}).get(recommended_profile)
    if not isinstance(profile_metrics, dict):
        profile_metrics = {}

    support_summary = ablation.get("support_pathology_summary") if isinstance(ablation.get("support_pathology_summary"), dict) else {}
    live_context = ablation.get("live_context") if isinstance(ablation.get("live_context"), dict) else {}
    support_progress = confidence_payload.get("support_progress") if isinstance(confidence_payload.get("support_progress"), dict) else {}

    def _to_int(value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    current_rows = _to_int(support_progress.get("current_rows"))
    if current_rows is None:
        current_rows = _to_int(support_summary.get("current_live_structure_bucket_rows"))
    minimum_rows = _to_int(support_progress.get("minimum_support_rows"))
    if minimum_rows is None:
        minimum_rows = _to_int(support_summary.get("minimum_support_rows"))
    gap_to_minimum = _to_int(support_progress.get("gap_to_minimum"))
    if gap_to_minimum is None:
        gap_to_minimum = _to_int(support_summary.get("current_live_structure_bucket_gap_to_minimum"))
    if gap_to_minimum is None and current_rows is not None and minimum_rows is not None:
        gap_to_minimum = max(0, minimum_rows - current_rows)

    support_route_verdict = (
        confidence_payload.get("support_route_verdict")
        or live_context.get("support_route_verdict")
        or support_summary.get("blocker_state")
    )
    support_route_deployable = confidence_payload.get("support_route_deployable")
    if support_route_deployable is None:
        support_route_deployable = live_context.get("support_route_deployable")

    reference_source = "live_scope_spillover"
    if spillover_regime_gate != "bull|CAUTION":
        current_live_bucket = str(
            confidence_payload.get("current_live_structure_bucket")
            or confidence_payload.get("structure_bucket")
            or support_summary.get("current_live_structure_bucket")
            or ""
        ).strip()
        current_regime = str(confidence_payload.get("regime_label") or "").strip()
        exact_support_missing = False
        if minimum_rows is not None and current_rows is not None and current_rows < minimum_rows:
            exact_support_missing = True
        elif str(support_route_verdict or "").startswith("exact_bucket_missing"):
            exact_support_missing = True

        spillover_is_bull_pocket = spillover_regime_gate.startswith("bull|")
        fallback_applicable = (
            exact_support_missing
            and bool(recommended_profile)
            and (
                spillover_is_bull_pocket
                or current_regime == "bull"
                or "bull_" in current_live_bucket
                or "|bull_" in current_live_bucket
            )
        )
        if not fallback_applicable:
            return None
        reference_patch_scope = "bull|CAUTION"
        reference_source = "bull_4h_pocket_ablation.bull_collapse_q35"

    reference_only = not bool(support_route_deployable)
    if minimum_rows is not None and current_rows is not None and current_rows < minimum_rows:
        reference_only = True
    status = "reference_only_until_exact_support_ready" if reference_only else "deployable_patch_candidate"
    reference_patch_scope_text = reference_patch_scope or "—"
    reference_source_text = reference_source or "—"
    if reference_only:
        reason = (
            f"參考 patch 來自 {reference_patch_scope_text}（source: {reference_source_text}），"
            f"建議 profile={recommended_profile}；但 current live exact support 仍是 {current_rows if current_rows is not None else '—'}"
            f"/{minimum_rows if minimum_rows is not None else '—'}；"
            "目前只能作治理 / 訓練參考，不可直接放行 runtime。"
        )
    else:
        reason = (
            f"參考 patch 來自 {reference_patch_scope_text}（source: {reference_source_text}），可直接對應到 {recommended_profile} patch；"
            "exact support 已達 deployable 條件，可把它視為正式 runtime / training patch 候選。"
        )

    return {
        "status": status,
        "reason": reason,
        "spillover_regime_gate": spillover_regime_gate,
        "reference_patch_scope": reference_patch_scope,
        "spillover_rows": spillover.get("extra_rows"),
        "recommended_profile": recommended_profile,
        "recommended_profile_source": "bull_4h_pocket_ablation.bull_collapse_q35",
        "reference_source": reference_source,
        "collapse_features": ablation.get("collapse_features") or [],
        "min_collapse_flags": ablation.get("min_collapse_flags"),
        "preferred_support_cohort": support_summary.get("preferred_support_cohort"),
        "support_route_verdict": support_route_verdict,
        "support_route_deployable": bool(support_route_deployable),
        "current_live_structure_bucket": confidence_payload.get("current_live_structure_bucket")
        or confidence_payload.get("structure_bucket")
        or support_summary.get("current_live_structure_bucket"),
        "current_live_structure_bucket_rows": current_rows,
        "minimum_support_rows": minimum_rows,
        "gap_to_minimum": gap_to_minimum,
        "recommended_action": support_summary.get("recommended_action"),
        "cohort_rows": cohort.get("rows"),
        "cohort_base_win_rate": cohort.get("base_win_rate"),
        "profile_cv_mean_accuracy": profile_metrics.get("cv_mean_accuracy"),
        "generated_at": ablation.get("generated_at"),
        "source_artifact": str(resolved_artifact_path),
    }


def build_live_pathology_scope_surface(
    confidence_payload: Dict[str, Any],
    scope_diagnostics: Optional[Dict[str, Any]],
    *,
    artifact_path: Optional[Path] = None,
    warn: Optional[Callable[[str], None]] = None,
) -> Optional[Dict[str, Any]]:
    scope_summary = build_live_pathology_scope_summary(scope_diagnostics)
    patch_summary = build_live_pathology_patch_summary(
        confidence_payload,
        scope_summary,
        artifact_path=artifact_path,
        warn=warn,
    )
    if isinstance(scope_summary, dict) and isinstance(patch_summary, dict):
        return {
            **scope_summary,
            "recommended_patch": patch_summary,
        }
    return scope_summary
