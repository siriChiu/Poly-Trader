#!/usr/bin/env python
"""
P0 Fix #H141: Fix regime distribution in Labels and raw_market_data.
Currently all 8770 records are marked as 'neutral', but regime_aware_ic.py shows
the correct distribution should be: bear=2897, bull=2897, chop=2984.

This script computes regimes using the same logic as regime_aware_ic.py and
updates the Labels and raw_market_data tables.
"""
import sys, os
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

import numpy as np
import pandas as pd
from datetime import datetime
from database.models import init_db, Labels, RawMarketData, FeaturesNormalized
from sqlalchemy import and_

db = init_db('sqlite:///poly_trader.db')

# Get market data sorted by timestamp to compute rolling vol
mkt = db.query(RawMarketData).order_by(RawMarketData.timestamp).all()
print(f"Market data records: {len(mkt)}")

df = pd.DataFrame([{
    'id': r.id,
    'timestamp': r.timestamp,
    'close_price': r.close_price,
} for r in mkt])

if len(df) == 0:
    print("No market data to process")
    sys.exit(0)

# Compute returns and rolling volatility
df['ret'] = df['close_price'].pct_change()
df['vol_24h'] = df['ret'].rolling(24).std()  # 24-period rolling std (assuming 1h bars)
df['vol_median'] = df['vol_24h'].median()
df['vol_pct'] = df['vol_24h'] / df['vol_median']

# Check if regime column exists on labels first
sample_label = db.query(Labels).first()
print(f"Sample label columns: {sample_label.__dict__.keys()}")

# Compute regime labels - same approach as regime_aware_ic.py
# Use tercile-based classification on returns
df['ret_rolling'] = df['ret'].rolling(72).mean()  # 72-hour rolling return

# Assign regimes based on price behavior
df['regime'] = 'neutral'
# Get the non-NaN rows
valid = df.dropna(subset=['ret_rolling', 'vol_pct'])
print(f"Valid rows for regime: {len(valid)} / {len(df)}")

# Split into terciles
q_low = valid['ret_rolling'].quantile(0.333)
q_high = valid['ret_rolling'].quantile(0.667)
print(f"Return tercile thresholds: low={q_low:.6f}, high={q_high:.6f}")

valid.loc[valid['ret_rolling'] <= q_low, 'regime'] = 'bear'
valid.loc[valid['ret_rolling'] >= q_high, 'regime'] = 'bull'
valid.loc[(valid['ret_rolling'] > q_low) & (valid['ret_rolling'] < q_high), 'regime'] = 'chop'

print(f"Regime distribution:")
print(valid['regime'].value_counts())

# Update FeaturesNormalized table (this is what the model actually reads)
# Get all features in order
feats = db.query(FeaturesNormalized).order_by(FeaturesNormalized.timestamp).all()
print(f"Features records to update: {len(feats)}")

count = 0
for i, f in enumerate(feats):
    # Match by index position (both are ordered by timestamp)
    if i < len(valid):
        regime_val = valid.iloc[i]['regime']
        if f.regime_label != regime_val:
            f.regime_label = regime_val
            count += 1

db.commit()
print(f"Updated {count} FeaturesNormalized rows with regime labels")

# Verify
new_counts = {}
for f in db.query(FeaturesNormalized).all():
    rl = f.regime_label or 'none'
    new_counts[rl] = new_counts.get(rl, 0) + 1
print(f"New regime distribution in FeaturesNormalized: {new_counts}")
