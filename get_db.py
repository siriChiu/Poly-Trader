import sqlite3  
conn = sqlite3.connect('poly_trader.db')  
c = conn.cursor()  
c.execute('SELECT COUNT(*) FROM raw_market_data')  
raw = c.fetchone()[0]  
c.execute('SELECT COUNT(*) FROM features_normalized')  
feat = c.fetchone()[0]  
c.execute('SELECT COUNT(*) FROM labels WHERE future_return_pct IS NOT NULL')  
lbl = c.fetchone()[0]  
c.execute('SELECT close_price, fear_greed_index, funding_rate, oi_roc FROM raw_market_data ORDER BY timestamp DESC LIMIT 1')  
row = c.fetchone()  
if row:  
    print(f"RAW: {raw}")  
    print(f"FEAT: {feat}")  
    print(f"LABELS: {lbl}")  
    print(f"BTC: ${row[0]}")  
    print(f"FNG: {row[1]}")  
    print(f"Funding: {row[2]}")  
    print(f"OI ROC: {row[3]}")  
else:  
    print("No data found")  
conn.close() 
