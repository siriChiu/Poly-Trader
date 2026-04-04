import sqlite3

conn = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')
cursor = conn.cursor()

# Check close price distribution
cursor.execute('SELECT COUNT(*), COUNT(DISTINCT close_price) FROM raw_market_data')
row = cursor.fetchone()
print(f'close_price: Total={row[0]}, Unique={row[1]}')

# Get some sample close prices
cursor.execute('SELECT close_price FROM raw_market_data ORDER BY timestamp DESC LIMIT 20')
for row in cursor.fetchall():
    print(f'  close={row[0]}')

# Check if close price changes are continuous
cursor.execute('''
    SELECT close_price, 
           LEAD(close_price) OVER (ORDER BY timestamp) as next_close,
           close_price - LEAD(close_price) OVER (ORDER BY timestamp) as diff
    FROM raw_market_data 
    ORDER BY timestamp DESC 
    LIMIT 30
''')
print('\nclose price diffs:')
for row in cursor.fetchall():
    if row[0] is not None:
        diff = row[0] - row[2] if row[2] is not None else None
        print(f'  close={row[0]}, next={row[2]}, diff={diff}')

conn.close()
