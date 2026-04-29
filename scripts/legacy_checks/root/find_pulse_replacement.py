"""Find best replacement for Pulse sensor"""
import sqlite3, numpy as np
from scipy import stats

conn = sqlite3.connect(r"C:\Users\Kazuha\repo\Poly-Trader\poly_trader.db")

# Get all available raw columns
raw_cols = [r[1] for r in conn.execute("PRAGMA table_info(raw_market_data)").fetchall()]
feat_cols = [r[1] for r in conn.execute("PRAGMA table_info(features_normalized)").fetchall()]
print("Raw columns:", raw_cols)
print("Feature columns:", feat_cols)

# Get raw data joined with labels for candidate feature engineering
rows = conn.execute("""
    SELECT r.close_price, r.volume, r.funding_rate, r.fear_greed_index,
           r.stablecoin_mcap, r.polymarket_prob, r.eye_dist, r.ear_prob,
           r.tongue_sentiment, r.volatility, r.oi_roc, r.timestamp, l.label
    FROM raw_market_data r
    JOIN labels l ON r.timestamp = l.timestamp
    WHERE l.horizon_hours = 4
    ORDER BY r.timestamp DESC
    LIMIT 2000
""").fetchall()

print(f"\nJoined rows: {len(rows)}")

df_data = {
    'close': [r[0] for r in rows],
    'volume': [r[1] for r in rows],
    'fr': [r[2] for r in rows],
    'fng': [r[3] for r in rows],
    'stable': [r[4] for r in rows],
    'oi_roc': [r[10] for r in rows],
    'volatility': [r[9] for r in rows],
    'label': [r[12] for r in rows]
}

import pandas as pd
df = pd.DataFrame(df_data)
df = df.replace([None], np.nan)
df = df.dropna(subset=['close', 'volume', 'label'])
labels = df['label'].values

# Candidate Pulse features
candidates = {}

# 1. Volatility Z-score (short vs long)
df['vol_float'] = pd.to_numeric(df['volatility'], errors='coerce')
rets = pd.to_numeric(df['close'], errors='coerce').pct_change()
df['vol_12'] = rets.rolling(12).std()
df['vol_48'] = rets.rolling(48).std()
df['vol_zscore_short'] = (df['vol_12'] - df['vol_48']) / (df['vol_48'] + 1e-10)
candidates['vol_zscore_short'] = df['vol_zscore_short'].values

# 2. Volume momentum (12h vs 48h)
vol = pd.to_numeric(df['volume'], errors='coerce')
candidates['vol_mom_ratio'] = (vol.rolling(12).mean() / (vol.rolling(48).mean() + 1e-10)).values

# 3. OI ROC (if available)
oi = pd.to_numeric(df['oi_roc'], errors='coerce')
if oi.notna().sum() > 100:
    candidates['oi_roc'] = oi.values
else:
    print("oi_roc: mostly null, skipping")

# 4. Price acceleration (ret change rate)
df['ret'] = pd.to_numeric(df['close'], errors='coerce').pct_change()
df['ret_accel'] = df['ret'].diff()
candidates['ret_accel'] = df['ret_accel'].values

# 5. Realized vol ratio (recent 6h vs 24h)
df['vol_6'] = rets.rolling(6).std()
df['vol_24'] = rets.rolling(24).std()
df['vol_ratio_6_24'] = df['vol_6'] / (df['vol_24'] + 1e-10)
candidates['vol_ratio_6_24'] = df['vol_ratio_6_24'].values

# 6. Volume spike (current vs MA20)
df['vol_spike'] = vol / (vol.rolling(20).mean() + 1e-10)
candidates['vol_spike'] = df['vol_spike'].values

print("\n--- Candidate IC scores (N~2000) ---")
best = None
best_abs = 0
for name, feat in candidates.items():
    mask = ~(np.isnan(feat) | np.isnan(labels))
    f_clean = feat[mask]
    l_clean = labels[mask]
    if len(f_clean) < 100:
        print(f"  {name}: insufficient data ({len(f_clean)})")
        continue
    ic, pval = stats.spearmanr(f_clean, l_clean)
    flag = "OK" if abs(ic) >= 0.05 and pval < 0.05 else "FAIL"
    print(f"  [{flag}] {name}: IC={ic:.4f} p={pval:.4f} N={len(f_clean)}")
    if abs(ic) > best_abs and pval < 0.05:
        best_abs = abs(ic)
        best = name

print(f"\nBest replacement: {best} (IC abs={best_abs:.4f})")
conn.close()
