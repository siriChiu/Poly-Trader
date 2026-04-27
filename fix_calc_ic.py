import sqlite3  
import numpy as np  
from scipy import stats  
conn = sqlite3.connect('poly_trader.db')  
c = conn.cursor()  
senses = [('eye', 'feat_eye'), ('ear', 'feat_ear'), ('nose', 'feat_nose'), ('tongue', 'feat_tongue'), ('body', 'feat_body'), ('pulse', 'feat_pulse'), ('aura', 'feat_aura'), ('mind', 'feat_mind')]  
print('\n--- IC with h=240 labels, recent 1000 ---')  
for sense, col in senses:  
    c.execute(f'SELECT f.{col}, l.future_return_pct FROM features_normalized f JOIN labels l ON f.timestamp = l.timestamp WHERE l.horizon_minutes = 240 ORDER BY f.timestamp DESC LIMIT 1000')  
    rows = c.fetchall()  
    if not rows:  
        print(f'  {sense}: NO DATA for h=240')  
        continue  
    v = np.array([float(r[0]) for r in rows])  
    lb = np.array([float(r[1]) for r in rows])  
    ic, pval = stats.spearmanr(v, lb)  
    print(f'  {sense}: IC={ic:.4f}, p={pval:.4f}')  
conn.close() 
