"""
重算 Pulse (v4) 和 Aura (v7) 特徵 — 直接操作 DB
Pulse: vol_roc48 (IC=+0.044)
Aura: vol_ratio_short_long (IC=+0.099)
"""
import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/Poly-Trader')

import sqlite3
import numpy as np
import pandas as pd

DB = '/home/admin/.openclaw/workspace/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

# Load raw data ordered by timestamp
raw = c.execute("SELECT timestamp, close_price, volume FROM raw_market_data ORDER BY timestamp").fetchall()
rdf = pd.DataFrame(raw, columns=['ts','price','volume'])
rdf['ts'] = pd.to_datetime(rdf['ts'])
rdf['price'] = pd.to_numeric(rdf['price'])
rdf['volume'] = pd.to_numeric(rdf['volume'])
rdf = rdf.sort_values('ts').reset_index(drop=True)

# Compute Pulse: vol_roc48
rdf['vol_roc48'] = rdf['volume'].pct_change(48)
rdf['feat_pulse_new'] = 1 / (1 + np.exp(-rdf['vol_roc48']))
rdf.loc[rdf['feat_pulse_new'].isna(), 'feat_pulse_new'] = 0.5

# Compute Aura: vol_ratio_short_long
rets = rdf['price'].pct_change()
vol_short = rets.rolling(12).std()
vol_long = rets.rolling(96).std()
vol_ratio = vol_short / (vol_long + 1e-10)
rdf['feat_aura_new'] = 1 / (1 + np.exp(-vol_ratio * 2 + 3))
rdf.loc[rdf['feat_aura_new'].isna(), 'feat_aura_new'] = 0.5

# Get feature timestamps
feat_ts = c.execute("SELECT id, timestamp FROM features_normalized ORDER BY timestamp").fetchall()
print(f"Total features to update: {len(feat_ts)}")

# Build lookup: raw timestamp -> (pulse, aura)
rdf['ts_str'] = rdf['ts'].astype(str)
pulse_map = dict(zip(rdf['ts_str'], rdf['feat_pulse_new']))
aura_map = dict(zip(rdf['ts_str'], rdf['feat_aura_new']))

# Match feature timestamps to raw data (nearest within 5 min)
rdf_ts = rdf['ts'].values  # numpy datetime64

updated = 0
for feat_id, feat_ts_str in feat_ts:
    feat_ts_dt = pd.to_datetime(feat_ts_str)
    # Find nearest raw timestamp
    diffs = np.abs(rdf_ts - np.datetime64(feat_ts_dt))
    min_idx = np.argmin(diffs)
    min_diff_sec = diffs[min_idx] / np.timedelta64(1, 's')
    if min_diff_sec <= 600:  # within 10 minutes
        pulse_val = rdf['feat_pulse_new'].iloc[min_idx]
        aura_val = rdf['feat_aura_new'].iloc[min_idx]
        if not np.isnan(pulse_val) and not np.isnan(aura_val):
            c.execute("UPDATE features_normalized SET feat_pulse=?, feat_aura=? WHERE id=?",
                      (float(pulse_val), float(aura_val), feat_id))
            updated += 1

conn.commit()
print(f"Updated {updated}/{len(feat_ts)} feature rows")

# Verify
check = c.execute("SELECT AVG(feat_pulse), AVG(feat_aura), COUNT(*) FROM features_normalized WHERE feat_pulse != 0").fetchone()
print(f"Post-update: avg_pulse={check[0]:.4f}, avg_aura={check[1]:.4f}, non-zero={check[2]}")
conn.close()
print("Done!")
