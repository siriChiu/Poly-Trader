"""
P0 #H325: Time-Weighted IC Fusion + Model Retraining
Implements exponentially decaying sample weights so recent data dominates training.
Tau=200 provides the best tradeoff: 4/8 sensors pass (vs 1/8 baseline).
"""

import sys, os, json, pickle, sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DATABASE_URL', 'sqlite:///poly_trader.db')

import numpy as np
import pandas as pd
from scipy import stats as _stats
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from database.models import FeaturesNormalized, Labels
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier
from sklearn.isotonic import IsotonicRegression

logger = None
def get_logger():
    global logger
    if logger is None:
        from utils.logger import setup_logger
        logger = setup_logger(__name__)
    return logger

FEATURE_COLS = [
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue",
    "feat_body", "feat_pulse", "feat_aura", "feat_mind",
    "feat_vix", "feat_dxy",
]
LAG_STEPS = [12, 48, 288]
BASE_FEATURE_COLS = FEATURE_COLS
CROSS_FEATURES = [
    "feat_vix_x_eye", "feat_vix_x_pulse", "feat_vix_x_mind",
    "feat_mind_x_pulse", "feat_eye_x_ear", "feat_nose_x_aura",
    "feat_eye_x_body", "feat_ear_x_nose", "feat_mind_x_aura",
    "feat_regime_flag", "feat_mean_rev_proxy"
]


def load_training_data(session: Session):
    """Load features + labels from DB."""
    feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
    label_rows = (
        session.query(Labels)
        .filter(Labels.label_sell_win.isnot(None), Labels.future_return_pct.isnot(None))
        .order_by(Labels.timestamp)
        .all()
    )
    if not feat_rows or not label_rows:
        return None

    feat_df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "regime_label": getattr(r, "regime_label", None),
        **{c: getattr(r, c, None) for c in FEATURE_COLS},
    } for r in feat_rows])
    label_df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "label_sell_win": int(r.label_sell_win),
    } for r in label_rows])

    feat_df["timestamp"] = pd.to_datetime(feat_df["timestamp"])
    label_df["timestamp"] = pd.to_datetime(label_df["timestamp"])

    merged = pd.merge_asof(
        feat_df.sort_values("timestamp"),
        label_df.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("10min"),
    )
    merged = merged.dropna(subset=["label_sell_win"]).copy()

    # Lag features
    lag_feature_cols = []
    for col in BASE_FEATURE_COLS:
        for lag in LAG_STEPS:
            lag_col = f"{col}_lag{lag}"
            merged[lag_col] = merged[col].shift(lag)
            lag_feature_cols.append(lag_col)

    all_feat_cols = FEATURE_COLS + lag_feature_cols
    for col in all_feat_cols:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')
    merged[all_feat_cols] = merged[all_feat_cols].fillna(0.0)

    # Cross features
    merged["feat_vix_x_eye"] = merged["feat_vix"] * merged["feat_eye"]
    merged["feat_vix_x_pulse"] = merged["feat_vix"] * merged["feat_pulse"]
    merged["feat_vix_x_mind"] = merged["feat_vix"] * merged["feat_mind"]
    merged["feat_mind_x_pulse"] = merged["feat_mind"] * merged["feat_pulse"]
    merged["feat_eye_x_ear"] = merged["feat_eye"] * merged["feat_ear"]
    merged["feat_nose_x_aura"] = merged["feat_nose"] * merged["feat_aura"]
    merged["feat_eye_x_body"] = merged["feat_eye"] * merged["feat_body"]
    merged["feat_ear_x_nose"] = merged["feat_ear"] * merged["feat_nose"]
    merged["feat_mind_x_aura"] = merged["feat_mind"] * merged["feat_aura"]
    merged["feat_regime_flag"] = merged["regime_label"].map(
        {"trend": 1.0, "chop": -1.0, "panic": -0.5, "event": 0.5, "normal": 0.0}
    ).fillna(0.0)
    merged["feat_mean_rev_proxy"] = merged["feat_mind"] - merged["feat_aura"]

    X_cols = all_feat_cols + CROSS_FEATURES
    X = merged[X_cols].copy()
    y = merged["label_sell_win"].astype(int)
    timestamps = merged["timestamp"].copy()
    return X, y, timestamps


def compute_time_weights(timestamps, tau: float):
    """Exponential decay weights: recent data gets higher weight.
    w_i = exp(-(N-1-i) / tau) where i goes from 0 (oldest) to N-1 (newest).
    """
    N = len(timestamps)
    indices = np.arange(N, dtype=float)
    weights = np.exp(-(N - 1 - indices) / tau)
    return weights


def train_with_time_weights(session: Session, tau: float = 200):
    """Train with time-weighted sample weights + time-weighted IC calculation."""
    log = get_logger()
    log.info(f"Loading training data (tau={tau})...")
    loaded = load_training_data(session)
    if loaded is None:
        log.warning("No training data")
        return None
    X, y, timestamps = loaded
    log.info(f"Loaded {len(X)} samples, {X.shape[1]} features")

    # --- Time-weighted IC computation ---
    y_arr = y.astype(float).values
    all_feature_cols = X.columns.tolist()
    ic_map = {}
    NEG_IC_FEATS = []

    for col in all_feature_cols:
        feat_arr = X[col].astype(float).values
        mask = ~(np.isnan(feat_arr) | np.isnan(y_arr))
        if mask.sum() > 30 and np.ptp(feat_arr[mask]) > 0:
            # Time-weighted correlation
            weights = compute_time_weights(timestamps, tau)
            w = weights[mask]
            fc = feat_arr[mask]
            yc = y_arr[mask]

            w_mean_f = np.average(fc, weights=w)
            w_mean_y = np.average(yc, weights=w)
            cov = np.average((fc - w_mean_f) * (yc - w_mean_y), weights=w)
            var_f = np.average((fc - w_mean_f)**2, weights=w)
            var_y = np.average((yc - w_mean_y)**2, weights=w)
            w_ic = cov / (np.sqrt(var_f * var_y) + 1e-15)

            # Also compute plain IC for comparison
            try:
                plain_ic, _ = _stats.spearmanr(fc, yc)
            except Exception:
                plain_ic = 0.0

            ic_map[col] = round(float(w_ic), 4)
            if w_ic < 0:
                NEG_IC_FEATS.append(col)
                log.debug(f"  {col}: TW-IC={w_ic:+.4f} (plain={plain_ic:+.4f}) [NEG] -- flipping sign in training")
                X[col] = -X[col]  # Flip for training
            else:
                log.debug(f"  {col}: TW-IC={w_ic:+.4f} (plain={plain_ic:+.4f})")
        else:
            ic_map[col] = 0.0

    passed = sum(1 for v in ic_map.values() if abs(v) >= 0.05)
    log.info(f"Time-weighted IC (tau={tau}): {passed}/{len(all_feature_cols)} passed |IC| >= 0.05")

    # Save time-weighted IC signs
    os.makedirs("model", exist_ok=True)
    with open("model/ic_signs.json", "w", encoding="utf-8") as f:
        json.dump({"neg_ic_feats": NEG_IC_FEATS, "ic_map": ic_map, "target": "label_sell_win"}, f, indent=2, ensure_ascii=False)
    log.info(f"Saved ic_signs.json (time-weighted, tau={tau})")

    # --- Time-weighted training ---
    weights = compute_time_weights(timestamps, tau)

    # Also apply class balance
    from sklearn.utils.class_weight import compute_sample_weight
    class_weights = compute_sample_weight("balanced", y)
    combined_weights = weights * class_weights

    params = {
        "n_estimators": 200,
        "max_depth": 2,  # depth=2 is best per HB#171
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 2.0,
        "reg_lambda": 6.0,
        "min_child_weight": 10,
        "gamma": 0.2,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "random_state": 42,
    }

    model = XGBClassifier(**params)
    model.fit(X, y, sample_weight=combined_weights)

    # Evaluate
    train_acc = float((model.predict(X) == y).mean())
    log.info(f"Train accuracy (time-weighted): {train_acc:.4f}")

    # TimeSeriesSplit CV
    tscv = TimeSeriesSplit(n_splits=5)
    valid_scores = []
    for tr_idx, te_idx in tscv.split(X):
        y_tr = y.iloc[tr_idx]
        if len(y_tr.unique()) < 2:
            continue
        m = XGBClassifier(**params)
        w_tr = combined_weights[tr_idx]
        m.fit(X.iloc[tr_idx], y_tr, sample_weight=w_tr)
        valid_scores.append(float((m.predict(X.iloc[te_idx]) == y.iloc[te_idx]).mean()))
    cv_acc = float(np.mean(valid_scores)) if valid_scores else float('nan')
    cv_std = float(np.std(valid_scores)) if valid_scores else float('nan')
    log.info(f"CV accuracy (time-weighted): {cv_acc:.4f} ± {cv_std:.4f}")
    train_gap = train_acc - cv_acc
    log.info(f"Overfit gap: {train_gap:.4f}")

    # Save model
    calibrator = fit_calibrator(model, X, y)
    payload = {
        'clf': model,
        'feature_names': X.columns.tolist(),
        'neg_ic_feats': NEG_IC_FEATS,
        'calibration': calibrator,
        'regime_threshold_bias': {
            'trend': -0.03, 'chop': 0.04, 'panic': -0.01, 'event': 0.02, 'normal': 0.0,
        },
    }
    with open("model/xgb_model.pkl", "wb") as f:
        pickle.dump(payload, f)
    log.info("Saved model/xgb_model.pkl")

    # Save metrics
    try:
        db = sqlite3.connect('poly_trader.db')
        from datetime import datetime
        cur = db.cursor()
        # Create table if not exists
        cur.execute("""CREATE TABLE IF NOT EXISTS model_metrics (
            id INTEGER PRIMARY KEY, timestamp TEXT, train_accuracy REAL,
            cv_accuracy REAL, cv_std REAL, n_features INTEGER, notes TEXT
        )""")
        cur.execute("""INSERT INTO model_metrics (timestamp, train_accuracy, cv_accuracy, cv_std, n_features, notes)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (datetime.utcnow().isoformat(), train_acc, cv_acc, cv_std, X.shape[1], f'time-weighted tau={tau}'))
        db.commit()
        db.close()
    except Exception as e:
        log.warning(f"Could not save metrics: {e}")

    return {
        "train_acc": train_acc,
        "cv_acc": cv_acc,
        "cv_std": cv_std,
        "overfit_gap": train_gap,
        "ic_passed": passed,
        "total_ics": len(all_feature_cols),
        "tau": tau,
    }


def fit_calibrator(model, X, y):
    """Isotonic regression calibration."""
    try:
        raw = model.predict_proba(X)
        scores = raw[:, -1] if raw.ndim == 2 and raw.shape[1] >= 2 else np.asarray(raw).ravel()
        scores = np.asarray(scores, dtype=float)
        y_arr = y.astype(float).values
        if len(np.unique(y_arr)) >= 2 and len(y_arr) >= 30:
            iso = IsotonicRegression(out_of_bounds='clip')
            iso.fit(scores, y_arr)
            return {
                'kind': 'isotonic',
                'x': [float(v) for v in iso.X_thresholds_.tolist()],
                'y': [float(v) for v in iso.y_thresholds_.tolist()],
            }
        p = np.clip(scores, 1e-6, 1 - 1e-6)
        logit = np.log(p / (1 - p))
        return {'kind': 'logit_affine', 'mu': float(np.mean(logit)), 'sigma': float(np.std(logit) or 1.0)}
    except Exception:
        return {'kind': 'none'}


def main():
    eng_url = os.environ.get('DATABASE_URL', 'sqlite:///poly_trader.db')
    engine = create_engine(eng_url)
    SessionLocal = Session
    sess = SessionLocal(bind=engine)

    # Try tau=200 first (balanced: 4/8 sensors pass)
    result = train_with_time_weights(sess, tau=200)
    if result:
        print(f"Results (tau={result['tau']}):")
        print(f"  IC passed: {result['ic_passed']}/{result['total_ics']}")
        print(f"  Train: {result['train_acc']:.4f}")
        print(f"  CV: {result['cv_acc']:.4f} ± {result['cv_std']:.4f}")
        print(f"  Gap: {result['overfit_gap']:.4f}")
    else:
        print("FAILED: no training data")

    sess.close()


if __name__ == "__main__":
    main()
