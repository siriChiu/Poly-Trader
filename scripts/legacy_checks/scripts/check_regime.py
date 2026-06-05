import sqlite3
import pandas as pd

conn = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')
f = pd.read_sql_query('SELECT regime_label FROM features_normalized LIMIT 5', conn)
print("Sample regime_label values:")
print(f.head())
print('---')
dist = pd.read_sql_query('SELECT regime_label, COUNT(*) as cnt FROM features_normalized GROUP BY regime_label', conn)
print("Regime distribution:")
print(dist)
print('---')
r = pd.read_sql_query('SELECT close FROM raw_market_data ORDER BY id DESC LIMIT 3', conn)
print('Latest closes:', list(r['close']))
conn.close()
