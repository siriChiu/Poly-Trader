#!/usr/bin/env python3
"""Generate feature coverage / distinctness report for chartable features."""

from __future__ import annotations

from pathlib import Path
import json
import sqlite3

DB_PATH = Path('/home/kazuha/Poly-Trader/poly_trader.db')
OUT_JSON = Path('/home/kazuha/Poly-Trader/data/feature_coverage_report.json')
OUT_MD = Path('/home/kazuha/Poly-Trader/data/feature_coverage_report.md')

FEATURE_KEY_MAP = {
    'feat_eye': 'eye', 'feat_ear': 'ear', 'feat_nose': 'nose', 'feat_tongue': 'tongue',
    'feat_body': 'body', 'feat_pulse': 'pulse', 'feat_aura': 'aura', 'feat_mind': 'mind',
    'feat_vix': 'vix', 'feat_dxy': 'dxy', 'feat_rsi14': 'rsi14', 'feat_macd_hist': 'macd_hist',
    'feat_atr_pct': 'atr_pct', 'feat_vwap_dev': 'vwap_dev', 'feat_bb_pct_b': 'bb_pct_b',
    'feat_nq_return_1h': 'nq_return_1h', 'feat_nq_return_24h': 'nq_return_24h',
    'feat_claw': 'claw', 'feat_claw_intensity': 'claw_intensity',
    'feat_fang_pcr': 'fang_pcr', 'feat_fang_skew': 'fang_skew', 'feat_fin_netflow': 'fin_netflow',
    'feat_web_whale': 'web_whale', 'feat_scales_ssr': 'scales_ssr', 'feat_nest_pred': 'nest_pred',
    'feat_4h_bias50': '4h_bias50', 'feat_4h_bias20': '4h_bias20', 'feat_4h_rsi14': '4h_rsi14',
    'feat_4h_macd_hist': '4h_macd_hist', 'feat_4h_bb_pct_b': '4h_bb_pct_b',
    'feat_4h_ma_order': '4h_ma_order', 'feat_4h_dist_swing_low': '4h_dist_sl',
}


def assess(clean_key: str, coverage_pct: float, distinct: int) -> tuple[bool, list[str]]:
    is_4h = clean_key.startswith('4h_')
    min_coverage = 5.0 if is_4h else 60.0
    reasons = []
    if coverage_pct < min_coverage:
        reasons.append(f'coverage<{min_coverage:.0f}%')
    if distinct < 10:
        reasons.append('distinct<10')
    return (coverage_pct >= min_coverage and distinct >= 10), reasons


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    total_rows = cur.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
    stats = []
    for db_key, clean_key in FEATURE_KEY_MAP.items():
        non_null, distinct, min_v, max_v = cur.execute(
            f'SELECT COUNT({db_key}), COUNT(DISTINCT {db_key}), MIN({db_key}), MAX({db_key}) FROM features_normalized'
        ).fetchone()
        coverage_pct = (non_null / total_rows * 100.0) if total_rows else 0.0
        usable, reasons = assess(clean_key, coverage_pct, distinct or 0)
        stats.append({
            'db_key': db_key,
            'key': clean_key,
            'non_null': non_null,
            'coverage_pct': round(coverage_pct, 2),
            'distinct': distinct or 0,
            'min': min_v,
            'max': max_v,
            'chart_usable': usable,
            'reasons': reasons,
        })
    conn.close()

    stats.sort(key=lambda row: (row['chart_usable'], row['coverage_pct'], row['distinct']))
    payload = {
        'rows_total': total_rows,
        'usable_count': sum(1 for row in stats if row['chart_usable']),
        'hidden_count': sum(1 for row in stats if not row['chart_usable']),
        'features': stats,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')

    lines = [
        '# Feature Coverage Report',
        '',
        f'- Total rows: **{total_rows}**',
        f'- Chart-usable: **{payload["usable_count"]}**',
        f'- Hidden by default: **{payload["hidden_count"]}**',
        '',
        '| Feature | Coverage | Distinct | Chart usable | Notes |',
        '|---|---:|---:|---|---|',
    ]
    for row in stats:
        notes = ', '.join(row['reasons']) if row['reasons'] else 'ok'
        lines.append(f"| {row['key']} | {row['coverage_pct']:.2f}% | {row['distinct']} | {'✅' if row['chart_usable'] else '❌'} | {notes} |")
    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f'\nSaved JSON to {OUT_JSON}')
    print(f'Saved Markdown to {OUT_MD}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
