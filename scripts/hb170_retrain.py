"""Heartbeat #131: Retrain XGBoost with max_depth=2 to reduce overfitting."""
import sys
sys.path.insert(0, '.')
from sqlalchemy.orm import Session
from database.models import Base
from sqlalchemy import create_engine
engine = create_engine("sqlite:///poly_trader.db")
from model.train import load_training_data, train_xgboost, save_model
import xgboost as xgb
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
import pickle

session = Session(bind=engine)
loaded = load_training_data(session, min_samples=50)
if loaded is None:
    print('No training data')
    sys.exit(1)

X, y = loaded
print(f'Training data: {X.shape[0]} samples, {X.shape[1]} features')

# Compare old vs new parameters
print('\n=== Parameter comparison ===')
print('Old: max_depth=3, reg_alpha=2.0, reg_lambda=6.0, min_child_weight=10, gamma=0.2')
print('New: max_depth=2, reg_alpha=3.0, reg_lambda=8.0, min_child_weight=15, gamma=0.3')

params_strong = {
    'n_estimators': 200,
    'max_depth': 2,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'reg_alpha': 3.0,
    'reg_lambda': 8.0,
    'min_child_weight': 15,
    'gamma': 0.3,
    'objective': 'binary:logistic',
    'eval_metric': 'logloss',
    'random_state': 42,
}

model = train_xgboost(X, y, params=params_strong)

train_acc = float((model.predict(X) == y).mean())
print(f'\nTrain accuracy: {train_acc:.4f}')

tscv = TimeSeriesSplit(n_splits=5)
cv_scores = []
for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    if len(y_train.unique()) < 2:
        continue
    m = xgb.XGBClassifier(**{k: v for k, v in model.get_params().items()})
    m.fit(X_train, y_train)
    cv_scores.append(float((m.predict(X_test) == y_test).mean()))

cv_mean = np.mean(cv_scores)
cv_std = np.std(cv_scores)
ov_gap = train_acc - cv_mean
print(f'CV accuracy: {cv_mean:.4f} ± {cv_std:.4f}')
print(f'Overfitting gap: {ov_gap:.4f} ({ov_gap*100:.1f}pp)')

# Save model with proper payload
payload = {
    'clf': model,
    'feature_names': X.columns.tolist(),
    'calibration': {'kind': 'none'},
    'regime_threshold_bias': {
        'trend': -0.03, 'chop': 0.04, 'panic': -0.01, 'event': 0.02, 'normal': 0.0
    },
}
save_model(payload)
print('Model saved successfully.')

# Save metrics
metrics = {
    'train_accuracy': train_acc,
    'cv_accuracy': cv_mean,
    'cv_std': cv_std,
    'n_samples': X.shape[0],
    'n_features': X.shape[1],
    'overfit_gap': ov_gap,
    'max_depth': 2,
}
with open('model/last_metrics_heart170.json', 'w') as f:
    json.dump(metrics, f, indent=2)

session.close()
print('Heartbeat #131 retrain complete.')
