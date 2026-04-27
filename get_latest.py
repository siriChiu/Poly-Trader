import sqlite3  
conn = sqlite3.connect('poly_trader.db')  
c = conn.cursor()  
c.execute('SELECT COUNT(*) FROM raw_market_data')  
raw = c.fetchone()[0]  
c.execute('SELECT COUNT(*) FROM features_normalized')  
feat = c.fetchone()[0]  
c.execute('SELECT COUNT(*) FROM labels WHERE future_return_pct IS NOT NULL')  
lbl = c.fetchone()[0]  
c.execute('SELECT timestamp, close_price, fear_greed_index, funding_rate, oi_roc FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')  
row = c.fetchone()  
if row:  
    print(f'Raw: {raw:,}, Features: {feat:,}, Labels: {lbl:,}')  
    print(f'BTC , FNG: {row[2]}, Funding: {row[3]:.2e}, OI ROC: {row[4]:.4f}')  
else:  
    print('No data')  
conn.close() 
