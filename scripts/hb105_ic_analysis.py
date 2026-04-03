"""Fresh IC analysis with full stats - Heartbeat #105"""
import json, os, sys, math
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

from sqlalchemy import create_engine
import pandas as pd
import numpy as np
from datetime import datetime

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
engine = create_engine(f'sqlite:///{DB_PATH}')

features_df = pd.read_sql('SELECT * FROM features_normalized', engine)
labels_df = pd.read_sql('SELECT * FROM labels', engine)

# Normalize timestamps
features_df['ts_key'] = pd.to_datetime(features_df['timestamp'], format='mixed').dt.floor('s')
labels_df['ts_key'] = pd.to_datetime(labels_df['timestamp'], format='mixed').dt.floor('s')
data = features_df.merge(labels_df, on='ts_key', suffixes=('_feat', '_label'))

print(f"Merged records: {len(data)}")

sensory_features = {
    'feat_eye': 'Eye', 'feat_ear': 'Ear', 'feat_nose': 'Nose',
    'feat_tongue': 'Tongue', 'feat_body': 'Body', 'feat_pulse': 'Pulse',
    'feat_aura': 'Aura', 'feat_mind': 'Mind'
}

label_col = 'label_up'
data_sorted = data.sort_values('timestamp_feat', ascending=False)

# Full IC
ics_full = {}
stats = {}
print(f"\n{'='*70}")
print(f"Full Dataset IC (N={len(data)})")
print(f"{'='*70}")
for feat_col, sense_name in sensory_features.items():
    valid = data[[feat_col, label_col]].dropna()
    n = len(valid)
    ic = valid[feat_col].corr(valid[label_col])
    std = valid[feat_col].std()
    vals = valid[feat_col].dropna()
    unique = vals.nunique()
    rng = [float(vals.min()), float(vals.max())]
    
    status = "PASS" if abs(ic) >= 0.05 else "FAIL"
    print(f"  {sense_name:8s}: IC={ic:+.4f} | std={std:.4f} | unique={unique} | range=[{rng[0]:.4f}, {rng[1]:.4f}] | {status}")
    
    ics_full[sense_name] = round(float(ic), 4)
    stats[sense_name] = {
        'ic': round(float(ic), 4), 'n': n, 'std': round(float(std), 4),
        'unique': int(unique), 'range': [round(rng[0], 4), round(rng[1], 4)],
        'status': status
    }

# Recent IC (N=5000)
data_recent = data_sorted.head(5000)
ics_recent = {}
print(f"\n{'='*70}")
print(f"Recent Data IC (last 5000)")
print(f"{'='*70}")
for feat_col, sense_name in sensory_features.items():
    valid = data_recent[[feat_col, label_col]].dropna()
    n = len(valid)
    ic = valid[feat_col].corr(valid[label_col])
    print(f"  {sense_name:8s}: IC={ic:+.4f} (n={n})")
    ics_recent[sense_name] = round(float(ic), 4)

# Label distribution
print(f"\n{'='*70}")
print(f"Label Distribution")
print(f"{'='*70}")
label_counts = data[label_col].value_counts()
print(label_counts)
print(f"Positive rate: {(data[label_col]==1).mean():.4f}")

# Current market data
raw_market = pd.read_sql('SELECT * FROM raw_market_data', engine)
if len(raw_market) > 0:
    latest_row = raw_market.sort_values('timestamp', ascending=False).iloc[0]
    print(f"\nLatest Market Data:")
    print(f"  BTC Price: ${latest_row['close_price']:,.2f}")
    print(f"  Volume: {latest_row['volume']:,.0f}")
    print(f"  Funding Rate: {latest_row['funding_rate']:.6f}")
    print(f"  Fear & Greed Index: {latest_row['fear_greed_index']:.1f}")
    if pd.notna(latest_row.get('polymarket_prob', None)):
        print(f"  Polymarket Prob: {latest_row['polymarket_prob']:.4f}")

# Save comprehensive results
result = {
    'timestamp': datetime.now().isoformat(),
    'n_records': len(data),
    'n_matched': len(data),
    'ics_full': ics_full,
    'ics_recent': ics_recent,
    'stats': stats,
    'label_distribution': {str(k): int(v) for k, v in label_counts.items()},
    'positive_rate': round(float((data[label_col]==1).mean()), 4),
}
json_path = '/home/kazuha/Poly-Trader/data/ic_signs.json'
with open(json_path, 'w') as f:
    json.dump(result, f, indent=2)
print(f"\nResults saved to {json_path}")
