#!/usr/bin/env python3
"""IC Analysis for Poly-Trader Heartbeat #157"""
import sqlite3
import numpy as np
from scipy.stats import pearsonr

db = sqlite3.connect("/home/kazuha/Poly-Trader/poly_trader.db")

features = db.execute('SELECT * FROM features_normalized').fetchall()
feat_cols = [desc[0] for desc in db.execute('SELECT * FROM features_normalized LIMIT 1').description]
labels = db.execute('SELECT timestamp, future_return_pct, label_spot_long_win, regime_label FROM labels WHERE future_return_pct IS NOT NULL').fetchall()
db.close()

label_map = {row[0]: (row[1], row[2], row[3]) for row in labels}

matched_feats = [f for f in features if f[feat_cols.index('timestamp')] in label_map]
n = len(matched_feats)

labels_arr = np.array([label_map[f[feat_cols.index('timestamp')]][1] for f in matched_feats])
regime_arr = [label_map[f[feat_cols.index('timestamp')]][2] for f in matched_feats]

sense_cols = [c for c in feat_cols if c.startswith('feat_')]
print(f'Matched: {n} | Sell win rate: {labels_arr.mean():.4f}')
print(f'Sense cols ({len(sense_cols)}): {sense_cols}')
print()

print('=== Global IC (h=4h) ===')
ics = {}
for col in sense_cols:
    ci = feat_cols.index(col)
    vals = np.array([float(f[ci]) if f[ci] is not None else np.nan for f in matched_feats])
    v = ~np.isnan(vals)
    if v.sum() > 100 and vals[v].std() > 1e-10:
        ic, _ = pearsonr(vals[v].astype(float), labels_arr[v].astype(float))
        ics[col] = ic
        s = 'PASS' if abs(ic) >= 0.05 else 'FAIL'
        print(f'  {col:>15s}: IC={ic:+.4f} [{s}] std={vals[v].std():.4f} uniq={len(np.unique(vals[v]))}')

print()
print('=== Regime-Aware IC ===')
rp = {}
for reg in ['Bear', 'Bull', 'Chop']:
    mask = np.array([r == reg for r in regime_arr])
    if mask.sum() < 50: continue
    rp[reg] = [0, []]
    lbl = labels_arr[mask].astype(float)
    print(f'  {reg} (n={mask.sum()}):')
    for col in sense_cols:
        ci = feat_cols.index(col)
        vals = np.array([float(f[ci]) if f[ci] is not None else np.nan for f in matched_feats])[mask]
        v = ~np.isnan(vals) & ~np.isnan(lbl)
        if v.sum() > 100 and vals[v].std() > 1e-10:
            ic, _ = pearsonr(vals[v].astype(float), lbl[v].astype(float))
            s = 'PASS' if abs(ic) >= 0.05 else 'FAIL'
            if abs(ic) >= 0.05: rp[reg][0] += 1; rp[reg][1].append(f"{col}({ic:+.4f})")
            print(f'    {col:>15s}: IC={ic:+.4f} [{s}]')

print()
for r, (c, ns) in rp.items():
    print(f'  {r}: {c}/8 => {ns}')

print()
print('=== Dynamic Window IC ===')
for N in [100, 200, 400, 600, 1000]:
    if N > n: continue
    rl = labels_arr[-N:].astype(float)
    passing, names = 0, []
    for col in sense_cols:
        ci = feat_cols.index(col)
        vals = np.array([float(f[ci]) if f[ci] is not None else np.nan for f in matched_feats])[-N:]
        v = ~np.isnan(vals) & ~np.isnan(rl)
        if v.sum() > 50 and vals[v].std() > 1e-10:
            ic, _ = pearsonr(vals[v].astype(float), rl[v].astype(float))
            if abs(ic) >= 0.05: passing += 1; names.append(f"{col}({ic:+.3f})")
    print(f'  N={N}: {passing}/{len(sense_cols)} => {names}')

print()
db2 = sqlite3.connect("/home/kazuha/Poly-Trader/poly_trader.db")
latest = db2.execute('SELECT close_price FROM raw_market_data ORDER BY rowid DESC LIMIT 1').fetchone()
prev = db2.execute('SELECT close_price FROM raw_market_data ORDER BY rowid DESC LIMIT 1 OFFSET 1').fetchone()
if latest and prev and prev[0] > 0:
    pct = (latest[0] - prev[0]) / prev[0] * 100
    print(f'BTC: ${latest[0]:,.0f} ({pct:+.2f}%)')
fng = db2.execute('SELECT fear_greed_index FROM raw_market_data ORDER BY rowid DESC LIMIT 1').fetchone()
if fng and fng[0] is not None: print(f'FNG: {int(fng[0])}')
fr = db2.execute('SELECT funding_rate FROM raw_market_data ORDER BY rowid DESC LIMIT 1').fetchone()
if fr and fr[0] is not None: print(f'Funding: {fr[0]}')
oi = db2.execute('SELECT oi_roc FROM raw_market_data ORDER BY rowid DESC LIMIT 1').fetchone()
if oi and oi[0] is not None: print(f'OI ROC: {oi[0]}')
vix = db2.execute('SELECT vix_value FROM raw_market_data ORDER BY rowid DESC LIMIT 1').fetchone()
if vix and vix[0] is not None: print(f'VIX: {vix[0]}')
dxy = db2.execute('SELECT dxy_value FROM raw_market_data ORDER BY rowid DESC LIMIT 1').fetchone()
if dxy and dxy[0] is not None: print(f'DXY: {dxy[0]}')

metrics = db2.execute('SELECT train_accuracy, cv_accuracy, cv_std, n_features, notes FROM model_metrics ORDER BY rowid DESC LIMIT 3').fetchall()
if metrics:
    print('\nRecent Models:')
    for m in metrics:
        print(f'  Train={m[0]:.4f} CV={m[1]:.4f} std={m[2]:.4f} nf={m[3]} | {m[4]}')
db2.close()
