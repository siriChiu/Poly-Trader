#!/usr/bin/env python
"""Run training with full evaluation."""
import sys, os
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score
from sklearn.model_selection import TimeSeriesSplit
from database.models import init_db
from model.train import load_training_data, train_xgboost

db = init_db('sqlite:///poly_trader.db')
result = load_training_data(db)
if result is None:
    print('No training data available')
    sys.exit(1)

X, y = result
print(f'Training data: {X.shape}')
print(f'Label distribution: {dict(y.value_counts())}')

# Train
model = train_xgboost(X, y)
train_acc = accuracy_score(y, model.predict(X))
print(f'Train accuracy: {train_acc:.4f}')

# Cross validation
tscv = TimeSeriesSplit(n_splits=5)
valid_scores = []
for tr, te in tscv.split(X):
    y_tr = y.iloc[tr]
    if len(y_tr.unique()) < 2:
        continue
    m = xgb.XGBClassifier(**{k: v for k, v in model.get_params().items()})
    m.fit(X.iloc[tr], y_tr)
    valid_scores.append(float((m.predict(X.iloc[te]) == y.iloc[te]).mean()))

cv_acc = np.mean(valid_scores) if valid_scores else float('nan')
cv_std = np.std(valid_scores) if valid_scores else float('nan')
print(f'CV accuracy: {cv_acc:.4f} ± {cv_std:.4f}')
print(f'Gap (train - cv): {train_acc - cv_acc:.4f}')

# Feature importance
imp = dict(zip(X.columns.tolist(), model.feature_importances_.tolist()))
top_features = sorted(imp.items(), key=lambda x: -x[1])[:10]
print(f'\nTop 10 feature importances:')
for feat, val in top_features:
    print(f'  {feat}: {val:.4f}')
