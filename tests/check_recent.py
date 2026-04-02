import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from config import load_config
from database.models import init_db, FeaturesNormalized
import numpy as np

cfg = load_config()
session = init_db(cfg["database"]["url"])

recent = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).limit(30).all()
print("Recent 30 features:")
for f in recent:
    print(f"  {f.timestamp}: tongue={f.feat_tongue_pct}, body={f.feat_body_roc}")

tongue_vals = [f.feat_tongue_pct for f in session.query(FeaturesNormalized).all() if f.feat_tongue_pct is not None]
body_vals = [f.feat_body_roc for f in session.query(FeaturesNormalized).all() if f.feat_body_roc is not None]

tongue_unique = len(set(tongue_vals))
body_unique = len(set(body_vals))
print(f"\nTotal features: {len(tongue_vals)} tongue, {len(body_vals)} body")
print(f"Unique values: {tongue_unique} tongue, {body_unique} body")
print(f"Tongue range: [{min(tongue_vals):.4f}, {max(tongue_vals):.4f}]")
print(f"Body range: [{min(body_vals):.6f}, {max(body_vals):.6f}]")

session.close()
