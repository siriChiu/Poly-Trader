#!/usr/bin/env python3
"""Check regime labels in the database."""
import sqlite3
db = sqlite3.connect("/home/kazuha/Poly-Trader/poly_trader.db")
l_rows = db.execute("SELECT DISTINCT regime_label FROM labels").fetchall()
print("Label regime_label values:", l_rows)
l_count = db.execute("SELECT COUNT(*) FROM labels WHERE regime_label IS NOT NULL").fetchone()[0]
print("Non-NULL regime labels:", l_count)
l_total = db.execute("SELECT COUNT(*) FROM labels").fetchone()[0]
print("Total labels:", l_total)

f_rows = db.execute("SELECT DISTINCT regime_label FROM features_normalized").fetchall()
print("\nFeature regime_label values:", f_rows)
f_count = db.execute("SELECT COUNT(*) FROM features_normalized WHERE regime_label IS NOT NULL").fetchone()[0]
print("Non-NULL regime_label features:", f_count)
f_total = db.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
print("Total features:", f_total)

# Sample rows to see what regime_label looks like
sample = db.execute("SELECT regime_label, COUNT(*) FROM labels GROUP BY regime_label").fetchall()
print("\nRegime distribution in labels:")
for row in sample:
    print(f"  {row[0]!r}: {row[1]}")

# Also check features
sample2 = db.execute("SELECT regime_label, COUNT(*) FROM features_normalized GROUP BY regime_label").fetchall()
print("\nRegime distribution in features:")
for row in sample2:
    print(f"  {row[0]!r}: {row[1]}")

db.close()
