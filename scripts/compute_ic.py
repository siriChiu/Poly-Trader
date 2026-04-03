import json, sys, os
from datetime import datetime
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')
from sqlalchemy import create_engine, text
import numpy as np
import pandas as pd

# Use ABSOLUTE path — the relative "sqlite:///poly_trader.db" only works
# when cwd is /home/kazuha/Poly-Trader. execute_code sandbox has different cwd.
DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
engine = create_engine(f'sqlite:///{DB_PATH}')

features_df = pd.read_sql('SELECT * FROM features_normalized', engine)
labels_df = pd.read_sql('SELECT timestamp, label_up FROM labels', engine)

# Normalize timestamps to avoid microsecond mismatch (features have .000000, labels don't)
features_df['ts_key'] = pd.to_datetime(features_df['timestamp'], format='mixed').dt.floor('s')
labels_df['ts_key'] = pd.to_datetime(labels_df['timestamp'], format='mixed').dt.floor('s')
data = features_df.merge(labels_df, on='ts_key', suffixes=('', '_label'))

print(f"Total records in features: {len(features_df)}")
print(f"Total records after merge: {len(data)}")

sensory_features = {
    'feat_eye': 'Eye', 'feat_ear': 'Ear', 'feat_nose': 'Nose',
    'feat_tongue': 'Tongue', 'feat_body': 'Body', 'feat_pulse': 'Pulse',
    'feat_aura': 'Aura', 'feat_mind': 'Mind'
}
label_col = 'label_up'

print('\n=== Full Dataset IC (N={}) ==='.format(len(data)))
ics_full = {}
for feat_col, sense_name in sensory_features.items():
    valid = data[[feat_col, label_col]].dropna()
    if len(valid) < 10:
        print(f'  {sense_name:8s}: SKIP (n={len(valid)})')
        ics_full[sense_name] = None
        continue
    ic = valid[feat_col].corr(valid[label_col])
    std = valid[feat_col].std()
    print(f'  {sense_name:8s}: IC={ic:+.4f} (std={std:.4f}, n={len(valid)})')
    ics_full[sense_name] = round(float(ic), 4)

print()
print('=== Recent Data IC (last 5000) ===')
ics_recent = {}
data_sorted = data.sort_values('timestamp', ascending=False).head(5000)
for feat_col, sense_name in sensory_features.items():
    valid = data_sorted[[feat_col, label_col]].dropna()
    if len(valid) < 10:
        print(f'  {sense_name:8s}: SKIP (n={len(valid)})')
        ics_recent[sense_name] = None
        continue
    ic = valid[feat_col].corr(valid[label_col])
    std = valid[feat_col].std()
    print(f'  {sense_name:8s}: IC={ic:+.4f} (std={std:.4f}, n={len(valid)})')
    ics_recent[sense_name] = round(float(ic), 4)

print()
print('=== Feature Stats ===')
for feat_col, sense_name in sensory_features.items():
    valid = data[feat_col].dropna()
    unique_count = valid.nunique()
    print(f'  {sense_name:8s}: range=[{valid.min():.4f}, {valid.max():.4f}], unique={unique_count}')

result = {
    'timestamp': datetime.now().isoformat(),
    'n_records': len(data),
    'ics_full': ics_full,
    'ics_recent': ics_recent,
}
json_path = '/home/kazuha/Poly-Trader/data/ic_signs.json'
with open(json_path, 'w') as f:
    json.dump(result, f, indent=2)
print(f'\nIC results saved to {json_path}')
