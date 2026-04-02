
path = r"C:\Users\Kazuha\repo\Poly-Trader\dashboard\app.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Step 1: Fix the SELECT to include all 8 senses
old_q = "SELECT timestamp, feat_eye_dist, feat_ear_zscore, feat_nose_sigmoid,\n               feat_tongue_pct, feat_body_roc\n        FROM features_normalized\n        ORDER BY timestamp DESC\n        LIMIT 1"
new_q = "SELECT timestamp, feat_eye_dist, feat_ear_zscore, feat_nose_sigmoid,\n               feat_tongue_pct, feat_body_roc, feat_pulse, feat_aura, feat_mind\n        FROM features_normalized\n        ORDER BY timestamp DESC\n        LIMIT 1"
content = content.replace(old_q, new_q)
print("Step1 col fix:", old_q in content or new_q in content)

# Step 2: Replace the fake weighted score calc with real predictor call
old_calc = 'weights = [0.2]*5\n        vals = df.iloc[0][["feat_eye_dist","feat_ear_zscore","feat_nose_sigmoid","feat_tongue_pct","feat_body_roc"]].fillna(0).values\n        score = sum(v * w for v, w in zip(vals, weights))\n        import numpy as np\n        confidence = 1/(1+np.exp(-score))\n        df["confidence"] = confidence\n        df["signal"] = "BUY" if confidence > 0.5 else "HOLD"'
new_calc = 'try:\n            from model.predictor import load_predictor as _lp\n            _pred = _lp()\n            row = df.iloc[0]\n            feats = {"feat_eye_dist": row.get("feat_eye_dist"), "feat_ear_zscore": row.get("feat_ear_zscore"), "feat_nose_sigmoid": row.get("feat_nose_sigmoid"), "feat_tongue_pct": row.get("feat_tongue_pct"), "feat_body_roc": row.get("feat_body_roc"), "feat_pulse": row.get("feat_pulse"), "feat_aura": row.get("feat_aura"), "feat_mind": row.get("feat_mind")}\n            conf_v = _pred.predict_proba(feats)\n            df["confidence"] = conf_v if conf_v is not None else 0.5\n        except Exception as _ex:\n            df["confidence"] = 0.5\n        conf_val = float(df.iloc[0]["confidence"])\n        df["signal"] = "BUY" if conf_val >= 0.65 else ("SELL" if conf_val <= 0.35 else "HOLD")'
if old_calc in content:
    content = content.replace(old_calc, new_calc)
    print("Step2 calc fix: OK")
else:
    print("Step2 calc fix: not matched exactly, check content")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
