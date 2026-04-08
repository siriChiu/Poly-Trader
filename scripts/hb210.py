#!/usr/bin/env python3
"""Heartbeat #210: Full sensory IC analysis + model CV"""
import sqlite3
import numpy as np
import pandas as pd
import json
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

db = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')

raw_count = db.execute('SELECT COUNT(*) FROM raw_market_data').fetchone()[0]
feat_count = db.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
label_count = db.execute('SELECT COUNT(*) FROM labels').fetchone()[0]
print(f"Raw={raw_count}, Features={feat_count}, Labels={label_count}")

feat_df = pd.read_sql("SELECT * FROM features_normalized", db)
label_df = pd.read_sql("SELECT * FROM labels", db)

merged = feat_df.merge(label_df, on=['id','timestamp','symbol'], how='inner', suffixes=('_f','_l'))
print(f"Merged: {len(merged)} rows")

btc_col = 'close_price'
if btc_col not in merged.columns:
    # Check raw table for latest BTC price
    try:
        latest = db.execute("SELECT close_price FROM raw_market_data ORDER BY timestamp DESC LIMIT 1").fetchone()
        btc_now = latest[0] if latest else None
    except:
        btc_now = None
else:
    btc_now = merged[btc_col].iloc[-1]

print(f"BTC now: {btc_now}")

y_col = 'label_spot_long_win'
y = merged[y_col].astype(float)
print(f"Label pos rate: {y.mean()*100:.1f}%")

regime_nulls = merged['regime_label_f'].isna().sum()
print(f"NULL regime labels: {regime_nulls}")

SENSE_MAP = {
    'Eye': 'feat_eye', 'Ear': 'feat_ear', 'Nose': 'feat_nose',
    'Tongue': 'feat_tongue', 'Body': 'feat_body', 'Pulse': 'feat_pulse',
    'Aura': 'feat_aura', 'Mind': 'feat_mind',
}
TECH_MAP = {
    'VIX': 'feat_vix', 'DXY': 'feat_dxy', 'RSI14': 'feat_rsi14',
    'MACD_hist': 'feat_macd_hist', 'ATR_pct': 'feat_atr_pct',
    'VWAP_dev': 'feat_vwap_dev', 'BB%p': 'feat_bb_pct_b',
}
ALL_FEATURES = {**SENSE_MAP, **TECH_MAP}

y_centered = y - y.mean()

print(f"\n=== FULL IC against sell_win (n={len(merged)}) ===")
passing = 0
ics = {}
for name, col in ALL_FEATURES.items():
    if col in merged.columns:
        x = merged[col].astype(float)
        # Drop rows where x or y is NaN before computing correlation
        valid = merged[col].notna() & merged['label_spot_long_win'].notna()
        x_valid = merged.loc[valid, col].astype(float)
        y_valid = merged.loc[valid, 'label_spot_long_win'].astype(float)
        y_centered_valid = y_valid - y_valid.mean()
        std_x = x.std()
        unique_n = x.nunique()
        if std_x > 0 and len(x_valid) > 2:
            ic = np.corrcoef(x_valid, y_centered_valid)[0, 1]
            if np.isnan(ic): ic = 0.0
        else:
            ic = 0.0
        ics[name] = {'ic': ic, 'std': std_x}
        status = "✅ PASS" if abs(ic) >= 0.05 else "❌"
        if abs(ic) >= 0.05: passing += 1
        print(f"  {name:12s}: {ic:+.4f}  std={std_x:.4f}  unique={unique_n}  {status}")
    else:
        ics[name] = {'ic': None, 'std': None}
        print(f"  {name:12s}: N/A")
print(f"Passing: {passing}/{len(ALL_FEATURES)}")

# Regime IC
regime_col = 'regime_label_f' if 'regime_label_f' in merged.columns else 'regime_label_l'
print(f"\n=== REGIME IC ===")
regime_ics = {}
for rn in sorted(merged[regime_col].dropna().unique()):
    sub = merged[merged[regime_col] == rn]
    ys = sub[y_col].astype(float)
    yc = ys - ys.mean()
    rp = 0
    rics = {}
    for sn, col in ALL_FEATURES.items():
        if col not in sub.columns: continue
        xs = sub[col].astype(float)
        if xs.std() > 0 and len(xs) > 2:
            ic = np.corrcoef(xs, yc)[0, 1]
            if np.isnan(ic): ic = 0.0
        else:
            ic = 0.0
        rics[sn] = ic
        if abs(ic) >= 0.05: rp += 1
    regime_ics[rn] = {'ics': rics, 'passing': rp, 'n': len(sub), 'sell_win': float(ys.mean())}
    print(f"  {rn:10s}: {rp}/{len(ALL_FEATURES)} passing, sell_win={ys.mean():.3f}, n={len(sub)}")

# Dynamic window
print(f"\n=== DYNAMIC WINDOW ===")
for w in [500, 1000, 2000, 5000]:
    recent = merged.tail(w)
    yw = recent[y_col].astype(float)
    ycw = yw - yw.mean()
    pw = 0
    for sn, col in ALL_FEATURES.items():
        if col not in recent.columns: continue
        xw = recent[col].astype(float)
        if xw.std() > 0 and len(xw) > 2:
            ic = np.corrcoef(xw, ycw)[0, 1]
            if np.isnan(ic): ic = 0.0
        else:
            ic = 0.0
        if abs(ic) >= 0.05: pw += 1
    print(f"  N={w}: {pw}/{len(ALL_FEATURES)} passing, sell_win={yw.mean():.3f}")

# Model CV
print(f"\n=== MODEL CV ===")
sense_cols = [c for c in ALL_FEATURES.values() if c in merged.columns]
X = merged[sense_cols].replace([np.inf, -np.inf], np.nan).fillna(0).astype(float)
y_cv = merged[y_col].astype(float)

print(f"  X shape: {X.shape}, y: {y_cv.value_counts().to_dict()}")

if X.shape[1] > 0 and len(y_cv) > 5:
    lr = LogisticRegression(max_iter=1000, random_state=42)
    cv_acc = cross_val_score(lr, X, y_cv, cv=5, scoring='accuracy')
    print(f"  CV: {cv_acc.mean()*100:.1f}% +/- {cv_acc.std()*100:.1f}%")
    lr.fit(X, y_cv)
    train_acc = lr.score(X, y_cv)
    print(f"  Train: {train_acc*100:.1f}%")
    print(f"  Overfit gap: {(train_acc - cv_acc.mean())*100:+.1f}pp")

# Sell win deep
print(f"\n=== SELL WIN DEEP ===")
sw = merged[y_col].astype(int)
def max_zeros(s):
    m, c = 0, 0
    for v in s:
        c = c+1 if v==0 else 0
        m = max(m, c)
    return m
print(f"  Global: {sw.mean():.3f}")
print(f"  Max consecutive 0s: {max_zeros(sw)}")
print(f"  Last 50: {sw.tail(50).mean():.3f}")
print(f"  Last 100: {sw.tail(100).mean():.3f}")
print(f"  Last 500: {sw.tail(500).mean():.3f}")

# Regime sell_win
for rn, rd in regime_ics.items():
    print(f"  {rn}: {rd['sell_win']:.3f} (n={rd['n']})")

# Save
results = {
    'timestamp': datetime.now().isoformat(), 'hb': 210,
    'raw': raw_count, 'features': feat_count, 'labels': label_count,
    'merged': len(merged), 'btc_price': float(btc_now) if btc_now else None,
    'ics': {k: v['ic'] for k,v in ics.items()},
    'regimes': {k: {'passing': v['passing'], 'sw': v['sell_win'], 'n': v['n']} for k,v in regime_ics.items()},
    'passing': passing, 'total': len(ALL_FEATURES),
}
with open('/home/kazuha/Poly-Trader/data/ic_heartbeat_210.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nSaved to data/ic_heartbeat_210.json")
db.close()
