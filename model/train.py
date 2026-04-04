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
# 8 core senses + VIX + DXY = 10 active features
# 8 auxiliary (whisper/tone/chorus/hype/oracle/shock/tide/storm) are zero/constant — keep out of training
FEATURE_COLS = [
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue",
    "feat_body", "feat_pulse", "feat_aura", "feat_mind",
    "feat_vix", "feat_dxy",
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


def load_training_data(session: Session, min_samples: int = 50) -> Optional[Tuple[pd.DataFrame, pd.Series]]:
    feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
    label_rows = (
        session.query(Labels)
        .filter(Labels.label_sell_win.isnot(None), Labels.future_return_pct.isnot(None))
        .order_by(Labels.timestamp)
        .all()
    )

    if not feat_rows or not label_rows:
        return None

    feat_df = pd.DataFrame([_feature_row(r) for r in feat_rows])
    label_df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "label_sell_win": int(r.label_sell_win),
        "label_up": int(r.label_up) if r.label_up is not None else None,
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
    merged[all_cols] = merged[all_cols].fillna(0.0)

    if len(merged) < min_samples:
        logger.warning(f"合併後樣本不足: {len(merged)} < {min_samples}")
        return None

    from scipy import stats as _stats
    merged = merged.copy()
    ic_map = {}
    NEG_IC_FEATS = []
    y_arr = merged["label_sell_win"].astype(float).values
    all_feature_cols = FEATURE_COLS + lag_feature_cols
    for col in all_feature_cols:
        feat_arr = merged[col].astype(float).values
        mask = ~(np.isnan(feat_arr) | np.isnan(y_arr))
        if mask.sum() > 30:
            masked = feat_arr[mask]
            # Skip constant columns to avoid ConstantInputWarning and NaN IC
            if np.ptp(masked) == 0.0 or np.unique(masked).size <= 1:
                ic_map[col] = 0.0
                continue
            corr, _ = _stats.spearmanr(masked, y_arr[mask])
            # Guard against NaN from edge cases in spearmanr
            if corr is None or (isinstance(corr, float) and not np.isfinite(corr)):
                ic_map[col] = 0.0
            else:
                ic_map[col] = float(corr)
                if corr < 0:
                    NEG_IC_FEATS.append(col)
                    merged[col] = -merged[col]
        else:
            ic_map[col] = 0.0

    os.makedirs("model", exist_ok=True)
    with open("model/ic_signs.json", "w", encoding="utf-8") as f:
        json.dump({"neg_ic_feats": NEG_IC_FEATS, "ic_map": ic_map, "target": "label_sell_win"}, f, indent=2, ensure_ascii=False)
    logger.info(f"動態 IC 計算完成: {ic_map}")
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
    merged["feat_regime_flag"] = merged["regime_label"].map({"trend": 1.0, "chop": -1.0, "panic": -0.5, "event": 0.5, "normal": 0.0}).fillna(0.0)

    # Mean-reversion proxy: difference between short-term (mind=ret_144) and long-term (aura=sma144_deviation)
    merged["feat_mean_rev_proxy"] = merged["feat_mind"] - merged["feat_aura"]

    # RSI proxy: nose IS rsi14_norm, so use it directly as-is (already in FEATURE_COLS)

    CROSS_FEATURES = [
        "feat_vix_x_eye", "feat_vix_x_pulse", "feat_vix_x_mind",
        "feat_mind_x_pulse", "feat_eye_x_ear", "feat_nose_x_aura",
        "feat_eye_x_body", "feat_ear_x_nose", "feat_mind_x_aura",
        "feat_regime_flag", "feat_mean_rev_proxy"
    ]

    X = merged[FEATURE_COLS + lag_feature_cols + CROSS_FEATURES]
    y = merged["label_sell_win"].astype(int)
    logger.info(f"載入訓練資料: {len(X)} 筆, {len(FEATURE_COLS)} base features + {len(lag_feature_cols)} lags + 4 cross-features")
    return X, y


def train_xgboost(X: pd.DataFrame, y: pd.Series, params: Optional[dict] = None) -> xgb.XGBClassifier:
    dist = y.value_counts().sort_index().to_dict()
    logger.info(f"Class dist: {dist}")

    if params is None:
        # P0 Fix #H130: Rollback from overfitted depth=5, reg_alpha=0.5
        # Conservative params that avoid memorization (8 core features only, no constant noise)
        params = {
            "n_estimators": 200,
            "max_depth": 3,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 2.0,
            "reg_lambda": 6.0,
            "min_child_weight": 10,
            "gamma": 0.2,
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


def run_training(session: Session) -> bool:
    logger.info("開始模型訓練 v5...")
    loaded = load_training_data(session, min_samples=50)
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
        from sklearn.model_selection import TimeSeriesSplit
        from datetime import datetime
        import sqlite3
        train_acc = float((model.predict(X) == y).mean())
        tscv = TimeSeriesSplit(n_splits=5)
        valid_scores = []
        for _tr, _te in tscv.split(X):
            y_tr = y.iloc[_tr]
            if len(y_tr.unique()) < 2:
                continue
            _m = xgb.XGBClassifier(**{k: v for k, v in model.get_params().items()})
            _m.fit(X.iloc[_tr], y_tr)
            valid_scores.append(float((_m.predict(X.iloc[_te]) == y.iloc[_te]).mean()))
        cv_acc = float(np.mean(valid_scores)) if valid_scores else float('nan')
        cv_std = float(np.std(valid_scores)) if valid_scores else float('nan')
        db = sqlite3.connect('poly_trader.db')
        cur = db.cursor()
        cur.execute("""
            INSERT INTO model_metrics (timestamp, train_accuracy, cv_accuracy, cv_std, n_features, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.utcnow().isoformat(), train_acc, cv_acc, cv_std, X.shape[1], 'sell-win auto-train'))
        db.commit(); db.close()
        logger.info(f"模型指標: Train={train_acc:.3f}, CV={cv_acc:.3f}±{cv_std:.3f}")
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

    # Re-load with regime info
    feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
    label_rows = (
        session.query(Labels)
        .filter(Labels.label_sell_win.isnot(None), Labels.future_return_pct.isnot(None))
        .order_by(Labels.timestamp)
        .all()
    )

    feat_df = pd.DataFrame([_feature_row(r) for r in feat_rows])
    label_df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "label_sell_win": int(r.label_sell_win),
        "label_up": int(r.label_up) if r.label_up is not None else None,
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

    X_cols = all_feat_cols + CROSS_FEATURES_LOCAL

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
