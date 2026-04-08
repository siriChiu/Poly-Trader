#!/usr/bin/env python3
"""Clean legacy sparse-source feature pollution from historical rows.

This script removes feature values that were written when the underlying sparse
source was unavailable (NULL raw row) or when the collector used a fallback
sentinel value (e.g. claw ratio=1.0, nest_pred=0.5).

Usage:
  python scripts/cleanup_sparse_source_history.py         # dry run
  python scripts/cleanup_sparse_source_history.py --apply # mutate DB
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

DB_PATH = Path('/home/kazuha/Poly-Trader/poly_trader.db')
EPS = 1e-12


@dataclass(frozen=True)
class GroupRule:
    name: str
    feature_cols: tuple[str, ...]
    raw_cols: tuple[str, ...]
    unavailable: Callable[[sqlite3.Row], bool]
    raw_cleanup_cols: tuple[str, ...] = ()


def _approx(value, target: float) -> bool:
    return value is not None and abs(float(value) - target) < EPS


GROUPS: tuple[GroupRule, ...] = (
    GroupRule(
        name='claw',
        feature_cols=('feat_claw', 'feat_claw_intensity'),
        raw_cols=('claw_liq_ratio', 'claw_liq_total'),
        unavailable=lambda row: row['claw_liq_ratio'] is None or (
            _approx(row['claw_liq_ratio'], 1.0)
            and (row['claw_liq_total'] is None or _approx(row['claw_liq_total'], 0.0))
        ),
        raw_cleanup_cols=('claw_liq_ratio', 'claw_liq_total'),
    ),
    GroupRule(
        name='fang',
        feature_cols=('feat_fang_pcr', 'feat_fang_skew'),
        raw_cols=('fang_pcr', 'fang_iv_skew'),
        unavailable=lambda row: row['fang_pcr'] is None and row['fang_iv_skew'] is None,
    ),
    GroupRule(
        name='fin',
        feature_cols=('feat_fin_netflow',),
        raw_cols=('fin_etf_netflow', 'fin_etf_trend'),
        unavailable=lambda row: (
            row['fin_etf_netflow'] is None and row['fin_etf_trend'] is None
        ) or (
            _approx(row['fin_etf_netflow'], 0.0) and (row['fin_etf_trend'] is None or _approx(row['fin_etf_trend'], 0.0))
        ),
        raw_cleanup_cols=('fin_etf_netflow', 'fin_etf_trend'),
    ),
    GroupRule(
        name='web',
        feature_cols=('feat_web_whale',),
        raw_cols=('web_whale_pressure', 'web_large_trades_count'),
        unavailable=lambda row: row['web_whale_pressure'] is None and row['web_large_trades_count'] is None,
    ),
    GroupRule(
        name='scales',
        feature_cols=('feat_scales_ssr',),
        raw_cols=('scales_ssr',),
        unavailable=lambda row: row['scales_ssr'] is None,
    ),
    GroupRule(
        name='nest',
        feature_cols=('feat_nest_pred',),
        raw_cols=('nest_pred',),
        unavailable=lambda row: row['nest_pred'] is None or _approx(row['nest_pred'], 0.5),
        raw_cleanup_cols=('nest_pred',),
    ),
)


def build_query() -> str:
    selected = ['f.id AS feature_id', 'r.id AS raw_id', 'f.timestamp', 'f.symbol']
    for group in GROUPS:
        selected.extend(f'f.{col} AS {col}' for col in group.feature_cols)
        selected.extend(f'r.{col} AS {col}' for col in group.raw_cols)
    return f'''
        SELECT {", ".join(selected)}
        FROM features_normalized f
        LEFT JOIN raw_market_data r
          ON r.timestamp = f.timestamp AND r.symbol = f.symbol
        ORDER BY f.timestamp, f.symbol
    '''


def summarize(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(build_query()).fetchall()
    report: dict[str, dict] = {}
    for group in GROUPS:
        flagged_feature_ids: list[int] = []
        raw_ids_for_cleanup: list[int] = []
        feature_non_null = 0
        for row in rows:
            has_feature = any(row[col] is not None for col in group.feature_cols)
            if not has_feature:
                continue
            feature_non_null += 1
            if group.unavailable(row):
                flagged_feature_ids.append(row['feature_id'])
                if row['raw_id'] is not None and group.raw_cleanup_cols:
                    raw_ids_for_cleanup.append(row['raw_id'])
        report[group.name] = {
            'feature_non_null': feature_non_null,
            'flagged_feature_rows': len(flagged_feature_ids),
            'feature_ids': sorted(set(flagged_feature_ids)),
            'raw_ids': sorted(set(raw_ids_for_cleanup)),
            'feature_cols': list(group.feature_cols),
            'raw_cleanup_cols': list(group.raw_cleanup_cols),
        }
    return report


def apply_cleanup(conn: sqlite3.Connection, report: dict) -> dict:
    feature_updates = {}
    raw_updates = {}
    for group in GROUPS:
        item = report[group.name]
        feature_ids = item['feature_ids']
        raw_ids = item['raw_ids']
        if feature_ids:
            set_clause = ', '.join(f'{col} = NULL' for col in group.feature_cols)
            placeholders = ', '.join('?' for _ in feature_ids)
            conn.execute(
                f'UPDATE features_normalized SET {set_clause} WHERE id IN ({placeholders})',
                feature_ids,
            )
        if raw_ids and group.raw_cleanup_cols:
            set_clause = ', '.join(f'{col} = NULL' for col in group.raw_cleanup_cols)
            placeholders = ', '.join('?' for _ in raw_ids)
            conn.execute(
                f'UPDATE raw_market_data SET {set_clause} WHERE id IN ({placeholders})',
                raw_ids,
            )
        feature_updates[group.name] = len(feature_ids)
        raw_updates[group.name] = len(raw_ids)
    conn.commit()
    return {'feature_updates': feature_updates, 'raw_updates': raw_updates}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply updates to the database')
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        before = summarize(conn)
        payload = {
            'mode': 'apply' if args.apply else 'dry_run',
            'before': {
                key: {k: v for k, v in value.items() if k not in {'feature_ids', 'raw_ids'}}
                for key, value in before.items()
            },
        }
        if args.apply:
            payload['applied'] = apply_cleanup(conn, before)
            after = summarize(conn)
            payload['after'] = {
                key: {k: v for k, v in value.items() if k not in {'feature_ids', 'raw_ids'}}
                for key, value in after.items()
            }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    finally:
        conn.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
