#!/usr/bin/env python3
"""Heartbeat #173 — Train model and evaluate"""
import sys, json
from pathlib import Path
sys.path.insert(0, '/home/kazuha/Poly-Trader')

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import FeaturesNormalized, Labels
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

db_path = str(Path('/home/kazuha/Poly-Trader/poly_trader.db'))
engine = create_engine(f'sqlite:///{db_path}')
Session = sessionmaker(bind=engine)
session = Session()

# Load data
rows = session.query(FeaturesNormalized, Labels).join(
    Labels, FeaturesNormalized.timestamp == Labels.timestamp
).filter(Labels.label_sell_win.isnot(None)).all()

print(f"Loaded {len(rows)} joined records")

# Build feature matrix
sense_cols = ['feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind']
ti_cols = ['feat_rsi14', 'feat_macd_hist', 'feat_atr_pct', 'feat_vwap_dev', 'feat_bb_pct_b']

feature_data = []
labels = []
regimes = []

for f, l in rows:
    row = {}
    for c in sense_cols + ti_cols:
        val = getattr(f, c, None)
        row[c] = val if val is not None else 0.0
    feature_data.append(row)
    labels.append(int(l.label_sell_win))
    regimes.append(getattr(l, 'regime_label', 'Unknown') or 'Unknown')

X = pd.DataFrame(feature_data)
y = np.array(labels)

# Filter out rows with NaN
valid = ~X.isna().any(axis=1)
X = X[valid]
y = y[valid]

print(f"  X: {X.shape}, sell_win rate: {y.mean():.4f}")

# Train with depth=2
model = XGBClassifier(
    max_depth=2,
    n_estimators=100,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric='logloss'
)

# CV
tscv = TimeSeriesSplit(n_splits=5)
cv_scores = cross_val_score(model, X, y, cv=tscv, scoring='accuracy')
print(f"  CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

# Train accuracy
model.fit(X, y)
train_pred = model.predict(X)
train_acc = accuracy_score(y, train_pred)
print(f"  Train Accuracy: {train_acc:.4f}")
print(f"  Overfit Gap: {(train_acc - cv_scores.mean())*100:.1f}pp")

# Save model
import pickle
model_path = Path('/home/kazuha/Poly-Trader/model/xgb_model.pkl')
with open(model_path, 'wb') as f:
    pickle.dump(model, f)
print(f"  Model saved to {model_path}")

session.close()
