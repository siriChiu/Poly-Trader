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

# Confidence thresholds for trade filtering — model predicts sell-win probability
CONFIDENCE_HIGH = 0.7   # SELL (short) — high confidence price will drop (sell-win)
CONFIDENCE_LOW = 0.3    # BUY/HOLD — low confidence, price likely rising
REGIME_THRESHOLD_BIAS = {
    'trend': -0.03,
    'chop': 0.04,
    'panic': -0.01,
    'event': 0.02,
    'normal': 0.0,
}


class XGBoostPredictor:
    def __init__(self, model):
        # model can be a dict (new format) or XGBClassifier (legacy)
        self._feature_names = None
        self._imputer = None
        self._neg_ic_feats = None
        self._calibration = {"kind": "none"}
        self._regime_threshold_bias = REGIME_THRESHOLD_BIAS.copy()

        if isinstance(model, dict):
            self._clf = model.get("clf")
            self._imputer = model.get("imputer")
            self._neg_ic_feats = set(model.get("neg_ic_feats", []))
            self._calibration = model.get("calibration", {"kind": "none"})
            self._feature_names = model.get("feature_names")
            self._regime_threshold_bias = model.get("regime_threshold_bias", REGIME_THRESHOLD_BIAS.copy())
        else:
            self._clf = model
        self.model = model

    def _apply_calibration(self, score: float) -> float:
        cal = self._calibration or {"kind": "none"}
        kind = cal.get("kind", "none")
        score = float(np.clip(score, 1e-6, 1 - 1e-6))
        if kind == "isotonic":
            try:
                xs = np.asarray(cal.get("isotonic_x", []), dtype=float)
                ys = np.asarray(cal.get("isotonic_y", []), dtype=float)
                if len(xs) >= 2 and len(xs) == len(ys):
                    return float(np.interp(score, xs, ys, left=ys[0], right=ys[-1]))
            except Exception:
                pass
        elif kind == "logit_affine":
            mu = float(cal.get("mu", 0.0))
            sigma = float(cal.get("sigma", 1.0) or 1.0)
            logit = np.log(score / (1 - score))
            z = (logit - mu) / sigma
            return float(1 / (1 + np.exp(-z)))
        return score

    def _get_neg_ic_feats(self):
        if self._neg_ic_feats is not None:
            return self._neg_ic_feats
        import json as _json, os as _os
        _ic_path = "model/ic_signs.json"
        if _os.path.exists(_ic_path):
            with open(_ic_path) as _f:
                return set(_json.load(_f).get("neg_ic_feats", []))
        return {"feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body", "feat_aura", "feat_pulse", "feat_mind"}

    def _get_proba(self, features: Dict):
        import pandas as pd
        NEG_IC_FEATS = self._get_neg_ic_feats()
        # Determine which feature columns the model expects
        # Priority: (1) model dict's 'feature_names', (2) clf.feature_names_in_, (3) BASE_FEATURE_COLS
        if self._feature_names:
            all_feat_cols = list(self._feature_names)
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
            raw = float(proba[2])  # confidence of "up" signal
        elif len(proba) > 1:
            raw = float(proba[1])
        else:
            raw = float(proba[0])
        return self._apply_calibration(raw)

    def _regime_bias(self, regime_label: str | None) -> float:
        if not regime_label:
            return 0.0
        return float(self._regime_threshold_bias.get(str(regime_label), 0.0))

    def predict_signal(self, features: Dict) -> dict:
        """返回完整3-class信號：down/neutral/up 及各機率。"""
        proba = self._get_proba(features)
        regime = features.get("regime_label") if isinstance(features, dict) else None
        bias = self._regime_bias(regime)
        if len(proba) == 3:
            labels = ["down", "neutral", "up"]
            pred_idx = int(proba.argmax())
            return {"signal": labels[pred_idx], "proba": dict(zip(labels, [float(p) for p in proba]))}
        # fallback binary
        p_up = float(proba[1]) if len(proba) > 1 else float(proba[0])
        adj = float(np.clip(p_up + bias, 0.0, 1.0))
        return {"signal": "up" if adj > 0.5 else "down", "proba": {"down": 1-adj, "up": adj}, "regime_bias": bias}


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


def _determine_regime(features: Dict) -> str:
    """Determine regime from latest feature values using simple heuristics.
    Mirrors the regime classification in scripts/fix_regimes_h141.py:
    - bear: momentum < -threshold
    - bull: momentum > threshold
    - chop: |momentum| < threshold
    """
    # Use feat_mind (short-term return) and feat_body (momentum) as regime signal
    mind = float(features.get('feat_mind', 0) or 0)
    body = float(features.get('feat_body', 0) or 0)
    momentum = (mind + body) / 2.0

    if momentum < -0.15:
        return 'bear'
    elif momentum > 0.15:
        return 'bull'
    else:
        return 'chop'


def load_predictor():
    """Load global model and per-regime models if available."""
    models = {}

    # Load global model
    global_model = None
    if os.path.exists(MODEL_PATH):
        try:
            import pickle
            with open(MODEL_PATH, "rb") as f:
                global_model = pickle.load(f)
        except Exception as e:
            logger.warning(f"Global model load failed: {e}")

    # Load per-regime models
    regime_path = MODEL_PATH.replace("xgb_model.pkl", "regime_models.pkl")
    if os.path.exists(regime_path):
        try:
            import pickle
            with open(regime_path, "rb") as f:
                regime_models = pickle.load(f)
            if isinstance(regime_models, dict):
                for regime_name, model_data in regime_models.items():
                    models[regime_name] = model_data
            logger.info(f"Per-regime models loaded: {list(models.keys())}")
        except Exception as e:
            logger.warning(f"Per-regime models load failed: {e}")

    return XGBoostPredictor(global_model) if global_model else DummyPredictor(), models


def load_latest_features(session: Session) -> Optional[Dict]:
    """Load latest features including lag features (for 32-feature model support),
    plus VIX, DXY, and cross-features that the model was trained with."""
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
        # P0 #H149-fix1: Include VIX and DXY at inference time (model was trained with them)
        "feat_vix": getattr(latest, "feat_vix", None),
        "feat_dxy": getattr(latest, "feat_dxy", None),
    }
    # Compute lag features: rows are DESC, so rows[lag] is `lag` steps ago
    for col in BASE_FEATURE_COLS:
        for lag in LAG_STEPS:
            lag_col = f"{col}_lag{lag}"
            if lag < len(rows):
                features[lag_col] = getattr(rows[lag], col, None)
            else:
                features[lag_col] = None  # Not enough history

    # P0 #H149-fix2: Compute VIX cross-features at inference time to match training
    vix = features.get("feat_vix") or 0
    eye = features.get("feat_eye") or 0
    pulse = features.get("feat_pulse") or 0
    mind = features.get("feat_mind") or 0
    features["feat_vix_x_eye"] = vix * eye
    features["feat_vix_x_pulse"] = vix * pulse
    features["feat_vix_x_mind"] = vix * mind

    # Cross-sense features matching train.py
    features["feat_mind_x_pulse"] = (mind * pulse)
    features["feat_eye_x_ear"] = (eye * features.get("feat_ear", 0))
    features["feat_nose_x_aura"] = (features.get("feat_nose", 0) * features.get("feat_aura", 0))
    features["feat_eye_x_body"] = eye * (features.get("feat_body", 0))
    features["feat_ear_x_nose"] = (features.get("feat_ear", 0) * features.get("feat_nose", 0))
    features["feat_mind_x_aura"] = mind * (features.get("feat_aura", 0))

    # Regime flag
    regime = features.get("regime_label")
    if regime is None:
        regime = _determine_regime(features)
    features["regime_label"] = regime
    features["feat_regime_flag"] = {"trend": 1.0, "chop": -1.0, "panic": -0.5, "event": 0.5, "normal": 0.0}.get(regime, 0.0)

    # Mean-reversion proxy
    features["feat_mean_rev_proxy"] = mind - (features.get("feat_aura", 0))

    return features


def predict(session: Session, predictor=None, regime_models=None) -> Optional[Dict]:
    features = load_latest_features(session)
    if not features:
        return None
    if predictor is None:
        predictor, regime_models = load_predictor()

    # Per-regime model routing (H145-fix + #H122 chop-abstain ensemble)
    used_model = "global"
    if regime_models and isinstance(features, dict):
        regime = _determine_regime(features)
        if regime in regime_models:
            # Chop regime: if confidence ≈ 50% (random), force abstain
            chop_abort = 0.50
            regime_predictor = XGBoostPredictor(regime_models[regime])
            reg_conf = regime_predictor.predict_proba(features)
            if regime == "chop" and abs(reg_conf - chop_abort) < 0.05:
                return {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "features": features,
                    "confidence": 0.5,
                    "signal": "ABSTAIN",
                    "confidence_level": "ABSTAIN",
                    "should_trade": False,
                    "model_type": "regime_ensemble",
                    "used_model": "regime_chop_abstain",
                }
            # Ensemble: weight regime model 60%, global 40%
            global_conf = predictor.predict_proba(features)
            confidence = 0.6 * reg_conf + 0.4 * global_conf
            used_model = f"regime_{regime}_ensemble"
        else:
            confidence = predictor.predict_proba(features)
    else:
        confidence = predictor.predict_proba(features)
        used_model = "global"

    # Confidence-based signal — model predicts sell-win (short profit)
    # High confidence = price will DROP = SELL/short is profitable
    # Low confidence = price will RISE = don't short, hold or take long
    if confidence > CONFIDENCE_HIGH:
        signal = "SELL"
        confidence_level = "HIGH"
    elif confidence < CONFIDENCE_LOW:
        signal = "BUY"
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
        "used_model": used_model,
    }
    logger.info(f"Prediction: conf={confidence:.4f}, signal={signal}, level={confidence_level}")
    return result
