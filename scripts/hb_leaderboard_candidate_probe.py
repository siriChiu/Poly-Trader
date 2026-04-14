#!/usr/bin/env python3
"""Probe leaderboard candidate-governance output for heartbeat verification."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any
import warnings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from server.routes import api as api_module  # noqa: E402

OUT_PATH = PROJECT_ROOT / "data" / "leaderboard_feature_profile_probe.json"
LAST_METRICS_PATH = PROJECT_ROOT / "model" / "last_metrics.json"
LIVE_PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
BULL_POCKET_PATH = PROJECT_ROOT / "data" / "bull_4h_pocket_ablation.json"
FEATURE_ABLATION_PATH = PROJECT_ROOT / "data" / "feature_group_ablation.json"


KNOWN_SKLEARN_FEATURE_NAME_WARNING_PATTERNS = (
    r"X has feature names, but LogisticRegression was fitted without feature names",
    r"X has feature names, but MLPClassifier was fitted without feature names",
    r"X has feature names, but SVC was fitted without feature names",
)


def _suppress_known_feature_name_warnings() -> None:
    """Hide noisy sklearn feature-name warnings from heartbeat probe stderr.

    The leaderboard probe reuses pre-fit sklearn models that were trained on ndarray
    inputs. During heartbeat governance we only need the resulting payload; repeated
    feature-name warnings drown out real stderr failures and make cron summaries hard
    to read. Keep the suppression narrowly scoped to the exact known warning strings.
    """
    for pattern in KNOWN_SKLEARN_FEATURE_NAME_WARNING_PATTERNS:
        warnings.filterwarnings(
            "ignore",
            message=pattern,
            category=UserWarning,
        )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _top_model_payload(payload: dict[str, Any]) -> dict[str, Any]:
    leaderboard = payload.get("leaderboard") or []
    top = leaderboard[0] if leaderboard else {}
    return {
        "model_name": top.get("model_name"),
        "deployment_profile": top.get("deployment_profile"),
        "selected_deployment_profile": top.get("selected_deployment_profile"),
        "deployment_profiles_evaluated": top.get("deployment_profiles_evaluated"),
        "feature_profile": top.get("feature_profile"),
        "selected_feature_profile": top.get("selected_feature_profile"),
        "selected_feature_profile_source": top.get("selected_feature_profile_source"),
        "feature_profiles_evaluated": top.get("feature_profiles_evaluated"),
        "selected_feature_profile_blocker_applied": top.get("selected_feature_profile_blocker_applied"),
        "selected_feature_profile_blocker_reason": top.get("selected_feature_profile_blocker_reason"),
        "feature_profile_support_cohort": top.get("feature_profile_support_cohort"),
        "feature_profile_support_rows": top.get("feature_profile_support_rows"),
        "feature_profile_exact_live_bucket_rows": top.get("feature_profile_exact_live_bucket_rows"),
        "feature_profile_candidate_diagnostics": top.get("feature_profile_candidate_diagnostics"),
        "overall_score": top.get("overall_score"),
        "avg_decision_quality_score": top.get("avg_decision_quality_score"),
    }


def _build_alignment(top_model: dict[str, Any]) -> dict[str, Any]:
    last_metrics = _load_json(LAST_METRICS_PATH)
    live_probe = _load_json(LIVE_PROBE_PATH)
    bull_pocket = _load_json(BULL_POCKET_PATH)
    feature_ablation = _load_json(FEATURE_ABLATION_PATH)

    live_context = bull_pocket.get("live_context") or {}
    cohorts = bull_pocket.get("cohorts") or {}
    support_cohort = cohorts.get("bull_supported_neighbor_buckets_proxy") or {}
    exact_lane_proxy = cohorts.get("bull_exact_live_lane_proxy") or {}
    exact_bucket_proxy = cohorts.get("bull_live_exact_lane_bucket_proxy") or {}
    live_bucket_rows = live_context.get("current_live_structure_bucket_rows")
    blocked_candidates = [
        {
            "feature_profile": row.get("feature_profile"),
            "feature_profile_source": row.get("feature_profile_source"),
            "support_cohort": row.get("support_cohort"),
            "support_rows": row.get("support_rows"),
            "exact_live_bucket_rows": row.get("exact_live_bucket_rows"),
            "blocker_reason": row.get("blocker_reason"),
        }
        for row in (top_model.get("feature_profile_candidate_diagnostics") or [])
        if row.get("blocker_applied")
    ]

    train_profile = last_metrics.get("feature_profile")
    global_recommended = feature_ablation.get("recommended_profile")
    leaderboard_selected = top_model.get("selected_feature_profile")
    dual_profile_state = "aligned"
    if leaderboard_selected != train_profile:
        dual_profile_state = "leaderboard_global_winner_vs_train_support_fallback"
    elif leaderboard_selected != global_recommended:
        dual_profile_state = "leaderboard_train_winner_vs_global_probe_drift"

    support_governance_route = "no_support_proxy"
    if int(live_bucket_rows or 0) > 0:
        support_governance_route = "exact_live_bucket_supported"
    elif int(exact_bucket_proxy.get("rows") or 0) > 0:
        support_governance_route = "exact_live_bucket_proxy_available"
    elif int(exact_lane_proxy.get("rows") or 0) > 0:
        support_governance_route = "exact_live_lane_proxy_available"
    elif int(support_cohort.get("rows") or 0) > 0:
        support_governance_route = "supported_neighbor_only"

    return {
        "global_recommended_profile": global_recommended,
        "train_selected_profile": train_profile,
        "train_selected_profile_source": last_metrics.get("feature_profile_source") or last_metrics.get("feature_profile_meta", {}).get("source"),
        "train_support_cohort": last_metrics.get("feature_profile_meta", {}).get("support_cohort"),
        "train_support_rows": last_metrics.get("feature_profile_meta", {}).get("support_rows"),
        "train_exact_live_bucket_rows": last_metrics.get("feature_profile_meta", {}).get("exact_live_bucket_rows"),
        "leaderboard_selected_profile": leaderboard_selected,
        "leaderboard_selected_profile_source": top_model.get("selected_feature_profile_source"),
        "dual_profile_state": dual_profile_state,
        "blocked_candidate_profiles": blocked_candidates,
        "live_regime_gate": live_probe.get("regime_gate"),
        "live_entry_quality_label": live_probe.get("entry_quality_label"),
        "live_execution_guardrail_reason": live_probe.get("execution_guardrail_reason"),
        "live_current_structure_bucket": live_context.get("current_live_structure_bucket"),
        "live_current_structure_bucket_rows": live_bucket_rows,
        "supported_neighbor_buckets": live_context.get("supported_neighbor_buckets") or [],
        "bull_support_aware_profile": support_cohort.get("recommended_profile"),
        "bull_support_neighbor_rows": support_cohort.get("rows"),
        "bull_exact_live_lane_proxy_profile": exact_lane_proxy.get("recommended_profile"),
        "bull_exact_live_lane_proxy_rows": exact_lane_proxy.get("rows"),
        "bull_live_exact_bucket_proxy_profile": exact_bucket_proxy.get("recommended_profile"),
        "bull_live_exact_bucket_proxy_rows": exact_bucket_proxy.get("rows"),
        "bull_exact_live_bucket_proxy_rows": exact_bucket_proxy.get("rows"),
        "support_governance_route": support_governance_route,
    }


def main() -> int:
    _suppress_known_feature_name_warnings()
    payload = api_module._build_model_leaderboard_payload()
    top_model = _top_model_payload(payload)
    result = {
        "generated_at": payload.get("snapshot_history", [{}])[0].get("created_at") if payload.get("snapshot_history") else None,
        "target_col": payload.get("target_col"),
        "leaderboard_count": payload.get("count", 0),
        "top_model": top_model,
        "alignment": _build_alignment(top_model),
    }
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
