#!/usr/bin/env python3
"""Heartbeat #209: Full IC analysis + BTC/derivatives data collection"""
import sqlite3
import numpy as np
import json
import urllib.request
import ssl
from datetime import datetime

ctx = ssl.create_default_context()
headers = {'User-Agent': 'Mozilla/5.0'}

db = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')

# Schema
raw_cols = [c[1] for c in db.execute('PRAGMA table_info("raw_market_data")').fetchall()]
feat_cols = [c[1] for c in db.execute('PRAGMA table_info("features_normalized")').fetchall()]
label_cols = [c[1] for c in db.execute('PRAGMA table_info("labels")').fetchall()]

print(f"Raw cols: {raw_cols}")
print(f"Feature cols: {feat_cols}")
print(f"Label cols: {label_cols}")

# Counts
raw_count = db.execute('SELECT COUNT(*) FROM raw_market_data').fetchone()[0]
feat_count = db.execute('SELECT COUNT(*) FROM features_normalized').fetchone()[0]
label_count = db.execute('SELECT COUNT(*) FROM labels').fetchone()[0]
print(f"\nCounts: raw={raw_count}, features={feat_count}, labels={label_count}")

# Join features + labels on timestamp (common key)
import pandas as pd
feat_df = pd.read_sql_query('SELECT * FROM features_normalized', db)
label_df = pd.read_sql_query('SELECT * FROM labels', db)

# Join on timestamp and symbol — rename regime_label in label_df to avoid collision
label_df_renamed = label_df.rename(columns={'regime_label': 'regime_label_l'})
merged = feat_df.merge(label_df_renamed, on=['timestamp', 'symbol'], how='inner', suffixes=('_f', '_l'))
print(f"Merged: {len(merged)} rows")

y_col = 'label_spot_long_win'
y = merged[y_col].astype(float)
print(f"sell_win rate: {y.mean():.4f} ({y.sum():.0f}/{len(y)})")

# Check NULL regime labels
print(f"Null regime labels: {merged['regime_label_l'].isna().sum()}")

# Sell win by regime
for reg in ['Bear', 'Bull', 'Chop', 'Neutral']:
    mask = merged['regime_label_l'] == reg
    if mask.sum() > 0:
        sw = merged.loc[mask, y_col].mean()
        print(f"  {reg} sell_win: {sw:.3f} (n={mask.sum()})")

# Recent sell_win
for n in [50, 100, 500]:
    recent = merged.tail(n)
    sw = recent[y_col].mean()
    consec_0 = 0
    for v in reversed(recent[y_col].values):
        if v == 0:
            consec_0 += 1
        else:
            break
    print(f"  last_{n} sell_win: {sw:.3f}, consecutive 0s at end: {consec_0}")

# BTC price
btc_price = '?'
try:
    btc_price_raw = merged['close_price'].iloc[-1] if 'close_price' in merged.columns else None
    if btc_price_raw:
        btc_price = f"${btc_price_raw:,.0f}"
    else:
        btc_price = '${:,.0f}'.format(merged.iloc[-1].get('close_price', 0))
except:
    pass

# Check raw for latest BTC price
latest_raw = db.execute('SELECT close_price FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
if latest_raw:
    btc_price = f"${latest_raw[0]:,.0f}"
print(f"\nBTC Price: {btc_price}")

# VIX/DXY from raw
latest = db.execute('SELECT vix_value, dxy_value FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
vix_val = latest[0] if latest and latest[0] else None
dxy_val = latest[1] if latest and latest[1] else None
print(f"VIX: {vix_val}, DXY: {dxy_val}")

# Derivatives: check if any derivatives data exists
deriv_tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%deriv%' OR name LIKE '%funding%' OR name LIKE '%oi%'").fetchall()
print(f"Derivatives tables: {deriv_tables}")

# Check raw_market_data columns for derivatives
deriv_cols = [c for c in raw_cols if any(x in c.lower() for x in ['funding', 'oi', 'lsr', 'gsr', 'taker', 'open_interest', 'long_short'])]
print(f"Derivatives columns: {deriv_cols}")

if deriv_cols:
    cols_str = ', '.join(deriv_cols)
    deriv_latest = db.execute(f'SELECT {cols_str} FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    for col, val in zip(deriv_cols, deriv_latest):
        print(f"  {col}: {val}")

# FNG
fng_cols = [c for c in raw_cols if 'fng' in c.lower() or 'fear' in c.lower()]
print(f"FNG columns: {fng_cols}")
if fng_cols:
    cols_str = ', '.join(fng_cols)
    fng_latest = db.execute(f'SELECT {cols_str} FROM raw_market_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    for col, val in zip(fng_cols, fng_latest):
        print(f"  {col}: {val}")

# === FULL IC Analysis (against label_spot_long_win) ===
SENSE_MAP = {
    'Eye': 'feat_eye',
    'Ear': 'feat_ear',
    'Nose': 'feat_nose',
    'Tongue': 'feat_tongue',
    'Body': 'feat_body',
    'Pulse': 'feat_pulse',
    'Aura': 'feat_aura',
    'Mind': 'feat_mind',
    'VIX': 'feat_vix',
    'DXY': 'feat_dxy',
    'RSI14': 'feat_rsi14',
    'MACD_hist': 'feat_macd_hist',
    'ATR_pct': 'feat_atr_pct',
    'VWAP_dev': 'feat_vwap_dev',
    'BB%p': 'feat_bb_pct_b',
}

y_centered = y - y.mean()
results = {}

print(f"\n{'='*70}")
print(f"=== FULL IC Analysis (against {y_col}) ===")
print(f"{'='*70}")

passing_full = 0
ics_out = {}
for sense, col in SENSE_MAP.items():
    if col not in merged.columns:
        print(f"  {sense:12s}: N/A (col '{col}' not found)")
        ics_out[sense] = None
        continue
    x = merged[col].fillna(0).astype(float)
    std_x = x.std()
    unique_n = x.nunique()
    if std_x > 0 and len(x) > 2:
        ic = np.corrcoef(x, y_centered)[0, 1]
    else:
        ic = 0.0
    ics_out[sense] = float(ic)
    status = "✅ PASS" if abs(ic) >= 0.05 else "❌ FAIL"
    if abs(ic) >= 0.05:
        passing_full += 1
    print(f"  {sense:12s}: {ic:+.4f} {status}  (std={std_x:.4f}, unique={unique_n})")

total_feats = len([v for v in ics_out.values() if v is not None])
print(f"\n  Passing: {passing_full}/{total_feats} (threshold |IC| >= 0.05)")

# === Regime Awareness ===
# Use regime_label_l from labels
regime_col = 'regime_label_l'
regimes = merged[regime_col].dropna().unique()

print(f"\n=== REGIME IC ===")
regime_results = {}
for reg in sorted(regimes):
    subset = merged[merged[regime_col] == reg]
    if len(subset) < 10:
        continue
    y_sub = subset[y_col].astype(float)
    y_c = y_sub - y_sub.mean()
    reg_pass = 0
    reg_ics = {}
    for sense, col in SENSE_MAP.items():
        if col not in subset.columns:
            continue
        x_sub = subset[col].fillna(0).astype(float)
        if x_sub.std() > 0 and len(x_sub) > 2:
            ic = np.corrcoef(x_sub, y_c)[0, 1]
        else:
            ic = 0.0
        reg_ics[sense] = float(ic)
        if abs(ic) >= 0.05:
            reg_pass += 1
    regime_results[reg] = {'pass': reg_pass, 'total': len(reg_ics), 'ics': reg_ics, 'sell_win': float(y_sub.mean())}
    print(f"  {reg:10s}: {reg_pass}/{len(reg_ics)} passing, sell_win={y_sub.mean():.3f} (n={len(subset)})")

# === Model CV ===
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

available_sense_cols = [col for col in SENSE_MAP.values() if col in merged.columns]
X = merged[available_sense_cols].fillna(0)
y_bin = y.astype(int)

print(f"\n=== MODEL CV ===")
print(f"  X shape: {X.shape}, y classes: {y_bin.value_counts().to_dict()}")

if X.shape[1] > 0:
    lr = LogisticRegression(max_iter=1000, random_state=42)
    try:
        cv_acc = cross_val_score(lr, X, y_bin, cv=5, scoring='accuracy')
        print(f"  LR CV: {cv_acc.mean()*100:.1f}% ± {cv_acc.std()*100:.1f}%")
    except Exception as e:
        print(f"  LR CV failed: {e}")
    
    # Check train accuracy
    lr.fit(X, y_bin)
    train_acc = lr.score(X, y_bin)
    print(f"  Train: {train_acc*100:.1f}%")
    print(f"  Overfit gap: {(train_acc - cv_acc.mean())*100:.1f}pp")
else:
    print("  No features available for model")

# === Recent sell_win streak analysis ===
recent_500 = merged.tail(500)
consec_0s = 0
for v in reversed(merged[y_col].values):
    if v == 0:
        consec_0s += 1
    else:
        break
print(f"\n  Consecutive 0s at end: {consec_0s}")

# Save results
results = {
    'timestamp': datetime.now().isoformat(),
    'raw_count': raw_count,
    'feat_count': feat_count,
    'label_count': label_count,
    'btc_price': btc_price,
    'vix': vix_val,
    'dxy': dxy_val,
    'sell_win_global': float(y.mean()),
    'consecutive_0s': consec_0s,
    'full_ics': ics_out,
    'passing': passing_full,
    'total': total_feats,
    'regime_results': regime_results,
}

with open('/home/kazuha/Poly-Trader/data/hb209_results.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nResults saved to data/hb209_results.json")

db.close()
