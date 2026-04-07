#!/usr/bin/env python3
"""P0 Fix #SELL_WIN: Re-label all data with corrected LONG-based sell_win, then retrain."""
import sys
from pathlib import Path
sys.path.insert(0, '/home/kazuha/Poly-Trader')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
from database.models import init_db, RawMarketData, FeaturesNormalized, Labels
from data_ingestion.labeling import generate_future_return_labels, save_labels_to_db

db_path = str(Path('/home/kazuha/Poly-Trader/poly_trader.db'))
engine = create_engine(f'sqlite:///{db_path}')
Session = sessionmaker(bind=engine)
session = Session()

# === Part 1: Delete stale labels (had wrong sell_win definition) ===
print("=== Part 1: Deleting stale labels with short-biased sell_win ===")
count_before = session.query(Labels).count()
print(f"  Labels before deletion: {count_before}")

# Delete only labels with horizon_minutes=240 (4h horizon which is what labeling.py uses)
deleted = session.query(Labels).filter(Labels.horizon_minutes == 240).delete()
session.commit()
print(f"  Deleted {deleted} labels with horizon=4h")

# === Part 2: Regenerate labels with correct LONG-based sell_win ===
print("\n=== Part 2: Generating labels with corrected sell_win definition ===")
labels_df = generate_future_return_labels(session, symbol="BTCUSDT", horizon_hours=4, threshold_pct=0.005)

if labels_df.empty:
    print("ERROR: No labels generated!")
    sys.exit(1)

sell_win_pct = labels_df['label_sell_win'].mean()
print(f"  Generated {len(labels_df)} labels")
print(f"  sell_win ratio: {sell_win_pct:.2%}")

# Check by regime distribution
regime_dist = pd.crosstab(labels_df['regime_label'], labels_df['label_sell_win'])
print(f"\n  Label distribution by regime:")
print(f"  {regime_dist}")

# === Part 3: Save labels to DB ===
print("\n=== Part 3: Saving corrected labels to DB ===")
save_labels_to_db(session, labels_df, symbol="BTCUSDT", horizon_hours=4)

# Verify
count_after = session.query(Labels).count()
sell_win_check = session.query(Labels).filter(Labels.label_sell_win == 1).count()
print(f"  Labels in DB after: {count_after}")
print(f"  sell_win=1 count: {sell_win_check} ({sell_win_check/count_after*100:.1f}%)")

# === Part 4: Retrain models ===
print("\n=== Part 4: Retraining models with corrected labels ===")
from model.train import run_training, train_regime_models

result = run_training(session)
print(f"  Global model training: {'SUCCESS' if result else 'FAILED'}")

result = train_regime_models(session) 
print(f"  Regime models training: {'SUCCESS' if result else 'FAILED'}")

session.close()
print("\n=== P0 Fix Complete ===")
