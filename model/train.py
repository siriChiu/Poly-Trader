"""
模型訓練模組 v5 — sell-win aware + probability calibration
"""

import os
import json
import pickle
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from sqlalchemy.orm import Session
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.isotonic import IsotonicRegression

from database.models import FeaturesNormalized, Labels, RawMarketData
from utils.logger import setup_logger

logger = setup_logger(__name__)

MODEL_PATH = "model/xgb_model.pkl"
DB_PATH = str(Path(__file__).parent.parent / "poly_trader.db")
FEATURE_COLS = [
    # === 8 Core Senses ===
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue",
    "feat_body", "feat_pulse", "feat_aura", "feat_mind",
    # === 2 Macro ===
    "feat_vix", "feat_dxy",
    # === 5 Technical Indicators ===
    "feat_rsi14", "feat_macd_hist", "feat_atr_pct",
    "feat_vwap_dev", "feat_bb_pct_b",
    # === P0/P1 Sensory + NQ ===
    # P0: Disabled — only 20 samples, no training signal (ic_status=LOW/NO_DATA)
    # "feat_claw", "feat_claw_intensity", "feat_fang_pcr",
    # "feat_fang_skew", "feat_fin_netflow", "feat_nq_return_1h",
    # === Re-enabled with sufficient data threshold ===
    # Re-add once these features have > 500 samples in the DB
]
LAG_STEPS = [12, 48, 288]
BASE_FEATURE_COLS = FEATURE_COLS

REGIME_THRESHOLD_BIAS = {
    'trend': -0.03,
    'chop': 0.04,
    'panic': -0.01,
    'event': 0.02,
    'normal': 0.0,
}


def _feature_row(r):
    return {
        "timestamp": r.timestamp,
        "symbol": getattr(r, "symbol", "BTCUSDT"),
        **{c: getattr(r, c, None) for c in FEATURE_COLS},
        "regime_label": getattr(r, "regime_label", None),
    }


def load_training_data(session: Session, min_samples: int = 50,
                       regime_filter: Optional[list] = None,
                       horizon_minutes: int = 720) -> Optional[Tuple[pd.DataFrame, pd.Series]]:
    """Load training data from DB, filtered by horizon_minutes.

    Args:
        session: SQLAlchemy session
        min_samples: minimum samples after merge
        regime_filter: optional list of regime labels to keep
        horizon_minutes: label horizon to use (default 720=12h). Pass None for all horizons.
    """
    feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
    label_query = session.query(Labels).filter(
        Labels.label_sell_win.isnot(None),
        Labels.future_return_pct.isnot(None),
    )
    if horizon_minutes is not None:
        label_query = label_query.filter(Labels.horizon_minutes == horizon_minutes)
    label_rows = label_query.order_by(Labels.timestamp).all()

    if not feat_rows or not label_rows:
        return None

    feat_df = pd.DataFrame([_feature_row(r) for r in feat_rows])
    label_df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "label_sell_win": int(r.label_sell_win),
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
    merged = merged.dropna(subset=["label_sell_win"]).copy()

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
    # P0 audit: Count non-null BEFORE fillna
    non_null_before = {col: int(merged[col].notna().sum()) for col in all_cols}
    # Fill NaN with 0 for XGBoost (but preserve counts for IC audit)
    merged[all_cols] = merged[all_cols].fillna(0.0)

    if len(merged) < min_samples:
        logger.warning(f"合併後樣本不足: {len(merged)} < {min_samples}")
        return None

    from scipy import stats as _stats

    merged = merged.copy()
    ic_map = {}
    ic_map_global = {}
    tw_ic_map = {}
    NEG_IC_FEATS = []
    y_arr = merged["label_sell_win"].astype(float).values
    all_feature_cols = FEATURE_COLS + lag_feature_cols
    N = len(y_arr)

    # P0 #H425: Time-weighted IC (TW-IC) — exponential decay gives recent samples more influence.
    # tau=200 matches production predictor (predictor.py:_time_weighted_ic).
    # For non-core features (lags, crosses), fall back to global Spearman IC.
    tau = 200
    core_cols = set(FEATURE_COLS)  # 8 core senses + VIX + DXY
    weights = np.exp(-(N - 1 - np.arange(N, dtype=float)) / tau)

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
            "target": "label_sell_win",
            "core_ic_summary": core_ic_summary,
            "tw_ic_summary": tw_ic_summary,
        }, f, indent=2, ensure_ascii=False)
    logger.info(f"TW-IC (core): {core_ic_summary}")
    logger.info(f"Global IC (core): {core_ic_summary}")
    logger.info(f"動態 TW-IC/Global IC 計算完成 — core 使用 TW-IC, 其餘使用 Global IC")
    logger.info(f"NEG_IC 反轉特徵: {NEG_IC_FEATS}")

    # High-IC alternative features discovered via hb105_exploratory_analysis (IC > 0.05):
    # eye_dist +0.050, mean_rev_20h -0.056, price_ret_12h -0.052, price_ret_24h -0.051, rsi_14_norm -0.051
    # These are derived from raw market data — need close_price from raw_market_data join
    # For now, construct them from the base features we have

    # Price return features (from feat_eye which is close_price normalized via return_24h/vol_72h,
    # we can approximate using the eye_dist which IS in raw_market_data)
    # Note: feat_eye IS eye_dist (alias in models.py), so it already contains the high-IC eye_dist signal

    # VIX interaction features — VIX is the highest-IC macro signal
    # VIX×Eye: fear × return/vol ratio (captures risk-off sentiment amplification)
    merged["feat_vix_x_eye"] = merged["feat_vix"] * merged["feat_eye"]
    # VIX×Pulse: fear × volume spike (panics come with volume)
    merged["feat_vix_x_pulse"] = merged["feat_vix"] * merged["feat_pulse"]
    # VIX×Mind: fear × short-term return (inverse relationship in fear regimes)
    merged["feat_vix_x_mind"] = merged["feat_vix"] * merged["feat_mind"]

    # Cross-sense features that capture regime friction
    merged["feat_mind_x_pulse"] = merged["feat_mind"] * merged["feat_pulse"]
    merged["feat_eye_x_ear"] = merged["feat_eye"] * merged["feat_ear"]
    merged["feat_nose_x_aura"] = merged["feat_nose"] * merged["feat_aura"]
    merged["feat_eye_x_body"] = merged["feat_eye"] * merged["feat_body"]
    merged["feat_ear_x_nose"] = merged["feat_ear"] * merged["feat_nose"]
    merged["feat_mind_x_aura"] = merged["feat_mind"] * merged["feat_aura"]
    # Handle suffix from merge_asof (both sides have regime_label → regime_label_x / regime_label_y)
    if "regime_label" not in merged.columns:
        if "regime_label_y" in merged.columns:
            merged["regime_label"] = merged["regime_label_y"]
        elif "regime_label_x" in merged.columns:
            merged["regime_label"] = merged["regime_label_x"]
        else:
            merged["regime_label"] = "neutral"
    merged["feat_regime_flag"] = merged["regime_label"].map({"trend": 1.0, "chop": -1.0, "panic": -0.5, "event": 0.5, "normal": 0.0}).fillna(0.0)

    # Mean-reversion proxy: difference between short-term (mind=ret_144) and long-term (aura=sma144_deviation)
    merged["feat_mean_rev_proxy"] = merged["feat_mind"] - merged["feat_aura"]

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
            pruned_cols.append(col)  # Always keep core features
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

    X = merged[all_training_cols]
    y = merged["label_sell_win"].astype(int)
    y_return = merged["future_return_pct"].astype(float)
    logger.info(f"載入訓練資料: {len(X)} 筆, {len(all_training_cols)} features ({len(FEATURE_COLS)} core + {len(all_training_cols)-len(FEATURE_COLS)} lag/cross, {pruned_count} pruned)")
    logger.info(f"分類目標 sell_win ratio: {y.mean():.3f}, 回歸目標 future_return_pct mean={y_return.mean():.5f} std={y_return.std():.5f}")
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
            return {
                'kind': 'isotonic',
                'x': [float(v) for v in iso.X_thresholds_.tolist()],
                'y': [float(v) for v in iso.y_thresholds_.tolist()],
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


def run_training(session: Session, regime_filter: Optional[list] = None) -> bool:
    """Train global XGBoost model with IC pruning and optional regime filtering.
    
    Args:
        session: SQLAlchemy session
        regime_filter: Optional list of regime labels to keep (e.g., ["bear", "bull"]).
                      If None, uses all regimes. Experiment shows Bear+Bull filtering
                      with IC pruning gives AUC=0.5454 vs 0.5241 for ALL.
    """
    logger.info("開始模型訓練 v5 (with IC pruning + optional regime filter)...")
    loaded = load_training_data(session, min_samples=50, regime_filter=regime_filter)
    if loaded is None:
        return False
    X, y = loaded
    model = train_xgboost(X, y)
    calibrator = fit_probability_calibrator(model, X, y)

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
        'neg_ic_feats': neg_ic,
        'calibration': calibrator,
        'regime_threshold_bias': REGIME_THRESHOLD_BIAS,
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

        db = sqlite3.connect('poly_trader.db')
        cur = db.cursor()
        cur.execute("""
            INSERT INTO model_metrics (timestamp, train_accuracy, cv_accuracy, cv_std, n_features, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.utcnow().isoformat(), train_acc, cv_acc, cv_std, X.shape[1],
              f'rolling_cv n={n_folds} worst={cv_worst:.4f} best={cv_best:.4f}'))
        db.commit(); db.close()
        logger.info(f"模型指標: Train={train_acc:.3f}, Rolling-CV={cv_acc:.3f}±{cv_std:.3f}, worst={cv_worst:.3f}")
    except Exception as e:
        logger.warning(f"無法保存 model_metrics: {e}")

    return True


def train_regime_models(session: Session) -> bool:
    """Train one XGBoost model per market regime (bear/bull/chop/neutral).
    Addresses P0 #H122 / #H301: global model CV ~52% because different regimes
    have different signal patterns. Regime-aware training should lift per-regime CV.
    """
    logger.info("開始訓練 Regime-Specific XGBoost 模型...")
    loaded = load_training_data(session, min_samples=50)
    if loaded is None:
        logger.warning("訓練資料不足，跳過 regime-specific 訓練")
        return False

    # Re-load with regime info (also filter by horizon_minutes=720)
    feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
    label_rows = (
        session.query(Labels)
        .filter(Labels.label_sell_win.isnot(None), Labels.future_return_pct.isnot(None),
                Labels.horizon_minutes == 720)
        .order_by(Labels.timestamp)
        .all()
    )

    feat_df = pd.DataFrame([_feature_row(r) for r in feat_rows])
    label_df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "label_sell_win": int(r.label_sell_win),
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
    merged = merged.dropna(subset=["label_sell_win"]).copy()

    # Build feature columns (same as global)
    for col in BASE_FEATURE_COLS:
        for lag in LAG_STEPS:
            lag_col = f"{col}_lag{lag}"
            merged[lag_col] = merged[col].shift(lag)

    all_feat_cols = FEATURE_COLS + [f"{c}_lag{l}" for c in BASE_FEATURE_COLS for l in LAG_STEPS]
    CROSS_FEATURES_LOCAL = [
        "feat_vix_x_eye", "feat_vix_x_pulse", "feat_vix_x_mind",
        "feat_mind_x_pulse", "feat_eye_x_ear", "feat_nose_x_aura",
        "feat_eye_x_body", "feat_ear_x_nose", "feat_mind_x_aura",
        "feat_mean_rev_proxy",
        # P0: Disabled — base features (claw, fang, fin, nq) have <500 samples
        # "feat_claw_x_pulse", "feat_fang_x_vix",
        # "feat_fin_x_claw", "feat_web_x_fang", "feat_nq_x_vix",
    ]
    for col in all_feat_cols:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')
    merged[all_feat_cols] = merged[all_feat_cols].fillna(0.0)
    # Cross features
    merged["feat_vix_x_eye"] = merged["feat_vix"] * merged["feat_eye"]
    merged["feat_vix_x_pulse"] = merged["feat_vix"] * merged["feat_pulse"]
    merged["feat_vix_x_mind"] = merged["feat_vix"] * merged["feat_mind"]
    merged["feat_mind_x_pulse"] = merged["feat_mind"] * merged["feat_pulse"]
    merged["feat_eye_x_ear"] = merged["feat_eye"] * merged["feat_ear"]
    merged["feat_nose_x_aura"] = merged["feat_nose"] * merged["feat_aura"]
    merged["feat_eye_x_body"] = merged["feat_eye"] * merged["feat_body"]
    merged["feat_ear_x_nose"] = merged["feat_ear"] * merged["feat_nose"]
    merged["feat_mind_x_aura"] = merged["feat_mind"] * merged["feat_aura"]
    merged["feat_mean_rev_proxy"] = merged["feat_mind"] - merged["feat_aura"]
    # P0: Disabled cross-features removed — base features have <500 samples

    X_cols = all_feat_cols + CROSS_FEATURES_LOCAL
    # Defensive: only include columns that actually exist in merged (avoids KeyError)
    X_cols = [c for c in X_cols if c in merged.columns]

    regime_models = {}
    params = {
        "n_estimators": 200, "max_depth": 3, "learning_rate": 0.05,
        "subsample": 0.8, "colsample_bytree": 0.8,
        "reg_alpha": 2.0, "reg_lambda": 6.0, "min_child_weight": 10, "gamma": 0.2,
        "objective": "binary:logistic", "eval_metric": "logloss", "random_state": 42,
    }

    for regime in ['bear', 'bull', 'chop']:
        regime_mask = merged['regime_label'] == regime
        regime_data = merged[regime_mask].copy()
        n = len(regime_data)
        if n < 200:
            logger.warning(f"Regime {regime}: only {n} samples, skipping")
            continue

        X_r = regime_data[X_cols].fillna(0.0)
        y_r = regime_data["label_sell_win"].astype(int)

        sample_weight = compute_sample_weight("balanced", y_r)
        model_r = xgb.XGBClassifier(**params)
        model_r.fit(X_r, y_r, sample_weight=sample_weight)

        train_acc = float((model_r.predict(X_r) == y_r).mean())

        # TimeSeriesSplit CV
        try:
            from sklearn.model_selection import TimeSeriesSplit
            tscv = TimeSeriesSplit(n_splits=3)
            cv_scores = []
            for _tr, _te in tscv.split(X_r):
                y_tr = y_r.iloc[_tr]
                if len(y_tr.unique()) < 2:
                    continue
                m = xgb.XGBClassifier(**{k: v for k, v in model_r.get_params().items()})
                m.fit(X_r.iloc[_tr], y_tr, sample_weight=compute_sample_weight("balanced", y_tr))
                cv_scores.append(float((m.predict(X_r.iloc[_te]) == y_r.iloc[_te]).mean()))
            cv_acc = float(np.mean(cv_scores)) if cv_scores else float('nan')
        except Exception as e:
            cv_acc = float('nan')
            logger.warning(f"Regime {regime} CV failed: {e}")

        reg_payload = {
            'clf': model_r, 'feature_names': X_cols,
            'neg_ic_feats': [], 'calibration': {'kind': 'none'},
            'regime_threshold_bias': REGIME_THRESHOLD_BIAS,
        }
        regime_models[regime] = reg_payload
        logger.info(f"Regime {regime} model: Train={train_acc:.4f}, CV={cv_acc:.4f}, n={n}")

    if regime_models:
        os.makedirs("model", exist_ok=True)
        with open("model/regime_models.pkl", "wb") as f:
            pickle.dump(regime_models, f)
        logger.info(f"Regime-specified models saved: {list(regime_models.keys())}")
        return True
    return False


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
        train_regime_models(session)
        rpath = str(Path(__file__).parent / "regime_models.pkl")
        if os.path.exists(rpath):
            with open(rpath, "rb") as f:
                rm = pickle.load(f)
            for r in rm:
                n = len(rm[r].get("feature_names", []))
                print("  {}: {} features saved".format(r, n))
        print("Training complete.")
        return True
    finally:
        session.close()


if __name__ == "__main__":
    main()
