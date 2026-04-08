import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "/home/kazuha/Poly-Trader/poly_trader.db"
conn = sqlite3.connect(DB_PATH)

# Get BTC price
try:
    raw = pd.read_sql_query("SELECT close_price FROM raw_market_data ORDER BY id DESC LIMIT 5", conn)
    btc_close = float(raw.iloc[-1]['close_price'])
    print(f"BTC current: ${btc_close:,.0f}")
except Exception as e:
    print(f"BTC price error: {e}")
    btc_close = 0

# Get FNG
try:
    raw = pd.read_sql_query("SELECT fear_greed_index FROM raw_market_data ORDER BY id DESC LIMIT 5", conn)
    fng = float(raw.iloc[-1]['fear_greed_index'])
    print(f"FNG: {fng:.0f}")
except:
    print("FNG: N/A")
    fng = 0

# Get funding rate
try:
    raw = pd.read_sql_query("SELECT funding_rate FROM raw_market_data ORDER BY id DESC LIMIT 5", conn)
    fr = float(raw.iloc[-1]['funding_rate'])
    print(f"Funding rate: {fr:.8f}")
except:
    print("Funding rate: N/A")
    fr = 0

# Derivatives data - check what's available
try:
    cols = pd.read_sql_query("PRAGMA table_info(raw_market_data)", conn)
    print(f"Raw columns: {list(cols['name'])}")
except:
    pass

# Get features and labels
features = pd.read_sql_query("SELECT * FROM features_normalized ORDER BY id", conn)
labels = pd.read_sql_query("SELECT * FROM labels ORDER BY id", conn)
print(f"\nFeatures: {len(features)}, Labels: {len(labels)}")

# Join - check if feature_id exists in labels
print(f"Label columns: {list(labels.columns)}")
print(f"Feature columns: {list(features.columns[:5])}")

# Merge strategy
common = set(features.columns) & set(labels.columns)
print(f"Common columns: {common}")

# Use id from features and feature_id from labels
if 'feature_id' in labels.columns:
    merged = features.merge(labels, left_on='id', right_on='feature_id', how='inner')
else:
    # Try timestamp join
    if 'timestamp' in features.columns and 'timestamp' in labels.columns:
        merged = features.merge(labels, on='timestamp', how='inner')
        print("Joined on timestamp")
    else:
        # Positional join
        min_len = min(len(features), len(labels))
        merged = features.iloc[:min_len].copy()
        for col in labels.columns:
            if col not in features.columns:
                merged[col] = labels[col].iloc[:min_len].values
        print(f"Positional join, {min_len} rows")

print(f"Merged: {len(merged)} rows")

# Check the join quality
if 'label_spot_long_win' in merged.columns:
    print(f"sell_win rate: {merged['label_spot_long_win'].mean():.1%}")
    print(f"sell_win value counts: {dict(merged['label_spot_long_win'].value_counts())}")

# Regime-aware IC
regime_col = next((c for c in ['regime_label', 'regime'] if c in merged.columns), None)
print(f"Regime column: {regime_col}")

senses_map = {
    'eye': 'feat_eye', 'ear': 'feat_ear', 'nose': 'feat_nose',
    'tongue': 'feat_tongue', 'body': 'feat_body', 'pulse': 'feat_pulse',
    'aura': 'feat_aura', 'mind': 'feat_mind'
}

global_ics = {}
if 'label_spot_long_win' in merged.columns:
    label = merged['label_spot_long_win'].astype(float)
    
    print("\n=== Global IC ===")
    for sname, col_name in senses_map.items():
        if col_name not in merged.columns:
            continue
        col = merged[col_name].astype(float)
        mask = col.notna() & label.notna()
        if mask.sum() > 10:
            ic = col[mask].corr(label[mask])
            std = col[mask].std()
            unique = col[mask].nunique()
            status = "PASS" if abs(ic) >= 0.05 else ("WARN" if abs(ic) >= 0.04 else "FAIL")
            global_ics[sname] = ic
            print(f"  {sname:6s}: IC={ic:+.4f} {status} | std={std:.4f} | unique={unique} | N={mask.sum()}")
    
    passed = sum(1 for v in global_ics.values() if abs(v) >= 0.05)
    print(f"\nGlobal passed: {passed}/8")
    
    # Regime-aware
    if regime_col:
        print(f"\n=== Regime-Aware IC ===")
        for regime in ['bear', 'bull', 'chop']:
            reg_mask = merged[regime_col].astype(str).str.strip().str.lower() == regime
            regime_passed = 0
            regime_passing = []
            for sname, col_name in senses_map.items():
                if col_name not in merged.columns:
                    continue
                col = merged[col_name].astype(float)
                mask = reg_mask & col.notna() & label.notna()
                if mask.sum() > 10:
                    ic = col[mask].corr(label[mask])
                    if abs(ic) >= 0.05:
                        regime_passed += 1
                        regime_passing.append(f"{sname}({ic:+.4f})")
            print(f"  {regime.capitalize()}: {regime_passed}/8 - {regime_passing}")

    # Dynamic window
    print(f"\n=== Dynamic Window IC ===")
    for win in [100, 500, 1000, 2000, 3000, 5000]:
        subset = merged.tail(win)
        passed_win = 0
        passing = []
        for sname, col_name in senses_map.items():
            if col_name not in subset.columns:
                continue
            col = subset[col_name].astype(float)
            l_sub = subset['label_spot_long_win'].astype(float)
            mask = col.notna() & l_sub.notna()
            if mask.sum() > 10:
                ic = col[mask].corr(l_sub[mask])
                if abs(ic) >= 0.05:
                    passed_win += 1
                    passing.append(f"{sname}({ic:+.4f})")
        print(f"  N={win}: {passed_win}/8 - {passing}")

conn.close()
