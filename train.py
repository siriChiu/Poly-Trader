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

def load_training_data(session: Session, min_samples: int = 100) -> Optional[Tuple[pd.DataFrame, pd.Series]]:
    """
    從資料庫提取特徵與標籤。
    特徵來自 features_normalized，標籤來自 labels 表（by timestamp）。
    """
    # 取特徵
    features_query = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp)
    rows = features_query.all()
    if not rows:
        logger.error("資料庫中無特徵數據")
        return None

    feature_data = []
    for r in rows:
        feature_data.append({
            "timestamp": r.timestamp,
            "feat_eye_dist": r.feat_eye_dist,
            "feat_ear_zscore": r.feat_ear_zscore,
            "feat_nose_sigmoid": r.feat_nose_sigmoid,
            "feat_tongue_pct": r.feat_tongue_pct,
            "feat_body_roc": r.feat_body_roc
        })
    feat_df = pd.DataFrame(feature_data)

    # 取標籤
    labels_query = session.query(Labels).order_by(Labels.feature_timestamp)
    label_rows = labels_query.all()
    if not label_rows:
        logger.error("資料庫中無標籤數據，請先執行 labeling")
        return None

    label_data = []
    for r in label_rows:
        label_data.append({
            "timestamp": r.feature_timestamp,
            "label": r.label,
            "future_return_pct": r.future_return_pct
        })
    label_df = pd.DataFrame(label_data)

    # merge by timestamp
    merged = pd.merge(feat_df, label_df, on="timestamp", how="inner").dropna()
    if len(merged) < min_samples:
        logger.warning(f"樣本不足：{len(merged)} < {min_samples}")
        return None

    X = merged[["feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid", "feat_tongue_pct", "feat_body_roc"]]
    y = merged["label"]
    logger.info(f"載入訓練數據完成：{len(X)} 筆，正样例比例={y.mean():.2%}")
    return X, y

def train_xgboost(X: pd.DataFrame, y: pd.Series, params: Optional[dict] = None) -> xgb.XGBClassifier:
    if params is None:
        params = {
            "n_estimators": 100,
            "max_depth": 4,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "use_label_encoder": False,
            "eval_metric": "logloss",
            "random_state": 42
        }
    model = xgb.XGBClassifier(**params)
    model.fit(X, y)
    logger.info("XGBoost 模型訓練完成")
    return model

def save_model(model, path: str = MODEL_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"模型已保存至：{path}")

def load_model(path: str = MODEL_PATH):
    if not os.path.exists(path):
        logger.error(f"模型文件不存在：{path}")
        return None
    with open(path, "rb") as f:
        model = pickle.load(f)
    logger.info(f"模型已從 {path} 載入")
    return model

def run_training(session: Session) -> bool:
    """
    執行完整訓練流程。
    Returns: True 若成功。
    """
    logger.info("開始模型訓練流程...")
    loaded = load_training_data(session)
    if loaded is None:
        logger.error("訓練數據加載失敗，請確保特徵數據已就緒")
        return False
    X, y = loaded

    # TODO: 真實標籤生成邏輯需補充
    if y.isnull().any() or (y == 0).all():
        logger.warning("標籤為空或全為零，訓練可能無意義")

    model = train_xgboost(X, y)
    save_model(model)
    logger.info("訓練完成")
    return True

if __name__ == "__main__":
    # 此處需手動創建 Session 才能執行
    print("Train 模組載入成功。請在應用程式中傳入 SQLAlchemy Session 執行 run_training。")
