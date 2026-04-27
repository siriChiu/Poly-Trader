#!/usr/bin/env python3
"""Feature-group ablation report for Poly-Trader canonical target.

Goal: compare accuracy/stability across feature families without adding new UI knobs.
Outputs:
- data/feature_group_ablation.json
- docs/analysis/feature_group_ablation.md
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
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

from database.models import FeaturesNormalized, Labels, init_db
from model import train as train_module

DB_URL = f"sqlite:///{PROJECT_ROOT / 'poly_trader.db'}"
OUT_JSON = PROJECT_ROOT / "data" / "feature_group_ablation.json"
OUT_MD = PROJECT_ROOT / "docs" / "analysis" / "feature_group_ablation.md"
TARGET_COL = "simulated_pyramid_win"
HORIZON_MINUTES = 1440
RECENT_ROWS = 5000
N_SPLITS = 5
TOP_K = 0.10
BOUNDED_RECENT_ROWS = 1000
BOUNDED_N_SPLITS = 2
BOUNDED_N_ESTIMATORS = 40
BOUNDED_PROFILE_NAMES = [
    "core_only",
    "core_plus_macro",
    "core_macro_plus_stable_4h",
    "core_plus_macro_plus_all_4h",
    "current_full_no_bull_collapse_4h",
    "current_full",
]

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
CROSS_FEATURES = list(train_module.CROSS_FEATURES)
BULL_COLLAPSE_4H_FEATURES = [
    "feat_4h_bb_pct_b",
    "feat_4h_dist_bb_lower",
    "feat_4h_dist_swing_low",
]
STABLE_4H_FEATURES = [f for f in FOUR_H_FEATURES if f not in BULL_COLLAPSE_4H_FEATURES]


@dataclass
class FoldMetrics:
    accuracy: float
    brier: float
    top10_win_rate: float | None
    top10_rows: int
    bear_top10_win_rate: float | None
    bear_top10_rows: int
    bull_top10_win_rate: float | None
    bull_top10_rows: int


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


def _feature_row(r: Any) -> dict[str, Any]:
    return train_module._feature_row(r)


def _load_training_frame(recent_rows: int = RECENT_ROWS) -> tuple[pd.DataFrame, pd.Series, pd.Series, dict[str, Any]]:
    session = init_db(DB_URL)
    try:
        feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
        label_rows = (
            session.query(Labels)
            .filter(
                getattr(Labels, TARGET_COL).isnot(None),
                Labels.future_return_pct.isnot(None),
                Labels.horizon_minutes == HORIZON_MINUTES,
            )
            .order_by(Labels.timestamp)
            .all()
        )
    finally:
        session.close()

    feat_df = pd.DataFrame([_feature_row(r) for r in feat_rows])
    feat_df = train_module._align_sparse_4h_features(feat_df)
    label_df = pd.DataFrame([
        {
            "timestamp": r.timestamp,
            TARGET_COL: int(getattr(r, TARGET_COL)),
            "future_return_pct": float(r.future_return_pct),
            "regime_label": r.regime_label if r.regime_label else "neutral",
        }
        for r in label_rows
    ])

    feat_df["timestamp"] = pd.to_datetime(feat_df["timestamp"])
    label_df["timestamp"] = pd.to_datetime(label_df["timestamp"])

    merged = pd.merge_asof(
        feat_df.sort_values("timestamp"),
        label_df.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("10min"),
    )
    merged = merged.dropna(subset=[TARGET_COL]).copy()

    for col in train_module.BASE_FEATURE_COLS:
        for lag in train_module.LAG_STEPS:
            merged[f"{col}_lag{lag}"] = merged[col].shift(lag)

    base_and_lags = train_module.FEATURE_COLS + [
        f"{col}_lag{lag}"
        for col in train_module.BASE_FEATURE_COLS
        for lag in train_module.LAG_STEPS
    ]
    for col in base_and_lags:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    fill4h_cols = [c for c in train_module.FEATURE_COLS if c.startswith("feat_4h_")]
    for col in fill4h_cols:
        median_val = merged[col].median()
        merged[col] = merged[col].fillna(0.0 if pd.isna(median_val) else float(median_val))
    for col in base_and_lags:
        if col not in fill4h_cols:
            merged[col] = merged[col].fillna(0.0)

    merged = train_module._append_cross_features(merged)

    feature_columns = list(base_and_lags) + CROSS_FEATURES
    merged = merged.dropna(subset=[TARGET_COL]).copy()
    effective_recent_rows = max(1, int(recent_rows or RECENT_ROWS))
    merged = merged.iloc[-effective_recent_rows:].reset_index(drop=True)

    latest_label_timestamp = None
    if not label_df.empty:
        latest_label_ts = label_df["timestamp"].max()
        if pd.notna(latest_label_ts):
            latest_label_timestamp = latest_label_ts.isoformat()

    source_meta = {
        "label_rows": int(len(label_df)),
        "latest_label_timestamp": latest_label_timestamp,
        "horizon_minutes": HORIZON_MINUTES,
        "target_col": TARGET_COL,
    }

    X = merged[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y = merged[TARGET_COL].astype(int)
    regimes = merged["regime_label"].fillna("neutral").astype(str)
    return X, y, regimes, source_meta


def _safe_win_rate(y_true: pd.Series, proba: np.ndarray, top_k: float = TOP_K) -> tuple[float | None, int]:
    if len(y_true) == 0:
        return None, 0
    n = max(1, int(math.ceil(len(y_true) * top_k)))
    order = np.argsort(proba)[-n:]
    selected = y_true.iloc[order]
    return float(selected.mean()), int(len(selected))


def _evaluate_subset(
    X: pd.DataFrame,
    y: pd.Series,
    regimes: pd.Series,
    columns: list[str],
    *,
    n_splits: int = N_SPLITS,
    xgb_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tscv = TimeSeriesSplit(n_splits=n_splits)
    folds: list[FoldMetrics] = []
    params = dict(xgb_params or DEFAULT_XGB_PARAMS)

    for train_idx, test_idx in tscv.split(X):
        X_train = X.iloc[train_idx][columns]
        X_test = X.iloc[test_idx][columns]
        y_train = y.iloc[train_idx]
        y_test = y.iloc[test_idx]
        regime_test = regimes.iloc[test_idx]

        model = XGBClassifier(**params)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)

        top10, top10_rows = _safe_win_rate(y_test, proba)
        bear_mask = regime_test == "bear"
        bull_mask = regime_test == "bull"
        bear_top10, bear_top10_rows = _safe_win_rate(y_test[bear_mask], proba[bear_mask.values])
        bull_top10, bull_top10_rows = _safe_win_rate(y_test[bull_mask], proba[bull_mask.values])

        folds.append(
            FoldMetrics(
                accuracy=float(accuracy_score(y_test, pred)),
                brier=float(brier_score_loss(y_test, proba)),
                top10_win_rate=top10,
                top10_rows=top10_rows,
                bear_top10_win_rate=bear_top10,
                bear_top10_rows=bear_top10_rows,
                bull_top10_win_rate=bull_top10,
                bull_top10_rows=bull_top10_rows,
            )
        )

    accs = [f.accuracy for f in folds]
    briers = [f.brier for f in folds]
    top10_rates = [f.top10_win_rate for f in folds if f.top10_win_rate is not None]
    bear_top10_rates = [f.bear_top10_win_rate for f in folds if f.bear_top10_win_rate is not None]
    bull_top10_rates = [f.bull_top10_win_rate for f in folds if f.bull_top10_win_rate is not None]

    return {
        "feature_count": len(columns),
        "cv_mean_accuracy": float(np.mean(accs)),
        "cv_std_accuracy": float(np.std(accs)),
        "cv_worst_accuracy": float(np.min(accs)),
        "cv_mean_brier": float(np.mean(briers)),
        "top10_win_rate_mean": float(np.mean(top10_rates)) if top10_rates else None,
        "bear_top10_win_rate_mean": float(np.mean(bear_top10_rates)) if bear_top10_rates else None,
        "bull_top10_win_rate_mean": float(np.mean(bull_top10_rates)) if bull_top10_rates else None,
        "folds": [
            {
                "accuracy": round(f.accuracy, 4),
                "brier": round(f.brier, 4),
                "top10_win_rate": None if f.top10_win_rate is None else round(f.top10_win_rate, 4),
                "top10_rows": f.top10_rows,
                "bear_top10_win_rate": None if f.bear_top10_win_rate is None else round(f.bear_top10_win_rate, 4),
                "bear_top10_rows": f.bear_top10_rows,
                "bull_top10_win_rate": None if f.bull_top10_win_rate is None else round(f.bull_top10_win_rate, 4),
                "bull_top10_rows": f.bull_top10_rows,
            }
            for f in folds
        ],
    }


def _feature_and_lag_columns(all_columns: list[str], base_features: list[str]) -> list[str]:
    return [
        col
        for col in all_columns
        if any(col == base or col.startswith(f"{base}_lag") for base in base_features)
    ]


def _build_subsets(all_columns: list[str]) -> dict[str, list[str]]:
    subsets = train_module._build_feature_profile_columns(all_columns)
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


def _write_markdown(payload: dict[str, Any]) -> None:
    rows = payload["profiles"]
    ranking = sorted(
        rows.items(),
        key=lambda item: (
            item[1]["cv_mean_accuracy"],
            item[1]["cv_worst_accuracy"],
            -item[1]["cv_std_accuracy"],
        ),
        reverse=True,
    )

    lines = [
        "# Feature Group Ablation Report",
        "",
        f"- target: `{payload['target_col']}`",
        f"- recent_rows: **{payload['recent_rows']}**",
        f"- splits: **{payload['n_splits']}** (TimeSeriesSplit)",
        f"- xgb_n_estimators: **{payload.get('xgb_n_estimators', DEFAULT_XGB_PARAMS['n_estimators'])}**",
        f"- refresh_mode: **{payload.get('refresh_mode', 'full_rebuild')}**",
        f"- generated_at: **{payload['generated_at']} UTC**",
        "",
        "## Ranking (accuracy / worst fold / stability)",
        "",
        "| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 | bull_top10 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, metrics in ranking:
        lines.append(
            "| {name} | {feature_count} | {cv_mean_accuracy:.4f} | {cv_std_accuracy:.4f} | {cv_worst_accuracy:.4f} | {cv_mean_brier:.4f} | {top10} | {bear_top10} | {bull_top10} |".format(
                name=name,
                feature_count=metrics["feature_count"],
                cv_mean_accuracy=metrics["cv_mean_accuracy"],
                cv_std_accuracy=metrics["cv_std_accuracy"],
                cv_worst_accuracy=metrics["cv_worst_accuracy"],
                cv_mean_brier=metrics["cv_mean_brier"],
                top10="-" if metrics["top10_win_rate_mean"] is None else f"{metrics['top10_win_rate_mean']:.4f}",
                bear_top10="-" if metrics["bear_top10_win_rate_mean"] is None else f"{metrics['bear_top10_win_rate_mean']:.4f}",
                bull_top10="-" if metrics["bull_top10_win_rate_mean"] is None else f"{metrics['bull_top10_win_rate_mean']:.4f}",
            )
        )

    best = payload.get("recommended_profile") or ranking[0][0]
    collapse_text = ", ".join(payload.get("bull_collapse_4h_features") or [])
    lines.extend(
        [
            "",
            "## Notes",
            "",
            f"- Recommended profile this run: **`{best}`**",
            f"- Bull collapse 4H watchlist carried into this run: `{collapse_text}`",
            "- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.",
            "- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.",
            "- `core_macro_plus_stable_4h` answers the current heartbeat question: do the non-collapse 4H signals help once the three toxic bull-pocket features are removed?",
            "- `current_full_no_bull_collapse_4h` removes the bull collapse trio plus their lag columns to test whether the live blocker is tied to that 4H family rather than to calibration alone.",
            "- `model/train.py` now auto-selects this recommended profile during training when the ablation artifact matches the active target.",
        ]
    )

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Feature-group ablation report for the canonical target.")
    parser.add_argument(
        "--bounded-refresh",
        action="store_true",
        help=(
            "Cron-safe candidate refresh: evaluate only the governance-critical profiles "
            "with a smaller recent window / split count / estimator budget. Manual runs "
            "without this flag still perform the full report."
        ),
    )
    parser.add_argument("--recent-rows", type=int, default=None, help="Override recent rows used for this report.")
    parser.add_argument("--n-splits", type=int, default=None, help="Override TimeSeriesSplit fold count.")
    parser.add_argument("--n-estimators", type=int, default=None, help="Override XGBoost n_estimators.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    recent_rows = args.recent_rows or (BOUNDED_RECENT_ROWS if args.bounded_refresh else RECENT_ROWS)
    n_splits = args.n_splits or (BOUNDED_N_SPLITS if args.bounded_refresh else N_SPLITS)
    n_estimators = args.n_estimators or (BOUNDED_N_ESTIMATORS if args.bounded_refresh else DEFAULT_XGB_PARAMS["n_estimators"])
    xgb_params = {**DEFAULT_XGB_PARAMS, "n_estimators": int(n_estimators)}

    X, y, regimes, source_meta = _load_training_frame(recent_rows=recent_rows)
    all_subsets = _build_subsets(list(X.columns))
    if args.bounded_refresh:
        subsets = {
            name: all_subsets[name]
            for name in BOUNDED_PROFILE_NAMES
            if name in all_subsets and all_subsets[name]
        }
        if not subsets:
            subsets = all_subsets
    else:
        subsets = all_subsets
    profile_results = {
        name: _evaluate_subset(X, y, regimes, columns, n_splits=n_splits, xgb_params=xgb_params)
        for name, columns in subsets.items()
    }

    generated_at = pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M:%S")
    ranked = sorted(
        profile_results.items(),
        key=lambda item: train_module._rank_feature_profile(item[0], item[1]),
        reverse=True,
    )
    payload = {
        "generated_at": generated_at,
        "source_meta": source_meta,
        "target_col": TARGET_COL,
        "recent_rows": int(recent_rows),
        "positive_ratio": round(float(y.mean()), 4),
        "regime_mix": {k: int(v) for k, v in regimes.value_counts().to_dict().items()},
        "n_splits": int(n_splits),
        "xgb_n_estimators": int(n_estimators),
        "refresh_mode": "bounded_candidate_refresh" if args.bounded_refresh else "full_rebuild",
        "profile_metrics_fresh": True,
        "profiles_evaluated": list(profile_results.keys()),
        "full_profile_count": len(all_subsets),
        "bounded_profile_count": len(profile_results) if args.bounded_refresh else None,
        "bull_collapse_4h_features": BULL_COLLAPSE_4H_FEATURES,
        "stable_4h_features": STABLE_4H_FEATURES,
        "recommended_profile": ranked[0][0] if ranked else None,
        "profiles": profile_results,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_markdown(payload)

    print(json.dumps({
        "json": str(OUT_JSON),
        "markdown": str(OUT_MD),
        "best_profile": payload.get("recommended_profile"),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
