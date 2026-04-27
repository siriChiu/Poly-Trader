import sqlite3  
import numpy as np  
from scipy import stats  
  
def calculate_ic_for_horizon(horizon_minutes):  
    conn = sqlite3.connect('poly_trader.db')  
    c = conn.cursor()  
  
    senses = [('eye', 'feat_eye'), ('ear', 'feat_ear'), ('nose', 'feat_nose'),  
             ('tongue', 'feat_tongue'), ('body', 'feat_body')]  
  
    print('\\n--- IC with h=' + str(horizon_minutes) + ' labels, recent 1000 ---')  
    for sense, col in senses:  
        query = 'SELECT f.' + col + ', l.future_return_pct FROM features_normalized f JOIN labels l ON f.timestamp = l.timestamp WHERE l.horizon_minutes = ' + str(horizon_minutes) + ' ORDER BY f.timestamp DESC LIMIT 1000'  
        c.execute(query)  
        rows = c.fetchall()  
        if not rows:  
            print('  ' + sense + ': NO DATA for h=' + str(horizon_minutes))  
            continue  
        v = [float(r[0]) for r in rows]  
        lb = [float(r[1]) for r in rows]  
