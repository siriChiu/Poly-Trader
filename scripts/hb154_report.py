"""Heartbeat #154 — Consolidated IC analysis & report generator"""
import sys, os, sqlite3, json
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

import numpy as np
import pandas as pd
from pathlib import Path

DB_PATH = Path('/home/kazuha/Poly-Trader/poly_trader.db')
db = sqlite3.connect(str(DB_PATH))

# Data counts
raw_count = db.execute("SELECT COUNT(*) FROM raw_market_data").fetchone()[0]
feat_count = db.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
label_count = db.execute("SELECT COUNT(*) FROM labels WHERE future_return_pct IS NOT NULL").fetchone()[0]

# Latest market data
close_price = db.execute("SELECT close_price FROM raw_market_data ORDER BY rowid DESC LIMIT 1").fetchone()[0]
fng = db.execute("SELECT fear_greed_index FROM raw_market_data ORDER BY rowid DESC LIMIT 1").fetchone()[0]
funding = db.execute("SELECT funding_rate FROM raw_market_data ORDER BY rowid DESC LIMIT 1").fetchone()[0]
# LSR not in schema as separate column; body_label has LSR info
body_label = db.execute("SELECT body_label FROM raw_market_data ORDER BY rowid DESC LIMIT 1").fetchone()[0]

# Load features and labels
features = pd.read_sql("SELECT * FROM features_normalized", db)
labels = pd.read_sql("SELECT id, timestamp, symbol, label_sell_win, label_up, future_return_pct FROM labels", db)
merged = pd.merge(features, labels, on=['timestamp', 'symbol'], how='inner')
db.close()

sell_win_rate = merged['label_sell_win'].mean()

# Sensory mapping
sensory_map = {}
for sense in ['eye', 'ear', 'nose', 'tongue', 'body', 'pulse', 'aura', 'mind']:
    col = f'feat_{sense}'
    if col in merged.columns:
        sensory_map[sense.capitalize()] = col

# Global IC (against label_sell_win)
global_ics = {}
for sense, col in sensory_map.items():
    ic = merged[col].corr(merged['label_sell_win'])
    global_ics[sense] = round(float(ic), 4)

# Regime-Aware IC
regime_ics = {}
for regime in ['bear', 'bull', 'chop', 'neutral']:
    mask = merged['regime_label'] == regime
    n = mask.sum()
    if n < 50:
        regime_ics[regime] = {'n': int(n), 'passed': 0, 'ics': {}}
        continue
    ics = {}
    passed = 0
    for sense, col in sensory_map.items():
        sub = merged[mask]
        ic = float(sub[col].corr(sub['label_sell_win']))
        ics[sense] = round(ic, 4)
        if abs(ic) >= 0.05:
            passed += 1
    regime_ics[regime] = {'n': int(n), 'passed': passed, 'ics': ics}

# Dynamic Window IC
dynamic_ics = {}
for window in [200, 500, 1000]:
    tail = merged.tail(window)
    passed_list = []
    for sense, col in sensory_map.items():
        ic = float(tail[col].corr(tail['label_sell_win']))
        if abs(ic) >= 0.05:
            passed_list.append(f"{sense}({ic:+.3f})")
    dynamic_ics[f"N={window}"] = f"{len(passed_list)}/8: {', '.join(passed_list) if passed_list else 'ALL FAIL'}"

# Output JSON
output = {
    "raw_count": raw_count,
    "feat_count": feat_count, 
    "label_count": label_count,
    "sell_win_rate": round(float(sell_win_rate), 4),
    "btc_price": round(float(close_price), 0) if close_price else "N/A",
    "fng": float(fng) if fng else "N/A",
    "funding_rate": float(funding) if funding else "N/A",
    "body_label": body_label,
    "global_ics": global_ics,
    "regime_ics": regime_ics,
    "dynamic_ics": dynamic_ics,
}

print(json.dumps(output, indent=2, ensure_ascii=False))
