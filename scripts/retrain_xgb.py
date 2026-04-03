#!/usr/bin/env python
"""Re-train XGBoost with tuned hyperparameters. Fixes P0 underfitting."""
import sys
from pathlib import Path
PT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PT_ROOT))

from database.models import init_db, FeaturesNormalized, Labels, FeaturesNormalized as FN
from model.train import train_xgboost, load_training_data, save_model
from sqlalchemy.orm import Session
import json
import numpy as np
from datetime import datetime
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb

db_path = PT_ROOT / 'poly_trader.db'
engine_url = f'sqlite:///{db_path}'
session = init_db(engine_url)

loaded = load_training_data(session, min_samples=50)
if loaded is None:
    print("ERROR: No training data available")
    sys.exit(1)

X, y = loaded
print(f"Training data: {X.shape[0]} samples, {X.shape[1]} features")
print(f"Class balance: {y.mean():.3f} positive ({y.sum()} / {len(y)})")

# Train with new hyperparameters
model = train_xgboost(X, y)
print("Training complete!")

# Evaluate
train_acc = float((model.predict(X) == y).mean())

# Time-series CV
tscv = TimeSeriesSplit(n_splits=5)
valid_scores = []
for tr_idx, te_idx in tscv.split(X):
    y_tr = y.iloc[tr_idx]
    if len(y_tr.unique()) < 2:
        continue
    m = xgb.XGBClassifier(**{k: v for k, v in model.get_params().items()})
    m.fit(X.iloc[tr_idx], y_tr)
    score = float((m.predict(X.iloc[te_idx]) == y.iloc[te_idx]).mean())
    valid_scores.append(score)

cv_acc = float(np.mean(valid_scores)) if valid_scores else float('nan')
cv_std = float(np.std(valid_scores)) if valid_scores else float('nan')
gap = train_acc - cv_acc

print(f"\n=== Results ===")
print(f"Train Accuracy: {train_acc:.4f}")
print(f"CV Accuracy:   {cv_acc:.4f} (±{cv_std:.4f})")
print(f"Gap:           {gap:+.4f} (should be positive, indicates proper fit)")

# Save
import pickle

# Load existing pipeline wrapper
model_path = PT_ROOT / 'model' / 'xgb_model.pkl'
with open(model_path, 'rb') as f:
    pipeline = pickle.load(f)

# Update the classifier in the pipeline
pipeline['clf'] = model
pipeline['feature_names'] = X.columns.tolist()
pipeline['calibration'] = {}  # placeholder

with open(model_path, 'wb') as f:
    pickle.dump(pipeline, f)

# Save metrics
metrics = {
    'train_accuracy': train_acc,
    'cv_accuracy': cv_acc,
    'cv_std': cv_std,
    'n_samples': len(X),
    'n_features': X.shape[1],
    'trained_at': datetime.utcnow().isoformat(),
}
with open(PT_ROOT / 'model' / 'last_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print(f"\nSaved model to {model_path}")
print(f"Saved metrics to {PT_ROOT / 'model' / 'last_metrics.json'}")
