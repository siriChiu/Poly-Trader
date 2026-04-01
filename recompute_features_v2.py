"""
重新計算所有特徵（v3 快速版）
直接從 raw_market_data 逐行計算 features_normalized。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import math
import numpy as np
from config import load_config
from database.models import init_db, FeaturesNormalized, RawMarketData
from utils.logger import setup_logger

logger = setup_logger(__name__)

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

cfg = load_config()
session = init_db(cfg["database"]["url"])

raw_rows = session.query(RawMarketData).order_by(RawMarketData.timestamp).all()
logger.info(f"Raw records: {len(raw_rows)}")

# Compute ear_zscore from funding_rate series (ear_prob has near-zero variance)
fr_vals = [float(r.funding_rate) for r in raw_rows if r.funding_rate is not None]
fr_mean = np.mean(fr_vals) if fr_vals else 0
fr_std = np.std(fr_vals) if len(fr_vals) > 1 else 1

logger.info(f"Funding Rate stats: mean={fr_mean:.8f}, std={fr_std:.8f} (for ear_zscore)")

# Clear old features
session.query(FeaturesNormalized).delete()
session.commit()

# Eye stats for normalization
eye_vals = [r.eye_dist for r in raw_rows if r.eye_dist is not None]
eye_min = min(eye_vals) if eye_vals else 0
eye_max = max(eye_vals) if eye_vals else 1

records = []
for r in raw_rows:
    # Eye: min-max normalize to -1~1
    if r.eye_dist is not None and (eye_max - eye_min) > 0:
        eye = 2 * (r.eye_dist - eye_min) / (eye_max - eye_min) - 1
    else:
        eye = 0.0

    # Ear: z-score of funding_rate, compressed to -1~1 via tanh(z/2)
    if r.funding_rate is not None and fr_std > 0:
        ear_z = float(math.tanh(((float(r.funding_rate) - fr_mean) / fr_std) / 2))
    else:
        ear_z = 0.0

    # Nose: funding rate sigmoid
    if r.funding_rate is not None:
        s = sigmoid(float(r.funding_rate) * 10000)
        nose = 2 * s - 1
    else:
        nose = 0.0

    # Tongue: v3 sentiment or FNG fallback
    if r.tongue_sentiment is not None:
        tongue = float(r.tongue_sentiment)
    elif r.fear_greed_index is not None:
        tongue = (float(r.fear_greed_index) - 50) / 50  # 0~100 → -1~1
    else:
        tongue = 0.0

    # Body: stablecoin_mcap ROC
    body = float(r.stablecoin_mcap) if r.stablecoin_mcap is not None else 0.0

    records.append(FeaturesNormalized(
        timestamp=r.timestamp,
        feat_eye_dist=float(eye) if eye is not None else None,
        feat_ear_zscore=float(ear_z),
        feat_nose_sigmoid=float(nose),
        feat_tongue_pct=float(tongue),
        feat_body_roc=float(body),
    ))

session.add_all(records)
session.commit()
logger.info(f"Saved {len(records)} feature records")

# Stats
tongue_vals = [f.feat_tongue_pct for f in records if f.feat_tongue_pct is not None]
body_vals = [f.feat_body_roc for f in records if f.feat_body_roc is not None]
eye_vals = [f.feat_eye_dist for f in records if f.feat_eye_dist is not None]
ear_vals = [f.feat_ear_zscore for f in records if f.feat_ear_zscore is not None]
nose_vals = [f.feat_nose_sigmoid for f in records if f.feat_nose_sigmoid is not None]

for name, vals in [("Eye", eye_vals), ("Ear", ear_vals), ("Nose", nose_vals), ("Tongue", tongue_vals), ("Body", body_vals)]:
    if vals:
        logger.info(f"{name}: unique={len(set(vals))}, range=[{min(vals):.6f}, {max(vals):.6f}], std={np.std(vals):.6f}")

session.close()
print("Done!")
