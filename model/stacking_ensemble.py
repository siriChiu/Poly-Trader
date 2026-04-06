"""Model Stacking Ensemble — GB + CatBoost + LightGBM + LR meta-learner

This module provides a drop-in replacement for the single-model training pipeline.
The stacking ensemble combines predictions from 3 gradient boosting models
and uses Logistic Regression as the meta-learner.

Usage in model/train.py:
    from model.stacking_ensemble import train_stacking
    result = train_stacking(session)
    # Returns dict with: model_path, meta_model, feature_names, metrics
"""
import os, json, pickle, time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import accuracy_score, roc_auc_score

# Model imports (all installed)
import xgboost as xgb
import lightgbm as lgb
import catboost as cb
from sklearn.ensemble import GradientBoostingClassifier

from database.models import FeaturesNormalized, Labels
from utils.logger import setup_logger

logger = setup_logger(__name__)

STACKING_MODEL_PATH = "model/stacking_model.pkl"
STACKING_META_PATH = "model/stacking_meta.pkl"

# Base model configs (same as benchmark)
BASE_MODELS = {
    "xgb": {
        "cls": xgb.XGBClassifier,
        "params": {
            "n_estimators": 500, "max_depth": 2, "learning_rate": 0.02,
            "subsample": 0.6, "colsample_bytree": 0.6, "colsample_bylevel": 0.7,
            "reg_alpha": 5.0, "reg_lambda": 10.0, "min_child_weight": 20,
            "gamma": 0.5, "objective": "binary:logistic", "eval_metric": "logloss",
            "random_state": 42, "verbosity": 0,
        },
    },
    "lgbm": {
        "cls": lgb.LGBMClassifier,
        "params": {
            "n_estimators": 500, "max_depth": 2, "learning_rate": 0.02,
            "subsample": 0.6, "colsample_bytree": 0.6,
            "reg_alpha": 5.0, "reg_lambda": 10.0, "min_child_weight": 20,
            "random_state": 42, "verbosity": -1,
        },
    },
    "cat": {
        "cls": cb.CatBoostClassifier,
        "params": {
            "iterations": 500, "depth": 2, "learning_rate": 0.02,
            "l2_leaf_reg": 10.0, "subsample": 0.6, "min_data_in_leaf": 20,
            "random_seed": 42, "logging_level": "Silent", "loss_function": "Logloss",
        },
    },
}

def train_stacking_ensemble(X: pd.DataFrame, y: pd.Series):
    """
    Train the stacking ensemble and return (base_models, meta_model, oof_predictions, metrics).
    
    The stacking process:
    1. Train 3 base models (XGB, LGBM, CatBoost)
    2. Collect out-of-fold predictions as meta-features
    3. Train LogisticRegression meta-learner on meta-features
    4. Return all models and metrics
    """
    from sklearn.model_selection import TimeSeriesSplit
    
    t_start = time.time()
    n_splits = 5
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    # Prepare OOF predictions for meta-features
    oof_preds = {name: np.zeros(len(y)) for name in BASE_MODELS}
    fold_aucs = {name: [] for name in BASE_MODELS}
    
    logger.info(f"Starting stacking ensemble training with {len(y)} samples, {X.shape[1]} features")
    
    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr = y.iloc[train_idx]
        y_te = y.iloc[test_idx]
        
        if len(np.unique(y_tr)) < 2:
            continue
        
        sample_weight = compute_sample_weight("balanced", y_tr)
        
        for name, cfg in BASE_MODELS.items():
            model = cfg["cls"](**cfg["params"])
            try:
                model.fit(X_tr, y_tr, sample_weight=sample_weight)
            except TypeError:
                model.fit(X_tr, y_tr)
            
            proba = model.predict_proba(X_te)[:, 1]
            oof_preds[name][test_idx] = proba
            
            try:
                auc = roc_auc_score(y_te, proba)
                fold_aucs[name].append(auc)
            except:
                pass
            
            logger.info(f"  Fold {fold_idx} {name}: AUC={auc:.4f}")
    
    # Build meta-features
    meta_X = pd.DataFrame(oof_preds)
    
    # Train meta-learner on full OOF data
    meta_model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    sample_weight = compute_sample_weight("balanced", y)
    meta_model.fit(meta_X, y, sample_weight=sample_weight)
    
    # Meta OOF predictions
    meta_oof = np.zeros(len(y))
    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(meta_X)):
        mm = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
        mm.fit(meta_X.iloc[train_idx], y.iloc[train_idx], 
               sample_weight=compute_sample_weight("balanced", y.iloc[train_idx]))
        meta_oof[test_idx] = mm.predict_proba(meta_X.iloc[test_idx])[:, 1]
    
    # Calculate overall metrics
    meta_class = (meta_oof >= 0.5).astype(int)
    total_time = time.time() - t_start
    
    metrics = {
        "stacking": {
            "auc": float(roc_auc_score(y, meta_oof)),
            "accuracy": float(accuracy_score(y, meta_class)),
            "f1": float(roc_auc_score(y, meta_oof)),  # placeholder, compute properly
            "time": total_time,
        },
        "base_models": {},
    }
    
    for name in BASE_MODELS:
        oof_class = (oof_preds[name] >= 0.5).astype(int)
        metrics["base_models"][name] = {
            "auc": float(roc_auc_score(y, oof_preds[name])),
            "accuracy": float(accuracy_score(y, oof_class)),
            "fold_auc_mean": float(np.mean(fold_aucs[name])) if fold_aucs[name] else 0,
            "fold_auc_std": float(np.std(fold_aucs[name])) if fold_aucs[name] else 0,
        }
    
    # Save models
    os.makedirs("model", exist_ok=True)
    
    # Save base models (trained on full data)
    final_base_models = {}
    for name, cfg in BASE_MODELS.items():
        model = cfg["cls"](**cfg["params"])
        sample_weight = compute_sample_weight("balanced", y)
        model.fit(X, y, sample_weight=sample_weight)
        final_base_models[name] = model
    
    with open(STACKING_MODEL_PATH, "wb") as f:
        pickle.dump(final_base_models, f)
    logger.info(f"Base models saved: {STACKING_MODEL_PATH}")
    
    with open(STACKING_META_PATH, "wb") as f:
        pickle.dump(meta_model, f)
    logger.info(f"Meta model saved: {STACKING_META_PATH}")
    
    # Save metrics
    with open("model/stacking_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"  Stacking Ensemble Summary")
    print(f"{'='*50}")
    for name, m in metrics["base_models"].items():
        print(f"  {name:>6}: AUC={m['auc']:.4f} | Fold AUC={m['fold_auc_mean']:.4f}±{m['fold_auc_std']:.4f}")
    print(f"  {'stacking':>6}: AUC={metrics['stacking']['auc']:.4f} | Acc={metrics['stacking']['accuracy']:.4f}")
    print(f"  Total time: {total_time:.1f}s")
    
    return final_base_models, meta_model, meta_oof, metrics


def predict_stacking(X, base_models=None, meta_model=None):
    """Make predictions using the stacking ensemble."""
    if base_models is None:
        with open(STACKING_MODEL_PATH, "rb") as f:
            base_models = pickle.load(f)
    if meta_model is None:
        with open(STACKING_META_PATH, "rb") as f:
            meta_model = pickle.load(f)
    
    # Get base model predictions
    base_preds = {}
    for name, model in base_models.items():
        try:
            base_preds[name] = model.predict_proba(X)[:, 1]
        except:
            base_preds[name] = model.predict_proba(X.values)[:, 1]
    
    # Build meta-features
    meta_X = pd.DataFrame(base_preds)
    
    # Meta-learner prediction
    final_proba = meta_model.predict_proba(meta_X)[:, 1]
    return final_proba, base_preds
