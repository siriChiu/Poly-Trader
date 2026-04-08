#!/usr/bin/env python3
"""HB#191 - Full IC & market data analysis"""
import sqlite3, os
os.chdir('/home/kazuha/Poly-Trader')
db = sqlite3.connect('poly_trader.db')

# Features schema
cols = db.execute('PRAGMA table_info(features_normalized)').fetchall()
all_feat = [c[1] for c in cols]
print('=== features_normalized columns ===')
for c in all_feat:
    print(f'  {c}')

# Raw schema
cols2 = db.execute('PRAGMA table_info(raw_market_data)').fetchall()
print('\n=== raw_market_data columns ===')
for c in cols2:
    print(f'  {c}')

# Latest raw
latest = db.execute('SELECT * FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
print(f'\n=== Latest raw row ===')
print(f'  {[c[0] for c in cols2]}')
print(f'  {latest}')

# Sell win rate
r = db.execute('SELECT COUNT(*), AVG(label_spot_long_win) FROM labels WHERE label_spot_long_win IS NOT NULL').fetchone()
print(f'\nTotal labels (non-null sell_win): {r[0]}, sell_win rate: {r[1]:.4f}')

# Recent sell_win (last 500)
r2 = db.execute('SELECT label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id DESC LIMIT 500').fetchall()
if r2:
    recent_win = sum(x[0] for x in r2) / len(r2)
    print(f'Recent sell_win (last 500): {recent_win:.4f}')

# Recent sell_win (last 100)
r3 = db.execute('SELECT label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id DESC LIMIT 100').fetchall()
if r3:
    recent100 = sum(x[0] for x in r3) / len(r3)
    print(f'Recent sell_win (last 100): {recent100:.4f}')

# VIX latest
try:
    vix = db.execute('SELECT feat_vix FROM features_normalized WHERE feat_vix IS NOT NULL ORDER BY timestamp DESC LIMIT 1').fetchone()
    if vix: print(f'Latest VIX: {vix[0]}')
except: print('VIX query failed')

# Ear zscore / tongue pct check
if 'feat_ear_zscore' in all_feat:
    ear_z = db.execute('SELECT COUNT(DISTINCT feat_ear_zscore), feat_ear_zscore FROM features_normalized WHERE feat_ear_zscore IS NOT NULL GROUP BY feat_ear_zscore').fetchall()
    print(f'Ear zscore unique: {len(ear_z)}, values: {[x[1] for x in ear_z[:10]]}')
else:
    print('feat_ear_zscore not in schema')

if 'feat_tongue_pct' in all_feat:
    tp = db.execute('SELECT COUNT(DISTINCT feat_tongue_pct), feat_tongue_pct FROM features_normalized WHERE feat_tongue_pct IS NOT NULL GROUP BY feat_tongue_pct').fetchall()
    print(f'Tongue pct unique: {len(tp)}, values: {[x[1] for x in tp[:10]]}')
else:
    print('feat_tongue_pct not in schema')

# Regime-aware IC for 8 senses + TI features
import numpy as np
senses = ['feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind']
ti_feats = ['feat_rsi14', 'feat_macd_hist', 'feat_atr_pct', 'feat_vwap_dev', 'feat_bb_pct_b']
all_feats = senses + ti_feats

feat_rows = db.execute(f'SELECT timestamp, regime_label, {", ".join(all_feats)} FROM features_normalized ORDER BY timestamp').fetchall()
label_rows = db.execute('SELECT timestamp, label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL').fetchall()
label_map = {r[0]: r[1] for r in label_rows}

# Build data
ts_list = []
data = {f: [] for f in all_feats}
regime_map = {}
for row in feat_rows:
    ts, regime = row[0], row[1]
    ts_list.append(ts)
    regime_map[ts] = regime
    for i, f in enumerate(all_feats):
        data[f].append(row[i+2] if row[i+2] is not None else np.nan)

# Global IC against sell_win
print('\n=== GLOBAL IC (sell_win) ===')
for f in all_feats:
    fv = np.array(data[f])
    mf, ml = [], []
    for i, ts in enumerate(ts_list):
        if ts in label_map and not np.isnan(fv[i]):
            mf.append(fv[i])
            ml.append(label_map[ts])
    mf, ml = np.array(mf), np.array(ml)
    if len(mf) < 100:
        continue
    std_val = np.std(mf)
    unique = len(np.unique(mf))
    if std_val < 1e-10:
        ic = 0
    else:
        c = np.corrcoef(mf, ml)
        ic = c[0,1] if np.isfinite(c[0,1]) else 0
    status = 'PASS' if abs(ic) >= 0.05 else 'FAIL'
    print(f'  {f:20s}: IC={ic:+.4f}  std={std_val:.6f}  unique={unique}  n={len(mf)}  [{status}]')

# Regime IC
for regime in ['bear', 'bull', 'chop']:
    ts_set = set(ts for ts, r in regime_map.items() if r == regime)
    print(f'\n=== {regime.upper()} IC ===')
    for f in all_feats:
        fv = np.array(data[f])
        mf, ml = [], []
        for i, ts in enumerate(ts_list):
            if ts in ts_set and ts in label_map and not np.isnan(fv[i]):
                mf.append(fv[i])
                ml.append(label_map[ts])
        mf, ml = np.array(mf), np.array(ml)
        if len(mf) < 100:
            continue
        if np.std(mf) < 1e-10:
            ic = 0
        else:
            c = np.corrcoef(mf, ml)
            ic = c[0,1] if np.isfinite(c[0,1]) else 0
        status = 'PASS' if abs(ic) >= 0.05 else 'FAIL'
        print(f'  {f:20s}: IC={ic:+.4f}  n={len(mf)}  [{status}]')

# Combined IC for Bear regime top features & fusion analysis
print('\n=== BEAR REGIME FUSION ANALYSIS ===')
bear_ts = [ts for ts, r in regime_map.items() if r == 'bear']
bear_feats = {}
for f in senses:
    fv = np.array(data[f])
    mf, ml = [], []
    for i, ts in enumerate(ts_list):
        if ts in set(bear_ts) and ts in label_map and not np.isnan(fv[i]):
            mf.append(fv[i])
            ml.append(label_map[ts])
    if len(mf) > 0:
        c = np.corrcoef(mf, ml)
        ic = c[0,1] if np.isfinite(c[0,1]) else 0
        bear_feats[f] = {'ic': ic, 'feat_values': mf, 'labels': ml, 'n': len(mf)}
        
# Sort by |IC| and take top 5 signed features
sorted_by_ic = sorted(bear_feats.items(), key=lambda x: abs(x[1]['ic']), reverse=True)
print('Bear IC ranking:')
for name, info in sorted_by_ic:
    print(f'  {name}: IC={info["ic"]:+.4f}')

# Sign-aware fusion: multiply features by -1 if IC < 0, then average
top5 = sorted_by_ic[:5]
print(f'\nTop 5 signed fusion:')
# Get common timestamps
common_ts = set(range(min(info['n'] for _, info in top5)))
# Actually build aligned arrays
aligned = []
for name, info in top5:
    vals = np.array(info['feat_values'])
    sign = -1 if info['ic'] < 0 else 1
    aligned.append(sign * vals[:min(info['n'] for _, info in top5)])

# Average
fusion = np.mean(aligned, axis=0)
labels = np.array(top5[0][1]['labels'][:min(info['n'] for _, info in top5)])
if len(fusion) > 100:
    c = np.corrcoef(fusion, labels)
    fusion_ic = c[0,1] if np.isfinite(c[0,1]) else 0
    print(f'  Fusion IC: {fusion_ic:+.4f}')

# VIX IC
try:
    vix_data = db.execute('SELECT feat_vix FROM features_normalized WHERE feat_vix IS NOT NULL').fetchall()
    vix_values = [x[0] for x in vix_data]
    vix_ts_list = db.execute('SELECT timestamp FROM features_normalized WHERE feat_vix IS NOT NULL ORDER BY timestamp').fetchall()
    vix_ts = [x[0] for x in vix_ts_list]
    
    mf, ml = [], []
    for i, ts in enumerate(vix_ts):
        if ts in label_map:
            mf.append(vix_values[i])
            ml.append(label_map[ts])
    if len(mf) > 100:
        vf = np.array(mf)
        vl = np.array(ml)
        c = np.corrcoef(vf, vl)
        ic = c[0,1] if np.isfinite(c[0,1]) else 0
        print(f'\nVIX IC (global): {ic:+.4f} n={len(mf)}')
        
        for regime in ['bear', 'bull', 'chop']:
            ts_set = set(ts for ts, r in regime_map.items() if r == regime and ts in set(vix_ts))
            mf2, ml2 = [], []
            for i, ts in enumerate(vix_ts):
                if ts in ts_set and ts in label_map:
                    mf2.append(vix_values[i])
                    ml2.append(label_map[ts])
            if len(mf2) > 100:
                c2 = np.corrcoef(mf2, ml2)
                ic2 = c2[0,1] if np.isfinite(c2[0,1]) else 0
                print(f'  VIX IC ({regime}): {ic2:+.4f} n={len(mf2)}')
except Exception as e:
    print(f'VIX IC failed: {e}')

db.close()
