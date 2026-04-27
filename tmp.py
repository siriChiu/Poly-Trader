"import sqlite3; conn=sqlite3.connect('poly_trader.db'); c=conn.cursor(); c.execute('SELECT * FROM raw_market_data ORDER BY id DESC LIMIT 1'); row=c.fetchone(); print(row); conn.close()"  
