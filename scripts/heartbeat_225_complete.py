#!/usr/bin/env python3
"""
Heartbeat #225: Complete analysis for Six Hats & ORID

This script produces corrected metrics for:
- Sell win rate (global and recent)
- Global IC for all 8 core sensors
- TW-IC (time-weighted IC, tau=200)
- Consecutive loss tracking
- Regime-wise analysis
"""
import sqlite3
import numpy as np
import pandas as pd
import os, sys
from scipy.linalg import toeplitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "poly_trader.db")

conn = sqlite3.connect(DB_PATH)

raw = pd.read_sql_query("SELECT * FROM raw_market_data ORDER BY id", conn)
feat = pd.read_sql_query("SELECT * FROM features_normalized ORDER BY rowid", conn)
labels = pd.read_sql_query("SELECT * FROM labels ORDER BY rowid", conn)

n_raw, n_feat, n_labels = len(raw), len(feat), len(labels)
print(f"Raw: {n_raw} / Features: {n_feat} / Labels: {n_labels}")

# BTC Price
btc_price = raw['close_price'].dropna().iloc[-1]
print(f"BTC Price: ${btc_price:,.0f}")
fng = raw['fear_greed_index'].dropna().iloc[-1]
print(f"FNG: {fng:.0f}")
vix = raw['vix_value'].dropna().iloc[-1] if 'vix_value' in raw.columns else None
dxy = raw['dxy_value'].dropna().iloc[-1] if 'dxy_value' in raw.columns else None
fr = raw['funding_rate'].dropna().iloc[-1] if 'funding_rate' in raw.columns else None
print(f"VIX: {vix:.2f}" if vix is not None else "VIX: N/A")
print(f"DXY: {dxy:.2f}" if dxy is not None else "DXY: N/A")
print(f"FR: {fr:.6f}" if fr is not None else "FR: N/A")

# Sell win rate
sell_col = 'label_sell_win'
sell = labels[sell_col].astype(float).dropna()
n_sell = len(sell)
sell_win_rate = sell.mean()
print(f"\nsell_win: {sell_win_rate*100:.2f}% (n={n_sell})")

# Buy win rate
if 'label_up' in labels.columns:
    buy = labels['label_up'].astype(float).dropna()
    print(f"label_up (buy proxy): {buy.mean()*100:.2f}% (n={len(buy)})")

# Recent
sell_500 = sell.iloc[-500:]
sell_100 = sell.iloc[-100:]
print(f"Recent 500 win rate: {sell_500.mean()*100:.2f}%")
print(f"Recent 100 win rate: {sell_100.mean()*100:.2f}%")

# Consecutive losses
binary = sell.astype(int).values
streaks = []
current = 0
for v in binary:
    if v == 0:
        current += 1
    else:
        if current > 0:
            streaks.append(current)
        current = 0
if current > 0:
    streaks.append(current)
max_loss = max(streaks) if streaks else 0
import numpy
from numpy.lib.stride_tricks import sliding_window_view
_trailing = 0
if binary[-1] == 0:
    for v in reversed(binary[-100:]):  # check last 100
        if v == 0:
            _trailing += 1
        else:
            break
current_streak = _trailing
last_100_losses = (binary[-100:] == 0).sum()
last_100_loses = (binary[-100:] == 0).sum()
print(f"Max loss streak: {max_loss}")
print(f"Current trailing loss streak: {current_streak}")
print(f"Last 100 losses: {last_100_loses}/100")

# Regime analysis
if 'regime_label' in feat.columns:
    min_len = min(len(feat), len(labels))
    regime = feat['regime_label'].iloc[:min_len].values
    sell_aligned = labels[sell_col].iloc[:min_len].values
    combined = pd.DataFrame({'sell_win': sell_aligned, 'regime': regime}).dropna()
    print(f"\n=== Regime Win Rates ===")
    for reg in sorted(combined['regime'].unique()):
        mask = combined['regime'] == reg
        rate = combined.loc[mask, 'sell_win'].mean()
        print(f"  {reg}: {rate*100:.1f}% (n={mask.sum()})")

# Global IC
sensor_map = {
    'feat_eye': 'Eye', 'feat_ear': 'Ear', 'feat_nose': 'Nose',
    'feat_tongue': 'Tongue', 'feat_body': 'Body', 'feat_pulse': 'Pulse',
    'feat_aura': 'Aura', 'feat_mind': 'Mind', 'feat_vix': 'VIX',
    'feat_dxy': 'DXY', 'feat_rsi14': 'RSI14', 'feat_macd_hist': 'MACD_hist',
    'feat_atr_pct': 'ATR_pct', 'feat_vwap_dev': 'VWAP_dev', 'feat_bb_pct_b': 'BB_pct_b'
}

core_sensors = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body', 'Pulse', 'Aura', 'Mind']
feat_cols = [c for c in sensor_map if c in feat.columns]

print(f"\n=== Global IC (h=4) ===")
global_ics = {}
for col in feat_cols:
    vals = feat[col].dropna()
    if len(vals) < 100:
        continue
    idx = vals.index
    lbl = sell.reindex(idx).dropna()
    common = vals.index.intersection(lbl.index)
    if len(common) < 100:
        continue
    ic = vals.loc[common].corr(lbl.loc[common])
    if np.isnan(ic):
        continue
    global_ics[col] = ic
    sensor = sensor_map.get(col, 'Other')
    status = 'PASS' if abs(ic) >= 0.05 else ('NEAR' if abs(ic) >= 0.04 else 'FAIL')
    print(f"  {col:<18} {ic:+.4f}  [{sensor}] {status}")

global_pass = sum(1 for ic in global_ics.values() if abs(ic) >= 0.05)
print(f"\nPass: {global_pass}/{len(feat_cols)}")

# TW-IC (tau=200)
print(f"\n=== TW-IC (tau=200) ===")
def tw_ic_for_feature(feats, lbls):
    """Time-weighted IC with tau=200."""
    f = feats.values
    l = lbls.values
    f = f - np.mean(f)
    l = l - np.mean(l)
    n = len(f)
    idx = np.arange(n, dtype=float)
    w = np.exp(-idx / 200.0)
    w_sum = w.sum()
    # weighted covariance
    cov = np.dot(w * f, w * l) / w_sum
    std_f = np.sqrt(np.dot(w * f, w * f) / w_sum)
    std_l = np.sqrt(np.dot(w * l, w * l) / w_sum)
    if std_f == 0 or std_l == 0:
        return 0.0
    return cov / (std_f * std_l)

tw_pass = 0
for sensor in core_sensors:
    cols = [c for c, s in sensor_map.items() if s == sensor and c in global_ics]
    if not cols:
        continue
    tw_vals = []
    for col in cols:
        vals = feat[col].dropna()
        idx = vals.index
        lbl = sell.reindex(idx).dropna()
        common = vals.index.intersection(lbl.index)
        if len(common) < 100:
            continue
        ic_tw = tw_ic_for_feature(vals.loc[common], lbl.loc[common])
        tw_vals.append(ic_tw)
    if tw_vals:
        mean_tw = np.mean(tw_vals)
        status = 'PASS' if abs(mean_tw) >= 0.05 else 'FAIL'
        if abs(mean_tw) >= 0.05:
            tw_pass += 1
        print(f"  {sensor}: {mean_tw:+.4f} ({status})")

print(f"TW-IC Pass: {tw_pass}/{len(core_sensors)}")

# Output structured data for the report
print(f"\n=== STRUCTURED ===")
print(f"RAW:{n_raw}|FEATURES:{n_feat}|LABELS:{n_labels}")
print(f"SELL_WIN:{sell_win_rate*100:.2f}%")
print(f"RECENT_100:{sell_100.mean()*100:.2f}%")
print(f"RECENT_500:{sell_500.mean()*100:.2f}%")
print(f"MAX_LOSS_STREAK:{max_loss}")

conn.close()
