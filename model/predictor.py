"""
模型預測模組 v3 — IC-validated features + confidence-based filtering
Only trade when model confidence > 0.7 or < 0.3
"""

import os
from typing import Optional, Dict
from datetime import datetime
import numpy as np
from sqlalchemy.orm import Session
from database.models import FeaturesNormalized, Labels
from utils.logger import setup_logger

logger = setup_logger(__name__)

MODEL_PATH = "model/xgb_model.pkl"
# Core 8 senses: IC-validated, non-constant features
BASE_FEATURE_COLS = [
    "feat_eye", "feat_ear", "feat_nose",
    "feat_tongue", "feat_body", "feat_pulse",
    "feat_aura", "feat_mind",
]

# Aux 8 senses: permanently removed from DB — #H380 (HB #206 cleanup)
# feat_whisper, feat_tone, feat_chorus, feat_hype, feat_oracle,
# feat_shock, feat_tide, feat_storm were all constant=0.0, IC=0.0000
# DB columns dropped. Feature counts: 15 alive (8 sensors + VIX + DXY + 6 technicals)
DISABLED_AUX_FEATURES = []
LAG_STEPS = [12, 48, 288]
LAG_FEATURE_COLS = [f"{col}_lag{lag}" for col in BASE_FEATURE_COLS for lag in LAG_STEPS]
# FEATURE_COLS: 8 base only (legacy compat). Full feature list = BASE + LAG when model supports it.
FEATURE_COLS = BASE_FEATURE_COLS

# Confidence thresholds for trade filtering — model predicts sell-win probability
CONFIDENCE_HIGH = 0.7   # SELL (short) — high confidence price will drop (sell-win)
CONFIDENCE_LOW = 0.3    # BUY/HOLD — low confidence, price likely rising

# P0 #H426: Bull regime sell signal inversion
# Bull sell_win=59.4% — model's "sell" signals are WRONG in bull markets
# This means we should INVERT the signal when in a bull regime
# Inverting gives 40.6% → buy_signal wins 59.4% of the time
BULL_SIGNAL_INVERT = True  # flip high-confidence sell → buy in bull regime

# P0 #H420: Circuit breaker — halt trading after N consecutive losses
# sell_win is at 49.90%, 156-streak ongoing — must prevent further damage
CIRCUIT_BREAKER_STREAK = 50  # consecutive sell losses before forced abstain
CIRCUIT_BREAKER_RECENT_WINRATE = 0.35  # if recent 100 win rate < 35%, force abstain
CIRCUIT_BREAKER_WINDOW = 100  # samples to check for win rate floor
REGIME_THRESHOLD_BIAS = {
    'trend': -0.03,
    'chop': 0.04,
    'panic': -0.01,
    'event': 0.02,
    'normal': 0.0,
    # P0 #H379: Bull regime sell suppression — sell signals in bull markets are inverted
    # (sell_win in bull = 60.5% means "sell" = "buy the dip" — don't sell).
    # Raise SELL threshold from 0.70 to 0.85+ (effectively -0.15 bias pulls conf down).
    'bull': -0.15,
    # Bear: slightly lower threshold — sell signals work better in bear (IC=8/23)
    'bear': 0.02,
}


def _time_weighted_ic(session, tau=200):
    """Compute time-weighted IC for the 8 core senses.
    Returns dict of {col_name: ic_value} with exponential decay weights.
    Recent samples get higher weight via exp(-(N-1-i)/tau).
    """
    import numpy as np
    from scipy import stats as _stats
    from database.models import FeaturesNormalized, Labels

    sense_col_names = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue",
                       "feat_body", "feat_pulse", "feat_aura", "feat_mind"]
    sense_cols = [getattr(FeaturesNormalized, c) for c in sense_col_names]

    # Load time-ordered features + labels
    feat_rows = session.query(FeaturesNormalized.timestamp, *sense_cols).order_by(FeaturesNormalized.timestamp).all()
    label_rows = session.query(Labels.timestamp, Labels.label_sell_win).filter(
        Labels.label_sell_win.isnot(None)).order_by(Labels.timestamp).all()

    feat_by_ts = {r[0]: {sense_col_names[i]: r[1+i] for i in range(len(sense_cols))} for r in feat_rows}
    labels_by_ts = {r[0]: int(r[1]) for r in label_rows}
    common_ts = sorted(set(feat_by_ts.keys()) & set(labels_by_ts.keys()))
    N = len(common_ts)
    if N < 10:
        return {col: 0.0 for col in sense_col_names}

    # Exponential decay weights
    weights = np.exp(-(N - 1 - np.arange(N, dtype=float)) / tau)

    ics = {}
    for col in sense_col_names:
        vals = np.array([feat_by_ts[ts].get(col) for ts in common_ts], dtype=float)
        sw = np.array([float(labels_by_ts[ts]) for ts in common_ts])
        mask = ~np.isnan(vals)
        if mask.sum() < 10:
            ics[col] = 0.0
            continue
        vc = vals[mask]; sc = sw[mask]; wc = weights[mask]
        wm_v = np.average(vc, weights=wc)
        wm_s = np.average(sc, weights=wc)
        cov = np.average((vc - wm_v) * (sc - wm_s), weights=wc)
        var_v = np.average((vc - wm_v)**2, weights=wc)
        var_s = np.average((sc - wm_s)**2, weights=wc)
        w_ic = cov / (np.sqrt(var_v * var_s) + 1e-15)
        ics[col] = round(float(w_ic), 4)
    return ics


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


class RegimeAwarePredictor:
    """Wrapper that routes inference to the correct regime-specific model."""

    def __init__(self, global_predictor, regime_models: Dict):
        self._global = global_predictor
        self._regime_models = regime_models  # dict of regime_name -> model_data dict
        # Build XGBoostPredictor wrappers for each regime
        self._regime_predictors = {}
        for regime_name, model_data in regime_models.items():
            self._regime_predictors[regime_name] = XGBoostPredictor(model_data)

    def predict_proba(self, features: Dict) -> float:
        """Route to regime-specific model if available, else global."""
        regime = features.get('regime_label')
        if regime and regime in self._regime_predictors:
            return self._regime_predictors[regime].predict_proba(features)
        return self._global.predict_proba(features)

    def predict_signal(self, features: Dict) -> dict:
        """Route to regime-specific model if available, else global."""
        regime = features.get('regime_label')
        if regime and regime in self._regime_predictors:
            return self._regime_predictors[regime].predict_signal(features)
        return self._global.predict_signal(features)


def load_predictor():
    """Load global model and per-regime models if available.
    Returns a RegimeAwarePredictor (or fallback) plus raw regime_models dict.
    """
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

    global_predictor = XGBoostPredictor(global_model) if global_model else DummyPredictor()
    if models:
        predictor = RegimeAwarePredictor(global_predictor, models)
        logger.info(f"RegimeAwarePredictor active with {len(models)} regime models")
    else:
        predictor = global_predictor
    return predictor, models


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
        # #H380: dead aux features removed from DB (HB #206 cleanup)
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

    # Regime flag — prefer DB regime_label over heuristic (P0 #H379)
    regime = getattr(latest, "regime_label", None)
    if regime is None or regime == "":
        regime = _determine_regime(features)
    features["regime_label"] = regime
    features["feat_regime_flag"] = {"trend": 1.0, "chop": -1.0, "panic": -0.5, "event": 0.5, "normal": 0.0}.get(regime, 0.0)

    # Mean-reversion proxy
    features["feat_mean_rev_proxy"] = mind - (features.get("feat_aura", 0))

    return features


def _check_circuit_breaker(session) -> Optional[Dict]:
    """P0 #H420: Circuit breaker — check for consecutive losses and recent win rate.
    Returns an abort dict if circuit breaker is triggered, None if safe to trade.
    """
    from sqlalchemy import func as _func
    from database.models import Labels

    # Check consecutive sell losses from most recent backwards
    recent_labels = (
        session.query(Labels.label_sell_win)
        .filter(Labels.label_sell_win.isnot(None))
        .order_by(Labels.timestamp.desc())
        .all()
    )

    streak = 0
    for row in recent_labels:
        if not row[0]:
            streak += 1
        else:
            break

    if streak >= CIRCUIT_BREAKER_STREAK:
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "confidence": 0.5,
            "signal": "CIRCUIT_BREAKER",
            "confidence_level": "CIRCUIT_BREAKER",
            "should_trade": False,
            "model_type": "circuit_breaker",
            "reason": f"Consecutive loss streak: {streak} >= {CIRCUIT_BREAKER_STREAK}",
            "streak": streak,
        }

    # Check recent win rate floor
    if len(recent_labels) >= CIRCUIT_BREAKER_WINDOW:
        window_wins = sum(1 for r in recent_labels[:CIRCUIT_BREAKER_WINDOW] if r[0])
        window_wr = window_wins / CIRCUIT_BREAKER_WINDOW
        if window_wr < CIRCUIT_BREAKER_RECENT_WINRATE:
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "confidence": 0.5,
                "signal": "CIRCUIT_BREAKER",
                "confidence_level": "CIRCUIT_BREAKER",
                "should_trade": False,
                "model_type": "circuit_breaker",
                "reason": f"Recent {CIRCUIT_BREAKER_WINDOW}-sample win rate: {window_wr:.2%} < {CIRCUIT_BREAKER_RECENT_WINRATE:.0%}",
                "win_rate": window_wr,
            }

    return None


def predict_with_ic_fusion(session: Session, predictor=None, tau: float = 200) -> Optional[Dict]:
    """Predict using time-weighted IC fusion instead of static model.
    Uses exp decay IC (tau) to weight each sense, then fuses via weighted average.
    Falls back to model-based prediction if fusion fails.

    P0 #H379 fix: Exclude Nose (TW-IC FAIL at -0.0279) and use |TW-IC| >= 0.05
    threshold. Senses below threshold get zero weight — they dilute the strong
    Tongue(+0.532) and Body(+0.505) signals.
    """
    import numpy as np
    from database.models import FeaturesNormalized, Labels
    from datetime import datetime

    # Circuit breaker before fusion
    cb = _check_circuit_breaker(session)
    if cb is not None:
        return cb

    features = load_latest_features(session)
    if not features:
        return None

    tw_ics = _time_weighted_ic(session, tau=tau)

    # Core 8 senses
    sense_cols = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue",
                   "feat_body", "feat_pulse", "feat_aura", "feat_mind"]
    raw_ics = [tw_ics.get(col, 0.0) for col in sense_cols]

    # #H391: Nose TW-IC fails (|-0.028| < 0.05 threshold) — exclude from fusion
    IC_PASS_THRESHOLD = getattr(predict_with_ic_fusion, '_ic_threshold', 0.05)

    # Weight each sense by its recent IC strength, exclude below-threshold
    feat_vals = []
    weights = []
    active_senses = []
    for col, ic in zip(sense_cols, raw_ics):
        val = features.get(col)
        if val is None:
            continue
        abs_ic = abs(ic)
        if abs_ic < IC_PASS_THRESHOLD:
            # #H391: Below-threshold senses get zero weight
            # Previously: min weight 0.01 let Nose dilute Tongue+Body
            continue
        # Flip sign for negative IC senses (align all to sell-win direction)
        aligned = (-val) if ic < 0 else val
        feat_vals.append(aligned)
        weights.append(abs_ic)
        active_senses.append(col)

    feat_arr = np.array(feat_vals, dtype=float)
    weight_arr = np.array(weights, dtype=float)

    if weight_arr.sum() == 0 or len(feat_arr) == 0:
        # Fallback to model
        if predictor is None:
            predictor, _ = load_predictor()
        confidence = predictor.predict_proba(features)
    else:
        # IC-weighted average of aligned senses → logistic transform
        score = np.average(feat_arr, weights=weight_arr)
        confidence = float(1 / (1 + np.exp(-score)))
        # Blend with model prediction (70% fusion, 30% model)
        if predictor is None:
            predictor, _ = load_predictor()
        model_conf = predictor.predict_proba(features)
        confidence = 0.7 * confidence + 0.3 * model_conf

    # Apply regime bias
    regime = features.get("regime_label")
    bias = REGIME_THRESHOLD_BIAS.get(regime, 0.0) if regime else 0.0
    adjusted = float(np.clip(confidence + bias, 0.0, 1.0))

    # P0 #H426: Bull regime signal inversion
    # Bull sell_win=59.4% — selling in bull markets is wrong; invert signal
    if BULL_SIGNAL_INVERT and regime == "bull":
        adjusted = float(np.clip(1.0 - adjusted, 0.0, 1.0))

    # Signal determination
    if adjusted > CONFIDENCE_HIGH:
        signal = "SELL"
        confidence_level = "HIGH"
    elif adjusted < CONFIDENCE_LOW:
        signal = "BUY"
        confidence_level = "HIGH"
    elif 0.45 < adjusted < 0.55:
        signal = "HOLD"
        confidence_level = "LOW"
    else:
        signal = "HOLD"
        confidence_level = "MEDIUM"

    result = {
        "timestamp": datetime.now().isoformat() + "Z",
        "features": features,
        "confidence": adjusted,
        "signal": signal,
        "confidence_level": confidence_level,
        "should_trade": confidence_level == "HIGH",
        "model_type": "ic_fusion_time_weighted_v2_nose_excluded",
        "ic_values": tw_ics,
        "active_senses": active_senses,
        "excluded_senses": [s for s in sense_cols if s not in active_senses],
        "tau": tau,
    }
    return result


def predict(session: Session, predictor=None, regime_models=None) -> Optional[Dict]:
    # P0 #H420: Circuit breaker check before any prediction
    cb = _check_circuit_breaker(session)
    if cb is not None:
        logger.warning(f"CIRCUIT BREAKER TRIGGERED: {cb['reason']}")
        return cb
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
