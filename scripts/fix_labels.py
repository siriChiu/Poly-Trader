#!/usr/bin/env python
"""Fix labels: compute proper 4h (240min) forward-looking labels with max_drawdown/runup."""
import sqlite3
import pandas as pd
import numpy as np
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'poly_trader.db')
HORIZON_MINUTES = 240  # 4 hours

conn = sqlite3.connect(DB_PATH)

# Load price data
df = pd.read_sql_query('SELECT timestamp, close_price FROM raw_market_data ORDER BY timestamp ASC', conn)
df['close_price'] = pd.to_numeric(df['close_price'], errors='coerce')
df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')

print(f"Loaded {len(df)} rows")
print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Compute forward-looking labels
# For each timestamp, look HORIZON_MINUTES ahead
interval_minutes = 60  # Assuming 1h intervals based on klines
lookahead_rows = HORIZON_MINUTES // interval_minutes  # 4 rows ahead

results = []
for i in range(len(df)):
    ts = df.iloc[i]['timestamp']
    current_price = df.iloc[i]['close_price']
    
    fidx = i + lookahead_rows
    if fidx >= len(df):
        # Near end of data - can't compute forward return
        future_ret = None
        max_dd = None
        max_ru = None
    else:
        # Future price
        future_row = df.iloc[fidx]
        future_price = future_row['close_price']
        future_ret = (future_price - current_price) / current_price
        
        # Max drawdown and runup in the lookahead window
        window_prices = df.iloc[i:fidx+1]['close_price'].dropna().values
        if len(window_prices) > 1:
            # Max drawdown: max peak-to-trough decline
            peak = window_prices[0]
            max_dd = 0
            for p in window_prices[1:]:
                if p > peak:
                    peak = p
                dd = (p - peak) / peak
                if dd < max_dd:
                    max_dd = dd
            
            # Max runup: max trough-to-peak gain
            trough = window_prices[0]
            max_ru = 0
            for p in window_prices[1:]:
                if p < trough:
                    trough = p
                ru = (p - trough) / trough
                if ru > max_ru:
                    max_ru = ru
        else:
            max_dd = 0
            max_ru = 0
    
    # label_up: 1 if future return > 0, else 0
    label_up = 1 if future_ret is not None and future_ret > 0 else 0
    if future_ret is None:
        label_up = 0  # Unknown
    
    # label_sell_win: 1 if max_runup > abs(max_drawdown), else 0
    if max_dd is not None and max_ru is not None:
        label_sell_win = 1 if max_ru > abs(max_dd) else 0
    else:
        label_sell_win = 0
    
    results.append({
        'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
        'horizon_minutes': HORIZON_MINUTES,
        'future_return_pct': future_ret,
        'future_max_drawdown': max_dd,
        'future_max_runup': max_ru,
        'label_up': label_up,
        'label_sell_win': label_sell_win,
        'regime_label': 'neutral'
    })

print(f"Computed {len(results)} label sets")

# Stats
ret_vals = [r['future_return_pct'] for r in results if r['future_return_pct'] is not None]
dd_vals = [r['future_max_drawdown'] for r in results if r['future_max_drawdown'] is not None]
ru_vals = [r['future_max_runup'] for r in results if r['future_max_runup'] is not None]

print(f"Future returns: avg={np.mean(ret_vals):.4f}, std={np.std(ret_vals):.4f}")
print(f"Max drawdowns: avg={np.mean(dd_vals):.4f}, max={max(dd_vals):.4f}")
print(f"Max runups: avg={np.mean(ru_vals):.4f}, max={max(ru_vals):.4f}")
print(f"label_up: {sum(r['label_up'] for r in results)} / {len(results)}")
print(f"label_sell_win: {sum(r['label_sell_win'] for r in results)} / {len(results)}")

# Update DB
cur = conn.cursor()
cur.execute('DELETE FROM labels')

for r in results:
    cur.execute('''INSERT INTO labels 
        (timestamp, symbol, horizon_minutes, future_return_pct, future_max_drawdown, 
         future_max_runup, label_sell_win, label_up, regime_label)
        VALUES (?, 'BTCUSDT', ?, ?, ?, ?, ?, ?, ?)''',
        (r['timestamp'], r['horizon_minutes'], r['future_return_pct'],
         r['future_max_drawdown'], r['future_max_runup'], r['label_sell_win'],
         r['label_up'], r['regime_label']))

conn.commit()
cur.execute('SELECT COUNT(*) FROM labels')
print(f"\nLabels in DB: {cur.fetchone()[0]}")
conn.close()
print("Labels updated successfully!")
