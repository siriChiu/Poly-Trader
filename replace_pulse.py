"""Replace Pulse feat with vol_ratio (12h/48h vol ratio) - IC=0.0613, stable"""
import sqlite3, numpy as np, pandas as pd
from scipy import stats
from datetime import datetime

conn = sqlite3.connect(r"C:\Users\Kazuha\repo\Poly-Trader\poly_trader.db")

# Compute vol_ratio for all raw data
raw_rows = conn.execute("""
    SELECT id, timestamp, close_price FROM raw_market_data ORDER BY timestamp ASC
""").fetchall()

df = pd.DataFrame(raw_rows, columns=['id','ts','close'])
df['ts'] = pd.to_datetime(df['ts'], format='mixed')
df['close'] = pd.to_numeric(df['close'], errors='coerce')

rets = df['close'].pct_change()
df['vol12'] = rets.rolling(12).std()
df['vol48'] = rets.rolling(48).std()
df['vol_ratio'] = df['vol12'] / (df['vol48'] + 1e-10)
# Normalize to sigmoid-like [0,1]
import math
def sigmoid(x):
    return 1 / (1 + math.exp(-x)) if not np.isnan(x) else 0.5

df['feat_pulse_new'] = df['vol_ratio'].apply(lambda x: sigmoid(x * 3 - 1) if not np.isnan(x) else 0.5)

# Build ts -> feat_pulse_new map
ts_map = {}
for _, row in df.iterrows():
    ts_map[str(row['ts'])] = row['feat_pulse_new']

# Get feature timestamps
feat_rows = conn.execute("SELECT id, timestamp FROM features_normalized ORDER BY timestamp").fetchall()
print(f"Features to update: {len(feat_rows)}")

feat_ts_vals = [(fid, pd.to_datetime(fts, format='mixed')) for fid, fts in feat_rows]
raw_ts_arr = df['ts'].values

updated = 0
for fid, fts_dt in feat_ts_vals:
    diffs = np.abs(raw_ts_arr - np.datetime64(fts_dt))
    min_idx = np.argmin(diffs)
    min_diff_sec = diffs[min_idx] / np.timedelta64(1, 's')
    if min_diff_sec <= 600:
        new_val = df['feat_pulse_new'].iloc[min_idx]
        if not np.isnan(new_val):
            conn.execute("UPDATE features_normalized SET feat_pulse=? WHERE id=?", (float(new_val), fid))
            updated += 1

conn.commit()
print(f"Updated {updated}/{len(feat_rows)} rows")

# Verify IC with new values
lbl_rows = conn.execute("SELECT timestamp, label FROM labels WHERE horizon_hours=4 ORDER BY timestamp DESC LIMIT 5000").fetchall()
feat_rows2 = conn.execute("SELECT timestamp, feat_pulse FROM features_normalized ORDER BY timestamp DESC LIMIT 5000").fetchall()

lbl_df = pd.DataFrame(lbl_rows, columns=['ts','label'])
feat_df = pd.DataFrame(feat_rows2, columns=['ts','feat'])
lbl_df['ts'] = pd.to_datetime(lbl_df['ts'], format='mixed')
feat_df['ts'] = pd.to_datetime(feat_df['ts'], format='mixed')

merged = pd.merge_asof(lbl_df.sort_values('ts'), feat_df.sort_values('ts'), on='ts', direction='nearest', tolerance=pd.Timedelta('5min'))
merged = merged.dropna()

ic, pval = stats.spearmanr(merged['feat'].values, merged['label'].values)
print(f"\nNew Pulse IC (vol_ratio, N={len(merged)}): {ic:.4f} p={pval:.4f}")
flag = "OK" if abs(ic) >= 0.05 and pval < 0.05 else "WARN"
print(f"Status: [{flag}]")
conn.close()
