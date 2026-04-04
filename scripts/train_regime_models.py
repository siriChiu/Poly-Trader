"""Train regime-specific models (P0 #H122 #H301)"""
import sys, os
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

import numpy as np
import pandas as pd
import xgboost as xgb
import pickle
import json
from scipy import stats
from sklearn.model_selection import TimeSeriesSplit
from sklearn.utils.class_weight import compute_sample_weight
from pathlib import Path

DB = Path('poly_trader.db')
import sqlite3
db = sqlite3.connect(str(DB))

features = pd.read_sql("SELECT * FROM features_normalized", db)
labels = pd.read_sql("SELECT timestamp, symbol, label_sell_win, label_up FROM labels", db)
db.close()

merged = pd.merge(features, labels, on=['timestamp', 'symbol'], how='inner')

BASE_COLS = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue", "feat_body", "feat_pulse", "feat_aura", "feat_mind", "feat_vix", "feat_dxy"]
LAG_STEPS = [12, 48, 288]

for col in BASE_COLS:
    for lag in LAG_STEPS:
        merged[f"{col}_lag{lag}"] = merged[col].shift(lag)

LAG_COLS = [f"{c}_lag{l}" for c in BASE_COLS for l in LAG_STEPS]
CROSS = ["feat_vix_x_eye", "feat_vix_x_pulse", "feat_vix_x_mind",
         "feat_mind_x_pulse", "feat_eye_x_ear", "feat_nose_x_aura",
         "feat_eye_x_body", "feat_ear_x_nose", "feat_mind_x_aura",
         "feat_mean_rev_proxy"]

merged["feat_vix_x_eye"] = merged["feat_vix"] * merged["feat_eye"]
merged["feat_vix_x_pulse"] = merged["feat_vix"] * merged["feat_pulse"]
merged["feat_vix_x_mind"] = merged["feat_vix"] * merged["feat_mind"]
merged["feat_mind_x_pulse"] = merged["feat_mind"] * merged["feat_pulse"]
merged["feat_eye_x_ear"] = merged["feat_eye"] * merged["feat_ear"]
merged["feat_nose_x_aura"] = merged["feat_nose"] * merged["feat_aura"]
merged["feat_eye_x_body"] = merged["feat_eye"] * merged["feat_body"]
merged["feat_ear_x_nose"] = merged["feat_ear"] * merged["feat_nose"]
merged["feat_mind_x_aura"] = merged["feat_mind"] * merged["feat_aura"]
merged["feat_mean_rev_proxy"] = merged["feat_mind"] - merged["feat_aura"]

ALL_COLS = BASE_COLS + LAG_COLS + CROSS
for col in ALL_COLS:
    merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0.0)

y = merged["label_sell_win"].astype(int)

# IC sign flip for neg correlations
neg_ic_feats = []
for col in ALL_COLS:
    feat_arr = merged[col].values.astype(float)
    label_arr = y.values.astype(float)
    mask = ~(np.isnan(feat_arr) | np.isnan(label_arr))
    if mask.sum() > 30:
        f_masked = feat_arr[mask]
        if np.ptp(f_masked) > 0:
            corr, _ = stats.spearmanr(f_masked, label_arr[mask])
            if corr is not None and np.isfinite(corr) and corr < 0:
                neg_ic_feats.append(col)
                merged[col] = -merged[col]

print(f"NEG_IC features flipped: {len(neg_ic_feats)}")

params = {
    "n_estimators": 200, "max_depth": 3, "learning_rate": 0.05,
    "subsample": 0.8, "colsample_bytree": 0.8,
    "reg_alpha": 2.0, "reg_lambda": 6.0, "min_child_weight": 10, "gamma": 0.2,
    "objective": "binary:logistic", "eval_metric": "logloss", "random_state": 42,
}

# Global model
print("\n=== Global Model ===")
X = merged[ALL_COLS].fillna(0.0)
sw = compute_sample_weight("balanced", y)
gm = xgb.XGBClassifier(**params)
gm.fit(X, y, sample_weight=sw)
train_acc = float((gm.predict(X) == y).mean())
tscv = TimeSeriesSplit(n_splits=5)
cvs = []
for tr, te in tscv.split(X):
    yt = y.iloc[tr]
    if len(yt.unique()) < 2:
        continue
    m = xgb.XGBClassifier(**{k: v for k, v in gm.get_params().items()})
    m.fit(X.iloc[tr], yt, sample_weight=compute_sample_weight("balanced", yt))
    cvs.append(float((m.predict(X.iloc[te]) == y.iloc[te]).mean()))
cv_acc = float(np.mean(cvs))
print(f"  Train={train_acc:.4f}, CV={cv_acc:.4f}")

# Save global model
global_payload = {
    'clf': gm, 'feature_names': ALL_COLS,
    'neg_ic_feats': neg_ic_feats, 'calibration': {'kind': 'none'},
    'regime_threshold_bias': {},
}
os.makedirs("model", exist_ok=True)
with open("model/xgb_model.pkl", "wb") as f:
    pickle.dump(global_payload, f)
with open("model/ic_signs.json", "w") as f:
    json.dump({"neg_ic_feats": neg_ic_feats}, f)
print("  Global model saved: model/xgb_model.pkl")

# Regime-specific models
print("\n=== Regime-Specific Models ===")
regime_models = {}
for regime in ['bear', 'bull', 'chop']:
    mask = merged['regime_label'] == regime
    regime_data = merged[mask].copy()
    n = len(regime_data)
    if n < 200:
        print(f"  {regime}: only {n} samples, skipping")
        continue
    X_r = regime_data[ALL_COLS].fillna(0.0)
    y_r = regime_data["label_sell_win"].astype(int)
    sw = compute_sample_weight("balanced", y_r)
    model_r = xgb.XGBClassifier(**params)
    model_r.fit(X_r, y_r, sample_weight=sw)
    train_acc_r = float((model_r.predict(X_r) == y_r).mean())
    # CV
    tscv_r = TimeSeriesSplit(n_splits=3)
    cvs_r = []
    for tr, te in tscv_r.split(X_r):
        yt = y_r.iloc[tr]
        if len(yt.unique()) < 2:
            continue
        m = xgb.XGBClassifier(**{k: v for k, v in model_r.get_params().items()})
        m.fit(X_r.iloc[tr], yt, sample_weight=compute_sample_weight("balanced", yt))
        cvs_r.append(float((m.predict(X_r.iloc[te]) == y_r.iloc[te]).mean()))
    cv_acc_r = float(np.mean(cvs_r)) if cvs_r else float('nan')
    
    reg_payload = {
        'clf': model_r, 'feature_names': ALL_COLS,
        'neg_ic_feats': neg_ic_feats, 'calibration': {'kind': 'none'},
        'regime_threshold_bias': {},
    }
    regime_models[regime] = reg_payload
    print(f"  {regime} (n={n}): Train={train_acc_r:.4f}, CV={cv_acc_r:.4f}")

with open("model/regime_models.pkl", "wb") as f:
    pickle.dump(regime_models, f)
print(f"  Regime models saved: {list(regime_models.keys())}")
print("\nTraining complete.")
