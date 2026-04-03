import sqlite3
import numpy as np
from scipy import stats

import os
_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poly_trader.db")
conn = sqlite3.connect(_db_path)

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
        f"SELECT f.{col}, l.future_return_pct FROM features_normalized f "
        f"JOIN labels l ON f.timestamp = l.timestamp "
        f"WHERE l.horizon_minutes = 240 ORDER BY f.timestamp DESC LIMIT 1000"
    ).fetchall()
    if not rows:
        rows = conn.execute(
            f"SELECT f.{col}, l.future_return_pct FROM features_normalized f "
            f"JOIN labels l ON f.timestamp = l.timestamp "
            f"ORDER BY f.timestamp DESC LIMIT 1000"
        ).fetchall()
    v = np.array([r[0] for r in rows], dtype=float)
    lb = np.array([r[1] for r in rows], dtype=float)
    ic, pval = stats.spearmanr(v, lb)
    flag = "WARN" if abs(ic) < 0.05 else "OK"
    print(f"[{flag}] {sense}: IC={ic:.4f} p={pval:.4f} N={len(rows)}")

# Check distinct horizon values
horizons = conn.execute("SELECT DISTINCT horizon_minutes FROM labels").fetchall()
print(f"\nDistinct horizons: {horizons}")
conn.close()
