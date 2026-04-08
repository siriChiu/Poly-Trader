#!/usr/bin/env python
"""Check raw data completeness - which columns have actual data vs NULL."""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'poly_trader.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Check all columns for completeness
cols = ['id', 'timestamp', 'symbol', 'close_price', 'volume', 
        'funding_rate', 'fear_greed_index', 'stablecoin_mcap', 
        'polymarket_prob', 'eye_dist', 'ear_prob', 
        'tongue_sentiment', 'volatility', 'oi_roc', 'body_label']

print("=== Raw Market Data Column Completeness ===")
for col in cols:
    cur.execute(f'SELECT COUNT({col}), COUNT(*) FROM raw_market_data')
    row = cur.fetchone()
    pct = row[0] / row[1] * 100 if row[1] > 0 else 0
    cur.execute(f'SELECT {col} FROM raw_market_data WHERE {col} IS NOT NULL AND {col} != 0 LIMIT 2',)
    sample = cur.fetchall()
    print(f"  {col}: {row[0]}/{row[1]} ({pct:.1f}%) non-null, samples: {sample}")

conn.close()
