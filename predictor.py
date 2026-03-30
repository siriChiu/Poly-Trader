"""
模型預測模組：載入 XGBoost 權重並輸出信心分數
目前實作 Dummy Predictor 作為占位符，後續可替換為真實模型。
"""

from typing import Optional, Dict
from datetime import datetime
import numpy as np
from sqlalchemy.orm import Session
from database.models import FeaturesNormalized
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DummyPredictor:
    """
    臨時用的 dummy 模型，基於最近的特徵計算一個虛擬信心分數。
    用於驗證整個預測流程。
    """
    def predict(self, features: Dict) -> float:
        """
        返回 0~1 之間的信心分數。
        策略：取各特徵的加權和，再經 sigmoid 縮放。
        """
        weights = {
            "feat_eye_dist": 0.20,
            "feat_ear_zscore": 0.20,
            "feat_nose_sigmoid": 0.20,
            "feat_tongue_pct": 0.20,
            "feat_body_roc": 0.20
        }
        score = 0.0
        total_weight = 0.0
        for key, w in weights.items():
            val = features.get(key)
            if val is not None:
                # 某些特徵可為正/負，直接加權
                score += val * w
                total_weight += w
        if total_weight > 0:
            score = score / total_weight  # 歸一化到實際權重範圍
        # 使用 sigmoid 將分數映射到 0~1
        prob = 1 / (1 + np.exp(-score))
        return float(prob)

def load_latest_features(session: Session, limit: int = 1) -> Optional[Dict]:
    """
    從資料庫讀取最新的特徵。
    """
    query = session.query(FeaturesNormalized).order_by(
        FeaturesNormalized.timestamp.desc()
    ).limit(limit)
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
        "feat_body_roc": row.feat_body_roc
    }

def predict(session: Session, predictor: Optional[DummyPredictor] = None) -> Optional[Dict]:
    """
    執行預測：
    1. 讀取最新特徵
    2. 使用模型產出信心分數
    3. 返回結果（包含預測時間、分數、特徵）
    """
    logger.info("開始執行模型預測...")
    features = load_latest_features(session)
    if not features:
        logger.error("無可用的特徵數據")
        return None

    if predictor is None:
        predictor = DummyPredictor()

    confidence = predictor.predict(features)
    result = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "features": features,
        "confidence": confidence,
        "signal": "BUY" if confidence > 0.5 else "HOLD"  # 簡單閾值
    }
    logger.info(f"預測完成：信心分數={confidence:.4f}, 信號={result['signal']}")
    return result

if __name__ == "__main__":
    print("Predictor 模組載入成功。請在初始化 SQLAlchemy Session 後調用 predict(session)。")
