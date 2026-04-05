#!/usr/bin/env python
"""Heartbeat #213: Full IC analysis with derivatives data"""
import os, sys, sqlite3
import numpy as np
import pandas as pd

DB = 'poly_trader.db'
conn = sqlite3.connect(DB)

# Get table names
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"Tables: {tables}")

# Figure out the raw data table name
raw_table = None
for t in tables:
    if 'raw' in t.lower() or 'market' in t.lower() or 'price' in t.lower():
        raw_table = t
        break

if raw_table:
    raw = pd.read_sql_query(f'SELECT * FROM {raw_table} ORDER BY timestamp DESC LIMIT 1', conn)
    print(f"\n=== Latest Raw Data ({raw_table}) ===")
    if not raw.empty:
        row = raw.iloc[0]
        cols = row.index.tolist()
        print(f"Columns: {cols}")
        btc = row.get('close_price', row.get('btc_price', 'N/A'))
        fng = row.get('fear_greed_index', row.get('fng', 'N/A'))
        fr = row.get('funding_rate', 'N/A')
        print(f"BTC: ${btc} | FNG: {fng} | Funding: {fr}")

# Raw, features, labels counts
raw_count = '-'
feat_count = '-'
label_count = '-'

for t in tables:
    if 'raw' in t.lower() or 'market' in t.lower() or 'price' in t.lower():
        raw_count = pd.read_sql_query(f'SELECT COUNT(*) as n FROM {t}', conn).iloc[0]['n']
        break
    if 'close_prices' in t.lower():
        raw_count = pd.read_sql_query(f'SELECT COUNT(*) as n FROM {t}', conn).iloc[0]['n']
        break

if 'feature_data' in tables:
    feat_count = pd.read_sql_query('SELECT COUNT(*) as n FROM feature_data', conn).iloc[0]['n']
if 'label_data' in tables:
    label_count = pd.read_sql_query('SELECT COUNT(*) as n FROM label_data', conn).iloc[0]['n']

print(f"\n=== Data Counts ===")
print(f"Raw: {raw_count}, Features: {feat_count}, Labels: {label_count}")

# Check derivatives-related tables
deriv_tables = [t for t in tables if any(k in t.lower() for k in ['deriv', 'long_short', 'taker', 'open_interest', 'oi', 'funding'])]
if deriv_tables:
    print(f"\n=== Derivatives Tables ===")
    for dt in deriv_tables:
        try:
            d = pd.read_sql_query(f'SELECT * FROM {dt} ORDER BY timestamp DESC LIMIT 1', conn)
            if not d.empty:
                print(f"{dt}: {dict(d.iloc[0])}")
        except:
            pass
else:
    print("\nNo derivatives tables found")

# Labels analysis  
if 'label_data' in tables:
    labels = pd.read_sql_query('SELECT COUNT(*) as total, '
        'SUM(CASE WHEN sell_win IS NULL THEN 1 ELSE 0 END) as null_count, '
        'SUM(CASE WHEN sell_win IS NOT NULL THEN 1 ELSE 0 END) as non_null, '
        'SUM(CASE WHEN sell_win = 1 THEN 1 ELSE 0 END) as wins '
        'FROM label_data', conn)
    print(f"\n=== Labels ===")
    print(f"Total: {labels.iloc[0]['total']}, NULL: {labels.iloc[0]['null_count']}, Non-null: {labels.iloc[0]['non_null']}, Wins: {labels.iloc[0]['wins']}")

if 'feature_data' in tables and 'label_data' in tables:
    # Try different join columns
    feat_cols = [r[1] for r in conn.execute("PRAGMA table_info(feature_data)").fetchall()]
    label_cols = [r[1] for r in conn.execute("PRAGMA table_info(label_data)").fetchall()]
    print(f"\nFeature columns: {feat_cols[:10]}...")
    print(f"Label columns: {label_cols}")

    join_col = 'timestamp' if 'timestamp' in feat_cols and 'timestamp' in label_cols else 'id'
    if join_col not in feat_cols:
        # Try to find a common column
        for c in feat_cols:
            if c in label_cols:
                join_col = c
                break

    has_sell_win = 'sell_win' in label_cols or 'label_sell_win' in label_cols
    sell_win_col = 'sell_win' if 'sell_win' in label_cols else 'label_sell_win'
    
    if has_sell_win:
        merged = pd.read_sql_query(
            f"SELECT f.*, l.{sell_win_col} as sell_win FROM feature_data f JOIN label_data l ON f.{join_col} = l.{join_col} WHERE l.{sell_win_col} IS NOT NULL", 
            conn)
        clean_n = len(merged)
        print(f"\n=== Clean Data (sell_win IS NOT NULL) ===")
        print(f"Clean records: {clean_n}")

        if clean_n > 0:
            clean_sw = merged['sell_win'].mean()
            print(f"Clean sell_win rate: {clean_sw:.4f}")
            
            # Global sell_win (all labels including NULL as 0)
            all_labels = pd.read_sql_query(f'SELECT {sell_win_col} as sell_win FROM label_data', conn)
            global_sw = all_labels['sell_win'].astype(float).mean()
            print(f"Global sell_win rate (NULL=0): {global_sw:.4f}")
            
            # Clean IC for sensory features
            features_cols = [c for c in merged.columns if c.startswith('feat_')]
            print(f"\n=== Clean IC (h=4, against sell_win, N={clean_n}) ===")
            sensor_results = []
            for col in features_cols:
                vals = pd.to_numeric(merged[col], errors='coerce')
                lbl = merged['sell_win']
                common = vals.dropna().index.intersection(lbl.dropna().index)
                if len(common) >= 100:
                    ic = vals.loc[common].corr(lbl.loc[common])
                    std_val = vals.std()
                    uniq = vals.nunique()
                    status = 'PASS' if abs(ic) >= 0.05 else ('NEAR' if abs(ic) >= 0.04 else 'FAIL')
                    sensor = col.replace('feat_', '')
                    sensor_results.append((sensor, ic, std_val, uniq, status, len(common)))
                    print(f"  {sensor:15s}: IC={ic:+.4f}  std={std_val:.6f}  unique={uniq}  n={len(common)}  [{status}]")
            
            passing = sum(1 for _, ic, _, _, _, _ in sensor_results if abs(ic) >= 0.05)
            print(f"\n全域達標: {passing}/{len(sensor_results)}")
            
            # Recent analysis
            print(f"\n=== Recent Sell Win ===")
            recent_50 = pd.read_sql_query(f'SELECT {sell_win_col} as sell_win FROM label_data ORDER BY timestamp DESC LIMIT 50', conn)
            recent_100 = pd.read_sql_query(f'SELECT {sell_win_col} as sell_win FROM label_data ORDER BY timestamp DESC LIMIT 100', conn)
            recent_500 = pd.read_sql_query(f'SELECT {sell_win_col} as sell_win FROM label_data ORDER BY timestamp DESC LIMIT 500', conn)
            
            r50 = recent_50['sell_win'].astype(float).mean()
            r100 = recent_100['sell_win'].astype(float).mean()
            r500 = recent_500['sell_win'].astype(float).mean()
            
            null_50 = recent_50['sell_win'].isna().sum()
            null_100 = recent_100['sell_win'].isna().sum()
            null_500 = recent_500['sell_win'].isna().sum()
            
            print(f"Last 50:  sell_win={r50:.3f} (NULL: {null_50})")
            print(f"Last 100: sell_win={r100:.3f} (NULL: {null_100})")
            print(f"Last 500: sell_win={r500:.3f} (NULL: {null_500})")

        # CV Model Check
        print(f"\n=== Model Performance ===")
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.model_selection import cross_val_score
            
            sensor_cols = [c for c in merged.columns if c.startswith('feat_')]
            X = merged[sensor_cols].apply(pd.to_numeric, errors='coerce')
            X = X.fillna(X.mean())
            y = merged['sell_win'].astype(float)
            
            if len(X) > 100:
                model = LogisticRegression(max_iter=1000, random_state=42)
                cv_scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
                print(f"CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
                
                model.fit(X, y)
                train_acc = model.score(X, y)
                print(f"Train Accuracy: {train_acc:.4f}")
                print(f"Overfit Gap: {train_acc - cv_scores.mean():+.4f}")
        except Exception as e:
            print(f"Model check failed: {e}")
    else:
        print(f"No sell_win column in labels. Available: {label_cols}")

conn.close()
print("\n=== Analysis Complete ===")
