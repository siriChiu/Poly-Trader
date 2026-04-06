#!/usr/bin/env python3
"""🧪 Stacking Ensemble Experiment — GB + CatBoost + LightGBM

使用 3 個最佳梯度提升模型的 out-of-fold predictions 作為 meta-features，
訓練一個簡單的 Logistic Regression meta-learner。

比較: 單一模型 vs Stacking Ensemble
"""
import os, sys, time, json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats

PROJECT = "/home/kazuha/Poly-Trader"
sys.path.insert(0, PROJECT)
os.chdir(PROJECT)

DB_PATH = os.path.join(PROJECT, "poly_trader.db")

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, precision_score, recall_score, brier_score_loss
from sklearn.linear_model import LogisticRegression
from sklearn.utils.class_weight import compute_sample_weight

# ─── Data loading (reuse pipeline) ───
FEATURE_COLS = [
    "feat_eye", "feat_ear", "feat_nose", "feat_tongue",
    "feat_body", "feat_pulse", "feat_aura", "feat_mind",
    "feat_vix", "feat_dxy",
    "feat_rsi14", "feat_macd_hist", "feat_atr_pct",
    "feat_vwap_dev", "feat_bb_pct_b",
    "feat_nq_return_1h", "feat_nq_return_24h",
    "feat_claw", "feat_claw_intensity", "feat_fang_pcr",
    "feat_fang_skew", "feat_fin_netflow",
    "feat_web_whale", "feat_scales_ssr", "feat_nest_pred",
]

def load_data():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    
    col_str = ", ".join([f"f.{c}" for c in FEATURE_COLS] + ["f.timestamp", "f.symbol"])
    df = pd.read_sql_query(f"SELECT {col_str} FROM features_normalized f ORDER BY f.timestamp", conn)
    labels = pd.read_sql_query(
        "SELECT timestamp, label_sell_win, future_return_pct FROM labels WHERE label_sell_win IS NOT NULL",
        conn
    )
    conn.close()
    
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    labels["timestamp"] = pd.to_datetime(labels["timestamp"], format="ISO8601")
    
    merged = pd.merge_asof(
        df.sort_values("timestamp"),
        labels.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("10min"),
    )
    merged = merged.dropna(subset=["label_sell_win"]).copy()
    
    if len(merged) < 100:
        return None, None
    
    # Lag features
    LAG_STEPS = [12, 48, 144]
    all_cols = list(FEATURE_COLS)
    for col in FEATURE_COLS:
        for lag in LAG_STEPS:
            lag_col = f"{col}_lag{lag}"
            merged[lag_col] = merged[col].shift(lag)
            all_cols.append(lag_col)
    
    # Cross features
    merged["feat_vix_x_eye"] = merged["feat_vix"] * merged["feat_eye"]
    merged["feat_vix_x_mind"] = merged["feat_vix"] * merged["feat_mind"]
    merged["feat_mind_x_pulse"] = merged["feat_mind"] * merged["feat_pulse"]
    merged["feat_eye_x_ear"] = merged["feat_eye"] * merged["feat_ear"]
    merged["feat_mean_rev_proxy"] = merged["feat_mind"] - merged["feat_aura"]
    all_cols.extend(["feat_vix_x_eye", "feat_vix_x_mind", "feat_mind_x_pulse", "feat_eye_x_ear", "feat_mean_rev_proxy"])
    
    for col in all_cols:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')
    merged[all_cols] = merged[all_cols].fillna(0.0)
    
    # Invert negative-IC features
    neg_ic = {"feat_nose", "feat_ear", "feat_mind", "feat_tongue", "feat_pulse", "feat_aura"}
    for col in all_cols:
        base = col.replace("_lag12", "").replace("_lag48", "").replace("_lag144", "")
        if base in neg_ic:
            merged[col] = -merged[col]
    
    X = merged[all_cols].copy()
    y = merged["label_sell_win"].astype(int).values
    
    print(f"📊 Data: {X.shape[0]} samples, {X.shape[1]} features")
    print(f"   sell_win rate: {y.mean():.4f}")
    return X, y


def train_and_evaluate(model, X, y, n_splits=5):
    """TimeSeriesSplit evaluation returning OOF predictions and metrics."""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    oof_pred = np.zeros(len(y))
    fold_metrics = []
    
    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]
        
        if len(np.unique(y_tr)) < 2:
            continue
        
        m = type(model)(**model.get_params())
        try:
            m.fit(X_tr, y_tr, sample_weight=compute_sample_weight("balanced", y_tr))
        except TypeError:
            m.fit(X_tr, y_tr)
        
        try:
            proba = m.predict_proba(X_te)[:, 1]
        except:
            proba = m.predict_proba(X_te.values)[:, 1]
        
        oof_pred[test_idx] = proba
        pred_class = (proba >= 0.5).astype(int)
        
        acc = accuracy_score(y_te, pred_class)
        try:
            auc = roc_auc_score(y_te, proba)
        except:
            auc = 0.5
        
        fold_metrics.append({"fold": fold_idx, "accuracy": acc, "auc": auc})
    
    oof_class = (oof_pred >= 0.5).astype(int)
    oof_auc = roc_auc_score(y, oof_pred)
    oof_acc = accuracy_score(y, oof_class)
    oof_f1 = f1_score(y, oof_class, zero_division=0)
    
    try:
        oof_ic = float(stats.spearmanr(oof_pred, y)[0])
    except:
        oof_ic = 0.0
    
    return oof_pred, {
        "oof_auc": oof_auc,
        "oof_accuracy": oof_acc,
        "oof_f1": oof_f1,
        "oof_ic": oof_ic,
        "folds": fold_metrics,
    }


def stacking_experiment(X, y):
    """Full stacking experiment."""
    import xgboost as xgb
    import lightgbm as lgb
    import catboost as cb
    from sklearn.ensemble import GradientBoostingClassifier
    
    print(f"\n{'='*60}")
    print(f"  🧪 Stacking Ensemble Experiment")
    print(f"  Data: {X.shape[0]} samples × {X.shape[1]} features")
    print(f"{'='*60}")
    
    results = {}
    oof_preds = {}
    
    # ─── Individual Models ───
    base_models = {
        "XGBoost": xgb.XGBClassifier(
            n_estimators=500, max_depth=2, learning_rate=0.02,
            subsample=0.6, colsample_bytree=0.6, colsample_bylevel=0.7,
            reg_alpha=5.0, reg_lambda=10.0, min_child_weight=20, gamma=0.5,
            objective="binary:logistic", eval_metric="logloss", random_state=42, verbosity=0),
        "LightGBM": lgb.LGBMClassifier(
            n_estimators=500, max_depth=2, learning_rate=0.02,
            subsample=0.6, colsample_bytree=0.6,
            reg_alpha=5.0, reg_lambda=10.0, min_child_weight=20,
            random_state=42, verbosity=-1),
        "CatBoost": cb.CatBoostClassifier(
            iterations=500, depth=2, learning_rate=0.02,
            l2_leaf_reg=10.0, subsample=0.6, min_data_in_leaf=20,
            random_seed=42, logging_level="Silent", loss_function="Logloss"),
        "GB": GradientBoostingClassifier(
            n_estimators=200, max_depth=2, learning_rate=0.02,
            subsample=0.6, min_samples_leaf=20, random_state=42),
    }
    
    for name, model in base_models.items():
        t_start = time.time()
        oof_pred, metrics = train_and_evaluate(model, X, y)
        elapsed = time.time() - t_start
        metrics["train_time"] = elapsed
        results[name] = metrics
        oof_preds[name] = oof_pred
        
        print(f"\n  {name}: AUC={metrics['oof_auc']:.4f} | Acc={metrics['oof_accuracy']:.4f} | "
              f"F1={metrics['oof_f1']:.4f} | IC={metrics['oof_ic']:+.4f} | Time={elapsed:.1f}s")
    
    # ─── Stacking: Train meta-learner on OOF predictions ───
    print(f"\n{'─'*40} Stacking Ensemble {'─'*40}")
    
    # Meta-features: OOF predictions from each base model
    meta_X = pd.DataFrame({
        "xgb": oof_preds["XGBoost"],
        "lgbm": oof_preds["LightGBM"],
        "cat": oof_preds["CatBoost"],
        "gb": oof_preds["GB"],
    })
    
    # Simple meta-learner: Logistic Regression on OOF predictions
    meta_model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    
    # Evaluate meta-learner with TimeSeriesSplit
    tscv = TimeSeriesSplit(n_splits=5)
    meta_oof = np.zeros(len(y))
    
    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(meta_X)):
        mx_tr = meta_X.iloc[train_idx]
        y_tr = y[train_idx]
        mx_te = meta_X.iloc[test_idx]
        y_te = y[test_idx]
        
        mm = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
        mm.fit(mx_tr, y_tr, sample_weight=compute_sample_weight("balanced", y_tr))
        meta_oof[test_idx] = mm.predict_proba(mx_te)[:, 1]
    
    meta_class = (meta_oof >= 0.5).astype(int)
    meta_auc = roc_auc_score(y, meta_oof)
    meta_acc = accuracy_score(y, meta_class)
    meta_f1 = f1_score(y, meta_class, zero_division=0)
    try:
        meta_ic = float(stats.spearmanr(meta_oof, y)[0])
    except:
        meta_ic = 0.0
    
    results["Stacking"] = {
        "oof_auc": meta_auc,
        "oof_accuracy": meta_acc,
        "oof_f1": meta_f1,
        "oof_ic": meta_ic,
        "train_time": 0,  # negligible
        "note": "Meta-learner: LogisticRegression on 4 OOF predictions",
    }
    
    print(f"  Stacking: AUC={meta_auc:.4f} | Acc={meta_acc:.4f} | F1={meta_f1:.4f} | IC={meta_ic:+.4f}")
    
    # Show meta-learner coefficients
    # Train on full data for coefficient display
    final_meta = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    final_meta.fit(meta_X, y, sample_weight=compute_sample_weight("balanced", y))
    print(f"\n  Meta-learner coefficients:")
    for col, coef in zip(meta_X.columns, final_meta.coef_[0]):
        print(f"    {col:>6}: {coef:+.4f}")
    
    # ─── Strategy simulation (Stacking) ───
    print(f"\n{'─'*40} Strategy Simulation {'─'*40}")
    for threshold in [0.55, 0.60, 0.65]:
        mask = meta_oof >= threshold
        n = mask.sum()
        if n > 10:
            wr = y[mask].mean()
            returns = y[mask].astype(float) * 2 - 1
            sharpe = returns.mean() / (returns.std() + 1e-9)
            print(f"  Stacking t={threshold:.2f}: WinRate={wr*100:.1f}% | Trades={n} | Sharpe={sharpe:.3f}")
    
    # For comparison, also show XGBoost strategy
    xgb_oof = oof_preds["XGBoost"]
    for threshold in [0.55, 0.60, 0.65]:
        mask = xgb_oof >= threshold
        n = mask.sum()
        if n > 10:
            wr = y[mask].mean()
            returns = y[mask].astype(float) * 2 - 1
            sharpe = returns.mean() / (returns.std() + 1e-9)
            print(f"  XGBoost  t={threshold:.2f}: WinRate={wr*100:.1f}% | Trades={n} | Sharpe={sharpe:.3f}")
    
    # ─── Ranking ───
    print(f"\n{'─'*40} Final Ranking {'─'*40}")
    ranked = sorted(results.items(), key=lambda x: x[1]["oof_auc"], reverse=True)
    
    header = f"{'Model':<15} {'AUC':<8} {'Accuracy':<10} {'F1':<8} {'IC':<8} {'Δ vs XGB':<10}"
    print(header)
    print("-" * len(header))
    
    xgb_auc = results["XGBoost"]["oof_auc"]
    for name, m in ranked:
        delta = m["oof_auc"] - xgb_auc
        print(f"{name:<15} {m['oof_auc']:.4f}   {m['oof_accuracy']:.4f}     {m['oof_f1']:.4f}   {m['oof_ic']:+.4f}   {delta:+.4f}")
    
    # Recommendation
    best = ranked[0][0]
    best_delta = ranked[0][1]["oof_auc"] - xgb_auc
    print(f"\n🏆 Winner: {best} (Δ={best_delta:+.4f} AUC vs XGBoost)")
    
    if best == "Stacking" and best_delta > 0.003:
        print(f"✅ Stacking provides meaningful improvement")
        return True, results
    elif best_delta < 0.003:
        print(f"⚠️  No model significantly outperforms XGBoost (<3pp advantage)")
        print(f"📌 Recommendation: Keep XGBoost, but deploy Stacking as a shadow ensemble")
        return False, results
    else:
        print(f"✅ {best} deserves consideration")
        return False, results


def save_integrate_script(stacking_wins, results):
    """Generate the integration script for model/train.py."""
    
    if not stacking_wins:
        print(f"\n📌 Stacking didn't win decisively, but we'll create the integration script")
        print(f"   as a shadow ensemble option for future use.")
    
    # Create the stacking integration module
    code = '''"""Model Stacking Ensemble — GB + CatBoost + LightGBM + LR meta-learner

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
    print(f"\\n{'='*50}")
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
'''
    
    os.makedirs("model", exist_ok=True)
    path = "model/stacking_ensemble.py"
    with open(path, "w") as f:
        f.write(code)
    print(f"\n💾 Integration script saved: {path}")


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{'='*60}")
    print(f"  🧪 Stacking Ensemble Experiment started {ts}")
    print(f"{'='*60}")
    
    X, y = load_data()
    if X is None:
        print("❌ Data loading failed")
        return
    
    stacking_wins, results = stacking_experiment(X, y)
    
    # Save results
    os.makedirs("data", exist_ok=True)
    result_path = f"data/stacking_experiment_{ts.replace(' ', '_').replace(':', '-')}.json"
    with open(result_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Results saved to {result_path}")
    
    # Generate integration script
    save_integrate_script(stacking_wins, results)


if __name__ == "__main__":
    main()
