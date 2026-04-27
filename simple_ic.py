import sqlite3  
conn = sqlite3.connect('poly_trader.db')  
c = conn.cursor()  
senses = [  
    ('eye', 'feat_eye_dist'),  
    ('ear', 'feat_ear_zscore'),  
    ('nose', 'feat_nose_sigmoid'),  
    ('tongue', 'feat_tongue_pct'),  
    ('body', 'feat_body_roc'),  
    ('pulse', 'feat_pulse'),  
    ('aura', 'feat_aura'),  
    ('mind', 'feat_mind')  
]  
for sense, col in senses:  
    c.execute('''  
        SELECT f.{} l.future_return_pct  
        FROM features_normalized f  
        JOIN labels l ON f.timestamp = l.timestamp  
        WHERE l.horizon_minutes = 240  
        ORDER BY f.timestamp DESC LIMIT 1000  
    '''.format(col))  
    rows = c.fetchall()  
    if not rows:  
        print('{}: NO DATA'.format(sense))  
        continue  
    # Simple correlation calculation  
    n = len(rows)  
    sum_x = sum(float(r[0]) for r in rows)  
    sum_y = sum(float(r[1]) for r in rows)  
    sum_xy = sum(float(r[0]) * float(r[1]) for r in rows)  
    sum_x2 = sum(float(r[0])**2 for r in rows)  
    sum_y2 = sum(float(r[1])**2 for r in rows)  
    numerator = n * sum_xy - sum_x * sum_y  
    denominator = ((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))**0.5  
    if denominator == 0:  
        ic = 0  
    else:  
        ic = numerator / denominator  
    print(f'{sense}: {ic:.4f}')  
conn.close() 
