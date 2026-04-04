#!/usr/bin/env python
"""
P0 Fix #H145: Regime-aware training.
Train per-regime models instead of one global model that fails for Bull (0/8) regime.
This addresses the fundamental issue that a single global model dilutes regime-specific signals.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
import numpy as np
import json
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import TimeSeriesSplit

conn = sqlite3.connect('poly_trader.db')
cur = conn.cursor()

# Get all data with regime labels
rows = cur.execute('''
    SELECT f.regime_label, f.feat_eye, f.feat_ear, f.feat_nose, f.feat_tongue,
           f.feat_body, f.feat_pulse, f.feat_aura, f.feat_mind, 
           l.label_sell_win
    FROM features_normalized f
    JOIN labels l ON f.timestamp = l.timestamp
    WHERE l.label_sell_win IS NOT NULL AND f.regime_label != 'neutral'
    ORDER BY f.timestamp
''').fetchall()

print(f"Total samples: {len(rows)}")

# Group by regime
from collections import defaultdict
regime_data = defaultdict(list)
for r in rows:
    regime_data[r[0]].append(r)

FEATURE_IDX = list(range(1, 9))

for regime_name in ['bear', 'bull', 'chop']:
    regime_rows = regime_data[regime_name]
    if len(regime_rows) < 100:
        print(f"{regime_name}: too few samples ({len(regime_rows)})")
        continue
    
    X = np.array([[float(r[i]) for i in FEATURE_IDX] for r in regime_rows])
    y = np.array([r[9] for r in regime_rows])
    
    # NaN fill
    X = np.nan_to_num(X, nan=0.0)
    
    print(f"\n{'='*60}")
    print(f"{regime_name.upper()} regime (n={len(X)}, pos_rate={y.mean():.3f})")
    print(f"{'='*60}")
    
    # Train with shallow trees (regularized)
    best_cv = 0
    best_params = {}
    for depth in [2, 3, 4, 5]:
        for min_samples_leaf in [20, 50, 100]:
            tscv = TimeSeriesSplit(n_splits=5)
            scores = []
            for tr_idx, te_idx in tscv.split(X):
                if len(np.unique(y[tr_idx])) < 2:
                    continue
                clf = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=min_samples_leaf, random_state=42)
                clf.fit(X[tr_idx], y[tr_idx])
                pred = clf.predict(X[te_idx])
                scores.append((pred == y[te_idx]).mean())
            
            if scores:
                cv_mean = np.mean(scores)
                train_acc = clf.fit(X, y).score(X, y)
                if cv_mean > best_cv:
                    best_cv = cv_mean
                    best_params = {'depth': depth, 'min_leaf': min_samples_leaf, 'train': train_acc, 'cv': cv_mean}
    
    print(f"  Best: depth={best_params['depth']}, min_leaf={best_params['min_leaf']}")
    print(f"  Train: {best_params['train']:.3f}, CV: {best_params['cv']:.3f}")
    print(f"  Gap: {(best_params['train'] - best_params['cv'])*100:.1f}pp")
    
# Global model (same approach for comparison)
global_X = np.array([[float(r[i]) for i in FEATURE_IDX] for r in rows])
global_y = np.array([r[9] for r in rows])
global_X = np.nan_to_num(global_X, nan=0.0)

best_global_cv = 0
for depth in [2, 3, 4, 5]:
    for min_samples_leaf in [20, 50, 100]:
        tscv = TimeSeriesSplit(n_splits=5)
        scores = []
        for tr_idx, te_idx in tscv.split(global_X):
            if len(np.unique(global_y[tr_idx])) < 2:
                continue
            clf = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=min_samples_leaf, random_state=42)
            clf.fit(global_X[tr_idx], global_y[tr_idx])
            pred = clf.predict(global_X[te_idx])
            scores.append((pred == global_y[te_idx]).mean())
        if scores:
            cv = np.mean(scores)
            if cv > best_global_cv:
                best_global_cv = cv

print(f"\n{'='*60}")
print(f"GLOBAL model best CV: {best_global_cv:.3f}")
print(f"{'='*60}")

conn.close()
