#!/usr/bin/env python
"""Recent 100 IC analysis for heartbeat #177"""
import sys, os
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

from sqlalchemy import create_engine
import pandas as pd

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
engine = create_engine(f'sqlite:///{DB_PATH}')

# Recent 100 features - just check which label columns exist on the features table itself
df = pd.read_sql("SELECT * FROM features_normalized ORDER BY id DESC LIMIT 100", engine)
print(f"Fetched {len(df)} records")
print(f"Columns: {list(df.columns)}")

# Get labels table separately
labels = pd.read_sql("SELECT * FROM labels ORDER BY id DESC LIMIT 100", engine)
print(f"Labels: {len(labels)} records")
print(f"Label cols: {list(labels.columns)}")

# Check timestamps match for join
print(f"\nFeature timestamps (last 5):")
print(df['timestamp'].tail(5))
print(f"\nLabel timestamps (last 5):")
print(labels['timestamp'].tail(5))

# Try joining
merged = pd.merge(df, labels, on='timestamp', how='left', suffixes=('_feat', '_label'))
print(f"\nAfter merge: {len(merged)} records, {merged['label_up'].notna().sum()} with label_up, {merged['label_sell_win'].notna().sum() if 'label_sell_win' in merged.columns else 0} with label_sell_win")
