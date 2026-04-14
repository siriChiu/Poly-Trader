#!/usr/bin/env python
"""Heartbeat predictor probe.

Runs the canonical predictor path against the local DB and prints a compact JSON
summary that proves inference is aligned with the current feature stack.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.models import init_db
from model.predictor import load_latest_features, load_predictor, predict

DB_URL = f"sqlite:///{PROJECT_ROOT / 'poly_trader.db'}"
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
        probe = {
            "db_url": DB_URL,
            "feature_timestamp": str(latest.get("timestamp")),
            "target_col": target_col,
            "used_model": used_model,
            "model_type": result.get("model_type"),
            "signal": result.get("signal"),
            "confidence": round(float(result.get("confidence", 0.0)), 6),
            "should_trade": bool(result.get("should_trade", False)),
            "regime_label": result.get("regime_label") or latest.get("regime_label"),
            "model_route_regime": result.get("model_route_regime"),
            "regime_gate": result.get("regime_gate"),
            "entry_quality": result.get("entry_quality"),
            "entry_quality_label": result.get("entry_quality_label"),
            "allowed_layers_raw": result.get("allowed_layers_raw"),
            "allowed_layers": result.get("allowed_layers"),
            "execution_guardrail_applied": result.get("execution_guardrail_applied"),
            "execution_guardrail_reason": result.get("execution_guardrail_reason"),
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
        print(json.dumps(probe, ensure_ascii=False, indent=2, default=str))
    finally:
        session.close()


if __name__ == "__main__":
    main()
