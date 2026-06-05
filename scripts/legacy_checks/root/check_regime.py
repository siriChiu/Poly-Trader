"""Check regime distribution in database."""
import sqlite3

db = sqlite3.connect('/home/kazuha/Poly-Trader/poly_trader.db')

feat_cols = [d[0] for d in db.execute("SELECT * FROM features_normalized LIMIT 0").description]
print(f"Features cols: {feat_cols}")

reg_label_feat = db.execute("SELECT regime_label, COUNT(*) FROM features_normalized GROUP BY regime_label").fetchall()
print(f"features regime_label distribution:")
for r in reg_label_feat:
    print(f"  {r[0]}: {r[1]}")

reg_label = db.execute("SELECT regime_label, COUNT(*) FROM labels GROUP BY regime_label").fetchall()
print(f"labels regime_label distribution:")
for r in reg_label:
    print(f"  {r[0]}: {r[1]}")

db.close()
