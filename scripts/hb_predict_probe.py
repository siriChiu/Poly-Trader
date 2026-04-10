#!/usr/bin/env python
"""Heartbeat predictor probe.

Runs the canonical predictor path against the local DB and prints a compact JSON
summary that proves inference is aligned with the current feature stack.
"""

from __future__ import annotations

import json
from pathlib import Path

from database.models import init_db
from model.predictor import load_latest_features, load_predictor, predict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
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
            "regime_label": latest.get("regime_label"),
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
