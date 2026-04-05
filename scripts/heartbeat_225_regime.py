import sqlite3, numpy as np, pandas as pd, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "poly_trader.db")

conn = sqlite3.connect(DB_PATH)

feat = pd.read_sql_query("SELECT * FROM features_normalized ORDER BY rowid", conn)
labels_df = pd.read_sql_query("SELECT * FROM labels ORDER BY rowid", conn)

# Regime analysis
if 'regime_label' in feat.columns and 'body_label' in feat.columns:
    print(f"feat regime_label values: {feat['regime_label'].value_counts().to_dict()}")
    
# Align feat and labels - they have same rowid order
min_len = min(len(feat), len(labels_df))
feat_regime = feat['regime_label'].iloc[:min_len].dropna().values
label_sell = labels_df['label_sell_win'].iloc[:min_len].values

combined = pd.DataFrame({'sell_win': label_sell[:len(feat_regime)], 'regime': feat_regime})
combined_valid = combined.dropna()

print(f"\n=== Regime Sell Win Rates (aligned) ===")
for reg in sorted(combined_valid['regime'].unique()):
    mask = combined_valid['regime'] == reg
    rate = (combined_valid.loc[mask, 'sell_win'] == 1).mean()
    n = mask.sum()
    print(f"  {reg}: {rate*100:.1f}% (n={n})")

# Overall
print(f"\nGlobal rate: {combined_valid['sell_win'].mean()*100:.2f}% (n={len(combined_valid)})")

# Check feature versions
if 'feature_version' in feat.columns:
    print(f"\nFeature versions: {feat['feature_version'].value_counts().to_dict()}")

# Check if we have new data at the tail
raw = pd.read_sql_query("SELECT * FROM raw_market_data ORDER BY id", conn)
print(f"\nLatest raw data entry:")
print(f"  timestamp: {raw['timestamp'].iloc[-1]}")
print(f"  close_price: {raw['close_price'].iloc[-1]}")

# Count unique timestamps
print(f"\nRaw unique timestamps: {raw['timestamp'].nunique()}")
print(f"Feat unique timestamps: {feat['timestamp'].nunique()}")
print(f"Labels unique timestamps: {labels_df['timestamp'].nunique()}")

conn.close()
