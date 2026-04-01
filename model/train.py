"""
模型訓練模組 v3 — IC-validated features + confidence-aware training
"""

import os
import pickle
from typing import Optional, Tuple
import pandas as pd
import numpy as np
import xgboost as xgb
from sqlalchemy.orm import Session

from database.models import FeaturesNormalized, Labels
from utils.logger import setup_logger

logger = setup_logger(__name__)

MODEL_PATH = "model/xgb_model.pkl"
FEATURE_COLS = [
    "feat_eye_dist",    # funding_ma72 (IC=-0.089)
    "feat_ear_zscore",  # momentum_48h (IC=-0.091)
    "feat_nose_sigmoid",# autocorr_48h (IC=-0.103)
    "feat_tongue_pct",  # volatility_24h (IC=-0.067)
    "feat_body_roc",    # range_pos_24h (IC=+0.018)
    "feat_pulse",       # funding_z_24h (IC=-0.075 n=2160)
    "feat_aura",        # funding_zscore_288 — 長週期 funding z-score (IC=-0.094, v4)
    "feat_mind",        # funding_z_24 (IC=+0.063)
]


def load_training_data(
    session: Session, min_samples: int = 50
) -> Optional[Tuple[pd.DataFrame, pd.Series]]:
    """從 DB 提取特徵 + Labels，以時間戳 JOIN。"""
    feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
    label_rows = (
        session.query(Labels)
        .filter(Labels.horizon_hours == 4, Labels.future_return_pct.isnot(None))
        .order_by(Labels.timestamp)
        .all()
    )  # fix #H62: only use h=1 labels with valid future_return_pct (exclude NULL pseudo-labels)

    feat_df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "feat_eye_dist": r.feat_eye_dist,
        "feat_ear_zscore": r.feat_ear_zscore,
        "feat_nose_sigmoid": r.feat_nose_sigmoid,
        "feat_tongue_pct": r.feat_tongue_pct,
        "feat_body_roc": r.feat_body_roc,
        "feat_pulse": r.feat_pulse,
        "feat_aura": r.feat_aura,
        "feat_mind": r.feat_mind,
    } for r in feat_rows])

    label_df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "label": r.label,
    } for r in label_rows])  # filtered: horizon=4, future_return_pct IS NOT NULL

    feat_df["timestamp"] = pd.to_datetime(feat_df["timestamp"])
    label_df["timestamp"] = pd.to_datetime(label_df["timestamp"])

    merged = pd.merge_asof(
        feat_df.sort_values("timestamp"),
        label_df.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("10min"),
    )
    merged.dropna(subset=FEATURE_COLS + ["label"], inplace=True)

    if len(merged) < min_samples:
        logger.warning(f"合併後樣本不足: {len(merged)} < {min_samples}")
        return None

    # #H48: 動態計算 IC，自動決定是否反轉（避免硬編碼過期問題）
    from scipy import stats as _stats
    import json as _json
    merged = merged.copy()
    ic_map = {}
    NEG_IC_FEATS = []
    labels_arr = merged["label"].astype(float).values
    for col in FEATURE_COLS:
        feat_arr = merged[col].astype(float).values
        mask = ~(np.isnan(feat_arr) | np.isnan(labels_arr))
        if mask.sum() > 30:
            corr, pval = _stats.spearmanr(feat_arr[mask], labels_arr[mask])
            ic_map[col] = float(corr)
            if corr < 0:
                NEG_IC_FEATS.append(col)
                merged[col] = -merged[col]
        else:
            ic_map[col] = 0.0
    # 保存 IC signs 供 predictor.py 推論時使用
    import os as _os
    _os.makedirs("model", exist_ok=True)
    with open("model/ic_signs.json", "w") as _f:
        _json.dump({"neg_ic_feats": NEG_IC_FEATS, "ic_map": ic_map}, _f, indent=2)
    logger.info(f"動態 IC 計算完成: {ic_map}")
    logger.info(f"NEG_IC 反轉特徵: {NEG_IC_FEATS}")

    X = merged[FEATURE_COLS]
    y = merged["label"].astype(int)
    logger.info(f"載入訓練資料: {len(X)} 筆, {len(FEATURE_COLS)} features")
    return X, y


LABEL_MAP = {-1: 0, 0: 1, 1: 2}   # XGBoost needs 0-based class indices
LABEL_MAP_INV = {0: -1, 1: 0, 2: 1}


def encode_labels(y: pd.Series) -> pd.Series:
    """Map -1/0/1 → 0/1/2 for XGBoost multi:softprob."""
    return y.map(LABEL_MAP).fillna(1).astype(int)


def decode_label(pred: int) -> int:
    """Map 0/1/2 → -1/0/1."""
    return LABEL_MAP_INV.get(pred, 0)


def train_xgboost(
    X: pd.DataFrame, y: pd.Series, params: Optional[dict] = None
) -> xgb.XGBClassifier:
    """訓練 XGBoost 3-class（跌/持平/漲）。"""
    # Re-encode if still in -1/0/1 space
    if y.min() < 0:
        y = encode_labels(y)

    dist = y.value_counts().sort_index().to_dict()
    logger.info(f"Class dist (encoded): {dist}")

    if params is None:
        params = {
            "n_estimators": 150,
            "max_depth": 3,
            "learning_rate": 0.03,
            "subsample": 0.6,
            "colsample_bytree": 0.7,
            "reg_alpha": 2.0,
            "reg_lambda": 5.0,
            "min_child_weight": 15,
            "objective": "multi:softprob",
            "num_class": 3,
            "eval_metric": "mlogloss",
            "random_state": 42,
        }

    model = xgb.XGBClassifier(**params)
    model.fit(X, y)
    logger.info("XGBoost v3 3-class 訓練完成")
    return model


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
    logger.info("開始模型訓練 v3...")
    loaded = load_training_data(session, min_samples=50)
    if loaded is None:
        return False
    X, y = loaded
    y_enc = encode_labels(y)  # -1/0/1 → 0/1/2 for XGBoost
    model = train_xgboost(X, y_enc)
    save_model(model)
    imp = dict(zip(FEATURE_COLS, model.feature_importances_.tolist()))
    logger.info(f"特徵重要性: {imp}")

    # Save metrics to model_metrics table
    try:
        from sklearn.model_selection import TimeSeriesSplit, cross_val_score
        from datetime import datetime
        import sqlite3
        train_acc = float((model.predict(X) == y_enc).mean())
        tscv = TimeSeriesSplit(n_splits=5)
        cv_scores = cross_val_score(model, X, y_enc, cv=tscv, scoring="accuracy")
        cv_acc = float(cv_scores.mean())
        cv_std = float(cv_scores.std())
        db = sqlite3.connect("poly_trader.db")
        cur = db.cursor()
        cur.execute("""
            INSERT INTO model_metrics (timestamp, train_accuracy, cv_accuracy, cv_std, n_features, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.utcnow().isoformat(), train_acc, cv_acc, cv_std, len(FEATURE_COLS), "auto-train"))
        db.commit()
        db.close()
        logger.info(f"模型指標: Train={train_acc:.3f}, CV={cv_acc:.3f}±{cv_std:.3f}")
    except Exception as e:
        logger.warning(f"無法保存 model_metrics: {e}")

    return True
