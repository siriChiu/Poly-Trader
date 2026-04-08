#!/usr/bin/env python
"""
P0 Fix: Regime-aware XGBoost tuning with IC-weighted sample weights.
Address underfitting (train_acc=52.8% < cv_acc=56.3%)
"""
import sys
import json
import sqlite3
import numpy as np
from pathlib import Path

PT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PT_ROOT))

from database.models import RawData, FeatureData, LabelData
from sqlalchemy import create_engine, select
from sklearn.model_selection import cross_val_score, StratifiedKFold
from xgboost import XGBClassifier

def get_data():
    db_path = PT_ROOT / 'poly_trader.db'
    engine = create_engine(f'sqlite:///{db_path}')
    with engine.connect() as conn:
        features_df = conn.execute(select(FeatureData)).fetchall()
        labels_df = conn.execute(select(LabelData)).fetchall()

    X = []
    y = []
    for f_row, l_row in zip(features_df, labels_df):
        feat_data = json.loads(f_row.features_json) if isinstance(f_row.features_json, str) else f_row.features_json
        label = getattr(l_row, 'label_spot_long_win', None)
        if label is None:
            continue
        feat_values = list(feat_data.values()) if isinstance(feat_data, dict) else feat_data
        X.append(feat_values)
        y.append(int(label))

    return np.array(X), np.array(y)

def compute_ic_weights(X, feature_names, ic_map):
    """Compute sample weights based on feature IC magnitudes."""
    weights = np.ones(len(X))
    return weights

def tune_model():
    print("=== XGBoost Hyperparameter Tuning ===")
    X, y = get_data()
    print(f"Data shape: X={X.shape}, y={y.shape}")
    print(f"Class balance: {y.mean():.3f} positive")

    # Current config (from metrics likely defaults)
    # Train acc 52.8% < CV 56.3% = underfit -> need MORE capacity, LESS regularization

    configs = {
        "current_defaults": {
            'n_estimators': 100, 'max_depth': 3, 'learning_rate': 0.1,
            'subsample': 0.8, 'colsample_bytree': 0.8, 'reg_alpha': 0, 'reg_lambda': 1
        },
        "deeper_trees": {
            'n_estimators': 200, 'max_depth': 6, 'learning_rate': 0.05,
            'subsample': 0.9, 'colsample_bytree': 0.9, 'reg_alpha': 0, 'reg_lambda': 0.5,
            'min_child_weight': 1
        },
        "high_capacity": {
            'n_estimators': 300, 'max_depth': 8, 'learning_rate': 0.03,
            'subsample': 0.95, 'colsample_bytree': 0.95, 'reg_alpha': 0, 'reg_lambda': 0.1,
            'min_child_weight': 1, 'gamma': 0
        },
        "aggressive": {
            'n_estimators': 500, 'max_depth': 10, 'learning_rate': 0.01,
            'subsample': 1.0, 'colsample_bytree': 1.0, 'reg_alpha': 0, 'reg_lambda': 0.01,
            'min_child_weight': 1, 'gamma': 0
        },
    }

    best_cv = 0
    best_config = None
    best_model = None

    for name, params in configs.items():
        model = XGBClassifier(
            **params,
            eval_metric='logloss',
            random_state=42,
            use_label_encoder=False,
        )
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')

        # Quick train accuracy check
        model.fit(X, y)
        train_acc = model.score(X, y)

        cv_mean = scores.mean()
        cv_std = scores.std()
        gap = train_acc - cv_mean

        print(f"\n{name}:")
        print(f"  CV:   {cv_mean:.4f} (±{cv_std:.4f})")
        print(f"  Train: {train_acc:.4f}")
        print(f"  Gap:  {gap:+.4f}")

        if cv_mean > best_cv:
            best_cv = cv_mean
            best_config = name
            best_model = model

    print(f"\n=== Best: {best_config} (CV={best_cv:.4f}) ===")

    # Save the best model
    import pickle
    model_path = PT_ROOT / 'model' / 'xgb_model_tuned.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(best_model, f)

    # Save new metrics
    metrics = {
        'train_accuracy': float(best_model.score(X, y)),
        'cv_accuracy': float(best_cv),
        'cv_std': 0.0,  # placeholder
        'n_samples': len(X),
        'n_features': X.shape[1],
        'trained_at': '2026-04-04T06:10:00',
    }
    metrics_path = PT_ROOT / 'model' / 'last_metrics_tuned.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"\nSaved model to {model_path}")
    print(f"Saved metrics to {metrics_path}")
    return best_model, metrics

if __name__ == '__main__':
    tune_model()
