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
TARGET_COL = 'simulated_pyramid_win'
CANONICAL_HORIZON_MINUTES = 1440

CORE_FEATURES = [
    'feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue',
    'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind',
]


def _is_finite_number(value):
    return isinstance(value, (int, float, np.floating)) and np.isfinite(value)


def _assign_regimes(matched):
    """Assign regimes using Mind tertiles when available, else fallback to features.regime_label.

    Heartbeat #630 fix: many canonical rows have feat_mind=None, which previously dumped
    most rows into a fake 'neutral' bucket and polluted regime-aware IC analysis.
    """
    mind_vals = np.array([
        float(r['feat_mind']) for r in matched if _is_finite_number(r.get('feat_mind'))
    ], dtype=float)

    fallback_used = 0
    if len(mind_vals) > 100:
        p33, p67 = float(np.percentile(mind_vals, 33)), float(np.percentile(mind_vals, 67))
        for r in matched:
            feat_mind = r.get('feat_mind')
            if _is_finite_number(feat_mind):
                feat_mind = float(feat_mind)
                if feat_mind < p33:
                    r['regime'] = 'bear'
                elif feat_mind > p67:
                    r['regime'] = 'bull'
                else:
                    r['regime'] = 'chop'
                continue

            feature_regime = r.get('feature_regime')
            if feature_regime in {'bear', 'bull', 'chop'}:
                r['regime'] = feature_regime
            else:
                r['regime'] = 'neutral'
            fallback_used += 1
        return {
            'method': 'mind_tertiles_with_feature_regime_fallback',
            'p33': round(p33, 6),
            'p67': round(p67, 6),
            'fallback_rows': fallback_used,
            'mind_rows': int(len(mind_vals)),
        }

    for r in matched:
        feature_regime = r.get('feature_regime')
        if feature_regime in {'bear', 'bull', 'chop'}:
            r['regime'] = feature_regime
        else:
            r['regime'] = 'neutral'
        fallback_used += 1
    return {
        'method': 'feature_regime_only_fallback',
        'fallback_rows': fallback_used,
        'mind_rows': int(len(mind_vals)),
    }


def _safe_spearman(vals, labs):
    vals = np.array(vals, dtype=float)
    labs = np.array(labs, dtype=float)
    if vals.size < 2 or labs.size < 2:
        return 0.0, 'too_few_samples'
    if np.unique(vals).size <= 1:
        return 0.0, 'constant_feature'
    if np.unique(labs).size <= 1:
        return 0.0, 'constant_target'
    if HAS_SCIPY:
        ic, _ = stats.spearmanr(vals, labs)
    else:
        ic = np.corrcoef(vals, labs)[0, 1]
    if ic is None or not np.isfinite(ic):
        return 0.0, 'non_finite_ic'
    return float(ic), 'ok'


def main():
    conn = sqlite3.connect(DB_PATH)
    
    # Load features + labels via JOIN
    feat_query = f"""SELECT f.{', f.'.join(CORE_FEATURES)}, f.timestamp, f.symbol, f.regime_label AS feature_regime
                     FROM features_normalized f ORDER BY f.timestamp"""
    feat_df = conn.execute(feat_query)
    feat_names = [d[0] for d in feat_df.description]
    feat_rows = feat_df.fetchall()
    
    label_query = f"""SELECT timestamp, symbol, {TARGET_COL}, regime_label
                     FROM labels
                     WHERE {TARGET_COL} IS NOT NULL
                       AND horizon_minutes = {CANONICAL_HORIZON_MINUTES}"""
    label_rows = conn.execute(label_query).fetchall()
    label_map = {(r[0], r[1]): {TARGET_COL: r[2], 'regime_label': r[3]} for r in label_rows}
    
    matched = []
    for row in feat_rows:
        row_dict = dict(zip(feat_names, row))
        key = (row_dict['timestamp'], row_dict['symbol'])
        if key in label_map:
            row_dict[TARGET_COL] = label_map[key][TARGET_COL]
            row_dict['label_regime'] = label_map[key]['regime_label']
            matched.append(row_dict)
    
    if not matched:
        print("ERROR: No matches!")
        return
    
    n = len(matched)
    print(f"Regime-Aware IC Analysis — n={n}")
    print("=" * 70)
    
    regime_meta = _assign_regimes(matched)

    regime_counts = {}
    for r in matched:
        regime_counts[r['regime']] = regime_counts.get(r['regime'], 0) + 1
    print(f"Regime distribution ({regime_meta['method']}): {regime_counts}")
    if regime_meta.get('fallback_rows'):
        print(
            f"  ↳ fallback rows using features.regime_label: {regime_meta['fallback_rows']}"
            f" / {len(matched)}"
        )
    
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
        diagnostics = {}
        for col in CORE_FEATURES:
            vals = [r[col] for r in subset if r[col] is not None and r[TARGET_COL] is not None]
            labs = [r[TARGET_COL] for r in subset if r[col] is not None and r[TARGET_COL] is not None]
            if len(vals) < 20:
                ics[col] = 0.0
                diagnostics[col] = 'too_few_samples'
                continue
            ic, reason = _safe_spearman(vals, labs)
            ics[col] = round(float(ic), 4)
            diagnostics[col] = reason
        
        passed = sum(1 for v in ics.values() if abs(v) >= 0.05)
        result[regime] = {'n': len(subset), 'ics': ics, 'passed': passed, 'diagnostics': diagnostics}
        
        for col in CORE_FEATURES:
            short = col.replace('feat_', '')
            ic = ics.get(col, 0)
            reason = diagnostics.get(col, 'ok')
            status = "✅" if abs(ic) >= 0.05 else ("⚠️" if reason != 'ok' else "❌")
            suffix = "" if reason == 'ok' else f" ({reason})"
            print(f"  {short:8s}: IC={ic:+.4f} {status}{suffix}")
        print(f"  → {passed}/{len(CORE_FEATURES)} passing")
    
    # Target hit rate by regime
    print(f"\n=== {TARGET_COL} Rate by Regime ===")
    for regime in regimes:
        subset = [r for r in matched if r['regime'] == regime]
        if len(subset) > 0:
            win_count = sum(1 for r in subset if r[TARGET_COL] == 1)
            rate = win_count / len(subset)
            print(f"  {regime:8s}: {TARGET_COL}={rate:.4f} (n={len(subset)})")
    
    # Overall target hit rate
    all_wins = sum(1 for r in matched if r[TARGET_COL] == 1)
    overall = all_wins / len(matched)
    print(f"\nOverall: {TARGET_COL}={overall:.4f} (n={len(matched)})")
    
    result[f'overall_{TARGET_COL}'] = round(overall, 4)
    result['overall_n'] = len(matched)
    result['regime_meta'] = regime_meta
    result['regime_counts'] = regime_counts
    
    os.makedirs('/home/kazuha/Poly-Trader/data', exist_ok=True)
    with open('/home/kazuha/Poly-Trader/data/ic_regime_analysis.json', 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nSaved to data/ic_regime_analysis.json")
    
    return result

if __name__ == '__main__':
    main()
