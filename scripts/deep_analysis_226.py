#!/usr/bin/env python
"""Deep analysis script for heartbeat #226"""
import sqlite3, os, json
import numpy as np
from scipy.stats import pearsonr, kendalltau
from scipy import stats as sp_stats

DB_PATH = os.path.expanduser("~/.poly-trader/data/poly_trader.db")
if not os.path.exists(DB_PATH):
    for alt in ["/home/kazuha/Poly-Trader/data/poly_trader.db"]:
        if os.path.exists(alt):
            DB_PATH = alt
            break

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1. Basic counts
for table in ['raw_data', 'features', 'labels']:
    cur.execute(f'SELECT COUNT(*) FROM {table}')
    print(f"{table}: {cur.fetchone()[0]} rows")

# 2. Sell win rates
cur.execute('SELECT label_sell_win FROM labels ORDER BY rowid')
all_labels = [int(r[0]) for r in cur.fetchall()]
n = len(all_labels)
global_wr = sum(all_labels) / n if n else 0
print(f"\nGlobal sell_win: {global_wr:.4f} ({sum(all_labels)}/{n})")

# Last 100
last100 = all_labels[-100:]
l100_wr = sum(last100) / len(last100) if last100 else 0
# Last 500
last500 = all_labels[-500:]
l500_wr = sum(last500) / len(last500) if last500 else 0
print(f"Last 100 win rate: {l100_wr:.4f}")
print(f"Last 500 win rate: {l500_wr:.4f}")

# 3. Max and current losing streak
max_streak = 0
curr_streak = 0
for w in all_labels:
    if w == 0:
        curr_streak += 1
        max_streak = max(max_streak, curr_streak)
    else:
        curr_streak = 0
print(f"Max losing streak: {max_streak}")
print(f"Current losing streak: {curr_streak}")

# 4. Buy win rate
try:
    cur.execute('SELECT label_up FROM labels ORDER BY rowid')
    buy_labels = [int(r[0]) for r in cur.fetchall()]
    buy_wr = sum(buy_labels) / len(buy_labels) if buy_labels else 0
    print(f"Buy win rate: {buy_wr:.4f}")
except Exception as e:
    print(f"Buy win rate: N/A ({e})")

# 5. Get features and calculate ICs
cur.execute('SELECT * FROM features ORDER BY rowid LIMIT 1')
cols = [d[0] for d in cur.description]
print(f"\nFeature columns: {cols}")

sensor_cols = [c for c in cols if c.startswith('feat_')]
cur.execute(f'SELECT {",".join(sensor_cols)} FROM features ORDER BY rowid')
feat_data = cur.fetchall()

# Get labels
cur.execute('SELECT label_sell_win FROM labels ORDER BY rowid')
label_data = [r[0] for r in cur.fetchall()]

# Align lengths
min_len = min(len(feat_data), len(label_data))
print(f"Aligned length: {min_len}")

print(f"\n=== Global IC (Pearson, against label_sell_win) ===")
ics = {}
for ci, scol in enumerate(sensor_cols):
    vals = np.array([float(r[ci]) if r[ci] is not None else np.nan for r in feat_data[:min_len]])
    lvals = np.array([float(l) for l in label_data[:min_len]])
    mask = ~np.isnan(vals)
    if mask.sum() > 10:
        r, p = sp_stats.pearsonr(vals[mask], lvals[mask])
        status = "PASS" if abs(r) >= 0.05 else ("NEAR" if abs(r) >= 0.03 else "FAIL")
        ics[scol] = r
        print(f"  {scol:20s}: {r:+.4f} ({status})")

# 6. TW-IC (time-decay weighted, tau=200)
print(f"\n=== TW-IC (tau=200) ===")
for scol in sensor_cols:
    vals = np.array([float(r[cols.index(scol)]) if r[cols.index(scol)] is not None else np.nan for r in feat_data[:min_len]])
    lvals = np.array([float(l) for l in label_data[:min_len]])
    mask = ~np.isnan(vals)
    idx = np.arange(min_len)[mask]
    v = vals[mask]
    l = lvals[mask]
    weights = np.exp(-idx / 200.0)
    w_sum = np.sum(weights)
    if w_sum > 0 and len(v) > 10:
        wv_mean = np.sum(weights * v) / w_sum
        wl_mean = np.sum(weights * l) / w_sum
        w_cov = np.sum(weights * (v - wv_mean) * (l - wl_mean)) / w_sum
        w_var_v = np.sum(weights * (v - wv_mean)**2) / w_sum
        w_var_l = np.sum(weights * (l - wl_mean)**2) / w_sum
        if w_var_v > 0 and w_var_l > 0:
            tw_ic = w_cov / np.sqrt(w_var_v * w_var_l)
            status = "PASS" if abs(tw_ic) >= 0.05 else "FAIL"
            print(f"  {scol:20s}: {tw_ic:+.4f} ({status})")

# 7. Regime analysis
try:
    for table_name in ['labels', 'raw_data']:
        try:
            cur.execute(f'SELECT name FROM sqlite_master WHERE type="table" AND name="{table_name}"')
            if cur.fetchone():
                cur.execute(f'PRAGMA table_info({table_name})')
                tcols = [c[1] for c in cur.fetchall()]
                if 'regime' in tcols or 'label_regime' in tcols:
                    rc = 'regime' if 'regime' in tcols else 'label_regime'
                    cur.execute(f'SELECT {rc}, label_sell_win FROM {table_name}')
                    rows = cur.fetchall()
                    print(f"\n=== Regime Sell Win Rates ({table_name}) ===")
                    from collections import defaultdict
                    regime_data = defaultdict(list)
                    for reg, sw in rows:
                        if reg:
                            regime_data[reg].append(sw)
                    for reg, vals in sorted(regime_data.items()):
                        if vals:
                            wr = sum(vals) / len(vals)
                            print(f"  {reg:15s}: {wr:.1%} (n={len(vals)})")
                    break
        except:
            continue
except:
    pass

# 8. DXY, VIX from features
extra_features = ['feat_dxy', 'feat_vix', 'dxy_level', 'vix_level', 'dxy', 'vix']
for ef in extra_features:
    if ef in cols:
        cur.execute(f'SELECT {ef} FROM features ORDER BY rowid')
        vals = [r[0] for r in cur.fetchall() if r[0] is not None]
        if vals:
            lvals = [float(l) for l in label_data[:len(vals)]]
            vals = [float(v) for v in vals]
            r, p = sp_stats.pearsonr(vals, lvals[:len(vals)])
            print(f"  {ef:20s}: IC={r:+.4f}, n={len(vals)}")

# 9. Recent BTC price and market data
print(f"\n=== Latest Market Data ===")
cur.execute('SELECT close_price, volume, fear_greed_index FROM raw_data ORDER BY rowid DESC LIMIT 1')
row = cur.fetchone()
if row:
    print(f"  BTC close: ${row[0]:,.2f}" if row[0] else f"  BTC close: N/A")
    print(f"  FNG: {row[2]}" if row[2] else f"  FNG: N/A")

conn.close()
print("\n=== Analysis Complete ===")
