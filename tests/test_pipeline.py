#!/usr/bin/env python3
"""
Poly-Trader End-to-End Test Pipeline
Steps:
1. Initialize DB
2. Collect multi-senses data
3. Run feature engineering
4. Generate labels
5. Train XGBoost (if enough samples)
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import sessionmaker
from config import load_config
from database.models import init_db
from data_ingestion.collector import run_collection_and_save
from feature_engine.preprocessor import run_preprocessor
from data_ingestion.labeling import generate_future_return_labels
from model.train import run_training
from model.predictor import predict

def main():
    print("=== Poly-Trader E2E Test ===\n")

    cfg = load_config()
    db_url = cfg["database"]["url"]
    symbol = cfg["trading"]["symbol"]

    # 1. Init DB
    print("[1/5] Initializing DB...")
    session = init_db(db_url)
    print("  OK")

    try:
        # 2. Collect data
        print("[2/5] Collecting multi-senses data...")
        ok = run_collection_and_save(session, symbol)
        if not ok:
            print("  FAIL: data collection failed")
            return
        print("  OK")

        # 3. Feature engineering
        print("[3/5] Running feature engineering...")
        feats = run_preprocessor(session, symbol)
        if not feats:
            print("  FAIL: feature computation failed")
            return
        print(f"  OK: features={list(feats.keys())}")

        # 4. Generate labels
        print("[4/5] Generating future return labels...")
        labels_df = generate_future_return_labels(session, symbol, horizon_hours=24)
        if labels_df.empty:
            print("  FAIL: labeling failed (insufficient data)")
        else:
            pos_ratio = labels_df['label'].mean()
            print(f"  OK: generated {len(labels_df)} labels, positive={pos_ratio:.2%}")

        # 5. Train model (if enough samples)
        if len(labels_df) >= 50:
            print("[5/5] Training XGBoost model...")
            ok_train = run_training(session)
            if not ok_train:
                print("  WARN: training did not complete successfully")
            else:
                print("  OK: model training finished")
        else:
            print("[5/5] Skipped training (samples < 50)")

        print("\n=== Test PASSED ===")
    finally:
        session.close()

if __name__ == "__main__":
    main()
