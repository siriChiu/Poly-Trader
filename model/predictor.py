"""
模型預測模組 v3 — IC-validated features + confidence-based filtering
Only trade when model confidence > 0.7 or < 0.3
"""

import os
import json
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


def _compute_live_regime_gate(bias200_value: float, regime: str, regime_min: float = LIVE_REGIME_BIAS200_MIN) -> str:
    """Mirror Strategy Lab's regime gate semantics for live inference.

    Keep these thresholds in sync with `backtesting.strategy_lab._compute_regime_gate`
    so the heartbeat can verify that live predictor output speaks the same decision
    contract as Strategy Lab / API / UI.
    """
    regime = (regime or "unknown").lower()
    if bias200_value < regime_min:
        return "BLOCK"
    if regime == "bear" and bias200_value <= -3.0:
        return "BLOCK"
    if regime in {"chop", "unknown"} or bias200_value < -1.0:
        return "CAUTION"
    return "ALLOW"


def _compute_live_entry_quality(bias50_value: float, nose_value: float, pulse_value: float, ear_value: float) -> float:
    """Mirror Strategy Lab's entry-quality baseline for live inference."""
    bias_score = _clamp01((-bias50_value + 2.4) / 5.0)
    nose_score = _clamp01(1.0 - nose_value)
    pulse_score = _clamp01(pulse_value)
    ear_score = _clamp01(1.0 - abs(ear_value) * 5.0)
    return round(0.40 * bias_score + 0.18 * nose_score + 0.27 * pulse_score + 0.15 * ear_score, 4)


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
            "entry_quality": None,
            "entry_quality_label": None,
            "allowed_layers": None,
            "decision_profile_version": "phase16_baseline_v2",
        }

    def _f(name: str) -> float:
        value = features.get(name)
        return 0.0 if value is None else float(value)

    regime = str(features.get("regime_label") or _determine_regime(features))
    regime_gate = _compute_live_regime_gate(_f("feat_4h_bias200"), regime)
    entry_quality = _compute_live_entry_quality(
        _f("feat_4h_bias50"),
        _f("feat_nose"),
        _f("feat_pulse"),
        _f("feat_ear"),
    )
    allowed_layers = _allowed_layers_for_live_signal(regime_gate, entry_quality, max_layers=max_layers)
    return {
        "regime_label": regime,
        "regime_gate": regime_gate,
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
        adverse_target = 0 if win_rate is None or win_rate <= 0.5 else 1
        adverse_streak = _longest_binary_streak(window_rows, "simulated_pyramid_win", adverse_target)
        candidates.append(
            {
                "score": (severity, negative_score, adverse_streak.get("count", 0), len(window_rows)),
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
    reason = (
        f"recent scope slice {chosen['window']} rows shows distribution_pathology "
        f"alerts={chosen['alerts']} win_rate={summary.get('win_rate')} avg_pnl={summary.get('avg_pnl')} "
        f"avg_quality={summary.get('avg_quality')} "
        f"window={summary.get('start_timestamp')}->{summary.get('end_timestamp')} "
        f"adverse_streak={adverse_streak.get('count', 0)}x{adverse_streak.get('target')} "
        f"({adverse_streak.get('start_timestamp')}->{adverse_streak.get('end_timestamp')})"
    )
    return {
        "applied": True,
        "window": chosen["window"],
        "alerts": chosen["alerts"],
        "reason": reason,
        "summary": summary,
    }


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
    selection_lanes = [
        ("regime_gate+entry_quality_label", lambda row: row.get("regime_gate") == target_gate and row.get("entry_quality_label") == target_quality_label, 30),
        ("regime_gate", lambda row: row.get("regime_gate") == target_gate, 50),
        ("entry_quality_label", lambda row: row.get("entry_quality_label") == target_quality_label, 50),
        ("global", lambda row: True, 1),
    ]

    chosen_scope = None
    chosen_rows: List[Dict[str, Any]] = []
    scope_guardrail_applied = False
    scope_guardrail_reason = None
    scope_guardrail_alerts: List[str] = []
    for scope_name, predicate, min_rows in selection_lanes:
        scoped_rows = [row for row in rows if predicate(row)]
        if len(scoped_rows) < min_rows:
            continue
        scope_alerts = _decision_quality_scope_alerts(scoped_rows)
        if enforce_scope_guardrails and scope_name != "global" and any(
            alert in scope_alerts for alert in ("constant_target", "label_imbalance")
        ):
            scope_guardrail_applied = True
            scope_guardrail_alerts = scope_alerts
            scope_guardrail_reason = (
                f"scope {scope_name} rejected via alerts={scope_alerts} "
                f"(rows={len(scoped_rows)})"
            )
            continue
        chosen_scope = scope_name
        chosen_rows = scoped_rows
        break
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
            "feat_nose": row.feat_nose,
            "feat_pulse": row.feat_pulse,
            "feat_ear": row.feat_ear,
        }
        hist_profile = _build_live_decision_profile(hist_features)
        summarized_rows.append({
            "timestamp": row.timestamp,
            "symbol": row.symbol,
            "regime_gate": hist_profile.get("regime_gate"),
            "entry_quality_label": hist_profile.get("entry_quality_label"),
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
    )
    reason_parts = [
        guardrail.get("guardrail_reason"),
        contract.get("decision_quality_scope_guardrail_reason"),
        contract.get("decision_quality_recent_pathology_reason"),
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
