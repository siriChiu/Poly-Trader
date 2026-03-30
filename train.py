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
    from sqlalchemy import text

    # 使用 SQL 直接 JOIN，避免 pandas 時間戳精度問題
    query = text("""
        SELECT
            f.feat_eye_dist,
            f.feat_ear_zscore,
            f.feat_nose_sigmoid,
            f.feat_tongue_pct,
            f.feat_body_roc,
            l.label
        FROM features_normalized f
        INNER JOIN labels l
            ON CAST(f.timestamp AS INTEGER) = CAST(l.timestamp AS INTEGER)
            OR strftime('%Y-%m-%d %H:00:00', f.timestamp) = strftime('%Y-%m-%d %H:00:00', l.timestamp)
        WHERE f.feat_eye_dist IS NOT NULL
          AND f.feat_nose_sigmoid IS NOT NULL
          AND l.label IS NOT NULL
    """)

    result = session.execute(query)
    rows = result.fetchall()

    if not rows:
        logger.error("SQL JOIN 無結果，嘗試 pandas merge...")

        # Fallback: pandas merge with rounded timestamps
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
                "ts_hour": r.timestamp.replace(minute=0, second=0, microsecond=0),
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
                "ts_hour": r.timestamp.replace(minute=0, second=0, microsecond=0),
                "label": r.label,
            }
            for r in label_rows
        ])

        merged = pd.merge(feat_df, label_df, on="ts_hour", how="inner")
        merged.dropna(subset=FEATURE_COLS + ["label"], inplace=True)

        if len(merged) < min_samples:
            logger.warning(f"合併後樣本不足: {len(merged)} < {min_samples}")
            return None

        X = merged[FEATURE_COLS]
        y = merged["label"].astype(int)
    else:
        df = pd.DataFrame(rows, columns=FEATURE_COLS + ["label"])
        df.dropna(inplace=True)

        if len(df) < min_samples:
            logger.warning(f"樣本不足: {len(df)} < {min_samples}")
            return None

        X = df[FEATURE_COLS]
        y = df["label"].astype(int)

    logger.info(f"載入訓練資料: {len(X)} 筆, 正樣本比例: {y.mean():.2%}")
    return X, y


def train_xgboost(
    X: pd.DataFrame, y: pd.Series, params: Optional[dict] = None
) -> xgb.XGBClassifier:
    """訓練 XGBoost 分類器"""
    if params is None:
        params = {
            "n_estimators": 100,
            "max_depth": 4,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "eval_metric": "logloss",
            "random_state": 42,
        }
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
