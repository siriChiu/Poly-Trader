"""Find best replacement - check join issue and use features directly"""
import sqlite3, numpy as np, pandas as pd
from scipy import stats

conn = sqlite3.connect(r"C:\Users\Kazuha\repo\Poly-Trader\poly_trader.db")

# Check why only 2000 rows join but 11k features exist
feat_cnt = conn.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
raw_cnt = conn.execute("SELECT COUNT(*) FROM raw_market_data").fetchone()[0]
lbl_cnt = conn.execute("SELECT COUNT(*) FROM labels WHERE horizon_hours=4").fetchone()[0]
print(f"Features: {feat_cnt}, Raw: {raw_cnt}, Labels h=4: {lbl_cnt}")

# Check timestamps
feat_ts_sample = conn.execute("SELECT timestamp FROM features_normalized ORDER BY timestamp DESC LIMIT 3").fetchall()
raw_ts_sample = conn.execute("SELECT timestamp FROM raw_market_data ORDER BY timestamp DESC LIMIT 3").fetchall()
lbl_ts_sample = conn.execute("SELECT timestamp FROM labels WHERE horizon_hours=4 ORDER BY timestamp DESC LIMIT 3").fetchall()
print("Feat TS:", feat_ts_sample)
print("Raw TS:", raw_ts_sample)
print("Label TS:", lbl_ts_sample)

# Test candidate: oi_roc stored in raw -> compute signal and join with features+labels
# Use inner join between raw and features (nearest timestamp approach)
rows = conn.execute("""
    SELECT f.feat_pulse, r.oi_roc, l.label
    FROM features_normalized f
    JOIN labels l ON f.timestamp = l.timestamp
    JOIN raw_market_data r ON r.timestamp = f.timestamp
    WHERE l.horizon_hours = 4
    ORDER BY f.timestamp DESC
    LIMIT 5000
""").fetchall()
print(f"\nTriple-join rows: {len(rows)}")

if rows:
    oi_vals = np.array([r[1] for r in rows], dtype=object)
    none_cnt = sum(1 for v in oi_vals if v is None)
    print(f"oi_roc: none={none_cnt}/{len(rows)}")
    
    valid = [(r[0], r[1], r[2]) for r in rows if r[1] is not None]
    if valid:
        v = np.array([r[1] for r in valid], dtype=float)
        lb = np.array([r[2] for r in valid], dtype=float)
        ic, pval = stats.spearmanr(v, lb)
        print(f"oi_roc IC (N={len(valid)}): {ic:.4f} p={pval:.4f}")

conn.close()
