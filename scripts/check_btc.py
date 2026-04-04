import sqlite3
import pandas as pd

conn = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')
# Check raw_market_data columns
rm = pd.read_sql_query('SELECT * FROM raw_market_data LIMIT 1', conn)
print("raw_market_data columns:", list(rm.columns))
conn.close()
