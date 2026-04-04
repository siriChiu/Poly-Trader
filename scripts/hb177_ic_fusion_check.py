#!/usr/bin/env python
"""Validate IC fusion in predictor.py for heartbeat #177"""
import sys, os
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

from model.predictor import RegimeAwarePredictor

# Try loading the model and checking available methods
pred = RegimeAwarePredictor()
print(f"Predictor class: {pred.__class__.__name__}")
print(f"Dir: {[m for m in dir(pred) if not m.startswith('_')]}")

# Check if ic_fusion method exists
if hasattr(pred, 'predict_with_ic_fusion'):
    print("predict_with_ic_fusion: EXISTS")
else:
    print("predict_with_ic_fusion: MISSING")

# Load model and check
if os.path.exists('data/xgb_model.pkl'):
    import joblib
    model = joblib.load('data/xgb_model.pkl')
    print(f"XGB Model loaded: {type(model).__name__}")
    if hasattr(model, 'feature_names_in_'):
        print(f"Features: {model.feature_names_in_}")
else:
    # Check models/ directory
    models_dir = 'models/'
    if os.path.exists(models_dir):
        for f in os.listdir(models_dir):
            print(f"Model file: {f}")
    else:
        print("No models/ directory")
