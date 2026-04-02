"""
Standalone model training script (no server needed)
"""
import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/Poly-Trader')

from database.models import init_db
import json

with open('/home/admin/.openclaw/workspace/Poly-Trader/config.json') as f:
    cfg = json.load(f)

session = init_db(cfg.get('database', {}).get('url', 'sqlite:///poly_trader.db'))

from model.train import run_training
# IC signs are calculated inside run_training (dynamic IC in train.py)
print("Training model (IC signs computed inside training)...")
result = run_training(session)
print(f"Training result: {result}")

import sqlite3, json as _json
conn = sqlite3.connect('/home/admin/.openclaw/workspace/Poly-Trader/poly_trader.db')
c = conn.cursor()
row = c.execute("SELECT train_accuracy, cv_accuracy, cv_std, timestamp FROM model_metrics ORDER BY timestamp DESC LIMIT 1").fetchone()
if row:
    print(f"Train={row[0]*100:.2f}%, CV={row[1]*100:.2f}%±{row[2]*100:.2f}% @ {row[3]}")
    # Also update last_metrics.json
    raw_cnt = conn.execute('SELECT COUNT(*) FROM raw_market_data').fetchone()[0]
    feat_cnt = conn.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
    n_features = conn.execute('SELECT n_features FROM model_metrics ORDER BY timestamp DESC LIMIT 1').fetchone()
    metrics = {
        'train_accuracy': row[0],
        'cv_accuracy': row[1],
        'cv_std': row[2],
        'n_samples': raw_cnt,
        'n_features': n_features[0] if n_features else 32,
        'trained_at': row[3]
    }
    with open('/home/admin/.openclaw/workspace/Poly-Trader/model/last_metrics.json', 'w') as f:
        _json.dump(metrics, f, indent=2)
    print(f"Updated last_metrics.json (raw={raw_cnt}, feat={feat_cnt})")
conn.close()
