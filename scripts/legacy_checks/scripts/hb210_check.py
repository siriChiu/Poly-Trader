#!/usr/bin/env python3
"""Heartbeat #210: Check merge loss and VIX/DXY data quality"""
import sqlite3
import pandas as pd

db = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')
feat = pd.read_sql('SELECT * FROM features_normalized', db)
label = pd.read_sql('SELECT * FROM labels', db)
feat_ids = set(feat['id'])
label_ids = set(label['id'])
print(f'Feature IDs: {len(feat_ids)}, Label IDs: {len(label_ids)}')
print(f'In both: {len(feat_ids & label_ids)}')
print(f'In features only: {len(feat_ids - label_ids)}')
print(f'In labels only: {len(label_ids - feat_ids)}')

feat_only_ids = feat_ids - label_ids
if feat_only_ids:
    feat_only = feat[feat['id'].isin(feat_only_ids)]
    print(f'\nFeature-only rows: {len(feat_only)}')
    if feat_only['feat_vix'].count() > 0:
        vix_vals = pd.to_numeric(feat_only['feat_vix'], errors='coerce')
        print(f'  VIX non-null: {vix_vals.notna().sum()}, mean: {vix_vals.mean():.2f}')
    if feat_only['feat_dxy'].count() > 0:
        dxy_vals = pd.to_numeric(feat_only['feat_dxy'], errors='coerce')
        print(f'  DXY non-null: {dxy_vals.notna().sum()}, mean: {dxy_vals.mean():.2f}')

# Check if VIX/DXY NaN is causing IC to be ~0
merged = feat.merge(label, on=['id','timestamp','symbol'], how='inner', suffixes=('_f','_l'))
print(f'\nMerged: {len(merged)} rows')
vix_col = pd.to_numeric(merged['feat_vix'], errors='coerce')
dxy_col = pd.to_numeric(merged['feat_dxy'], errors='coerce')
y_col = merged['label_spot_long_win'].astype(float)
y_centered = y_col - y_col.mean()

import numpy as np
vix_valid = merged[merged['feat_vix'].notna() & merged['feat_dxy'].notna()]
print(f'Rows with both VIX and DXY: {len(vix_valid)}')

if len(vix_valid) > 0:
    y_v = vix_valid['label_spot_long_win'].astype(float)
    yc = y_v - y_v.mean()
    
    vix_v = vix_valid['feat_vix'].astype(float)
    dxy_v = vix_valid['feat_dxy'].astype(float)
    
    vix_ic = np.corrcoef(vix_v, yc)[0, 1]
    dxy_ic = np.corrcoef(dxy_v, yc)[0, 1]
    print(f'VIX IC (valid rows only): {vix_ic:+.4f}')
    print(f'DXY IC (valid rows only): {dxy_ic:+.4f}')

# Check VIX/DXY distribution
print(f'\n=== VIX/DXY Distribution ===')
print(f'VIX: nulls={merged["feat_vix"].isna().sum()}, zeros={(merged["feat_vix"]==0).sum()}, '
      f'non-zero non-null={(merged["feat_vix"]!=0).sum() - merged["feat_vix"].isna().sum()}')
print(f'DXY: nulls={merged["feat_dxy"].isna().sum()}, zeros={(merged["feat_dxy"]==0).sum()}, '
      f'non-zero non-null={(merged["feat_dxy"]!=0).sum() - merged["feat_dxy"].isna().sum()}')

db.close()
