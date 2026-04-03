"""Diagnose IC compute merge issue"""
import os, sys
sys.path.insert(0, '/home/kazuha/Poly-Trader')
os.chdir('/home/kazuha/Poly-Trader')

from sqlalchemy import create_engine, inspect
import pandas as pd

DB_PATH = '/home/kazuha/Poly-Trader/poly_trader.db'
engine = create_engine(f'sqlite:///{DB_PATH}')

# Check schema
inspector = inspect(engine)
for table_name in inspector.get_table_names():
    cols = inspector.get_columns(table_name)
    col_names = [c['name'] for c in cols]
    print(f"\n=== {table_name} ({len(cols)} columns) ===")
    print(f"Columns: {col_names}")
    cnt = pd.read_sql(f'SELECT COUNT(*) as c FROM {table_name}', engine)
    print(f"Row count: {cnt['c'].iloc[0]}")
    
    # Check timestamp column types and sample values
    if 'timestamp' in col_names:
        sample = pd.read_sql(f'SELECT timestamp FROM {table_name} LIMIT 5', engine)
        print(f"Sample timestamps: {sample['timestamp'].tolist()}")
    
    if 'timestamp_label' in col_names:
        sample = pd.read_sql(f'SELECT timestamp_label FROM {table_name} LIMIT 5', engine)
        print(f"Sample timestamp_label: {sample['timestamp_label'].tolist()}")

# Check overlap
feat_ts = set(pd.read_sql('SELECT timestamp FROM features_normalized', engine)['timestamp'].values)
label_ts = set(pd.read_sql('SELECT timestamp FROM labels', engine)['timestamp'].values)

print(f"\n=== Timestamp overlap ===")
print(f"Unique feature timestamps: {len(feat_ts)}")
print(f"Unique label timestamps: {len(label_ts)}")
intersection = feat_ts & label_ts
print(f"Matching timestamps: {len(intersection)}")
if len(intersection) < 100:
    print(f"Some feature timestamps: {sorted(feat_ts)[:10]}")
    print(f"Some label timestamps: {sorted(label_ts)[:10]}")
    # Try to understand format
    if intersection:
        print(f"Matched examples: {sorted(intersection)[:5]}")

# Check features_normalized columns and sample
feat_sample = pd.read_sql('SELECT * FROM features_normalized LIMIT 2', engine)
print(f"\n=== feature columns ({len(feat_sample.columns)}) ===")
print(feat_sample.columns.tolist())
print(feat_sample.head(2).to_string())

# Check labels columns
labels_sample = pd.read_sql('SELECT * FROM labels LIMIT 2', engine)
print(f"\n=== label columns ({len(labels_sample.columns)}) ===")
print(labels_sample.columns.tolist())
print(labels_sample.head(2).to_string())
