import sqlite3

db = sqlite3.connect('poly_trader.db')
import pandas as pd
feat = pd.read_sql_query('SELECT feat_ear_zscore, feat_tongue_pct FROM features_normalized', db)
print('Ear zscore:')
vals = sorted(feat["feat_ear_zscore"].unique())
print(f'  unique: {feat["feat_ear_zscore"].nunique()}')
print(f'  top 20: {vals[:20]}')
print(f'  std: {feat["feat_ear_zscore"].std():.6f}')
print()
print('Tongue pct:')
tvals = sorted(feat["feat_tongue_pct"].unique())
print(f'  unique: {feat["feat_tongue_pct"].nunique()}')
print(f'  top 20: {tvals[:20]}')
print(f'  std: {feat["feat_tongue_pct"].std():.6f}')
db.close()
