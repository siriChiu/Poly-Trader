import sqlite3  
conn = sqlite3.connect('poly_trader.db')  
c = conn.cursor()  
c.execute('SELECT COUNT(*) FROM raw_market_data')  
raw = c.fetchone()[0]  
c.execute('SELECT COUNT(*) FROM features_normalized')  
feat = c.fetchone()[0]  
c.execute('SELECT COUNT(*) FROM labels WHERE future_return_pct IS NOT NULL')  
lbl = c.fetchone()[0]  
print(f'raw: {raw}, features: {feat}, labels: {lbl}')  
conn.close()  
