from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from typing import Any, Dict, Iterable, List, Sequence

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

SOURCE_SNAPSHOT_SUBTYPES = {
    'claw': ('claw_snapshot',),
    'claw_intensity': ('claw_snapshot',),
    'fang_pcr': ('fang_snapshot',),
    'fang_skew': ('fang_snapshot',),
    'fin_netflow': ('fin_snapshot',),
    'web_whale': ('web_snapshot',),
    'scales_ssr': ('scales_snapshot',),
    'nest_pred': ('nest_snapshot',),
}

# A single snapshot means forward archiving has started, but it is not enough to
# call the archive "ready" for chart/debug workflows. We use 10 events because
# the FeatureChart distinct-count gate also treats <10 as too sparse to be
# meaningful, so heartbeat/runtime/UI all share the same maturity threshold.
FORWARD_ARCHIVE_READY_MIN_EVENTS = 10
FORWARD_ARCHIVE_STALE_MINUTES = 60

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


def is_zero_like(value: Any) -> bool:
    return value is not None and abs(float(value)) < 1e-12


def source_history_meta(clean_key: str) -> Dict[str, Any]:
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


def assess_feature_quality(clean_key: str, coverage_pct: float, distinct: int, non_null: int, min_v, max_v) -> Dict[str, Any]:
    is_4h = clean_key.startswith('4h_')
    min_coverage = 5.0 if is_4h else 60.0
    min_distinct = 2 if clean_key == '4h_ma_order' else 10
    reasons: List[str] = []

    zero_only_series = non_null > 0 and distinct <= 1 and is_zero_like(min_v) and is_zero_like(max_v)
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

    return {
        'chart_usable': coverage_pct >= min_coverage and distinct >= min_distinct,
        'reasons': reasons,
        'quality_flag': quality_flag,
        'quality_label': quality_label,
        'expected_min_coverage': min_coverage,
        'expected_min_distinct': min_distinct,
        **source_history_meta(clean_key),
    }


def _parse_sqlite_timestamp(value: Any) -> datetime | None:
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith('Z'):
            text = text[:-1] + '+00:00'
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _snapshot_minute_key(ts_value: Any) -> str | None:
    ts = _parse_sqlite_timestamp(ts_value)
    if ts is None:
        return None
    return ts.astimezone(timezone.utc).replace(second=0, microsecond=0).isoformat()



def _compute_archive_window_coverage(
    clean_key: str,
    timestamp_values: Sequence[Any],
    feature_values: Sequence[Any],
    snapshot_stats: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    snapshot_stats = snapshot_stats or {}
    subtypes = SOURCE_SNAPSHOT_SUBTYPES.get(clean_key, ())
    oldest_points = [
        _parse_sqlite_timestamp(snapshot_stats.get(subtype, {}).get('oldest_ts'))
        for subtype in subtypes
        if snapshot_stats.get(subtype, {}).get('oldest_ts')
    ]
    archive_start_dt = min((dt for dt in oldest_points if dt is not None), default=None)
    if archive_start_dt is None:
        return {
            'archive_window_started': False,
            'archive_window_start_ts': None,
            'archive_window_rows': 0,
            'archive_window_non_null': 0,
            'archive_window_coverage_pct': None,
        }

    snapshot_minute_keys = {
        minute_key
        for subtype in subtypes
        for minute_key in snapshot_stats.get(subtype, {}).get('minute_keys', [])
        if minute_key
    }

    rows_since_start = 0
    non_null_since_start = 0
    for ts_value, feature_value in zip(timestamp_values, feature_values):
        ts = _parse_sqlite_timestamp(ts_value)
        if ts is None:
            continue
        if snapshot_minute_keys:
            minute_key = _snapshot_minute_key(ts_value)
            if minute_key not in snapshot_minute_keys:
                continue
        elif ts < archive_start_dt:
            continue
        rows_since_start += 1
        if feature_value is not None:
            non_null_since_start += 1

    coverage_pct = None
    if rows_since_start > 0:
        coverage_pct = round(non_null_since_start / rows_since_start * 100.0, 2)

    return {
        'archive_window_started': True,
        'archive_window_start_ts': archive_start_dt.isoformat(),
        'archive_window_rows': rows_since_start,
        'archive_window_non_null': non_null_since_start,
        'archive_window_coverage_pct': coverage_pct,
    }


def _safe_parse_payload_json(payload_json: Any) -> Dict[str, Any]:
    if not payload_json:
        return {}
    if isinstance(payload_json, dict):
        return payload_json
    try:
        parsed = json.loads(payload_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def compute_raw_snapshot_stats(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='raw_events'"
    ).fetchone()
    if not table_exists:
        return {}

    rows = conn.execute(
        'SELECT subtype, timestamp, payload_json FROM raw_events ORDER BY subtype, timestamp, id'
    ).fetchall()
    stats: Dict[str, Dict[str, Any]] = {}
    now = datetime.now(timezone.utc)

    for subtype, ts_value, payload_json in rows:
        subtype = str(subtype)
        ts = _parse_sqlite_timestamp(ts_value)
        payload = _safe_parse_payload_json(payload_json)
        bucket = stats.setdefault(
            subtype,
            {
                'count': 0,
                'oldest_dt': None,
                'latest_dt': None,
                'latest_payload': {},
                'minute_keys': set(),
            },
        )
        bucket['count'] += 1
        if ts is not None:
            if bucket['oldest_dt'] is None or ts < bucket['oldest_dt']:
                bucket['oldest_dt'] = ts
            if bucket['latest_dt'] is None or ts >= bucket['latest_dt']:
                bucket['latest_dt'] = ts
                bucket['latest_payload'] = payload
            minute_key = _snapshot_minute_key(ts)
            if minute_key:
                bucket['minute_keys'].add(minute_key)
        elif not bucket['latest_payload']:
            bucket['latest_payload'] = payload

    normalized: Dict[str, Dict[str, Any]] = {}
    for subtype, bucket in stats.items():
        oldest_dt = bucket['oldest_dt']
        latest_dt = bucket['latest_dt']
        span_hours = None
        if oldest_dt and latest_dt:
            span_hours = round(max(0.0, (latest_dt - oldest_dt).total_seconds() / 3600.0), 2)
        age_minutes = None
        if latest_dt:
            age_minutes = round(max(0.0, (now - latest_dt).total_seconds() / 60.0), 1)
        latest_payload = bucket.get('latest_payload') or {}
        normalized[subtype] = {
            'count': int(bucket['count']),
            'oldest_ts': oldest_dt.isoformat() if oldest_dt else None,
            'latest_ts': latest_dt.isoformat() if latest_dt else None,
            'span_hours': span_hours,
            'latest_age_minutes': age_minutes,
            'latest_status': latest_payload.get('status'),
            'latest_message': latest_payload.get('message'),
            'minute_keys': sorted(bucket['minute_keys']),
        }
    return normalized


def compute_raw_snapshot_counts(conn: sqlite3.Connection) -> Dict[str, int]:
    return {
        subtype: row.get('count', 0)
        for subtype, row in compute_raw_snapshot_stats(conn).items()
    }


def attach_forward_archive_meta(clean_key: str, quality: Dict[str, Any], snapshot_counts: Dict[str, int] | None = None, snapshot_stats: Dict[str, Dict[str, Any]] | None = None) -> Dict[str, Any]:
    snapshot_counts = snapshot_counts or {}
    snapshot_stats = snapshot_stats or {}
    subtypes = list(SOURCE_SNAPSHOT_SUBTYPES.get(clean_key, ()))
    raw_snapshot_events = sum(snapshot_counts.get(subtype, 0) for subtype in subtypes)
    relevant_stats = [snapshot_stats.get(subtype, {}) for subtype in subtypes if snapshot_stats.get(subtype)]
    latest_ages = [row.get('latest_age_minutes') for row in relevant_stats if row.get('latest_age_minutes') is not None]
    spans = [row.get('span_hours') for row in relevant_stats if row.get('span_hours') is not None]
    latest_ts_values = [row.get('latest_ts') for row in relevant_stats if row.get('latest_ts')]
    oldest_ts_values = [row.get('oldest_ts') for row in relevant_stats if row.get('oldest_ts')]
    latest_statuses = [row.get('latest_status') for row in relevant_stats if row.get('latest_status')]
    latest_messages = [row.get('latest_message') for row in relevant_stats if row.get('latest_message')]
    latest_age_minutes = min(latest_ages) if latest_ages else None
    max_span_hours = max(spans) if spans else None
    latest_snapshot_ts = max(latest_ts_values) if latest_ts_values else None
    oldest_snapshot_ts = min(oldest_ts_values) if oldest_ts_values else None
    archive_started = raw_snapshot_events > 0
    archive_ready = raw_snapshot_events >= FORWARD_ARCHIVE_READY_MIN_EVENTS
    archive_stale = archive_started and latest_age_minutes is not None and latest_age_minutes > FORWARD_ARCHIVE_STALE_MINUTES
    progress_pct = 0.0
    if FORWARD_ARCHIVE_READY_MIN_EVENTS > 0:
        progress_pct = min(100.0, raw_snapshot_events / FORWARD_ARCHIVE_READY_MIN_EVENTS * 100.0)
    if archive_ready:
        archive_status = 'stale' if archive_stale else 'ready'
    elif archive_started:
        archive_status = 'stale' if archive_stale else 'building'
    else:
        archive_status = 'missing'

    enriched = dict(quality)
    enriched['raw_snapshot_subtypes'] = subtypes
    enriched['raw_snapshot_events'] = raw_snapshot_events
    enriched['raw_snapshot_latest_ts'] = latest_snapshot_ts
    enriched['raw_snapshot_oldest_ts'] = oldest_snapshot_ts
    enriched['raw_snapshot_span_hours'] = max_span_hours
    enriched['raw_snapshot_latest_age_min'] = latest_age_minutes
    enriched['raw_snapshot_latest_status'] = latest_statuses[0] if latest_statuses else None
    enriched['raw_snapshot_latest_message'] = latest_messages[0] if latest_messages else None
    enriched['forward_archive_started'] = archive_started
    enriched['forward_archive_ready'] = archive_ready
    enriched['forward_archive_stale'] = archive_stale
    enriched['forward_archive_status'] = archive_status
    enriched['forward_archive_ready_min_events'] = FORWARD_ARCHIVE_READY_MIN_EVENTS
    enriched['forward_archive_stale_after_min'] = FORWARD_ARCHIVE_STALE_MINUTES
    enriched['forward_archive_progress_pct'] = round(progress_pct, 1)

    if clean_key in SOURCE_FEATURE_KEYS:
        latest_status = enriched.get('raw_snapshot_latest_status')
        latest_message = enriched.get('raw_snapshot_latest_message')
        if latest_status == 'auth_missing':
            enriched['quality_flag'] = 'source_auth_blocked'
            enriched['quality_label'] = 'source auth missing; latest snapshots are failing'
            reasons = list(enriched.get('reasons', []))
            if 'source_auth_blocked' not in reasons:
                reasons.insert(0, 'source_auth_blocked')
            enriched['reasons'] = reasons
        elif latest_status and latest_status not in ('ok', 'missing'):
            enriched['quality_flag'] = 'source_fetch_error'
            detail = f': {latest_message}' if latest_message else ''
            enriched['quality_label'] = f'source fetch failing ({latest_status}){detail}'
            reasons = list(enriched.get('reasons', []))
            fetch_reason = f'source_fetch_error:{latest_status}'
            if fetch_reason not in reasons:
                reasons.insert(0, fetch_reason)
            enriched['reasons'] = reasons

    if clean_key in SOURCE_FEATURE_KEYS and raw_snapshot_events > 0:
        blocker = enriched.get('backfill_blocker')
        latest_status = enriched.get('raw_snapshot_latest_status')
        latest_message = enriched.get('raw_snapshot_latest_message')
        archive_window_cov = enriched.get('archive_window_coverage_pct')
        archive_window_started = bool(enriched.get('archive_window_started'))
        blocker_note = (
            f' Forward raw snapshot archive is {archive_status} '
            f'({raw_snapshot_events}/{FORWARD_ARCHIVE_READY_MIN_EVENTS} stored event(s) '
            f'across {", ".join(subtypes)}), but historical rows before the archive cutoff are still missing.'
        )
        if latest_status and latest_status != 'ok':
            blocker_note += f' Latest snapshot status={latest_status}.'
            if latest_message:
                blocker_note += f' Detail: {latest_message}'
        if archive_stale and latest_age_minutes is not None:
            blocker_note += (
                f' Latest archive event is {latest_age_minutes:.1f} minutes old, so forward collection is not progressing right now.'
            )
        if blocker and blocker_note.strip() not in blocker:
            enriched['backfill_blocker'] = blocker + blocker_note
        if latest_status == 'auth_missing':
            enriched['recommended_action'] = (
                'Configure COINGLASS_API_KEY for the CoinGlass-backed source first; forward archive events are being logged, '
                'but they currently contain auth_missing snapshots so feature coverage cannot improve until credentials work. '
                'After auth is fixed, keep running heartbeat collection until at least '
                f'{FORWARD_ARCHIVE_READY_MIN_EVENTS} successful forward snapshots accumulate, then evaluate whether historical export/backfill is still needed.'
            )
        elif latest_status and latest_status not in ('ok', 'missing'):
            detail = f' ({latest_message})' if latest_message else ''
            enriched['recommended_action'] = (
                f'Fix the current source fetch failure before treating this as a pure history gap: latest snapshot status={latest_status}{detail}. '
                f'Once snapshots succeed, keep collecting until at least {FORWARD_ARCHIVE_READY_MIN_EVENTS} forward raw snapshots accumulate, '
                'then decide whether a dedicated historical export/archive loader is still required.'
            )
        elif archive_stale and latest_age_minutes is not None:
            enriched['recommended_action'] = (
                f'Restart or re-run heartbeat collection immediately; latest snapshot archive event is '
                f'{latest_age_minutes:.1f} minutes old (stale threshold {FORWARD_ARCHIVE_STALE_MINUTES}m). '
                f'After collection resumes, keep running until at least {FORWARD_ARCHIVE_READY_MIN_EVENTS} '
                'forward raw snapshots accumulate; add historical export/API archive if you need rows before the cutoff.'
            )
        elif archive_window_started and archive_window_cov is not None and archive_window_cov >= 100.0 and not archive_ready:
            enriched['recommended_action'] = (
                'Forward recent-window coverage is already healthy, so do not reopen live-fetch debugging for this source. '
                f'Keep heartbeat collection running until at least {FORWARD_ARCHIVE_READY_MIN_EVENTS} forward raw snapshots accumulate '
                'to mature the archive span, then plan a dedicated historical export/archive loader for rows before the cutoff.'
            )
        elif archive_window_started and archive_window_cov is not None and archive_window_cov > 0.0 and not archive_ready:
            enriched['recommended_action'] = (
                f'Forward archive is partially producing recent values ({archive_window_cov:.1f}% recent-window coverage), '
                'so treat this as an active source/path quality gap instead of a pure historical gap. '
                'Keep heartbeat collection running, but inspect parser/source mapping until recent-window coverage reaches 100%; '
                f'after that, continue accumulating toward {FORWARD_ARCHIVE_READY_MIN_EVENTS} forward snapshots before deciding on historical export.'
            )
        elif archive_ready:
            enriched['recommended_action'] = (
                'Forward raw snapshot archive is ready for recent-window diagnostics; '
                'keep collection running to extend the archive span, but historical rows before the cutoff '
                'still require a dedicated export/archive loader before coverage can exceed the legacy gap.'
            )
        else:
            enriched['recommended_action'] = (
                f'Keep heartbeat collection running until at least '
                f'{FORWARD_ARCHIVE_READY_MIN_EVENTS} forward raw snapshots accumulate; '
                'add historical export/API archive if you need to backfill rows before the archive cutoff.'
            )

    return enriched


def compute_sqlite_feature_coverage(db_path: str | Path) -> Dict[str, Any]:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    snapshot_stats = compute_raw_snapshot_stats(conn)
    snapshot_counts = {subtype: row.get('count', 0) for subtype, row in snapshot_stats.items()}
    total_rows = cur.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
    available_columns = {
        row[1] for row in cur.execute("PRAGMA table_info(features_normalized)").fetchall()
    }
    ordered_timestamps = [
        row[0] for row in cur.execute('SELECT timestamp FROM features_normalized ORDER BY timestamp').fetchall()
    ]
    stats = []
    for db_key, clean_key in FEATURE_KEY_MAP.items():
        if db_key in available_columns:
            timestamp_and_values = cur.execute(
                f'SELECT timestamp, {db_key} FROM features_normalized ORDER BY timestamp'
            ).fetchall()
            timestamp_values = [row[0] for row in timestamp_and_values]
            feature_values = [row[1] for row in timestamp_and_values]
            non_null, distinct, min_v, max_v = cur.execute(
                f'SELECT COUNT({db_key}), COUNT(DISTINCT {db_key}), MIN({db_key}), MAX({db_key}) FROM features_normalized'
            ).fetchone()
        else:
            timestamp_values = ordered_timestamps
            feature_values = [None] * len(ordered_timestamps)
            non_null, distinct, min_v, max_v = 0, 0, None, None
        coverage_pct = (non_null / total_rows * 100.0) if total_rows else 0.0
        archive_window = _compute_archive_window_coverage(clean_key, timestamp_values, feature_values, snapshot_stats)
        quality = assess_feature_quality(
            clean_key,
            coverage_pct,
            distinct or 0,
            non_null,
            min_v,
            max_v,
        )
        quality.update(archive_window)
        quality = attach_forward_archive_meta(clean_key, quality, snapshot_counts, snapshot_stats)
        stats.append({
            'db_key': db_key,
            'key': clean_key,
            'non_null': non_null,
            'coverage_pct': round(coverage_pct, 2),
            'distinct': distinct or 0,
            'min': min_v,
            'max': max_v,
            **quality,
        })
    conn.close()
    stats.sort(key=lambda row: (row['chart_usable'], row['coverage_pct'], row['distinct']))
    return {
        'rows_total': total_rows,
        'usable_count': sum(1 for row in stats if row['chart_usable']),
        'hidden_count': sum(1 for row in stats if not row['chart_usable']),
        'features': stats,
    }


def build_source_blocker_summary(feature_rows: Sequence[Dict[str, Any]] | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(feature_rows, dict):
        feature_rows = feature_rows.get('features', [])
    blocked = [
        row for row in feature_rows
        if row.get('key') in SOURCE_FEATURE_KEYS and row.get('backfill_status') == 'blocked'
    ]
    counts_by_class: Dict[str, int] = {}
    for row in blocked:
        history_class = row.get('history_class', 'unknown')
        counts_by_class[history_class] = counts_by_class.get(history_class, 0) + 1
    return {
        'blocked_count': len(blocked),
        'counts_by_history_class': counts_by_class,
        'blocked_features': [
            {
                'key': row['key'],
                'coverage_pct': row.get('coverage_pct'),
                'history_class': row.get('history_class'),
                'quality_flag': row.get('quality_flag'),
                'backfill_blocker': row.get('backfill_blocker'),
                'recommended_action': row.get('recommended_action'),
                'raw_snapshot_events': row.get('raw_snapshot_events', 0),
                'raw_snapshot_latest_ts': row.get('raw_snapshot_latest_ts'),
                'raw_snapshot_oldest_ts': row.get('raw_snapshot_oldest_ts'),
                'raw_snapshot_span_hours': row.get('raw_snapshot_span_hours'),
                'raw_snapshot_latest_age_min': row.get('raw_snapshot_latest_age_min'),
                'raw_snapshot_latest_status': row.get('raw_snapshot_latest_status'),
                'raw_snapshot_latest_message': row.get('raw_snapshot_latest_message'),
                'forward_archive_started': row.get('forward_archive_started', False),
                'forward_archive_ready': row.get('forward_archive_ready', False),
                'forward_archive_stale': row.get('forward_archive_stale', False),
                'forward_archive_status': row.get('forward_archive_status', 'missing'),
                'forward_archive_ready_min_events': row.get('forward_archive_ready_min_events', FORWARD_ARCHIVE_READY_MIN_EVENTS),
                'forward_archive_stale_after_min': row.get('forward_archive_stale_after_min', FORWARD_ARCHIVE_STALE_MINUTES),
                'forward_archive_progress_pct': row.get('forward_archive_progress_pct', 0.0),
                'archive_window_started': row.get('archive_window_started', False),
                'archive_window_start_ts': row.get('archive_window_start_ts'),
                'archive_window_rows': row.get('archive_window_rows', 0),
                'archive_window_non_null': row.get('archive_window_non_null', 0),
                'archive_window_coverage_pct': row.get('archive_window_coverage_pct'),
            }
            for row in blocked
        ],
    }
