#!/usr/bin/env python3
"""Inspect DB state for heartbeat."""
import sqlite3

db_path = 'poly_trader.db'
db = sqlite3.connect(db_path)

raw_count = db.execute('SELECT COUNT(*) FROM raw_market_data').fetchone()[0]
feat_count = db.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
label_count = db.execute('SELECT COUNT(*) FROM labels WHERE future_return_pct IS NOT NULL').fetchone()[0]
print(f'Raw: {raw_count}, Features: {feat_count}, Labels: {label_count}')

# Get stats
stats = db.execute('SELECT MIN(timestamp), MAX(timestamp), COUNT(DISTINCT DATE(timestamp)) FROM raw_market_data').fetchone()
print(f'Timestamp range: {stats}')

# Get latest row
latest = db.execute('SELECT timestamp, close_price FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
print(f'Latest: {latest}')

# Get feature columns
cols_f = db.execute('SELECT * FROM features_normalized LIMIT 1').description
col_names = [c[0] for c in cols_f]
print(f'Feature columns ({len(col_names)}): {col_names}')

# Get label distribution
label_dist = db.execute('SELECT label, COUNT(*) FROM labels GROUP BY label').fetchall()
print(f'Label distribution: {label_dist}')

# Sell win count
sell_wins = db.execute('SELECT COUNT(*) FROM labels WHERE sell_win = 1').fetchone()[0]
sell_total = db.execute('SELECT COUNT(*) FROM labels WHERE sell_win IS NOT NULL').fetchone()[0]
print(f'Sell win rate: {sell_wins}/{sell_total} = {sell_wins/max(sell_total,1)*100:.1f}%')

db.close()
