"""
模型訓練模組：載入歷史特徵與標籤，訓練 XGBoost 分類模型
此為框架實現，後續需準備訓練數據。
"""

import os
import pickle
from typing import Optional, Tuple
import pandas as pd
import numpy as np
import xgboost as xgb
from sqlalchemy.orm import Session
from database.models import FeaturesNormalized, TradeHistory
from utils.logger import setup_logger

logger = setup_logger(__name__)

MODEL_PATH = "model/xgb_model.pkl"

def load_training_data(session: Session, min_samples: int = 100) -> Optional[Tuple[pd.DataFrame, pd.Series]]:
    """
    從資料庫提取特徵與標籤。
    標籤定義：假設我們用未來 24 小時的價格變動方向作為二元標籤（1=上漲，0=下跌）。
    由於 Currently 缺乏價格歷史，此函數先返回特徵 DataFrame；標籤部分需後續設計。
    """
    # 取 FeaturesNormalized 全部或部分
    features_query = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp)
    rows = features_query.all()
    if not rows:
        logger.error("資料庫中無特徵數據")
        return None

    # 構建特徵 DataFrame
    data = []
    for r in rows:
        data.append({
            "timestamp": r.timestamp,
            "feat_eye_dist": r.feat_eye_dist,
            "feat_ear_zscore": r.feat_ear_zscore,
            "feat_nose_sigmoid": r.feat_nose_sigmoid,
            "feat_tongue_pct": r.feat_tongue_pct,
            "feat_body_roc": r.feat_body_roc
        })
    df = pd.DataFrame(data)
    df.dropna(inplace=True)  # 簡化：去除缺失
    if len(df) < min_samples:
        logger.warning(f"特徵樣本不足：{len(df)} < {min_samples}，仍需收集數據")
        return None

    # TODO: 提取對應的標籤
    # 目前返回特徵與空標籤 Series 作為佔位符
    logger.info(f"載入特徵完成，樣本數：{len(df)}")
    return df, pd.Series([0] * len(df))  # 佔位符

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
