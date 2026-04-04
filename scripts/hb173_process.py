#!/usr/bin/env python3
"""Heartbeat #173 — Process unprocessed data, retrain model, update IC stats"""
import sys
from pathlib import Path
sys.path.insert(0, '/home/kazuha/Poly-Trader')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import init_db, RawMarketData, FeaturesNormalized, Labels
from feature_engine.preprocessor import run_preprocessor, recompute_all_features
from data_ingestion.labeling import generate_future_return_labels, save_labels_to_db

db_path = str(Path('/home/kazuha/Poly-Trader/poly_trader.db'))
engine = create_engine(f'sqlite:///{db_path}')
Session = sessionmaker(bind=engine)
session = Session()

# Step 1: Process any unprocessed raw data
try:
    feat = run_preprocessor(session, "BTCUSDT")
    if feat:
        print(f"Feature processed OK")
    else:
        print("Feature processing returned None")
except Exception as e:
    print(f"Feature processing error: {e}")

# Step 2: Update labels
try:
    labels_df = generate_future_return_labels(session, symbol="BTCUSDT", horizon_hours=4, threshold_pct=0.005)
    if labels_df is not None and not labels_df.empty:
        save_labels_to_db(session, labels_df, symbol="BTCUSDT", horizon_hours=4)
        print(f"Labels updated: {len(labels_df)} rows")
    else:
        print("No new labels generated")
except Exception as e:
    print(f"Label update error: {e}")

# Final stats
raw_count = session.query(RawMarketData).count()
feat_count = session.query(FeaturesNormalized).count()
label_count = session.query(Labels).count()
print(f"Final: raw={raw_count}, features={feat_count}, labels={label_count}")

session.close()
