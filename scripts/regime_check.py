#!/usr/bin/env python
"""Heartbeat Step 2: Regimen and VIX/DXY IC analysis"""
import sqlite3
import numpy as np
import pandas as pd
import json
import sys

DB_PATH = "/home/kazuha/Poly-Trader/poly_trader.db"
conn = sqlite3.connect(DB_PATH)

raw_df = pd.read_sql_query("SELECT * FROM raw_market_data ORDER BY timestamp", conn)
feat_df = pd.read_sql_query("SELECT * FROM features_normalized ORDER BY timestamp", conn)
label_df = pd.read_sql_query("SELECT * FROM labels ORDER BY timestamp", conn)

# Check if regime column exists
feat_cols = feat_df.columns.tolist()
print("Feature columns:", feat_cols)
print("\nHas regime:", 'regime' in feat_cols)

# Check for vix/dxy in raw
raw_cols = raw_df.columns.tolist()
print("Raw columns:", raw_cols)
print("\nHas vix:", any('vix' in c.lower() for c in raw_cols))
print("Has dxy:", any('dxy' in c.lower() for c in raw_cols))

# Check if there's a separate table for VIX
tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
print("\nTables:", tables['name'].tolist())

# Try to get regime from different sources
for c in feat_cols:
    print(f"  {c} - dtype: {feat_df[c].dtype}, nulls: {feat_df[c].isnull().sum()}, unique: {feat_df[c].nunique()}")

# Check model_metrics for CV
metrics_df = pd.read_sql_query("SELECT * FROM model_metrics ORDER BY id DESC LIMIT 5", conn)
print("\n=== Recent Model Metrics ===")
print(metrics_df.to_string())

conn.close()
