"""
模型預測模組：載入 XGBoost 權重並輸出信心分數
優先載入訓練好的模型，若不存在則使用 DummyPredictor。
"""

import os
from typing import Optional, Dict
from datetime import datetime
import numpy as np
from sqlalchemy.orm import Session
from database.models import FeaturesNormalized
from utils.logger import setup_logger

logger = setup_logger(__name__)

MODEL_PATH = "model/xgb_model.pkl"
# Match train.py: exclude feat_mind (constant), feat_aura (near-constant)
FEATURE_COLS = [
    "feat_eye_dist",
    "feat_ear_zscore",
    "feat_nose_sigmoid",
    "feat_tongue_pct",
    "feat_body_roc",
    "feat_pulse",
]


class XGBoostPredictor:
    """使用訓練好的 XGBoost 模型進行預測。"""

    def __init__(self, model):
        self.model = model
        logger.info("XGBoost 模型已載入")

    def predict(self, features: Dict) -> float:
        """返回 0~1 之間的信心分數（上漲機率）。"""
        import pandas as pd

        X = pd.DataFrame([{col: features.get(col) for col in FEATURE_COLS}])
        X = X.fillna(0)

        proba = self.model.predict_proba(X)[0]
        # proba[1] = 上漲機率
        return float(proba[1]) if len(proba) > 1 else float(proba[0])


class DummyPredictor:
    """備用：等權重 sigmoid。"""

    def predict(self, features: Dict) -> float:
        weights = {col: 0.20 for col in FEATURE_COLS}
        score = 0.0
        total_weight = 0.0
        for key, w in weights.items():
            val = features.get(key)
            if val is not None:
                score += val * w
                total_weight += w
        if total_weight > 0:
            score = score / total_weight
        prob = 1 / (1 + np.exp(-score))
        return float(prob)


def load_predictor() -> object:
    """載入 XGBoost 模型，若不存在則返回 DummyPredictor。"""
    if os.path.exists(MODEL_PATH):
        try:
            import pickle
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            return XGBoostPredictor(model)
        except Exception as e:
            logger.warning(f"載入 XGBoost 模型失敗: {e}，使用 DummyPredictor")

    logger.info("未找到訓練模型，使用 DummyPredictor")
    return DummyPredictor()


def load_latest_features(session: Session, limit: int = 1) -> Optional[Dict]:
    """從資料庫讀取最新的特徵。"""
    query = (
        session.query(FeaturesNormalized)
        .order_by(FeaturesNormalized.timestamp.desc())
        .limit(limit)
    )
    rows = query.all()
    if not rows:
        return None
    row = rows[0]
    return {
        "timestamp": row.timestamp,
        "feat_eye_dist": row.feat_eye_dist,
        "feat_ear_zscore": row.feat_ear_zscore,
        "feat_nose_sigmoid": row.feat_nose_sigmoid,
        "feat_tongue_pct": row.feat_tongue_pct,
        "feat_body_roc": row.feat_body_roc,
    }


def predict(session: Session, predictor=None) -> Optional[Dict]:
    """執行預測：讀取特徵 → 模型產出信心分數 → 返回結果。"""
    logger.info("開始執行模型預測...")
    features = load_latest_features(session)
    if not features:
        logger.error("無可用的特徵數據")
        return None

    if predictor is None:
        predictor = load_predictor()

    confidence = predictor.predict(features)

    # 輸出特徵重要性（若為 XGBoost）
    importance_info = ""
    if isinstance(predictor, XGBoostPredictor):
        try:
            imp = dict(zip(FEATURE_COLS, predictor.model.feature_importances_.tolist()))
            top = sorted(imp.items(), key=lambda x: -x[1])[:2]
            importance_info = f", top_features={top[0][0]}({top[0][1]:.2f}), {top[1][0]}({top[1][1]:.2f})"
        except Exception:
            pass

    signal = "BUY" if confidence > 0.5 else "HOLD"

    result = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "features": features,
        "confidence": confidence,
        "signal": signal,
        "model_type": type(predictor).__name__,
    }
    logger.info(f"預測完成: confidence={confidence:.4f}, signal={signal}{importance_info}")
    return result
