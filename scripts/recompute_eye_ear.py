"""
快速批量重算 Eye (fr_cumsum_48) 和 Ear (mom_24) 特徵
#H104 + #H105 修正後使用
"""
import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/Poly-Trader')
import sqlite3
import pandas as pd
import numpy as np

DB = '/home/admin/.openclaw/workspace/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(DB)

# Load raw data
print("Loading raw data...")
raw = pd.read_sql('SELECT timestamp, close_price, funding_rate FROM raw_market_data WHERE symbol="BTCUSDT" ORDER BY timestamp', conn)
print(f"Raw rows: {len(raw)}")

# Compute features
print("Computing features...")
raw['feat_eye_dist'] = raw['funding_rate'].rolling(48).sum()
raw['feat_ear_zscore'] = raw['close_price'].pct_change(24)

# Fill where not enough data
fr_mean = raw['funding_rate'].expanding(min_periods=8).mean()
raw['feat_eye_dist'] = raw['feat_eye_dist'].fillna(raw['funding_rate'].expanding().sum())

ear_fallback = raw['close_price'].pct_change(12)
raw['feat_ear_zscore'] = raw['feat_ear_zscore'].fillna(ear_fallback)

# Update DB
print("Updating features_normalized...")
cur = conn.cursor()
updated = 0
for _, row in raw.iterrows():
    if pd.isna(row['feat_eye_dist']) and pd.isna(row['feat_ear_zscore']):
        continue
    vals = []
    sets = []
    if not pd.isna(row['feat_eye_dist']):
        sets.append('feat_eye_dist=?')
        vals.append(float(row['feat_eye_dist']))
    if not pd.isna(row['feat_ear_zscore']):
        sets.append('feat_ear_zscore=?')
        vals.append(float(row['feat_ear_zscore']))
    vals.append(row['timestamp'])
    cur.execute(f"UPDATE features_normalized SET {', '.join(sets)} WHERE timestamp=?", vals)
    updated += cur.rowcount

conn.commit()
print(f"Updated {updated} rows")
conn.close()
print("Done!")
