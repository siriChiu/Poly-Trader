#!/usr/bin/env python3
"""Fix timestamp format mismatch in features_normalized."""
import sqlite3, os, json

db_path = os.path.join(os.path.dirname(__file__), "poly_trader.db")
db = sqlite3.connect(db_path)

# Check how many have .000000 suffix
with_suffix = db.execute("SELECT COUNT(*) FROM features_normalized WHERE timestamp LIKE '%.000000'").fetchone()[0]
without_suffix = db.execute("SELECT COUNT(*) FROM features_normalized WHERE timestamp NOT LIKE '%.000000'").fetchone()[0]
print(f"Features with .000000 suffix: {with_suffix}")
print(f"Features without suffix: {without_suffix}")

# Check labels
label_suffix = db.execute("SELECT COUNT(*) FROM labels WHERE timestamp LIKE '%.000000'").fetchone()[0]
label_nosuffix = db.execute("SELECT COUNT(*) FROM labels WHERE timestamp NOT LIKE '%.000000'").fetchone()[0]
print(f"Labels with .000000 suffix: {label_suffix}")
print(f"Labels without suffix: {label_nosuffix}")

# Check raw_market_data
raw_suffix = db.execute("SELECT COUNT(*) FROM raw_market_data WHERE timestamp LIKE '%.000000'").fetchone()[0]
raw_nosuffix = db.execute("SELECT COUNT(*) FROM raw_market_data WHERE timestamp NOT LIKE '%.000000'").fetchone()[0]
print(f"Raw with .000000 suffix: {raw_suffix}")
print(f"Raw without suffix: {raw_nosuffix}")

# Fix features: strip .000000 suffix
if with_suffix > 0:
    print(f"\nFixing {with_suffix} feature rows...")
    db.execute("UPDATE features_normalized SET timestamp = REPLACE(timestamp, '.000000', '') WHERE timestamp LIKE '%.000000'")
    db.commit()
    
    # Verify
    after = db.execute("SELECT COUNT(*) FROM features_normalized WHERE timestamp LIKE '%.000000'").fetchone()[0]
    print(f"After fix, rows with suffix: {after}")
    
    # Check overlap
    overlap = db.execute("""
        SELECT COUNT(*) FROM features_normalized f 
        INNER JOIN labels l ON f.timestamp = l.timestamp
    """).fetchone()[0]
    print(f"After fix, matching timestamps: {overlap}")

# Also fix raw_market_data if needed
if raw_suffix > 0:
    print(f"\nFixing {raw_suffix} raw rows...")
    db.execute("UPDATE raw_market_data SET timestamp = REPLACE(timestamp, '.000000', '') WHERE timestamp LIKE '%.000000'")
    db.commit()
    after_raw = db.execute("SELECT COUNT(*) FROM raw_market_data WHERE timestamp LIKE '%.000000'").fetchone()[0]
    print(f"After fix, raw rows with suffix: {after_raw}")

# Save ic_signs.json with correct values from the existing (old) IC map
# We need to recompute, but first let's verify overlap
feat_ts = set(r[0] for r in db.execute("SELECT timestamp FROM features_normalized").fetchall())
label_ts = set(r[0] for r in db.execute("SELECT timestamp FROM labels").fetchall())
overlap = feat_ts & label_ts
print(f"\nFinal overlap: {len(overlap)} / {min(len(feat_ts), len(label_ts))}")

db.close()
print("DONE")
