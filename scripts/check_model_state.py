#!/usr/bin/env python3
"""Get CV accuracy, model info, and recent trade data"""
import json, os, sys
import sqlite3

DB = '/home/kazuha/Poly-Trader/poly_trader.db'
db = sqlite3.connect(DB)

# Check for training metrics (CV accuracy)
metrics_files = [
    '/home/kazuha/Poly-Trader/model/last_metrics.json',
    '/home/kazuha/Poly-Trader/data/cv_results.json',
    '/home/kazuha/Poly-Trader/.metrics.json',
]
for f in metrics_files:
    if os.path.exists(f):
        with open(f) as fh:
            print(f"\n=== {f} ===")
            print(fh.read()[:500])

# Check for model files
try:
    import glob
    model_files = glob.glob('/home/kazuha/Poly-Trader/model/*.json') + \
                  glob.glob('/home/kazuha/Poly-Trader/model/*.pkl') + \
                  glob.glob('/home/kazuha/Poly-Trader/model/*.joblib') + \
                  glob.glob('/home/kazuha/Poly-Trader/model/*.txt')
    for mf in sorted(model_files):
        size = os.path.getsize(mf)
        print(f"Model file: {os.path.basename(mf)} ({size} bytes)")
except Exception as e:
    print(f"Model dir check error: {e}")

# Trade history
trade_count = db.execute("SELECT COUNT(*) FROM trade_history").fetchone()[0]
print(f"\nTrade history: {trade_count} trades")
if trade_count > 0:
    sells = db.execute("SELECT sell_win FROM trade_history WHERE sell_win IS NOT NULL").fetchall()
    if sells:
        wins = sum(1 for r in sells if r[0] == 1)
        total = len(sells)
        print(f"Sell win rate: {wins}/{total} = {wins/total*100:.1f}%")

# Check recent labels
recent_labels = db.execute("SELECT timestamp, label_sell_win FROM labels ORDER BY id DESC LIMIT 20").fetchall()
if recent_labels:
    n_pos = sum(1 for r in recent_labels if r[1] == 1)
    print(f"\nRecent 20 labels: {n_pos} pos / {20-n_pos} neg")

db.close()
