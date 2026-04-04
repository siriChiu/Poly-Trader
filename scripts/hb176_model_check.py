#!/usr/bin/env python3
"""HB #176 - Check model performance"""
import pickle, numpy as np, sqlite3
from pathlib import Path

# Load model
model_path = Path('models/xgb_model.pkl')
if model_path.exists():
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    print(f"Model: {type(model).__name__}")
    if hasattr(model, 'max_depth'):
        print(f"Max depth: {model.max_depth}")
    if hasattr(model, 'feature_importances_'):
        fi = model.feature_importances_
        print(f"Feature importances ({len(fi)} features):")
        top_idx = np.argsort(fi)[-10:][::-1]
        for i in top_idx:
            print(f"  [{i}]: {fi[i]:.4f}")

# CV check - run cross validation
print("\n=== Quick CV Check ===")
conn = sqlite3.connect('poly_trader.db')
feat_cols = ['feat_eye','feat_ear','feat_nose','feat_tongue','feat_body','feat_pulse','feat_aura','feat_mind']
cols_str = ','.join(feat_cols)
rows = conn.execute(f"""
    SELECT f.{cols_str}, l.label_sell_win
    FROM features_normalized f
    INNER JOIN labels l ON f.timestamp = l.timestamp
    WHERE l.label_sell_win IS NOT NULL
    ORDER BY f.timestamp
""").fetchall()

X = np.array([[float(r[i]) for i in range(8)] for r in rows])
y = np.array([float(r[8]) for r in rows])

print(f"Dataset: {X.shape[0]} samples, {X.shape[1]} features")
print(f"Class balance: {y.mean():.4f} positive rate")

if model_path.exists() and hasattr(model, 'predict'):
    pred = model.predict(X)
    acc = (pred == y).mean()
    print(f"Full-train accuracy: {acc:.4f}")
    
    # Last 1000
    pred_last = model.predict(X[-1000:])
    acc_last = (pred_last == y[-1000:]).mean()
    print(f"Last-1000 accuracy: {acc_last:.4f}")
    
    # Bear regime check
    regimes = conn.execute("SELECT regime_label FROM features_normalized ORDER BY timestamp").fetchall()
    regime_arr = [r[0] for r in regimes[-len(rows):]]
    
    for reg in ['bear', 'bull', 'chop']:
        mask = np.array([r == reg for r in regime_arr])
        if mask.sum() > 50:
            pred_r = model.predict(X[mask])
            acc_r = (pred_r == y[mask]).mean()
            print(f"{reg} accuracy ({mask.sum()} samples): {acc_r:.4f}")

conn.close()

# Check if IC fusion code exists
try:
    from model.predictor import predict_with_ic_fusion, _time_weighted_ic
    print("\nIC fusion functions available.")
except ImportError:
    print("\nNo IC fusion functions found in predictor.py")
