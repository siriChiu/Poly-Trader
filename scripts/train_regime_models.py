#!/usr/bin/env python3
"""
P0 Fix #H145 (Phase 2): Train and save per-regime DecisionTree models.
These models consistently outperform the global XGBoost model:
  Bear: CV 55.6% vs Global 51.3%  (+4.3pp)
  Bull: CV 59.0% vs Global 51.3%  (+7.7pp)
  Chop: CV 52.6% vs Global 51.3%  (+1.3pp)

This script trains and saves models for integration into the prediction pipeline.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
import numpy as np
import pickle
import json
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import TimeSeriesSplit
from collections import defaultdict
from datetime import datetime
from sklearn.preprocessing import StandardScaler

MODEL_DIR = PROJECT_ROOT / "model"
MODEL_PATH = MODEL_DIR / "regime_models.pkl"

conn = sqlite3.connect(str(PROJECT_ROOT / "poly_trader.db"))

# Get all data with regime labels
rows = conn.execute('''
    SELECT f.regime_label, f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue,
           f.feat_body, f.feat_pulse, f.feat_aura, f.feat_mind, 
           l.label_sell_win
    FROM features_normalized f
    JOIN labels l ON f.timestamp = l.timestamp
    WHERE l.label_sell_win IS NOT NULL AND f.regime_label IN ('bear', 'bull', 'chop')
    ORDER BY f.timestamp
''').fetchall()

print(f"Total samples: {len(rows)}")

# Group by regime
regime_data = defaultdict(list)
for r in rows:
    regime_data[r[0]].append(r)

BASE_FEATURE_NAMES = ["feat_eye", "feat_ear", "feat_nose", "feat_tongue",
                      "feat_body", "feat_pulse", "feat_aura", "feat_mind"]
FEATURE_IDX = list(range(1, 9))

regime_models = {}

for regime_name in ['bear', 'bull', 'chop']:
    regime_rows = regime_data[regime_name]
    if len(regime_rows) < 100:
        print(f"{regime_name}: too few samples ({len(regime_rows)})")
        continue
    
    X = np.array([[float(r[i]) for i in FEATURE_IDX] for r in regime_rows])
    X = np.nan_to_num(X, nan=0.0)
    y = np.array([r[9] for r in regime_rows]).astype(int)
    
    print(f"\n{'='*60}")
    print(f"{regime_name.upper()} regime (n={len(X)}, pos_rate={y.mean():.3f})")
    print(f"{'='*60}")
    
    best_cv = 0
    best_model_data = None
    for depth in [2, 3, 4, 5]:
        for min_leaf in [10, 20, 50, 100]:
            tscv = TimeSeriesSplit(n_splits=5)
            scores = []
            for tr_idx, te_idx in tscv.split(X):
                if len(np.unique(y[tr_idx])) < 2:
                    continue
                clf = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=min_leaf, random_state=42)
                clf.fit(X[tr_idx], y[tr_idx])
                scores.append((clf.predict(X[te_idx]) == y[te_idx]).mean())
            
            if scores:
                cv_mean = np.mean(scores)
                if cv_mean > best_cv:
                    best_cv = cv_mean
                    final_clf = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=min_leaf, random_state=42)
                    final_clf.fit(X, y)
                    best_model_data = {
                        'model': final_clf,
                        'params': {'max_depth': depth, 'min_samples_leaf': min_leaf},
                        'train_acc': final_clf.score(X, y),
                        'cv': cv_mean,
                        'feature_names': BASE_FEATURE_NAMES,
                        'pos_rate': float(y.mean()),
                    }
    
    if best_model_data:
        regime_models[regime_name] = best_model_data
        gap = (best_model_data['train_acc'] - best_model_data['cv']) * 100
        p = best_model_data['params']
        print(f"  depth={p['max_depth']}, min_leaf={p['min_samples_leaf']}")
        print(f"  Train: {best_model_data['train_acc']:.3f}, CV: {best_model_data['cv']:.3f}")
        print(f"  Gap: {gap:.1f}pp")

# Also compute global decision tree for comparison
global_X = np.array([[float(r[i]) for i in FEATURE_IDX] for r in rows])
global_X = np.nan_to_num(global_X, nan=0.0)
global_y = np.array([r[9] for r in rows]).astype(int)

global_best_cv = 0
global_model_info = {}
for depth in [2, 3, 4, 5]:
    for min_leaf in [10, 20, 50, 100]:
        tscv = TimeSeriesSplit(n_splits=5)
        scores = []
        for tr_idx, te_idx in tscv.split(global_X):
            if len(np.unique(global_y[tr_idx])) < 2:
                continue
            clf = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=min_leaf, random_state=42)
            clf.fit(global_X[tr_idx], global_y[tr_idx])
            scores.append((clf.predict(global_X[te_idx]) == global_y[te_idx]).mean())
        if scores:
            cv = np.mean(scores)
            if cv > global_best_cv:
                final_global = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=min_leaf, random_state=42)
                final_global.fit(global_X, global_y)
                global_best_cv = cv
                global_model_info = {
                    'model': final_global,
                    'train_acc': final_global.score(global_X, global_y),
                    'cv': cv,
                    'params': {'max_depth': depth, 'min_samples_leaf': min_leaf},
                }

# Get current XGBoost metrics
current_xgboost_cv = None
metrics_path = MODEL_DIR / "last_metrics.json"
try:
    # Try model directory first
    with open(metrics_path) as f:
        m = json.load(f)
        current_xgboost_cv = m.get('cv', {}).get('accuracy', m.get('cv_accuracy', m.get('cv_mean')))
except Exception:
    pass

# Try other possible locations
for alt_path in [PROJECT_ROOT / "data" / "last_metrics.json", PROJECT_ROOT / "output" / "last_metrics.json"]:
    if current_xgboost_cv is None and alt_path.exists():
        try:
            with open(alt_path) as f:
                m = json.load(f)
                current_xgboost_cv = m.get('cv', {}).get('accuracy', m.get('cv_accuracy', m.get('cv_mean')))
        except:
            pass

# Save regime models
save_data = {
    'timestamp': datetime.utcnow().isoformat(),
    'type': 'regime_ensemble',
    'regime_models': regime_models,
    'global_decision_tree': global_model_info,
    'global_dt_cv': global_best_cv,
    'current_xgboost_cv': current_xgboost_cv,
}

with open(MODEL_PATH, "wb") as f:
    pickle.dump(save_data, f, protocol=pickle.HIGHEST_PROTOCOL)

print(f"\n{'='*60}")
print(f"Model saved to: {MODEL_PATH}")
print(f"Global DT CV: {global_best_cv:.3f}")
if current_xgboost_cv:
    print(f"XGBoost CV: {current_xgboost_cv:.3f}")
print(f"{'='*60}")

print("\n=== REGIME MODEL SUMMARY ===")
for name, data in regime_models.items():
    gap = (data['train_acc'] - data['cv']) * 100
    improvement = (data['cv'] - global_best_cv) * 100
    print(f"  {name:6s}: CV={data['cv']:.3f} (gap={gap:.1f}pp, vs global=+{improvement:.1f}pp)")

conn.close()
