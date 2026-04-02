import sqlite3
import numpy as np

conn = sqlite3.connect(r"C:\Users\Kazuha\repo\Poly-Trader\poly_trader.db")

# Check feature column stats
cols = ["feat_pulse", "feat_eye_dist", "feat_ear_zscore", "feat_nose_sigmoid", 
        "feat_tongue_pct", "feat_body_roc", "feat_aura", "feat_mind"]

print("Feature column stats (last 1000):")
for col in cols:
    rows = conn.execute(f"SELECT {col} FROM features_normalized ORDER BY timestamp DESC LIMIT 1000").fetchall()
    v = np.array([r[0] for r in rows], dtype=float)
    std = np.std(v)
    unique = len(set(v))
    print(f"  {col}: mean={np.mean(v):.4f}, std={std:.4f}, unique={unique}")

conn.close()
