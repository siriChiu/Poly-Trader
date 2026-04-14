#!/usr/bin/env python3
"""Probe leaderboard candidate-governance output for heartbeat verification."""
from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from server.routes import api as api_module  # noqa: E402

OUT_PATH = PROJECT_ROOT / "data" / "leaderboard_feature_profile_probe.json"


def main() -> int:
    payload = api_module._build_model_leaderboard_payload()
    leaderboard = payload.get("leaderboard") or []
    top = leaderboard[0] if leaderboard else {}
    result = {
        "generated_at": payload.get("snapshot_history", [{}])[0].get("created_at") if payload.get("snapshot_history") else None,
        "target_col": payload.get("target_col"),
        "leaderboard_count": payload.get("count", 0),
        "top_model": {
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
        },
    }
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
