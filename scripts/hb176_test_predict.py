#!/usr/bin/env python3
"""HB #176 - Test if actual predictor loads properly from the system"""
import os, sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')

os.chdir('/home/kazuha/Poly-Trader')

# Test actual predictor load
from model.predictor import load_predictor
predictor, models = load_predictor()
print(f"Predictor type: {type(predictor).__name__}")
print(f"Regime models available: {list(models.keys())}")

# Test a prediction with dummy features
test_features = {
    "feat_eye": 0.3, "feat_ear": 0.5, "feat_nose": 0.7,
    "feat_tongue": 0.1, "feat_body": -0.2, "feat_pulse": 0.4,
    "feat_aura": -0.1, "feat_mind": 0.6,
    "feat_vix": 1.0, "feat_dxy": 0.5,
    "regime_label": "bear"
}

try:
    proba = predictor.predict_proba(test_features)
    print(f"Prediction probability: {proba:.4f}")
    signal = predictor.predict_signal(test_features)
    print(f"Signal: {signal}")
except Exception as e:
    print(f"Prediction error: {e}")
    import traceback
    traceback.print_exc()
