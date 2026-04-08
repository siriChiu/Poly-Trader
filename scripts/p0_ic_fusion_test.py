#!/usr/bin/env python3
"""
P0 Fix #H137: IC-Weighted Signal Fusion
Instead of relying on LR/XGBoost models that produce ~50% CV accuracy,
this implements a direct IC-weighted multi-signal voting system.

Rationale: When ML models can't extract signal better than random,
direct weighted combination using IC as weights is more robust.
"""
import sys, os, json, pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import sqlite3
import warnings
warnings.filterwarnings('ignore')
from scipy.stats import spearmanr
from sklearn.model_selection import TimeSeriesSplit

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'poly_trader.db')

def run_ic_fusion():
    conn = sqlite3.connect(DB_PATH)
    
    # Load features and labels
    import pandas as pd
    feats = pd.read_sql_query('SELECT * FROM features_normalized', conn)
    labels = pd.read_sql_query('SELECT * FROM labels WHERE label_spot_long_win IS NOT NULL', conn)
    
    merged = feats.merge(labels[['timestamp', 'label_spot_long_win', 'regime_label']],
                        on='timestamp', how='inner')
    
    senses = ['eye', 'ear', 'nose', 'tongue', 'body', 'pulse', 'aura', 'mind']
    sense_cols = {s: f'feat_{s}' for s in senses}
    
    # Calculate IC for each sense
    ics = {}
    for s, col in sense_cols.items():
        valid = merged[[col, 'label_spot_long_win']].dropna()
        if len(valid) > 10:
            corr, _ = spearmanr(valid[col], valid['label_spot_long_win'])
            ics[s] = float(corr)
    
    print("=== IC-Weighted Signal Fusion ===")
    print(f"Sensory ICs: {ics}")
    
    # Regime-aware IC
    n = len(merged)
    third = n // 3
    regimes = {
        'bear': merged.iloc[:third],
        'chop': merged.iloc[third:2*third],
        'bull': merged.iloc[2*third:]
    }
    
    regime_ics = {}
    for rname, rdf in regimes.items():
        r_ics = {}
        for s, col in sense_cols.items():
            valid = rdf[[col, 'label_spot_long_win']].dropna()
            if len(valid) > 100:
                corr, _ = spearmanr(valid[col], valid['label_spot_long_win'])
                r_ics[s] = float(corr)
        regime_ics[rname] = r_ics
        print(f"{rname.upper()} IC: {r_ics}")
    
    # IC-weighted signal fusion
    # For each sample: weighted_vote = sum(|IC_s| * sign(IC_s) * feature_s)
    valid = merged.dropna(subset=[f'feat_{s}' for s in senses]).copy()
    y = valid['label_spot_long_win'].values
    
    # Test fusion approach 1: global IC-weighted sum
    ic_weights = np.array([ics[s] for s in senses])
    X = valid[[f'feat_{s}' for s in senses]].values
    
    # Weighted signal: sum of |IC| * sign(IC) * feat = sum(IC * feat)
    signal = X @ ic_weights
    # Predict: if signal < 0 -> sell_win (negative IC means high value → sell_win=1)
    # Normalize to probability using sigmoid
    from scipy.special import expit
    # Optimal threshold search
    best_acc = 0
    best_thresh = 0
    for pct in range(0, 101, 1):
        thresh = np.percentile(signal, pct)
        pred = (signal < thresh).astype(int)  # negative signal → sell_win=1
        acc = (pred == y).mean()
        if acc > best_acc:
            best_acc = acc
            best_thresh = thresh
    
    print(f"\n=== Fusion Results ===")
    print(f"Dumb threshold: {best_acc*100:.1f}% at p{np.searchsorted(np.sort(signal), best_thresh)*100//len(signal)}")
    
    # Test with cross-validation
    tscv = TimeSeriesSplit(n_splits=5)
    cv_accs = []
    for train_idx, test_idx in tscv.split(X):
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]
        
        # Calculate IC on training set
        tr_ics = np.zeros(8)
        for i in range(8):
            c, _ = spearmanr(X_tr[:, i], y_tr)
            tr_ics[i] = c if np.isfinite(c) else 0
        
        signal_te = X_te @ tr_ics
        # Optimize threshold on train
        signal_tr = X_tr @ tr_ics
        best_t = 0
        best_a = 0
        for pct in range(0, 101, 1):
            t = np.percentile(signal_tr, pct)
            p = (signal_tr < t).astype(int)
            a = (p == y_tr).mean()
            if a > best_a:
                best_a = a
                best_t = t
        
        pred_te = (signal_te < best_t).astype(int)
        cv_accs.append((pred_te == y_te).mean())
    
    cv_mean = np.mean(cv_accs)
    cv_std = np.std(cv_accs)
    print(f"IC-Fusion CV: {cv_mean*100:.1f}% ± {cv_std*100:.1f}%")
    
    # Compare against LR/XGBoost baselines
    from sklearn.linear_model import LogisticRegression
    from xgboost import XGBClassifier
    from sklearn.model_selection import cross_val_score
    
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr_scores = cross_val_score(lr, X, y, cv=5, scoring='accuracy')
    print(f"LR CV: {lr_scores.mean()*100:.1f}%")
    
    xgb = XGBClassifier(n_estimators=200, max_depth=3, random_state=42,
                        reg_alpha=2.0, reg_lambda=6.0, learning_rate=0.05,
                        min_child_weight=10, gamma=0.2,
                        use_label_encoder=False, eval_metric='logloss')
    xgb_scores = cross_val_score(xgb, X, y, cv=5, scoring='accuracy')
    print(f"XGB CV: {xgb_scores.mean()*100:.1f}%")
    
    # Regime-specific IC-weighted fusion
    print("\n=== Regime-Specific IC Fusion CV ===")
    for rname, rdf in regimes.items():
        valid_r = rdf.dropna(subset=[f'feat_{s}' for s in senses]).copy()
        y_r = valid_r['label_spot_long_win'].values
        X_r = valid_r[[f'feat_{s}' for s in senses]].values
        
        if len(X_r) < 200:
            print(f"{rname.upper()}: too few samples ({len(X_r)})")
            continue
        
        r_tscv = TimeSeriesSplit(n_splits=3)
        r_cv_accs = []
        for train_idx, test_idx in r_tscv.split(X_r):
            X_tr, X_te = X_r[train_idx], X_r[test_idx]
            y_tr, y_te = y_r[train_idx], y_r[test_idx]
            
            tr_ics = np.zeros(8)
            for i in range(8):
                c, _ = spearmanr(X_tr[:, i], y_tr)
                tr_ics[i] = c if np.isfinite(c) else 0
            
            signal_tr = X_tr @ tr_ics
            signal_te = X_te @ tr_ics
            
            # Optimize threshold on train
            best_t = 0
            best_a = 0
            for pct in range(0, 101, 1):
                t = np.percentile(signal_tr, pct)
                p = (signal_tr < t).astype(int)
                a = (p == y_tr).mean()
                if a > best_a:
                    best_a = a
                    best_t = t
            
            pred_te = (signal_te < best_t).astype(int)
            r_cv_accs.append((pred_te == y_te).mean())
        
        r_mean = np.mean(r_cv_accs)
        r_std = np.std(r_cv_accs)
        print(f"{rname.upper()}: {r_mean*100:.1f}% ± {r_std*100:.1f}% (n={len(X_r)})")
    
    conn.close()

if __name__ == "__main__":
    run_ic_fusion()
