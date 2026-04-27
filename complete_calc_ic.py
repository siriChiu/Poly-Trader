import sqlite3  
import numpy as np  
from scipy import stats  
  
def calculate_ic_for_horizon(horizon_minutes):  
    conn = sqlite3.connect('poly_trader.db')  
    c = conn.cursor()  
  
    # Map sense names to actual column names in features_normalized  
    senses = [('eye', 'feat_eye'), ('ear', 'feat_ear'), ('nose', 'feat_nose'),  
             ('tongue', 'feat_tongue'), ('body', 'feat_body')]  
  
    print(f'\n--- IC with h={horizon_minutes} labels, recent 1000 ---')  
    for sense, col in senses:  
        c.execute(f'SELECT f.{{col}}, l.future_return_pct FROM features_normalized f JOIN labels l ON f.timestamp = l.timestamp WHERE l.horizon_minutes = {{horizon_minutes}} ORDER BY f.timestamp DESC LIMIT 1000')  
        rows = c.fetchall()  
        if not rows:  
            print(f'  {{sense}}: NO DATA for h={{horizon_minutes}}')  
            continue  
        v = np.array([float(r[0]) for r in rows])  
        lb = np.array([float(r[1]) for r in rows])  
        # Check if we have valid data (not all same values)  

