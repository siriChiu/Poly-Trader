#!/usr/bin/env python3
"""Heartbeat #202 - Full IC analysis and 3-feature LR CV."""
import sqlite3, json, os
import numpy as np
from datetime import datetime

db_path = os.path.join('/home/kazuha/Poly-Trader', 'poly_trader.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# ── Data Counts ──
cur.execute('SELECT COUNT(*) FROM raw_market_data')
raw_count = cur.fetchone()[0]
cur.execute('SELECT timestamp, close_price FROM raw_market_data ORDER BY rowid DESC LIMIT 1')
raw_latest = cur.fetchone()

cur.execute('SELECT COUNT(*) FROM features_normalized')
feat_count = cur.fetchone()[0]
cur.execute('SELECT MAX(timestamp) FROM features_normalized')
feat_latest = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM labels')
label_count = cur.fetchone()[0]
cur.execute('SELECT MAX(timestamp) FROM labels')
label_latest = cur.fetchone()[0]

# sell_win stats
cur.execute('SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM labels WHERE label_sell_win IS NOT NULL')
global_sell_win = cur.fetchone()[0]

cur.execute('SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM (SELECT label_sell_win FROM labels WHERE label_sell_win IS NOT NULL ORDER BY rowid DESC LIMIT 50)')
recent_50 = cur.fetchone()[0]

cur.execute('SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM (SELECT label_sell_win FROM labels WHERE label_sell_win IS NOT NULL ORDER BY rowid DESC LIMIT 100)')
recent_100 = cur.fetchone()[0]

cur.execute('SELECT AVG(CAST(label_sell_win AS FLOAT)) FROM (SELECT label_sell_win FROM labels WHERE label_sell_win IS NOT NULL ORDER BY rowid DESC LIMIT 500)')
recent_500 = cur.fetchone()[0]

# Regime sell_win
cur.execute('''SELECT regime_label, AVG(CAST(label_sell_win AS FLOAT)), COUNT(*) 
               FROM labels WHERE label_sell_win IS NOT NULL AND regime_label IS NOT NULL GROUP BY regime_label''')
regime_stats = cur.fetchall()

# VIX/DXY from raw market data
cur.execute('SELECT vix_value, dxy_value, fear_greed_index FROM raw_market_data WHERE vix_value IS NOT NULL ORDER BY rowid DESC LIMIT 1')
vix_dxy = cur.fetchone()

# Label horizon
cur.execute('SELECT DISTINCT horizon_minutes FROM labels ORDER BY horizon_minutes LIMIT 5')
horizons = cur.fetchall()

print(f"=== Data Snapshot [2026-04-05 03:25 UTC] ===")
print(f"Raw: {raw_count} (latest: {raw_latest[0]}, close: ${raw_latest[1]})")
print(f"Features: {feat_count} (latest: {feat_latest})")
print(f"Labels: {label_count} (latest: {label_latest})")
print(f"Label horizon(s): {horizons}")
print(f"Global sell_win: {global_sell_win:.4f}" if global_sell_win else "Global sell_win: N/A")
print(f"Recent sell_win: 50={recent_50:.4f}, 100={recent_100:.4f}, 500={recent_500:.4f}")
print(f"Regimes: {[(r, f'{w:.4f}', c) for r, w, c in regime_stats]}")
print(f"VIX={vix_dxy[0]}, DXY={vix_dxy[1]}, FNG={vix_dxy[2]}" if vix_dxy else "VIX/DXY/FNG: N/A")

# ── Feature IC Analysis (join features + labels on timestamp+symbol) ──
# Feature col names in features_normalized
cur.execute("PRAGMA table_info(features_normalized)")
all_feat_cols = [r[1] for r in cur.fetchall()]
feat_sensor_cols = [c for c in all_feat_cols if c.startswith('feat_') and c not in ('feature_version',)]

print(f"\nFeature sensor columns: {feat_sensor_cols}")

# Join: match features to labels by timestamp AND symbol
query_cols = ['f.timestamp', 'f.regime_label'] + [f'f.{c}' for c in feat_sensor_cols] + ['l.label_sell_win']
join_query = f'''
    SELECT {', '.join(query_cols)}
    FROM features_normalized f
    INNER JOIN labels l ON f.timestamp = l.timestamp 
        AND (f.symbol = l.symbol OR f.symbol = l.symbol OR 1=1)
    WHERE l.label_sell_win IS NOT NULL
    ORDER BY f.timestamp
'''

# Try inner join with most specific first
try:
    cur.execute(f'''
        SELECT f.timestamp, f.symbol, f.regime_label, {', '.join(f'f.{c}' for c in feat_sensor_cols)}, l.label_sell_win
        FROM features_normalized f
        INNER JOIN labels l ON f.timestamp = l.timestamp AND f.symbol = l.symbol
        WHERE l.label_sell_win IS NOT NULL
        ORDER BY f.timestamp
    ''')
    rows = cur.fetchall()
    print(f"Strict join (ts+symbol): {len(rows)} rows")
except:
    rows = []

if len(rows) < 100:
    # Fallback: join on timestamp only (assume matching by position/latest)
    # Get features and labels separately, join by matching timestamps
    cur.execute(f'''
        SELECT timestamp, symbol, regime_label, {', '.join(feat_sensor_cols)}
        FROM features_normalized
        ORDER BY timestamp
    ''')
    feat_rows = cur.fetchall()
    
    cur.execute('''
        SELECT timestamp, label_sell_win, regime_label
        FROM labels
        WHERE label_sell_win IS NOT NULL
        ORDER BY timestamp
    ''')
    label_rows = cur.fetchall()
    
    feat_ts_set = {r[0]: i for i, r in enumerate(feat_rows)}
    
    joined_rows = []
    for lr in label_rows:
        ts = lr[0]
        if ts in feat_ts_set:
            fi = feat_ts_set[ts]
            fr = feat_rows[fi]
            # fr: timestamp, symbol, regime_label, features...
            joined_rows.append((lr[0], fr[2],) + fr[3:] + (lr[1], lr[2]))
    
    rows = joined_rows
    print(f"Timestamp-only join: {len(rows)} rows")

if len(rows) < 100:
    # Last resort: positional join
    cur.execute(f'''
        SELECT timestamp, regime_label, {', '.join(feat_sensor_cols)}
        FROM features_normalized
        ORDER BY timestamp
    ''')
    feat_rows = cur.fetchall()
    
    cur.execute('''
        SELECT timestamp, label_sell_win
        FROM labels
        WHERE label_sell_win IS NOT NULL
        ORDER BY timestamp
    ''')
    label_rows = cur.fetchall()
    
    min_len = min(len(feat_rows), len(label_rows))
    joined_rows = []
    for i in range(min_len):
        fr = feat_rows[i]
        lr = label_rows[i - (len(label_rows) - min_len)]
        row = (fr[0], fr[1]) + fr[2:] + (lr[1],)
        joined_rows.append(row)
    rows = joined_rows
    print(f"Positional join: {len(rows)} rows")

# Calculate ICs
if rows:
    # Map column indices: timestamp=0, regime=1, feat_cols=2..(n+1), label=n+2
    
    # 1. Global IC against label_sell_win
    sell_win = np.array([r[-1] for r in rows], dtype=float)
    valid_mask = ~np.isnan(sell_win)
    
    print(f"\n=== Global IC (N={valid_mask.sum()}) ===")
    global_ics = {}
    offset = 3  # timestamp=0, symbol=1, regime=2
    for i, col in enumerate(feat_sensor_cols):
        vals = np.array([r[i+offset] for r in rows], dtype=float)
        finite_mask = np.isfinite(vals) & valid_mask
        n = finite_mask.sum()
        if n < 50:
            global_ics[col] = {'ic': 0.0, 'std': 0.0, 'status': 'DEAD', 'n': int(n)}
            continue
        v = vals[finite_mask]
        w = sell_win[finite_mask]
        std_val = np.std(v)
        unique_count = len(np.unique(v[:1000]))  # sample for speed
        if std_val < 1e-10:
            global_ics[col] = {'ic': 0.0, 'std': round(std_val, 6), 'status': 'DEAD', 'n': int(n)}
            continue
        ic = np.corrcoef(v, w)[0, 1]
        status = 'PASS' if abs(ic) >= 0.05 else 'FAIL'
        global_ics[col] = {'ic': round(float(ic), 4), 'std': round(float(std_val), 4), 'status': status, 'n': int(n)}
        marker = '✅' if status == 'PASS' else '⚠️' if abs(ic) >= 0.04 else ''
        print(f"  {col:20s}: IC={ic:+.4f}  std={std_val:.4f}  {status}  {marker}")
    
    pass_count = sum(1 for v in global_ics.values() if v['status'] == 'PASS')
    active = sum(1 for v in global_ics.values() if v['status'] != 'DEAD')
    print(f"\nGlobal: {pass_count}/{active} features PASS (threshold: |IC| >= 0.05)")
    
    # 2. Regime IC
    print(f"\n=== Regime IC ===")
    regime_ics = {}
    for regime in ['BULLISH', 'BEARISH', 'CHOPPY', 'NEUTRAL', 'bull', 'bear', 'chop', 'neutral']:
        subset = [r for r in rows if r[1] and str(r[1]).upper() == regime.upper()]
        if len(subset) < 30:
            continue
        subset_sell = np.array([r[-1] for r in subset], dtype=float)
        subset_fin = ~np.isnan(subset_sell)
        
        rics = {}
        passed = 0
        for i, col in enumerate(feat_sensor_cols):
            vals = np.array([r[i+offset] for r in subset], dtype=float)
            finite = np.isfinite(vals) & subset_fin
            if finite.sum() < 30:
                continue
            v = vals[finite]
            w = subset_sell[finite]
            s = np.std(v)
            if s < 1e-10:
                continue
            ic = np.corrcoef(v, w)[0, 1]
            status = 'PASS' if abs(ic) >= 0.05 else 'FAIL'
            if status == 'PASS':
                passed += 1
            rics[col] = {'ic': round(float(ic), 4), 'status': status}
        
        regime_sell_win = subset_sell[subset_fin].mean() if subset_fin.sum() > 0 else None
        regime_ics[regime] = {'count': len(subset), 'sell_win': round(float(regime_sell_win), 4) if regime_sell_win is not None else None, 'passed': passed, 'total': len(rics), 'ics': rics}
        print(f"  {regime}: {passed}/{len(rics)} pass, sell_win={regime_sell_win:.4f}" if regime_sell_win is not None else f"  {regime}: n/a")
    
    # 3. 3-feature LR Cross-Validation
    print(f"\n=== 3-Feature LR CV ===")
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.metrics import accuracy_score
        
        # Pick top 3 features by |IC|
        sorted_feats = sorted(global_ics.items(), key=lambda x: abs(x[1]['ic']), reverse=True)
        top3 = [f for f, v in sorted_feats[:3] if v['status'] != 'DEAD']
        
        # Build feature matrix
        X = []
        y = []
        for r in rows:
            label_val = r[-1]
            if np.isnan(label_val):
                continue
            feat_vals = []
            valid_row = True
            for i, col in enumerate(feat_sensor_cols):
                if col in top3:
                    v = r[i+offset]
                    if not np.isfinite(v):
                        valid_row = False
                        break
                    feat_vals.append(v)
            if valid_row and len(feat_vals) == len(top3):
                X.append(feat_vals)
                y.append(int(label_val))
        
        X = np.array(X)
        y = np.array(y)
        
        # Drop DEAD features (std~0)
        good_mask = np.std(X, axis=0) > 1e-10
        X = X[:, good_mask]
        top3_filtered = [f for f, g in zip(top3, good_mask) if g]
        
        print(f"  Features: {top3_filtered}")
        print(f"  Shape: {X.shape}")
        
        cv = TimeSeriesSplit(n_splits=5)
        cv_scores = []
        for train_idx, test_idx in cv.split(X):
            model = LogisticRegression(max_iter=1000, random_state=42)
            model.fit(X[train_idx], y[train_idx])
            pred = model.predict(X[test_idx])
            score = accuracy_score(y[test_idx], pred)
            cv_scores.append(score)
        
        # Train accuracy
        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X, y)
        train_acc = accuracy_score(y, model.predict(X))
        
        print(f"  CV Accuracy: {np.mean(cv_scores):.4f} ± {np.std(cv_scores):.4f}")
        print(f"  CV scores: {[f'{s:.4f}' for s in cv_scores]}")
        print(f"  Train accuracy: {train_acc:.4f}")
        print(f"  Overfit gap: {train_acc - np.mean(cv_scores):.4f}")
        print(f"  Coefficients: {dict(zip(top3_filtered, [round(c, 4) for c in model.coef_[0]]))}")
        
        lr_result = {
            'features': top3_filtered,
            'cv_accuracy': round(float(np.mean(cv_scores)), 4),
            'cv_std': round(float(np.std(cv_scores)), 4),
            'cv_scores': [round(float(s), 4) for s in cv_scores],
            'train_accuracy': round(float(train_acc), 4),
            'overfit_gap': round(float(train_acc - np.mean(cv_scores)), 4),
            'coefficients': {f: round(float(c), 4) for f, c in zip(top3_filtered, model.coef_[0])}
        }
    except ImportError:
        print("  sklearn not available")
        lr_result = None
    except Exception as e:
        print(f"  Error: {e}")
        lr_result = None
    
    # Output structured data for ISSUES.md
    output = {
        'data_summary': {
            'raw': raw_count,
            'features': feat_count,
            'labels': label_count,
            'raw_latest': raw_latest[0],
            'features_latest': feat_latest,
            'labels_latest': label_latest,
            'btc_close': raw_latest[1] if raw_latest else None,
            'vix': vix_dxy[0] if vix_dxy else None,
            'dxy': vix_dxy[1] if vix_dxy else None,
            'fng': vix_dxy[2] if vix_dxy else None,
        },
        'sell_win': {
            'global': round(float(global_sell_win), 4) if global_sell_win else None,
            'recent_50': round(float(recent_50), 4) if recent_50 else None,
            'recent_100': round(float(recent_100), 4) if recent_100 else None,
            'recent_500': round(float(recent_500), 4) if recent_500 else None,
            'regimes': {r: {'win_rate': round(float(w), 4), 'count': c} for r, w, c in regime_stats}
        },
        'global_ics': global_ics,
        'regime_ics': regime_ics,
        'three_feature_lr': lr_result,
    }
    
    out_path = '/home/kazuha/Poly-Trader/data/ic_heartbeat_202.json'
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n=== Results saved to {out_path} ===")

conn.close()
