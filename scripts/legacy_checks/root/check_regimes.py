#!/usr/bin/env python3
"""Regime-Aware IC analysis standalone"""
import sqlite3
import numpy as np
from scipy.stats import pearsonr

db = sqlite3.connect("/home/kazuha/Poly-Trader/poly_trader.db")

features = db.execute('SELECT * FROM features_normalized').fetchall()
feat_cols = [desc[0] for desc in db.execute('SELECT * FROM features_normalized LIMIT 1').description]
labels = db.execute('SELECT timestamp, future_return_pct, label_spot_long_win, regime_label FROM labels WHERE future_return_pct IS NOT NULL').fetchall()

# Get regime distribution from labels table
regime_counts = {}
for row in labels:
    r = row[3] if row[3] is not None else 'Unknown'
    regime_counts[r] = regime_counts.get(r, 0) + 1
print("Regime distribution in labels:", regime_counts)

# Check what's in features regime_label
feat_regime_counts = {}
regime_feat_col = feat_cols.index('regime_label')
for f in features:
    r = f[regime_feat_col] if f[regime_feat_col] is not None else 'None'
    feat_regime_counts[r] = feat_regime_counts.get(r, 0) + 1
print("Regime distribution in features:", feat_regime_counts)

db.close()
