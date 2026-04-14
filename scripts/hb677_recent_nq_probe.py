#!/usr/bin/env python3
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
conn = sqlite3.connect(ROOT / 'poly_trader.db')
conn.row_factory = sqlite3.Row
rows = conn.execute(
    '''
    SELECT f.timestamp,
           f.feat_nq_return_1h,
           f.feat_nq_return_24h,
           r.nq_value,
           r.vix_value,
           r.dxy_value,
           l.simulated_pyramid_win,
           l.simulated_pyramid_pnl,
           l.simulated_pyramid_quality,
           f.regime_label
    FROM features_normalized f
    JOIN labels l
      ON l.timestamp = f.timestamp AND l.symbol = f.symbol AND l.horizon_minutes = 1440
    LEFT JOIN raw_market_data r
      ON r.timestamp = f.timestamp AND r.symbol = f.symbol
    ORDER BY f.timestamp DESC
    LIMIT 120
    '''
).fetchall()

zero_1h = sum(1 for r in rows if r['feat_nq_return_1h'] == 0.0)
zero_24h = sum(1 for r in rows if r['feat_nq_return_24h'] == 0.0)
null_raw = sum(1 for r in rows if r['nq_value'] is None)
print(f'rows={len(rows)} zero_1h={zero_1h} zero_24h={zero_24h} null_raw={null_raw}')
for r in rows[:10]:
    print(dict(r))
