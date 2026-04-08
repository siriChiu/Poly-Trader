#!/usr/bin/env python3
"""Heartbeat Step 1 & 2: Data collection + IC analysis"""
import sys, os
os.chdir('/home/kazuha/Poly-Trader')
sys.path.insert(0, '/home/kazuha/Poly-Trader')

import sqlite3, json
import numpy as np, pandas as pd
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score

db = sqlite3.connect('poly_trader.db')

# ============ STEP 1: DATA COLLECTION ============
raw_count = db.execute('SELECT COUNT(*) FROM raw_market_data').fetchone()[0]
feat_count = db.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
label_count = db.execute('SELECT COUNT(*) FROM labels WHERE future_return_pct IS NOT NULL').fetchone()[0]

# Check actual column names
feat_cols_info = db.execute('PRAGMA table_info(features_normalized)').fetchall()
feat_col_names = [c[1] for c in feat_cols_info]
print(f"Feature columns: {feat_col_names}")

# Find close_price variant
btc_col = None
for c in feat_col_names:
    if 'close' in c.lower() or 'price' in c.lower():
        btc_col = c
        break

# Join features and labels
select_cols = ['f.' + c for c in feat_col_names if c not in ('close_price',)]
if btc_col and btc_col != 'close_price':
    select_cols = ['f.' + c for c in feat_col_names]

query = f'''
    SELECT f.*, l.horizon_minutes, l.future_return_pct, l.future_max_drawdown,
           l.future_max_runup, l.label_spot_long_win, l.label_up, l.regime_label as label_regime
    FROM features_normalized f
    INNER JOIN labels l ON f.id = l.id
'''
df = pd.read_sql_query(query, db)
print(f"Merged: {len(df)} rows, {len(df.columns)} cols")

y = df['label_spot_long_win'].astype(float)
print(f"sell_win pos rate: {y.mean()*100:.1f}%")

# BTC from live data
with open('data/live_market_data.json') as f:
    lm = json.load(f)
btc_live = lm['btc_price']
print(f"BTC live: ${btc_live}")
print(f"FNG: {lm['fear_greed']} ({lm['fear_greed_label']})")
print(f"LSR: {lm['long_short_ratio']}, OI: {lm['open_interest']}")
print(f"Funding: {lm['funding_rate']}, Taker B/S: {lm['taker_buy_sell_ratio']}")

# ============ STEP 2: SENSORY IC ANALYSIS ============
SENSE_MAP = {
    'Eye': 'feat_eye', 'Ear': 'feat_ear', 'Nose': 'feat_nose',
    'Tongue': 'feat_tongue', 'Body': 'feat_body', 'Pulse': 'feat_pulse',
    'Aura': 'feat_aura', 'Mind': 'feat_mind',
}

y_c = y - y.mean()

print(f"\n=== FULL IC (vs sell_win) ===")
passing_full = 0
ics_full = {}
for sense, col in SENSE_MAP.items():
    x = df[col].astype(float)
    s = x.std()
    if s > 0 and len(x) > 2:
        ic = float(np.corrcoef(x, y_c)[0, 1])
    else:
        ic = 0.0
    ics_full[sense] = ic
    status = "✅" if abs(ic) >= 0.05 else "❌"
    if abs(ic) >= 0.05: passing_full += 1
    print(f"  {sense:8s}: {ic:+.4f} {status}")
print(f"Passing: {passing_full}/8")

# Regime-aware - get price from raw_market_data to sort
raw_df = pd.read_sql_query('SELECT id, close_price FROM raw_market_data ORDER BY id', db)
# Merge price into our dataframe
if 'id' in df.columns and 'close_price' in raw_df.columns:
    df_with_price = df.merge(raw_df[['id', 'close_price']], on='id', how='left')
    price_col = 'close_price'
    print(f"Using close_price for regime sorting, {df_with_price[price_col].notna().sum()} values")
else:
    df_with_price = df
    price_col = df_with_price.columns[0]  # fallback
    print(f"WARNING: No price column, using {price_col} for fake regime split")

sorted_df = df_with_price.sort_values(by=price_col)
n = len(sorted_df); third = n // 3
bear = sorted_df.iloc[:third]; chop = sorted_df.iloc[third:2*third]; bull = sorted_df.iloc[2*third:]

print(f"\n=== REGIME-AWARE IC ===")
bear_p = bull_p = chop_p = 0
ics_regime = {}
for sense, col in SENSE_MAP.items():
    regs = {}
    for nm, sub in [('Bear', bear), ('Bull', bull), ('Chop', chop)]:
        ys = sub['label_spot_long_win'].astype(float)
        yc = ys - ys.mean()
        xs = sub[col].astype(float)
        ic = float(np.corrcoef(xs, yc)[0, 1]) if xs.std() > 0 and len(xs) > 2 else 0.0
        regs[nm] = ic
        if abs(ic) >= 0.05:
            if nm == 'Bear': bear_p += 1
            elif nm == 'Bull': bull_p += 1
            else: chop_p += 1
    ics_regime[sense] = regs
    bm = "✅" if abs(regs['Bear']) >= 0.05 else "❌"
    um = "✅" if abs(regs['Bull']) >= 0.05 else "❌"
    cm = "✅" if abs(regs['Chop']) >= 0.05 else "❌"
    print(f"  {sense:8s}: Bear {regs['Bear']:+.4f} {bm} | Bull {regs['Bull']:+.4f} {um} | Chop {regs['Chop']:+.4f} {cm}")
print(f"Bear={bear_p}/8, Bull={bull_p}/8, Chop={chop_p}/8")

# Dynamic windows
print(f"\n=== DYNAMIC WINDOW IC ===")
dyn_ics = {}
for w in [500, 1000, 2000, 3000, 5000]:
    rec = df.tail(w)
    if len(rec) < 3: continue
    yw = rec['label_spot_long_win'].astype(float)
    ycw = yw - yw.mean()
    pw = 0
    ics_w = {}
    for sense, col in SENSE_MAP.items():
        xw = rec[col].astype(float)
        ic = float(np.corrcoef(xw, ycw)[0, 1]) if xw.std() > 0 else 0.0
        ics_w[sense] = ic
        if abs(ic) >= 0.05: pw += 1
    dyn_ics[w] = ics_w
    print(f"  N={w}: {pw}/8 passing")

# Model CV
sense_cols = list(SENSE_MAP.values())
X = df[sense_cols].fillna(0)
y_bin = df['label_spot_long_win'].astype(int)

lr = LogisticRegression(max_iter=1000, random_state=42)
cv_acc = cross_val_score(lr, X, y_bin, cv=5, scoring='accuracy')
print(f"\n=== MODEL CV ===")
print(f"  LR: {cv_acc.mean()*100:.1f}% +/- {cv_acc.std()*100:.1f}%")

weights = []
for col in sense_cols:
    x = df[col].astype(float)
    ic = abs(float(np.corrcoef(x, y_c)[0, 1])) if x.std() > 0 else 0.0
    weights.append(max(ic, 0.001))
weights = np.array(weights)
weights = weights / weights.sum()

fused = (df[sense_cols].fillna(0).values * weights).sum(axis=1)
threshold = np.median(fused)
preds = (fused > threshold).astype(float)
ic_fus_acc = accuracy_score(y_bin, preds)
print(f"  IC-Fusion: {ic_fus_acc*100:.1f}%")

# Recent model metrics
metrics = db.execute('SELECT * FROM model_metrics ORDER BY id DESC LIMIT 3').fetchall()
if metrics:
    print(f"\n=== Recent Model Metrics ===")
    cols_m = [d[1] for d in db.execute('PRAGMA table_info(model_metrics)').fetchall()]
    for m in metrics:
        d = dict(zip(cols_m, m))
        print(f"  CV={d.get('cv_accuracy','?')}, train={d.get('train_accuracy','?')}")

# Save
results = {
    'timestamp': datetime.now().isoformat(),
    'raw_count': raw_count, 'feat_count': feat_count, 'label_count': len(df),
    'label_pos': int(y_bin.sum()), 'label_neg': int(len(y_bin) - y_bin.sum()),
    'btc_price': float(btc_live),
    'ics_full': {s: round(v, 4) for s, v in ics_full.items()},
    'ics_regime': {s: {k: round(v, 4) for k, v in d.items()} for s, d in ics_regime.items()},
    'regime_passing': {'bear': bear_p, 'bull': bull_p, 'chop': chop_p},
    'lr_cv': round(cv_acc.mean(), 4), 'ic_fusion': round(ic_fus_acc, 4),
    'dyn_ics': {str(k): {s: round(v, 4) for s, v in d.items()} for k, d in dyn_ics.items()},
}
with open('data/hb168_results.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nSaved to data/hb168_results.json")
db.close()
