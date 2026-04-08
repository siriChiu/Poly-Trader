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
    'feat_4h_bias50': '4h_bias50', 'feat_4h_bias20': '4h_bias20', 'feat_4h_bias200': '4h_bias200',
    'feat_4h_rsi14': '4h_rsi14', 'feat_4h_macd_hist': '4h_macd_hist', 'feat_4h_bb_pct_b': '4h_bb_pct_b',
    'feat_4h_dist_bb_lower': '4h_dist_bb_lower', 'feat_4h_ma_order': '4h_ma_order',
    'feat_4h_dist_swing_low': '4h_dist_sl', 'feat_4h_vol_ratio': '4h_vol_ratio',
}

SOURCE_FEATURE_KEYS = {
    'claw', 'claw_intensity', 'fang_pcr', 'fang_skew', 'fin_netflow',
    'web_whale', 'scales_ssr', 'nest_pred',
}

SOURCE_HISTORY_POLICIES = {
    'claw': {
        'history_class': 'archive_required',
        'backfill_status': 'blocked',
        'backfill_blocker': 'CoinGlass liquidation integration only saves recent live windows; no historical liquidation archive is wired into raw_market_data.',
        'recommended_action': 'Keep forward collection running or add CoinGlass historical export/API archive before attempting backfill.',
    },
    'claw_intensity': {
        'history_class': 'archive_required',
        'backfill_status': 'blocked',
        'backfill_blocker': 'Claw intensity is derived from CoinGlass liquidation history, but the project only stores live windows and has no historical archive loader.',
        'recommended_action': 'Backfill claw raw history first, then recompute feature rows from raw.',
    },
    'fang_pcr': {
        'history_class': 'snapshot_only',
        'backfill_status': 'blocked',
        'backfill_blocker': 'Deribit options summary integration is a latest snapshot fetch; historical option-chain snapshots were never archived.',
        'recommended_action': 'Add periodic raw snapshot collection or a dedicated historical options source before expecting chart coverage.',
    },
    'fang_skew': {
        'history_class': 'snapshot_only',
        'backfill_status': 'blocked',
        'backfill_blocker': 'Fang skew depends on latest Deribit option-book snapshot; there is no historical snapshot archive in the current pipeline.',
        'recommended_action': 'Add periodic raw snapshot collection or a dedicated historical options source before backfilling.',
    },
    'fin_netflow': {
        'history_class': 'archive_required',
        'backfill_status': 'blocked',
        'backfill_blocker': 'ETF flow collector only reads the current CoinGlass flow payload; no historical day-by-day ETF archive has been persisted.',
        'recommended_action': 'Wire a historical ETF flow export/API path into raw_market_data, then recompute feature history.',
    },
    'web_whale': {
        'history_class': 'short_window_public_api',
        'backfill_status': 'blocked',
        'backfill_blocker': 'Binance aggTrades endpoint only exposes a short recent trade window in the current implementation; no historical whale snapshot archive exists.',
        'recommended_action': 'Accumulate snapshots forward or add a historical large-trade data source; do not synthesize history with carry-forward.',
    },
    'scales_ssr': {
        'history_class': 'snapshot_only',
        'backfill_status': 'blocked',
        'backfill_blocker': 'Scales SSR currently uses a live CoinGecko stablecoin market-cap snapshot, not a stored historical time series.',
        'recommended_action': 'Add a historical stablecoin market-cap source or collect periodic raw snapshots going forward.',
    },
    'nest_pred': {
        'history_class': 'snapshot_only',
        'backfill_status': 'blocked',
        'backfill_blocker': 'Polymarket integration searches current active markets only; past market probabilities were not archived into raw_market_data.',
        'recommended_action': 'Persist market snapshots each heartbeat or add historical Polymarket event replay before backfilling.',
    },
}


def _is_zero_like(value) -> bool:
    return value is not None and abs(float(value)) < 1e-12


def _source_history_meta(clean_key: str) -> dict:
    if clean_key not in SOURCE_FEATURE_KEYS:
        return {
            'history_class': 'native_timeseries',
            'backfill_status': 'n/a',
            'backfill_blocker': None,
            'recommended_action': None,
        }
    return SOURCE_HISTORY_POLICIES.get(clean_key, {
        'history_class': 'unknown_source_policy',
        'backfill_status': 'investigate',
        'backfill_blocker': 'Sparse source policy missing from SOURCE_HISTORY_POLICIES.',
        'recommended_action': 'Document the source history contract before treating this coverage gap as a frontend bug.',
    })


def assess(clean_key: str, coverage_pct: float, distinct: int, non_null: int, min_v, max_v) -> tuple[bool, list[str], str, str, dict]:
    is_4h = clean_key.startswith('4h_')
    min_coverage = 5.0 if is_4h else 60.0
    min_distinct = 2 if clean_key == '4h_ma_order' else 10
    reasons = []

    zero_only_series = non_null > 0 and distinct <= 1 and _is_zero_like(min_v) and _is_zero_like(max_v)
    source_issue = clean_key in SOURCE_FEATURE_KEYS

    if zero_only_series and source_issue:
        reasons.append('source_fallback_zero')
    elif coverage_pct < min_coverage and source_issue:
        reasons.append('source_history_gap')
    elif distinct < min_distinct and source_issue:
        reasons.append('source_constant_series')

    if coverage_pct < min_coverage:
        reasons.append(f'coverage<{min_coverage:.0f}%')
    if distinct < min_distinct:
        reasons.append(f'distinct<{min_distinct}')

    if zero_only_series and source_issue:
        quality_flag = 'source_fallback_zero'
        quality_label = 'source fallback wrote zero-like values'
    elif coverage_pct < min_coverage and source_issue:
        quality_flag = 'source_history_gap'
        quality_label = 'source-level history coverage gap'
    elif distinct < min_distinct and source_issue:
        quality_flag = 'source_constant_series'
        quality_label = 'source values are effectively constant'
    elif coverage_pct < min_coverage:
        quality_flag = 'low_coverage'
        quality_label = 'coverage below chart threshold'
    elif distinct < min_distinct:
        quality_flag = 'low_distinct'
        quality_label = 'distinct count below chart threshold'
    else:
        quality_flag = 'ok'
        quality_label = 'ok'

    history_meta = _source_history_meta(clean_key)
    return (
        coverage_pct >= min_coverage and distinct >= min_distinct,
        reasons,
        quality_flag,
        quality_label,
        history_meta,
    )


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
        usable, reasons, quality_flag, quality_label, history_meta = assess(
            clean_key,
            coverage_pct,
            distinct or 0,
            non_null,
            min_v,
            max_v,
        )
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
            'quality_flag': quality_flag,
            'quality_label': quality_label,
            **history_meta,
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
        '| Feature | Coverage | Distinct | Chart usable | Quality | History policy | Next action |',
        '|---|---:|---:|---|---|---|---|',
    ]
    for row in stats:
        notes = ', '.join(row['reasons']) if row['reasons'] else 'ok'
        history_policy = row.get('history_class', 'native_timeseries')
        next_action = row.get('recommended_action') or notes
        lines.append(
            f"| {row['key']} | {row['coverage_pct']:.2f}% | {row['distinct']} | {'✅' if row['chart_usable'] else '❌'} | {row['quality_flag']} | {history_policy} | {next_action} |"
        )
    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f'\nSaved JSON to {OUT_JSON}')
    print(f'Saved Markdown to {OUT_MD}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
