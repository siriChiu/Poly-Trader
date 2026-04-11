#!/usr/bin/env python3
"""Dynamic Window training — scans recent windows and applies distribution-aware guardrails."""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path('/home/kazuha/Poly-Trader')
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

DB_PATH = PROJECT_ROOT / 'poly_trader.db'
DRIFT_REPORT_PATH = PROJECT_ROOT / 'data' / 'recent_drift_report.json'
DW_RESULT_PATH = PROJECT_ROOT / 'data' / 'dw_result.json'
TARGET_COL = 'simulated_pyramid_win'
CANONICAL_HORIZON_MINUTES = 1440
WINDOWS = [100, 200, 400, 600, 1000, 2000, 5000]
CORE_FEATURES = [
    'feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue',
    'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind',
]


def _round(value):
    if value is None:
        return None
    return round(float(value), 4)


def _counter_to_dict(counter: Counter) -> dict[str, int]:
    return {str(k): int(v) for k, v in counter.items()}


def _pct(numerator: int, denominator: int):
    if not denominator:
        return None
    return round(numerator / denominator, 4)


def load_recent_drift_report():
    if not DRIFT_REPORT_PATH.exists():
        return {}
    try:
        return json.loads(DRIFT_REPORT_PATH.read_text())
    except Exception:
        return {}


def build_distribution_summary(data_window, baseline_regimes: Counter):
    label_values = [int(r[TARGET_COL]) for r in data_window if r[TARGET_COL] is not None]
    target_counts = Counter(label_values)
    regime_counts = Counter((r.get('regime_label') or 'unknown') for r in data_window)
    total = len(label_values)
    dominant_regime, dominant_count = regime_counts.most_common(1)[0] if regime_counts else (None, 0)
    dominant_share = (dominant_count / total) if total else None
    baseline_total = sum(baseline_regimes.values())
    baseline_dominant_share = (
        baseline_regimes.get(dominant_regime, 0) / baseline_total
        if dominant_regime and baseline_total
        else 0.0
    )
    win_rate = (target_counts.get(1, 0) / total) if total else None
    unique_targets = sorted(target_counts.keys())

    alerts = []
    if len(unique_targets) <= 1:
        alerts.append('constant_target')
    elif win_rate is not None and (win_rate >= 0.8 or win_rate <= 0.2):
        alerts.append('label_imbalance')
    if dominant_share is not None and dominant_share >= 0.9:
        alerts.append('regime_concentration')
    if dominant_share is not None and (dominant_share - baseline_dominant_share) >= 0.2:
        alerts.append('regime_shift')

    return {
        'constant_target': len(unique_targets) <= 1,
        'target_counts': {str(k): int(v) for k, v in sorted(target_counts.items())},
        'win_rate': _round(win_rate),
        'regime_counts': _counter_to_dict(regime_counts),
        'regime_pct': {k: _pct(v, total) for k, v in _counter_to_dict(regime_counts).items()},
        'dominant_regime': dominant_regime,
        'dominant_regime_share': _round(dominant_share),
        'alerts': alerts,
    }


def analyze_window(data_window, baseline_regimes: Counter):
    """Return ICs plus distribution diagnostics for a given window."""
    ics = {}
    diagnostics = {}
    distribution = build_distribution_summary(data_window, baseline_regimes)

    for col in CORE_FEATURES:
        vals = [r[col] for r in data_window if r[col] is not None and r[TARGET_COL] is not None]
        labs = [r[TARGET_COL] for r in data_window if r[col] is not None and r[TARGET_COL] is not None]
        diag = {"n": len(vals), "reason": "ok"}
        if len(vals) < 20:
            ics[col] = 0.0
            diag["reason"] = "too_few_samples"
            diagnostics[col] = diag
            continue
        if len(set(vals)) <= 1:
            ics[col] = 0.0
            diag["reason"] = "constant_feature"
            diagnostics[col] = diag
            continue
        if len(set(labs)) <= 1:
            ics[col] = 0.0
            diag["reason"] = "constant_target"
            diagnostics[col] = diag
            continue
        if HAS_SCIPY:
            ic, _ = stats.spearmanr(vals, labs)
        else:
            ic = np.corrcoef(vals, labs)[0, 1]
        if ic is None or not np.isfinite(ic):
            ics[col] = 0.0
            diag["reason"] = "non_finite_ic"
        else:
            ics[col] = round(float(ic), 4)
        diagnostics[col] = diag

    return {
        "ics": ics,
        "diagnostics": diagnostics,
        **distribution,
    }


def merge_recent_drift(analysis, drift_report, window_size):
    windows = (drift_report or {}).get('windows') or {}
    external = windows.get(str(window_size)) or {}
    if not external:
        analysis['external_drift_summary'] = None
        analysis['distribution_guardrail'] = any(
            alert in analysis.get('alerts', []) for alert in ('constant_target', 'regime_concentration')
        )
        return analysis

    merged_alerts = sorted(set(analysis.get('alerts', [])) | set(external.get('alerts', [])))
    analysis['alerts'] = merged_alerts
    analysis['external_drift_summary'] = {
        'win_rate': external.get('win_rate'),
        'win_rate_delta_vs_full': external.get('win_rate_delta_vs_full'),
        'dominant_regime': external.get('dominant_regime'),
        'dominant_regime_share': external.get('dominant_regime_share'),
        'alerts': external.get('alerts', []),
    }
    analysis['distribution_guardrail'] = any(
        alert in merged_alerts for alert in ('constant_target', 'regime_concentration')
    )
    return analysis


def choose_best_windows(results):
    numeric_windows = sorted(k for k in results.keys() if isinstance(k, int))
    raw_best = None
    recommended_best = None

    for window in numeric_windows:
        analysis = results[window]
        passed = sum(1 for v in analysis['ics'].values() if abs(v) >= 0.05)
        if raw_best is None or passed > raw_best[1] or (passed == raw_best[1] and window < raw_best[0]):
            raw_best = (window, passed)
        if analysis.get('distribution_guardrail'):
            continue
        if recommended_best is None or passed > recommended_best[1] or (passed == recommended_best[1] and window < recommended_best[0]):
            recommended_best = (window, passed)

    return raw_best, recommended_best


def main():
    conn = sqlite3.connect(DB_PATH)

    feat_query = f"""
        SELECT f.{', f.'.join(CORE_FEATURES)}, f.timestamp, f.symbol, f.regime_label
        FROM features_normalized f
        ORDER BY f.timestamp
    """
    feat_df = conn.execute(feat_query)
    feat_names = [d[0] for d in feat_df.description]
    feat_rows = feat_df.fetchall()

    label_query = f"""
        SELECT timestamp, symbol, {TARGET_COL}
        FROM labels
        WHERE {TARGET_COL} IS NOT NULL
          AND horizon_minutes = {CANONICAL_HORIZON_MINUTES}
    """
    label_rows = conn.execute(label_query).fetchall()
    label_map = {(r[0], r[1]): r[2] for r in label_rows}
    conn.close()

    matched = []
    for row in feat_rows:
        row_dict = dict(zip(feat_names, row))
        key = (row_dict['timestamp'], row_dict['symbol'])
        if key in label_map:
            row_dict[TARGET_COL] = label_map[key]
            matched.append(row_dict)

    if not matched:
        print("ERROR: No matches!")
        return

    total_n = len(matched)
    baseline_regimes = Counter((r.get('regime_label') or 'unknown') for r in matched)
    drift_report = load_recent_drift_report()

    print(f"Dynamic Window Analysis — total n={total_n}")
    print("=" * 70)

    results = {}
    for window_size in WINDOWS:
        if window_size > total_n:
            continue
        window = matched[-window_size:]
        analysis = analyze_window(window, baseline_regimes)
        analysis = merge_recent_drift(analysis, drift_report, window_size)
        passed = sum(1 for v in analysis['ics'].values() if abs(v) >= 0.05)
        results[window_size] = analysis

        target_counts = ', '.join(f"{k}:{v}" for k, v in analysis['target_counts'].items()) or 'none'
        dominant_regime = analysis.get('dominant_regime') or 'unknown'
        dominant_share = analysis.get('dominant_regime_share')
        dominant_text = f"{dominant_regime}({dominant_share:.2%})" if dominant_share is not None else dominant_regime
        alerts = analysis.get('alerts', [])
        headline = (
            f"\nN={window_size:>5d}: {passed}/{len(CORE_FEATURES)} passed | "
            f"target_counts={target_counts} | dominant_regime={dominant_text}"
        )
        if alerts:
            headline += f" | alerts={alerts}"
        if analysis.get('distribution_guardrail'):
            headline += " | distribution_guardrail=skip_for_recommendation"
        print(headline)

        for feat in CORE_FEATURES:
            short = feat.replace('feat_', '')
            ic = analysis['ics'].get(feat, 0)
            reason = analysis['diagnostics'].get(feat, {}).get('reason', 'ok')
            status = "✅" if abs(ic) >= 0.05 else ("⚠️" if reason != 'ok' else "❌")
            suffix = "" if reason == 'ok' else f" ({reason})"
            print(f"  {short:8s}: IC={ic:+.4f} {status}{suffix}")

    raw_best, recommended_best = choose_best_windows(results)

    print(f"\n{'=' * 70}")
    if raw_best is not None:
        print(f"Raw best window: N={raw_best[0]} ({raw_best[1]}/{len(CORE_FEATURES)} passing)")
    if recommended_best is not None:
        print(
            f"Recommended window: N={recommended_best[0]} "
            f"({recommended_best[1]}/{len(CORE_FEATURES)} passing, guardrail-safe)"
        )
    else:
        print("Recommended window: none (all candidate windows are guardrailed)")

    results['raw_best_n'] = raw_best[0] if raw_best else None
    results['raw_best_pass'] = raw_best[1] if raw_best else None
    results['recommended_best_n'] = recommended_best[0] if recommended_best else None
    results['recommended_best_pass'] = recommended_best[1] if recommended_best else None
    results['guardrail_policy'] = {
        'disqualifying_alerts': ['constant_target', 'regime_concentration'],
        'source': 'local_window_distribution + recent_drift_report.json',
    }
    results['total_n'] = total_n

    DW_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DW_RESULT_PATH.write_text(json.dumps(results, indent=2))
    print(f"Saved to {DW_RESULT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == '__main__':
    main()
