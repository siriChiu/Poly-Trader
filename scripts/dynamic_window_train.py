#!/usr/bin/env python
"""Dynamic window training for Poly-Trader.

P0 Fix #H138: IC decay resolved by auto-finding optimal N.

Strategy:
1. Scan range of sample sizes N (200..5000)
2. For each N, compute IC for all 8 senses
3. Select N that maximizes passing senses (|IC| >= 0.05)
4. Tie-break: prefer smaller N (more responsive, less stale data)
5. Train regime-aware model using the optimal window

Usage:
    venv/bin/python scripts/dynamic_window_train.py
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
import numpy as np
import pandas as pd

DB_PATH = str(Path(__file__).parent.parent / 'poly_trader.db')
engine = create_engine(f'sqlite:///{DB_PATH}')
os.chdir(str(Path(__file__).parent.parent))

IC_THRESHOLD = 0.05
SENSE_COLS = {
    'feat_eye': 'Eye', 'feat_ear': 'Ear', 'feat_nose': 'Nose',
    'feat_tongue': 'Tongue', 'feat_body': 'Body', 'feat_pulse': 'Pulse',
    'feat_aura': 'Aura', 'feat_mind': 'Mind'
}

def find_optimal_window(features_df, label_series):
    """Find N that maximizes passing IC senses, tie-breaking to smaller N."""
    data = pd.DataFrame(features_df.copy())
    data['label'] = label_series.values
    data = data.dropna(subset=['label'])
    
    best_n = 1000
    best_score = 0
    results = {}
    
    for n in range(200, min(len(data), 5001), 200):
        window = data.tail(n)
        passing = 0
        ics = {}
        for col, name in SENSE_COLS.items():
            if col not in window.columns:
                continue
            valid = window[[col, 'label']].dropna()
            if len(valid) < 30:
                continue
            ic = valid[col].corr(valid['label'], method='pearson')
            if not np.isnan(ic):
                ics[name] = float(ic)
                if abs(ic) >= IC_THRESHOLD:
                    passing += 1
        
        results[n] = {'passing': passing, 'ics': ics}
        
        if passing > best_score:
            best_score = passing
            best_n = n
    
    return best_n, best_score, results


def main():
    print(f"\n=== Dynamic Window Training [{datetime.utcnow().isoformat()}] ===")
    
    # Load data
    features_df = pd.read_sql('SELECT * FROM features_normalized', engine)
    labels_df = pd.read_sql('SELECT timestamp, label_sell_win, label_up FROM labels', engine)
    
    # Merge
    features_df['ts_key'] = pd.to_datetime(features_df['timestamp'], format='mixed').dt.floor('s')
    labels_df['ts_key'] = pd.to_datetime(labels_df['timestamp'], format='mixed').dt.floor('s')
    
    merged = features_df.merge(labels_df, on='ts_key', suffixes=('', '_label'))
    merged = merged.sort_values('timestamp')
    merged = merged.dropna(subset=['label_sell_win'])
    
    print(f"Merged records with labels: {len(merged)}")
    
    # Find optimal N
    best_n, best_score, all_results = find_optimal_window(merged[list(SENSE_COLS.keys())], merged['label_sell_win'])
    
    print(f"\nOptimal window: N={best_n} ({best_score}/8 senses pass)")
    print(f"IC breakdown at optimal N:")
    for name, ic in all_results[best_n]['ics'].items():
        status = "PASS" if abs(ic) >= IC_THRESHOLD else "fail"
        print(f"  {name:8s}: IC={ic:+.4f} [{status}]")
    
    # Scan summary
    print(f"\nWindow scan summary (N → passing):")
    for n in sorted(all_results.keys()):
        p = all_results[n]['passing']
        marker = " <<<" if n == best_n else ""
        print(f"  N={n:>5}: {p}/8{marker}")
    
    # Save results
    output = {
        'timestamp': datetime.utcnow().isoformat(),
        'optimal_n': best_n,
        'best_score': best_score,
        'scan_results': {str(k): v for k, v in all_results.items()},
    }
    out_path = Path(__file__).parent.parent / 'data' / 'dynamic_window_analysis.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")
    
    # Now train with the optimal window
    print(f"\n=== Training with N={best_n} ===")
    window_data = merged.tail(best_n)
    
    from sklearn.utils.class_weight import compute_sample_weight
    from scipy import stats
    
    # Build feature matrix
    X = window_data[[c for c in SENSE_COLS.keys() if c in window_data.columns]].fillna(0).copy()
    y = window_data['label_sell_win'].astype(int)
    
    # Apply IC sign flip
    for col in X.columns:
        valid = X[col].dropna()
        if len(valid) > 30 and float(valid.std()) > 0:
            ic = stats.spearmanr(valid, y.reindex(valid.index))[0]
            if ic and ic < 0:
                X[col] = -X[col]
    
    lag_steps = [12, 48, 288]
    lag_features = []
    for col in X.columns:
        for lag in lag_steps:
            lag_col = f"{col}_lag{lag}"
            X[lag_col] = X[col].shift(lag)
            lag_features.append(lag_col)
    
    X = X.ffill().bfill()
    X = X.fillna(0)
    
    n_features = len(X.columns)
    print(f"Feature matrix: {X.shape[0]} samples, {n_features} features")
    
    # Train XGBoost with conservative (anti-overfit) params
    import xgboost as xgb
    from sklearn.model_selection import TimeSeriesSplit
    
    params = {
        'n_estimators': 200,
        'max_depth': 3,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'reg_alpha': 2.0,
        'reg_lambda': 6.0,
        'min_child_weight': 10,
        'gamma': 0.2,
        'objective': 'binary:logistic',
        'eval_metric': 'logloss',
        'random_state': 42,
    }
    
    sample_weight = compute_sample_weight('balanced', y)
    
    model = xgb.XGBClassifier(**params)
    
    # Train-CV loop
    model.fit(X, y, sample_weight=sample_weight)
    train_acc = float((model.predict(X) == y).mean())
    
    tscv = TimeSeriesSplit(n_splits=5)
    cv_scores = []
    for train_idx, test_idx in tscv.split(X):
        y_tr = y.iloc[train_idx]
        if len(y_tr.unique()) < 2:
            continue
        m = xgb.XGBClassifier(**params)
        m.fit(X.iloc[train_idx], y_tr)
        cv_scores.append(float((m.predict(X.iloc[test_idx]) == y.iloc[test_idx]).mean()))
    
    cv_acc = float(np.mean(cv_scores)) if cv_scores else 0
    cv_std = float(np.std(cv_scores)) if cv_scores else 0
    
    print(f"Dynamic Window Training Results:")
    print(f"  Window: N={best_n}")
    print(f"  Train accuracy: {train_acc*100:.1f}%")
    print(f"  CV accuracy:    {cv_acc*100:.1f}% +/- {cv_std*100:.1f}%")
    print(f"  Train-CV gap:   {(train_acc-cv_acc)*100:.1f}pp")
    print(f"  Passing senses: {best_score}/8 at N={best_n}")
    
    # Compare to global model
    print(f"\n=== Comparison with Global Model ===")
    print(f"  Global:         Train=71.3%, CV=50.5%, gap=20.8pp")
    print(f"  Dynamic(N={best_n:4d}): Train={train_acc*100:.1f}%, CV={cv_acc*100:.1f}%, gap={(train_acc-cv_acc)*100:.1f}pp")
    
    # Save model if improvement
    if cv_acc > 0.55:  # Better than global baseline
        model_path = Path(__file__).parent.parent / 'model' / 'xgb_model.pkl'
        pickle = __import__('pickle')
        payload = {
            'clf': model,
            'feature_names': X.columns.tolist(),
            'regime_threshold_bias': {},  # placeholder
            'calibration': {'kind': 'none'},
            'dynamic_window': best_n,
        }
        model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(model_path, 'wb') as f:
            pickle.dump(payload, f)
        print(f"\nModel saved (cv={cv_acc*100:.1f}% > 55% threshold)")
    else:
        print(f"\nModel NOT saved (cv={cv_acc*100:.1f}% does not exceed 55% threshold)")
    
    # Record in DB
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS model_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                train_accuracy REAL,
                cv_accuracy REAL,
                cv_std REAL,
                n_features INTEGER,
                notes TEXT
            )
        """)
        notes = f'dynamic_window_N={best_n}, passing_senses={best_score}/8'
        cur.execute("""
            INSERT INTO model_metrics (timestamp, train_accuracy, cv_accuracy, cv_std, n_features, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.utcnow().isoformat(), train_acc, cv_acc, cv_std, n_features, notes))
        conn.commit()
        print(f"Metrics recorded in DB")
    except Exception as e:
        print(f"DB note: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
