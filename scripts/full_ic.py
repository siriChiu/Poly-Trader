#!/usr/bin/env python3
"""Full IC analysis — v5. Global IC, TW-IC (tau=200), extended 15 TI features."""
import json, os, sys
import numpy as np

sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

try:
    import sqlite3
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    print("scipy not available, using numpy correlation")
    HAS_SCIPY = False

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    
    # Load features
    feat_cols = [
        'feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue',
        'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind',
        'feat_vix', 'feat_dxy',
        'feat_rsi14', 'feat_macd_hist', 'feat_atr_pct',
        'feat_vwap_dev', 'feat_bb_pct_b',
        # 4H Timeframe Features (低雜訊大方向)
        'feat_4h_bias50', 'feat_4h_bias20',
        'feat_4h_rsi14', 'feat_4h_macd_hist', 'feat_4h_bb_pct_b',
        'feat_4h_ma_order', 'feat_4h_dist_swing_low',
    ]
    col_str = ', '.join([f'f.{c}' for c in feat_cols] + ['f.timestamp', 'f.symbol', 'f.regime_label'])
    
    feat_query = f"SELECT {col_str} FROM features_normalized f ORDER BY f.timestamp"
    feat_df = conn.execute(feat_query)
    feat_names = [d[0] for d in feat_df.description]
    feat_rows = feat_df.fetchall()
    
    # Load labels
    label_query = """SELECT timestamp, symbol, label_spot_long_win, regime_label
                     FROM labels WHERE label_spot_long_win IS NOT NULL"""
    label_rows = conn.execute(label_query).fetchall()
    label_map = {(r[0], r[1]): r[2] for r in label_rows}
    
    # Join on timestamp + symbol
    matched = []
    for row in feat_rows:
        row_dict = dict(zip(feat_names, row))
        key = (row_dict['timestamp'], row_dict['symbol'])
        if key in label_map:
            row_dict['label_spot_long_win'] = label_map[key]
            matched.append(row_dict)
    
    if not matched:
        print("ERROR: No matches between features and labels!")
        return
    
    n = len(matched)
    print(f"Full IC Analysis (v5) — n={n}")
    print("=" * 70)
    
    # Global IC (Spearman)
    print(f"\n=== Global IC (Spearman, n={n}) ===")
    global_ics = {}
    for col in feat_cols:
        vals = [r[col] for r in matched if r[col] is not None and r['label_spot_long_win'] is not None]
        labs = [r['label_spot_long_win'] for r in matched if r[col] is not None and r['label_spot_long_win'] is not None]
        if len(vals) < 50:
            print(f"  {col:20s}: SKIP (n={len(vals)})")
            global_ics[col] = 0.0
            continue
        if HAS_SCIPY:
            ic, _ = stats.spearmanr(vals, labs)
        else:
            ic = np.corrcoef(vals, labs)[0, 1]
        status = "✅ PASS" if abs(ic) >= 0.05 else "❌ FAIL"
        print(f"  {col:20s}: IC={ic:+.4f} {status}")
        global_ics[col] = round(float(ic), 4)
    
    global_pass = sum(1 for v in global_ics.values() if abs(v) >= 0.05)
    print(f"\nGlobal IC: {global_pass}/{len(feat_cols)} passing")
    
    # Time-Weighted IC (tau=200)
    print(f"\n=== Time-Weighted IC (tau=200, n={n}) ===")
    tw_ics = {}
    tau = 200
    for col in feat_cols:
        valid_pairs = [(r[col], r['label_spot_long_win']) for r in matched
                       if r[col] is not None and r['label_spot_long_win'] is not None]
        if len(valid_pairs) < 50:
            tw_ics[col] = 0.0
            continue
        
        vals = [p[0] for p in valid_pairs]
        labs = [p[1] for p in valid_pairs]
        
        # Exponential decay weights (recent = higher weight)
        w = np.array([np.exp(-(len(vals) - 1 - i) / tau) for i in range(len(vals))])
        
        # Weighted Spearman approximation via weighted Pearson
        vals = np.array(vals, dtype=float)
        labs = np.array(labs, dtype=float)
        
        if HAS_SCIPY:
            # Use Pearson on rank-transformed data as approximation
            vals_rank = stats.rankdata(vals)
            labs_rank = stats.rankdata(labs)
            
            # Weighted mean
            w_sum = w.sum()
            vals_wmean = np.sum(w * vals_rank) / w_sum
            labs_wmean = np.sum(w * labs_rank) / w_sum
            
            # Weighted covariance
            cov = np.sum(w * (vals_rank - vals_wmean) * (labs_rank - labs_wmean))
            std_v = np.sqrt(np.sum(w * (vals_rank - vals_wmean) ** 2))
            std_l = np.sqrt(np.sum(w * (labs_rank - labs_wmean) ** 2))
            
            if std_v * std_l > 0:
                ic = float(cov / (std_v * std_l))
            else:
                ic = 0.0
        else:
            ic = float(np.corrcoef(vals, labs)[0, 1])
        
        tw_ics[col] = round(float(ic), 4)
        status = "✅ PASS" if abs(ic) >= 0.05 else "❌ FAIL"
        print(f"  {col:20s}: TW-IC={ic:+.4f} {status}")
    
    tw_pass = sum(1 for v in tw_ics.values() if abs(v) >= 0.05)
    print(f"\nTW-IC: {tw_pass}/{len(feat_cols)} passing")
    
    # Save results
    result = {
        'n': n,
        'global_ics': global_ics,
        'tw_ics': tw_ics,
        'global_pass': global_pass,
        'tw_pass': tw_pass,
        'total_features': len(feat_cols),
    }
    
    os.makedirs('/home/kazuha/Poly-Trader/data', exist_ok=True)
    with open('/home/kazuha/Poly-Trader/data/full_ic_result.json', 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to data/full_ic_result.json")
    
    # Also update ic_signs.json for model train pipeline
    ic_signs = {fc: global_ics.get(fc, 0.0) for fc in feat_cols}
    ic_signs['tw_ics'] = tw_ics
    ic_signs['n'] = n
    ic_signs['global_pass'] = global_pass
    ic_signs['tw_pass'] = tw_pass
    
    with open('/home/kazuha/Poly-Trader/model/ic_signs.json', 'w') as f:
        json.dump(ic_signs, f, indent=2)
    print("Saved to model/ic_signs.json")
    
    return result

if __name__ == '__main__':
    main()
