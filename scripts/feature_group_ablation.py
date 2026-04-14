#!/usr/bin/env python3
"""Feature-group ablation report for Poly-Trader canonical target.

Goal: compare accuracy/stability across feature families without adding new UI knobs.
Outputs:
- data/feature_group_ablation.json
- docs/analysis/feature_group_ablation.md
"""

from __future__ import annotations

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


@dataclass
class FoldMetrics:
    accuracy: float
    brier: float
    top10_win_rate: float | None
    top10_rows: int
    bear_top10_win_rate: float | None
    bear_top10_rows: int


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


def _load_training_frame() -> tuple[pd.DataFrame, pd.Series, pd.Series]:
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
    merged = merged.iloc[-RECENT_ROWS:].reset_index(drop=True)

    X = merged[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y = merged[TARGET_COL].astype(int)
    regimes = merged["regime_label"].fillna("neutral").astype(str)
    return X, y, regimes


def _safe_win_rate(y_true: pd.Series, proba: np.ndarray, top_k: float = TOP_K) -> tuple[float | None, int]:
    if len(y_true) == 0:
        return None, 0
    n = max(1, int(math.ceil(len(y_true) * top_k)))
    order = np.argsort(proba)[-n:]
    selected = y_true.iloc[order]
    return float(selected.mean()), int(len(selected))


def _evaluate_subset(X: pd.DataFrame, y: pd.Series, regimes: pd.Series, columns: list[str]) -> dict[str, Any]:
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    folds: list[FoldMetrics] = []

    for train_idx, test_idx in tscv.split(X):
        X_train = X.iloc[train_idx][columns]
        X_test = X.iloc[test_idx][columns]
        y_train = y.iloc[train_idx]
        y_test = y.iloc[test_idx]
        regime_test = regimes.iloc[test_idx]

        model = XGBClassifier(**DEFAULT_XGB_PARAMS)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)

        top10, top10_rows = _safe_win_rate(y_test, proba)
        bear_mask = regime_test == "bear"
        bear_top10, bear_top10_rows = _safe_win_rate(y_test[bear_mask], proba[bear_mask.values])

        folds.append(
            FoldMetrics(
                accuracy=float(accuracy_score(y_test, pred)),
                brier=float(brier_score_loss(y_test, proba)),
                top10_win_rate=top10,
                top10_rows=top10_rows,
                bear_top10_win_rate=bear_top10,
                bear_top10_rows=bear_top10_rows,
            )
        )

    accs = [f.accuracy for f in folds]
    briers = [f.brier for f in folds]
    top10_rates = [f.top10_win_rate for f in folds if f.top10_win_rate is not None]
    bear_top10_rates = [f.bear_top10_win_rate for f in folds if f.bear_top10_win_rate is not None]

    return {
        "feature_count": len(columns),
        "cv_mean_accuracy": float(np.mean(accs)),
        "cv_std_accuracy": float(np.std(accs)),
        "cv_worst_accuracy": float(np.min(accs)),
        "cv_mean_brier": float(np.mean(briers)),
        "top10_win_rate_mean": float(np.mean(top10_rates)) if top10_rates else None,
        "bear_top10_win_rate_mean": float(np.mean(bear_top10_rates)) if bear_top10_rates else None,
        "folds": [
            {
                "accuracy": round(f.accuracy, 4),
                "brier": round(f.brier, 4),
                "top10_win_rate": None if f.top10_win_rate is None else round(f.top10_win_rate, 4),
                "top10_rows": f.top10_rows,
                "bear_top10_win_rate": None if f.bear_top10_win_rate is None else round(f.bear_top10_win_rate, 4),
                "bear_top10_rows": f.bear_top10_rows,
            }
            for f in folds
        ],
    }


def _build_subsets(all_columns: list[str]) -> dict[str, list[str]]:
    lag_cols = [c for c in all_columns if "_lag" in c]
    cross_cols = [c for c in all_columns if c in CROSS_FEATURES]

    core_cols = [c for c in all_columns if c in CORE_FEATURES]
    macro_cols = [c for c in all_columns if c in MACRO_FEATURES]
    technical_cols = [c for c in all_columns if c in TECHNICAL_FEATURES]
    four_h_cols = [c for c in all_columns if c in FOUR_H_FEATURES]

    base_no_lags_cross = [c for c in all_columns if c not in lag_cols and c not in cross_cols]

    return {
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
        f"- generated_at: **{payload['generated_at']} UTC**",
        "",
        "## Ranking (accuracy / worst fold / stability)",
        "",
        "| profile | n_features | cv_mean | cv_std | cv_worst | brier | top10 | bear_top10 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, metrics in ranking:
        lines.append(
            "| {name} | {feature_count} | {cv_mean_accuracy:.4f} | {cv_std_accuracy:.4f} | {cv_worst_accuracy:.4f} | {cv_mean_brier:.4f} | {top10} | {bear_top10} |".format(
                name=name,
                feature_count=metrics["feature_count"],
                cv_mean_accuracy=metrics["cv_mean_accuracy"],
                cv_std_accuracy=metrics["cv_std_accuracy"],
                cv_worst_accuracy=metrics["cv_worst_accuracy"],
                cv_mean_brier=metrics["cv_mean_brier"],
                top10="-" if metrics["top10_win_rate_mean"] is None else f"{metrics['top10_win_rate_mean']:.4f}",
                bear_top10="-" if metrics["bear_top10_win_rate_mean"] is None else f"{metrics['bear_top10_win_rate_mean']:.4f}",
            )
        )

    best = ranking[0][0]
    lines.extend(
        [
            "",
            "## Notes",
            "",
            f"- Best profile this run: **`{best}`**",
            "- `full_no_*` profiles are removal tests — if they improve worst fold or reduce std, that feature family is a variance suspect.",
            "- `core_plus_*` profiles are additive sanity checks — they show which family helps most before lags/cross-features enter.",
        ]
    )

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    X, y, regimes = _load_training_frame()
    subsets = _build_subsets(list(X.columns))

    profile_results = {
        name: _evaluate_subset(X, y, regimes, columns)
        for name, columns in subsets.items()
    }

    generated_at = pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "generated_at": generated_at,
        "target_col": TARGET_COL,
        "recent_rows": int(len(X)),
        "positive_ratio": float(y.mean()),
        "regime_mix": {str(k): int(v) for k, v in regimes.value_counts().to_dict().items()},
        "n_splits": N_SPLITS,
        "profiles": profile_results,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_markdown(payload)

    print(json.dumps({
        "json": str(OUT_JSON),
        "markdown": str(OUT_MD),
        "best_profile": max(profile_results.items(), key=lambda item: item[1]["cv_mean_accuracy"])[0],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
