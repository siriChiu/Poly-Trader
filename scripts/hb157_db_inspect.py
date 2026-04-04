#!/usr/bin/env python3
"""Heartbeat #157 - DB inspection for P0 analysis"""
import sqlite3, os, sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')
db = sqlite3.connect('poly_trader.db')

# Regime distribution
counts = db.execute('SELECT regime_label, COUNT(*) FROM features_normalized GROUP BY regime_label').fetchall()
print('Regime counts:', counts)

# Feature columns
cols = db.execute('PRAGMA table_info(features_normalized)').fetchall()
print('\nFeature columns:')
for c in cols:
    print(f'  {c[1]} ({c[2]})')

# Label distribution per regime
result = db.execute('''
    SELECT f.regime_label, 
           COUNT(l.label_sell_win) as total,
           SUM(l.label_sell_win) as wins,
           AVG(l.label_sell_win) as win_rate
    FROM features_normalized f
    JOIN labels l ON f.timestamp = l.timestamp
    WHERE f.regime_label IS NOT NULL AND l.label_sell_win IS NOT NULL
    GROUP BY f.regime_label
''').fetchall()
print('\nLabel distribution per regime:')
for r in result:
    print(f'  {r[0]}: total={r[1]}, wins={r[2]}, win_rate={r[3]:.3f}')

# Check VIX/DXY columns
vix_cols = [c[1] for c in cols if 'vix' in c[1].lower() or 'dxy' in c[1].lower()]
print(f'\nVIX/DXY columns: {vix_cols}')

# Raw data columns
raw_cols = db.execute('PRAGMA table_info(raw_market_data)').fetchall()
print('\nRaw data columns:')
for c in raw_cols:
    print(f'  {c[1]} ({c[2]})')

# Check models directory
models_dir = '/home/kazuha/Poly-Trader/models'
if os.path.exists(models_dir):
    print(f'\nModels dir exists: {os.listdir(models_dir)}')
else:
    print(f'\nModels dir does not exist')

# Check data/ directory for model state
import json
for f in ['regime_train_result.json', 'hb156_results.json']:
    path = f'/home/kazuha/Poly-Trader/data/{f}'
    if os.path.exists(path):
        with open(path) as fh:
            data = json.load(fh)
        print(f'\n{f} keys: {list(data.keys()) if isinstance(data, dict) else type(data)}')

# Check for existing model save paths
print('\nChecking model save logic...')
import subprocess
r = subprocess.run(['grep', '-r', 'joblib.*save\|model.*save\|save_model'], 
                   ['/home/kazuha/Poly-Trader/model/'], capture_output=True, text=True)
print('model/*.py model save patterns:', r.stdout[:500] if r.stdout else 'None found')

db.close()
