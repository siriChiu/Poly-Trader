"""Heartbeat #105 - Explore alternative features for Aura and all senses
Try new feature candidates against label_up to find IC > 0.05"""
import os, sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

from sqlalchemy import create_engine
import pandas as pd
import numpy as np

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
engine = create_engine(f'sqlite:///{DB_PATH}')

# Load raw market data
raw = pd.read_sql('SELECT * FROM raw_market_data ORDER BY timestamp', engine)
labels = pd.read_sql('SELECT timestamp, label_up FROM labels', engine)

# Normalize timestamps
raw['ts_key'] = pd.to_datetime(raw['timestamp'], format='mixed').dt.floor('s')
labels['ts_key'] = pd.to_datetime(labels['timestamp'], format='mixed').dt.floor('s')

merged = raw.merge(labels[['ts_key', 'label_up']], on='ts_key', how='inner')
merged = merged.sort_values('timestamp').reset_index(drop=True)
print(f"Combined N={len(merged)}")

# Also load features
feats = pd.read_sql('SELECT * FROM features_normalized ORDER BY timestamp', engine)
feats['ts_key'] = pd.to_datetime(feats['timestamp'], format='mixed').dt.floor('s')
full = feats.merge(merged[['ts_key', 'label_up', 'close_price', 'volume', 'funding_rate',
                             'fear_greed_index', 'polymarket_prob', 'eye_dist', 'ear_prob',
                             'tongue_sentiment', 'volatility', 'oi_roc', 'body_label']],
                    on='ts_key', how='inner', suffixes=('_feat', '_raw'))
print(f"Full merged N={len(full)}")

label_col = 'label_up'

# ===== Current feature ICs =====
print(f"\n{'='*70}")
print(f"CURRENT SENSORY FEATURE ICs")
print(f"{'='*70}")

current_feats = {
    'Eye': 'feat_eye', 'Ear': 'feat_ear', 'Nose': 'feat_nose',
    'Tongue': 'feat_tongue', 'Body': 'feat_body', 'Pulse': 'feat_pulse',
    'Aura': 'feat_aura', 'Mind': 'feat_mind'
}

for name, col in current_feats.items():
    if col in full.columns:
        valid = full[[col, label_col]].dropna()
        if len(valid) >= 100:
            ic = valid[col].corr(valid[label_col])
            n = len(valid)
            unique = valid[col].nunique()
            print(f"  {name:10s}: IC={ic:+.4f} (n={n}, unique={unique})")

# ===== CANDIDATE ALTERNATIVE FEATURES =====
print(f"\n{'='*70}")
print(f"ALTERNATIVE FEATURE CANDIDATES")
print(f"{'='*70}")

# Raw market columns
raw_cols_analysis = {
    'close_price': 'BTC価格',
    'volume': 'Volume',
    'funding_rate': 'Funding Rate',
    'fear_greed_index': 'Fear & Greed',
    'polymarket_prob': 'Polymarket Prob',
    'eye_dist': 'Eye Distribution',
    'ear_prob': 'Ear Probability',
    'tongue_sentiment': 'Tongue Sentiment',
    'volatility': 'Volatility',
    'oi_roc': 'OI Rate of Change',
    'body_label': 'Body Label',
}

for col, desc in raw_cols_analysis.items():
    if col in merged.columns:
        valid = merged[[col, label_col]].dropna()
        if len(valid) >= 100:
            ic = valid[col].corr(valid[label_col])
            n = len(valid)
            unique = valid[col].nunique()
            std = valid[col].std()
            print(f"  {col:25s}: IC={ic:+.4f} (n={n}, std={std:.4f}, unique={unique})")

# ===== ENGINEERED CANDIDATES =====
print(f"\n{'='*70}")
print(f"ENGINEERED CANDIDATES")
print(f"{'='*70}")

# Price returns at different horizons
for lag in [4, 12, 24, 48, 96, 144]:
    if len(merged) > lag:
        ret = merged['close_price'].pct_change(lag)
        valid = pd.DataFrame({'feat': ret, label_col: merged[label_col]}).dropna()
        if len(valid) >= 100:
            ic = valid['feat'].corr(valid[label_col])
            print(f"  price_ret_{lag:3d}h: IC={ic:+.4f} (n={len(valid)})")

# Volume changes
for lag in [4, 12, 24, 48]:
    if len(merged) > lag:
        vol_chg = merged['volume'].pct_change(lag)
        valid = pd.DataFrame({'feat': vol_chg, label_col: merged[label_col]}).dropna()
        if len(valid) >= 100:
            ic = valid['feat'].corr(valid[label_col])
            print(f"  volume_chg_{lag:3d}h: IC={ic:+.4f} (n={len(valid)})")

# Funding rate changes
for lag in [4, 12, 24]:
    if len(merged) > lag:
        fr_chg = merged['funding_rate'].diff(lag)
        valid = pd.DataFrame({'feat': fr_chg, label_col: merged[label_col]}).dropna()
        if len(valid) >= 100:
            ic = valid['feat'].corr(valid[label_col])
            print(f"  fr_diff_{lag:3d}h:   IC={ic:+.4f} (n={len(valid)})")

# OI ROC changes
for lag in [4, 12, 24]:
    if len(merged) > lag:
        oi_diff = merged['oi_roc'].diff(lag)
        valid = pd.DataFrame({'feat': oi_diff, label_col: merged[label_col]}).dropna()
        if len(valid) >= 100:
            ic = valid['feat'].corr(valid[label_col])
            print(f"  oi_roc_diff_{lag:3d}h: IC={ic:+.4f} (n={len(valid)})")

# Fear greed index changes
for lag in [4, 12, 24]:
    if len(merged) > lag:
        fng_diff = merged['fear_greed_index'].diff(lag)
        valid = pd.DataFrame({'feat': fng_diff, label_col: merged[label_col]}).dropna()
        if len(valid) >= 100:
            ic = valid['feat'].corr(valid[label_col])
            print(f"  fng_diff_{lag:3d}h: IC={ic:+.4f} (n={len(valid)})")

# Interaction features
print(f"\n{'='*70}")
print(f"INTERACTION FEATURES")
print(f"{'='*70}")

# Current feature interaction with price return
for col in ['feat_eye', 'feat_ear', 'feat_nose', 'feat_pulse', 'feat_mind']:
    if col in full.columns:
        ret_24 = full['close_price'].pct_change(24)
        interact = full[col] * ret_24
        valid = pd.DataFrame({'feat': interact, label_col: full[label_col]}).dropna()
        if len(valid) >= 100:
            ic = valid['feat'].corr(valid[label_col])
            print(f"  {col}_×_ret24: IC={ic:+.4f} (n={len(valid)})")

# RSI
if len(merged) >= 15:
    delta = merged['close_price'].diff(1)
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - 100 / (1 + rs)
    rsi_norm = (rsi - 50) / 50  # Normalize to [-1, 1]
    valid = pd.DataFrame({'rsi_norm': rsi_norm, label_col: merged[label_col]}).dropna()
    if len(valid) >= 100:
        ic = valid['rsi_norm'].corr(valid[label_col])
        print(f"  rsi_14_norm:  IC={ic:+.4f} (n={len(valid)})")

# MACD
if len(merged) >= 27:
    ema12 = merged['close_price'].ewm(span=12).mean()
    ema26 = merged['close_price'].ewm(span=26).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9).mean()
    macd_hist = macd - macd_signal
    for name, feat in [('macd', macd), ('macd_hist', macd_hist)]:
        valid = pd.DataFrame({'feat': feat, label_col: merged[label_col]}).dropna()
        if len(valid) >= 100:
            ic = valid['feat'].corr(valid[label_col])
            print(f"  {name}:        IC={ic:+.4f} (n={len(valid)})")

# Volatility-based
if len(merged) >= 25:
    for window in [12, 24, 48]:
        vol = merged['close_price'].pct_change(1).rolling(window).std()
        valid = pd.DataFrame({'feat': vol, label_col: merged[label_col]}).dropna()
        if len(valid) >= 100:
            ic = valid['feat'].corr(valid[label_col])
            print(f"  vol_{window:3d}h:    IC={ic:+.4f} (n={len(valid)})")

# Mean reversion features
if len(merged) >= 50:
    for window in [20, 50, 100]:
        sma = merged['close_price'].rolling(window).mean()
        dist = (merged['close_price'] - sma) / sma
        valid = pd.DataFrame({'feat': dist, label_col: merged[label_col]}).dropna()
        if len(valid) >= 100:
            ic = valid['feat'].corr(valid[label_col])
            print(f"  mean_rev_{window:3d}h: IC={ic:+.4f} (n={len(valid)})")
