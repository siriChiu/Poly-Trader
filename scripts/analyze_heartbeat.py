#!/usr/bin/env python3
"""Full heartbeat analysis - Steps 1 and 2"""
import sqlite3
import sys
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'poly_trader.db')

if not os.path.exists(db_path):
    print(f"ERROR: Database not found at {db_path}")
    sys.exit(1)

db = sqlite3.connect(db_path)

# List all tables
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
table_names = [t[0] for t in tables]
print(f"=== DATABASE SCHEMA ===")
print(f"Tables: {table_names}")

# Print schema for each table
for tname in table_names:
    cols = db.execute(f'PRAGMA table_info("{tname}")').fetchall()
    cnt = db.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
    col_details = [(c[1], c[2]) for c in cols]
    print(f"  {tname}: {cnt} rows, columns: {col_details}")

# Get data counts
raw_count = cnt
features_count = 0
labels_count = 0

for tname in table_names:
    cnt = db.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
    if 'raw' in tname.lower() or 'data' in tname.lower():
        raw_count = cnt
    elif 'feature' in tname.lower():
        features_count = cnt
    elif 'label' in tname.lower():
        labels_count = cnt

print(f"\n=== DATA COUNTS ===")
print(f"Raw: {raw_count}, Features: {features_count}, Labels: {labels_count}")

# Find price data
for tname in table_names:
    cols = [c[1] for c in db.execute(f'PRAGMA table_info("{tname}")').fetchall()]
    if 'close' in cols or 'price' in cols:
        row = db.execute(f'SELECT * FROM "{tname}" ORDER BY rowid DESC LIMIT 1').fetchone()
        print(f"\n=== Latest {tname} ===")
        for col, val in zip(cols, row):
            print(f"  {col}: {val}")
        
        # Get previous row for change calculation
        rows = db.execute(f'SELECT * FROM "{tname}" ORDER BY rowid DESC LIMIT 2').fetchall()
        if len(rows) >= 2:
            r1, r2 = rows[0], rows[1]
            if 'close' in cols:
                idx = cols.index('close')
                try:
                    change = (float(r1[idx]) - float(r2[idx])) / float(r2[idx]) * 100
                    print(f"  CHANGE: {change:+.2f}%")
                except:
                    pass
        break

# Sell win stats
for tname in table_names:
    cols = [c[1] for c in db.execute(f'PRAGMA table_info("{tname}")').fetchall()]
    if 'sell_win' in cols:
        sw = db.execute(f'SELECT AVG(sell_win) FROM "{tname}" WHERE sell_win IS NOT NULL').fetchone()
        print(f"\n=== SELL WIN STATS ===")
        print(f"Global sell_win: {sw[0]:.4f}")
        
        for n in [500, 100, 50]:
            recent = db.execute(f'SELECT AVG(sell_win) FROM (SELECT sell_win FROM "{tname}" WHERE sell_win IS NOT NULL ORDER BY rowid DESC LIMIT {n})').fetchone()
            if recent[0] is not None:
                print(f"Recent sell_win (last {n}): {recent[0]:.4f}")

# Fear & Greed
for tname in table_names:
    cols = [c[1] for c in db.execute(f'PRAGMA table_info("{tname}")').fetchall()]
    if 'fear' in tname.lower() or 'greed' in tname.lower() or 'fng' in cols:
        val_col = 'value' if 'value' in cols else cols[1] if len(cols) > 1 else cols[0]
        fng = db.execute(f'SELECT "{val_col}" FROM "{tname}" ORDER BY rowid DESC LIMIT 1').fetchone()
        if fng:
            print(f"FNG: {fng[0]}")

# Derivatives
for tname in table_names:
    if 'deriv' in tname.lower():
        cols = [c[1] for c in db.execute(f'PRAGMA table_info("{tname}")').fetchall()]
        row = db.execute(f'SELECT * FROM "{tname}" ORDER BY rowid DESC LIMIT 1').fetchone()
        print(f"\n=== DERIVATIVES ===")
        for col, val in zip(cols, row):
            print(f"  {col}: {val}")

# VIX
for tname in table_names:
    if 'vix' in tname.lower():
        cols = [c[1] for c in db.execute(f'PRAGMA table_info("{tname}")').fetchall()]
        val_col = 'value' if 'value' in cols else cols[0]
        row = db.execute(f'SELECT "{val_col}" FROM "{tname}" ORDER BY rowid DESC LIMIT 1').fetchone()
        if row:
            print(f"\nVIX: {row[0]:.2f}")

# DXY
for tname in table_names:
    if 'dxy' in tname.lower():
        cols = [c[1] for c in db.execute(f'PRAGMA table_info("{tname}")').fetchall()]
        val_col = 'value' if 'value' in cols else cols[0]
        row = db.execute(f'SELECT "{val_col}" FROM "{tname}" ORDER BY rowid DESC LIMIT 1').fetchone()
        if row:
            print(f"DXY: {row[0]:.2f}")

# IC Analysis
print(f"\n=== IC ANALYSIS ===")
try:
    import numpy as np
    from scipy.stats import spearmanr
    
    # Feature store
    feat_table = None
    for tname in table_names:
        if 'feature' in tname.lower():
            feat_table = tname
            break
    
    label_table = None
    for tname in table_names:
        if 'label' in tname.lower():
            label_table = tname
            break
    
    if not feat_table:
        print("No feature table found, skipping IC analysis")
    else:
        feat_cols = [c[1] for c in db.execute(f'PRAGMA table_info("{feat_table}")').fetchall()]
        print(f"Feature table: {feat_table}, columns: {feat_cols[:20]}")
        
        if label_table:
            label_cols = [c[1] for c in db.execute(f'PRAGMA table_info("{label_table}")').fetchall()]
            print(f"Label table: {label_table}, columns: {label_cols[:20]}")
            
            # Get sell_win
            if 'sell_win' in label_cols:
                print("IC against sell_win...")
                # Get all data
                feat_data = db.execute(f'SELECT * FROM "{feat_table}"').fetchall()
                label_data = db.execute(f'SELECT sell_win FROM "{label_table}"').fetchall()
                
                n_samples = len(feat_data)
                n_labels = len(label_data)
                min_n = min(n_samples, n_labels)
                
                print(f"Feature samples: {n_samples}, Labels: {n_labels}, min: {min_n}")
                
                # Calculate IC for each feature column
                for col in feat_cols:
                    if col in ['id', 'timestamp', 'date', 'rowid']:
                        continue
                    
                    vals = []
                    labels = []
                    for i in range(min_n):
                        fv = feat_data[i][col]
                        lv = label_data[i][0]
                        if fv is not None and lv is not None:
                            try:
                                vals.append(float(fv))
                                labels.append(float(lv))
                            except (ValueError, TypeError):
                                pass
                    
                    if len(vals) > 100:
                        arr = np.array(vals)
                        std = np.std(arr)
                        unique = len(np.unique(arr))
                        
                        if std < 1e-10 or unique <= 1:
                            print(f"  {col}: IC=0 (dead), std={std:.6f}, unique={unique}")
                        else:
                            corr, p = spearmanr(vals, labels)
                            status = "PASS" if abs(corr) >= 0.05 else "FAIL"
                            print(f"  {col}: IC={corr:+.4f}, std={std:.4f}, unique={unique} [{status}]")

except Exception as e:
    print(f"IC analysis skipped: {e}")

db.close()
print("\n=== ANALYSIS COMPLETE ===")
