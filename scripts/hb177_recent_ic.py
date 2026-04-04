#!/usr/bin/env python
"""Recent N=100 IC analysis for heartbeat #177 using raw label_up from features with proper timestamp parsing"""
import sys, os
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

from sqlalchemy import create_engine
import pandas as pd
from datetime import datetime

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
engine = create_engine(f'sqlite:///{DB_PATH}')

# Get features 
df = pd.read_sql("SELECT * FROM features_normalized ORDER BY id DESC LIMIT 1600", engine)
print(f"Fetched {len(df)} records")

# Parse timestamps
df['ts_key'] = pd.to_datetime(df['timestamp'], format='mixed').dt.floor('s')

# Get labels
labels_df = pd.read_sql("SELECT timestamp, label_up, label_sell_win FROM labels", engine)
labels_df['ts_key'] = pd.to_datetime(labels_df['timestamp'], format='mixed').dt.floor('s')

# Merge
merged = df.merge(labels_df[['ts_key', 'label_up', 'label_sell_win']], on='ts_key', how='left', suffixes=('_feat', '_label'))
print(f"Merge: {len(merged)} total, {merged['label_up'].notna().sum()} with label_up, {merged['label_sell_win'].notna().sum()} with label_sell_win")

# Count non-null matches to understand overlap
matched = merged.dropna(subset=['label_up'])
print(f"Matched rows: {len(matched)}")
if len(matched) > 0:
    print(f"Feature timestamps range: {matched['timestamp'].min()} to {matched['timestamp'].max()}")
    print(f"Label timestamps range: {matched['ts_key'].min()} to {matched['ts_key'].max()}")
    
    # Use label_up for recent IC
    sorted_merged = matched.sort_values('timestamp', ascending=False).reset_index(drop=True)
    
    # Recent 100
    recent100 = sorted_merged.head(100)
    senses = {
        'feat_eye': 'Eye', 'feat_ear': 'Ear', 'feat_nose': 'Nose',
        'feat_tongue': 'Tongue', 'feat_body': 'Body', 'feat_pulse': 'Pulse',
        'feat_aura': 'Aura', 'feat_mind': 'Mind'
    }
    
    print("\n=== Recent 100 IC (vs label_up) ===")
    for feat_col, sense_name in senses.items():
        valid = recent100[[feat_col, 'label_up']].dropna()
        if len(valid) >= 10:
            ic = valid[feat_col].corr(valid['label_up'])
            status = 'PASS' if abs(ic) >= 0.05 else 'FAIL'
            print(f'  {sense_name:8s}: IC={ic:+.4f} (n={len(valid)}) {status}')
    
    # Recent 100 vs label_sell_win if available
    if merged['label_sell_win'].notna().sum() > 50:
        sorted_sw = merged.dropna(subset=['label_sell_win']).sort_values('timestamp', ascending=False).reset_index(drop=True)
        recent100_sw = sorted_sw.head(100)
        print("\n=== Recent 100 IC (vs label_sell_win) ===")
        for feat_col, sense_name in senses.items():
            valid = recent100_sw[[feat_col, 'label_sell_win']].dropna()
            if len(valid) >= 10:
                ic = valid[feat_col].corr(valid['label_sell_win'])
                status = 'PASS' if abs(ic) >= 0.05 else 'FAIL'
                print(f'  {sense_name:8s}: IC={ic:+.4f} (n={len(valid)}) {status}')
    else:
        print("\n(No label_sell_win matches found)")
