#!/usr/bin/env python3
"""Backfill low-coverage macro / external features into raw_market_data and features_normalized.

Priority targets:
- vix / dxy / nq
- fang_pcr / fang_skew
- fin_netflow
- web_whale / nest_pred / scales_ssr

Rules:
- Yahoo hourly history is fetched in chunks and aligned to raw rows with carry-forward
  up to 72h (market-closure aware).
- Existing sparse raw feature columns (fang/web/nest/scales) are carried forward for a
  limited window so feature history becomes continuous rather than spike-only.
- fin_etf_netflow is only backfilled if raw data already exists; current live source
  often returns default 0.0 with no API key/data.
- features_normalized is updated from raw_market_data using deterministic transforms,
  without touching unrelated feature columns.
"""

from __future__ import annotations

import bisect
import json
import math
import sqlite3
import ssl
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

DB_PATH = Path('/home/kazuha/Poly-Trader/poly_trader.db')
REPORT_PATH = Path('/home/kazuha/Poly-Trader/data/low_coverage_backfill_report.json')
_CTX = ssl.create_default_context()
_HEADERS = {'User-Agent': 'Mozilla/5.0'}

YAHOO_SYMBOLS = {
    'vix_value': '%5EVIX',
    'dxy_value': 'DX-Y.NYB',
    'nq_value': 'NQ=F',
}
RAW_CARRY_FORWARD_COLS = {
    'fang_pcr': 24,
    'fang_iv_skew': 24,
    'web_whale_pressure': 12,
    'web_large_trades_count': 12,
    'scales_ssr': 24,
    'nest_pred': 12,
}


@dataclass
class SeriesPoint:
    ts: int
    value: float


def _dt_to_epoch(dt_str: str) -> int:
    dt = datetime.fromisoformat(str(dt_str).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _fetch_yahoo_range(symbol: str, range_d: str = '730d', interval: str = '1h') -> list[SeriesPoint]:
    url = (
        f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
        f'?range={range_d}&interval={interval}&includePrePost=false&events=history'
    )
    req = Request(url, headers=_HEADERS)
    with urlopen(req, context=_CTX, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    result = (((data or {}).get('chart') or {}).get('result') or [None])[0]
    if not result:
        return []
    timestamps = result.get('timestamp') or []
    closes = (((result.get('indicators') or {}).get('quote') or [{}])[0].get('close') or [])
    return [SeriesPoint(int(ts), float(close)) for ts, close in zip(timestamps, closes) if close is not None]


def fetch_yahoo_history(symbol: str, start_epoch: int, end_epoch: int) -> list[SeriesPoint]:
    points = _fetch_yahoo_range(symbol, range_d='730d', interval='1h')
    return [p for p in points if start_epoch <= p.ts <= end_epoch]


def nearest_asof(points: list[SeriesPoint], target_epoch: int, max_age_hours: int) -> float | None:
    if not points:
        return None
    ts_list = [p.ts for p in points]
    idx = bisect.bisect_right(ts_list, target_epoch) - 1
    if idx < 0:
        return None
    point = points[idx]
    age_hours = (target_epoch - point.ts) / 3600.0
    if age_hours < 0 or age_hours > max_age_hours:
        return None
    return point.value


def load_raw_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        'SELECT id, timestamp, symbol, vix_value, dxy_value, nq_value, '
        'fang_pcr, fang_iv_skew, fin_etf_netflow, web_whale_pressure, '
        'web_large_trades_count, scales_ssr, nest_pred '
        'FROM raw_market_data ORDER BY timestamp'
    ).fetchall()


def backfill_yahoo_raw(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> dict:
    if not rows:
        return {}
    start_epoch = _dt_to_epoch(rows[0]['timestamp']) - 7 * 24 * 3600
    end_epoch = _dt_to_epoch(rows[-1]['timestamp']) + 24 * 3600

    report = {}
    cur = conn.cursor()
    for col, symbol in YAHOO_SYMBOLS.items():
        series = fetch_yahoo_history(symbol, start_epoch, end_epoch)
        updates = 0
        for row in rows:
            current = row[col]
            if current is not None:
                continue
            target_epoch = _dt_to_epoch(row['timestamp'])
            matched = nearest_asof(series, target_epoch, max_age_hours=72)
            if matched is None:
                continue
            cur.execute(f'UPDATE raw_market_data SET {col}=? WHERE id=?', (matched, row['id']))
            updates += 1
        report[col] = {
            'series_points': len(series),
            'raw_updates': updates,
        }
    conn.commit()
    return report


def carry_forward_existing_raw(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> dict:
    cur = conn.cursor()
    report = {}
    for col, max_age_hours in RAW_CARRY_FORWARD_COLS.items():
        sparse = [SeriesPoint(_dt_to_epoch(r['timestamp']), float(r[col])) for r in rows if r[col] is not None]
        updates = 0
        for row in rows:
            if row[col] is not None:
                continue
            target_epoch = _dt_to_epoch(row['timestamp'])
            matched = nearest_asof(sparse, target_epoch, max_age_hours=max_age_hours)
            if matched is None:
                continue
            cur.execute(f'UPDATE raw_market_data SET {col}=? WHERE id=?', (matched, row['id']))
            updates += 1
        report[col] = {
            'sparse_points': len(sparse),
            'raw_updates': updates,
        }
    conn.commit()
    return report


def compute_nq_returns(rows: list[sqlite3.Row]) -> tuple[dict[str, float], dict[str, float]]:
    valid = [(str(r['timestamp']), float(r['nq_value'])) for r in rows if r['nq_value'] is not None]
    ts_list = [ts for ts, _ in valid]
    vals = [v for _, v in valid]
    ret_1h: dict[str, float] = {}
    ret_24h: dict[str, float] = {}
    for i, (ts, latest) in enumerate(valid):
        if i >= 1 and vals[i - 1] > 0:
            ret_1h[ts] = -(latest / vals[i - 1] - 1.0)
        if i >= 24 and vals[i - 24] > 0:
            ret_24h[ts] = -(latest / vals[i - 24] - 1.0)
    return ret_1h, ret_24h


def backfill_features_from_raw(conn: sqlite3.Connection) -> dict:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        'SELECT r.timestamp, r.symbol, r.vix_value, r.dxy_value, r.nq_value, '
        'r.fang_pcr, r.fang_iv_skew, r.fin_etf_netflow, r.web_whale_pressure, '
        'r.web_large_trades_count, r.scales_ssr, r.nest_pred '
        'FROM raw_market_data r ORDER BY r.timestamp'
    ).fetchall()
    ret_1h, ret_24h = compute_nq_returns(rows)

    cur = conn.cursor()
    updates = defaultdict(int)
    for row in rows:
        ts = str(row['timestamp'])
        symbol = row['symbol']
        assignments = {}
        if row['vix_value'] is not None:
            assignments['feat_vix'] = float(row['vix_value'])
        if row['dxy_value'] is not None:
            assignments['feat_dxy'] = float(row['dxy_value'])
        if ts in ret_1h:
            assignments['feat_nq_return_1h'] = float(ret_1h[ts])
        if ts in ret_24h:
            assignments['feat_nq_return_24h'] = float(ret_24h[ts])
        if row['fang_pcr'] is not None:
            assignments['feat_fang_pcr'] = float(math.tanh((float(row['fang_pcr']) - 1.0) * 2.0))
        if row['fang_iv_skew'] is not None:
            assignments['feat_fang_skew'] = float(float(row['fang_iv_skew']) / 10.0)
        if row['fin_etf_netflow'] is not None:
            assignments['feat_fin_netflow'] = float(-math.tanh(float(row['fin_etf_netflow']) / 500_000_000.0))
        if row['web_whale_pressure'] is not None:
            assignments['feat_web_whale'] = float(row['web_whale_pressure'])
        if row['scales_ssr'] is not None:
            assignments['feat_scales_ssr'] = float(row['scales_ssr'])
        if row['nest_pred'] is not None:
            assignments['feat_nest_pred'] = float(float(row['nest_pred']) - 0.5)
        if not assignments:
            continue
        set_clause = ', '.join(f'{col}=?' for col in assignments)
        params = list(assignments.values()) + [ts, symbol]
        cur.execute(
            f'UPDATE features_normalized SET {set_clause} WHERE timestamp=? AND symbol=?',
            params,
        )
        for col in assignments:
            updates[col] += cur.rowcount
    conn.commit()
    return dict(updates)


def measure_coverage(conn: sqlite3.Connection, table: str, cols: Iterable[str]) -> dict:
    cur = conn.cursor()
    total = cur.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    report = {}
    for col in cols:
        non_null, distinct_cnt = cur.execute(f'SELECT COUNT({col}), COUNT(DISTINCT {col}) FROM {table}').fetchone()
        report[col] = {
            'non_null': non_null,
            'coverage_pct': round(non_null / total * 100.0, 2) if total else 0.0,
            'distinct': distinct_cnt,
        }
    return report


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    rows_before = load_raw_rows(conn)
    raw_before = measure_coverage(conn, 'raw_market_data', [*YAHOO_SYMBOLS.keys(), *RAW_CARRY_FORWARD_COLS.keys(), 'fin_etf_netflow'])
    feat_before = measure_coverage(conn, 'features_normalized', [
        'feat_vix', 'feat_dxy', 'feat_nq_return_1h', 'feat_nq_return_24h',
        'feat_fang_pcr', 'feat_fang_skew', 'feat_fin_netflow', 'feat_web_whale',
        'feat_scales_ssr', 'feat_nest_pred',
    ])

    yahoo_report = backfill_yahoo_raw(conn, rows_before)
    rows_mid = load_raw_rows(conn)
    carry_report = carry_forward_existing_raw(conn, rows_mid)
    feature_updates = backfill_features_from_raw(conn)

    raw_after = measure_coverage(conn, 'raw_market_data', [*YAHOO_SYMBOLS.keys(), *RAW_CARRY_FORWARD_COLS.keys(), 'fin_etf_netflow'])
    feat_after = measure_coverage(conn, 'features_normalized', [
        'feat_vix', 'feat_dxy', 'feat_nq_return_1h', 'feat_nq_return_24h',
        'feat_fang_pcr', 'feat_fang_skew', 'feat_fin_netflow', 'feat_web_whale',
        'feat_scales_ssr', 'feat_nest_pred',
    ])
    conn.close()

    report = {
        'yahoo_backfill': yahoo_report,
        'carry_forward_backfill': carry_report,
        'feature_updates': feature_updates,
        'raw_before': raw_before,
        'raw_after': raw_after,
        'features_before': feat_before,
        'features_after': feat_after,
        'notes': {
            'fin_etf_netflow': 'No historical backfill performed without usable raw/API data.',
            'web_whale_pressure': 'Carry-forward uses existing sparse raw points only; no public historical OKX large-trade archive was added in this pass.',
            'nest_pred': 'Carry-forward uses existing sparse raw points only; current live Polymarket fetch returns neutral 0.5.',
        },
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f'\nSaved report to {REPORT_PATH}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
