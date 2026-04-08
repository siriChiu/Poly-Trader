#!/usr/bin/env python3
"""Heartbeat #211 — full analysis with IC, regime, model, and ORID."""
import sqlite3, json, numpy as np

db_path = '/home/kazuha/Poly-Trader/poly_trader.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# === Data counts ===
raw_count = conn.execute('SELECT COUNT(*) as c FROM raw_market_data').fetchone()['c']
feat_count = conn.execute('SELECT COUNT(*) as c FROM features_normalized').fetchone()['c']
label_count = conn.execute('SELECT COUNT(*) as c FROM labels').fetchone()['c']
merged_count = conn.execute("""
    SELECT COUNT(*) as c FROM features_normalized f
    INNER JOIN labels l ON f.timestamp = l.timestamp
""").fetchone()['c']

# BTC price
row = conn.execute('SELECT close_price, fear_greed_index, funding_rate, vix_value, dxy_value, body_label, oi_roc, polymarket_prob FROM raw_market_data ORDER BY id DESC LIMIT 1').fetchone()
btc_price = row['close_price'] if row and row['close_price'] else 0
fng_raw = row['fear_greed_index'] if row and row['fear_greed_index'] else 0
fng_val = int(fng_raw) if fng_raw else 0
if fng_val <= 25: fng_class = 'Extreme Fear'
elif fng_val <= 45: fng_class = 'Fear'
elif fng_val <= 55: fng_class = 'Neutral'
elif fng_val <= 75: fng_class = 'Greed'
else: fng_class = 'Extreme Greed'

funding_rate = row['funding_rate'] if row and row['funding_rate'] else 0
vix_value = row['vix_value'] if row and row['vix_value'] else 0
dxy_value = row['dxy_value'] if row and row['dxy_value'] else 0
oi_roc = row['oi_roc'] if row and row['oi_roc'] else 0
body_label_raw = row['body_label'] if row else 'N/A'
polymarket = row['polymarket_prob'] if row and row['polymarket_prob'] else 0

print(f"BTC=${btc_price:.0f} FNG={fng_val} ({fng_class}) Funding={funding_rate:.4%} VIX={vix_value} DXY={dxy_value}")
print(f"OI ROC={oi_roc:.4%} Polymarket={polymarket:.3f} Body={body_label_raw}")

# Sell_win stats
sell_win_row = conn.execute('SELECT AVG(label_spot_long_win) as avg_sw, COUNT(*) as cnt FROM labels WHERE label_spot_long_win IS NOT NULL').fetchone()
global_sw = sell_win_row['avg_sw']

recent = conn.execute('SELECT label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id DESC LIMIT 50').fetchall()
recent_vals = [r['label_spot_long_win'] for r in recent if r['label_spot_long_win'] is not None]
recent_sw = sum(recent_vals) / len(recent_vals) if recent_vals else 0

recent100 = conn.execute('SELECT label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id DESC LIMIT 100').fetchall()
recent100_vals = [r['label_spot_long_win'] for r in recent100 if r['label_spot_long_win'] is not None]
recent100_sw = sum(recent100_vals) / len(recent100_vals) if recent100_vals else 0

recent500 = conn.execute('SELECT label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id DESC LIMIT 500').fetchall()
recent500_vals = [r['label_spot_long_win'] for r in recent500 if r['label_spot_long_win'] is not None]
recent500_sw = sum(recent500_vals) / len(recent500_vals) if recent500_vals else 0

# Consecutive zeros
all_sw = conn.execute('SELECT label_spot_long_win FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id DESC').fetchall()
consec_zeros = 0
for v in [r['label_spot_long_win'] for r in all_sw]:
    if v == 0: consec_zeros += 1
    else: break

# NULL regime labels
null_regime_count = conn.execute('SELECT COUNT(*) as c FROM labels WHERE regime_label IS NULL').fetchone()['c']

# Sell_win by regime
regime_sw = conn.execute("SELECT regime_label, AVG(label_spot_long_win) as avg_sw, COUNT(*) as cnt FROM labels WHERE label_spot_long_win IS NOT NULL GROUP BY regime_label").fetchall()
regime_sw_dict = {}
for r in regime_sw:
    regime_sw_dict[r['regime_label'] or 'NULL'] = {'avg_sw': r['avg_sw'], 'n': r['cnt']}

# === IC Analysis ===
feature_cols = [
    'feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body',
    'feat_pulse', 'feat_aura', 'feat_mind',
    'feat_vix', 'feat_dxy', 'feat_rsi14', 'feat_macd_hist',
    'feat_atr_pct', 'feat_vwap_dev', 'feat_bb_pct_b'
]

feat_rows = conn.execute(
    f"SELECT id, timestamp, {', '.join(feature_cols)} FROM features_normalized ORDER BY id"
).fetchall()

label_rows = conn.execute(
    "SELECT id, timestamp, label_spot_long_win, regime_label FROM labels WHERE label_spot_long_win IS NOT NULL ORDER BY id"
).fetchall()

feat_ts = {r['timestamp']: r for r in feat_rows}
label_ts = {r['timestamp']: r for r in label_rows}
common_ts = sorted(set(feat_ts.keys()) & set(label_ts.keys()))

n = len(common_ts)
sell_win_arr = np.array([label_ts[ts]['label_spot_long_win'] for ts in common_ts], dtype=float)

ic_results = []
for fc in feature_cols:
    raw_vals = [feat_ts[ts][fc] for ts in common_ts]
    vals = np.array([float(v) if v is not None else float('nan') for v in raw_vals])
    mask = np.isfinite(vals) & np.isfinite(sell_win_arr)
    v = vals[mask]
    s = sell_win_arr[mask]
    if len(v) < 100:
        continue
    std_val = float(np.std(v))
    if std_val > 1e-10:
        ic = float(np.corrcoef(v, s)[0, 1])
        if np.isnan(ic): ic = 0.0
    else:
        ic = 0.0
    passed = abs(ic) >= 0.05
    ic_results.append({
        'name': fc,
        'ic': round(ic, 4),
        'std': round(std_val, 4),
        'n': len(v),
        'passed': passed,
    })

passed_count = sum(1 for r in ic_results if r['passed'])

# === Regime IC ===
regimes = ['bear', 'bull', 'chop', 'neutral']
regime_ic = {}
for regime in regimes:
    reg_mask = np.array([label_ts[ts]['regime_label'] == regime for ts in common_ts])
    if reg_mask.sum() < 100:
        regime_ic[regime] = {'passed': 0, 'total': len(feature_cols), 'n': int(reg_mask.sum())}
        continue
    
    reg_sw = sell_win_arr[reg_mask]
    reg_passed = 0
    reg_features = []
    for fc in feature_cols:
        raw_vals = [feat_ts[ts][fc] for ts in common_ts]
        vals = np.array([float(v) if v is not None else float('nan') for v in raw_vals])[reg_mask]
        mask = np.isfinite(vals) & np.isfinite(reg_sw)
        v = vals[mask]
        s = reg_sw[mask]
        if len(v) < 50: continue
        if np.std(v) > 1e-10:
            ic = float(np.corrcoef(v, s)[0, 1])
            if np.isnan(ic): ic = 0
            if abs(ic) >= 0.05:
                reg_passed += 1
                reg_features.append(f"{fc}={ic:+.3f}")
    regime_ic[regime] = {'passed': reg_passed, 'total': len(feature_cols), 'n': int(reg_mask.sum()), 'features': reg_features[:5]}

# === Dynamic window IC ===
dynamic_window_ic = {}
for window in [500, 1000, 2000, 5000]:
    if n < window: continue
    sub_sw = sell_win_arr[-window:]
    sub_n = len(sub_sw)
    dw_passed = 0
    for fc in feature_cols:
        raw_vals = [feat_ts[ts][fc] for ts in common_ts][-window:]
        vals = np.array([float(v) if v is not None else float('nan') for v in raw_vals])
        mask = np.isfinite(vals) & np.isfinite(sub_sw)
        v = vals[mask]
        s = sub_sw[mask]
        if len(v) < 50: continue
        if np.std(v) > 1e-10:
            ic = float(np.corrcoef(v, s)[0, 1])
            if np.isnan(ic): ic = 0
            if abs(ic) >= 0.05:
                dw_passed += 1
    reg_mask = np.array([label_ts[ts]['regime_label'] is not None for ts in common_ts])[-window:]
    sub_sw_mask = sub_sw  # use as is
    
    # Calculate sell_win for this window
    sub_sw_mean = float(np.mean(sub_sw))
    dynamic_window_ic[f'N={window}'] = {'passed': dw_passed, 'total': len(feature_cols), 'sell_win': round(sub_sw_mean, 3)}

# === Model metrics ===
metric = conn.execute('SELECT * FROM model_metrics ORDER BY id DESC LIMIT 1').fetchone()
cv_acc = round(metric['cv_accuracy'] * 100, 1) if metric else 0
cv_std_val = round(metric['cv_std'] * 100, 1) if metric and metric['cv_std'] else 0
train_acc = round(metric['train_accuracy'] * 100, 1) if metric else 0
overfit_gap = round(train_acc - cv_acc, 1) if metric else 0

# === Output ===
print(f"RAW={raw_count} FEAT={feat_count} LABELS={label_count} MERGED={merged_count}")
print(f"BTC=${btc_price} FNG={fng_val} ({fng_class})")
print(f"GLOBAL_SW={global_sw:.3f} LAST50={recent_sw:.3f} LAST100={recent100_sw:.3f} LAST500={recent500_sw:.3f}")
print(f"CONSEC_ZEROS={consec_zeros}")
print(f"NULL_REGIME={null_regime_count}")
print(f"IC_PASSED={passed_count}/{len(ic_results)}")
print(f"CV={cv_acc}%±{cv_std_val}% TRAIN={train_acc}% OVERFIT={overfit_gap}pp")

print()
for r in sorted(ic_results, key=lambda x: abs(x['ic']), reverse=True):
    status = "PASS" if r['passed'] else "FAIL"
    print(f"  {r['name']:20s} IC={r['ic']:+.4f} std={r['std']:.4f} {status}")

print()
for reg, info in regime_ic.items():
    feat_str = ', '.join(info.get('features', []))
    print(f"  {reg}: {info['passed']}/{info['total']} (n={info['n']}){': ' + feat_str if feat_str else ''}")

print()
for w, info in dynamic_window_ic.items():
    print(f"  {w}: {info['passed']}/{info['total']} sell_win={info['sell_win']}")

# Save JSON
output = {
    'raw_count': raw_count, 'feat_count': feat_count, 'label_count': label_count,
    'merged_count': merged_count, 'btc_price': btc_price, 'fng_value': fng_val,
    'fng_class': fng_class, 'global_sell_win': round(global_sw, 3),
    'recent_sell_win_50': round(recent_sw, 3), 'recent_sell_win_100': round(recent100_sw, 3),
    'recent_sell_win_500': round(recent500_sw, 3), 'consecutive_zeros': consec_zeros,
    'null_regime_labels': null_regime_count, 'ic_passed': passed_count,
    'ic_total': len(ic_results), 'feature_ics': ic_results,
    'regime_ic': regime_ic, 'dynamic_window_ic': dynamic_window_ic, 'sell_win_by_regime': regime_sw_dict,
    'model_cv': cv_acc, 'model_cv_std': cv_std_val, 'model_train': train_acc,
    'model_overfit': overfit_gap,
}
with open('/tmp/hb211_data.json', 'w') as f:
    json.dump(output, f, indent=2)
print("\nData saved to /tmp/hb211_data.json")
conn.close()
