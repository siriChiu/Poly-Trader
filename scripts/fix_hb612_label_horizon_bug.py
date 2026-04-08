#!/usr/bin/env python3
"""Remove mislabeled 14400-minute rows created by hb_collect horizon unit bug."""
import sqlite3
from pathlib import Path

DB_PATH = Path('/home/kazuha/Poly-Trader/poly_trader.db')
BROKEN_HORIZON = 14400


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    before = cur.execute(
        'SELECT COUNT(*) FROM labels WHERE horizon_minutes = ?',
        (BROKEN_HORIZON,),
    ).fetchone()[0]
    dup_before = cur.execute(
        '''SELECT COUNT(*) FROM (
               SELECT timestamp, symbol
               FROM labels
               GROUP BY timestamp, symbol
               HAVING COUNT(*) > 1
           )'''
    ).fetchone()[0]
    print(f'broken_horizon_rows_before={before}')
    print(f'duplicate_ts_symbol_before={dup_before}')
    if before == 0:
        print('No cleanup needed.')
        conn.close()
        return 0

    cur.execute('DELETE FROM labels WHERE horizon_minutes = ?', (BROKEN_HORIZON,))
    conn.commit()

    after = cur.execute(
        'SELECT COUNT(*) FROM labels WHERE horizon_minutes = ?',
        (BROKEN_HORIZON,),
    ).fetchone()[0]
    dup_after = cur.execute(
        '''SELECT COUNT(*) FROM (
               SELECT timestamp, symbol
               FROM labels
               GROUP BY timestamp, symbol
               HAVING COUNT(*) > 1
           )'''
    ).fetchone()[0]
    horizon_counts = cur.execute(
        'SELECT horizon_minutes, COUNT(*) FROM labels GROUP BY horizon_minutes ORDER BY horizon_minutes'
    ).fetchall()
    print(f'broken_horizon_rows_after={after}')
    print(f'duplicate_ts_symbol_after={dup_after}')
    print(f'horizon_counts_after={horizon_counts}')
    conn.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
