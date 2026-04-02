import sys, sqlite3
import numpy as np
sys.path.insert(0, r"C:\Users\Kazuha\repo\Poly-Trader")
from scipy import stats

conn = sqlite3.connect(r"C:\Users\Kazuha\repo\Poly-Trader\poly_trader.db")

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

for sense, col in senses.items():
    rows = conn.execute(
        f"SELECT f.{col}, l.label FROM features_normalized f "
        f"JOIN labels l ON f.timestamp = l.timestamp "
        f"WHERE l.horizon = 4 ORDER BY f.timestamp DESC LIMIT 1000"
    ).fetchall()
    v = np.array([r[0] for r in rows], dtype=float)
    lb = np.array([r[1] for r in rows], dtype=float)
    ic, pval = stats.spearmanr(v, lb)
    flag = "WARN" if abs(ic) < 0.05 else "OK"
    print(f"[{flag}] {sense}: IC={ic:.4f} p={pval:.4f} N={len(rows)}")

conn.close()
