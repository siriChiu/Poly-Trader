#!/usr/bin/env python3
"""Heartbeat Step 2: Full sensory IC analysis + model CV"""
import sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')
import os
os.chdir('/home/kazuha/Poly-Trader')

import sqlite3
import numpy as np
import json
from datetime import datetime

# Load DB
db = sqlite3.connect('poly_trader.db')

# Get table info
tables = db.execute("SELECT * FROM sqlite_master WHERE type='table'").fetchall()
print("=== DB TABLES ===")
for t in tables:
    cols = db.execute(f'PRAGMA table_info("{t[1]}")').fetchall()
    col_names = [c[1] for c in cols]
    cnt = db.execute(f'SELECT COUNT(*) FROM "{t[1]}"').fetchone()[0]
    print(f"  {t[1]}: {len(col_names)} cols ({col_names[:5]}...), {cnt} rows")
print()

# Find raw/features/labels tables
raw_table = None; feat_table = None; label_table = None
for t in tables:
    name = t[1].lower()
    if 'raw' in name or 'market' in name:
        raw_table = t[1]
    if 'feature' in name or 'norm' in name:
        feat_table = t[1]
    if 'label' in name:
        label_table = t[1]

print(f"Identified - raw:{raw_table}, features:{feat_table}, labels:{label_table}")

# Get counts
raw_count = db.execute(f'SELECT COUNT(*) FROM "{raw_table}"').fetchone()[0] if raw_table else 0
feat_count = db.execute(f'SELECT COUNT(*) FROM "{feat_table}"').fetchone()[0] if feat_table else 0
label_count = db.execute(f'SELECT COUNT(*) FROM "{label_table}"').fetchone()[0] if label_table else 0
print(f"Counts: raw={raw_count}, features={feat_count}, labels={label_count}")

# Get feature columns
if feat_table:
    feat_cols = [c[1] for c in db.execute(f'PRAGMA table_info("{feat_table}")').fetchall()]
    # Get label columns
    if label_table:
        label_cols = [c[1] for c in db.execute(f'PRAGMA table_info("{label_table}")').fetchall()]
    
    # Join features and labels
    # Find common key
    print(f"\nFeature cols: {feat_cols}")
    print(f"Label cols: {label_cols}")
    
    # Find common columns for joining
    common = [c for c in feat_cols if c in label_cols and c != 'rowid']
    print(f"Join keys: {common}")
    
    if common:
        key = common[0]
        query = f'''SELECT f.*, l.* FROM "{feat_table}" f 
                    INNER JOIN "{label_table}" l ON f.{key} = l.{key}'''
    else:
        # Maybe same row count, use index
        query = f'''SELECT * FROM "{feat_table}" f 
                    INNER JOIN "{label_table}" l ON f.rowid = l.rowid'''
    
    import pandas as pd
    df = pd.read_sql_query(query, db)
    print(f"\nMerged dataset: {len(df)} rows, {len(df.columns)} cols")
    
    # Find sell_win column
    sell_win_col = None
    for c in df.columns:
        if 'sell_win' in c.lower() or 'sell' in c.lower() or 'label' in c.lower():
            sell_win_col = c
            break
    if sell_win_col is None:
        # Check label table for target columns
        for c in label_cols:
            if c not in feat_cols:
                print(f"  Label-only col: {c}")
    
    # Try to find binary label columns
    for c in df.columns:
        if c in feat_cols:
            continue
        vals = df[c].dropna().values
        vals_unique = sorted(set(vals))
        if len(vals_unique) <= 5:
            print(f"  Label col '{c}': values={list(vals_unique)[:10]}")

    # Try various label column names
    for candidate in ['sell_win', 'label_spot_long_win', 'sell', 'target', 'label', 'future_return_pct', 'label_class']:
        if candidate in df.columns:
            y_col = candidate
            y = df[candidate].astype(float)
            print(f"\nUsing label column: {y_col}, positive rate: {y.mean()*100:.1f}%")
            break
    else:
        # Find the first non-feature column that's numeric
        for c in df.columns:
            if c not in feat_cols:
                y_col = c
                y = df[c].astype(float) 
                print(f"\nUsing label column: {y_col}, positive rate: {y.mean()*100:.1f}%")
                break
    
    # BTC price from features
    btc_col = None
    for c in ['close', 'btc_close', 'price', 'btc_price']:
        if c in df.columns:
            btc_col = c
            break
    
    btc_now = df[btc_col].iloc[-1] if btc_col else None
    
    # === IC Analysis ===
    SENSE_MAP = {
        'Eye': 'eye_signal',
        'Ear': 'ear_signal',
        'Nose': 'nose_signal',
        'Tongue': 'tongue_signal',
        'Body': 'body_signal',
        'Pulse': 'pulse_signal',
        'Aura': 'aura_signal',
        'Mind': 'mind_signal',
    }
    
    y_centered = y - y.mean()
    
    print("\n=== FULL IC (against sell_win) ===")
    passing_full = 0
    full_ics = {}
    for sense, col in SENSE_MAP.items():
        if col in df.columns:
            x = df[col].astype(float)
            std_x = x.std()
            unique_n = x.nunique()
            if std_x > 0 and len(x) > 2:
                ic = np.corrcoef(x, y_centered)[0, 1]
            else:
                ic = 0.0
            full_ics[sense] = ic
            status = "✅" if abs(ic) >= 0.05 else "❌"
            if abs(ic) >= 0.05: passing_full += 1
            print(f"  {sense:8s}: {ic:+.4f} {status}  (std={std_x:.4f}, unique={unique_n})")
        else:
            full_ics[sense] = None
            print(f"  {sense:8s}: N/A (col '{col}' not found)")
    print(f"\n  Passing: {passing_full}/8 (threshold |IC| >= 0.05)")
    
    # === Regime-Aware IC ===
    # Sort by price to get bear/chop/bull
    if btc_col:
        sorted_df = df.sort_values(by=btc_col)
    else:
        sorted_df = df.copy()
    n = len(sorted_df)
    third = n // 3
    bear = sorted_df.iloc[:third]
    chop = sorted_df.iloc[third:2*third]
    bull = sorted_df.iloc[2*third:]
    
    print(f"\n=== REGIME-AWARE IC (tercile split) ===")
    bear_pass = bull_pass = chop_pass = 0
    regime_ics = {}
    for sense, col in SENSE_MAP.items():
        if col not in df.columns: continue
        ics = {}
        for name, subset in [('Bear', bear), ('Bull', bull), ('Chop', chop)]:
            y_s = subset.iloc[0].name  # Use index
            y_sub = subset[y_col].astype(float)
            y_c = y_sub - y_sub.mean()
            x_sub = subset[col].astype(float)
            if x_sub.std() > 0 and len(x_sub) > 2:
                ic = np.corrcoef(x_sub, y_c)[0, 1]
            else:
                ic = 0.0
            ics[name] = ic
            if abs(ic) >= 0.05:
                if name == 'Bear': bear_pass += 1
                elif name == 'Bull': bull_pass += 1
                else: chop_pass += 1
        regime_ics[sense] = ics
        bm = "✅" if abs(ics['Bear']) >= 0.05 else "❌"
        um = "✅" if abs(ics['Bull']) >= 0.05 else "❌"
        cm = "✅" if abs(ics['Chop']) >= 0.05 else "❌"
        print(f"  {sense:8s}: Bear {ics['Bear']:+.4f} {bm} | Bull {ics['Bull']:+.4f} {um} | Chop {ics['Chop']:+.4f} {cm}")
    print(f"\n  Regime passing: Bear={bear_pass}/8, Bull={bull_pass}/8, Chop={chop_pass}/8")
    
    # === Dynamic Window IC ===
    print(f"\n=== DYNAMIC WINDOW IC ===")
    for w in [500, 1000, 2000, 3000, 5000]:
        recent = df.tail(w)
        if len(recent) < 3: continue
        y_w = recent[y_col].astype(float)
        y_cw = y_w - y_w.mean()
        pw = 0
        ics_w = {}
        for sense, col in SENSE_MAP.items():
            if col not in recent.columns: continue
            x_w = recent[col].astype(float)
            if x_w.std() > 0:
                ic = np.corrcoef(x_w, y_cw)[0, 1]
            else:
                ic = 0.0
            ics_w[sense] = ic
            if abs(ic) >= 0.05: pw += 1
        print(f"  N={w}: {pw}/8 passing")
    
    # === Model CV ===
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import accuracy_score
    
    sense_cols = [c for c in SENSE_MAP.values() if c in df.columns]
    X = df[sense_cols].fillna(0)
    y_cv = df[y_col].astype(float)
    y_bin = (y_cv > 0.5).astype(int) if y_cv.max() <= 1.0 else y_cv
    
    print(f"\n=== MODEL CV ===")
    print(f"  X shape: {X.shape}, y classes: {y_bin.value_counts().to_dict()}")
    
    lr = LogisticRegression(max_iter=1000, random_state=42)
    cv_acc = cross_val_score(lr, X, y_bin, cv=5, scoring='accuracy')
    print(f"  LR CV: {cv_acc.mean()*100:.1f}% ± {cv_acc.std()*100:.1f}%")
    
    # IC-weighted fusion
    weights = []
    for col in sense_cols:
        x = df[col].astype(float)
        if x.std() > 0:
            ic = abs(np.corrcoef(x, y_centered)[0, 1])
        else:
            ic = 0.0
        weights.append(max(ic, 0.001))
    weights = np.array(weights)
    weights = weights / weights.sum()
    
    if len(sense_cols) > 1:
        fused = (df[sense_cols].fillna(0).values * weights).sum(axis=1)
        threshold = np.median(fused)
        preds = (fused > threshold).astype(float)
        ic_fusion_acc = accuracy_score(y_bin, preds)
        print(f"  IC-Fusion CV: {ic_fusion_acc*100:.1f}%")
    
    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'raw_count': raw_count,
        'feat_count': feat_count,
        'label_count': label_count,
        'label_pos': int(y_bin.sum()),
        'label_neg': int(len(y_bin) - y_bin.sum()),
        'btc_price': float(btc_now) if btc_now else None,
        'full_ics': full_ics,
        'regime_ics': {s: {k: float(v) for k,v in d.items()} for s,d in regime_ics.items()},
        'regime_passing': {'bear': bear_pass, 'bull': bull_pass, 'chop': chop_pass},
        'lr_cv': float(cv_acc.mean()),
    }
    with open('data/hb168_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to data/hb168_results.json")

db.close()
