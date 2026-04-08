#!/usr/bin/env python3
"""Generate feature coverage / distinctness report for chartable features."""

from __future__ import annotations

from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from feature_engine.feature_history_policy import compute_sqlite_feature_coverage

DB_PATH = PROJECT_ROOT / 'poly_trader.db'
OUT_JSON = Path('/home/kazuha/Poly-Trader/data/feature_coverage_report.json')
OUT_MD = Path('/home/kazuha/Poly-Trader/data/feature_coverage_report.md')


def main() -> int:
    payload = compute_sqlite_feature_coverage(DB_PATH)
    total_rows = payload['rows_total']
    stats = payload['features']
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')

    lines = [
        '# Feature Coverage Report',
        '',
        f'- Total rows: **{total_rows}**',
        f'- Chart-usable: **{payload["usable_count"]}**',
        f'- Hidden by default: **{payload["hidden_count"]}**',
        '',
        '| Feature | Coverage | Archive-window coverage | Distinct | Chart usable | Quality | History policy | Forward archive | Freshness | Next action |',
        '|---|---:|---:|---:|---|---|---|---|---|---|',
    ]
    for row in stats:
        notes = ', '.join(row['reasons']) if row['reasons'] else 'ok'
        history_policy = row.get('history_class', 'native_timeseries')
        archive_note = 'n/a'
        if row.get('raw_snapshot_subtypes'):
            archive_note = (
                f"{row.get('raw_snapshot_events', 0)}/{row.get('forward_archive_ready_min_events', 10)} "
                f"{row.get('forward_archive_status', 'missing')}"
                f" ({'/'.join(row['raw_snapshot_subtypes'])})"
            )
            latest_status = row.get('raw_snapshot_latest_status')
            if latest_status and latest_status != 'ok':
                archive_note += f" · status={latest_status}"
                if row.get('raw_snapshot_latest_message'):
                    archive_note += f" ({row['raw_snapshot_latest_message']})"
        freshness = 'n/a'
        if row.get('raw_snapshot_events'):
            freshness = (
                f"age={row.get('raw_snapshot_latest_age_min', 'n/a')}m"
                f" / span={row.get('raw_snapshot_span_hours', 'n/a')}h"
            )
        next_action = row.get('recommended_action') or notes
        archive_window = 'n/a'
        if row.get('archive_window_started'):
            coverage = row.get('archive_window_coverage_pct')
            if coverage is None:
                archive_window = f"0/{row.get('archive_window_rows', 0)}"
            else:
                archive_window = (
                    f"{coverage:.2f}% "
                    f"({row.get('archive_window_non_null', 0)}/{row.get('archive_window_rows', 0)})"
                )
        lines.append(
            f"| {row['key']} | {row['coverage_pct']:.2f}% | {archive_window} | {row['distinct']} | {'✅' if row['chart_usable'] else '❌'} | {row['quality_flag']} | {history_policy} | {archive_note} | {freshness} | {next_action} |"
        )
    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f'\nSaved JSON to {OUT_JSON}')
    print(f'Saved Markdown to {OUT_MD}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
