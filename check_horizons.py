import sqlite3  
conn = sqlite3.connect('poly_trader.db')  
c = conn.cursor()  
c.execute('SELECT DISTINCT horizon_minutes FROM labels')  
rows = c.fetchall()  
print('Horizon minutes:', [row[0] for row in rows])  
conn.close()  
