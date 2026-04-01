"""
模型訓練模組：載入歷史特徵與標籤，訓練 XGBoost 分類模型
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
    "feat_eye_dist",
    "feat_ear_zscore",
    "feat_nose_sigmoid",
    "feat_tongue_pct",
    "feat_body_roc",
]


def load_training_data(
    session: Session, min_samples: int = 50
) -> Optional[Tuple[pd.DataFrame, pd.Series]]:
    """
    從資料庫提取特徵與 Labels 表的標籤。
    以時間戳 JOIN（向下取整到小時以匹配）。
    """
    # 使用 pandas merge_asof 做最近時間匹配（避免 SQL cross-join）
    feat_rows = (
        session.query(FeaturesNormalized)
        .order_by(FeaturesNormalized.timestamp)
        .all()
    )
    label_rows = (
        session.query(Labels)
        .order_by(Labels.timestamp)
        .all()
    )

    feat_df = pd.DataFrame([
        {
            "timestamp": r.timestamp,
            "feat_eye_dist": r.feat_eye_dist,
            "feat_ear_zscore": r.feat_ear_zscore,
            "feat_nose_sigmoid": r.feat_nose_sigmoid,
            "feat_tongue_pct": r.feat_tongue_pct,
            "feat_body_roc": r.feat_body_roc,
        }
        for r in feat_rows
    ])

    label_df = pd.DataFrame([
        {
            "timestamp": r.timestamp,
            "label": r.label,
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
    merged.dropna(subset=FEATURE_COLS + ["label"], inplace=True)

    if len(merged) < min_samples:
        logger.warning(f"合併後樣本不足: {len(merged)} < {min_samples}")
        return None

    X = merged[FEATURE_COLS]
    y = merged["label"].astype(int)
    logger.info(f"載入訓練資料: {len(X)} 筆 (merge_asof, 10min tolerance)")
    return X, y


def train_xgboost(
    X: pd.DataFrame, y: pd.Series, params: Optional[dict] = None
) -> xgb.XGBClassifier:
    """訓練 XGBoost 分類器，自動處理類別不平衡。"""
    # 計算類別不平衡比例
    n_neg = (y == 0).sum()
    n_pos = (y == 1).sum()
    scale_pos_weight = n_neg / max(n_pos, 1)

    if params is None:
        params = {
            "n_estimators": 100,
            "max_depth": 4,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "eval_metric": "logloss",
            "scale_pos_weight": scale_pos_weight,
            "random_state": 42,
        }
    else:
        params.setdefault("scale_pos_weight", scale_pos_weight)

    logger.info(f"類別平衡: neg={n_neg}, pos={n_pos}, scale_pos_weight={scale_pos_weight:.2f}")
    model = xgb.XGBClassifier(**params)
    model.fit(X, y)
    logger.info("XGBoost 模型訓練完成")
    return model


def save_model(model, path: str = MODEL_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"模型已保存至: {path}")


def load_model(path: str = MODEL_PATH):
    if not os.path.exists(path):
        logger.error(f"模型文件不存在: {path}")
        return None
    with open(path, "rb") as f:
        model = pickle.load(f)
    logger.info(f"模型已從 {path} 載入")
    return model


def run_training(session: Session) -> bool:
    """執行完整訓練流程。"""
    logger.info("開始模型訓練流程...")
    loaded = load_training_data(session, min_samples=50)
    if loaded is None:
        logger.error("訓練數據加載失敗")
        return False

    X, y = loaded
    model = train_xgboost(X, y)
    save_model(model)

    # 輸出特徵重要性
    importances = dict(zip(FEATURE_COLS, model.feature_importances_.tolist()))
    logger.info(f"特徵重要性: {importances}")

    logger.info("訓練完成")
    return True
