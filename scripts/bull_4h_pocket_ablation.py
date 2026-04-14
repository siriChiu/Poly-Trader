#!/usr/bin/env python3
"""Bull 4H collapse-pocket ablation for Poly-Trader.

Goal:
- focus on the live bull blocker instead of generic calibration tuning
- compare a small set of 4H feature-family variants against the current shrinkage baseline
- surface which 4H groups help or hurt inside bull-only and collapse-pocket cohorts

Outputs:
- data/bull_4h_pocket_ablation.json
- docs/analysis/bull_4h_pocket_ablation.md
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model import predictor as predictor_module
from model import train as train_module
from scripts import feature_group_ablation as feature_group_module

OUT_JSON = PROJECT_ROOT / "data" / "bull_4h_pocket_ablation.json"
OUT_MD = PROJECT_ROOT / "docs" / "analysis" / "bull_4h_pocket_ablation.md"
LIVE_PROBE_PATH = PROJECT_ROOT / "data" / "live_predict_probe.json"
TARGET_COL = "simulated_pyramid_win"
N_SPLITS = 5
TOP_K = 0.10
COLLAPSE_QUANTILE = 0.35
MIN_COLLAPSE_FLAGS = 2

COLLAPSE_FEATURES = [
    "feat_4h_dist_swing_low",
    "feat_4h_dist_bb_lower",
    "feat_4h_bb_pct_b",
]
TREND_4H_FEATURES = [
    "feat_4h_bias50",
    "feat_4h_bias200",
    "feat_4h_ma_order",
]
MOMENTUM_4H_FEATURES = [
    "feat_4h_rsi14",
    "feat_4h_macd_hist",
    "feat_4h_vol_ratio",
]

DEFAULT_XGB_PARAMS = {
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


def _safe_topk_win_rate(y_true: pd.Series, proba: np.ndarray, top_k: float = TOP_K) -> tuple[float | None, int]:
    if len(y_true) == 0:
        return None, 0
    n = max(1, int(math.ceil(len(y_true) * top_k)))
    order = np.argsort(proba)[-n:]
    selected = y_true.iloc[order]
    return float(selected.mean()), int(len(selected))


def _load_frame() -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    X, y, regimes = feature_group_module._load_training_frame()
    frame = X.copy()
    frame["regime_label"] = regimes.values
    return frame, y, regimes


def _derive_live_bucket_columns(frame: pd.DataFrame) -> pd.DataFrame:
    derived = frame.copy()
    gate_debugs: list[dict[str, Any]] = []
    structure_buckets: list[str | None] = []
    regime_gates: list[str | None] = []
    regime_gate_reasons: list[str | None] = []
    structure_quality_values: list[float | None] = []
    entry_quality_values: list[float | None] = []
    entry_quality_labels: list[str | None] = []

    for _, row in derived.iterrows():
        gate_debug = predictor_module._compute_live_regime_gate_debug(
            bias200_value=float(row.get("feat_4h_bias200", 0.0) or 0.0),
            regime=str(row.get("regime_label") or "unknown"),
            bb_pct_b_value=row.get("feat_4h_bb_pct_b"),
            dist_bb_lower_value=row.get("feat_4h_dist_bb_lower"),
            dist_swing_low_value=row.get("feat_4h_dist_swing_low"),
        )
        entry_quality = predictor_module._compute_live_entry_quality(
            bias50_value=float(row.get("feat_4h_bias50", 0.0) or 0.0),
            nose_value=float(row.get("feat_nose", 0.0) or 0.0),
            pulse_value=float(row.get("feat_pulse", 0.0) or 0.0),
            ear_value=float(row.get("feat_ear", 0.0) or 0.0),
            bb_pct_b_value=row.get("feat_4h_bb_pct_b"),
            dist_bb_lower_value=row.get("feat_4h_dist_bb_lower"),
            dist_swing_low_value=row.get("feat_4h_dist_swing_low"),
        )
        gate_debugs.append(gate_debug)
        structure_buckets.append(predictor_module._live_structure_bucket_from_debug(gate_debug))
        regime_gates.append(gate_debug.get("final_gate"))
        regime_gate_reasons.append(gate_debug.get("final_reason"))
        structure_quality_values.append(gate_debug.get("structure_quality"))
        entry_quality_values.append(entry_quality)
        entry_quality_labels.append(predictor_module._quality_label(entry_quality))

    derived["regime_gate"] = regime_gates
    derived["regime_gate_reason"] = regime_gate_reasons
    derived["structure_quality"] = structure_quality_values
    derived["structure_bucket"] = structure_buckets
    derived["entry_quality"] = entry_quality_values
    derived["entry_quality_label"] = entry_quality_labels
    return derived


def _collapse_thresholds(frame: pd.DataFrame, features: list[str], quantile: float = COLLAPSE_QUANTILE) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    bull_rows = frame.loc[frame["regime_label"] == "bull"]
    for feature in features:
        if feature not in bull_rows.columns:
            continue
        series = pd.to_numeric(bull_rows[feature], errors="coerce").dropna()
        if series.empty:
            thresholds[feature] = float("nan")
        else:
            thresholds[feature] = float(series.quantile(quantile))
    return thresholds


def build_bull_collapse_mask(
    frame: pd.DataFrame,
    features: list[str] = COLLAPSE_FEATURES,
    quantile: float = COLLAPSE_QUANTILE,
    min_flags: int = MIN_COLLAPSE_FLAGS,
) -> tuple[pd.Series, dict[str, float]]:
    bull_mask = frame["regime_label"].astype(str) == "bull"
    thresholds = _collapse_thresholds(frame, features, quantile=quantile)
    hit_count = pd.Series(0, index=frame.index, dtype=int)
    for feature in features:
        threshold = thresholds.get(feature)
        if feature not in frame.columns or threshold is None or not np.isfinite(threshold):
            continue
        values = pd.to_numeric(frame[feature], errors="coerce")
        hit_count = hit_count + ((values <= threshold) & bull_mask).astype(int)
    mask = bull_mask & (hit_count >= int(min_flags))
    return mask, thresholds


def build_candidate_profiles(all_columns: list[str]) -> dict[str, list[str]]:
    base_profiles = train_module._build_feature_profile_columns(all_columns)
    base = base_profiles[train_module.STRONG_BASELINE_FEATURE_PROFILE]
    collapse = [c for c in COLLAPSE_FEATURES if c in all_columns]
    trend = [c for c in TREND_4H_FEATURES if c in all_columns]
    momentum = [c for c in MOMENTUM_4H_FEATURES if c in all_columns]
    all_4h = [c for c in train_module.FOUR_H_FEATURES if c in all_columns]
    current_full = list(all_columns)
    return {
        "core_plus_macro": base,
        "core_plus_macro_plus_4h_structure_shift": sorted(set(base + collapse)),
        "core_plus_macro_plus_4h_trend": sorted(set(base + trend)),
        "core_plus_macro_plus_4h_momentum": sorted(set(base + momentum)),
        "core_plus_macro_plus_all_4h": sorted(set(base + all_4h)),
        "current_full_minus_4h_structure_shift": [c for c in current_full if c not in collapse],
        "current_full_minus_4h": [c for c in current_full if c not in all_4h],
        "current_full": current_full,
    }


def _evaluate_subset(X: pd.DataFrame, y: pd.Series, columns: list[str], n_splits: int = N_SPLITS) -> dict[str, Any] | None:
    if len(X) < 30:
        return None
    folds: list[dict[str, Any]] = []
    evaluation_mode = "timeseries_split"

    effective_splits = min(n_splits, max(2, len(X) // 40))
    if len(X) >= max(60, n_splits * 20) and effective_splits >= 2:
        tscv = TimeSeriesSplit(n_splits=effective_splits)
        for train_idx, test_idx in tscv.split(X):
            X_train = X.iloc[train_idx][columns]
            X_test = X.iloc[test_idx][columns]
            y_train = y.iloc[train_idx]
            y_test = y.iloc[test_idx]
            if len(y_train.unique()) < 2 or len(y_test.unique()) < 2:
                continue
            model = XGBClassifier(**DEFAULT_XGB_PARAMS)
            model.fit(X_train, y_train)
            proba = model.predict_proba(X_test)[:, 1]
            pred = (proba >= 0.5).astype(int)
            top10, top10_rows = _safe_topk_win_rate(y_test, proba)
            folds.append(
                {
                    "accuracy": float(accuracy_score(y_test, pred)),
                    "brier": float(brier_score_loss(y_test, proba)),
                    "top10_win_rate": top10,
                    "top10_rows": top10_rows,
                }
            )

    if not folds:
        split_at = max(int(len(X) * 0.7), 20)
        if split_at >= len(X):
            split_at = len(X) - 10
        if split_at <= 0 or split_at >= len(X):
            return None
        X_train = X.iloc[:split_at][columns]
        X_test = X.iloc[split_at:][columns]
        y_train = y.iloc[:split_at]
        y_test = y.iloc[split_at:]
        if len(y_train.unique()) < 2 or len(y_test.unique()) < 2:
            return None
        evaluation_mode = "single_holdout"
        model = XGBClassifier(**DEFAULT_XGB_PARAMS)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)
        top10, top10_rows = _safe_topk_win_rate(y_test, proba)
        folds.append(
            {
                "accuracy": float(accuracy_score(y_test, pred)),
                "brier": float(brier_score_loss(y_test, proba)),
                "top10_win_rate": top10,
                "top10_rows": top10_rows,
            }
        )

    if not folds:
        return None
    accs = [f["accuracy"] for f in folds]
    briers = [f["brier"] for f in folds]
    top10_rates = [f["top10_win_rate"] for f in folds if f["top10_win_rate"] is not None]
    return {
        "feature_count": len(columns),
        "n_splits": len(folds),
        "evaluation_mode": evaluation_mode,
        "cv_mean_accuracy": float(np.mean(accs)),
        "cv_std_accuracy": float(np.std(accs)),
        "cv_worst_accuracy": float(np.min(accs)),
        "cv_mean_brier": float(np.mean(briers)),
        "top10_win_rate_mean": float(np.mean(top10_rates)) if top10_rates else None,
    }


def rank_profile(metrics: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        float(metrics.get("cv_mean_accuracy", float("-inf"))),
        float(metrics.get("cv_worst_accuracy", float("-inf"))),
        -float(metrics.get("cv_std_accuracy", float("inf"))),
        -float(metrics.get("cv_mean_brier", float("inf"))),
    )


def _live_context() -> dict[str, Any]:
    if not LIVE_PROBE_PATH.exists():
        return {}
    payload = json.loads(LIVE_PROBE_PATH.read_text(encoding="utf-8"))
    diags = payload.get("decision_quality_scope_diagnostics") or {}
    exact = diags.get("regime_label+regime_gate+entry_quality_label") or {}
    narrow = diags.get("regime_label+entry_quality_label") or {}
    broad = diags.get("regime_gate+entry_quality_label") or {}
    pathology_consensus = diags.get("pathology_consensus") or {}
    snapshot = (((broad.get("spillover_vs_exact_live_lane") or {}).get("worst_extra_regime_gate_feature_snapshot")) or {})
    exact_bucket_counts = exact.get("recent500_structure_bucket_counts") or {}
    current_bucket = exact.get("current_live_structure_bucket") or broad.get("current_live_structure_bucket")
    supported_neighbor_buckets = [
        bucket for bucket, count in exact_bucket_counts.items()
        if bucket != current_bucket and int(count or 0) > 0
    ]
    return {
        "feature_timestamp": payload.get("feature_timestamp"),
        "regime_label": payload.get("regime_label"),
        "regime_gate": payload.get("regime_gate"),
        "entry_quality_label": payload.get("entry_quality_label"),
        "execution_guardrail_reason": payload.get("execution_guardrail_reason"),
        "decision_quality_calibration_scope": payload.get("decision_quality_calibration_scope"),
        "decision_quality_scope_guardrail_applied": payload.get("decision_quality_scope_guardrail_applied"),
        "decision_quality_scope_guardrail_reason": payload.get("decision_quality_scope_guardrail_reason"),
        "decision_quality_narrowed_pathology_scope": payload.get("decision_quality_narrowed_pathology_scope"),
        "decision_quality_narrowed_pathology_reason": payload.get("decision_quality_narrowed_pathology_reason"),
        "decision_quality_label": payload.get("decision_quality_label"),
        "current_live_structure_bucket": current_bucket,
        "current_live_structure_bucket_rows": exact.get("current_live_structure_bucket_rows"),
        "exact_scope_rows": exact.get("rows"),
        "exact_scope_metrics": {
            "rows": exact.get("rows"),
            "win_rate": exact.get("win_rate"),
            "avg_pnl": exact.get("avg_pnl"),
            "avg_quality": exact.get("avg_quality"),
            "avg_drawdown_penalty": exact.get("avg_drawdown_penalty"),
            "avg_time_underwater": exact.get("avg_time_underwater"),
        },
        "exact_recent_structure_bucket_counts": exact_bucket_counts,
        "exact_dominant_structure_bucket": exact.get("recent500_dominant_structure_bucket"),
        "exact_current_live_structure_bucket_metrics": exact.get("current_live_structure_bucket_metrics"),
        "narrow_recent_structure_bucket_counts": narrow.get("recent500_structure_bucket_counts") or {},
        "narrow_scope_rows": narrow.get("rows"),
        "narrow_current_live_structure_bucket_rows": narrow.get("current_live_structure_bucket_rows"),
        "narrow_current_live_structure_bucket_metrics": narrow.get("current_live_structure_bucket_metrics"),
        "broad_scope_rows": broad.get("rows"),
        "broad_current_live_structure_bucket_rows": broad.get("current_live_structure_bucket_rows"),
        "broad_current_live_structure_bucket_metrics": broad.get("current_live_structure_bucket_metrics"),
        "broad_recent500_regime_counts": broad.get("recent500_regime_counts") or {},
        "broad_recent500_dominant_regime": broad.get("recent500_dominant_regime"),
        "broad_recent_pathology": broad.get("recent_pathology") or {},
        "supported_neighbor_buckets": supported_neighbor_buckets,
        "collapse_feature_snapshot": snapshot,
        "pathology_worst_scope": (pathology_consensus.get("worst_pathology_scope") or {}).get("scope"),
        "pathology_shared_shift_features": [
            item.get("feature")
            for item in (pathology_consensus.get("shared_top_shift_features") or [])
            if item.get("feature")
        ],
    }


def _cohort_overview(name: str, cohort: dict[str, Any]) -> str:
    return (
        f"- {name} rows: **{cohort['rows']}** / win_rate **{cohort['base_win_rate']:.4f}**"
        f" / recommended **`{cohort['recommended_profile']}`**"
    )


def _cohort_detail(cohort: dict[str, Any] | None) -> dict[str, Any]:
    cohort = cohort or {}
    recommended_profile = cohort.get("recommended_profile")
    profiles = cohort.get("profiles") or {}
    return {
        "rows": int(cohort.get("rows") or 0),
        "base_win_rate": cohort.get("base_win_rate"),
        "recommended_profile": recommended_profile,
        "recommended_metrics": profiles.get(recommended_profile) or {},
    }


def _metric_delta(lhs: Any, rhs: Any) -> float | None:
    try:
        if lhs is None or rhs is None:
            return None
        return round(float(lhs) - float(rhs), 4)
    except (TypeError, ValueError):
        return None


def _support_pathology_summary(payload: dict[str, Any]) -> dict[str, Any]:
    live_context = payload.get("live_context") or {}
    cohorts = payload.get("cohorts") or {}
    min_support_rows = int(train_module.MIN_SUPPORT_AWARE_BUCKET_ROWS)
    current_bucket = live_context.get("current_live_structure_bucket")
    current_bucket_rows = int(live_context.get("current_live_structure_bucket_rows") or 0)
    exact_lane_rows = int((cohorts.get("bull_exact_live_lane_proxy") or {}).get("rows") or 0)
    exact_bucket_proxy_rows = int((cohorts.get("bull_live_exact_lane_bucket_proxy") or {}).get("rows") or 0)
    supported_neighbor_rows = int((cohorts.get("bull_supported_neighbor_buckets_proxy") or {}).get("rows") or 0)
    supported_neighbor_buckets = list(live_context.get("supported_neighbor_buckets") or [])
    bucket_counts = live_context.get("exact_recent_structure_bucket_counts") or {}
    dominant_neighbor_bucket = None
    dominant_neighbor_rows = 0
    for bucket, count in bucket_counts.items():
        count_int = int(count or 0)
        if bucket == current_bucket or count_int <= dominant_neighbor_rows:
            continue
        dominant_neighbor_bucket = bucket
        dominant_neighbor_rows = count_int

    if current_bucket_rows >= min_support_rows:
        blocker_state = "exact_live_bucket_supported"
        preferred_support_cohort = "exact_live_bucket"
        recommended_action = "可回到 exact live bucket 直接治理與驗證。"
    elif exact_bucket_proxy_rows >= min_support_rows:
        blocker_state = "exact_live_bucket_proxy_ready_but_exact_missing"
        preferred_support_cohort = "bull_live_exact_lane_bucket_proxy"
        recommended_action = "維持部署 blocker，優先補 exact bucket 真樣本，proxy 只可作治理參考。"
    elif exact_lane_rows >= min_support_rows:
        blocker_state = "exact_lane_proxy_fallback_only"
        preferred_support_cohort = "bull_exact_live_lane_proxy"
        recommended_action = "維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。"
    elif supported_neighbor_rows >= min_support_rows:
        blocker_state = "supported_neighbor_only"
        preferred_support_cohort = "bull_supported_neighbor_buckets_proxy"
        recommended_action = "僅可用鄰近 bucket 做治理參考；不得視為 exact bucket 已獲支持。"
    else:
        blocker_state = "insufficient_support_everywhere"
        preferred_support_cohort = None
        recommended_action = "support 全面不足；下一輪需優先擴充樣本或縮小治理範圍。"

    collapse_snapshot = live_context.get("collapse_feature_snapshot") or {}
    shared_shift_features = list(live_context.get("pathology_shared_shift_features") or [])
    live_regime = live_context.get("regime_label")
    broad_bucket_rows = int(live_context.get("broad_current_live_structure_bucket_rows") or 0)
    broad_dominant_regime = live_context.get("broad_recent500_dominant_regime") or {}
    broad_dominant_regime_label = broad_dominant_regime.get("regime")
    broad_dominant_regime_share = float(broad_dominant_regime.get("share") or 0.0)
    broad_bucket_metrics = live_context.get("broad_current_live_structure_bucket_metrics") or {}
    exact_scope_metrics = live_context.get("exact_scope_metrics") or {}
    exact_dominant_structure_bucket = live_context.get("exact_dominant_structure_bucket") or {}
    exact_bucket_proxy = _cohort_detail(cohorts.get("bull_live_exact_lane_bucket_proxy"))
    exact_lane_proxy = _cohort_detail(cohorts.get("bull_exact_live_lane_proxy"))
    broader_same_bucket_summary = {
        "bucket": current_bucket,
        "rows": broad_bucket_rows,
        "dominant_regime": broad_dominant_regime_label,
        "dominant_regime_share": broad_dominant_regime_share,
        "win_rate": broad_bucket_metrics.get("win_rate"),
        "avg_pnl": broad_bucket_metrics.get("avg_pnl"),
        "avg_quality": broad_bucket_metrics.get("avg_quality"),
        "avg_drawdown_penalty": broad_bucket_metrics.get("avg_drawdown_penalty"),
        "avg_time_underwater": broad_bucket_metrics.get("avg_time_underwater"),
    }
    exact_scope_bucket = (
        current_bucket if current_bucket_rows > 0 else (exact_dominant_structure_bucket or {}).get("structure_bucket")
    )
    exact_live_lane_summary = {
        "bucket": exact_scope_bucket,
        "rows": int(exact_scope_metrics.get("rows") or 0),
        "current_live_bucket_rows": current_bucket_rows,
        "win_rate": exact_scope_metrics.get("win_rate"),
        "avg_pnl": exact_scope_metrics.get("avg_pnl"),
        "avg_quality": exact_scope_metrics.get("avg_quality"),
        "avg_drawdown_penalty": exact_scope_metrics.get("avg_drawdown_penalty"),
        "avg_time_underwater": exact_scope_metrics.get("avg_time_underwater"),
    }
    bucket_evidence_comparison = {
        "current_live_bucket": current_bucket,
        "exact_live_lane": exact_live_lane_summary,
        "exact_bucket_proxy": {
            "bucket": current_bucket,
            **exact_bucket_proxy,
        },
        "exact_lane_proxy": {
            "bucket": exact_scope_bucket,
            **exact_lane_proxy,
        },
        "broader_same_bucket": broader_same_bucket_summary,
        "proxy_vs_broader_same_bucket": {
            "win_rate_delta": _metric_delta(
                exact_bucket_proxy.get("base_win_rate"),
                broader_same_bucket_summary.get("win_rate"),
            ),
            "proxy_cv_mean_accuracy": (exact_bucket_proxy.get("recommended_metrics") or {}).get("cv_mean_accuracy"),
            "row_delta": int(exact_bucket_proxy.get("rows") or 0) - broad_bucket_rows,
        },
        "exact_live_lane_vs_broader_same_bucket": {
            "win_rate_delta": _metric_delta(
                exact_live_lane_summary.get("win_rate"),
                broader_same_bucket_summary.get("win_rate"),
            ),
            "quality_delta": _metric_delta(
                exact_live_lane_summary.get("avg_quality"),
                broader_same_bucket_summary.get("avg_quality"),
            ),
            "row_delta": int(exact_live_lane_summary.get("rows") or 0) - broad_bucket_rows,
        },
    }
    exact_bucket_root_cause = "insufficient_scope_data"
    if current_bucket_rows >= min_support_rows:
        exact_bucket_root_cause = "exact_bucket_supported"
    elif current_bucket_rows > 0:
        exact_bucket_root_cause = "exact_bucket_present_but_below_minimum"
    elif broad_bucket_rows > 0 and broad_dominant_regime_label and broad_dominant_regime_label != live_regime:
        exact_bucket_root_cause = "cross_regime_spillover_dominates_q65"
    elif dominant_neighbor_bucket and dominant_neighbor_rows > 0:
        exact_bucket_root_cause = "same_lane_shifted_to_neighbor_bucket"
    elif exact_lane_rows > 0:
        exact_bucket_root_cause = "same_lane_exists_but_q65_missing"
    broad_recent_pathology = live_context.get("broad_recent_pathology") or {}
    broader_bucket_pathology = ((broad_recent_pathology.get("summary") or {}).get("reference_window_comparison") or {}).get("top_mean_shift_features") or []
    comparison_takeaway = "support_gap_unresolved"
    proxy_win_delta = (bucket_evidence_comparison.get("proxy_vs_broader_same_bucket") or {}).get("win_rate_delta")
    exact_win_delta = (bucket_evidence_comparison.get("exact_live_lane_vs_broader_same_bucket") or {}).get("win_rate_delta")
    if current_bucket_rows >= min_support_rows:
        comparison_takeaway = "exact_bucket_supported"
    elif broad_dominant_regime_label and broad_dominant_regime_label != live_regime and proxy_win_delta is not None and proxy_win_delta > 0:
        comparison_takeaway = "prefer_same_bucket_proxy_over_cross_regime_spillover"
    elif exact_scope_bucket and exact_scope_bucket != current_bucket and exact_win_delta is not None and exact_win_delta > 0:
        comparison_takeaway = "neighbor_bucket_outperforms_broader_same_bucket"

    return {
        "blocker_state": blocker_state,
        "preferred_support_cohort": preferred_support_cohort,
        "minimum_support_rows": min_support_rows,
        "current_live_structure_bucket": current_bucket,
        "current_live_structure_bucket_rows": current_bucket_rows,
        "current_live_structure_bucket_gap_to_minimum": max(min_support_rows - current_bucket_rows, 0),
        "exact_live_lane_proxy_rows": exact_lane_rows,
        "exact_live_lane_proxy_gap_to_minimum": max(min_support_rows - exact_lane_rows, 0),
        "exact_live_bucket_proxy_rows": exact_bucket_proxy_rows,
        "exact_live_bucket_proxy_gap_to_minimum": max(min_support_rows - exact_bucket_proxy_rows, 0),
        "supported_neighbor_bucket_rows": supported_neighbor_rows,
        "supported_neighbor_bucket_gap_to_minimum": max(min_support_rows - supported_neighbor_rows, 0),
        "supported_neighbor_buckets": supported_neighbor_buckets,
        "dominant_neighbor_bucket": dominant_neighbor_bucket,
        "dominant_neighbor_bucket_rows": dominant_neighbor_rows,
        "bucket_gap_vs_dominant_neighbor": max(dominant_neighbor_rows - current_bucket_rows, 0),
        "exact_scope_rows": int(live_context.get("exact_scope_rows") or 0),
        "broad_scope_rows": int(live_context.get("broad_scope_rows") or 0),
        "broad_current_live_structure_bucket_rows": broad_bucket_rows,
        "broad_current_live_structure_bucket_metrics": broad_bucket_metrics,
        "broad_dominant_regime": broad_dominant_regime_label,
        "broad_dominant_regime_share": broad_dominant_regime_share,
        "exact_bucket_root_cause": exact_bucket_root_cause,
        "root_cause_interpretation": (
            "q65 在較寬 ALLOW+D scope 內存在，但主要由其他 regime 支配；目前 bull exact lane 只剩 q85 鄰近 bucket。"
            if exact_bucket_root_cause == "cross_regime_spillover_dominates_q65"
            else "bull exact lane 已出現當前 bucket 樣本，但距離 minimum support 仍有缺口；需持續累積 exact rows，不能當成已解 blocker。"
            if exact_bucket_root_cause == "exact_bucket_present_but_below_minimum"
            else "bull exact lane 仍有同 lane 樣本，但當前結構已偏到鄰近 bucket，需先查 q65↔q85 分桶與 same-lane pathology。"
            if exact_bucket_root_cause == "same_lane_shifted_to_neighbor_bucket"
            else "exact bucket 已獲支持，可直接驗證 exact lane。"
            if exact_bucket_root_cause == "exact_bucket_supported"
            else "目前支持資訊不足，需補更多 same-lane / broader-scope 證據。"
        ),
        "bucket_evidence_comparison": bucket_evidence_comparison,
        "bucket_comparison_takeaway": comparison_takeaway,
        "broader_bucket_pathology_shift_features": [
            item.get("feature") for item in broader_bucket_pathology if item.get("feature")
        ],
        "decision_quality_calibration_scope": live_context.get("decision_quality_calibration_scope"),
        "decision_quality_label": live_context.get("decision_quality_label"),
        "scope_guardrail_applied": bool(live_context.get("decision_quality_scope_guardrail_applied")),
        "scope_guardrail_reason": live_context.get("decision_quality_scope_guardrail_reason"),
        "narrowed_pathology_scope": live_context.get("decision_quality_narrowed_pathology_scope"),
        "narrowed_pathology_reason": live_context.get("decision_quality_narrowed_pathology_reason"),
        "pathology_worst_scope": live_context.get("pathology_worst_scope"),
        "pathology_shared_shift_features": shared_shift_features,
        "collapse_feature_snapshot": collapse_snapshot,
        "recommended_action": recommended_action,
    }


def _write_markdown(payload: dict[str, Any]) -> None:
    bull = payload["cohorts"]["bull_all"]["profiles"]
    collapse = payload["cohorts"]["bull_collapse_q35"]["profiles"]
    live_bucket = payload["cohorts"]["bull_live_exact_lane_bucket_proxy"]["profiles"]
    supported_neighbors = payload["cohorts"]["bull_supported_neighbor_buckets_proxy"]["profiles"]
    support_summary = payload.get("support_pathology_summary") or {}
    bull_rank = sorted(bull.items(), key=lambda item: rank_profile(item[1]), reverse=True)
    collapse_rank = sorted(collapse.items(), key=lambda item: rank_profile(item[1]), reverse=True)
    live_bucket_rank = sorted(live_bucket.items(), key=lambda item: rank_profile(item[1]), reverse=True) if live_bucket else []
    supported_neighbor_rank = sorted(supported_neighbors.items(), key=lambda item: rank_profile(item[1]), reverse=True) if supported_neighbors else []
    lines = [
        "# Bull 4H Collapse Pocket Ablation",
        "",
        f"- generated_at: **{payload['generated_at']} UTC**",
        f"- target: `{payload['target_col']}`",
        f"- collapse quantile: **q{int(payload['collapse_quantile'] * 100):02d}**",
        f"- min collapse flags: **{payload['min_collapse_flags']} / {len(payload['collapse_features'])}**",
        f"- live context: **{payload['live_context'].get('regime_label')} / {payload['live_context'].get('regime_gate')} / {payload['live_context'].get('entry_quality_label')}**",
        f"- live structure bucket: `{payload['live_context'].get('current_live_structure_bucket')}`",
        "",
        "## Cohorts",
        "",
        _cohort_overview("bull_all", payload['cohorts']['bull_all']),
        _cohort_overview("bull_collapse_q35", payload['cohorts']['bull_collapse_q35']),
        _cohort_overview("bull_exact_live_lane_proxy", payload['cohorts']['bull_exact_live_lane_proxy']),
        _cohort_overview("bull_live_exact_lane_bucket_proxy", payload['cohorts']['bull_live_exact_lane_bucket_proxy']),
        _cohort_overview("bull_supported_neighbor_buckets_proxy", payload['cohorts']['bull_supported_neighbor_buckets_proxy']),
        "",
        "## Bull-all ranking",
        "",
        "| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, metrics in bull_rank:
        top10_text = "-" if metrics["top10_win_rate_mean"] is None else f"{metrics['top10_win_rate_mean']:.4f}"
        lines.append(
            f"| {name} | {metrics['feature_count']} | {metrics['cv_mean_accuracy']:.4f} | {metrics['cv_std_accuracy']:.4f} | {metrics['cv_worst_accuracy']:.4f} | {metrics['cv_mean_brier']:.4f} | {top10_text} |"
        )
    lines.extend([
        "",
        "## Bull collapse-pocket ranking",
        "",
        "| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for name, metrics in collapse_rank:
        top10_text = "-" if metrics["top10_win_rate_mean"] is None else f"{metrics['top10_win_rate_mean']:.4f}"
        lines.append(
            f"| {name} | {metrics['feature_count']} | {metrics['cv_mean_accuracy']:.4f} | {metrics['cv_std_accuracy']:.4f} | {metrics['cv_worst_accuracy']:.4f} | {metrics['cv_mean_brier']:.4f} | {top10_text} |"
        )
    lines.extend([
        "",
        "## Live-bucket proxy ranking",
        "",
        "| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for name, metrics in live_bucket_rank:
        top10_text = "-" if metrics["top10_win_rate_mean"] is None else f"{metrics['top10_win_rate_mean']:.4f}"
        lines.append(
            f"| {name} | {metrics['feature_count']} | {metrics['cv_mean_accuracy']:.4f} | {metrics['cv_std_accuracy']:.4f} | {metrics['cv_worst_accuracy']:.4f} | {metrics['cv_mean_brier']:.4f} | {top10_text} |"
        )
    lines.extend([
        "",
        "## Supported-neighbor bucket proxy ranking",
        "",
        "| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for name, metrics in supported_neighbor_rank:
        top10_text = "-" if metrics["top10_win_rate_mean"] is None else f"{metrics['top10_win_rate_mean']:.4f}"
        lines.append(
            f"| {name} | {metrics['feature_count']} | {metrics['cv_mean_accuracy']:.4f} | {metrics['cv_std_accuracy']:.4f} | {metrics['cv_worst_accuracy']:.4f} | {metrics['cv_mean_brier']:.4f} | {top10_text} |"
        )
    lines.extend([
        "",
        "## Support / pathology summary",
        "",
        f"- blocker_state: **{support_summary.get('blocker_state')}**",
        f"- preferred_support_cohort: **{support_summary.get('preferred_support_cohort')}**",
        f"- current bucket gap to minimum: **{support_summary.get('current_live_structure_bucket_gap_to_minimum')}**",
        f"- exact-bucket proxy gap to minimum: **{support_summary.get('exact_live_bucket_proxy_gap_to_minimum')}**",
        f"- exact-lane proxy gap to minimum: **{support_summary.get('exact_live_lane_proxy_gap_to_minimum')}**",
        f"- dominant neighbor bucket: `{support_summary.get('dominant_neighbor_bucket')}` rows={support_summary.get('dominant_neighbor_bucket_rows')}",
        f"- bucket gap vs dominant neighbor: **{support_summary.get('bucket_gap_vs_dominant_neighbor')}**",
        f"- exact bucket root cause: **{support_summary.get('exact_bucket_root_cause')}**",
        f"- broader q65 rows / dominant regime: **{support_summary.get('broad_current_live_structure_bucket_rows')} / {support_summary.get('broad_dominant_regime')} ({support_summary.get('broad_dominant_regime_share'):.4f})**",
        f"- root cause interpretation: {support_summary.get('root_cause_interpretation')}",
        f"- bucket comparison takeaway: **{support_summary.get('bucket_comparison_takeaway')}**",
        f"- decision-quality scope / label: **{support_summary.get('decision_quality_calibration_scope')} / {support_summary.get('decision_quality_label')}**",
        f"- narrowed pathology scope: **{support_summary.get('narrowed_pathology_scope')}**",
        f"- worst pathology scope: **{support_summary.get('pathology_worst_scope')}**",
        f"- shared pathology shift features: {json.dumps(support_summary.get('pathology_shared_shift_features') or [], ensure_ascii=False)}",
        f"- broader-bucket pathology shifts: {json.dumps(support_summary.get('broader_bucket_pathology_shift_features') or [], ensure_ascii=False)}",
        f"- recommended_action: {support_summary.get('recommended_action')}",
        "",
        "## Bucket evidence comparison",
        "",
        "| cohort | bucket | rows | win_rate | quality / cv | note |",
        "|---|---|---:|---:|---:|---|",
        f"| exact live lane | {((support_summary.get('bucket_evidence_comparison') or {}).get('exact_live_lane') or {}).get('bucket')} | {((support_summary.get('bucket_evidence_comparison') or {}).get('exact_live_lane') or {}).get('rows')} | {((support_summary.get('bucket_evidence_comparison') or {}).get('exact_live_lane') or {}).get('win_rate')} | {((support_summary.get('bucket_evidence_comparison') or {}).get('exact_live_lane') or {}).get('avg_quality')} | current bucket rows={((support_summary.get('bucket_evidence_comparison') or {}).get('exact_live_lane') or {}).get('current_live_bucket_rows')} |",
        f"| exact bucket proxy | {((support_summary.get('bucket_evidence_comparison') or {}).get('exact_bucket_proxy') or {}).get('bucket')} | {((support_summary.get('bucket_evidence_comparison') or {}).get('exact_bucket_proxy') or {}).get('rows')} | {((support_summary.get('bucket_evidence_comparison') or {}).get('exact_bucket_proxy') or {}).get('base_win_rate')} | {(((support_summary.get('bucket_evidence_comparison') or {}).get('exact_bucket_proxy') or {}).get('recommended_metrics') or {}).get('cv_mean_accuracy')} | proxy-vs-broader win Δ={(((support_summary.get('bucket_evidence_comparison') or {}).get('proxy_vs_broader_same_bucket') or {}).get('win_rate_delta'))} |",
        f"| broader same bucket | {((support_summary.get('bucket_evidence_comparison') or {}).get('broader_same_bucket') or {}).get('bucket')} | {((support_summary.get('bucket_evidence_comparison') or {}).get('broader_same_bucket') or {}).get('rows')} | {((support_summary.get('bucket_evidence_comparison') or {}).get('broader_same_bucket') or {}).get('win_rate')} | {((support_summary.get('bucket_evidence_comparison') or {}).get('broader_same_bucket') or {}).get('avg_quality')} | dominant_regime={((support_summary.get('bucket_evidence_comparison') or {}).get('broader_same_bucket') or {}).get('dominant_regime')} |",
        "",
        "## Notes",
        "",
        f"- collapse features under inspection: {', '.join(payload['collapse_features'])}",
        f"- thresholds (bull q35): {json.dumps(payload['collapse_thresholds'], ensure_ascii=False)}",
        f"- exact live structure bucket: `{payload['live_context'].get('current_live_structure_bucket')}` rows={payload['live_context'].get('current_live_structure_bucket_rows')}",
        f"- supported neighbor buckets from exact scope: {json.dumps(payload['live_context'].get('supported_neighbor_buckets') or [], ensure_ascii=False)}",
        f"- best bull-all profile: **{payload['cohorts']['bull_all']['recommended_profile']}**",
        f"- best bull-collapse profile: **{payload['cohorts']['bull_collapse_q35']['recommended_profile']}**",
        f"- best live-bucket proxy profile: **{payload['cohorts']['bull_live_exact_lane_bucket_proxy']['recommended_profile']}**",
        "- If live-bucket proxy stays tiny and unstable while supported-neighbor buckets remain healthier, the next fix should become a support-aware deployment blocker / fallback policy rather than a broader feature expansion.",
    ])
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    frame, y, _ = _load_frame()
    frame = _derive_live_bucket_columns(frame)
    all_columns = [
        c for c in frame.columns
        if c not in {"regime_label", "regime_gate", "regime_gate_reason", "structure_quality", "structure_bucket", "entry_quality", "entry_quality_label"}
    ]
    profiles = build_candidate_profiles(all_columns)
    live_context = _live_context()
    bull_mask = frame["regime_label"] == "bull"
    collapse_mask, thresholds = build_bull_collapse_mask(frame)
    exact_live_lane_mask = (
        bull_mask
        & (frame["regime_gate"] == live_context.get("regime_gate"))
        & (frame["entry_quality_label"] == live_context.get("entry_quality_label"))
    )
    current_bucket = live_context.get("current_live_structure_bucket")
    live_bucket_mask = exact_live_lane_mask & (frame["structure_bucket"] == current_bucket)
    supported_neighbor_buckets = set(live_context.get("supported_neighbor_buckets") or [])
    supported_neighbor_mask = exact_live_lane_mask & frame["structure_bucket"].isin(supported_neighbor_buckets)

    def _evaluate_cohort(mask: pd.Series) -> dict[str, Any]:
        cohort_X = frame.loc[mask, all_columns].reset_index(drop=True)
        cohort_y = y.loc[mask].reset_index(drop=True)
        results = {
            name: metrics
            for name, columns in profiles.items()
            if (metrics := _evaluate_subset(cohort_X, cohort_y, columns)) is not None
        }
        ranked = sorted(results.items(), key=lambda item: rank_profile(item[1]), reverse=True)
        return {
            "rows": int(mask.sum()),
            "base_win_rate": float(cohort_y.mean()) if len(cohort_y) else 0.0,
            "recommended_profile": ranked[0][0] if ranked else None,
            "profiles": results,
        }

    payload = {
        "generated_at": pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M:%S"),
        "target_col": TARGET_COL,
        "collapse_features": COLLAPSE_FEATURES,
        "collapse_quantile": COLLAPSE_QUANTILE,
        "min_collapse_flags": MIN_COLLAPSE_FLAGS,
        "collapse_thresholds": {k: None if not np.isfinite(v) else round(v, 4) for k, v in thresholds.items()},
        "live_context": live_context,
        "cohorts": {
            "bull_all": _evaluate_cohort(bull_mask),
            "bull_collapse_q35": _evaluate_cohort(collapse_mask),
            "bull_exact_live_lane_proxy": _evaluate_cohort(exact_live_lane_mask),
            "bull_live_exact_lane_bucket_proxy": _evaluate_cohort(live_bucket_mask),
            "bull_supported_neighbor_buckets_proxy": _evaluate_cohort(supported_neighbor_mask),
        },
    }
    payload["support_pathology_summary"] = _support_pathology_summary(payload)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_markdown(payload)
    print(json.dumps({
        "json": str(OUT_JSON),
        "markdown": str(OUT_MD),
        "bull_recommended_profile": payload["cohorts"]["bull_all"]["recommended_profile"],
        "bull_collapse_recommended_profile": payload["cohorts"]["bull_collapse_q35"]["recommended_profile"],
        "bull_exact_live_lane_proxy_rows": payload["cohorts"]["bull_exact_live_lane_proxy"]["rows"],
        "bull_live_exact_lane_bucket_proxy_rows": payload["cohorts"]["bull_live_exact_lane_bucket_proxy"]["rows"],
        "bull_supported_neighbor_buckets_proxy_rows": payload["cohorts"]["bull_supported_neighbor_buckets_proxy"]["rows"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
