import sqlite3  
import numpy as np  
from scipy import stats  
  
conn = sqlite3.connect('poly_trader.db')  
  
senses = {  
    'pulse': 'feat_pulse',  
    'eye': 'feat_eye_dist',  
    'ear': 'feat_ear_zscore',  
    'nose': 'feat_nose_sigmoid',  
    'tongue': 'feat_tongue_pct',  
    'body': 'feat_body_roc',  
    'aura': 'feat_aura',  
    'mind': 'feat_mind',  
}  
  
for sense, col in senses.items():  
    rows = conn.execute(f'SELECT f.{col}, l.future_return_pct FROM features_normalized f JOIN labels l ON f.timestamp = l.timestamp WHERE l.horizon_minutes = 240 ORDER BY f.timestamp DESC LIMIT 1000').fetchall()  
    if not rows:  
        rows = conn.execute(f'SELECT f.{col}, l.future_return_pct FROM features_normalized f JOIN labels l ON f.timestamp = l.timestamp ORDER BY f.timestamp DESC LIMIT 1000').fetchall()  
    v = [float(r[0]) for r in rows]  
    lb = [float(r[1]) for r in rows]  
    # Filter out None/NaN values  
    pairs = [(x, y) for x, y in zip(v, lb) if x is not None and y is not None]  
