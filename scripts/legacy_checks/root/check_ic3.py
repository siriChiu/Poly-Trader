import sqlite3
import numpy as np
from scipy import stats

conn = sqlite3.connect(r"C:\Users\Kazuha\repo\Poly-Trader\poly_trader.db")

# Check actual horizon counts
horizons = conn.execute("SELECT horizon_hours, COUNT(*) FROM labels GROUP BY horizon_hours").fetchall()
print(f"Label counts by horizon: {horizons}")

# Check features count
feat_cnt = conn.execute("SELECT COUNT(*) FROM features_normalized").fetchone()[0]
print(f"Features: {feat_cnt}")

# Check overlap h=4 vs features
overlap4 = conn.execute(
    "SELECT COUNT(*) FROM features_normalized f JOIN labels l ON f.timestamp = l.timestamp WHERE l.horizon_hours = 4"
).fetchone()[0]
overlap24 = conn.execute(
    "SELECT COUNT(*) FROM features_normalized f JOIN labels l ON f.timestamp = l.timestamp WHERE l.horizon_hours = 24"
).fetchone()[0]
print(f"Overlap h=4: {overlap4}, h=24: {overlap24}")

# Use h=4 explicitly
senses = {
    "pulse": "feat_pulse",
    "eye": "feat_eye_dist",
    "ear": "feat_ear_zscore",
    "nose": "feat_nose_sigmoid",
    "tongue": "feat_tongue_pct",
    "body": "feat_body_roc",
    "aura": "feat_aura",
    "mind": "feat_mind",
}

print("\n--- IC with h=4 labels, recent 1000 ---")
for sense, col in senses.items():
    rows = conn.execute(
        f"SELECT f.{col}, l.label FROM features_normalized f "
        f"JOIN labels l ON f.timestamp = l.timestamp "
        f"WHERE l.horizon_hours = 4 ORDER BY f.timestamp DESC LIMIT 1000"
    ).fetchall()
    if not rows:
        print(f"  {sense}: NO DATA for h=4")
        continue
    v = np.array([r[0] for r in rows], dtype=float)
    lb = np.array([r[1] for r in rows], dtype=float)
    ic, pval = stats.spearmanr(v, lb)
    flag = "WARN" if abs(ic) < 0.05 else "OK"
    print(f"  [{flag}] {sense}: IC={ic:.4f} p={pval:.4f} N={len(rows)}")

conn.close()
