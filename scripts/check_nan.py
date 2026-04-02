
import sys
sys.path.insert(0, r"C:\Users\Kazuha\repo\Poly-Trader")
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import load_config
from model.predictor import load_predictor
import json

cfg = load_config()
engine = create_engine(cfg["database"]["url"])

with engine.connect() as conn:
    row = conn.execute(text("""
        SELECT timestamp, feat_eye_dist, feat_ear_zscore, feat_nose_sigmoid,
               feat_tongue_pct, feat_body_roc, feat_pulse, feat_aura, feat_mind
        FROM features_normalized ORDER BY timestamp DESC LIMIT 1
    """)).fetchone()

if row:
    feat = {
        "feat_eye_dist": row[1], "feat_ear_zscore": row[2],
        "feat_nose_sigmoid": row[3], "feat_tongue_pct": row[4],
        "feat_body_roc": row[5], "feat_pulse": row[6],
        "feat_aura": row[7], "feat_mind": row[8]
    }
    print("Latest features:", json.dumps({k: float(v) if v is not None else None for k,v in feat.items()}, indent=2))
    predictor = load_predictor()
    conf = predictor.predict_proba(feat)
    sig = "BUY" if conf >= 0.65 else ("SELL" if conf <= 0.35 else "HOLD")
    print(f"Confidence: {conf:.4f} -> Signal: {sig}")
else:
    print("No data")
