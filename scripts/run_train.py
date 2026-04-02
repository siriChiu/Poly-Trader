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

from model.train import run_training, calc_and_save_ic_signs
print("Calculating IC signs...")
calc_and_save_ic_signs(session)
print("Training model...")
result = run_training(session)
print(f"Training result: {result}")

import sqlite3, json
conn = sqlite3.connect('/home/admin/.openclaw/workspace/Poly-Trader/poly_trader.db')
c = conn.cursor()
row = c.execute("SELECT train_accuracy, cv_accuracy, cv_std, timestamp FROM model_metrics ORDER BY timestamp DESC LIMIT 1").fetchone()
if row:
    print(f"Train={row[0]*100:.2f}%, CV={row[1]*100:.2f}%±{row[2]*100:.2f}% @ {row[3]}")
conn.close()
