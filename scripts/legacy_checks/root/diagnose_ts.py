#!/usr/bin/env python3
"""Diagnose timestamp matching issue."""
import sqlite3, os

db_path = os.path.join(os.path.dirname(__file__), "poly_trader.db")
db = sqlite3.connect(db_path)

# Get sample timestamps from both tables
feat_ts = [r[0] for r in db.execute("SELECT timestamp FROM features_normalized ORDER BY timestamp LIMIT 5").fetchall()]
feat_ts_last = [r[0] for r in db.execute("SELECT timestamp FROM features_normalized ORDER BY timestamp DESC LIMIT 5").fetchall()]

label_ts = [r[0] for r in db.execute("SELECT timestamp FROM labels ORDER BY timestamp LIMIT 5").fetchall()]
label_ts_last = [r[0] for r in db.execute("SELECT timestamp FROM labels ORDER BY timestamp DESC LIMIT 5").fetchall()]

print("Feature timestamps (first 5):")
for ts in feat_ts:
    print(f"  repr={repr(ts)}  type={type(ts).__name__}")

print("\nLabels timestamps (first 5):")
for ts in label_ts:
    print(f"  repr={repr(ts)}  type={type(ts).__name__}")

print("\nFeature timestamps (last 5):")
for ts in feat_ts_last:
    print(f"  repr={repr(ts)}  type={type(ts).__name__}")

print("\nLabels timestamps (last 5):")
for ts in label_ts_last:
    print(f"  repr={repr(ts)}  type={type(ts).__name__}")

# Count unique timestamps
n_feat_ts = db.execute("SELECT COUNT(DISTINCT timestamp) FROM features_normalized").fetchone()[0]
n_label_ts = db.execute("SELECT COUNT(DISTINCT timestamp) FROM labels").fetchone()[0]

print(f"\nDistinct feature timestamps: {n_feat_ts}")
print(f"Distinct label timestamps: {n_label_ts}")

# Check overlap
feat_set = set(r[0] for r in db.execute("SELECT timestamp FROM features_normalized").fetchall())
label_set = set(r[0] for r in db.execute("SELECT timestamp FROM labels").fetchall())
overlap = feat_set & label_set
only_feat = feat_set - label_set
only_label = label_set - feat_set
print(f"Overlap: {len(overlap)}")
print(f"Only in features: {len(only_feat)}")
print(f"Only in labels: {len(only_label)}")
if only_feat:
    print(f"  Examples: {list(only_feat)[:5]}")
if only_label:
    print(f"  Examples: {list(only_label)[:5]}")
if overlap:
    print(f"  Overlap examples: {list(overlap)[:5]}")

# Try to find the common ones
if overlap:
    sample = list(overlap)[:3]
    for ts in sample:
        f_row = db.execute("SELECT * FROM features_normalized WHERE timestamp=?", (ts,)).fetchone()
        l_row = db.execute("SELECT * FROM labels WHERE timestamp=?", (ts,)).fetchone()
        print(f"\n=== Match: {ts} ===")
        print(f"  feature columns: {[c[0] for c in db.execute('SELECT * FROM features_normalized LIMIT 0').description]}")
        print(f"  feature values: {f_row}")
        print(f"  label columns: {[c[0] for c in db.execute('SELECT * FROM labels LIMIT 0').description]}")
        print(f"  label values: {l_row}")

db.close()
