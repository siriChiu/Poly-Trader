#!/usr/bin/env python3
"""Quick DB introspection"""
import sqlite3, sys
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "poly_trader.db"
db = sqlite3.connect(str(db_path))
cur = db.cursor()

# List tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

# Feature/label table names - check common names
feature_tables = [t for t in tables if 'feature' in t.lower()]
label_tables = [t for t in tables if 'label' in t.lower()]
raw_tables = [t for t in tables if 'raw' in t.lower() or 'market' in t.lower() or 'candle' in t.lower()]

print(f"\nFeature-like tables: {feature_tables}")
print(f"Label-like tables: {label_tables}")
print(f"Raw/Market-like tables: {raw_tables}")

# Count rows for each table
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM [{t}]")
        count = cur.fetchone()[0]
        print(f"  {t}: {count} rows")
    except Exception as e:
        print(f"  {t}: ERROR - {e}")

# Check columns on key tables
for t in tables:
    if count > 0:
        cur.execute(f"PRAGMA table_info([{t}])")
        cols = [r[1] for r in cur.fetchall()]
        if len(cols) <= 15:
            print(f"\nColumns for {t}: {cols}")
        else:
            print(f"\nColumns for {t} ({len(cols)} cols): {cols[:10]}... +{len(cols)-10} more")

# Close
db.close()
