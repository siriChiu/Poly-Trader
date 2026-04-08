#!/usr/bin/env python3
"""Heartbeat #218 — TW-IC + Dynamic Window + Regime analysis"""
import sys, os, json
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

import sqlite3
import numpy as np
from datetime import datetime

db = sqlite3.connect('poly_trader.db')

def tw_ic(ts, vals, labels, tau=200):
    """Time-weighted IC calculation."""
    n = len(ts)
    weights = np.exp(-np.arange(n)[::-1] / float(tau))
    v = np.array(vals, float)
    l = np.array(labels, float)
    w = weights
    mask = ~(np.isnan(v) | np.isnan(l))
    v, l, w = v[mask], l[mask]
    if len(v) < 10:
        return None
    w_sum = w.sum()
    vm = (w * v).sum() / w_sum
    lm = (w * l).sum() / w_sum
    cov = ((w * (v - vm) * (l - lm)).sum()) / w_sum
    vs = np.sqrt((w * (v - vm)**2).sum() / w_sum)
    ls = np.sqrt((w * (l - lm)**2).sum() / w_sum)
    if vs > 0 and ls > 0:
        return cov / (vs * ls)
    return 0

cols = ['feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind']
sense_names = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']

rows = db.execute(f'''SELECT f.timestamp, {', '.join(cols)}, l.label_spot_long_win
    FROM features_normalized f JOIN labels l ON l.timestamp = f.timestamp
    WHERE l.label_spot_long_win IS NOT NULL ORDER BY f.timestamp''').fetchall()

timestamps = [r[0] for r in rows]
tw_results = {}
global_results = {}

for name, idx in zip(sense_names, range(len(cols))):
    vals = [r[idx+1] for r in rows]
    lbls = [r[-1] for r in rows]
    v = np.array(vals, float)
    l = np.array(lbls, float)
    mask = ~(np.isnan(v) | np.isnan(l))
    vc, lc = v[mask], l[mask]
    
    gic = float(np.corrcoef(vc, lc)[0,1]) if len(vc) > 2 else 0
    tic = tw_ic(timestamps, vals, lbls)
    
    tw_results[name] = {'tw_ic': tic, 'global_ic': gic, 'delta': tic - gic if tic else 0}
    global_results[name] = gic

# Dynamic Window
print("=== Dynamic Window IC Analysis ===")
dw_results = {}
for wsize in [100, 200, 400, 600, 1000]:
    subset = rows[-wsize:]
    n = len(subset)
    passing = 0
    passing_list = []
    for idx, name in enumerate(sense_names):
        vals = [r[idx+1] for r in subset]
        lbls = [r[-1] for r in subset]
        v = np.array(vals, float)
        l = np.array(lbls, float)
        mask = ~(np.isnan(v) | np.isnan(l))
        vc, lc = v[mask], l[mask]
        if len(vc) > 2 and np.std(vc) > 0:
            ic = float(np.corrcoef(vc, lc)[0,1])
            if not np.isnan(ic) and abs(ic) >= 0.05:
                passing += 1
                passing_list.append(f'{name}{ic:+.2f}')
    dw_results[wsize] = {'passing': passing, 'total': 8, 'features': passing_list}
    print(f'N={wsize:4d}: {passing}/8 pass ({", ".join(passing_list[:4])})')

# Regime-wise IC
print("\n=== Regime-aware IC ===")
regime_results = {}
for regime in ['bear', 'bull', 'chop']:
    r2 = db.execute(f'''SELECT {', '.join(cols)}, l.label_spot_long_win
        FROM features_normalized f JOIN labels l ON l.timestamp = f.timestamp
        WHERE l.regime_label = '{regime}' AND l.label_spot_long_win IS NOT NULL''').fetchall()
    n_pass = 0
    key_feats = []
    for idx, name in enumerate(sense_names):
        vals = [float(r[idx]) for r in r2 if r[idx] is not None]
        lbls = [float(r[-1]) for r in r2 if r[idx] is not None]
        v, l = np.array(vals), np.array(lbls)
        if len(v) > 2 and np.std(v) > 0:
            ic = float(np.corrcoef(v, l)[0,1])
            if not np.isnan(ic) and abs(ic) >= 0.05:
                n_pass += 1
                key_feats.append(f'{name}{ic:+.3f}')
    regime_results[regime] = {'passing': n_pass, 'total': 8, 'key': key_feats}
    print(f'  {regime:8s}: {n_pass}/8 pass')

# Regime sell win rates
print("\n=== Regime Sell Win Rates ===")
r2 = db.execute('''SELECT regime_label, COUNT(*) as n,
    SUM(CASE WHEN label_spot_long_win=1 THEN 1 ELSE 0 END),
    SUM(CASE WHEN label_spot_long_win=0 THEN 1 ELSE 0 END)
    FROM labels WHERE regime_label IS NOT NULL AND label_spot_long_win IS NOT NULL
    GROUP BY regime_label''').fetchall()
for reg, n, p, neg2 in r2:
    rate = p/n if n > 0 else 0
    print(f'  {reg:10s}: {rate:.3f} ({p}/{n})')

# Global IC for extra features
print("\n=== Extra Features Global IC ===")
extra_results = {}
for name, col in [('VIX', 'feat_vix'), ('DXY', 'feat_dxy'), ('RSI14', 'feat_rsi14'),
                  ('MACD_hist', 'feat_macd_hist'), ('ATR_pct', 'feat_atr_pct'),
                  ('VWAP_dev', 'feat_vwap_dev'), ('BB_pct_b', 'feat_bb_pct_b')]:
    rows2 = db.execute(f'SELECT {col}, l.label_spot_long_win FROM features_normalized f JOIN labels l ON l.timestamp = f.timestamp WHERE l.label_spot_long_win IS NOT NULL').fetchall()
    vals = [float(r[0]) for r in rows2 if r[0] is not None]
    lbls = [float(r[1]) for r in rows2 if r[0] is not None]
    v, l = np.array(vals), np.array(lbls)
    if len(v) > 2 and np.std(v) > 0:
        ic = float(np.corrcoef(v, l)[0,1])
        extra_results[name] = {'ic': ic, 'std': float(np.std(v)), 'unique': len(set(vals))}
        print(f'  {name:12s}: IC={ic:+.4f} std={np.std(v):.4f} unique={len(set(vals))}')

# Summary stats
print("\n=== Summary ===")
raw_count = db.execute("SELECT COUNT(*) FROM raw_market_data").fetchone()[0]
feat_count = db.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
label_count = db.execute("SELECT COUNT(*) FROM labels").fetchone()[0]
pos = db.execute("SELECT COUNT(*) FROM labels WHERE label_spot_long_win=1").fetchone()[0]
neg = db.execute("SELECT COUNT(*) FROM labels WHERE label_spot_long_win=0").fetchone()[0]
raw_ts = set(r[0] for r in db.execute("SELECT timestamp FROM raw_market_data").fetchall())
feat_ts = set(r[0] for r in db.execute("SELECT timestamp FROM features_normalized").fetchall())
label_ts = set(r[0] for r in db.execute("SELECT timestamp FROM labels WHERE label_spot_long_win IS NOT NULL").fetchall())

latest = db.execute("SELECT close_price, fear_greed_index, vix_value, dxy_value, funding_rate FROM raw_market_data ORDER BY id DESC LIMIT 1").fetchone()
print(f'Raw: {raw_count} | Features: {feat_count} | Labels: {label_count}')
print(f'Gaps: RAW→Features={len(raw_ts-feat_ts)} Features→Labels={len(feat_ts-label_ts)}')
print(f'sell_win rate: {pos/(pos+neg):.4f} ({pos} pos / {neg} neg)')
print(f'BTC: ${latest[0]:,.0f} | FNG: {latest[1]} | VIX: {latest[2]} | DXY: {latest[3]} | Funding: {latest[4]}')

# Save for next heartbeat
save_data = {
    'timestamp': datetime.now().isoformat(),
    'counts': {'raw': raw_count, 'features': feat_count, 'labels': label_count},
    'gaps': {'raw_features': len(raw_ts - feat_ts), 'features_labels': len(feat_ts - label_ts)},
    'market': {'btc': latest[0], 'fng': latest[1], 'vix': latest[2], 'dxy': latest[3], 'funding': latest[4]},
    'sell_win': {'pos': pos, 'neg': neg, 'rate': pos/(pos+neg)},
    'tw_ic': tw_results,
    'global_ic': global_results,
    'extra_ic': extra_results,
    'regime_ic': regime_results,
    'dynamic_window': dw_results,
}
os.makedirs('data', exist_ok=True)
with open('data/ic_heartbeat_latest.json', 'w') as f:
    json.dump(save_data, f, indent=2)
print("\nSaved to data/ic_heartbeat_latest.json")
