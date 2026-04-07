"""
端到端值驗證：收集多特徵 → 計算特徵 → 確認值
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config
from database.models import init_db, RawMarketData, FeaturesNormalized
from data_ingestion.collector import run_collection_and_save
from feature_engine.preprocessor import run_preprocessor

cfg = load_config()
session = init_db(cfg["database"]["url"])
symbol = cfg["trading"]["symbol"]

print(f"=== E2E Pipeline Test (symbol={symbol}) ===\n")

# Step 1: Collect
print("Step 1: Collecting multi-senses...")
ok = run_collection_and_save(session, symbol)
print(f"  Collection: {'OK' if ok else 'FAILED'}")

if ok:
    # Step 2: Preprocess
    print("\nStep 2: Computing features...")
    features = run_preprocessor(session, symbol)
    if features:
        print("  Features computed:")
        for k, v in features.items():
            if k != "timestamp":
                status = "OK" if v is not None else "NULL"
                print(f"    {k} = {v} [{status}]")
    else:
        print("  Feature computation FAILED")

# Step 3: Check DB state
print(f"\n=== Database State ===")
raw_count = session.query(RawMarketData).count()
feat_count = session.query(FeaturesNormalized).count()
print(f"Raw records: {raw_count}")
print(f"Feature records: {feat_count}")

latest_raw = session.query(RawMarketData).order_by(RawMarketData.timestamp.desc()).first()
if latest_raw:
    print(f"\nLatest raw data:")
    print(f"  close_price  = {latest_raw.close_price}")
    print(f"  funding_rate = {latest_raw.funding_rate}")
    print(f"  fng_index    = {latest_raw.fear_greed_index}")
    print(f"  body_roc     = {latest_raw.stablecoin_mcap}")
    print(f"  polymkt_prob = {latest_raw.polymarket_prob}")
    print(f"  eye_dist     = {latest_raw.eye_dist}")
    print(f"  ear_prob     = {latest_raw.ear_prob}")

latest_feat = session.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp.desc()).first()
if latest_feat:
    print(f"\nLatest features:")
    for col in ["feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid", "feat_tongue_pct", "feat_body_roc"]:
        val = getattr(latest_feat, col)
        status = "OK" if val is not None else "NULL"
        print(f"  {col} = {val} [{status}]")

session.close()
print("\n=== E2E Test Complete ===")
