"""Find best Pulse replacement"""
import sqlite3, numpy as np, pandas as pd
from scipy import stats

conn = sqlite3.connect(r"C:\Users\Kazuha\repo\Poly-Trader\poly_trader.db")

raw_rows = conn.execute("""
    SELECT timestamp, close_price, volume, funding_rate
    FROM raw_market_data ORDER BY timestamp DESC LIMIT 12000
""").fetchall()

lbl_rows = conn.execute("""
    SELECT timestamp, label FROM labels WHERE horizon_hours = 4
    ORDER BY timestamp DESC LIMIT 12000
""").fetchall()

raw_df = pd.DataFrame(raw_rows, columns=['ts','close','volume','fr'])
lbl_df = pd.DataFrame(lbl_rows, columns=['ts','label'])
raw_df['ts'] = pd.to_datetime(raw_df['ts'], format='mixed')
lbl_df['ts'] = pd.to_datetime(lbl_df['ts'], format='mixed')

raw_df = raw_df.sort_values('ts').reset_index(drop=True)
raw_df['close'] = pd.to_numeric(raw_df['close'], errors='coerce')
raw_df['volume'] = pd.to_numeric(raw_df['volume'], errors='coerce')
raw_df['fr'] = pd.to_numeric(raw_df['fr'], errors='coerce')

rets = raw_df['close'].pct_change()
vol = raw_df['volume']

raw_df['vol12'] = rets.rolling(12).std()
raw_df['vol48'] = rets.rolling(48).std()
raw_df['vol_ratio'] = raw_df['vol12'] / (raw_df['vol48'] + 1e-10)
raw_df['vol_mom'] = vol.rolling(6).mean() / (vol.rolling(48).mean() + 1e-10)
raw_df['vol_spike6'] = vol / (vol.rolling(6).mean() + 1e-10)
raw_df['ret_6'] = raw_df['close'].pct_change(6)
raw_df['vol24'] = rets.rolling(24).std()
raw_df['vol_ratio_12_24'] = raw_df['vol12'] / (raw_df['vol24'] + 1e-10)
raw_df['fr_abs'] = raw_df['fr'].abs()
raw_df['fr_zscore'] = (raw_df['fr'] - raw_df['fr'].rolling(48).mean()) / (raw_df['fr'].rolling(48).std() + 1e-10)

lbl_df = lbl_df.sort_values('ts').reset_index(drop=True)
merged = pd.merge_asof(lbl_df, raw_df, on='ts', direction='nearest', tolerance=pd.Timedelta('5min'))
merged = merged.dropna(subset=['close'])
print(f"Merged rows: {len(merged)}")

candidates = ['vol_ratio', 'vol_mom', 'vol_spike6', 'ret_6', 'vol_ratio_12_24', 'fr_abs', 'fr_zscore']
N = min(5000, len(merged))
merged_recent = merged.tail(N)

print(f"\n--- Candidate Pulse ICs (N={len(merged_recent)}) ---")
best = None
best_ic = 0
for cand in candidates:
    sub = merged_recent[['label', cand]].dropna()
    if len(sub) < 100:
        print(f"  {cand}: insufficient ({len(sub)})")
        continue
    ic, pval = stats.spearmanr(sub[cand].values, sub['label'].values)
    flag = "OK" if abs(ic) >= 0.05 and pval < 0.05 else "FAIL"
    print(f"  [{flag}] {cand}: IC={ic:.4f} p={pval:.4f} N={len(sub)}")
    if abs(ic) > abs(best_ic) and pval < 0.05:
        best_ic = ic
        best = cand

print(f"\nBest candidate: {best} IC={best_ic:.4f}")
conn.close()
