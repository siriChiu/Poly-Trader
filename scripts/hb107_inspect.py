#!/usr/bin/env python3
"""Heartbeat #107 data inspection"""
import sqlite3, json
from datetime import datetime

db = sqlite3.connect('poly_trader.db')

# Raw data count
raw = db.execute('SELECT COUNT(*) FROM raw_market_data').fetchone()[0]
feat = db.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
labels = db.execute('SELECT COUNT(*) FROM labels WHERE future_return_pct IS NOT NULL').fetchone()[0]
print(f'Raw: {raw}, Features: {feat}, Labels: {labels}')

# Label balance
pos = db.execute('SELECT COUNT(*) FROM labels WHERE sell_win = 1').fetchone()[0]
total_labels = db.execute('SELECT COUNT(*) FROM labels WHERE sell_win IS NOT NULL').fetchone()[0]
if total_labels:
    print(f'Labels balanced: {pos}/{total_labels} pos ({100*pos/total_labels:.1f}%)')
else:
    print('No sell_win labels')

# Latest BTC price
latest = db.execute('SELECT price, timestamp FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
print(f'Latest BTC: USD ${latest[0]:,.2f} at {latest[1]}')

# Funding rate stats
fr = db.execute('SELECT funding_rate FROM raw_market_data WHERE funding_rate IS NOT NULL').fetchall()
print(f'Funding rate: {len(fr)} non-null entries')

# Volume stats
vol = db.execute('SELECT volume FROM raw_market_data WHERE volume IS NOT NULL').fetchall()
print(f'Volume: {len(vol)} non-null entries')

# Fear_greed
fg = db.execute('SELECT fear_greed FROM raw_market_data WHERE fear_greed IS NOT NULL').fetchall()
print(f'Fear/Greed: {len(fg)} non-null entries')

# Polymarket
pm = db.execute('SELECT polymarket_prob FROM raw_market_data WHERE polymarket_prob IS NOT NULL').fetchall()
print(f'Polymarket: {len(pm)} non-null entries')

# Latest LSR, Taker, OI
deriv = db.execute('''
    SELECT long_short_ratio, taker_buy_sell_ratio, open_interest, funding_rate
    FROM raw_market_data 
    WHERE long_short_ratio IS NOT NULL 
    ORDER BY timestamp DESC LIMIT 1
''').fetchone()
if deriv:
    print(f'Derivatives: LSR={deriv[0]}, Taker={deriv[1]}, OI={deriv[2]}')

db.close()

# IC analysis
with open('data/ic_regime_analysis.json') as f:
    ic_data = json.load(f)
print(f'IC analysis: OK ({datetime.now().strftime("%Y-%m-%d %H:%M")})')

with open('data/ic_regime_weights.json') as f:
    weights = json.load(f)
print(f'Regime weights: {json.dumps(weights, indent=2)}')
