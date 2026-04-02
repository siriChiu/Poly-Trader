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
BASE_FEATURE_COLS = [
    "feat_eye", "feat_ear", "feat_nose",
    "feat_tongue", "feat_body", "feat_pulse",
    "feat_aura", "feat_mind",
    "feat_whisper", "feat_tone", "feat_chorus", "feat_hype",
    "feat_oracle", "feat_shock", "feat_tide", "feat_storm",
]
LAG_STEPS = [12, 48, 288]
LAG_FEATURE_COLS = [f"{col}_lag{lag}" for col in BASE_FEATURE_COLS for lag in LAG_STEPS]
# FEATURE_COLS: 8 base only (legacy compat). Full feature list = BASE + LAG when model supports it.
FEATURE_COLS = BASE_FEATURE_COLS

# Confidence thresholds for trade filtering
CONFIDENCE_HIGH = 0.7   # Only BUY when prob > 0.7
CONFIDENCE_LOW = 0.3    # Only SELL/HOLD when prob < 0.3


class XGBoostPredictor:
    def __init__(self, model):
        # model can be a dict (new format) or XGBClassifier (legacy)
        if isinstance(model, dict):
            self._clf = model.get("clf")
            self._imputer = model.get("imputer")
            self._neg_ic_feats = set(model.get("neg_ic_feats", []))
        else:
            self._clf = model
            self._imputer = None
            self._neg_ic_feats = None
        self.model = model

    def _get_neg_ic_feats(self):
        if self._neg_ic_feats is not None:
            return self._neg_ic_feats
        import json as _json, os as _os
        _ic_path = "model/ic_signs.json"
        if _os.path.exists(_ic_path):
            with open(_ic_path) as _f:
                return set(_json.load(_f).get("neg_ic_feats", []))
        return {"feat_eye_dist", "feat_ear_zscore", "feat_body_roc", "feat_aura", "feat_pulse", "feat_mind"}

    def _get_proba(self, features: Dict):
        import pandas as pd
        NEG_IC_FEATS = self._get_neg_ic_feats()
        # Determine which feature columns the model expects
        # Priority: (1) model dict's 'feature_names', (2) clf.feature_names_in_, (3) BASE_FEATURE_COLS
        if isinstance(self.model, dict) and self.model.get('feature_names'):
            all_feat_cols = list(self.model['feature_names'])
        else:
            try:
                fn = self._clf.feature_names_in_
                all_feat_cols = list(fn) if fn is not None else BASE_FEATURE_COLS
            except Exception:
                all_feat_cols = BASE_FEATURE_COLS
        legacy_map = {
            "feat_eye_dist": "feat_eye",
            "feat_ear_zscore": "feat_ear",
            "feat_nose_sigmoid": "feat_nose",
            "feat_tongue_pct": "feat_tongue",
            "feat_body_roc": "feat_body",
        }
        def _feat(col):
            key = legacy_map.get(col, col)
            val = features.get(key, features.get(col, 0))
            return 0 if val is None else val
        adjusted = {col: (-_feat(col) if col in NEG_IC_FEATS else _feat(col)) for col in all_feat_cols}
        X = pd.DataFrame([adjusted]).fillna(0)
        if self._imputer is not None:
            try:
                X = pd.DataFrame(self._imputer.transform(X), columns=X.columns)
            except Exception:
                pass
        return self._clf.predict_proba(X)[0]

    def predict_proba(self, features: Dict) -> float:
        proba = self._get_proba(features)
        # 3-class: proba=[P(down), P(neutral), P(up)]  (encoded: 0=down, 1=neutral, 2=up)
        if len(proba) == 3:
            return float(proba[2])  # confidence of "up" signal
        return float(proba[1]) if len(proba) > 1 else float(proba[0])

    def predict_signal(self, features: Dict) -> dict:
        """返回完整3-class信號：down/neutral/up 及各機率。"""
        proba = self._get_proba(features)
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
    """Load latest features including lag features (for 32-feature model support)."""
    max_lag = max(LAG_STEPS) + 1  # need 289 rows for lag288
    rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).limit(max_lag).all()
    if not rows:
        return None
    # rows[0] is the latest
    latest = rows[0]
    features = {
        "timestamp": latest.timestamp,
        "feat_eye": getattr(latest, "feat_eye", None),
        "feat_ear": getattr(latest, "feat_ear", None),
        "feat_nose": getattr(latest, "feat_nose", None),
        "feat_tongue": getattr(latest, "feat_tongue", None),
        "feat_body": getattr(latest, "feat_body", None),
        "feat_pulse": getattr(latest, "feat_pulse", None),
        "feat_aura": getattr(latest, "feat_aura", None),
        "feat_mind": getattr(latest, "feat_mind", None),
        "feat_whisper": getattr(latest, "feat_whisper", None),
        "feat_tone": getattr(latest, "feat_tone", None),
        "feat_chorus": getattr(latest, "feat_chorus", None),
        "feat_hype": getattr(latest, "feat_hype", None),
        "feat_oracle": getattr(latest, "feat_oracle", None),
        "feat_shock": getattr(latest, "feat_shock", None),
        "feat_tide": getattr(latest, "feat_tide", None),
        "feat_storm": getattr(latest, "feat_storm", None),
    }
    # Compute lag features: rows are DESC, so rows[lag] is `lag` steps ago
    for col in BASE_FEATURE_COLS:
        for lag in LAG_STEPS:
            lag_col = f"{col}_lag{lag}"
            if lag < len(rows):
                features[lag_col] = getattr(rows[lag], col, None)
            else:
                features[lag_col] = None  # Not enough history
    return features


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
