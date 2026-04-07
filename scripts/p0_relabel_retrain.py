#!/usr/bin/env python3
"""
P0 Fix: Re-label with corrected LONG-based sell_win, retrain with fusion features.

1. Re-label ALL 18,052 entries with correct LONG definition (price up = win)
2. Save with force_update_all=True
3. Retrain global + regime models
"""
import sys
from pathlib import Path
sys.path.insert(0, '/home/kazuha/Poly-Trader')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
from database.models import RawMarketData, FeaturesNormalized, Labels
from data_ingestion.labeling import generate_future_return_labels, save_labels_to_db

db_path = str(Path('/home/kazuha/Poly-Trader/poly_trader.db'))
engine = create_engine(f'sqlite:///{db_path}')
Session = sessionmaker(bind=engine)
session = Session()

# === Part 1: Re-label with LONG-based sell_win ===
print("=== Part 1: Generating labels with corrected LONG-based sell_win ===")
count_before = session.query(Labels).count()
print(f"  Labels in DB before relabeling: {count_before}")

labels_df = generate_future_return_labels(session, symbol="BTCUSDT", horizon_hours=4, threshold_pct=0.005)

if labels_df.empty:
    print("ERROR: No labels generated!")
    sys.exit(1)

sell_win_pct = labels_df['label_sell_win'].mean()
print(f"  Generated {len(labels_df)} labels")
print(f"  sell_win ratio: {sell_win_pct:.2%}")

# Distribution by regime
if len(labels_df) > 0 and 'regime_label' in labels_df.columns:
    print(f"\n  Sell-win by regime:")
    print(f"  {pd.crosstab(labels_df['regime_label'], labels_df['label_sell_win'])}")

# === Part 2: Save ALL labels with force_update_all ===
print(f"\n=== Part 2: Force-updating ALL {len(labels_df)} labels in DB ===")
save_labels_to_db(session, labels_df, symbol="BTCUSDT", horizon_hours=4, force_update_all=True)

# Verify
count_after = session.query(Labels).count()
sell_win_check = session.query(Labels).filter(Labels.label_sell_win == 1).count()
print(f"  Labels in DB: {count_after}")
print(f"  sell_win=1: {sell_win_check} ({sell_win_check/max(count_after,1)*100:.1f}%)")

# === Part 3: Retrain models ===
print("\n=== Part 3: Retraining global model ===")
from model.train import run_training, train_regime_models

result = run_training(session)
print(f"  Global model training: {'SUCCESS' if result else 'FAILED'}")

# Read and print metrics
import json, os
metrics_path = "/home/kazuha/Poly-Trader/model/ic_signs.json"
if os.path.exists(metrics_path):
    with open(metrics_path) as f:
        ic_signs = json.load(f)
    print(f"  Total samples: {ic_signs.get('total_samples', '?')}")

# Read last_metrics.json
last_metrics_path = "/home/kazuha/Poly-Trader/model/last_metrics.json"
if os.path.exists(last_metrics_path):
    with open(last_metrics_path) as f:
        metrics = json.load(f)
    print(f"\n  Global model metrics:")
    print(f"    Train: {metrics.get('train_accuracy', '?')}")
    print(f"    Rolling-CV: {metrics.get('cv_accuracy', '?')}±{metrics.get('cv_std', '?')}")
    print(f"    Features: {metrics.get('n_features', '?')}, Samples: {metrics.get('n_samples', '?')}")

# === Part 4: Retrain regime models ===
print("\n=== Part 4: Retraining regime models with walk-forward CV ===")
regime_stats = train_regime_models(session)
if regime_stats:
    for r, s in regime_stats.items():
        print(f"  {r}: CV={s['cv_accuracy']} Train={s['train_accuracy']} n={s['n_samples']} pos={s['pos_ratio']}")
else:
    print("  Regime models not returned (check logs)")

session.close()
print("\n=== P0 Fix Complete ===")
