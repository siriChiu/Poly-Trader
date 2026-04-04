#!/usr/bin/env python
"""Heartbeat Step 1 & 2: Data collection + IC analysis"""
import sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')

from data.db_store import DBStore
import numpy as np
import pandas as pd

db = DBStore()

# === Step 1: Data Collection ===
raw_count = db.db.execute('SELECT COUNT(*) FROM market_raw').fetchone()[0]
features_count = db.db.execute('SELECT COUNT(*) FROM market_features').fetchone()[0]
labels_count = db.db.execute('SELECT COUNT(*) FROM market_labels').fetchone()[0]

label_df = db.load_labels()
sell_win_ratio = label_df['sell_win'].mean() if 'sell_win' in label_df.columns else None

features_df = db.load_features()
btc_now = None
if 'close' in features_df.columns:
    btc_now = features_df['close'].iloc[-1]
elif 'btc_close' in features_df.columns:
    btc_now = features_df['btc_close'].iloc[-1]

feat_cols = features_df.columns.tolist()

# Get derivatives data if available
derivatives = {}
try:
    lsrs = db.db.execute('SELECT * FROM binance_lsr ORDER BY timestamp DESC LIMIT 1').fetchone()
    if lsrs:
        derivatives['lsr'] = lsrs
except:
    pass

print("=== STEP 1: DATA COLLECTION ===")
print(f"Raw: {raw_count}")
print(f"Features: {features_count}")
print(f"Labels: {labels_count}")
print(f"sell_win%: {sell_win_ratio*100:.1f}%" if sell_win_ratio else "N/A")
print(f"BTC price: ${btc_now:,.0f}" if btc_now else "N/A")
print(f"Feature cols ({len(feat_cols)}): {feat_cols}")
print()

# === Step 2: Sensory IC Analysis ===
# Core 8 senses mapping to feature columns
SENSE_MAP = {
    'Eye': 'eye_signal',
    'Ear': 'ear_signal',
    'Nose': 'nose_signal',
    'Tongue': 'tongue_signal',
    'Body': 'body_signal',
    'Pulse': 'pulse_signal',
    'Aura': 'aura_signal',
    'Mind': 'mind_signal',
}

# Combine features + labels
merged = features_df.copy()
if not label_df.empty:
    # Align on index or join
    if len(merged) == len(label_df):
        merged = pd.concat([merged.reset_index(drop=True), label_df.reset_index(drop=True)], axis=1)
    else:
        min_len = min(len(merged), len(label_df))
        merged = merged.iloc[:min_len].reset_index(drop=True)
        label_sub = label_df.iloc[:min_len].reset_index(drop=True)
        merged = pd.concat([merged, label_sub], axis=1)

if 'sell_win' not in merged.columns:
    print("ERROR: sell_win not in merged data")
    sys.exit(1)

y = merged['sell_win'].astype(float)
y_centered = y - y.mean()

print("=== STEP 2: SENSORY IC ANALYSIS (h=4) ===")
print()

# Full IC
full_ics = {}
for sense_name, col in SENSE_MAP.items():
    if col in merged.columns:
        x = merged[col].astype(float)
        if x.std() > 0:
            ic = np.corrcoef(x, y_centered)[0, 1]
        else:
            ic = 0.0
        full_ics[sense_name] = ic
    else:
        full_ics[sense_name] = None

print("--- Full IC (against sell_win) ---")
passing = 0
for sense, ic in full_ics.items():
    status = "✅" if ic is not None and abs(ic) >= 0.05 else "❌"
    if ic is not None and abs(ic) >= 0.05:
        passing += 1
    print(f"  {sense:8s}: {ic:+.4f} {status}" if ic is not None else f"  {sense:8s}: N/A")
print(f"Passing: {passing}/8")
print()

# Regime-aware IC (tercile split)
sorted_merged = merged.sort_values(by='close' if 'close' in merged.columns else merged.columns[0])
n = len(sorted_merged)
third = n // 3
bear_data = sorted_merged.iloc[:third]
chop_data = sorted_merged.iloc[third:2*third]
bull_data = sorted_merged.iloc[2*third:]

print("--- Regime-Aware IC ---")
print(f"{'Sense':<8s} | {'Bear IC':>8s} | {'Bull IC':>8s} | {'Chop IC':>8s}")
bear_pass = bull_pass = chop_pass = 0
for sense_name, col in SENSE_MAP.items():
    if col not in merged.columns:
        continue
    ics = {}
    for name, subset in [('Bear', bear_data), ('Bull', bull_data), ('Chop', chop_data)]:
        y_sub = subset['sell_win'].astype(float)
        y_c = y_sub - y_sub.mean()
        x_sub = subset[col].astype(float)
        if x_sub.std() > 0 and len(x_sub) > 2:
            ic = np.corrcoef(x_sub, y_c)[0, 1]
        else:
            ic = 0.0
        ics[name] = ic
        if abs(ic) >= 0.05:
            if name == 'Bear': bear_pass += 1
            elif name == 'Bull': bull_pass += 1
            else: chop_pass += 1
    
    bear_m = "✅" if abs(ics['Bear']) >= 0.05 else "❌"
    bull_m = "✅" if abs(ics['Bull']) >= 0.05 else "❌"
    chop_m = "✅" if abs(ics['Chop']) >= 0.05 else "❌"
    print(f"{sense_name:<8s} | {ics['Bear']:+.4f} {bear_m} | {ics['Bull']:+.4f} {bull_m} | {ics['Chop']:+.4f} {chop_m}")

print(f"\nRegime passing: Bear={bear_pass}/8, Bull={bull_pass}/8, Chop={chop_pass}/8")
print()

# Dynamic window IC
print("--- Dynamic Window IC ---")
for window in [500, 1000, 2000, 3000, 5000]:
    recent = merged.tail(window)
    if len(recent) < 3:
        continue
    y_w = recent['sell_win'].astype(float)
    y_cw = y_w - y_w.mean()
    passing_w = 0
    for sense_name, col in SENSE_MAP.items():
        if col not in recent.columns:
            continue
        x_w = recent[col].astype(float)
        if x_w.std() > 0:
            ic_w = np.corrcoef(x_w, y_cw)[0, 1]
        else:
            ic_w = 0.0
        if abs(ic_w) >= 0.05:
            passing_w += 1
    print(f"  N={window}: {passing_w}/8 passing")

print()

# Model CV
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

sense_cols_in_data = [SENSE_MAP[s] for s in SENSE_MAP if SENSE_MAP[s] in merged.columns]
X = merged[sense_cols_in_data].fillna(0)
y_cv = merged['sell_win'].astype(float)

if len(X) > 0 and len(y_cv) > 0:
    lr = LogisticRegression(max_iter=1000, random_state=42)
    cv_scores = cross_val_score(lr, X, y_cv, cv=5, scoring='accuracy')
    print(f"=== Model CV Accuracy ===")
    print(f"  LR:    {cv_scores.mean()*100:.1f}% ± {cv_scores.std()*100:.1f}%")
    
    # IC-weighted fusion
    weights = []
    for col in sense_cols_in_data:
        x = merged[col].astype(float)
        if x.std() > 0:
            ic = abs(np.corrcoef(x, y_centered)[0, 1])
        else:
            ic = 0.0
        weights.append(max(ic, 0.001))
    weights = np.array(weights)
    weights = weights / weights.sum()
    
    if len(sense_cols_in_data) > 1:
        fused = (merged[sense_cols_in_data].fillna(0).values * weights).sum(axis=1)
        # Simple threshold classifier
        from sklearn.metrics import accuracy_score
        threshold = np.median(fused)
        preds = (fused > threshold).astype(float)
        ic_fusion_acc = accuracy_score(y_cv, preds)
        print(f"  IC-Fusion: {ic_fusion_acc*100:.1f}%")
else:
    print("Not enough data for CV")

# FNG
print()
try:
    from sensory.fear_greed_index import get_fng_data
    fng_data = get_fng_data()
    print(f"FNG: {fng_data.get('value', 'N/A')} ({fng_data.get('value_classification', 'N/A')})")
except Exception as e:
    print(f"FNG: Could not fetch ({e})")

# Derivatives
print()
print("=== Derivatives ===")
try:
    # Try to get latest derivatives
    for table in ['binance_lsr', 'binance_gsr', 'binance_taker', 'binance_open_interest']:
        try:
            row = db.db.execute(f'SELECT * FROM {table} ORDER BY timestamp DESC LIMIT 1').fetchone()
            if row:
                desc = db.db.execute(f'PRAGMA table_info({table})').fetchall()
                col_names = [d[1] for d in desc]
                print(f"  {table}: {dict(zip(col_names, row))}")
            else:
                print(f"  {table}: empty")
        except:
            print(f"  {table}: not available")
except Exception as e:
    print(f"  Derivatives error: {e}")
