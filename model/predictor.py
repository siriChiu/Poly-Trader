"""
模型預測模組 v3 — IC-validated features + confidence-based filtering
Only trade when model confidence > 0.7 or < 0.3
"""

import os
import json
from collections import Counter
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import numpy as np
from sqlalchemy.orm import Session
from database.models import FeaturesNormalized, Labels
from utils.logger import setup_logger

logger = setup_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DW_RESULT_PATH = PROJECT_ROOT / "data" / "dw_result.json"

DEFAULT_TARGET_COL = "simulated_pyramid_win"
MODEL_PATH = "model/xgb_model.pkl"
# Canonical inference feature base — must stay in parity with model.train.FEATURE_COLS.
BASE_FEATURE_COLS = [
    # 8 core senses
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue",
    "feat_body", "feat_pulse", "feat_aura", "feat_mind",
    # 2 macro
    "feat_vix", "feat_dxy",
    # technical indicators
    "feat_rsi14", "feat_macd_hist", "feat_atr_pct",
    "feat_vwap_dev", "feat_bb_pct_b", "feat_nw_width",
    "feat_nw_slope", "feat_adx", "feat_choppiness", "feat_donchian_pos",
    # 4H timeframe features
    "feat_4h_bias50", "feat_4h_bias20", "feat_4h_bias200",
    "feat_4h_rsi14", "feat_4h_macd_hist", "feat_4h_bb_pct_b",
    "feat_4h_dist_bb_lower", "feat_4h_ma_order",
    "feat_4h_dist_swing_low", "feat_4h_vol_ratio",
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

# Confidence thresholds for trade filtering — model predicts long-win probability
CONFIDENCE_HIGH = 0.7   # BUY — high confidence price will rise enough for spot-long pyramiding
CONFIDENCE_LOW = 0.3    # HOLD — low confidence, avoid entering
LIVE_MAX_LAYERS = 3
LIVE_REGIME_BIAS200_MIN = -10.0
# Heartbeat #715: bull ALLOW + D rows with very stretched 4H structure were still
# passing the gate even though 19 historical rows at/above this pocket went 0/19.
# Treat this as an explicit ALLOW-lane veto until the gate is retrained with a
# richer structure-aware bucket instead of monotonic "farther from lower band is better".
LIVE_4H_OVEREXTENDED_BB_PCT_B_MIN = 1.0
LIVE_4H_OVEREXTENDED_DIST_BB_LOWER_MIN = 10.0
LIVE_4H_OVEREXTENDED_DIST_SWING_LOW_MIN = 11.0

# P0 #H426: Bull regime signal inversion
# Legacy short-selling logic needed inversion in bull markets.
# For the spot-long target we keep raw confidence (no inversion).
BULL_SIGNAL_INVERT = False  # spot-long target does not need bull-time inversion

# P0 #H420: Circuit breaker — halt trading after N consecutive losses
# spot-long win rate is at 49.90%, 156-streak ongoing — must prevent further damage
CIRCUIT_BREAKER_STREAK = 50  # consecutive long-entry losses before forced abstain
CIRCUIT_BREAKER_RECENT_WINRATE = 0.30  # if recent 50 win rate < 30%, force abstain (HB#234: tightened from 35% at 100-sample)
CIRCUIT_BREAKER_WINDOW = 50  # samples to check for win rate floor (HB#234: reduced from 100 for faster response)
REGIME_THRESHOLD_BIAS = {
    'trend': 0.03,
    'chop': -0.04,
    'panic': -0.08,
    'event': -0.02,
    'normal': 0.0,
    # Bull regime should boost long-win confidence, not suppress it.
    'bull': 0.10,
    # Bear regimes should be more conservative for spot-long entries.
    'bear': -0.05,
}


def _global_ic(session):
    """Compute full-history (unweighted) Spearman IC for the 8 core senses.
    Used as a sanity check: if Global IC = 0/8, TW-IC fusion is likely
    chasing noise rather than signal. P0 fix HB#234.
    """
    import numpy as np
    from scipy import stats as _stats
    from database.models import FeaturesNormalized, Labels

    sense_col_names = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue",
                       "feat_body", "feat_pulse", "feat_aura", "feat_mind"]
    sense_cols = [getattr(FeaturesNormalized, c) for c in sense_col_names]

    feat_rows = session.query(FeaturesNormalized.timestamp, *sense_cols).order_by(FeaturesNormalized.timestamp).all()
    label_target = getattr(Labels, DEFAULT_TARGET_COL, Labels.label_spot_long_win)
    label_rows = session.query(Labels.timestamp, label_target).filter(
        label_target.isnot(None), Labels.horizon_minutes == 1440).order_by(Labels.timestamp).all()

    feat_by_ts = {r[0]: {sense_col_names[i]: r[1+i] for i in range(len(sense_cols))} for r in feat_rows}
    labels_by_ts = {r[0]: int(r[1]) for r in label_rows}
    common_ts = sorted(set(feat_by_ts.keys()) & set(labels_by_ts.keys()))
    if len(common_ts) < 50:
        return {col: 0.0 for col in sense_col_names}

    ics = {}
    for col in sense_col_names:
        vals = np.array([feat_by_ts[ts].get(col) for ts in common_ts], dtype=float)
        sw = np.array([float(labels_by_ts[ts]) for ts in common_ts])
        mask = (~np.isnan(vals)) & (~np.isnan(sw))
        if mask.sum() < 50:
            ics[col] = 0.0
            continue
        vc = vals[mask]; sc = sw[mask]
        if np.std(vc) < 1e-10 or np.std(sc) < 1e-10:
            ics[col] = 0.0
            continue
        r, _ = _stats.spearmanr(vc, sc)
        ics[col] = round(float(r), 4)
    return ics


def _time_weighted_ic(session, tau=200):
    """Compute time-weighted IC for the 8 core senses.
    Returns dict of {col_name: ic_value} with exponential decay weights.
    Recent samples get higher weight via exp(-(N-1-i)/tau).

    P0 fix HB#234: Also returns global IC for sanity check.
    If global IC = 0/8, TW-IC fusion is operating on noise — require
    stronger signals and fewer active senses.
    """
    import numpy as np
    from scipy import stats as _stats
    from database.models import FeaturesNormalized, Labels

    sense_col_names = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue",
                       "feat_body", "feat_pulse", "feat_aura", "feat_mind"]
    sense_cols = [getattr(FeaturesNormalized, c) for c in sense_col_names]

    # Load time-ordered features + labels
    feat_rows = session.query(FeaturesNormalized.timestamp, *sense_cols).order_by(FeaturesNormalized.timestamp).all()
    label_target = getattr(Labels, DEFAULT_TARGET_COL, Labels.label_spot_long_win)
    label_rows = session.query(Labels.timestamp, label_target).filter(
        label_target.isnot(None), Labels.horizon_minutes == 1440).order_by(Labels.timestamp).all()

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

        self._target_col = DEFAULT_TARGET_COL
        if isinstance(model, dict):
            self._clf = model.get("clf")
            self._imputer = model.get("imputer")
            self._neg_ic_feats = set(model.get("neg_ic_feats", []))
            self._calibration = model.get("calibration", {"kind": "none"})
            self._feature_names = model.get("feature_names")
            self._regime_threshold_bias = model.get("regime_threshold_bias", REGIME_THRESHOLD_BIAS.copy())
            self._target_col = model.get("target_col", DEFAULT_TARGET_COL)
        else:
            self._clf = model
        self.model = model

    def _apply_calibration(self, score: float) -> float:
        cal = self._calibration or {"kind": "none"}
        kind = cal.get("kind", "none")
        score = float(np.clip(score, 1e-6, 1 - 1e-6))
        if kind == "isotonic":
            try:
                xs = np.asarray(cal.get("isotonic_x") or cal.get("x") or [], dtype=float)
                ys = np.asarray(cal.get("isotonic_y") or cal.get("y") or [], dtype=float)
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
    """P0 #REGIME: Determine regime from feat_body (primary) + feat_mind.
    Thresholds tuned to actual data ranges (not arbitrary 0.15 values):
    - bear: body < -0.5 (strong downward momentum)
    - bull: body > 0.2 (strong upward momentum)
    - chop: -0.5 <= body <= 0.2 (sideways)
    """
    # Use feat_mind (short-term return) and feat_body (momentum) as regime signal
    mind = float(features.get('feat_mind', 0) or 0)
    body = float(features.get('feat_body', 0) or 0)
    momentum = (mind + body) / 2.0

    # P0 #REGIME: Use feat_body as primary regime signal (feat_mind is order of magnitude smaller)
    # body values: 10th pct ~ -1.5, 90th pct ~ 0.8, median ~ -0.3
    momentum = (mind + body) / 2.0
    if momentum < -0.15:
        return 'bear'
    elif momentum > 0.15:
        return 'bull'
    else:
        return 'chop'


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _compute_live_regime_gate_debug(
    bias200_value: float,
    regime: str,
    regime_min: float = LIVE_REGIME_BIAS200_MIN,
    bb_pct_b_value: Optional[float] = None,
    dist_bb_lower_value: Optional[float] = None,
    dist_swing_low_value: Optional[float] = None,
) -> Dict[str, Any]:
    """Explain how the live regime gate was formed for diagnostics/root-cause work."""
    regime = (regime or "unknown").lower()
    missing_inputs = [
        name
        for name, value in (
            ("feat_4h_bias200", bias200_value),
            ("feat_4h_bb_pct_b", bb_pct_b_value),
            ("feat_4h_dist_bb_lower", dist_bb_lower_value),
            ("feat_4h_dist_swing_low", dist_swing_low_value),
        )
        if value is None
    ]
    structure_quality = _compute_live_4h_structure_quality(
        bb_pct_b_value=bb_pct_b_value,
        dist_bb_lower_value=dist_bb_lower_value,
        dist_swing_low_value=dist_swing_low_value,
    )
    if bias200_value < regime_min:
        return {
            "regime": regime,
            "bias200": _round_optional(bias200_value),
            "structure_quality": structure_quality,
            "base_gate": "BLOCK",
            "final_gate": "BLOCK",
            "final_reason": "bias200_below_min",
            "missing_inputs": missing_inputs,
        }
    if regime == "bear" and bias200_value <= -3.0:
        return {
            "regime": regime,
            "bias200": _round_optional(bias200_value),
            "structure_quality": structure_quality,
            "base_gate": "BLOCK",
            "final_gate": "BLOCK",
            "final_reason": "bear_bias200_hard_block",
            "missing_inputs": missing_inputs,
        }
    if regime in {"chop", "unknown"} or bias200_value < -1.0:
        base_gate = "CAUTION"
        base_reason = "base_caution_regime_or_bias"
    else:
        base_gate = "ALLOW"
        base_reason = "base_allow"

    final_gate = base_gate
    final_reason = base_reason
    if base_gate == "ALLOW" and _is_live_4h_structure_overextended(
        bb_pct_b_value=bb_pct_b_value,
        dist_bb_lower_value=dist_bb_lower_value,
        dist_swing_low_value=dist_swing_low_value,
    ):
        final_gate = "BLOCK"
        final_reason = "structure_overextended_block"
    elif base_gate == "ALLOW" and structure_quality is not None:
        if structure_quality < 0.15:
            final_gate = "BLOCK"
            final_reason = "structure_quality_block"
        # Heartbeat #718: ALLOW+q35 produced a live bull path that looked permissive
        # but had almost no historical support (2 rows in the 24h calibration set).
        # Treat borderline 4H structure (<0.65) as CAUTION so runtime semantics stop
        # advertising these sparse, weak-structure setups as true ALLOW lanes.
        elif structure_quality < 0.65:
            final_gate = "CAUTION"
            final_reason = "structure_quality_caution"

    return {
        "regime": regime,
        "bias200": _round_optional(bias200_value),
        "structure_quality": structure_quality,
        "base_gate": base_gate,
        "final_gate": final_gate,
        "final_reason": final_reason,
        "missing_inputs": missing_inputs,
    }



def _compute_live_regime_gate(
    bias200_value: float,
    regime: str,
    regime_min: float = LIVE_REGIME_BIAS200_MIN,
    bb_pct_b_value: Optional[float] = None,
    dist_bb_lower_value: Optional[float] = None,
    dist_swing_low_value: Optional[float] = None,
) -> str:
    """Mirror Strategy Lab's regime gate semantics for live inference.

    Keep these thresholds in sync with `backtesting.strategy_lab._compute_regime_gate`
    so the heartbeat can verify that live predictor output speaks the same decision
    contract as Strategy Lab / API / UI.
    """
    return str(
        _compute_live_regime_gate_debug(
            bias200_value,
            regime,
            regime_min=regime_min,
            bb_pct_b_value=bb_pct_b_value,
            dist_bb_lower_value=dist_bb_lower_value,
            dist_swing_low_value=dist_swing_low_value,
        ).get("final_gate")
        or "BLOCK"
    )


def _is_live_4h_structure_overextended(
    bb_pct_b_value: Optional[float] = None,
    dist_bb_lower_value: Optional[float] = None,
    dist_swing_low_value: Optional[float] = None,
) -> bool:
    if bb_pct_b_value is None or dist_bb_lower_value is None or dist_swing_low_value is None:
        return False
    return (
        float(bb_pct_b_value) >= LIVE_4H_OVEREXTENDED_BB_PCT_B_MIN
        and float(dist_bb_lower_value) >= LIVE_4H_OVEREXTENDED_DIST_BB_LOWER_MIN
        and float(dist_swing_low_value) >= LIVE_4H_OVEREXTENDED_DIST_SWING_LOW_MIN
    )


def _compute_live_4h_structure_quality(
    bb_pct_b_value: Optional[float] = None,
    dist_bb_lower_value: Optional[float] = None,
    dist_swing_low_value: Optional[float] = None,
) -> Optional[float]:
    components: List[tuple[float, float]] = []
    if bb_pct_b_value is not None:
        components.append((0.34, _clamp01(float(bb_pct_b_value))))
    if dist_bb_lower_value is not None:
        components.append((0.33, _clamp01(float(dist_bb_lower_value) / 8.0)))
    if dist_swing_low_value is not None:
        components.append((0.33, _clamp01(float(dist_swing_low_value) / 10.0)))
    if not components:
        return None

    total_weight = sum(weight for weight, _ in components)
    score = sum(weight * value for weight, value in components) / total_weight
    return round(float(score), 4)



def _live_structure_bucket_from_debug(debug: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(debug, dict):
        return None
    final_gate = str(debug.get("final_gate") or "").strip()
    if not final_gate:
        return None
    structure_quality = debug.get("structure_quality")
    if structure_quality is None:
        quality_bucket = "missing"
    else:
        quality_value = float(structure_quality)
        if quality_value >= 0.85:
            quality_bucket = "q85"
        elif quality_value >= 0.65:
            quality_bucket = "q65"
        elif quality_value >= 0.35:
            quality_bucket = "q35"
        elif quality_value >= 0.15:
            quality_bucket = "q15"
        else:
            quality_bucket = "q00"
    final_reason = str(debug.get("final_reason") or "unknown")
    return f"{final_gate}|{final_reason}|{quality_bucket}"



def _compute_live_entry_quality(
    bias50_value: float,
    nose_value: float,
    pulse_value: float,
    ear_value: float,
    bb_pct_b_value: Optional[float] = None,
    dist_bb_lower_value: Optional[float] = None,
    dist_swing_low_value: Optional[float] = None,
) -> float:
    """Mirror Strategy Lab's entry-quality baseline for live inference."""
    bias_score = _clamp01((-bias50_value + 2.4) / 5.0)
    nose_score = _clamp01(1.0 - nose_value)
    pulse_score = _clamp01(pulse_value)
    ear_score = _clamp01(1.0 - abs(ear_value) * 5.0)
    base_quality = 0.40 * bias_score + 0.18 * nose_score + 0.27 * pulse_score + 0.15 * ear_score

    structure_quality = _compute_live_4h_structure_quality(
        bb_pct_b_value=bb_pct_b_value,
        dist_bb_lower_value=dist_bb_lower_value,
        dist_swing_low_value=dist_swing_low_value,
    )
    if structure_quality is None:
        return round(base_quality, 4)

    return round(0.75 * base_quality + 0.25 * structure_quality, 4)


def _quality_label(entry_quality: float) -> str:
    if entry_quality >= 0.82:
        return "A"
    if entry_quality >= 0.68:
        return "B"
    if entry_quality >= 0.55:
        return "C"
    return "D"


def _allowed_layers_for_live_signal(regime_gate: str, entry_quality: float, max_layers: int = LIVE_MAX_LAYERS) -> int:
    max_layers = max(0, int(max_layers))
    if regime_gate == "BLOCK" or entry_quality < 0.55:
        return 0
    if entry_quality < 0.68:
        return min(1, max_layers)
    if regime_gate == "CAUTION" or entry_quality < 0.70:
        return min(2, max_layers)
    return min(3, max_layers)


def _build_live_decision_profile(features: Optional[Dict], max_layers: int = LIVE_MAX_LAYERS) -> Dict:
    if not features:
        return {
            "regime_label": None,
            "regime_gate": None,
            "regime_gate_reason": None,
            "structure_quality": None,
            "structure_bucket": None,
            "entry_quality": None,
            "entry_quality_label": None,
            "allowed_layers": None,
            "decision_profile_version": "phase16_baseline_v2",
        }

    def _f(name: str) -> float:
        value = features.get(name)
        return 0.0 if value is None else float(value)

    regime = str(features.get("regime_label") or _determine_regime(features))
    bb_pct_b_value = features.get("feat_4h_bb_pct_b")
    dist_bb_lower_value = features.get("feat_4h_dist_bb_lower")
    dist_swing_low_value = features.get("feat_4h_dist_swing_low")
    gate_debug = _compute_live_regime_gate_debug(
        _f("feat_4h_bias200"),
        regime,
        bb_pct_b_value=bb_pct_b_value,
        dist_bb_lower_value=dist_bb_lower_value,
        dist_swing_low_value=dist_swing_low_value,
    )
    regime_gate = str(gate_debug.get("final_gate") or "BLOCK")
    entry_quality = _compute_live_entry_quality(
        _f("feat_4h_bias50"),
        _f("feat_nose"),
        _f("feat_pulse"),
        _f("feat_ear"),
        bb_pct_b_value,
        dist_bb_lower_value,
        dist_swing_low_value,
    )
    allowed_layers = _allowed_layers_for_live_signal(regime_gate, entry_quality, max_layers=max_layers)
    return {
        "regime_label": regime,
        "regime_gate": regime_gate,
        "regime_gate_reason": gate_debug.get("final_reason"),
        "structure_quality": gate_debug.get("structure_quality"),
        "structure_bucket": _live_structure_bucket_from_debug(gate_debug),
        "entry_quality": entry_quality,
        "entry_quality_label": _quality_label(entry_quality),
        "allowed_layers": allowed_layers,
        "decision_profile_version": "phase16_baseline_v2",
    }


def _decision_quality_fallback(profile_version: str = "phase16_baseline_v2") -> Dict[str, Any]:
    return {
        "decision_quality_horizon_minutes": 1440,
        "decision_quality_calibration_scope": None,
        "decision_quality_sample_size": 0,
        "decision_quality_reference_from": None,
        "decision_quality_calibration_window": None,
        "decision_quality_guardrail_applied": False,
        "decision_quality_guardrail_reason": None,
        "decision_quality_recent_pathology_applied": False,
        "decision_quality_recent_pathology_reason": None,
        "decision_quality_recent_pathology_window": 0,
        "decision_quality_recent_pathology_alerts": [],
        "decision_quality_recent_pathology_summary": None,
        "decision_quality_exact_live_lane_toxicity_applied": False,
        "decision_quality_exact_live_lane_status": None,
        "decision_quality_exact_live_lane_reason": None,
        "decision_quality_exact_live_lane_summary": None,
        "decision_quality_exact_live_lane_bucket_verdict": None,
        "decision_quality_exact_live_lane_bucket_reason": None,
        "decision_quality_exact_live_lane_toxic_bucket": None,
        "decision_quality_exact_live_lane_bucket_diagnostics": None,
        "decision_quality_live_structure_bucket": None,
        "decision_quality_structure_bucket_guardrail_applied": False,
        "decision_quality_structure_bucket_guardrail_reason": None,
        "decision_quality_structure_bucket_support_mode": None,
        "decision_quality_structure_bucket_support_rows": 0,
        "decision_quality_structure_bucket_support_share": None,
        "decision_quality_exact_live_structure_bucket_support_rows": 0,
        "decision_quality_exact_live_structure_bucket_support_share": None,
        "decision_quality_structure_bucket_supported_neighbor_buckets": [],
        "expected_win_rate": None,
        "expected_pyramid_pnl": None,
        "expected_pyramid_quality": None,
        "expected_drawdown_penalty": None,
        "expected_time_underwater": None,
        "decision_quality_score": None,
        "decision_quality_label": None,
        "decision_profile_version": profile_version,
    }


def _load_dynamic_window_guardrail() -> Dict[str, Any]:
    if not DW_RESULT_PATH.exists():
        return {}
    try:
        payload = json.loads(DW_RESULT_PATH.read_text())
    except Exception:
        return {}

    recommended_best_n = payload.get("recommended_best_n")
    raw_best_n = payload.get("raw_best_n")
    if not isinstance(recommended_best_n, int) or recommended_best_n <= 0:
        return {}

    raw_best = payload.get(str(raw_best_n), {}) if raw_best_n is not None else {}
    recommended_best = payload.get(str(recommended_best_n), {})
    raw_alerts = list(raw_best.get("alerts") or [])
    recommended_alerts = list(recommended_best.get("alerts") or [])
    disqualifying = set((payload.get("guardrail_policy") or {}).get("disqualifying_alerts") or [])
    raw_guardrailed = bool(raw_best.get("distribution_guardrail")) or any(a in disqualifying for a in raw_alerts)

    reason_parts = []
    if raw_guardrailed and raw_best_n is not None and raw_best_n != recommended_best_n:
        reason_parts.append(
            f"raw_best_n={raw_best_n} guardrailed via alerts={raw_alerts or ['distribution_guardrail']}"
        )
    if recommended_alerts:
        reason_parts.append(f"recommended_best alerts={recommended_alerts}")

    return {
        "recommended_best_n": recommended_best_n,
        "raw_best_n": raw_best_n,
        "raw_best_guardrailed": raw_guardrailed,
        "recommended_alerts": recommended_alerts,
        "guardrail_reason": "; ".join(reason_parts) if reason_parts else None,
    }


def _decision_quality_label(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score >= 0.65:
        return "A"
    if score >= 0.50:
        return "B"
    if score >= 0.35:
        return "C"
    return "D"


def _decision_quality_scope_alerts(rows: List[Dict[str, Any]]) -> List[str]:
    wins = [int(row["simulated_pyramid_win"]) for row in rows if row.get("simulated_pyramid_win") is not None]
    if not wins:
        return ["no_target_rows"]

    unique_targets = set(wins)
    if len(unique_targets) <= 1:
        return ["constant_target"]

    win_rate = sum(wins) / len(wins)
    alerts: List[str] = []
    if win_rate >= 0.8 or win_rate <= 0.2:
        alerts.append("label_imbalance")
    return alerts


def _compute_decision_quality_score(win_rate: Optional[float], pyramid_quality: Optional[float], drawdown_penalty: Optional[float], time_underwater: Optional[float]) -> Optional[float]:
    if win_rate is None or pyramid_quality is None or drawdown_penalty is None or time_underwater is None:
        return None
    score = (
        0.45 * float(win_rate)
        + 0.25 * float(pyramid_quality)
        - 0.20 * float(drawdown_penalty)
        - 0.10 * float(time_underwater)
    )
    return round(float(score), 4)


def _avg_metric(rows: List[Dict[str, Any]], key: str) -> Optional[float]:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    if not values:
        return None
    return round(float(sum(values) / len(values)), 4)


def _longest_binary_streak(rows: List[Dict[str, Any]], key: str, target_value: int) -> Dict[str, Any]:
    best_rows: List[Dict[str, Any]] = []
    current_rows: List[Dict[str, Any]] = []
    for row in rows:
        value = row.get(key)
        if value is None:
            if len(current_rows) > len(best_rows):
                best_rows = list(current_rows)
            current_rows = []
            continue
        current_value = int(value)
        if current_value == target_value:
            current_rows.append(row)
            continue
        if len(current_rows) > len(best_rows):
            best_rows = list(current_rows)
        current_rows = []
    if len(current_rows) > len(best_rows):
        best_rows = list(current_rows)

    if not best_rows:
        return {
            "target": target_value,
            "count": 0,
            "start_timestamp": None,
            "end_timestamp": None,
        }

    return {
        "target": target_value,
        "count": len(best_rows),
        "start_timestamp": str(best_rows[-1].get("timestamp")) if best_rows[-1].get("timestamp") is not None else None,
        "end_timestamp": str(best_rows[0].get("timestamp")) if best_rows[0].get("timestamp") is not None else None,
    }


def _feature_mean_snapshot(
    rows: List[Dict[str, Any]],
    reference_rows: List[Dict[str, Any]],
    feature_keys: tuple[str, ...],
) -> Dict[str, Dict[str, Optional[float]]]:
    snapshot: Dict[str, Dict[str, Optional[float]]] = {}
    for feature_key in feature_keys:
        current_mean = _avg_metric(rows, feature_key)
        reference_mean = _avg_metric(reference_rows, feature_key)
        if current_mean is None and reference_mean is None:
            continue
        delta = None
        if current_mean is not None and reference_mean is not None:
            delta = round(float(current_mean) - float(reference_mean), 4)
        snapshot[feature_key] = {
            "current_mean": current_mean,
            "reference_mean": reference_mean,
            "mean_delta": delta,
        }
    return snapshot


def _reference_window_contrast(
    rows: List[Dict[str, Any]],
    reference_rows: List[Dict[str, Any]],
    feature_keys: tuple[str, ...] = (
        "feat_4h_dist_bb_lower",
        "feat_4h_dist_swing_low",
        "feat_4h_bb_pct_b",
    ),
) -> Dict[str, Any]:
    if not rows or not reference_rows:
        return {}

    def _delta(current: Optional[float], reference: Optional[float]) -> Optional[float]:
        if current is None or reference is None:
            return None
        return round(float(current) - float(reference), 4)

    current_quality = {
        "win_rate": _avg_metric(rows, "simulated_pyramid_win"),
        "avg_simulated_pnl": _avg_metric(rows, "simulated_pyramid_pnl"),
        "avg_simulated_quality": _avg_metric(rows, "simulated_pyramid_quality"),
        "avg_drawdown_penalty": _avg_metric(rows, "simulated_pyramid_drawdown_penalty"),
        "avg_time_underwater": _avg_metric(rows, "simulated_pyramid_time_underwater"),
    }
    reference_quality = {
        "win_rate": _avg_metric(reference_rows, "simulated_pyramid_win"),
        "avg_simulated_pnl": _avg_metric(reference_rows, "simulated_pyramid_pnl"),
        "avg_simulated_quality": _avg_metric(reference_rows, "simulated_pyramid_quality"),
        "avg_drawdown_penalty": _avg_metric(reference_rows, "simulated_pyramid_drawdown_penalty"),
        "avg_time_underwater": _avg_metric(reference_rows, "simulated_pyramid_time_underwater"),
    }

    feature_shifts: List[Dict[str, Any]] = []
    for feature_key in feature_keys:
        current_mean = _avg_metric(rows, feature_key)
        reference_mean = _avg_metric(reference_rows, feature_key)
        if current_mean is None or reference_mean is None:
            continue
        delta = round(float(current_mean) - float(reference_mean), 4)
        feature_shifts.append(
            {
                "feature": feature_key,
                "current_mean": current_mean,
                "reference_mean": reference_mean,
                "mean_delta": delta,
            }
        )
    feature_shifts.sort(key=lambda row: (-abs(float(row.get("mean_delta") or 0.0)), row["feature"]))

    return {
        "current_quality": current_quality,
        "reference_quality": reference_quality,
        "win_rate_delta_vs_reference": _delta(current_quality.get("win_rate"), reference_quality.get("win_rate")),
        "avg_simulated_pnl_delta_vs_reference": _delta(current_quality.get("avg_simulated_pnl"), reference_quality.get("avg_simulated_pnl")),
        "avg_simulated_quality_delta_vs_reference": _delta(current_quality.get("avg_simulated_quality"), reference_quality.get("avg_simulated_quality")),
        "avg_drawdown_penalty_delta_vs_reference": _delta(current_quality.get("avg_drawdown_penalty"), reference_quality.get("avg_drawdown_penalty")),
        "avg_time_underwater_delta_vs_reference": _delta(current_quality.get("avg_time_underwater"), reference_quality.get("avg_time_underwater")),
        "top_mean_shift_features": feature_shifts[:3],
    }


def _recent_scope_pathology_summary(
    rows: List[Dict[str, Any]],
    recent_windows: tuple[int, ...] = (100, 250, 500),
    min_rows: int = 30,
) -> Dict[str, Any]:
    if len(rows) < min_rows:
        return {
            "applied": False,
            "window": min(len(rows), min(recent_windows) if recent_windows else 0),
            "alerts": [],
            "reason": None,
            "summary": None,
        }

    ordered_rows = sorted(
        rows,
        key=lambda row: (str(row.get("timestamp") or ""), str(row.get("symbol") or "")),
        reverse=True,
    )
    candidates = []
    for recent_window in recent_windows:
        if recent_window <= 0:
            continue
        window_rows = ordered_rows[: min(recent_window, len(ordered_rows))]
        if len(window_rows) < min_rows:
            continue
        alerts = _decision_quality_scope_alerts(window_rows)
        win_rate = _avg_metric(window_rows, "simulated_pyramid_win")
        avg_pnl = _avg_metric(window_rows, "simulated_pyramid_pnl")
        avg_quality = _avg_metric(window_rows, "simulated_pyramid_quality")
        avg_drawdown_penalty = _avg_metric(window_rows, "simulated_pyramid_drawdown_penalty")
        avg_time_underwater = _avg_metric(window_rows, "simulated_pyramid_time_underwater")
        reference_rows = ordered_rows[len(window_rows): len(window_rows) * 2]
        sibling_contrast = _reference_window_contrast(window_rows, reference_rows)

        is_negative_pathology = any(alert in alerts for alert in ("constant_target", "label_imbalance")) and (
            (win_rate is not None and win_rate <= 0.2)
            or (avg_pnl is not None and avg_pnl < 0)
            or (avg_quality is not None and avg_quality < 0)
        )
        if not is_negative_pathology:
            continue

        severity = 0
        if "constant_target" in alerts:
            severity += 4
        if "label_imbalance" in alerts:
            severity += 3
        negative_score = round(
            max(0.0, 0.2 - float(win_rate if win_rate is not None else 0.2))
            + max(0.0, -(avg_pnl or 0.0))
            + max(0.0, -(avg_quality or 0.0)),
            6,
        )
        sibling_contrast_score = round(
            max(0.0, -(sibling_contrast.get("win_rate_delta_vs_reference") or 0.0))
            + max(0.0, -(sibling_contrast.get("avg_simulated_pnl_delta_vs_reference") or 0.0))
            + max(0.0, -(sibling_contrast.get("avg_simulated_quality_delta_vs_reference") or 0.0)),
            6,
        )
        adverse_target = 0 if win_rate is None or win_rate <= 0.5 else 1
        adverse_streak = _longest_binary_streak(window_rows, "simulated_pyramid_win", adverse_target)
        candidates.append(
            {
                "score": (severity, sibling_contrast_score, negative_score, adverse_streak.get("count", 0), len(window_rows)),
                "window": len(window_rows),
                "alerts": alerts,
                "summary": {
                    "rows": len(window_rows),
                    "win_rate": win_rate,
                    "avg_pnl": avg_pnl,
                    "avg_quality": avg_quality,
                    "avg_drawdown_penalty": avg_drawdown_penalty,
                    "avg_time_underwater": avg_time_underwater,
                    "start_timestamp": str(window_rows[-1].get("timestamp")) if window_rows[-1].get("timestamp") is not None else None,
                    "end_timestamp": str(window_rows[0].get("timestamp")) if window_rows[0].get("timestamp") is not None else None,
                    "adverse_target_streak": adverse_streak,
                    "reference_window_comparison": sibling_contrast,
                },
            }
        )

    if not candidates:
        return {
            "applied": False,
            "window": min(len(ordered_rows), min(recent_windows) if recent_windows else 0),
            "alerts": [],
            "reason": None,
            "summary": None,
        }

    chosen = max(candidates, key=lambda row: row["score"])
    summary = chosen["summary"]
    adverse_streak = summary.get("adverse_target_streak") or {}
    sibling_contrast = summary.get("reference_window_comparison") or {}
    sibling_reason = ""
    if sibling_contrast:
        top_shift = sibling_contrast.get("top_mean_shift_features") or []
        top_shift_text = ", ".join(
            f"{row.get('feature')}({row.get('reference_mean')}→{row.get('current_mean')})"
            for row in top_shift[:3]
        )
        sibling_reason = (
            f" vs sibling prev_win_rate={sibling_contrast.get('reference_quality', {}).get('win_rate')}"
            f" Δwin_rate={sibling_contrast.get('win_rate_delta_vs_reference')}"
            f" prev_quality={sibling_contrast.get('reference_quality', {}).get('avg_simulated_quality')}"
            f" Δquality={sibling_contrast.get('avg_simulated_quality_delta_vs_reference')}"
            f" prev_pnl={sibling_contrast.get('reference_quality', {}).get('avg_simulated_pnl')}"
            f" Δpnl={sibling_contrast.get('avg_simulated_pnl_delta_vs_reference')}"
        )
        if top_shift_text:
            sibling_reason += f" top_shifts={top_shift_text}"
    reason = (
        f"recent scope slice {chosen['window']} rows shows distribution_pathology "
        f"alerts={chosen['alerts']} win_rate={summary.get('win_rate')} avg_pnl={summary.get('avg_pnl')} "
        f"avg_quality={summary.get('avg_quality')} "
        f"window={summary.get('start_timestamp')}->{summary.get('end_timestamp')} "
        f"adverse_streak={adverse_streak.get('count', 0)}x{adverse_streak.get('target')} "
        f"({adverse_streak.get('start_timestamp')}->{adverse_streak.get('end_timestamp')})"
        f"{sibling_reason}"
    )
    return {
        "applied": True,
        "window": chosen["window"],
        "alerts": chosen["alerts"],
        "reason": reason,
        "summary": summary,
    }


def _recent_scope_value_counts(scoped_rows: List[Dict[str, Any]], key: str, limit: int = 500) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in scoped_rows[: max(0, int(limit))]:
        value = str(row.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _recent_scope_regime_counts(scoped_rows: List[Dict[str, Any]], limit: int = 500) -> Dict[str, int]:
    return _recent_scope_value_counts(scoped_rows, "regime_label", limit=limit)


def _recent_scope_gate_counts(scoped_rows: List[Dict[str, Any]], limit: int = 500) -> Dict[str, int]:
    return _recent_scope_value_counts(scoped_rows, "regime_gate", limit=limit)


def _recent_scope_regime_gate_counts(scoped_rows: List[Dict[str, Any]], limit: int = 500) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in scoped_rows[: max(0, int(limit))]:
        regime = str(row.get("regime_label") or "unknown")
        gate = str(row.get("regime_gate") or "unknown")
        combo = f"{regime}|{gate}"
        counts[combo] = counts.get(combo, 0) + 1
    return counts


def _recent_scope_structure_bucket_counts(scoped_rows: List[Dict[str, Any]], limit: int = 500) -> Dict[str, int]:
    return _recent_scope_value_counts(scoped_rows, "structure_bucket", limit=limit)


def _dominant_value_summary(counts: Dict[str, int], field_name: str) -> Optional[Dict[str, Any]]:
    if not counts:
        return None
    value, count = max(counts.items(), key=lambda item: (int(item[1]), str(item[0])))
    total = sum(int(v) for v in counts.values())
    if total <= 0:
        return None
    return {
        field_name: value,
        "count": int(count),
        "share": round(float(count) / float(total), 4),
    }


def _dominant_regime_summary(counts: Dict[str, int]) -> Optional[Dict[str, Any]]:
    return _dominant_value_summary(counts, "regime")


def _dominant_gate_summary(counts: Dict[str, int]) -> Optional[Dict[str, Any]]:
    return _dominant_value_summary(counts, "gate")


def _dominant_regime_gate_summary(counts: Dict[str, int]) -> Optional[Dict[str, Any]]:
    summary = _dominant_value_summary(counts, "regime_gate")
    if not summary or not summary.get("regime_gate"):
        return summary
    regime_gate = str(summary.get("regime_gate") or "")
    regime, _, gate = regime_gate.partition("|")
    summary["regime"] = regime or None
    summary["gate"] = gate or None
    return summary


def _dominant_structure_bucket_summary(counts: Dict[str, int]) -> Optional[Dict[str, Any]]:
    return _dominant_value_summary(counts, "structure_bucket")


def _scope_metric_summary(scoped_rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not scoped_rows:
        return None
    return {
        "rows": len(scoped_rows),
        "win_rate": _avg_metric(scoped_rows, "simulated_pyramid_win"),
        "avg_pnl": _avg_metric(scoped_rows, "simulated_pyramid_pnl"),
        "avg_quality": _avg_metric(scoped_rows, "simulated_pyramid_quality"),
        "avg_drawdown_penalty": _avg_metric(scoped_rows, "simulated_pyramid_drawdown_penalty"),
        "avg_time_underwater": _avg_metric(scoped_rows, "simulated_pyramid_time_underwater"),
    }


def _exact_live_lane_bucket_diagnostics(
    scoped_rows: List[Dict[str, Any]],
    current_bucket: Optional[str],
) -> Dict[str, Any]:
    if not scoped_rows:
        return {
            "bucket_count": 0,
            "buckets": {},
            "toxic_bucket": None,
            "verdict": "no_exact_lane_rows",
            "reason": "exact live lane 沒有 rows，無法做子 bucket 診斷。",
        }

    buckets: Dict[str, Dict[str, Any]] = {}
    for row in scoped_rows:
        bucket = row.get("structure_bucket")
        if not bucket:
            continue
        bucket_rows = buckets.setdefault(bucket, {"rows_data": []})["rows_data"]
        bucket_rows.append(row)

    if not buckets:
        return {
            "bucket_count": 0,
            "buckets": {},
            "toxic_bucket": None,
            "verdict": "missing_structure_bucket",
            "reason": "exact live lane 缺少 structure_bucket，無法做子 bucket 診斷。",
        }

    normalized_buckets: Dict[str, Dict[str, Any]] = {}
    for bucket, payload in buckets.items():
        rows_data = payload.get("rows_data") or []
        normalized_buckets[bucket] = {
            "rows": len(rows_data),
            "win_rate": _avg_metric(rows_data, "simulated_pyramid_win"),
            "avg_pnl": _avg_metric(rows_data, "simulated_pyramid_pnl"),
            "avg_quality": _avg_metric(rows_data, "simulated_pyramid_quality"),
            "avg_drawdown_penalty": _avg_metric(rows_data, "simulated_pyramid_drawdown_penalty"),
            "avg_time_underwater": _avg_metric(rows_data, "simulated_pyramid_time_underwater"),
        }

    current_metrics = normalized_buckets.get(current_bucket or "") if current_bucket else None
    bucket_payloads = []
    for bucket, payload in normalized_buckets.items():
        versus_current = None
        if current_metrics and bucket != current_bucket:
            versus_current = {
                "win_rate_delta": _round_optional(
                    (payload.get("win_rate") - current_metrics.get("win_rate"))
                    if payload.get("win_rate") is not None and current_metrics.get("win_rate") is not None
                    else None
                ),
                "quality_delta": _round_optional(
                    (payload.get("avg_quality") - current_metrics.get("avg_quality"))
                    if payload.get("avg_quality") is not None and current_metrics.get("avg_quality") is not None
                    else None
                ),
                "pnl_delta": _round_optional(
                    (payload.get("avg_pnl") - current_metrics.get("avg_pnl"))
                    if payload.get("avg_pnl") is not None and current_metrics.get("avg_pnl") is not None
                    else None
                ),
            }
        bucket_payload = {
            "bucket": bucket,
            **payload,
            "vs_current_bucket": versus_current,
        }
        normalized_buckets[bucket] = bucket_payload
        bucket_payloads.append(bucket_payload)

    toxic_bucket = None
    if current_metrics and bucket_payloads:
        overall_worst = min(
            bucket_payloads,
            key=lambda row: (
                float(row.get("win_rate") if row.get("win_rate") is not None else 1.0),
                float(row.get("avg_quality") if row.get("avg_quality") is not None else 1.0),
                -int(row.get("rows") or 0),
                str(row.get("bucket") or ""),
            ),
        )
        if overall_worst.get("bucket") == current_bucket:
            competitor_buckets = [row for row in bucket_payloads if row.get("bucket") != current_bucket]
            best_alternative = max(
                competitor_buckets,
                key=lambda row: (
                    float(row.get("win_rate") if row.get("win_rate") is not None else 0.0),
                    float(row.get("avg_quality") if row.get("avg_quality") is not None else 0.0),
                    int(row.get("rows") or 0),
                    str(row.get("bucket") or ""),
                ),
                default=None,
            )
            if best_alternative is not None:
                overall_worst = {
                    **overall_worst,
                    "vs_current_bucket": {
                        "win_rate_delta": _round_optional(
                            (overall_worst.get("win_rate") - best_alternative.get("win_rate"))
                            if overall_worst.get("win_rate") is not None and best_alternative.get("win_rate") is not None
                            else None
                        ),
                        "quality_delta": _round_optional(
                            (overall_worst.get("avg_quality") - best_alternative.get("avg_quality"))
                            if overall_worst.get("avg_quality") is not None and best_alternative.get("avg_quality") is not None
                            else None
                        ),
                        "pnl_delta": _round_optional(
                            (overall_worst.get("avg_pnl") - best_alternative.get("avg_pnl"))
                            if overall_worst.get("avg_pnl") is not None and best_alternative.get("avg_pnl") is not None
                            else None
                        ),
                        "reference_bucket": best_alternative.get("bucket"),
                    },
                }
        toxic_bucket = overall_worst

    verdict = "no_exact_lane_sub_bucket_split"
    reason = "exact live lane 沒有可比較的非 current bucket 子 bucket。"
    if toxic_bucket and current_metrics:
        quality_delta = ((toxic_bucket.get("vs_current_bucket") or {}).get("quality_delta"))
        win_delta = ((toxic_bucket.get("vs_current_bucket") or {}).get("win_rate_delta"))
        if (
            (quality_delta is not None and quality_delta <= -0.15)
            or (win_delta is not None and win_delta <= -0.20)
        ):
            verdict = "toxic_sub_bucket_identified"
            if toxic_bucket.get("bucket") == current_bucket:
                reason = (
                    f"exact live lane 的 current bucket `{current_bucket}` 本身就是最差子 bucket，"
                    "應直接升級成 runtime veto / rejection 規則。"
                )
            else:
                reason = (
                    f"exact live lane 內的 `{toxic_bucket.get('bucket')}` 明顯比 current bucket `{current_bucket}` 更差，"
                    "應把它視為 lane-internal veto / rejection 候選，而不是把整條 lane 一起降級。"
                )
        else:
            verdict = "sub_buckets_present_but_not_toxic"
            reason = "exact live lane 雖有其他子 bucket，但目前沒有任何一個達到 toxic 判定門檻。"

    return {
        "bucket_count": len(normalized_buckets),
        "buckets": normalized_buckets,
        "toxic_bucket": toxic_bucket,
        "verdict": verdict,
        "reason": reason,
    }


def _round_optional(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), 4)


def _subtract_count_maps(base: Dict[str, int], subtract: Dict[str, int]) -> Dict[str, int]:
    diff: Dict[str, int] = {}
    keys = set(base) | set(subtract)
    for key in keys:
        remaining = int(base.get(key, 0)) - int(subtract.get(key, 0))
        if remaining > 0:
            diff[key] = remaining
    return diff


def _scope_row_identity(row: Dict[str, Any]) -> tuple:
    return (
        row.get("timestamp"),
        row.get("symbol"),
        row.get("regime_label"),
        row.get("regime_gate"),
        row.get("entry_quality_label"),
        row.get("simulated_pyramid_win"),
        row.get("simulated_pyramid_pnl"),
        row.get("simulated_pyramid_quality"),
    )


def _summarize_regime_gate_pockets(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    pockets: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        regime = row.get("regime_label") or "unknown"
        gate = row.get("regime_gate") or "unknown"
        pocket = f"{regime}|{gate}"
        pockets.setdefault(pocket, []).append(row)

    summaries: Dict[str, Dict[str, Any]] = {}
    for pocket, pocket_rows in pockets.items():
        summaries[pocket] = {
            "rows": len(pocket_rows),
            "win_rate": _avg_metric(pocket_rows, "simulated_pyramid_win"),
            "avg_pnl": _avg_metric(pocket_rows, "simulated_pyramid_pnl"),
            "avg_quality": _avg_metric(pocket_rows, "simulated_pyramid_quality"),
            "avg_drawdown_penalty": _avg_metric(pocket_rows, "simulated_pyramid_drawdown_penalty"),
            "avg_time_underwater": _avg_metric(pocket_rows, "simulated_pyramid_time_underwater"),
        }
    return summaries
def _pick_worst_regime_gate_pocket(
    pockets: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not pockets:
        return None

    def _sort_key(item: tuple[str, Dict[str, Any]]) -> tuple[float, float, float, float, str]:
        pocket, payload = item
        win_rate = payload.get("win_rate")
        quality = payload.get("avg_quality")
        pnl = payload.get("avg_pnl")
        dd = payload.get("avg_drawdown_penalty")
        tuw = payload.get("avg_time_underwater")
        return (
            float(win_rate) if win_rate is not None else 1.0,
            float(quality) if quality is not None else 1.0,
            float(pnl) if pnl is not None else float("inf"),
            -float(dd) if dd is not None else float("inf"),
            -float(tuw) if tuw is not None else float("inf"),
            pocket,
        )

    pocket, payload = min(pockets.items(), key=_sort_key)
    regime, _, gate = pocket.partition("|")
    return {
        "regime_gate": pocket,
        "regime": regime or None,
        "gate": gate or None,
        **payload,
    }



def _summarize_gate_path(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rows:
        return None

    final_gate_counts: Dict[str, int] = {}
    final_reason_counts: Dict[str, int] = {}
    base_gate_counts: Dict[str, int] = {}
    missing_input_feature_counts: Dict[str, int] = {}
    missing_input_rows = 0
    structure_quality_values: List[float] = []
    bias200_values: List[float] = []
    target_counts: Dict[str, int] = {}
    pnl_sign_counts: Dict[str, int] = {"positive": 0, "zero": 0, "negative": 0}
    quality_sign_counts: Dict[str, int] = {"positive": 0, "zero": 0, "negative": 0}

    def _bucket_target(value: Any) -> str:
        if value is None:
            return "missing"
        try:
            val = float(value)
        except (TypeError, ValueError):
            return "missing"
        if val >= 0.5:
            return "win"
        return "loss"

    def _bucket_sign(value: Any) -> Optional[str]:
        if value is None:
            return None
        try:
            val = float(value)
        except (TypeError, ValueError):
            return None
        if val > 0:
            return "positive"
        if val < 0:
            return "negative"
        return "zero"

    for row in rows:
        bias200_raw = row.get("feat_4h_bias200")
        debug = _compute_live_regime_gate_debug(
            0.0 if bias200_raw is None else float(bias200_raw),
            str(row.get("regime_label") or "unknown"),
            bb_pct_b_value=row.get("feat_4h_bb_pct_b"),
            dist_bb_lower_value=row.get("feat_4h_dist_bb_lower"),
            dist_swing_low_value=row.get("feat_4h_dist_swing_low"),
        )
        final_gate = str(debug.get("final_gate") or "unknown")
        final_reason = str(debug.get("final_reason") or "unknown")
        base_gate = str(debug.get("base_gate") or "unknown")
        final_gate_counts[final_gate] = final_gate_counts.get(final_gate, 0) + 1
        final_reason_counts[final_reason] = final_reason_counts.get(final_reason, 0) + 1
        base_gate_counts[base_gate] = base_gate_counts.get(base_gate, 0) + 1
        missing_inputs = list(debug.get("missing_inputs") or [])
        if missing_inputs:
            missing_input_rows += 1
            for feature in missing_inputs:
                missing_input_feature_counts[feature] = missing_input_feature_counts.get(feature, 0) + 1
        structure_quality = debug.get("structure_quality")
        if structure_quality is not None:
            structure_quality_values.append(float(structure_quality))
        bias200 = debug.get("bias200")
        if bias200 is not None:
            bias200_values.append(float(bias200))
        target_bucket = _bucket_target(row.get(DEFAULT_TARGET_COL))
        target_counts[target_bucket] = target_counts.get(target_bucket, 0) + 1
        pnl_bucket = _bucket_sign(row.get("simulated_pyramid_pnl"))
        if pnl_bucket:
            pnl_sign_counts[pnl_bucket] = pnl_sign_counts.get(pnl_bucket, 0) + 1
        quality_bucket = _bucket_sign(row.get("simulated_pyramid_quality"))
        if quality_bucket:
            quality_sign_counts[quality_bucket] = quality_sign_counts.get(quality_bucket, 0) + 1

    def _avg(values: List[float]) -> Optional[float]:
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    def _nearest_quantiles(values: List[float]) -> Optional[Dict[str, float]]:
        if not values:
            return None
        ordered = sorted(float(v) for v in values)

        def _pick(frac: float) -> float:
            idx = int(round((len(ordered) - 1) * frac))
            return round(ordered[idx], 4)

        return {
            "min": round(ordered[0], 4),
            "p25": _pick(0.25),
            "p50": _pick(0.50),
            "p75": _pick(0.75),
            "max": round(ordered[-1], 4),
        }

    def _structure_gate_bands(values: List[float]) -> Dict[str, int]:
        block = sum(1 for value in values if value < 0.15)
        caution = sum(1 for value in values if 0.15 <= value < 0.35)
        allow = sum(1 for value in values if value >= 0.35)
        return {
            "block_lt_0.15": block,
            "caution_0.15_to_0.35": caution,
            "allow_ge_0.35": allow,
        }

    canonical_true_negative_rows = min(
        int(target_counts.get("loss", 0)),
        int(pnl_sign_counts.get("negative", 0)),
        int(quality_sign_counts.get("negative", 0)),
    )

    return {
        "rows": len(rows),
        "final_gate_counts": final_gate_counts,
        "final_reason_counts": final_reason_counts,
        "base_gate_counts": base_gate_counts,
        "avg_structure_quality": _avg(structure_quality_values),
        "structure_quality_distribution": _nearest_quantiles(structure_quality_values),
        "structure_quality_gate_bands": _structure_gate_bands(structure_quality_values),
        "avg_bias200": _avg(bias200_values),
        "target_counts": target_counts,
        "pnl_sign_counts": pnl_sign_counts,
        "quality_sign_counts": quality_sign_counts,
        "canonical_true_negative_rows": canonical_true_negative_rows,
        "canonical_true_negative_share": round(canonical_true_negative_rows / len(rows), 4) if rows else None,
        "missing_input_rows": missing_input_rows,
        "missing_input_feature_counts": missing_input_feature_counts,
    }



def _scope_spillover_vs_exact_live_lane(
    scoped_rows: List[Dict[str, Any]],
    exact_scoped_rows: List[Dict[str, Any]],
    scope_info: Dict[str, Any],
    exact_scope_info: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    scope_rows = int(scope_info.get("rows") or 0)
    exact_rows = int(exact_scope_info.get("rows") or 0)
    extra_rows = max(0, scope_rows - exact_rows)
    if extra_rows <= 0:
        return None

    scope_regime_gate_counts = scope_info.get("recent500_regime_gate_counts") or {}
    exact_regime_gate_counts = exact_scope_info.get("recent500_regime_gate_counts") or {}
    spillover_regime_gate_counts = _subtract_count_maps(scope_regime_gate_counts, exact_regime_gate_counts)

    scope_gate_counts = scope_info.get("recent500_gate_counts") or {}
    exact_gate_counts = exact_scope_info.get("recent500_gate_counts") or {}
    spillover_gate_counts = _subtract_count_maps(scope_gate_counts, exact_gate_counts)

    exact_win_rate = exact_scope_info.get("win_rate")
    exact_pnl = exact_scope_info.get("avg_pnl")
    exact_quality = exact_scope_info.get("avg_quality")
    exact_dd = exact_scope_info.get("avg_drawdown_penalty")
    exact_tuw = exact_scope_info.get("avg_time_underwater")

    scope_win_rate = scope_info.get("win_rate")
    scope_pnl = scope_info.get("avg_pnl")
    scope_quality = scope_info.get("avg_quality")
    scope_dd = scope_info.get("avg_drawdown_penalty")
    scope_tuw = scope_info.get("avg_time_underwater")

    exact_keys = {_scope_row_identity(row) for row in exact_scoped_rows}
    spillover_rows = [row for row in scoped_rows if _scope_row_identity(row) not in exact_keys]
    spillover_regime_gate_metrics = _summarize_regime_gate_pockets(spillover_rows)
    worst_spillover_regime_gate = _pick_worst_regime_gate_pocket(spillover_regime_gate_metrics)
    worst_spillover_contrast = None
    gate_input_features = (
        "feat_4h_bias200",
        "feat_4h_bb_pct_b",
        "feat_4h_dist_bb_lower",
        "feat_4h_dist_swing_low",
    )
    worst_spillover_feature_snapshot = None
    worst_spillover_gate_path_summary = None
    exact_live_gate_path_summary = _summarize_gate_path(exact_scoped_rows)
    if worst_spillover_regime_gate and worst_spillover_regime_gate.get("regime_gate"):
        target_regime_gate = worst_spillover_regime_gate.get("regime_gate")
        worst_spillover_rows = [
            row for row in spillover_rows
            if f"{row.get('regime_label') or 'unknown'}|{row.get('regime_gate') or 'unknown'}" == target_regime_gate
        ]
        worst_spillover_contrast = _reference_window_contrast(
            worst_spillover_rows,
            exact_scoped_rows,
            feature_keys=gate_input_features,
        )
        worst_spillover_feature_snapshot = _feature_mean_snapshot(
            worst_spillover_rows,
            exact_scoped_rows,
            feature_keys=gate_input_features,
        )
        worst_spillover_gate_path_summary = _summarize_gate_path(worst_spillover_rows)

    return {
        "extra_rows": extra_rows,
        "extra_row_share": round(float(extra_rows) / float(scope_rows), 4) if scope_rows > 0 else None,
        "extra_gate_counts": spillover_gate_counts,
        "extra_dominant_gate": _dominant_gate_summary(spillover_gate_counts),
        "extra_regime_gate_counts": spillover_regime_gate_counts,
        "extra_dominant_regime_gate": _dominant_regime_gate_summary(spillover_regime_gate_counts),
        "extra_regime_gate_metrics": spillover_regime_gate_metrics,
        "worst_extra_regime_gate": worst_spillover_regime_gate,
        "worst_extra_regime_gate_feature_contrast": worst_spillover_contrast,
        "worst_extra_regime_gate_feature_snapshot": worst_spillover_feature_snapshot,
        "worst_extra_regime_gate_path_summary": worst_spillover_gate_path_summary,
        "exact_live_gate_path_summary": exact_live_gate_path_summary,
        "win_rate_delta_vs_exact": _round_optional(
            None if scope_win_rate is None or exact_win_rate is None else float(scope_win_rate) - float(exact_win_rate)
        ),
        "avg_pnl_delta_vs_exact": _round_optional(
            None if scope_pnl is None or exact_pnl is None else float(scope_pnl) - float(exact_pnl)
        ),
        "avg_quality_delta_vs_exact": _round_optional(
            None if scope_quality is None or exact_quality is None else float(scope_quality) - float(exact_quality)
        ),
        "avg_drawdown_penalty_delta_vs_exact": _round_optional(
            None if scope_dd is None or exact_dd is None else float(scope_dd) - float(exact_dd)
        ),
        "avg_time_underwater_delta_vs_exact": _round_optional(
            None if scope_tuw is None or exact_tuw is None else float(scope_tuw) - float(exact_tuw)
        ),
    }


def _build_decision_quality_scope_diagnostics(
    rows: List[Dict[str, Any]],
    decision_profile: Dict[str, Any],
) -> Dict[str, Any]:
    if not rows:
        return {}

    target_gate = decision_profile.get("regime_gate")
    target_quality_label = decision_profile.get("entry_quality_label")
    target_regime_label = decision_profile.get("regime_label")
    target_structure_bucket = decision_profile.get("structure_bucket")

    scope_rows = {
        "regime_label+regime_gate+entry_quality_label": [
            row for row in rows
            if row.get("regime_label") == target_regime_label
            and row.get("regime_gate") == target_gate
            and row.get("entry_quality_label") == target_quality_label
        ],
        "regime_gate+entry_quality_label": [
            row for row in rows
            if row.get("regime_gate") == target_gate and row.get("entry_quality_label") == target_quality_label
        ],
        "regime_gate": [row for row in rows if row.get("regime_gate") == target_gate],
        "entry_quality_label": [row for row in rows if row.get("entry_quality_label") == target_quality_label],
        "regime_label+entry_quality_label": [
            row for row in rows
            if row.get("regime_label") == target_regime_label and row.get("entry_quality_label") == target_quality_label
        ],
        "regime_label": [row for row in rows if row.get("regime_label") == target_regime_label],
        "global": list(rows),
    }

    diagnostics: Dict[str, Any] = {}
    for scope_name, scoped_rows in scope_rows.items():
        if not scoped_rows:
            diagnostics[scope_name] = {
                "rows": 0,
                "alerts": ["no_rows"],
                "win_rate": None,
                "avg_pnl": None,
                "avg_quality": None,
                "avg_drawdown_penalty": None,
                "avg_time_underwater": None,
                "recent500_regime_counts": {},
                "recent500_dominant_regime": None,
                "recent500_gate_counts": {},
                "recent500_dominant_gate": None,
                "recent500_regime_gate_counts": {},
                "recent500_dominant_regime_gate": None,
                "recent500_structure_bucket_counts": {},
                "recent500_dominant_structure_bucket": None,
                "current_live_structure_bucket": target_structure_bucket,
                "current_live_structure_bucket_rows": 0,
                "current_live_structure_bucket_share": None,
                "current_live_structure_bucket_metrics": None,
                "exact_lane_bucket_diagnostics": {
                    "bucket_count": 0,
                    "buckets": {},
                    "toxic_bucket": None,
                    "verdict": "no_exact_lane_rows",
                    "reason": "exact live lane 沒有 rows，無法做子 bucket 診斷。",
                },
                "recent_pathology": {
                    "applied": False,
                    "window": 0,
                    "alerts": [],
                    "reason": None,
                    "summary": None,
                },
            }
            continue
        regime_counts = _recent_scope_regime_counts(scoped_rows)
        gate_counts = _recent_scope_gate_counts(scoped_rows)
        regime_gate_counts = _recent_scope_regime_gate_counts(scoped_rows)
        structure_bucket_counts = _recent_scope_structure_bucket_counts(scoped_rows)
        bucket_rows = [
            row for row in scoped_rows
            if target_structure_bucket and row.get("structure_bucket") == target_structure_bucket
        ]
        bucket_rows_count = len(bucket_rows)
        diagnostics[scope_name] = {
            "rows": len(scoped_rows),
            "alerts": _decision_quality_scope_alerts(scoped_rows),
            "win_rate": _avg_metric(scoped_rows, "simulated_pyramid_win"),
            "avg_pnl": _avg_metric(scoped_rows, "simulated_pyramid_pnl"),
            "avg_quality": _avg_metric(scoped_rows, "simulated_pyramid_quality"),
            "avg_drawdown_penalty": _avg_metric(scoped_rows, "simulated_pyramid_drawdown_penalty"),
            "avg_time_underwater": _avg_metric(scoped_rows, "simulated_pyramid_time_underwater"),
            "recent500_regime_counts": regime_counts,
            "recent500_dominant_regime": _dominant_regime_summary(regime_counts),
            "recent500_gate_counts": gate_counts,
            "recent500_dominant_gate": _dominant_gate_summary(gate_counts),
            "recent500_regime_gate_counts": regime_gate_counts,
            "recent500_dominant_regime_gate": _dominant_regime_gate_summary(regime_gate_counts),
            "recent500_structure_bucket_counts": structure_bucket_counts,
            "recent500_dominant_structure_bucket": _dominant_structure_bucket_summary(structure_bucket_counts),
            "current_live_structure_bucket": target_structure_bucket,
            "current_live_structure_bucket_rows": bucket_rows_count,
            "current_live_structure_bucket_share": _round_optional(
                bucket_rows_count / len(scoped_rows) if target_structure_bucket and scoped_rows else None
            ),
            "current_live_structure_bucket_metrics": _scope_metric_summary(bucket_rows),
            "exact_lane_bucket_diagnostics": _exact_live_lane_bucket_diagnostics(
                scoped_rows if scope_name == "regime_label+regime_gate+entry_quality_label" else [],
                target_structure_bucket,
            ),
            "recent_pathology": _recent_scope_pathology_summary(scoped_rows),
        }

    exact_live_scope_name = "regime_label+regime_gate+entry_quality_label"
    exact_live_scope = diagnostics.get(exact_live_scope_name) or {}
    exact_live_scope_rows = scope_rows.get(exact_live_scope_name) or []
    diagnostics.setdefault(exact_live_scope_name, {})["spillover_vs_exact_live_lane"] = None
    for scope_name in (
        "regime_gate+entry_quality_label",
        "regime_label+entry_quality_label",
        "entry_quality_label",
        "regime_gate",
        "regime_label",
        "global",
    ):
        scope_info = diagnostics.get(scope_name) or {}
        scope_info["spillover_vs_exact_live_lane"] = _scope_spillover_vs_exact_live_lane(
            scope_rows.get(scope_name) or [],
            exact_live_scope_rows,
            scope_info,
            exact_live_scope,
        )

    focus_scopes = (
        exact_live_scope_name,
        "regime_gate+entry_quality_label",
        "regime_label+entry_quality_label",
        "entry_quality_label",
    )
    pathological_scope_rows: List[Dict[str, Any]] = []
    shared_feature_map: Dict[str, Dict[str, Any]] = {}
    for scope_name in focus_scopes:
        scope_info = diagnostics.get(scope_name) or {}
        recent = scope_info.get("recent_pathology") or {}
        summary = recent.get("summary") or {}
        reference = summary.get("reference_window_comparison") or {}
        top_shifts = reference.get("top_mean_shift_features") or []
        if not recent.get("applied") or not top_shifts:
            continue
        pathological_scope_rows.append(
            {
                "scope": scope_name,
                "rows": scope_info.get("rows"),
                "win_rate": scope_info.get("win_rate"),
                "avg_quality": scope_info.get("avg_quality"),
                "avg_drawdown_penalty": scope_info.get("avg_drawdown_penalty"),
                "avg_time_underwater": scope_info.get("avg_time_underwater"),
                "window": recent.get("window"),
                "alerts": recent.get("alerts") or [],
                "recent500_regime_counts": scope_info.get("recent500_regime_counts") or {},
                "recent500_dominant_regime": scope_info.get("recent500_dominant_regime"),
                "recent500_gate_counts": scope_info.get("recent500_gate_counts") or {},
                "recent500_dominant_gate": scope_info.get("recent500_dominant_gate"),
                "recent500_regime_gate_counts": scope_info.get("recent500_regime_gate_counts") or {},
                "recent500_dominant_regime_gate": scope_info.get("recent500_dominant_regime_gate"),
            }
        )
        for shift in top_shifts:
            feature = shift.get("feature")
            if not feature:
                continue
            entry = shared_feature_map.setdefault(
                feature,
                {
                    "feature": feature,
                    "scope_count": 0,
                    "scopes": [],
                    "mean_deltas": {},
                    "current_means": {},
                    "reference_means": {},
                },
            )
            entry["scope_count"] += 1
            entry["scopes"].append(scope_name)
            entry["mean_deltas"][scope_name] = shift.get("mean_delta")
            entry["current_means"][scope_name] = shift.get("current_mean")
            entry["reference_means"][scope_name] = shift.get("reference_mean")

    consensus_features: List[Dict[str, Any]] = []
    for entry in shared_feature_map.values():
        if entry["scope_count"] < 2:
            continue
        max_abs_delta = max(abs(float(v or 0.0)) for v in entry["mean_deltas"].values()) if entry["mean_deltas"] else 0.0
        consensus_features.append(
            {
                **entry,
                "scopes": sorted(entry["scopes"]),
                "max_abs_delta": round(float(max_abs_delta), 4),
            }
        )
    consensus_features.sort(
        key=lambda row: (-int(row.get("scope_count") or 0), -float(row.get("max_abs_delta") or 0.0), row.get("feature") or "")
    )

    if pathological_scope_rows:
        pathological_scope_rows.sort(
            key=lambda row: (
                float(row.get("win_rate") if row.get("win_rate") is not None else 1.0),
                float(row.get("avg_quality") if row.get("avg_quality") is not None else 1.0),
                int(row.get("rows") or 0),
            )
        )
        diagnostics["pathology_consensus"] = {
            "pathology_scope_count": len(pathological_scope_rows),
            "pathology_scopes": pathological_scope_rows,
            "worst_pathology_scope": pathological_scope_rows[0],
            "shared_top_shift_features": consensus_features[:3],
        }
    else:
        diagnostics["pathology_consensus"] = {
            "pathology_scope_count": 0,
            "pathology_scopes": [],
            "worst_pathology_scope": None,
            "shared_top_shift_features": [],
        }
    return diagnostics


def _min_optional(current: Optional[float], other: Optional[float]) -> Optional[float]:
    if current is None:
        return other
    if other is None:
        return current
    return round(min(float(current), float(other)), 4)


def _max_optional(current: Optional[float], other: Optional[float]) -> Optional[float]:
    if current is None:
        return other
    if other is None:
        return current
    return round(max(float(current), float(other)), 4)


def _exact_live_lane_toxicity_guardrail(
    decision_profile: Dict[str, Any],
    chosen_scope: Optional[str],
    scope_diagnostics: Dict[str, Any],
    expected_win_rate: Optional[float],
    expected_pnl: Optional[float],
    expected_quality: Optional[float],
    expected_drawdown_penalty: Optional[float],
    expected_time_underwater: Optional[float],
) -> Dict[str, Any]:
    exact_scope_name = "regime_label+regime_gate+entry_quality_label"
    exact_scope = (scope_diagnostics or {}).get(exact_scope_name) or {}
    bucket_diagnostics = exact_scope.get("exact_lane_bucket_diagnostics") or {}
    toxic_bucket = bucket_diagnostics.get("toxic_bucket") or {}
    default_result = {
        "applied": False,
        "status": None,
        "reason": None,
        "summary": None,
        "bucket_verdict": bucket_diagnostics.get("verdict"),
        "bucket_reason": bucket_diagnostics.get("reason"),
        "bucket_diagnostics": bucket_diagnostics,
        "toxic_bucket": toxic_bucket or None,
        "expected_win_rate": expected_win_rate,
        "expected_pnl": expected_pnl,
        "expected_quality": expected_quality,
        "expected_drawdown_penalty": expected_drawdown_penalty,
        "expected_time_underwater": expected_time_underwater,
    }

    current_bucket = str(decision_profile.get("structure_bucket") or "")
    toxic_bucket_name = str(toxic_bucket.get("bucket") or "")
    toxic_bucket_rows = int(toxic_bucket.get("rows") or 0)
    toxic_bucket_matches_current = (
        bucket_diagnostics.get("verdict") == "toxic_sub_bucket_identified"
        and current_bucket
        and toxic_bucket_name == current_bucket
        and toxic_bucket_rows > 0
    )
    if toxic_bucket_matches_current:
        summary = {
            "scope": exact_scope_name,
            "rows": toxic_bucket_rows,
            "regime_label": decision_profile.get("regime_label"),
            "regime_gate": decision_profile.get("regime_gate"),
            "entry_quality_label": decision_profile.get("entry_quality_label"),
            "structure_bucket": toxic_bucket_name,
            "win_rate": _round_optional(toxic_bucket.get("win_rate")),
            "avg_pnl": _round_optional(toxic_bucket.get("avg_pnl")),
            "avg_quality": _round_optional(toxic_bucket.get("avg_quality")),
            "avg_drawdown_penalty": _round_optional(toxic_bucket.get("avg_drawdown_penalty")),
            "avg_time_underwater": _round_optional(toxic_bucket.get("avg_time_underwater")),
            "vs_current_bucket": toxic_bucket.get("vs_current_bucket"),
        }
        reason = (
            f"exact live lane current bucket `{current_bucket}` 已被標記為 toxic sub-bucket "
            f"(rows={toxic_bucket_rows}, win_rate={summary['win_rate']}, quality={summary['avg_quality']})"
        )
        return {
            **default_result,
            "applied": True,
            "status": "toxic_sub_bucket_current_bucket",
            "reason": reason,
            "summary": summary,
            "expected_win_rate": _min_optional(expected_win_rate, toxic_bucket.get("win_rate")),
            "expected_pnl": _min_optional(expected_pnl, toxic_bucket.get("avg_pnl")),
            "expected_quality": _min_optional(expected_quality, toxic_bucket.get("avg_quality")),
            "expected_drawdown_penalty": _max_optional(expected_drawdown_penalty, toxic_bucket.get("avg_drawdown_penalty")),
            "expected_time_underwater": _max_optional(expected_time_underwater, toxic_bucket.get("avg_time_underwater")),
        }

    if chosen_scope == exact_scope_name:
        return default_result

    exact_rows = int(exact_scope.get("rows") or 0)
    if exact_rows < 20:
        return default_result

    target_regime = str(decision_profile.get("regime_label") or "")
    target_gate = str(decision_profile.get("regime_gate") or "")
    target_label = str(decision_profile.get("entry_quality_label") or "")
    dominant_regime_gate = exact_scope.get("recent500_dominant_regime_gate") or {}
    if (
        str(dominant_regime_gate.get("regime") or "") != target_regime
        or str(dominant_regime_gate.get("gate") or "") != target_gate
        or float(dominant_regime_gate.get("share") or 0.0) < 0.8
    ):
        return default_result

    exact_gate_path_summary = None
    for scope_name, scope_info in (scope_diagnostics or {}).items():
        if scope_name == exact_scope_name or not isinstance(scope_info, dict):
            continue
        spillover = scope_info.get("spillover_vs_exact_live_lane") or {}
        candidate = spillover.get("exact_live_gate_path_summary")
        if candidate:
            exact_gate_path_summary = candidate
            break
    if not isinstance(exact_gate_path_summary, dict):
        return default_result

    final_gate_counts = exact_gate_path_summary.get("final_gate_counts") or {}
    allow_rows = int(final_gate_counts.get("ALLOW") or 0)
    gate_rows = int(exact_gate_path_summary.get("rows") or exact_rows)
    allow_share = (allow_rows / gate_rows) if gate_rows > 0 else 0.0
    true_negative_share = exact_gate_path_summary.get("canonical_true_negative_share")
    true_negative_share = float(true_negative_share) if true_negative_share is not None else None
    exact_win_rate = exact_scope.get("win_rate")
    exact_pnl = exact_scope.get("avg_pnl")
    exact_quality = exact_scope.get("avg_quality")
    exact_drawdown_penalty = exact_scope.get("avg_drawdown_penalty")
    exact_time_underwater = exact_scope.get("avg_time_underwater")

    toxic_allow_lane = (
        allow_rows > 0
        and allow_share >= 0.8
        and true_negative_share is not None
        and true_negative_share >= 0.65
        and (
            (exact_win_rate is not None and float(exact_win_rate) <= 0.35)
            or (exact_pnl is not None and float(exact_pnl) < 0)
            or (exact_quality is not None and float(exact_quality) <= 0.05)
        )
    )
    if not toxic_allow_lane:
        return default_result

    summary = {
        "scope": exact_scope_name,
        "rows": exact_rows,
        "regime_label": target_regime or None,
        "regime_gate": target_gate or None,
        "entry_quality_label": target_label or None,
        "win_rate": _round_optional(exact_win_rate),
        "avg_pnl": _round_optional(exact_pnl),
        "avg_quality": _round_optional(exact_quality),
        "avg_drawdown_penalty": _round_optional(exact_drawdown_penalty),
        "avg_time_underwater": _round_optional(exact_time_underwater),
        "allow_rows": allow_rows,
        "allow_share": round(float(allow_share), 4),
        "canonical_true_negative_share": round(float(true_negative_share), 4),
        "final_gate_counts": final_gate_counts,
    }
    reason = (
        f"exact {target_regime}/{target_gate}/{target_label} lane stays ALLOW but is toxic "
        f"(rows={exact_rows}, win_rate={summary['win_rate']}, quality={summary['avg_quality']}, "
        f"true_negative_share={summary['canonical_true_negative_share']}, allow_share={summary['allow_share']})"
    )
    return {
        **default_result,
        "applied": True,
        "status": "toxic_allow_lane",
        "reason": reason,
        "summary": summary,
        "expected_win_rate": _min_optional(expected_win_rate, exact_win_rate),
        "expected_pnl": _min_optional(expected_pnl, exact_pnl),
        "expected_quality": _min_optional(expected_quality, exact_quality),
        "expected_drawdown_penalty": _max_optional(expected_drawdown_penalty, exact_drawdown_penalty),
        "expected_time_underwater": _max_optional(expected_time_underwater, exact_time_underwater),
    }



def _narrowed_regime_scope_downside_guardrail(
    decision_profile: Dict[str, Any],
    chosen_scope: Optional[str],
    scope_diagnostics: Dict[str, Any],
    expected_win_rate: Optional[float],
    expected_pnl: Optional[float],
    expected_quality: Optional[float],
    expected_drawdown_penalty: Optional[float],
    expected_time_underwater: Optional[float],
) -> Dict[str, Any]:
    default_result = {
        "applied": False,
        "scope": None,
        "reason": None,
        "expected_win_rate": expected_win_rate,
        "expected_pnl": expected_pnl,
        "expected_quality": expected_quality,
        "expected_drawdown_penalty": expected_drawdown_penalty,
        "expected_time_underwater": expected_time_underwater,
    }

    target_regime = str(decision_profile.get("regime_label") or "")
    target_gate = str(decision_profile.get("regime_gate") or "")
    candidate_scopes = [
        "regime_label+regime_gate+entry_quality_label",
        "regime_label+entry_quality_label",
    ]
    if chosen_scope in candidate_scopes:
        return default_result

    for scope_name in candidate_scopes:
        narrowed_scope = (scope_diagnostics or {}).get(scope_name) or {}
        if not narrowed_scope:
            continue

        dominant = narrowed_scope.get("recent500_dominant_regime") or {}
        dominant_regime = str(dominant.get("regime") or "")
        dominant_share = float(dominant.get("share") or 0.0)
        if not target_regime or dominant_regime != target_regime or dominant_share < 0.8:
            continue

        if scope_name == "regime_label+regime_gate+entry_quality_label":
            current_gate = str(decision_profile.get("regime_gate") or "")
            scope_rows_for_gate = int(narrowed_scope.get("rows") or 0)
            if not current_gate or scope_rows_for_gate < 30:
                continue
        narrowed_alerts = list(narrowed_scope.get("alerts") or [])
        narrowed_rows = int(narrowed_scope.get("rows") or 0)
        if narrowed_rows < 30:
            continue

        recent_pathology = narrowed_scope.get("recent_pathology") or {}
        narrowed_win_rate = narrowed_scope.get("win_rate")
        narrowed_pnl = narrowed_scope.get("avg_pnl")
        narrowed_quality = narrowed_scope.get("avg_quality")
        narrowed_summary = recent_pathology.get("summary") or {}
        if recent_pathology.get("applied"):
            narrowed_win_rate = _min_optional(narrowed_win_rate, narrowed_summary.get("win_rate"))
            narrowed_pnl = _min_optional(narrowed_pnl, narrowed_summary.get("avg_pnl"))
            narrowed_quality = _min_optional(narrowed_quality, narrowed_summary.get("avg_quality"))
        narrowed_dd = _max_optional(
            narrowed_scope.get("avg_drawdown_penalty"),
            narrowed_summary.get("avg_drawdown_penalty"),
        )
        narrowed_tuw = _max_optional(
            narrowed_scope.get("avg_time_underwater"),
            narrowed_summary.get("avg_time_underwater"),
        )
        narrowed_scope_is_pathological = bool(recent_pathology.get("applied")) or (
            any(alert in narrowed_alerts for alert in ("constant_target", "label_imbalance"))
            and (
                (narrowed_win_rate is not None and float(narrowed_win_rate) <= 0.2)
                or (narrowed_pnl is not None and float(narrowed_pnl) < 0)
                or (narrowed_quality is not None and float(narrowed_quality) < 0)
            )
        )
        if not narrowed_scope_is_pathological:
            continue

        is_materially_worse = False
        if narrowed_win_rate is not None and expected_win_rate is not None and float(narrowed_win_rate) + 0.02 < float(expected_win_rate):
            is_materially_worse = True
        if narrowed_quality is not None and expected_quality is not None and float(narrowed_quality) + 0.02 < float(expected_quality):
            is_materially_worse = True
        if not is_materially_worse:
            continue

        reason = (
            f"narrowed {scope_name} lane dominates current {target_regime}/{target_gate} runtime path "
            f"(rows={narrowed_rows}, dominant={dominant_regime}@{round(dominant_share, 4)}, "
            f"win_rate={narrowed_win_rate}, quality={narrowed_quality})"
        )
        if recent_pathology.get("applied") and recent_pathology.get("reason"):
            reason += f"; {recent_pathology.get('reason')}"

        return {
            "applied": True,
            "scope": scope_name,
            "reason": reason,
            "expected_win_rate": _min_optional(expected_win_rate, narrowed_win_rate),
            "expected_pnl": _min_optional(expected_pnl, narrowed_pnl),
            "expected_quality": _min_optional(expected_quality, narrowed_quality),
            "expected_drawdown_penalty": _max_optional(expected_drawdown_penalty, narrowed_dd),
            "expected_time_underwater": _max_optional(expected_time_underwater, narrowed_tuw),
        }

    return default_result


def _structure_bucket_support_guardrail(
    decision_profile: Dict[str, Any],
    chosen_scope: Optional[str],
    scope_diagnostics: Dict[str, Any],
    expected_win_rate: Optional[float],
    expected_pnl: Optional[float],
    expected_quality: Optional[float],
    expected_drawdown_penalty: Optional[float],
    expected_time_underwater: Optional[float],
) -> Dict[str, Any]:
    live_structure_bucket = decision_profile.get("structure_bucket")
    default_result = {
        "applied": False,
        "reason": None,
        "support_mode": None,
        "support_rows": 0,
        "support_share": None,
        "exact_support_rows": 0,
        "exact_support_share": None,
        "supported_neighbor_buckets": [],
        "live_structure_bucket": live_structure_bucket,
        "expected_win_rate": expected_win_rate,
        "expected_pnl": expected_pnl,
        "expected_quality": expected_quality,
        "expected_drawdown_penalty": expected_drawdown_penalty,
        "expected_time_underwater": expected_time_underwater,
    }
    if not chosen_scope or not live_structure_bucket:
        return default_result

    exact_scope_name = "regime_label+regime_gate+entry_quality_label"
    chosen_info = (scope_diagnostics or {}).get(chosen_scope) or {}
    exact_info = (scope_diagnostics or {}).get(exact_scope_name) or {}

    support_rows = int(chosen_info.get("current_live_structure_bucket_rows") or 0)
    support_share = chosen_info.get("current_live_structure_bucket_share")
    support_share = float(support_share) if support_share is not None else None
    support_metrics = chosen_info.get("current_live_structure_bucket_metrics") or {}
    dominant_structure_bucket = (chosen_info.get("recent500_dominant_structure_bucket") or {}).get("structure_bucket")

    exact_support_rows = int(exact_info.get("current_live_structure_bucket_rows") or 0)
    exact_support_share = exact_info.get("current_live_structure_bucket_share")
    exact_support_share = float(exact_support_share) if exact_support_share is not None else None
    exact_support_metrics = exact_info.get("current_live_structure_bucket_metrics") or {}
    exact_bucket_counts = exact_info.get("recent500_structure_bucket_counts") or {}
    supported_neighbor_buckets = [
        bucket
        for bucket, count in exact_bucket_counts.items()
        if bucket != live_structure_bucket and int(count or 0) > 0
    ]

    apply_guardrail = support_rows < 5
    if not apply_guardrail and support_share is not None and dominant_structure_bucket:
        apply_guardrail = support_share < 0.1 and dominant_structure_bucket != live_structure_bucket
    if not apply_guardrail:
        return default_result

    expected_win_rate_new = expected_win_rate
    expected_pnl_new = expected_pnl
    expected_quality_new = expected_quality
    expected_drawdown_penalty_new = expected_drawdown_penalty
    expected_time_underwater_new = expected_time_underwater
    support_mode = "chosen_scope_bucket"

    if exact_support_rows <= 0:
        reason = (
            f"exact live scope {exact_scope_name} has zero support for live structure bucket {live_structure_bucket} "
            f"(chosen_scope={chosen_scope}, chosen_support_rows={support_rows}, chosen_support_share={_round_optional(support_share)})"
            f"; supported_neighbor_buckets={supported_neighbor_buckets or []}"
            f"; broader same-bucket scopes are informational only and cannot authorize this live bucket"
        )
        return {
            "applied": True,
            "reason": reason,
            "support_mode": "exact_bucket_unsupported_block",
            "support_rows": support_rows,
            "support_share": _round_optional(support_share),
            "exact_support_rows": exact_support_rows,
            "exact_support_share": _round_optional(exact_support_share),
            "supported_neighbor_buckets": supported_neighbor_buckets,
            "live_structure_bucket": live_structure_bucket,
            "expected_win_rate": expected_win_rate_new,
            "expected_pnl": expected_pnl_new,
            "expected_quality": expected_quality_new,
            "expected_drawdown_penalty": expected_drawdown_penalty_new,
            "expected_time_underwater": expected_time_underwater_new,
        }

    metrics_to_apply = exact_support_metrics if exact_support_metrics else support_metrics if support_metrics else None
    if metrics_to_apply is exact_support_metrics and exact_support_metrics:
        support_mode = "exact_bucket_supported"

    if metrics_to_apply:
        expected_win_rate_new = _min_optional(expected_win_rate_new, metrics_to_apply.get("win_rate"))
        expected_pnl_new = _min_optional(expected_pnl_new, metrics_to_apply.get("avg_pnl"))
        expected_quality_new = _min_optional(expected_quality_new, metrics_to_apply.get("avg_quality"))
        expected_drawdown_penalty_new = _max_optional(
            expected_drawdown_penalty_new,
            metrics_to_apply.get("avg_drawdown_penalty"),
        )
        expected_time_underwater_new = _max_optional(
            expected_time_underwater_new,
            metrics_to_apply.get("avg_time_underwater"),
        )

    reason = (
        f"chosen scope {chosen_scope} has weak support for live structure bucket {live_structure_bucket} "
        f"(support_rows={support_rows}, support_share={_round_optional(support_share)}, "
        f"dominant_bucket={dominant_structure_bucket or 'unknown'})"
        f"; exact_scope_rows={exact_support_rows}, exact_scope_share={_round_optional(exact_support_share)}"
        f"; supported_neighbor_buckets={supported_neighbor_buckets or []}"
    )
    return {
        "applied": True,
        "reason": reason,
        "support_mode": support_mode,
        "support_rows": support_rows,
        "support_share": _round_optional(support_share),
        "exact_support_rows": exact_support_rows,
        "exact_support_share": _round_optional(exact_support_share),
        "supported_neighbor_buckets": supported_neighbor_buckets,
        "live_structure_bucket": live_structure_bucket,
        "expected_win_rate": expected_win_rate_new,
        "expected_pnl": expected_pnl_new,
        "expected_quality": expected_quality_new,
        "expected_drawdown_penalty": expected_drawdown_penalty_new,
        "expected_time_underwater": expected_time_underwater_new,
    }



def _summarize_decision_quality_contract(
    rows: List[Dict[str, Any]],
    decision_profile: Dict[str, Any],
    horizon_minutes: int = 1440,
    enforce_scope_guardrails: bool = False,
) -> Dict[str, Any]:
    base = _decision_quality_fallback(decision_profile.get("decision_profile_version") or "phase16_baseline_v2")
    if not rows:
        return base

    target_gate = decision_profile.get("regime_gate")
    target_quality_label = decision_profile.get("entry_quality_label")
    target_regime_label = decision_profile.get("regime_label")
    selection_lanes = []
    if target_regime_label:
        selection_lanes.append(
            (
                "regime_label+regime_gate+entry_quality_label",
                lambda row: row.get("regime_label") == target_regime_label
                and row.get("regime_gate") == target_gate
                and row.get("entry_quality_label") == target_quality_label,
                30,
            )
        )
    selection_lanes.append(
        ("regime_gate+entry_quality_label", lambda row: row.get("regime_gate") == target_gate and row.get("entry_quality_label") == target_quality_label, 30)
    )
    if target_regime_label:
        selection_lanes.extend([
            ("regime_label+entry_quality_label", lambda row: row.get("regime_label") == target_regime_label and row.get("entry_quality_label") == target_quality_label, 30),
            ("regime_label", lambda row: row.get("regime_label") == target_regime_label, 50),
        ])
    selection_lanes.extend([
        ("regime_gate", lambda row: row.get("regime_gate") == target_gate, 50),
        ("entry_quality_label", lambda row: row.get("entry_quality_label") == target_quality_label, 50),
        ("global", lambda row: True, 1),
    ])

    chosen_scope = None
    chosen_rows: List[Dict[str, Any]] = []
    scope_guardrail_applied = False
    scope_guardrail_reason = None
    scope_guardrail_reasons: List[str] = []
    scope_guardrail_alerts: List[str] = []
    rejected_semantic_scope: Optional[tuple[str, List[Dict[str, Any]]]] = None
    semantic_scope_priority = {
        "regime_label+regime_gate+entry_quality_label": 0,
        "regime_label+entry_quality_label": 1,
        "regime_label": 2,
    }
    for scope_name, predicate, min_rows in selection_lanes:
        scoped_rows = [row for row in rows if predicate(row)]
        if len(scoped_rows) < min_rows:
            continue
        scope_alerts = _decision_quality_scope_alerts(scoped_rows)
        scope_win_rate = _avg_metric(scoped_rows, "simulated_pyramid_win")
        scope_pnl = _avg_metric(scoped_rows, "simulated_pyramid_pnl")
        scope_quality = _avg_metric(scoped_rows, "simulated_pyramid_quality")
        reject_scope = False
        reject_reason = None
        if "constant_target" in scope_alerts:
            reject_scope = True
        elif "label_imbalance" in scope_alerts:
            reject_scope = any(
                condition
                for condition in (
                    scope_win_rate is not None and float(scope_win_rate) <= 0.2,
                    scope_pnl is not None and float(scope_pnl) < 0,
                    scope_quality is not None and float(scope_quality) < 0,
                )
            )
        if reject_scope:
            reject_reason = (
                f"scope {scope_name} rejected via alerts={scope_alerts} "
                f"(rows={len(scoped_rows)}, win_rate={_round_optional(scope_win_rate)}, "
                f"pnl={_round_optional(scope_pnl)}, quality={_round_optional(scope_quality)})"
            )

        if (
            enforce_scope_guardrails
            and target_regime_label
            and scope_name in {"regime_gate+entry_quality_label", "entry_quality_label", "regime_gate"}
        ):
            recent_rows = scoped_rows[-500:]
            regime_counts = Counter(
                str(row.get("regime_label") or "unknown")
                for row in recent_rows
                if row.get("regime_label") is not None
            )
            dominant_regime = _dominant_regime_summary(regime_counts)
            dominant_regime_label = str((dominant_regime or {}).get("regime") or "")
            dominant_regime_share = float((dominant_regime or {}).get("share") or 0.0)
            if (
                dominant_regime_label
                and dominant_regime_label != target_regime_label
                and dominant_regime_share >= 0.8
            ):
                reject_scope = True
                reject_reason = (
                    f"scope {scope_name} rejected via dominant recent regime mismatch "
                    f"(target={target_regime_label}, dominant={dominant_regime_label}@{round(dominant_regime_share, 4)}, "
                    f"rows={len(scoped_rows)})"
                )

        if enforce_scope_guardrails and scope_name != "global" and reject_scope:
            scope_guardrail_applied = True
            scope_guardrail_alerts = sorted(set(scope_guardrail_alerts).union(scope_alerts))
            if reject_reason:
                scope_guardrail_reasons.append(reject_reason)
            scope_guardrail_reason = "; ".join(scope_guardrail_reasons) if scope_guardrail_reasons else None
            if scope_name in semantic_scope_priority and (
                rejected_semantic_scope is None
                or semantic_scope_priority[scope_name] < semantic_scope_priority[rejected_semantic_scope[0]]
            ):
                rejected_semantic_scope = (scope_name, scoped_rows)
            continue
        chosen_scope = scope_name
        chosen_rows = scoped_rows
        break
    if chosen_scope == "global" and rejected_semantic_scope is not None:
        chosen_scope, chosen_rows = rejected_semantic_scope
        fallback_reason = (
            f"retained same-regime fallback {chosen_scope} after broader lanes were rejected"
        )
        scope_guardrail_reasons.append(fallback_reason)
        scope_guardrail_reason = "; ".join(scope_guardrail_reasons) if scope_guardrail_reasons else fallback_reason
    if not chosen_rows:
        return base

    expected_win_rate = _avg_metric(chosen_rows, "simulated_pyramid_win")
    expected_pnl = _avg_metric(chosen_rows, "simulated_pyramid_pnl")
    expected_quality = _avg_metric(chosen_rows, "simulated_pyramid_quality")
    expected_drawdown_penalty = _avg_metric(chosen_rows, "simulated_pyramid_drawdown_penalty")
    expected_time_underwater = _avg_metric(chosen_rows, "simulated_pyramid_time_underwater")

    recent_pathology = _recent_scope_pathology_summary(chosen_rows)
    if recent_pathology.get("applied"):
        pathology_summary = recent_pathology.get("summary") or {}
        expected_win_rate = _min_optional(expected_win_rate, pathology_summary.get("win_rate"))
        expected_pnl = _min_optional(expected_pnl, pathology_summary.get("avg_pnl"))
        expected_quality = _min_optional(expected_quality, pathology_summary.get("avg_quality"))
        expected_drawdown_penalty = _max_optional(expected_drawdown_penalty, pathology_summary.get("avg_drawdown_penalty"))
        expected_time_underwater = _max_optional(expected_time_underwater, pathology_summary.get("avg_time_underwater"))

    scope_diagnostics = _build_decision_quality_scope_diagnostics(rows, decision_profile)
    exact_live_lane_guardrail = _exact_live_lane_toxicity_guardrail(
        decision_profile,
        chosen_scope,
        scope_diagnostics,
        expected_win_rate,
        expected_pnl,
        expected_quality,
        expected_drawdown_penalty,
        expected_time_underwater,
    )
    expected_win_rate = exact_live_lane_guardrail["expected_win_rate"]
    expected_pnl = exact_live_lane_guardrail["expected_pnl"]
    expected_quality = exact_live_lane_guardrail["expected_quality"]
    expected_drawdown_penalty = exact_live_lane_guardrail["expected_drawdown_penalty"]
    expected_time_underwater = exact_live_lane_guardrail["expected_time_underwater"]

    narrowed_scope_guardrail = _narrowed_regime_scope_downside_guardrail(
        decision_profile,
        chosen_scope,
        scope_diagnostics,
        expected_win_rate,
        expected_pnl,
        expected_quality,
        expected_drawdown_penalty,
        expected_time_underwater,
    )
    expected_win_rate = narrowed_scope_guardrail["expected_win_rate"]
    expected_pnl = narrowed_scope_guardrail["expected_pnl"]
    expected_quality = narrowed_scope_guardrail["expected_quality"]
    expected_drawdown_penalty = narrowed_scope_guardrail["expected_drawdown_penalty"]
    expected_time_underwater = narrowed_scope_guardrail["expected_time_underwater"]

    structure_bucket_guardrail = _structure_bucket_support_guardrail(
        decision_profile,
        chosen_scope,
        scope_diagnostics,
        expected_win_rate,
        expected_pnl,
        expected_quality,
        expected_drawdown_penalty,
        expected_time_underwater,
    )
    expected_win_rate = structure_bucket_guardrail["expected_win_rate"]
    expected_pnl = structure_bucket_guardrail["expected_pnl"]
    expected_quality = structure_bucket_guardrail["expected_quality"]
    expected_drawdown_penalty = structure_bucket_guardrail["expected_drawdown_penalty"]
    expected_time_underwater = structure_bucket_guardrail["expected_time_underwater"]

    decision_quality_score = _compute_decision_quality_score(
        expected_win_rate,
        expected_quality,
        expected_drawdown_penalty,
        expected_time_underwater,
    )
    latest_ts = max((row.get("timestamp") for row in chosen_rows if row.get("timestamp") is not None), default=None)

    return {
        **base,
        "decision_quality_horizon_minutes": horizon_minutes,
        "decision_quality_calibration_scope": chosen_scope,
        "decision_quality_scope_diagnostics": scope_diagnostics,
        "decision_quality_sample_size": len(chosen_rows),
        "decision_quality_reference_from": str(latest_ts) if latest_ts is not None else None,
        "decision_quality_calibration_window": len(rows),
        "decision_quality_scope_guardrail_applied": scope_guardrail_applied,
        "decision_quality_scope_guardrail_reason": scope_guardrail_reason,
        "decision_quality_scope_guardrail_alerts": scope_guardrail_alerts,
        "decision_quality_recent_pathology_applied": bool(recent_pathology.get("applied")),
        "decision_quality_recent_pathology_reason": recent_pathology.get("reason"),
        "decision_quality_recent_pathology_window": int(recent_pathology.get("window") or 0),
        "decision_quality_recent_pathology_alerts": list(recent_pathology.get("alerts") or []),
        "decision_quality_recent_pathology_summary": recent_pathology.get("summary"),
        "decision_quality_exact_live_lane_toxicity_applied": bool(exact_live_lane_guardrail.get("applied")),
        "decision_quality_exact_live_lane_status": exact_live_lane_guardrail.get("status"),
        "decision_quality_exact_live_lane_reason": exact_live_lane_guardrail.get("reason"),
        "decision_quality_exact_live_lane_summary": exact_live_lane_guardrail.get("summary"),
        "decision_quality_exact_live_lane_bucket_verdict": exact_live_lane_guardrail.get("bucket_verdict"),
        "decision_quality_exact_live_lane_bucket_reason": exact_live_lane_guardrail.get("bucket_reason"),
        "decision_quality_exact_live_lane_toxic_bucket": exact_live_lane_guardrail.get("toxic_bucket"),
        "decision_quality_exact_live_lane_bucket_diagnostics": exact_live_lane_guardrail.get("bucket_diagnostics"),
        "decision_quality_live_structure_bucket": structure_bucket_guardrail.get("live_structure_bucket"),
        "decision_quality_structure_bucket_guardrail_applied": bool(structure_bucket_guardrail.get("applied")),
        "decision_quality_structure_bucket_guardrail_reason": structure_bucket_guardrail.get("reason"),
        "decision_quality_structure_bucket_support_mode": structure_bucket_guardrail.get("support_mode"),
        "decision_quality_structure_bucket_support_rows": int(structure_bucket_guardrail.get("support_rows") or 0),
        "decision_quality_structure_bucket_support_share": structure_bucket_guardrail.get("support_share"),
        "decision_quality_exact_live_structure_bucket_support_rows": int(structure_bucket_guardrail.get("exact_support_rows") or 0),
        "decision_quality_exact_live_structure_bucket_support_share": structure_bucket_guardrail.get("exact_support_share"),
        "decision_quality_structure_bucket_supported_neighbor_buckets": list(structure_bucket_guardrail.get("supported_neighbor_buckets") or []),
        "decision_quality_narrowed_pathology_applied": bool(narrowed_scope_guardrail.get("applied")),
        "decision_quality_narrowed_pathology_scope": narrowed_scope_guardrail.get("scope"),
        "decision_quality_narrowed_pathology_reason": narrowed_scope_guardrail.get("reason"),
        "expected_win_rate": expected_win_rate,
        "expected_pyramid_pnl": expected_pnl,
        "expected_pyramid_quality": expected_quality,
        "expected_drawdown_penalty": expected_drawdown_penalty,
        "expected_time_underwater": expected_time_underwater,
        "decision_quality_score": decision_quality_score,
        "decision_quality_label": _decision_quality_label(decision_quality_score),
    }


def _infer_live_decision_quality_contract(session: Session, decision_profile: Dict[str, Any], horizon_minutes: int = 1440, lookback_rows: int = 5000) -> Dict[str, Any]:
    base = _decision_quality_fallback(decision_profile.get("decision_profile_version") or "phase16_baseline_v2")
    guardrail = _load_dynamic_window_guardrail()
    calibration_window = guardrail.get("recommended_best_n") or lookback_rows
    rows = (
        session.query(
            FeaturesNormalized.timestamp,
            FeaturesNormalized.symbol,
            FeaturesNormalized.regime_label,
            FeaturesNormalized.feat_4h_bias200,
            FeaturesNormalized.feat_4h_bias50,
            FeaturesNormalized.feat_4h_bb_pct_b,
            FeaturesNormalized.feat_4h_dist_bb_lower,
            FeaturesNormalized.feat_4h_dist_swing_low,
            FeaturesNormalized.feat_nose,
            FeaturesNormalized.feat_pulse,
            FeaturesNormalized.feat_ear,
            Labels.simulated_pyramid_win,
            Labels.simulated_pyramid_pnl,
            Labels.simulated_pyramid_quality,
            Labels.simulated_pyramid_drawdown_penalty,
            Labels.simulated_pyramid_time_underwater,
        )
        .join(
            Labels,
            (FeaturesNormalized.timestamp == Labels.timestamp)
            & (FeaturesNormalized.symbol == Labels.symbol),
        )
        .filter(
            Labels.horizon_minutes == horizon_minutes,
            Labels.simulated_pyramid_win.isnot(None),
        )
        .order_by(FeaturesNormalized.timestamp.desc())
        .limit(calibration_window)
        .all()
    )
    if not rows:
        return base

    summarized_rows: List[Dict[str, Any]] = []
    for row in rows:
        hist_features = {
            "regime_label": row.regime_label,
            "feat_4h_bias200": row.feat_4h_bias200,
            "feat_4h_bias50": row.feat_4h_bias50,
            "feat_4h_bb_pct_b": row.feat_4h_bb_pct_b,
            "feat_4h_dist_bb_lower": row.feat_4h_dist_bb_lower,
            "feat_4h_dist_swing_low": row.feat_4h_dist_swing_low,
            "feat_nose": row.feat_nose,
            "feat_pulse": row.feat_pulse,
            "feat_ear": row.feat_ear,
        }
        hist_profile = _build_live_decision_profile(hist_features)
        summarized_rows.append({
            "timestamp": row.timestamp,
            "symbol": row.symbol,
            "regime_label": row.regime_label,
            "regime_gate": hist_profile.get("regime_gate"),
            "regime_gate_reason": hist_profile.get("regime_gate_reason"),
            "structure_quality": hist_profile.get("structure_quality"),
            "structure_bucket": hist_profile.get("structure_bucket"),
            "entry_quality_label": hist_profile.get("entry_quality_label"),
            "feat_4h_bias200": row.feat_4h_bias200,
            "feat_4h_bb_pct_b": row.feat_4h_bb_pct_b,
            "feat_4h_dist_bb_lower": row.feat_4h_dist_bb_lower,
            "feat_4h_dist_swing_low": row.feat_4h_dist_swing_low,
            "simulated_pyramid_win": row.simulated_pyramid_win,
            "simulated_pyramid_pnl": row.simulated_pyramid_pnl,
            "simulated_pyramid_quality": row.simulated_pyramid_quality,
            "simulated_pyramid_drawdown_penalty": row.simulated_pyramid_drawdown_penalty,
            "simulated_pyramid_time_underwater": row.simulated_pyramid_time_underwater,
        })
    enforce_scope_guardrails = bool(
        guardrail.get("raw_best_guardrailed")
        or guardrail.get("recommended_alerts")
    )
    contract = _summarize_decision_quality_contract(
        summarized_rows,
        decision_profile,
        horizon_minutes=horizon_minutes,
        enforce_scope_guardrails=enforce_scope_guardrails,
    )
    contract["decision_quality_calibration_window"] = calibration_window
    contract["decision_quality_guardrail_applied"] = bool(
        guardrail.get("raw_best_guardrailed")
        or contract.get("decision_quality_scope_guardrail_applied")
        or contract.get("decision_quality_recent_pathology_applied")
        or contract.get("decision_quality_exact_live_lane_toxicity_applied")
        or contract.get("decision_quality_narrowed_pathology_applied")
        or contract.get("decision_quality_structure_bucket_guardrail_applied")
    )
    reason_parts = [
        guardrail.get("guardrail_reason"),
        contract.get("decision_quality_scope_guardrail_reason"),
        contract.get("decision_quality_recent_pathology_reason"),
        contract.get("decision_quality_exact_live_lane_reason"),
        contract.get("decision_quality_narrowed_pathology_reason"),
        contract.get("decision_quality_structure_bucket_guardrail_reason"),
    ]
    contract["decision_quality_guardrail_reason"] = "; ".join(part for part in reason_parts if part)
    return contract


def _apply_live_execution_guardrails(decision_profile: Dict[str, Any], decision_quality_contract: Dict[str, Any]) -> Dict[str, Any]:
    """Convert decision-quality diagnostics into execution-time risk controls.

    Heartbeat #667 found that live predictor guardrails were still informational only:
    the probe remained BUY / 2 layers even when the calibration window was guardrailed
    and the resulting decision-quality label was only C. Cap deployment before the
    result is exposed so the live path actually reduces risk under polluted windows.
    """
    guarded = dict(decision_profile or {})
    raw_layers = max(0, int(guarded.get("allowed_layers") or 0))
    capped_layers = raw_layers
    reasons: List[str] = []

    quality_label = decision_quality_contract.get("decision_quality_label")
    quality_score = decision_quality_contract.get("decision_quality_score")
    guardrail_applied = bool(decision_quality_contract.get("decision_quality_guardrail_applied"))
    recent_pathology_applied = bool(decision_quality_contract.get("decision_quality_recent_pathology_applied"))
    exact_live_lane_toxicity_applied = bool(
        decision_quality_contract.get("decision_quality_exact_live_lane_toxicity_applied")
    )
    exact_live_lane_status = decision_quality_contract.get("decision_quality_exact_live_lane_status") or "toxicity"
    structure_bucket_guardrail_applied = bool(
        decision_quality_contract.get("decision_quality_structure_bucket_guardrail_applied")
    )
    structure_bucket_support_mode = decision_quality_contract.get("decision_quality_structure_bucket_support_mode")
    structure_bucket_support_rows = int(
        decision_quality_contract.get("decision_quality_structure_bucket_support_rows") or 0
    )
    exact_structure_bucket_support_rows = int(
        decision_quality_contract.get("decision_quality_exact_live_structure_bucket_support_rows") or 0
    )

    if quality_label == "D" or (quality_score is not None and float(quality_score) < 0.35):
        capped_layers = 0
        reasons.append("decision_quality_below_trade_floor")
    elif quality_label == "C" and capped_layers > 1:
        capped_layers = 1
        reasons.append("decision_quality_label_C_caps_layers")

    if recent_pathology_applied and capped_layers > 0:
        capped_layers = 0
        reasons.append("recent_distribution_pathology_blocks_trade")
    elif guardrail_applied and capped_layers > 1:
        capped_layers = 1
        reasons.append("guardrailed_calibration_caps_layers")

    if exact_live_lane_toxicity_applied:
        capped_layers = 0
        toxic_reason = f"exact_live_lane_{exact_live_lane_status}_blocks_trade"
        if toxic_reason not in reasons:
            reasons.append(toxic_reason)

    if structure_bucket_guardrail_applied:
        if structure_bucket_support_mode == "exact_bucket_unsupported_block" or exact_structure_bucket_support_rows <= 0:
            capped_layers = 0
            structure_reason = "unsupported_exact_live_structure_bucket_blocks_trade"
        elif structure_bucket_support_rows < 5:
            capped_layers = 0
            structure_reason = "unsupported_live_structure_bucket_blocks_trade"
        elif capped_layers > 1:
            capped_layers = 1
            structure_reason = "weak_live_structure_bucket_support_caps_layers"
        else:
            structure_reason = None
        if structure_reason and structure_reason not in reasons:
            reasons.append(structure_reason)

    guarded["allowed_layers_raw"] = raw_layers
    guarded["allowed_layers"] = capped_layers
    guarded["execution_guardrail_applied"] = bool(reasons)
    guarded["execution_guardrail_reason"] = "; ".join(reasons) if reasons else None
    return guarded


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
    """Load latest features in parity with the training pipeline.

    Critical contract: inference must see the same base + lag feature space as
    `model.train.load_training_data()`, including sparse 4H features aligned via
    the same asof merge logic rather than raw `None` values on dense rows.
    """
    import pandas as pd
    from model.train import _align_sparse_4h_features

    max_lag = max(LAG_STEPS) + 1  # need 289 dense rows for lag288
    lookback_rows = max(max_lag, 2000)  # include sparse 4H snapshots for asof alignment
    rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).limit(lookback_rows).all()
    if not rows:
        return None

    latest = rows[0]
    dense_rows = []
    for row in reversed(rows):
        dense_rows.append({
            "timestamp": row.timestamp,
            "regime_label": getattr(row, "regime_label", None),
            **{col: getattr(row, col, None) for col in BASE_FEATURE_COLS},
        })
    aligned_df = _align_sparse_4h_features(pd.DataFrame(dense_rows))
    aligned_df = aligned_df.sort_values("timestamp", ascending=False).reset_index(drop=True)
    latest_aligned = aligned_df.iloc[0].to_dict()

    features = {
        "timestamp": latest.timestamp,
        **{col: latest_aligned.get(col) for col in BASE_FEATURE_COLS},
        # Keep sparse / experimental features visible for diagnostics even though
        # they are intentionally excluded from the canonical training feature set.
        "feat_claw": getattr(latest, "feat_claw", None),
        "feat_claw_intensity": getattr(latest, "feat_claw_intensity", None),
        "feat_fang_pcr": getattr(latest, "feat_fang_pcr", None),
        "feat_fang_skew": getattr(latest, "feat_fang_skew", None),
        "feat_fin_netflow": getattr(latest, "feat_fin_netflow", None),
        "feat_web_whale": getattr(latest, "feat_web_whale", None),
        "feat_scales_ssr": getattr(latest, "feat_scales_ssr", None),
        "feat_nest_pred": getattr(latest, "feat_nest_pred", None),
        "feat_nq_return_1h": getattr(latest, "feat_nq_return_1h", None),
        "feat_nq_return_24h": getattr(latest, "feat_nq_return_24h", None),
    }
    # Compute lag features from the aligned dense frame so 4H lags match training-time asof alignment.
    for col in BASE_FEATURE_COLS:
        for lag in LAG_STEPS:
            lag_col = f"{col}_lag{lag}"
            if lag < len(aligned_df):
                val = aligned_df.iloc[lag].get(col)
                features[lag_col] = None if pd.isna(val) else val
            else:
                features[lag_col] = None  # Not enough history

    def _num(name: str) -> float:
        val = features.get(name)
        return 0.0 if val is None else float(val)

    # P0 #H149-fix2: Compute VIX cross-features at inference time to match training
    vix = _num("feat_vix")
    eye = _num("feat_eye")
    pulse = _num("feat_pulse")
    mind = _num("feat_mind")
    features["feat_vix_x_eye"] = vix * eye
    features["feat_vix_x_pulse"] = vix * pulse
    features["feat_vix_x_mind"] = vix * mind

    # Cross-sense features matching train.py
    features["feat_mind_x_pulse"] = mind * pulse
    features["feat_eye_x_ear"] = eye * _num("feat_ear")
    features["feat_nose_x_aura"] = _num("feat_nose") * _num("feat_aura")
    features["feat_eye_x_body"] = eye * _num("feat_body")
    features["feat_ear_x_nose"] = _num("feat_ear") * _num("feat_nose")
    features["feat_mind_x_aura"] = mind * _num("feat_aura")

    # Regime flag — prefer DB regime_label over heuristic (P0 #H379)
    regime = getattr(latest, "regime_label", None)
    if regime is None or regime == "":
        regime = _determine_regime(features)
    features["regime_label"] = regime
    features["feat_regime_flag"] = {"trend": 1.0, "chop": -1.0, "panic": -0.5, "event": 0.5, "normal": 0.0}.get(regime, 0.0)

    # Mean-reversion proxy
    features["feat_mean_rev_proxy"] = mind - _num("feat_aura")
    # P0: Disabled cross-features — base features (claw, fang, fin, nq) have <500 samples
    # Re-enable when these features have sufficient data
    # vix = features.get("feat_vix", 0) or 0
    # claw = features.get("feat_claw", 0) or 0
    # nq = features.get("feat_nq_return_1h", 0) or 0
    # fang = features.get("feat_fang_pcr", 0) or 0
    # fin = features.get("feat_fin_netflow", 0) or 0
    # web = features.get("feat_web_whale", 0) or 0
    # features["feat_claw_x_pulse"] = claw * (features.get("feat_pulse", 0) or 0)
    # features["feat_fang_x_vix"] = fang * vix
    # features["feat_fin_x_claw"] = fin * claw
    # features["feat_web_x_fang"] = web * fang
    # features["feat_nq_x_vix"] = nq * vix

    return features


def _check_circuit_breaker(session) -> Optional[Dict]:
    """P0 #H420: Circuit breaker — check for consecutive losses and recent win rate.
    Returns an abort dict if circuit breaker is triggered, None if safe to trade.
    """
    from sqlalchemy import func as _func
    from database.models import Labels

    # Check consecutive recent target failures from most recent backwards
    label_target = getattr(Labels, DEFAULT_TARGET_COL, Labels.label_spot_long_win)
    recent_labels = (
        session.query(label_target)
        .filter(label_target.isnot(None))
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

    P0 HB#234 fix: Global IC sanity check. When Global IC = 0/8 (no sense has
    any full-history predictive power), TW-IC fusion may be chasing noise.
    Raise the IC threshold to require stronger signals before trusting fusion.
    Threshold tuned to 0.10 (HB#235): balances noise filtering with signal capture.
    At 0.15, Eye (TW-IC=0.136) was excluded — too conservative.
    At 0.10, 6/8 pass, total |IC| > 2.0 — strong fusion signal.
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
    glob_ics = _global_ic(session)

    # Core 8 senses
    sense_cols = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue",
                   "feat_body", "feat_pulse", "feat_aura", "feat_mind"]
    raw_ics = [tw_ics.get(col, 0.0) for col in sense_cols]

    # P0 HB#234: Global IC sanity check
    global_pass = sum(1 for v in glob_ics.values() if abs(v) >= 0.05)
    if global_pass == 0:
        # No sense has full-history predictive power — TW-IC may be noise
        # Raise threshold to require stronger TW-IC signals
        IC_PASS_THRESHOLD = 0.10
        logger.warning(f"Global IC = 0/8 — raising IC threshold to {IC_PASS_THRESHOLD}")
    else:
        IC_PASS_THRESHOLD = getattr(predict_with_ic_fusion, '_ic_threshold', 0.05)
        logger.info(f"Global IC {global_pass}/8 — using IC threshold {IC_PASS_THRESHOLD}")

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
            continue
        # Flip sign for negative IC senses so all aligned signals point toward
        # a profitable spot-long pyramid.
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
        # P0 #H379 HB#233: Model has CV=51.4% (~random), dilutes IC fusion.
        # When total |IC| > 0.5 (strong signals), use 100% IC fusion.
        # Otherwise blend with model as fallback (50/50).
        total_abs_ic = weight_arr.sum()
        if total_abs_ic > 0.5:
            # Strong IC signals — trust fusion over random model
            pass  # confidence stays 100% IC fusion
        else:
            # Weak signals — blend with model as fallback
            if predictor is None:
                predictor, _ = load_predictor()
            model_conf = predictor.predict_proba(features)
            confidence = 0.5 * confidence + 0.5 * model_conf

    # Apply regime bias
    regime = features.get("regime_label")
    bias = REGIME_THRESHOLD_BIAS.get(regime, 0.0) if regime else 0.0
    adjusted = float(np.clip(confidence + bias, 0.0, 1.0))

    # P0 #H426: Bull regime signal inversion
    # Bull markets should not emit SELL for a spot-long strategy.
    if BULL_SIGNAL_INVERT and regime == "bull":
        adjusted = float(np.clip(1.0 - adjusted, 0.0, 1.0))

    # Signal determination for spot-long pyramiding:
    # high confidence => BUY, otherwise HOLD/abstain.
    if adjusted > CONFIDENCE_HIGH:
        signal = "BUY"
        confidence_level = "HIGH"
    elif adjusted < CONFIDENCE_LOW:
        signal = "HOLD"
        confidence_level = "LOW"
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
        "should_trade": signal == "BUY",
        "model_type": "ic_fusion_time_weighted_v2_nose_excluded",
        "target_col": DEFAULT_TARGET_COL,
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
        return {
            **cb,
            **_decision_quality_fallback(),
            "regime_gate": None,
            "entry_quality": None,
            "entry_quality_label": None,
            "allowed_layers": 0,
        }
    features = load_latest_features(session)
    if not features:
        return None
    if predictor is None:
        predictor, regime_models = load_predictor()

    decision_profile = _build_live_decision_profile(features)
    decision_quality_contract = _infer_live_decision_quality_contract(session, decision_profile)
    execution_profile = _apply_live_execution_guardrails(decision_profile, decision_quality_contract)

    # Per-regime model routing (H145-fix + #H122 chop-abstain ensemble)
    used_model = "global"
    if regime_models and isinstance(features, dict):
        regime = execution_profile.get("regime_label") or features.get("regime_label") or _determine_regime(features)
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
                    "model_route_regime": regime,
                    "target_col": getattr(getattr(predictor, '_global', predictor), '_target_col', DEFAULT_TARGET_COL),
                    **execution_profile,
                    **decision_quality_contract,
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

    # Confidence-based signal — model predicts long-win probability.
    # High confidence = setup is favorable for spot-long pyramiding.
    if confidence > CONFIDENCE_HIGH:
        signal = "BUY"
        confidence_level = "HIGH"
    elif confidence < CONFIDENCE_LOW:
        signal = "HOLD"
        confidence_level = "LOW"
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
        "should_trade": signal == "BUY" and (execution_profile.get("allowed_layers") or 0) > 0,
        "model_type": type(predictor).__name__,
        "used_model": used_model,
        "model_route_regime": execution_profile.get("regime_label") or features.get("regime_label") or _determine_regime(features),
        "target_col": getattr(getattr(predictor, '_global', predictor), '_target_col', DEFAULT_TARGET_COL),
        **execution_profile,
        **decision_quality_contract,
    }
    logger.info(
        "Prediction: conf=%.4f, signal=%s, level=%s, gate=%s, quality=%.4f, layers=%s",
        confidence,
        signal,
        confidence_level,
        result.get("regime_gate"),
        float(result.get("entry_quality") or 0.0),
        result.get("allowed_layers"),
    )
    return result
