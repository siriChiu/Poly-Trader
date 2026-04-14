from pathlib import Path
import sqlite3

DB = Path(__file__).resolve().parents[1] / 'poly_trader.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """
    SELECT f.timestamp,
           f.feat_4h_bias50,
           f.feat_4h_bb_pct_b,
           f.feat_4h_dist_bb_lower,
           f.feat_4h_dist_swing_low,
           f.feat_4h_ma_order,
           f.feat_4h_vol_ratio
    FROM features_normalized f
    JOIN labels l ON l.timestamp = f.timestamp AND l.symbol = f.symbol
    WHERE l.horizon_minutes = 1440
      AND l.simulated_pyramid_win IS NOT NULL
    ORDER BY l.timestamp DESC
    LIMIT 500
    """
).fetchall()

keys = [
    'feat_4h_bias50',
    'feat_4h_bb_pct_b',
    'feat_4h_dist_bb_lower',
    'feat_4h_dist_swing_low',
    'feat_4h_ma_order',
    'feat_4h_vol_ratio',
]

for k in keys:
    nulls = sum(1 for r in rows if r[k] is None)
    zeros = sum(1 for r in rows if r[k] == 0)
    print(f"{k}: nulls={nulls} zeros={zeros}")

print('\nexample rows with missing 4h projection:')
shown = 0
for r in rows:
    if any(r[k] is None for k in keys):
        print(r['timestamp'], {k: r[k] for k in keys})
        shown += 1
        if shown >= 10:
            break
