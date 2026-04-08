#!/usr/bin/env python3
"""Regime-aware IC analysis — splits data by bear/bull/chop using Mind tertiles."""
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

def main():
    conn = sqlite3.connect(DB_PATH)
    
    # Load features + labels via JOIN
    feat_query = f"""SELECT f.{', f.'.join(CORE_FEATURES)}, f.timestamp, f.symbol, f.regime_label
                     FROM features_normalized f ORDER BY f.timestamp"""
    feat_df = conn.execute(feat_query)
    feat_names = [d[0] for d in feat_df.description]
    feat_rows = feat_df.fetchall()
    
    label_query = """SELECT timestamp, symbol, label_spot_long_win, regime_label
                     FROM labels WHERE label_spot_long_win IS NOT NULL"""
    label_rows = conn.execute(label_query).fetchall()
    label_map = {(r[0], r[1]): {'label_spot_long_win': r[2], 'regime_label': r[3]} for r in label_rows}
    
    matched = []
    for row in feat_rows:
        row_dict = dict(zip(feat_names, row))
        key = (row_dict['timestamp'], row_dict['symbol'])
        if key in label_map:
            row_dict['label_spot_long_win'] = label_map[key]['label_spot_long_win']
            row_dict['label_regime'] = label_map[key]['regime_label']
            matched.append(row_dict)
    
    if not matched:
        print("ERROR: No matches!")
        return
    
    n = len(matched)
    print(f"Regime-Aware IC Analysis — n={n}")
    print("=" * 70)
    
    # Determine regime using Mind tertiles (as per skill doc pattern)
    mind_vals = np.array([r['feat_mind'] for r in matched if r['feat_mind'] is not None])
    if len(mind_vals) > 100:
        p33, p67 = float(np.percentile(mind_vals, 33)), float(np.percentile(mind_vals, 67))
        for r in matched:
            if r['feat_mind'] is not None:
                if r['feat_mind'] < p33:
                    r['regime'] = 'bear'
                elif r['feat_mind'] > p67:
                    r['regime'] = 'bull'
                else:
                    r['regime'] = 'chop'
            else:
                r['regime'] = 'neutral'
    else:
        for r in matched:
            r['regime'] = 'neutral'
    
    # Also count DB regime_label
    regime_counts = {}
    for r in matched:
        regime_counts[r['regime']] = regime_counts.get(r['regime'], 0) + 1
    print(f"Regime distribution (Mind tertiles): {regime_counts}")
    
    # Compute IC per regime
    regimes = ['bear', 'bull', 'chop', 'neutral']
    result = {}
    for regime in regimes:
        subset = [r for r in matched if r['regime'] == regime]
        if len(subset) < 20:
            print(f"\n{regime.upper()}: n={len(subset)} (too small)")
            result[regime] = {'n': len(subset), 'ics': {}}
            continue
        
        print(f"\n{regime.upper()} (n={len(subset)})")
        ics = {}
        for col in CORE_FEATURES:
            vals = [r[col] for r in subset if r[col] is not None]
            labs = [r['label_spot_long_win'] for r in subset if r[col] is not None]
            if len(vals) < 20:
                ics[col] = 0.0
                continue
            if HAS_SCIPY:
                ic, _ = stats.spearmanr(vals, labs)
            else:
                ic = np.corrcoef(vals, labs)[0, 1]
            ics[col] = round(float(ic), 4)
        
        passed = sum(1 for v in ics.values() if abs(v) >= 0.05)
        result[regime] = {'n': len(subset), 'ics': ics, 'passed': passed}
        
        for col in CORE_FEATURES:
            short = col.replace('feat_', '')
            ic = ics.get(col, 0)
            status = "✅" if abs(ic) >= 0.05 else "❌"
            print(f"  {short:8s}: IC={ic:+.4f} {status}")
        print(f"  → {passed}/{len(CORE_FEATURES)} passing")
    
    # Sell win by regime
    print(f"\n=== Sell Win Rate by Regime ===")
    for regime in regimes:
        subset = [r for r in matched if r['regime'] == regime]
        if len(subset) > 0:
            win_count = sum(1 for r in subset if r['label_spot_long_win'] == 1)
            rate = win_count / len(subset)
            print(f"  {regime:8s}: sell_win={rate:.4f} (n={len(subset)})")
    
    # Overall sell_win
    all_wins = sum(1 for r in matched if r['label_spot_long_win'] == 1)
    overall = all_wins / len(matched)
    print(f"\nOverall: sell_win={overall:.4f} (n={len(matched)})")
    
    result['overall_sell_win'] = round(overall, 4)
    result['overall_n'] = len(matched)
    
    os.makedirs('/home/kazuha/Poly-Trader/data', exist_ok=True)
    with open('/home/kazuha/Poly-Trader/data/ic_regime_analysis.json', 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nSaved to data/ic_regime_analysis.json")
    
    return result

if __name__ == '__main__':
    main()
