"""
模型訓練模組 v5 — sell-win aware + probability calibration
"""

import os
import json
import pickle
import sys
from pathlib import Path
from typing import Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import xgboost as xgb
from sqlalchemy.orm import Session
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.isotonic import IsotonicRegression

from database.models import FeaturesNormalized, Labels, RawMarketData
from utils.logger import setup_logger

logger = setup_logger(__name__)

DEFAULT_TARGET_COL = "simulated_pyramid_win"
MODEL_PATH = "model/xgb_model.pkl"
DB_PATH = str(Path(__file__).parent.parent / "poly_trader.db")
PROJECT_ROOT = Path(__file__).parent.parent
DW_RESULT_PATH = PROJECT_ROOT / "data" / "dw_result.json"
RECENT_DRIFT_REPORT_PATH = PROJECT_ROOT / "data" / "recent_drift_report.json"
FEATURE_ABLATION_PATH = PROJECT_ROOT / "data" / "feature_group_ablation.json"
BULL_4H_POCKET_ABLATION_PATH = PROJECT_ROOT / "data" / "bull_4h_pocket_ablation.json"
FEATURE_COLS = [
    # === 8 Core Senses ===
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue",
    "feat_body", "feat_pulse", "feat_aura", "feat_mind",
    # === 2 Macro ===
    "feat_vix", "feat_dxy",
    # === Technical Indicators ===
    "feat_rsi14", "feat_macd_hist", "feat_atr_pct",
    "feat_vwap_dev", "feat_bb_pct_b", "feat_nw_width",
    "feat_nw_slope", "feat_adx", "feat_choppiness", "feat_donchian_pos",
    # === 4H Timeframe Features (低雜訊大方向) ===
    "feat_4h_bias50", "feat_4h_bias20", "feat_4h_bias200",
    "feat_4h_rsi14", "feat_4h_macd_hist", "feat_4h_bb_pct_b",
    "feat_4h_dist_bb_lower", "feat_4h_ma_order",
    "feat_4h_dist_swing_low", "feat_4h_vol_ratio",
    # === P0/P1 Sensory + NQ ===
    # P0: Disabled — only 20 samples, no training signal (ic_status=LOW/NO_DATA)
    # "feat_claw", "feat_claw_intensity", "feat_fang_pcr",
    # "feat_fang_skew", "feat_fin_netflow", "feat_nq_return_1h",
    # === Re-enabled with sufficient data threshold ===
    # Re-add once these features have > 500 samples in the DB
]
LAG_STEPS = [12, 48, 288]
BASE_FEATURE_COLS = FEATURE_COLS
CORE_FEATURES = [
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue",
    "feat_body", "feat_pulse", "feat_aura", "feat_mind",
]
MACRO_FEATURES = ["feat_vix", "feat_dxy"]
TECHNICAL_FEATURES = [
    "feat_rsi14", "feat_macd_hist", "feat_atr_pct",
    "feat_vwap_dev", "feat_bb_pct_b", "feat_nw_width",
    "feat_nw_slope", "feat_adx", "feat_choppiness", "feat_donchian_pos",
]
FOUR_H_FEATURES = [
    "feat_4h_bias50", "feat_4h_bias20", "feat_4h_bias200",
    "feat_4h_rsi14", "feat_4h_macd_hist", "feat_4h_bb_pct_b",
    "feat_4h_dist_bb_lower", "feat_4h_ma_order",
    "feat_4h_dist_swing_low", "feat_4h_vol_ratio",
]
BULL_COLLAPSE_4H_FEATURES = [
    "feat_4h_bb_pct_b",
    "feat_4h_dist_bb_lower",
    "feat_4h_dist_swing_low",
]
STABLE_4H_FEATURES = [f for f in FOUR_H_FEATURES if f not in BULL_COLLAPSE_4H_FEATURES]
CROSS_FEATURES = [
    "feat_vix_x_eye", "feat_vix_x_pulse", "feat_vix_x_mind",
    "feat_mind_x_pulse", "feat_eye_x_ear", "feat_nose_x_aura",
    "feat_eye_x_body", "feat_ear_x_nose", "feat_mind_x_aura",
    "feat_regime_flag", "feat_mean_rev_proxy",
]
STRONG_BASELINE_FEATURE_PROFILE = "core_plus_macro"
MIN_SUPPORT_AWARE_BUCKET_ROWS = 50

REGIME_THRESHOLD_BIAS = {
    'trend': -0.03,
    'chop': 0.04,
    'panic': -0.01,
    'event': 0.02,
    'normal': 0.0,
}

TW_GUARDRAIL_ALERTS = {"constant_target", "regime_concentration"}


def _load_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _feature_and_lag_columns(all_columns: list[str], base_features: list[str]) -> list[str]:
    return [
        col
        for col in all_columns
        if any(col == base or col.startswith(f"{base}_lag") for base in base_features)
    ]


def _build_feature_profile_columns(all_columns: list[str]) -> dict[str, list[str]]:
    """Canonical feature-profile definitions used by ablation and training shrinkage."""
    lag_cols = [c for c in all_columns if "_lag" in c]
    cross_cols = [c for c in all_columns if c in CROSS_FEATURES]
    core_cols = [c for c in all_columns if c in CORE_FEATURES]
    macro_cols = [c for c in all_columns if c in MACRO_FEATURES]
    technical_cols = [c for c in all_columns if c in TECHNICAL_FEATURES]
    four_h_cols = [c for c in all_columns if c in FOUR_H_FEATURES]
    base_no_lags_cross = [c for c in all_columns if c not in lag_cols and c not in cross_cols]
    subsets = {
        "core_only": core_cols,
        "core_plus_4h": sorted(set(core_cols + four_h_cols)),
        "core_plus_technical": sorted(set(core_cols + technical_cols)),
        "core_plus_macro": sorted(set(core_cols + macro_cols)),
        "full_no_lags": sorted(set(base_no_lags_cross + cross_cols)),
        "full_no_cross": [c for c in all_columns if c not in cross_cols],
        "full_no_technical": [c for c in all_columns if c not in technical_cols],
        "full_no_macro": [c for c in all_columns if c not in macro_cols],
        "full_no_4h": [c for c in all_columns if c not in four_h_cols],
        "current_full": list(all_columns),
    }

    strong_baseline = subsets.get("core_plus_macro", [])
    stable_4h_with_lags = _feature_and_lag_columns(all_columns, STABLE_4H_FEATURES)
    weak_4h_with_lags = set(_feature_and_lag_columns(all_columns, BULL_COLLAPSE_4H_FEATURES))
    if strong_baseline and stable_4h_with_lags:
        subsets["core_macro_plus_stable_4h"] = sorted(set(strong_baseline + stable_4h_with_lags))
    if weak_4h_with_lags:
        subsets["current_full_no_bull_collapse_4h"] = [
            col for col in all_columns if col not in weak_4h_with_lags
        ]
    return subsets


def _rank_feature_profile(name: str, metrics: dict) -> tuple[float, float, float, float, str]:
    """Sort higher mean/worst and lower std/brier first."""
    return (
        float(metrics.get("cv_mean_accuracy", float("-inf"))),
        float(metrics.get("cv_worst_accuracy", float("-inf"))),
        -float(metrics.get("cv_std_accuracy", float("inf"))),
        -float(metrics.get("cv_mean_brier", float("inf"))),
        name,
    )


def _parse_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _select_support_aware_profile(
    profile_columns: dict[str, list[str]],
    ablation_payload: dict,
    bull_pocket_payload: dict,
    target_col: str,
) -> tuple[str, list[str], dict] | None:
    """Prefer a supported small-family profile when the live bull structure bucket has no support."""
    if not bull_pocket_payload or bull_pocket_payload.get("target_col") != target_col:
        return None

    profiles = ablation_payload.get("profiles") or {}
    if not profiles:
        return None

    live_context = bull_pocket_payload.get("live_context") or {}
    live_bucket_rows = _parse_int(live_context.get("current_live_structure_bucket_rows"), default=0)
    if live_bucket_rows >= MIN_SUPPORT_AWARE_BUCKET_ROWS:
        return None

    cohorts = bull_pocket_payload.get("cohorts") or {}
    for cohort_name in (
        "bull_live_exact_lane_bucket_proxy",
        "bull_exact_live_lane_proxy",
        "bull_supported_neighbor_buckets_proxy",
        "bull_collapse_q35",
    ):
        cohort = cohorts.get(cohort_name) or {}
        profile_name = cohort.get("recommended_profile")
        row_count = _parse_int(cohort.get("rows"), default=0)
        if (
            not profile_name
            or row_count < MIN_SUPPORT_AWARE_BUCKET_ROWS
            or profile_name not in profile_columns
            or profile_name not in profiles
        ):
            continue
        columns = profile_columns.get(profile_name) or []
        if not columns:
            continue
        return profile_name, columns, {
            "source": "bull_4h_pocket_ablation.support_aware_profile",
            "generated_at": bull_pocket_payload.get("generated_at"),
            "support_cohort": cohort_name,
            "support_rows": row_count,
            "exact_live_bucket_rows": live_bucket_rows,
            "minimum_support_rows": MIN_SUPPORT_AWARE_BUCKET_ROWS,
            "support_profile_rank": _rank_feature_profile(profile_name, profiles[profile_name]),
        }

    return None


def select_feature_profile(
    all_columns: list[str],
    target_col: str = DEFAULT_TARGET_COL,
    ablation_payload: Optional[dict] = None,
    bull_pocket_payload: Optional[dict] = None,
) -> tuple[str, list[str], dict]:
    """Choose a shrinkage profile automatically from the latest ablation report.

    This keeps training focused on the currently best validated feature family mix
    without adding new user-facing knobs.
    """
    profile_columns = _build_feature_profile_columns(all_columns)
    payload = ablation_payload if ablation_payload is not None else _load_json_file(FEATURE_ABLATION_PATH)
    bull_payload = (
        bull_pocket_payload
        if bull_pocket_payload is not None
        else ({} if ablation_payload is not None else _load_json_file(BULL_4H_POCKET_ABLATION_PATH))
    )
    profiles = payload.get("profiles") or {}
    recommended_name = payload.get("recommended_profile")
    compatible = (
        bool(payload)
        and payload.get("target_col") == target_col
        and all(name in profile_columns for name in profiles.keys())
    )

    if compatible:
        support_aware = _select_support_aware_profile(
            profile_columns=profile_columns,
            ablation_payload=payload,
            bull_pocket_payload=bull_payload,
            target_col=target_col,
        )
        if support_aware is not None:
            return support_aware

    if compatible and recommended_name in profile_columns:
        cols = profile_columns[recommended_name]
        if cols:
            return recommended_name, cols, {
                "source": "feature_group_ablation.recommended_profile",
                "generated_at": payload.get("generated_at"),
                "candidate_count": len(profiles),
            }

    if compatible and profiles:
        ranked = sorted(profiles.items(), key=lambda item: _rank_feature_profile(item[0], item[1]), reverse=True)
        best_name, best_metrics = ranked[0]
        cols = profile_columns.get(best_name) or []
        if cols:
            return best_name, cols, {
                "source": "feature_group_ablation.ranked_profiles",
                "generated_at": payload.get("generated_at"),
                "cv_mean_accuracy": float(best_metrics.get("cv_mean_accuracy", 0.0)),
                "cv_worst_accuracy": float(best_metrics.get("cv_worst_accuracy", 0.0)),
                "cv_std_accuracy": float(best_metrics.get("cv_std_accuracy", 0.0)),
            }

    fallback_name = STRONG_BASELINE_FEATURE_PROFILE if profile_columns.get(STRONG_BASELINE_FEATURE_PROFILE) else "current_full"
    return fallback_name, profile_columns.get(fallback_name, list(all_columns)), {
        "source": "code_default",
        "generated_at": None,
    }


def _load_tw_ic_guardrail() -> dict:
    """Load dynamic-window / drift guardrails for recency-heavy TW-IC weighting."""
    dw_payload = _load_json_file(DW_RESULT_PATH)
    drift_payload = _load_json_file(RECENT_DRIFT_REPORT_PATH)

    primary = drift_payload.get("primary_window") or {}
    primary_alerts = list(primary.get("alerts") or [])
    primary_window = primary.get("window")
    try:
        primary_window = int(primary_window) if primary_window is not None else 0
    except (TypeError, ValueError):
        primary_window = 0

    recommended_best_n = dw_payload.get("recommended_best_n")
    raw_best_n = dw_payload.get("raw_best_n")
    try:
        recommended_best_n = int(recommended_best_n) if recommended_best_n is not None else None
    except (TypeError, ValueError):
        recommended_best_n = None
    try:
        raw_best_n = int(raw_best_n) if raw_best_n is not None else None
    except (TypeError, ValueError):
        raw_best_n = None

    disqualifying = set((dw_payload.get("guardrail_policy") or {}).get("disqualifying_alerts") or [])
    if not disqualifying:
        disqualifying = set(TW_GUARDRAIL_ALERTS)

    raw_best = dw_payload.get(str(raw_best_n), {}) if raw_best_n is not None else {}
    raw_best_alerts = list(raw_best.get("alerts") or [])
    raw_best_guardrailed = bool(raw_best.get("distribution_guardrail")) or any(
        alert in disqualifying for alert in raw_best_alerts
    )
    should_dampen_recent_window = primary_window > 0 and any(
        alert in disqualifying for alert in primary_alerts
    )

    reason_parts = []
    if raw_best_guardrailed and raw_best_n is not None and recommended_best_n is not None:
        reason_parts.append(
            f"dynamic_window raw_best_n={raw_best_n} -> recommended_best_n={recommended_best_n}"
        )
    if should_dampen_recent_window:
        reason_parts.append(f"recent_window={primary_window} alerts={primary_alerts}")

    return {
        "recommended_best_n": recommended_best_n,
        "raw_best_n": raw_best_n,
        "raw_best_guardrailed": raw_best_guardrailed,
        "primary_window": primary_window,
        "primary_alerts": primary_alerts,
        "should_dampen_recent_window": should_dampen_recent_window,
        "guardrail_reason": "; ".join(reason_parts) if reason_parts else None,
    }


def _build_time_decay_weights(n_samples: int, tau: int = 200, guardrail: Optional[dict] = None) -> Tuple[np.ndarray, dict]:
    """Build TW-IC weights and damp polluted recent windows when guardrailed."""
    weights = np.exp(-(n_samples - 1 - np.arange(n_samples, dtype=float)) / tau)
    metadata = {
        "tau": tau,
        "applied": False,
        "damped_recent_rows": 0,
        "damp_factor": None,
        "primary_window": 0,
        "recommended_best_n": None,
        "raw_best_n": None,
        "guardrail_reason": None,
    }
    if not guardrail:
        return weights, metadata

    metadata.update(
        {
            "primary_window": int(guardrail.get("primary_window") or 0),
            "recommended_best_n": guardrail.get("recommended_best_n"),
            "raw_best_n": guardrail.get("raw_best_n"),
            "guardrail_reason": guardrail.get("guardrail_reason"),
        }
    )

    if not guardrail.get("should_dampen_recent_window"):
        return weights, metadata

    damp_rows = min(int(guardrail.get("primary_window") or 0), n_samples)
    if damp_rows <= 0:
        return weights, metadata

    damp_factor = 0.25
    if damp_rows >= n_samples:
        weights = weights * damp_factor
    else:
        boundary_idx = n_samples - damp_rows - 1
        boundary_weight = float(weights[boundary_idx])
        capped_weight = boundary_weight * damp_factor
        weights[-damp_rows:] = np.minimum(weights[-damp_rows:], capped_weight)

    metadata.update(
        {
            "applied": True,
            "damped_recent_rows": damp_rows,
            "damp_factor": damp_factor,
        }
    )
    return weights, metadata


def _ensure_regime_label_column(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize merge suffixes so downstream feature engineering sees one regime_label.

    Take a de-fragmenting copy before adding the column; otherwise pandas emits
    fragmentation warnings during training/diagnostic scripts that append many features.
    """
    if "regime_label" in df.columns:
        return df
    normalized = df.copy()
    if "regime_label_y" in normalized.columns:
        normalized["regime_label"] = normalized["regime_label_y"]
    elif "regime_label_x" in normalized.columns:
        normalized["regime_label"] = normalized["regime_label_x"]
    else:
        normalized["regime_label"] = "neutral"
    return normalized


def _append_cross_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add cross/regime features in one concat to avoid DataFrame fragmentation warnings."""
    df = _ensure_regime_label_column(df)
    cross_df = pd.DataFrame(
        {
            "feat_vix_x_eye": df["feat_vix"] * df["feat_eye"],
            "feat_vix_x_pulse": df["feat_vix"] * df["feat_pulse"],
            "feat_vix_x_mind": df["feat_vix"] * df["feat_mind"],
            "feat_mind_x_pulse": df["feat_mind"] * df["feat_pulse"],
            "feat_eye_x_ear": df["feat_eye"] * df["feat_ear"],
            "feat_nose_x_aura": df["feat_nose"] * df["feat_aura"],
            "feat_eye_x_body": df["feat_eye"] * df["feat_body"],
            "feat_ear_x_nose": df["feat_ear"] * df["feat_nose"],
            "feat_mind_x_aura": df["feat_mind"] * df["feat_aura"],
            "feat_regime_flag": df["regime_label"].map({
                "trend": 1.0,
                "chop": -1.0,
                "panic": -0.5,
                "event": 0.5,
                "normal": 0.0,
            }).fillna(0.0),
            "feat_mean_rev_proxy": df["feat_mind"] - df["feat_aura"],
        },
        index=df.index,
    )
    return pd.concat([df, cross_df], axis=1)


def _feature_row(r):
    return {
        "timestamp": r.timestamp,
        "symbol": getattr(r, "symbol", "BTCUSDT"),
        **{c: getattr(r, c, None) for c in FEATURE_COLS},
        "regime_label": getattr(r, "regime_label", None),
    }


def _align_sparse_4h_features(feat_df: pd.DataFrame, tolerance: str = "6h") -> pd.DataFrame:
    """Align sparse 4H snapshots onto dense 1m feature rows via asof merge.

    This replaces training-time forward-fill. 4H features remain independently
    computed rows in the DB; we simply attach the latest available 4H snapshot to
    each dense row using timestamp alignment with an explicit tolerance.
    """
    if feat_df.empty:
        return feat_df

    df = feat_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
    df = df.sort_values("timestamp").reset_index(drop=True)

    cols_4h = [c for c in FEATURE_COLS if c.startswith("feat_4h_") and c in df.columns]
    regime_col = ["regime_label"] if "regime_label" in df.columns else []
    sparse_cols = ["timestamp", *regime_col, *cols_4h]
    sparse_4h = df[sparse_cols].dropna(subset=cols_4h, how="all").copy()

    if sparse_4h.empty:
        return df

    base_cols = [c for c in df.columns if c not in ["regime_label", *cols_4h]]
    base_df = df[base_cols].copy()
    sparse_4h = sparse_4h.sort_values("timestamp").rename(columns={"regime_label": "regime_label_4h"})

    aligned = pd.merge_asof(
        base_df.sort_values("timestamp"),
        sparse_4h,
        on="timestamp",
        direction="backward",
        tolerance=pd.Timedelta(tolerance),
    )

    if "regime_label_4h" in aligned.columns:
        aligned["regime_label"] = aligned.pop("regime_label_4h")
    elif "regime_label" not in aligned.columns:
        aligned["regime_label"] = None
    return aligned


def load_training_data(session: Session, min_samples: int = 50,
                       regime_filter: Optional[list] = None,
                       horizon_minutes: int = 1440,
                       target_col: str = DEFAULT_TARGET_COL) -> Optional[Tuple[pd.DataFrame, pd.Series]]:
    """Load training data from DB, filtered by horizon_minutes.

    Args:
        session: SQLAlchemy session
        min_samples: minimum samples after merge
        regime_filter: optional list of regime labels to keep
        horizon_minutes: label horizon to use (default 1440=24h). Pass None for all horizons.
    """
    feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
    target_attr = getattr(Labels, target_col, None)
    if target_attr is None:
        logger.warning(f"Labels model lacks target column: {target_col}")
        return None

    label_query = session.query(Labels).filter(
        target_attr.isnot(None),
        Labels.future_return_pct.isnot(None),
    )
    if horizon_minutes is not None:
        label_query = label_query.filter(Labels.horizon_minutes == horizon_minutes)
    label_rows = label_query.order_by(Labels.timestamp).all()

    if not feat_rows or not label_rows:
        return None

    feat_df = pd.DataFrame([_feature_row(r) for r in feat_rows])
    feat_df = _align_sparse_4h_features(feat_df)
    label_df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "label_spot_long_win": int(r.label_spot_long_win) if r.label_spot_long_win is not None else int(r.label_up or 0),
        "label_spot_long_tp_hit": int(r.label_spot_long_tp_hit) if getattr(r, 'label_spot_long_tp_hit', None) is not None else None,
        "label_spot_long_quality": float(r.label_spot_long_quality) if getattr(r, 'label_spot_long_quality', None) is not None else None,
        "simulated_pyramid_win": int(r.simulated_pyramid_win) if getattr(r, 'simulated_pyramid_win', None) is not None else None,
        "simulated_pyramid_pnl": float(r.simulated_pyramid_pnl) if getattr(r, 'simulated_pyramid_pnl', None) is not None else None,
        "simulated_pyramid_quality": float(r.simulated_pyramid_quality) if getattr(r, 'simulated_pyramid_quality', None) is not None else None,
        "simulated_pyramid_drawdown_penalty": float(r.simulated_pyramid_drawdown_penalty) if getattr(r, 'simulated_pyramid_drawdown_penalty', None) is not None else None,
        "simulated_pyramid_time_underwater": float(r.simulated_pyramid_time_underwater) if getattr(r, 'simulated_pyramid_time_underwater', None) is not None else None,
        "label_sell_win": int(r.label_sell_win) if r.label_sell_win is not None else None,
        "label_up": int(r.label_up) if r.label_up is not None else None,
        "future_return_pct": float(r.future_return_pct) if r.future_return_pct is not None else None,
        "future_max_drawdown": float(r.future_max_drawdown) if r.future_max_drawdown is not None else None,
        "future_max_runup": float(r.future_max_runup) if r.future_max_runup is not None else None,
        "regime_label": r.regime_label if r.regime_label else "neutral",
    } for r in label_rows])

    feat_df["timestamp"] = pd.to_datetime(feat_df["timestamp"])
    label_df["timestamp"] = pd.to_datetime(label_df["timestamp"])

    merged = pd.merge_asof(
        feat_df.sort_values("timestamp"),
        label_df.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("10min"),
    )
    if target_col not in merged.columns:
        logger.warning(f"目標欄位不存在: {target_col}")
        return None
    merged = merged.dropna(subset=[target_col]).copy()

    # P0 #H430: Regime Filtering — optional exclusion of noisy regimes.
    # Experiment showed Bear+Bull only (exclude Chop) with IC pruning gives AUC=0.5454
    # vs 0.5241 for ALL regimes. Useful for production when chop degrades performance.
    if regime_filter is not None and len(regime_filter) > 0:
        before_count = len(merged)
        merged = merged[merged["regime_label"].isin(regime_filter)].copy()
        logger.info(f"Regime filter applied: keeping {regime_filter}, {before_count} → {len(merged)} samples")
        if len(merged) < min_samples:
            logger.warning(f"After regime filter, too few samples: {len(merged)} < {min_samples}")
            return None

    lag_feature_cols = []
    for col in BASE_FEATURE_COLS:
        for lag in LAG_STEPS:
            lag_col = f"{col}_lag{lag}"
            merged[lag_col] = merged[col].shift(lag)
            lag_feature_cols.append(lag_col)

    all_cols = FEATURE_COLS + lag_feature_cols
    # Coerce all feature columns to numeric — handles NULL/None/object dtype
    for col in all_cols:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')

    # 4H features are aligned independently via _align_sparse_4h_features().
    # Only fill any leading gaps that still remain after the timestamp alignment.
    FILL4H_COLS = [c for c in FEATURE_COLS if c.startswith('feat_4h_')]
    for col in FILL4H_COLS:
        median_val = merged[col].median()
        if pd.isna(median_val):
            median_val = 0.0
        merged[col] = merged[col].fillna(median_val)

    # P0 audit: Count non-null AFTER ffill, BEFORE general fillna
    non_null_before = {col: int(merged[col].notna().sum()) for col in all_cols}

    # Fill remaining NaN with 0 for XGBoost (only non-4H cols; 4H already ffill'd)
    for col in all_cols:
        if col not in FILL4H_COLS:
            remaining_na = merged[col].isna().sum()
            if remaining_na > 0:
                merged[col] = merged[col].fillna(0.0)

    if len(merged) < min_samples:
        logger.warning(f"合併後樣本不足: {len(merged)} < {min_samples}")
        return None

    from scipy import stats as _stats

    merged = merged.copy()
    ic_map = {}
    ic_map_global = {}
    tw_ic_map = {}
    NEG_IC_FEATS = []
    y_arr = merged[target_col].astype(float).values
    all_feature_cols = FEATURE_COLS + lag_feature_cols
    N = len(y_arr)

    # P0 #H425: Time-weighted IC (TW-IC) — exponential decay gives recent samples more influence.
    # tau=200 matches production predictor (predictor.py:_time_weighted_ic).
    # For non-core features (lags, crosses), fall back to global Spearman IC.
    tau = 200
    core_cols = set(FEATURE_COLS)  # 8 core senses + VIX + DXY
    tw_guardrail = _load_tw_ic_guardrail()
    weights, tw_guardrail_meta = _build_time_decay_weights(N, tau=tau, guardrail=tw_guardrail)

    for col in all_feature_cols:
        feat_arr = merged[col].astype(float).values
        mask = ~(np.isnan(feat_arr) | np.isnan(y_arr))
        if mask.sum() > 30:
            masked_f = feat_arr[mask]
            masked_y = y_arr[mask]
            # Skip constant columns
            if np.ptp(masked_f) == 0.0 or np.unique(masked_f).size <= 1:
                ic_map[col] = 0.0
                ic_map_global[col] = 0.0
                tw_ic_map[col] = 0.0
                continue

            # Global Spearman IC (baseline for reference)
            corr_g, _ = _stats.spearmanr(masked_f, masked_y)
            if corr_g is None or not np.isfinite(corr_g):
                corr_g = 0.0
            ic_map_global[col] = float(corr_g)

            if col in core_cols:
                # Time-weighted IC for core senses
                masked_w = weights[mask]
                wm_f = np.average(masked_f, weights=masked_w)
                wm_y = np.average(masked_y, weights=masked_w)
                cov = np.average((masked_f - wm_f) * (masked_y - wm_y), weights=masked_w)
                var_f = np.average((masked_f - wm_f)**2, weights=masked_w)
                var_y = np.average((masked_y - wm_y)**2, weights=masked_w)
                tw_ic = cov / (np.sqrt(var_f * var_y) + 1e-15)
                ic_map[col] = float(tw_ic)
                tw_ic_map[col] = float(tw_ic)
            else:
                # Non-core features: use global IC
                ic_map[col] = float(corr_g)
                tw_ic_map[col] = 0.0  # not computed for non-core

            if ic_map[col] < 0:
                NEG_IC_FEATS.append(col)
                merged[col] = -merged[col]
        else:
            ic_map[col] = 0.0
            ic_map_global[col] = 0.0
            tw_ic_map[col] = 0.0

    # P0 #H425: Compute null counts + IC status, then save
    os.makedirs("model", exist_ok=True)
    core_ic_summary = {c: round(ic_map.get(c, 0), 4) for c in FEATURE_COLS}
    tw_ic_summary = {c: round(tw_ic_map.get(c, 0), 4) for c in FEATURE_COLS}

    # P0#2: null counts from pre-fillna
    null_counts = non_null_before.copy()
    # P0#2: IC status classification
    ic_status = {}
    for col in all_feature_cols:
        nn = null_counts.get(col, 0)
        total = len(merged)
        if nn == 0:
            ic_status[col] = "NO_DATA"
        elif nn < total * 0.1:
            ic_status[col] = f"LOW({nn}/{total})"
        elif abs(ic_map.get(col, 0)) >= 0.05:
            ic_status[col] = "PASS"
        else:
            ic_status[col] = "FAIL"

    with open("model/ic_signs.json", "w", encoding="utf-8") as f:
        json.dump({
            "neg_ic_feats": NEG_IC_FEATS,
            "ic_map": ic_map,
            "ic_global": ic_map_global,
            "ic_tw": tw_ic_map,
            "null_counts": null_counts,
            "ic_status": ic_status,
            "total_samples": len(merged),
            "target": target_col,
            "core_ic_summary": core_ic_summary,
            "tw_ic_summary": tw_ic_summary,
            "tw_guardrail": tw_guardrail_meta,
        }, f, indent=2, ensure_ascii=False)
    logger.info(f"TW-IC (core): {tw_ic_summary}")
    logger.info(f"Global IC (core): {core_ic_summary}")
    logger.info(f"TW-IC guardrail: {tw_guardrail_meta}")
    logger.info(f"動態 TW-IC/Global IC 計算完成 — core 使用 TW-IC, 其餘使用 Global IC")
    logger.info(f"NEG_IC 反轉特徵: {NEG_IC_FEATS}")

    # High-IC alternative features discovered via hb105_exploratory_analysis (IC > 0.05):
    # eye_dist +0.050, mean_rev_20h -0.056, price_ret_12h -0.052, price_ret_24h -0.051, rsi_14_norm -0.051
    # These are derived from raw market data — need close_price from raw_market_data join
    # For now, construct them from the base features we have

    # Price return features (from feat_eye which is close_price normalized via return_24h/vol_72h,
    # we can approximate using the eye_dist which IS in raw_market_data)
    # Note: feat_eye IS eye_dist (alias in models.py), so it already contains the high-IC eye_dist signal

    # VIX / cross-sense / regime interaction features.
    # Build in one concat so retraining does not emit pandas fragmentation warnings.
    merged = _append_cross_features(merged)

    # RSI proxy: nose IS rsi14_norm, so use it directly as-is (already in FEATURE_COLS)

    CROSS_FEATURES = [
        "feat_vix_x_eye", "feat_vix_x_pulse", "feat_vix_x_mind",
        "feat_mind_x_pulse", "feat_eye_x_ear", "feat_nose_x_aura",
        "feat_eye_x_body", "feat_ear_x_nose", "feat_mind_x_aura",
        "feat_regime_flag", "feat_mean_rev_proxy",
        # P0: Disabled — base features have <500 samples
        # "feat_claw_x_pulse", "feat_fang_x_vix",
        # "feat_fin_x_claw", "feat_web_x_fang", "feat_nq_x_vix",
    ]

    all_training_cols = FEATURE_COLS + lag_feature_cols + CROSS_FEATURES

    # P0 #H430: Dynamic IC Pruning — remove features with |IC| < 0.03.
    # Experiment showed this improves OOF AUC from 0.524 → 0.529 (ALL) and 0.521 → 0.545 (Bear+Bull).
    # Only prune lag and cross features; always keep core FEATURE_COLS.
    IC_PRUNE_THRESHOLD = 0.03
    pruned_cols = []
    pruned_count = 0
    for col in all_training_cols:
        if col in set(FEATURE_COLS):
            pruned_cols.append(col)  # Always keep base features before shrinkage profile selection
            continue
        # For lag/cross features, check IC
        base_col = col.replace("_lag12", "").replace("_lag48", "").replace("_lag144", "")
        feat_ic = abs(ic_map.get(base_col, 0))
        col_ic = abs(ic_map.get(col, 0))
        # Use the base feature's IC for lag features, the feature's own IC for cross features
        effective_ic = max(feat_ic, col_ic)
        if effective_ic >= IC_PRUNE_THRESHOLD:
            pruned_cols.append(col)
        else:
            pruned_count += 1
    if pruned_count > 0:
        logger.info(f"P0 #H430: IC Pruning — dropped {pruned_count} features (|IC| < {IC_PRUNE_THRESHOLD}), keeping {len(pruned_cols)}/{len(all_training_cols)}")
        all_training_cols = pruned_cols

    feature_profile_name, all_training_cols, feature_profile_meta = select_feature_profile(
        all_training_cols,
        target_col=target_col,
    )
    logger.info(
        "Feature shrinkage profile selected: %s (%s cols, source=%s)",
        feature_profile_name,
        len(all_training_cols),
        feature_profile_meta.get("source"),
    )

    X = merged[all_training_cols].copy()
    X.attrs["feature_profile"] = feature_profile_name
    X.attrs["feature_profile_meta"] = feature_profile_meta
    y = merged[target_col].astype(int)
    y_return = merged["future_return_pct"].astype(float)
    logger.info(f"載入訓練資料: {len(X)} 筆, {len(all_training_cols)} features (profile={feature_profile_name}, pruned={pruned_count})")
    logger.info(f"分類目標 {target_col} ratio: {y.mean():.3f}, 回歸目標 future_return_pct mean={y_return.mean():.5f} std={y_return.std():.5f}")
    return X, y, y_return


def train_xgboost(X: pd.DataFrame, y: pd.Series, params: Optional[dict] = None) -> xgb.XGBClassifier:
    dist = y.value_counts().sort_index().to_dict()
    logger.info(f"Class dist: {dist}")

    if params is None:
        # P0 Fix #H392 #H130: Reduce Train-CV gap (was +20pp: 71% vs 51%)
        # Stronger regularization + lower depth + subsampling to fight overfit
        params = {
            "n_estimators": 500,
            "max_depth": 2,
            "learning_rate": 0.02,
            "subsample": 0.6,
            "colsample_bytree": 0.6,
            "colsample_bylevel": 0.7,
            "reg_alpha": 5.0,
            "reg_lambda": 10.0,
            "min_child_weight": 20,
            "gamma": 0.5,
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "random_state": 42,
        }

    sample_weight = compute_sample_weight("balanced", y)
    model = xgb.XGBClassifier(**params)
    model.fit(X, y, sample_weight=sample_weight)
    logger.info("XGBoost v5 binary training completed")
    return model


def fit_probability_calibrator(model, X: pd.DataFrame, y: pd.Series):
    """Fit a lightweight calibration layer and return serializable metadata."""
    try:
        raw = model.predict_proba(X)
        scores = raw[:, -1] if raw.ndim == 2 and raw.shape[1] >= 2 else np.asarray(raw).ravel()
        scores = np.asarray(scores, dtype=float)
        y_arr = y.astype(float).values

        if len(np.unique(y_arr)) >= 2 and len(y_arr) >= 30:
            iso = IsotonicRegression(out_of_bounds='clip')
            iso.fit(scores, y_arr)
            xs = [float(v) for v in iso.X_thresholds_.tolist()]
            ys = [float(v) for v in iso.y_thresholds_.tolist()]
            return {
                'kind': 'isotonic',
                # Keep both legacy and canonical keys so older predictor payloads
                # remain readable while new code can use explicit names.
                'x': xs,
                'y': ys,
                'isotonic_x': xs,
                'isotonic_y': ys,
            }

        p = np.clip(scores, 1e-6, 1 - 1e-6)
        logit = np.log(p / (1 - p))
        return {
            'kind': 'logit_affine',
            'mu': float(np.mean(logit)),
            'sigma': float(np.std(logit) or 1.0),
        }
    except Exception as e:
        logger.warning(f"calibrator fit failed: {e}")
        return {'kind': 'none'}


def save_model(model, path: str = MODEL_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"模型已保存: {path}")


def load_model(path: str = MODEL_PATH):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def run_training(session: Session, regime_filter: Optional[list] = None, target_col: str = DEFAULT_TARGET_COL) -> bool:
    """Train global XGBoost model with IC pruning and optional regime filtering.
    
    Args:
        session: SQLAlchemy session
        regime_filter: Optional list of regime labels to keep (e.g., ["bear", "bull"]).
                      If None, uses all regimes. Experiment shows Bear+Bull filtering
                      with IC pruning gives AUC=0.5454 vs 0.5241 for ALL.
        target_col: Label column to optimize. Supports label_spot_long_win and
                    simulated_pyramid_win for target-comparison experiments.
    """
    logger.info(f"開始模型訓練 v5 (with IC pruning + optional regime filter, target={target_col})...")
    loaded = load_training_data(session, min_samples=50, regime_filter=regime_filter, target_col=target_col)
    if loaded is None:
        return False
    X, y, y_return = loaded
    model = train_xgboost(X, y)
    calibrator = fit_probability_calibrator(model, X, y)
    feature_profile = X.attrs.get("feature_profile", "current_full")
    feature_profile_meta = X.attrs.get("feature_profile_meta", {"source": "unknown"})

    neg_ic = []
    ic_path = Path('model/ic_signs.json')
    if ic_path.exists():
        try:
            neg_ic = json.loads(ic_path.read_text(encoding='utf-8')).get('neg_ic_feats', [])
        except Exception:
            neg_ic = []

    payload = {
        'clf': model,
        'feature_names': X.columns.tolist(),
        'feature_profile': feature_profile,
        'feature_profile_meta': feature_profile_meta,
        'neg_ic_feats': neg_ic,
        'calibration': calibrator,
        'regime_threshold_bias': REGIME_THRESHOLD_BIAS,
        'target_col': target_col,
    }
    save_model(payload)
    imp = dict(zip(X.columns.tolist(), model.feature_importances_.tolist()))
    logger.info(f"特徵重要性: {imp}")

    try:
        from datetime import datetime
        import sqlite3
        train_acc = float((model.predict(X) == y).mean())

        # Rolling/expanding window CV — more realistic for financial time series.
        # Uses multiple train/test windows that mimic walk-forward validation:
        # - Train on 60% of data, test on next 10%, sliding forward in steps.
        # - Reports both mean and worst-fold accuracy to detect overfitting.
        cv_scores = []
        n = len(X)
        train_frac = 0.6
        test_frac = 0.1
        step_frac = 0.08  # slide the window by 8% of data each time

        train_base = int(n * train_frac)
        test_size = max(int(n * test_frac), 20)
        step = max(int(n * step_frac), 10)

        start = train_base
        while start + test_size <= n:
            train_idx = list(range(0, start))
            test_idx = list(range(start, start + test_size))
            y_tr = y.iloc[train_idx]
            if len(y_tr.unique()) < 2:
                start += step
                continue
            _m = xgb.XGBClassifier(**{k: v for k, v in model.get_params().items()})
            _m.fit(X.iloc[train_idx], y_tr, sample_weight=compute_sample_weight("balanced", y_tr))
            fold_acc = float((_m.predict(X.iloc[test_idx]) == y.iloc[test_idx]).mean())
            cv_scores.append(fold_acc)
            start += step

        cv_acc = float(np.mean(cv_scores)) if cv_scores else float('nan')
        cv_std = float(np.std(cv_scores)) if cv_scores else float('nan')
        cv_worst = float(np.min(cv_scores)) if cv_scores else float('nan')
        cv_best = float(np.max(cv_scores)) if cv_scores else float('nan')
        n_folds = len(cv_scores)

        trained_at = datetime.utcnow().isoformat()
        db = sqlite3.connect('poly_trader.db')
        cur = db.cursor()
        cur.execute("""
            INSERT INTO model_metrics (timestamp, train_accuracy, cv_accuracy, cv_std, n_features, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (trained_at, train_acc, cv_acc, cv_std, X.shape[1],
              f'target={target_col} rolling_cv n={n_folds} worst={cv_worst:.4f} best={cv_best:.4f}'))
        db.commit(); db.close()
        metrics_payload = {
            'target_col': target_col,
            'feature_profile': feature_profile,
            'feature_profile_meta': feature_profile_meta,
            'train_accuracy': train_acc,
            'cv_accuracy': cv_acc,
            'cv_std': cv_std,
            'cv_worst': cv_worst,
            'cv_best': cv_best,
            'n_samples': int(len(X)),
            'n_features': int(X.shape[1]),
            'positive_ratio': float(y.mean()),
            'trained_at': trained_at,
        }
        Path('model').mkdir(parents=True, exist_ok=True)
        Path('model/last_metrics.json').write_text(json.dumps(metrics_payload, indent=2, ensure_ascii=False), encoding='utf-8')
        logger.info(f"模型指標: Train={train_acc:.3f}, Rolling-CV={cv_acc:.3f}±{cv_std:.3f}, worst={cv_worst:.3f}")
    except Exception as e:
        logger.warning(f"無法保存 model_metrics: {e}")

    return True


def train_regime_models(session: Session, target_col: str = DEFAULT_TARGET_COL) -> dict:
    """Train one XGBoost model per market regime with per-regime params and walk-forward CV.
    Addresses P0 #CV_CEILING and #BULL_CHOP_DEAD: global model CV stuck ~51% because
    one model tries to fit conflicting signal patterns across regimes.
    Each regime gets optimized hyperparameters and a walk-forward CV score.
    Returns dict: {regime: {cv_accuracy, train_accuracy, n_samples, params}}
    """
    from sklearn.model_selection import TimeSeriesSplit
    from itertools import product
    logger.info("開始訓練 Regime-Specific XGBoost 模型 (per-regime params + walk-forward CV)...")

    feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
    target_attr = getattr(Labels, target_col, None)
    if target_attr is None:
        logger.warning(f"Regime training target column missing: {target_col}")
        return {}

    label_rows = (
        session.query(Labels)
        .filter(target_attr.isnot(None), Labels.future_return_pct.isnot(None),
                Labels.horizon_minutes == 1440)
        .order_by(Labels.timestamp)
        .all()
    )
    if not feat_rows or not label_rows:
        logger.warning("訓練資料不足，跳過 regime-specific 訓練")
        return {}

    feat_df = pd.DataFrame([_feature_row(r) for r in feat_rows])
    feat_df = _align_sparse_4h_features(feat_df)
    label_df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "label_spot_long_win": int(r.label_spot_long_win) if r.label_spot_long_win is not None else int(r.label_up or 0),
        "simulated_pyramid_win": int(r.simulated_pyramid_win) if getattr(r, 'simulated_pyramid_win', None) is not None else None,
        "label_sell_win": int(r.label_sell_win) if r.label_sell_win is not None else None,
        "future_return_pct": float(r.future_return_pct) if r.future_return_pct is not None else None,
        "future_max_drawdown": float(r.future_max_drawdown) if r.future_max_drawdown is not None else None,
        "future_max_runup": float(r.future_max_runup) if r.future_max_runup is not None else None,
        "regime_label": r.regime_label if r.regime_label else "neutral",
    } for r in label_rows])

    feat_df["timestamp"] = pd.to_datetime(feat_df["timestamp"])
    label_df["timestamp"] = pd.to_datetime(label_df["timestamp"])

    merged = pd.merge_asof(
        feat_df.sort_values("timestamp"),
        label_df.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("10min"),
    )
    if target_col not in merged.columns:
        logger.warning(f"Regime training merged frame missing target: {target_col}")
        return {}
    merged = merged.dropna(subset=[target_col]).copy().sort_values("timestamp").reset_index(drop=True)

    # Handle merge suffix for regime_label
    if "regime_label" not in merged.columns:
        if "regime_label_y" in merged.columns:
            merged["regime_label"] = merged["regime_label_y"]
        elif "regime_label_x" in merged.columns:
            merged["regime_label"] = merged["regime_label_x"]
        else:
            merged["regime_label"] = "neutral"

    # Build feature columns
    for col in BASE_FEATURE_COLS:
        for lag in LAG_STEPS:
            lag_col = f"{col}_lag{lag}"
            merged[lag_col] = merged[col].shift(lag)

    all_feat_cols = FEATURE_COLS + [f"{c}_lag{l}" for c in BASE_FEATURE_COLS for l in LAG_STEPS]
    for col in all_feat_cols:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')
    # 4H features are aligned independently via _align_sparse_4h_features().
    FILL4H = [c for c in FEATURE_COLS if c.startswith('feat_4h_')]
    for col in FILL4H:
        median_val = merged[col].median()
        if pd.isna(median_val):
            median_val = 0.0
        merged[col] = merged[col].fillna(median_val)
    merged[all_feat_cols] = merged[all_feat_cols].fillna(0.0)

    # Cross features
    merged = _append_cross_features(merged)

    X_cols = [c for c in all_feat_cols + CROSS_FEATURES if c in merged.columns]

    # === Per-regime param grids (tuned for sample size and signal characteristics) ===
    regime_param_grids = {
        'bear': {
            # Bear: aggressive regularization (fewer samples, noisy signals)
            'max_depth': [2],
            'learning_rate': [0.02, 0.03],
            'reg_lambda': [15, 20],
            'min_child_weight': [30, 40],
        },
        'bull': {
            # Bull: moderate params (trend signals are clearer but still noisy)
            'max_depth': [3],
            'learning_rate': [0.03, 0.05],
            'reg_lambda': [8, 12],
            'min_child_weight': [15, 20],
        },
        'chop': {
            # Chop: very aggressive regularization (choppy = high noise, low signal)
            'max_depth': [2],
            'learning_rate': [0.01, 0.02],
            'reg_lambda': [25, 30],
            'min_child_weight': [50, 60],
        },
    }

    base_params = {
        "n_estimators": 300,
        "subsample": 0.7,
        "colsample_bytree": 0.6,
        "reg_alpha": 5.0,
        "gamma": 0.3,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "random_state": 42,
    }

    regime_models = {}
    regime_stats = {}

    for regime, param_grid in regime_param_grids.items():
        regime_mask = merged['regime_label'] == regime
        regime_data = merged[regime_mask].copy()
        n = len(regime_data)
        if n < 200:
            logger.warning(f"Regime {regime}: only {n} samples, skipping")
            continue

        X_r = regime_data[X_cols].fillna(0.0)
        y_r = regime_data[target_col].astype(int)

        param_lists = list(product(
            param_grid.get('max_depth', [base_params.get('max_depth', 3)]),
            param_grid.get('learning_rate', [base_params.get('learning_rate', 0.03)]),
            param_grid.get('reg_lambda', [base_params.get('reg_lambda', 10)]),
            param_grid.get('min_child_weight', [base_params.get('min_child_weight', 20)])
        ))

        best_cv = -1
        best_params = None
        best_cv_scores = []

        # Walk-forward CV with expanding window
        n_val = max(int(n * 0.15), 50)
        n_train_min = max(int(n * 0.4), 100)
        step = max(int(n * 0.08), 20)

        logger.info(f"Regime {regime}: testing {len(param_lists)} param combos, n={n}")

        for md, lr, rl, mcw in param_lists:
            test_params = {**base_params,
                          "max_depth": md, "learning_rate": lr,
                          "reg_lambda": rl, "min_child_weight": mcw}

            cv_scores = []
            start = n_train_min
            while start + n_val <= n:
                y_tr = y_r.iloc[:start]
                y_te = y_r.iloc[start:start+n_val]
                if len(y_tr.unique()) < 2:
                    start += step
                    continue
                X_tr = X_r.iloc[:start]
                X_te = X_r.iloc[start:start+n_val]
                sw = compute_sample_weight("balanced", y_tr)
                m = xgb.XGBClassifier(**test_params)
                m.fit(X_tr, y_tr, sample_weight=sw)
                acc = float((m.predict(X_te) == y_te).mean())
                cv_scores.append(acc)
                start += step

            if cv_scores:
                mean_cv = float(np.mean(cv_scores))
                if mean_cv > best_cv:
                    best_cv = mean_cv
                    best_params = test_params
                    best_cv_scores = cv_scores

        # Train final model on all data with best params
        sample_weight = compute_sample_weight("balanced", y_r)
        model_r = xgb.XGBClassifier(**best_params)
        model_r.fit(X_r, y_r, sample_weight=sample_weight)

        train_acc = float((model_r.predict(X_r) == y_r).mean())
        pos_ratio = float(y_r.mean())

        regime_models[regime] = {
            'clf': model_r, 'feature_names': X_cols,
            'neg_ic_feats': [], 'calibration': {'kind': 'none'},
            'regime_threshold_bias': REGIME_THRESHOLD_BIAS,
            'best_params': best_params,
            'target_col': target_col,
        }
        regime_stats[regime] = {
            'cv_accuracy': round(best_cv, 4),
            'train_accuracy': round(train_acc, 4),
            'n_samples': n,
            'pos_ratio': round(pos_ratio, 4),
            'cv_folds': len(best_cv_scores),
        }
        logger.info(f"  {regime}: Train={train_acc:.3f}, WF-CV={best_cv:.3f}, n={n}, pos={pos_ratio:.3f}, params={best_params}")

    if regime_models:
        os.makedirs("model", exist_ok=True)
        with open("model/regime_models.pkl", "wb") as f:
            pickle.dump(regime_models, f)
        # Save stats
        stats_path = "model/regime_stats.json"
        with open(stats_path, "w") as f:
            json.dump(regime_stats, f, indent=2)
        logger.info(f"Regime models saved: {list(regime_stats.keys())}")
        for r, s in regime_stats.items():
            logger.info(f"  {r}: {s}")
    return regime_stats


def main():
    """Standalone training entry point: python model/train.py"""
    import json, pickle
    from database.models import init_db
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
    db_path = str(Path(__file__).parent.parent / "poly_trader.db")
    db_url = "sqlite:///" + db_path
    print("Loading data from " + db_path)
    session = init_db(db_url)
    try:
        loaded = load_training_data(session)
        if loaded is None:
            logger.error("載入訓練資料失敗")
            return
        X, y, y_return = loaded
        print("Training data: {} samples, {} features".format(len(X), len(X.columns)))
        print("Positive ratio: {:.4f}".format(y.mean()))
        print("Training global model...")
        result = run_training(session)
        metrics_path = str(Path(__file__).parent / "last_metrics.json")
        if result and os.path.exists(metrics_path):
            with open(metrics_path) as f:
                metrics = json.load(f)
            print("  Global -> Train={}, CV={} +/- {}".format(
                metrics.get("train_accuracy", "?"),
                metrics.get("cv_accuracy", "?"),
                metrics.get("cv_std", "?")))
        print("Training regime models...")
        regime_stats = train_regime_models(session)
        rpath = str(Path(__file__).parent / "regime_models.pkl")
        if os.path.exists(rpath):
            with open(rpath, "rb") as f:
                rm = pickle.load(f)
            for r in rm:
                n = len(rm[r].get("feature_names", []))
                print("  {}: {} features saved".format(r, n))
        if regime_stats:
            for r, s in regime_stats.items():
                print("  {}: CV={} Train={} n={}".format(
                    r, s.get("cv_accuracy", "?"), s.get("train_accuracy", "?"), s.get("n_samples", "?")))
        print("Training complete.")
        return True
    finally:
        session.close()


if __name__ == "__main__":
    main()
