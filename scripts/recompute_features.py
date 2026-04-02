from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from config import load_config
from database.models import FeaturesNormalized, RawMarketData, init_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

cfg = load_config()
session = init_db(cfg["database"]["url"])

raw_rows = session.query(RawMarketData).order_by(RawMarketData.timestamp).all()
feat_rows = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
logger.info(f"Raw records: {len(raw_rows)}, Feature records: {len(feat_rows)}")

fng_map = {
    r.timestamp.replace(minute=0, second=0, microsecond=0): r.fear_greed_index
    for r in raw_rows
}
raw_by_ts = {
    r.timestamp.replace(minute=0, second=0, microsecond=0): float(r.close_price)
    for r in raw_rows
    if r.close_price is not None
}

fng_values = [v for v in fng_map.values() if v is not None]
if fng_values:
    fng_arr = np.array(fng_values, dtype=float)
    fng_mean = float(fng_arr.mean())
    fng_std = float(fng_arr.std())
else:
    fng_mean = 0.0
    fng_std = 0.0

closes = []
updated = 0
for feat in feat_rows:
    ts_key = feat.timestamp.replace(minute=0, second=0, microsecond=0)

    fng_val = fng_map.get(ts_key)
    if fng_val is not None and fng_std > 0:
        z = (float(fng_val) - fng_mean) / fng_std
        feat.feat_tongue_pct = float(math.tanh(z))

    close_val = raw_by_ts.get(ts_key)
    if close_val is not None:
        closes.append(close_val)
        if len(closes) >= 48:
            window = closes[-48:]
            lo = min(window)
            hi = max(window)
            feat.feat_body_roc = float((closes[-1] - lo) / (hi - lo + 1e-10))
        elif len(closes) >= 2:
            prev = closes[-2]
            if prev != 0:
                feat.feat_body_roc = float((closes[-1] - prev) / prev)
    updated += 1

session.commit()
logger.info(f"Updated {updated} feature records")

feat_check = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).limit(5).all()
for f in feat_check:
    logger.info(f"  ts={f.timestamp}: tongue={f.feat_tongue_pct:.4f}, body={f.feat_body_roc}")

body_vals = [f.feat_body_roc for f in session.query(FeaturesNormalized).all() if f.feat_body_roc is not None]
logger.info(f"Body stats: mean={np.mean(body_vals):.6f}, std={np.std(body_vals):.6f}")

session.close()
print("\nDone! Features recomputed.")
