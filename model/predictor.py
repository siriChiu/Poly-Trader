"""
模型預測模組 v3 — IC-validated features + confidence-based filtering
Only trade when model confidence > 0.7 or < 0.3
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
FEATURE_COLS = [
    "feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid",
    "feat_tongue_pct", "feat_body_roc", "feat_pulse",
    "feat_aura", "feat_mind",
]

# Confidence thresholds for trade filtering
CONFIDENCE_HIGH = 0.7   # Only BUY when prob > 0.7
CONFIDENCE_LOW = 0.3    # Only SELL/HOLD when prob < 0.3


class XGBoostPredictor:
    def __init__(self, model):
        self.model = model

    def predict_proba(self, features: Dict) -> float:
        import pandas as pd
        # IC 反轉：與 train.py 保持一致，負 IC 特徵取反
        NEG_IC_FEATS = {"feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid", "feat_tongue_pct", "feat_body_roc", "feat_pulse", "feat_aura"}
        adjusted = {col: (-features.get(col, 0) if col in NEG_IC_FEATS else features.get(col, 0)) for col in FEATURE_COLS}
        X = pd.DataFrame([adjusted]).fillna(0)
        proba = self.model.predict_proba(X)[0]
        # 3-class: proba=[P(down), P(neutral), P(up)]  (encoded: 0=down, 1=neutral, 2=up)
        if len(proba) == 3:
            return float(proba[2])  # confidence of "up" signal
        return float(proba[1]) if len(proba) > 1 else float(proba[0])

    def predict_signal(self, features: Dict) -> dict:
        """返回完整3-class信號：down/neutral/up 及各機率。"""
        import pandas as pd
        NEG_IC_FEATS = {"feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid", "feat_tongue_pct", "feat_body_roc", "feat_pulse", "feat_aura"}
        adjusted = {col: (-features.get(col, 0) if col in NEG_IC_FEATS else features.get(col, 0)) for col in FEATURE_COLS}
        X = pd.DataFrame([adjusted]).fillna(0)
        proba = self.model.predict_proba(X)[0]
        if len(proba) == 3:
            labels = ["down", "neutral", "up"]
            pred_idx = int(proba.argmax())
            return {"signal": labels[pred_idx], "proba": dict(zip(labels, [float(p) for p in proba]))}
        # fallback binary
        p_up = float(proba[1]) if len(proba) > 1 else float(proba[0])
        return {"signal": "up" if p_up > 0.5 else "down", "proba": {"down": 1-p_up, "up": p_up}}


class DummyPredictor:
    def predict_proba(self, features: Dict) -> float:
        vals = [features.get(c, 0) for c in FEATURE_COLS if features.get(c) is not None]
        if not vals:
            return 0.5
        score = np.mean(vals)
        return float(1 / (1 + np.exp(-score)))


def load_predictor():
    if os.path.exists(MODEL_PATH):
        try:
            import pickle
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            return XGBoostPredictor(model)
        except Exception as e:
            logger.warning(f"模型載入失敗: {e}")
    return DummyPredictor()


def load_latest_features(session: Session) -> Optional[Dict]:
    row = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).first()
    if not row:
        return None
    return {
        "timestamp": row.timestamp,
        "feat_eye_dist": row.feat_eye_dist,
        "feat_ear_zscore": row.feat_ear_zscore,
        "feat_nose_sigmoid": row.feat_nose_sigmoid,
        "feat_tongue_pct": row.feat_tongue_pct,
        "feat_body_roc": row.feat_body_roc,
        "feat_pulse": row.feat_pulse,
        "feat_aura": row.feat_aura,
        "feat_mind": row.feat_mind,
    }


def predict(session: Session, predictor=None) -> Optional[Dict]:
    features = load_latest_features(session)
    if not features:
        return None
    if predictor is None:
        predictor = load_predictor()

    confidence = predictor.predict_proba(features)

    # Confidence-based signal
    if confidence > CONFIDENCE_HIGH:
        signal = "BUY"
        confidence_level = "HIGH"
    elif confidence < CONFIDENCE_LOW:
        signal = "SELL"
        confidence_level = "HIGH"
    elif 0.45 < confidence < 0.55:
        signal = "HOLD"
        confidence_level = "LOW"
    else:
        signal = "HOLD"
        confidence_level = "MEDIUM"

    result = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "features": features,
        "confidence": confidence,
        "signal": signal,
        "confidence_level": confidence_level,
        "should_trade": confidence_level == "HIGH",
        "model_type": type(predictor).__name__,
    }
    logger.info(f"Prediction: conf={confidence:.4f}, signal={signal}, level={confidence_level}")
    return result
