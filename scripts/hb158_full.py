#!/usr/bin/env python3
"""Heartbeat #158: Full sensory analysis including auxiliary senses."""
import sqlite3, json, numpy as np

db = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')

# All feature cols (8 core + 8 auxiliary + VIX + DXY + regime)
all_sense_cols = ['feat_eye', 'feat_ear', 'feat_nose', 'feat_tongue', 'feat_body', 'feat_pulse', 'feat_aura', 'feat_mind']
aux_cols = ['feat_whisper', 'feat_tone', 'feat_chorus', 'feat_hype', 'feat_oracle', 'feat_shock', 'feat_tide', 'feat_storm']
extra_cols = ['feat_vix', 'feat_dxy']
all_cols = all_sense_cols + aux_cols + extra_cols
all_names = ['Eye','Ear','Nose','Tongue','Body','Pulse','Aura','Mind',
             'whisper','tone','chorus','hype','oracle','shock','tide','storm',
             'VIX','DXY']

# Get features with timestamps
select_cols = ', '.join(['timestamp'] + all_cols + ['regime_label'])
feat_rows = db.execute(f"SELECT {select_cols} FROM features_normalized ORDER BY timestamp").fetchall()

# Get labels
label_rows = db.execute("SELECT timestamp, label_spot_long_win FROM labels ORDER BY timestamp").fetchall()
label_dict = {row[0]: row[1] for row in label_rows}

# Match
common_ts = sorted(set(r[0] for r in feat_rows) & set(label_dict.keys()))
print(f"Matched: {len(common_ts)} / {len(feat_rows)}")

# Build feature lookup
feat_lookup = {}
regime_lookup = {}
for row in feat_rows:
    ts = row[0]
    feat_lookup[ts] = {all_cols[i]: row[1+i] for i in range(len(all_cols))}
    regime_lookup[ts] = row[-1]

# Check auxiliary senses for constant/zero behavior
print("\n=== Auxiliary Senses Status ===")
for col, name in zip(aux_cols, all_names[8:16]):
    vals = [feat_lookup[ts].get(col) for ts in common_ts if feat_lookup[ts].get(col) is not None]
    if len(vals) == 0:
        print(f"  {name}: no data")
        continue
    vals_f = [float(v) for v in vals]
    unique = len(set(vals_f))
    std = np.std(vals_f)
    mean = np.mean(vals_f)
    min_v, max_v = min(vals_f), max(vals_f)
    flag = "🔴 DEAD" if std < 1e-10 or unique == 1 else ("⚠️ low variance" if std < 0.001 else "✅")
    print(f"  {name}: mean={mean:.6f} std={std:.6f} unique={unique}/{len(vals_f)} range=[{min_v:.6f},{max_v:.6f}] {flag}")

# All senses IC
print(f"\n=== Full IC (N={len(common_ts)}) - All 18 Senses ===")
ics = {}
for col, name in zip(all_cols, all_names):
    pairs = []
    for ts in common_ts:
        fval = feat_lookup[ts].get(col)
        lval = label_dict.get(ts)
        if fval is not None and lval is not None:
            pairs.append((float(fval), float(lval)))
    if len(pairs) < 10:
        continue
    x = [p[0] for p in pairs]
    y = [p[1] for p in pairs]
    if np.std(x) < 1e-10:
        ics[name] = {'ic': None, 'std': np.std(x), 'n': len(pairs), 'status': 'CONSTANT'}
        print(f"  {name}: IC=NaN (CONSTANT) n={len(pairs)}")
        continue
    ic = float(np.corrcoef(x, y)[0, 1])
    flag = " ✅" if abs(ic) >= 0.05 else ""
    ics[name] = {'ic': round(ic, 4), 'std': round(float(np.std(x)), 4), 'n': len(pairs), 'status': 'PASS' if abs(ic) >= 0.05 else 'FAIL'}
    print(f"  {name}: IC={ic:+.4f}{flag} n={len(pairs)}")

# Dynamic window scan
print("\n=== Dynamic Window IC ===")
windows = [200, 300, 400, 500, 600, 800, 1000, 2000]
for w in windows:
    if w >= len(common_ts):
        continue
    window_ts = common_ts[-w:]
    passed = 0
    pass_list = []
    for col, name in zip(all_sense_cols, all_names[:8]):
        pairs = []
        for ts in window_ts:
            fval = feat_lookup[ts].get(col)
            lval = label_dict.get(ts)
            if fval is not None and lval is not None:
                pairs.append((float(fval), float(lval)))
        if len(pairs) < 30:
            continue
        x = [p[0] for p in pairs]
        y = [p[1] for p in pairs]
        if np.std(x) < 1e-10:
            continue
        ic = float(np.corrcoef(x, y)[0, 1])
        if abs(ic) >= 0.05:
            passed += 1
            pass_list.append(f'{name}({ic:+.3f})')
    print(f"  N={w}: {passed}/8 pass [{', '.join(pass_list) if pass_list else 'ALL FAIL'}]")

# Market data
print("\n=== Latest Market Data ===")
c = db.cursor()
c.execute("SELECT close_price, fear_greed_index, funding_rate, oi_roc, polymarket_prob, timestamp FROM raw_market_data ORDER BY timestamp DESC LIMIT 1")
row = c.fetchone()
if row:
    print(f"  BTC Price: ${row[0]}")
    print(f"  FNG: {row[1]}")
    print(f"  Funding Rate: {row[2]}")
    print(f"  OI ROC: {row[3]}")
    print(f"  Polymarket: {row[4]}")
    print(f"  Timestamp: {row[5]}")

# Model metrics
c.execute("SELECT cv_accuracy, cv_std, notes, timestamp FROM model_metrics ORDER BY timestamp DESC LIMIT 3")
metrics = c.fetchall()
print("\n=== Recent Model Metrics ===")
for m in metrics:
    print(f"  CV Acc: {m[0]} (std={m[1]}) - {m[2]} - {m[3]}")

# Trade history
c.execute("SELECT COUNT(*) FROM trade_history")
trade_count = c.fetchone()[0]
print(f"\n=== Trades: {trade_count} ===")

# Feature and label counts
c.execute("SELECT COUNT(*) FROM features_normalized")
feat_count = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM labels")
label_count = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM raw_market_data")
raw_count = c.fetchone()[0]
c.execute("SELECT AVG(label_spot_long_win) FROM labels WHERE label_spot_long_win IS NOT NULL")
swr = c.fetchone()[0]

print(f"\n=== Pipeline Summary ===")
print(f"  Raw: {raw_count}")
print(f"  Features: {feat_count}")
print(f"  Labels: {label_count} (sell_win rate: {swr:.4f})")

# VIX, DXY IC 
print("\n=== VIX & DXY ===")
c.execute("SELECT vix_value, dxy_value FROM raw_market_data WHERE vix_value IS NOT NULL AND dxy_value IS NOT NULL LIMIT 1000")
vd_rows = c.fetchall()

db.close()
print("\n=== Heartbeat #158 Analysis Complete ===")
