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

from database.models import FeaturesNormalized, Labels
from utils.logger import setup_logger

logger = setup_logger(__name__)

MODEL_PATH = "model/xgb_model.pkl"
FEATURE_COLS = [
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue",
    "feat_body", "feat_pulse", "feat_aura", "feat_mind",
    "feat_whisper", "feat_tone", "feat_chorus", "feat_hype",
    "feat_oracle", "feat_shock", "feat_tide", "feat_storm",
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
            corr, _ = _stats.spearmanr(feat_arr[mask], y_arr[mask])
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

    # New feature exploration: a small cross-feature set that often captures regime friction.
    merged["feat_mind_x_pulse"] = merged["feat_mind"] * merged["feat_pulse"]
    merged["feat_eye_x_ear"] = merged["feat_eye"] * merged["feat_ear"]
    merged["feat_aura_x_tide"] = merged["feat_aura"] * merged["feat_tide"]
    merged["feat_regime_flag"] = merged["regime_label"].map({"trend": 1.0, "chop": -1.0, "panic": -0.5, "event": 0.5, "normal": 0.0}).fillna(0.0)

    X = merged[FEATURE_COLS + lag_feature_cols + ["feat_mind_x_pulse", "feat_eye_x_ear", "feat_aura_x_tide", "feat_regime_flag"]]
    y = merged["label_sell_win"].astype(int)
    logger.info(f"載入訓練資料: {len(X)} 筆, {len(FEATURE_COLS)} base features + {len(lag_feature_cols)} lags + 4 cross-features")
    return X, y


def train_xgboost(X: pd.DataFrame, y: pd.Series, params: Optional[dict] = None) -> xgb.XGBClassifier:
    dist = y.value_counts().sort_index().to_dict()
    logger.info(f"Class dist: {dist}")

    if params is None:
        params = {
            "n_estimators": 250,
            "max_depth": 3,
            "learning_rate": 0.03,
            "subsample": 0.7,
            "colsample_bytree": 0.7,
            "reg_alpha": 2.0,
            "reg_lambda": 6.0,
            "min_child_weight": 10,
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
