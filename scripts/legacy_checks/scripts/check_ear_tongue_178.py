#!/usr/bin/env python3
"""Check feat_ear and feat_tongue value distribution in features_normalized."""
import sqlite3

db = sqlite3.connect("poly_trader.db")

# Check the actual values (not normalized)
for col in ["feat_ear", "feat_tongue"]:
    rows = db.execute(f"SELECT DISTINCT {col}, COUNT(*) FROM features_normalized GROUP BY {col} ORDER BY {col}").fetchall()
    print(f"\n{col} distinct values:")
    for val, cnt in rows:
        print(f"  {val}: {cnt} rows")
    
    total = db.execute(f"SELECT COUNT(*) FROM features_normalized").fetchone()[0]
    print(f"  Total rows: {total}")

# Check if these 4 values come from a specific model/feature version
for col in ["feat_ear", "feat_tongue"]:
    versions = db.execute(f"SELECT DISTINCT feature_version, COUNT(*) FROM features_normalized GROUP BY feature_version").fetchall()
    print(f"\nfeature_version distribution:")
    for v, c in versions:
        print(f"  {v}: {c} rows")

db.close()
