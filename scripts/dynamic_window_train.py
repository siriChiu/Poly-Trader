#!/usr/bin/env python3
"""Dynamic Window training — scans N=100..5000, computes IC at each window."""
import json, os, sys
import numpy as np

sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

try:
    import sqlite3
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'

CORE_FEATURES = [
    'feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue',
    'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind',
]

def analyze_window(data_window):
    """Return dict of ic per feature for a given window."""
    ics = {}
    for col in CORE_FEATURES:
        vals = [r[col] for r in data_window if r[col] is not None]
        labs = [r['label_sell_win'] for r in data_window if r[col] is not None]
        if len(vals) < 20:
            ics[col] = 0.0
            continue
        if HAS_SCIPY:
            ic, _ = stats.spearmanr(vals, labs)
        else:
            ic = np.corrcoef(vals, labs)[0, 1]
        ics[col] = round(float(ic), 4)
    return ics

def main():
    conn = sqlite3.connect(DB_PATH)
    
    feat_query = f"""SELECT f.{', f.'.join(CORE_FEATURES)}, f.timestamp, f.symbol
                     FROM features_normalized f ORDER BY f.timestamp"""
    feat_df = conn.execute(feat_query)
    feat_names = [d[0] for d in feat_df.description]
    feat_rows = feat_df.fetchall()
    
    label_query = """SELECT timestamp, symbol, label_sell_win FROM labels WHERE label_sell_win IS NOT NULL"""
    label_rows = conn.execute(label_query).fetchall()
    label_map = {(r[0], r[1]): r[2] for r in label_rows}
    
    matched = []
    for row in feat_rows:
        row_dict = dict(zip(feat_names, row))
        key = (row_dict['timestamp'], row_dict['symbol'])
        if key in label_map:
            row_dict['label_sell_win'] = label_map[key]
            matched.append(row_dict)
    
    if not matched:
        print("ERROR: No matches!")
        return
    
    total_n = len(matched)
    print(f"Dynamic Window Analysis — total n={total_n}")
    print("=" * 70)
    
    windows = [100, 200, 400, 600, 1000, 2000, 5000]
    best_pass = -1
    best_n = None
    best_ics = None
    results = {}
    
    for N in windows:
        if N > total_n:
            continue
        window = matched[-N:]  # Last N samples (most recent)
        ics = analyze_window(window)
        passed = sum(1 for v in ics.values() if abs(v) >= 0.05)
        results[N] = ics
        
        best_feats = {k: v for k, v in ics.items() if abs(v) >= 0.05}
        print(f"\nN={N:>5d}: {passed}/{len(CORE_FEATURES)} passed")
        for feat in CORE_FEATURES:
            short = feat.replace('feat_', '')
            ic = ics.get(feat, 0)
            status = "✅" if abs(ic) >= 0.05 else "❌"
            print(f"  {short:8s}: IC={ic:+.4f} {status}")
        
        if passed > best_pass:
            best_pass = passed
            best_n = N
            best_ics = ics
    
    print(f"\n{'='*70}")
    if best_n is not None:
        print(f"Best window: N={best_n} ({best_pass}/{len(CORE_FEATURES)} passing)")
    
    results['best_n'] = best_n
    results['best_pass'] = best_pass
    results['total_n'] = total_n
    
    # Save
    os.makedirs('/home/kazuha/Poly-Trader/data', exist_ok=True)
    with open('/home/kazuha/Poly-Trader/data/dw_result.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Saved to data/dw_result.json")

if __name__ == '__main__':
    main()
