#!/usr/bin/env python3
"""Fix P0: backfill regime_label in labels table from features_normalized"""
import sqlite3
import sys
import os
PROJECT_ROOT = "/home/kazuha/Poly-Trader"
sys.path.insert(0, PROJECT_ROOT)

db_path = os.path.join(PROJECT_ROOT, "poly_trader.db")
db = sqlite3.connect(db_path)

print("Before fix - labels regime_label distribution:")
counts = db.execute("SELECT regime_label, COUNT(*) FROM labels GROUP BY regime_label").fetchall()
for c in counts:
    print(f"  {c[0]}: {c[1]}")

# Backfill: update labels.regime_label from features_normalized
update = """
UPDATE labels
SET regime_label = (
    SELECT f.regime_label 
    FROM features_normalized f 
    WHERE f.timestamp = labels.timestamp
)
WHERE labels.regime_label IS NULL OR labels.regime_label = 'neutral'
"""
rows = db.execute(update)
print(f"\nUpdated {rows.rowcount} rows")
db.commit()

# Verify
print("\nAfter fix - labels regime_label distribution:")
counts2 = db.execute("SELECT regime_label, COUNT(*) FROM labels GROUP BY regime_label").fetchall()
for c in counts2:
    print(f"  {c[0]}: {c[1]}")

db.close()
print("\nDone!")
